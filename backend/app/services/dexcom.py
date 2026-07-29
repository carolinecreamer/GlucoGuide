from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from urllib.parse import urlencode

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import DexcomConnection, GlucoseReading, OAuthState
from app.services.crypto import TokenCipher


class DexcomService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def authorization_url(self, session: AsyncSession, user_id: str) -> str:
        if not self.settings.dexcom_client_id:
            raise RuntimeError("DEXCOM_CLIENT_ID is not configured")

        state = token_urlsafe(32)
        session.add(
            OAuthState(
                state=state,
                user_id=user_id,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
        await session.commit()
        query = urlencode(
            {
                "client_id": self.settings.dexcom_client_id,
                "redirect_uri": self.settings.dexcom_redirect_uri,
                "response_type": "code",
                "scope": "offline_access",
                "state": state,
            }
        )
        return f"{self.settings.dexcom_base_url}/v3/oauth2/login?{query}"

    async def complete_authorization(
        self, session: AsyncSession, code: str, state: str
    ) -> str:
        state_row = await session.get(OAuthState, state)
        now = datetime.now(timezone.utc)
        if state_row is None or state_row.expires_at.replace(tzinfo=timezone.utc) < now:
            raise ValueError("OAuth state is invalid or expired")

        secret = self.settings.dexcom_client_secret.get_secret_value()
        if not secret:
            raise RuntimeError("DEXCOM_CLIENT_SECRET is not configured")

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.settings.dexcom_base_url}/v3/oauth2/token",
                data={
                    "client_id": self.settings.dexcom_client_id,
                    "client_secret": secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.settings.dexcom_redirect_uri,
                },
            )
            response.raise_for_status()
            token = response.json()

        cipher = TokenCipher(self.settings)
        connection = await session.get(DexcomConnection, state_row.user_id)
        values = {
            "encrypted_access_token": cipher.encrypt(token["access_token"]),
            "encrypted_refresh_token": cipher.encrypt(token["refresh_token"]),
            "expires_at": now + timedelta(seconds=int(token["expires_in"])),
            "updated_at": now,
        }
        if connection is None:
            session.add(DexcomConnection(user_id=state_row.user_id, **values))
        else:
            for key, value in values.items():
                setattr(connection, key, value)

        await session.execute(delete(OAuthState).where(OAuthState.state == state))
        await session.commit()
        return state_row.user_id

    async def sync_egvs(
        self, session: AsyncSession, user_id: str, hours: int = 72
    ) -> int:
        connection = await session.get(DexcomConnection, user_id)
        if connection is None:
            raise ValueError("Dexcom is not connected")

        access_token = await self._valid_access_token(session, connection)
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=min(hours, 720))
        params = {
            "startDate": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "endDate": end.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.settings.dexcom_base_url}/v3/users/self/egvs",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            records = response.json().get("records", [])

        inserted = 0
        for record in records:
            raw_record_id = record.get("recordId") or record.get("record_id")
            if raw_record_id is None:
                continue
            record_id = str(raw_record_id)
            if await session.get(GlucoseReading, record_id):
                continue
            observed = record.get("systemTime") or record.get("displayTime")
            session.add(
                GlucoseReading(
                    id=record_id,
                    user_id=user_id,
                    observed_at=datetime.fromisoformat(observed.replace("Z", "+00:00")),
                    value_mg_dl=int(record["value"]),
                    trend=record.get("trend"),
                )
            )
            inserted += 1
        await session.commit()
        return inserted

    async def _valid_access_token(
        self, session: AsyncSession, connection: DexcomConnection
    ) -> str:
        cipher = TokenCipher(self.settings)
        now = datetime.now(timezone.utc)
        expires_at = connection.expires_at.replace(tzinfo=timezone.utc)
        if expires_at > now + timedelta(minutes=2):
            return cipher.decrypt(connection.encrypted_access_token)

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.settings.dexcom_base_url}/v3/oauth2/token",
                data={
                    "client_id": self.settings.dexcom_client_id,
                    "client_secret": self.settings.dexcom_client_secret.get_secret_value(),
                    "refresh_token": cipher.decrypt(connection.encrypted_refresh_token),
                    "grant_type": "refresh_token",
                },
            )
            response.raise_for_status()
            token = response.json()

        connection.encrypted_access_token = cipher.encrypt(token["access_token"])
        if token.get("refresh_token"):
            connection.encrypted_refresh_token = cipher.encrypt(token["refresh_token"])
        connection.expires_at = now + timedelta(seconds=int(token["expires_in"]))
        connection.updated_at = now
        await session.commit()
        return token["access_token"]
