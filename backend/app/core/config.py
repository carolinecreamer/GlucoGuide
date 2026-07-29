from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite+aiosqlite:///./glucoguide.db"
    api_base_url: str = "http://localhost:8000"
    dexcom_environment: Literal["sandbox", "production"] = "sandbox"
    dexcom_client_id: str = ""
    dexcom_client_secret: SecretStr = SecretStr("")
    dexcom_redirect_uri: str = (
        "http://localhost:8000/api/v1/integrations/dexcom/callback"
    )
    token_encryption_key: SecretStr = SecretStr("")
    demo_user_id: str = "00000000-0000-0000-0000-000000000001"

    @property
    def dexcom_base_url(self) -> str:
        if self.dexcom_environment == "sandbox":
            return "https://sandbox-api.dexcom.com"
        return "https://api.dexcom.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()

