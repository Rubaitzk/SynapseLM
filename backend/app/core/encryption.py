from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

class EncryptionError(Exception):
    pass

class MissingEncryptionKeyError(EncryptionError):
    pass

class InvalidCiphertextError(EncryptionError):
    pass

def get_fernet() -> Fernet:
    if not settings.CREDENTIAL_ENCRYPTION_KEY:
        raise MissingEncryptionKeyError("CREDENTIAL_ENCRYPTION_KEY is not configured.")
    try:
        return Fernet(settings.CREDENTIAL_ENCRYPTION_KEY.encode('utf-8'))
    except Exception as e:
        raise EncryptionError(f"Invalid CREDENTIAL_ENCRYPTION_KEY: {e}")

def encrypt_credential(plaintext: str) -> str:
    """Encrypts a plaintext credential using Fernet."""
    if not plaintext:
        raise ValueError("Cannot encrypt an empty credential.")
    
    fernet = get_fernet()
    try:
        return fernet.encrypt(plaintext.encode('utf-8')).decode('utf-8')
    except Exception as e:
        raise EncryptionError(f"Failed to encrypt credential: {e}")

def decrypt_credential(ciphertext: str) -> str:
    """Decrypts a ciphertext credential using Fernet."""
    if not ciphertext:
        raise ValueError("Cannot decrypt an empty ciphertext.")
    
    fernet = get_fernet()
    try:
        return fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        raise InvalidCiphertextError("Invalid or tampered ciphertext.")
    except Exception as e:
        raise EncryptionError(f"Failed to decrypt credential: {e}")
