from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.models import (
    ExerciseLog,
    GlucoseReading,
    InsulinDose,
    MealLog,
    RegimenSetting,
    UserProfile,
)
from app.schemas import (
    DoseInput,
    ExerciseGuidanceRequest,
    ExerciseInput,
    GuidanceView,
    InsightView,
    MealGuidanceRequest,
    MealInput,
    ProfileUpsert,
    ProfileView,
    RegimenInput,
)
from app.services.advisory import exercise_guidance, meal_guidance
from app.services.dexcom import DexcomService
from app.services.insights import generate_insights

router = APIRouter(prefix="/api/v1")


def user_id(settings: Settings = Depends(get_settings)) -> str:
    # Development vertical slice. Replace with the authenticated subject from
    # Microsoft Entra External ID before any multi-user deployment.
    return settings.demo_user_id


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "glucoguide-api"}


@router.put("/profile", response_model=ProfileView)
async def upsert_profile(
    payload: ProfileUpsert,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> UserProfile:
    profile = await session.get(UserProfile, current_user)
    if profile is None:
        profile = UserProfile(id=current_user)
        session.add(profile)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    await session.commit()
    await session.refresh(profile)
    return profile


@router.get("/profile", response_model=ProfileView)
async def get_profile(
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> UserProfile:
    profile = await session.get(UserProfile, current_user)
    if profile is None:
        raise HTTPException(404, "Profile not found")
    return profile


@router.put("/regimen")
async def replace_regimen(
    payload: list[RegimenInput],
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> dict:
    existing = list(
        (
            await session.scalars(
                select(RegimenSetting).where(RegimenSetting.user_id == current_user)
            )
        ).all()
    )
    for item in existing:
        await session.delete(item)
    session.add_all(
        [RegimenSetting(user_id=current_user, **item.model_dump()) for item in payload]
    )
    await session.commit()
    return {"saved": len(payload)}


@router.post("/logs/meals", status_code=201)
async def log_meal(
    payload: MealInput,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> dict:
    item = MealLog(user_id=current_user, **payload.model_dump())
    session.add(item)
    await session.commit()
    return {"id": item.id}


@router.post("/logs/exercise", status_code=201)
async def log_exercise(
    payload: ExerciseInput,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> dict:
    item = ExerciseLog(user_id=current_user, **payload.model_dump())
    session.add(item)
    await session.commit()
    return {"id": item.id}


@router.post("/logs/doses", status_code=201)
async def log_dose(
    payload: DoseInput,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> dict:
    item = InsulinDose(user_id=current_user, **payload.model_dump())
    session.add(item)
    await session.commit()
    return {"id": item.id}


@router.get("/glucose/recent")
async def recent_glucose(
    limit: int = Query(default=48, ge=1, le=288),
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> list[dict]:
    readings = (
        await session.scalars(
            select(GlucoseReading)
            .where(GlucoseReading.user_id == current_user)
            .order_by(GlucoseReading.observed_at.desc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": row.id,
            "observed_at": row.observed_at,
            "value_mg_dl": row.value_mg_dl,
            "trend": row.trend,
        }
        for row in readings
    ]


@router.post("/sample-data")
async def create_sample_data(
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> dict:
    if await session.scalar(
        select(GlucoseReading.id).where(GlucoseReading.user_id == current_user).limit(1)
    ):
        return {"created": 0}
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    rows = []
    for index in range(288):
        observed = now - timedelta(minutes=(287 - index) * 5)
        baseline = 125 + (20 if 7 <= observed.hour <= 10 else 0)
        value = baseline + ((index % 24) - 12)
        rows.append(
            GlucoseReading(
                id=f"sample-{current_user}-{index}",
                user_id=current_user,
                observed_at=observed,
                value_mg_dl=value,
                trend="Flat",
                source="sample",
            )
        )
    session.add_all(rows)
    await session.commit()
    return {"created": len(rows)}


@router.get("/integrations/dexcom/start")
async def dexcom_start(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: str = Depends(user_id),
) -> dict:
    try:
        url = await DexcomService(settings).authorization_url(session, current_user)
        return {"authorization_url": url}
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error


@router.get("/integrations/dexcom/callback", response_class=HTMLResponse)
async def dexcom_callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> str:
    try:
        await DexcomService(settings).complete_authorization(session, code, state)
    except (ValueError, RuntimeError) as error:
        raise HTTPException(400, str(error)) from error
    except httpx.HTTPError as error:
        raise HTTPException(502, "Dexcom rejected the authorization exchange") from error
    return """
    <html><body style="font-family: -apple-system; padding: 32px">
      <h1>Dexcom connected</h1>
      <p>You can return to GlucoGuide and synchronize your glucose history.</p>
    </body></html>
    """


@router.post("/integrations/dexcom/sync")
async def dexcom_sync(
    hours: int = Query(default=72, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: str = Depends(user_id),
) -> dict:
    try:
        inserted = await DexcomService(settings).sync_egvs(session, current_user, hours)
        return {"inserted": inserted}
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error
    except httpx.HTTPError as error:
        raise HTTPException(502, "Dexcom synchronization failed") from error


@router.post("/insights/generate", response_model=list[InsightView])
async def refresh_insights(
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
):
    return await generate_insights(session, current_user)


@router.post("/guidance/exercise", response_model=GuidanceView)
async def get_exercise_guidance(
    payload: ExerciseGuidanceRequest,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
):
    try:
        return await exercise_guidance(session, current_user, payload)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error


@router.post("/guidance/meals", response_model=GuidanceView)
async def get_meal_guidance(
    payload: MealGuidanceRequest,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
):
    return await meal_guidance(session, current_user, payload)
