import base64
import hashlib
import os

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:  # pragma: no cover - optional dependency
    Fernet = None
    InvalidToken = Exception


def _get_fernet():
    if Fernet is None:
        raise RuntimeError("cryptography is required for API key encryption")
    secret = os.getenv("API_KEY_ENCRYPTION_SECRET") or os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError("API_KEY_ENCRYPTION_SECRET or SECRET_KEY must be set")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    if not api_key:
        raise ValueError("API key is required")
    fernet = _get_fernet()
    return fernet.encrypt(api_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted_api_key: str) -> str | None:
    if not encrypted_api_key:
        return None
    fernet = _get_fernet()
    try:
        return fernet.decrypt(encrypted_api_key.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise ValueError("Invalid encrypted API key")
