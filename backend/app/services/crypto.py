from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings


class TokenCipher:
    def __init__(self, settings: Settings):
        key = settings.token_encryption_key.get_secret_value()
        if not key:
            raise RuntimeError("TOKEN_ENCRYPTION_KEY is required for Dexcom connections")
        self._fernet = Fernet(key.encode())

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken as error:
            raise RuntimeError("Stored Dexcom token could not be decrypted") from error

