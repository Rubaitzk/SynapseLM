import pytest
from cryptography.fernet import Fernet
from app.core.encryption import encrypt_credential, decrypt_credential, MissingEncryptionKeyError, InvalidCiphertextError, get_fernet

def test_encrypt_decrypt_round_trip(monkeypatch):
    # Setup test key
    test_key = Fernet.generate_key().decode('utf-8')
    monkeypatch.setattr("app.core.config.settings.CREDENTIAL_ENCRYPTION_KEY", test_key)
    
    plaintext = "sk-test-api-key-12345"
    ciphertext = encrypt_credential(plaintext)
    
    assert ciphertext != plaintext
    
    decrypted = decrypt_credential(ciphertext)
    assert decrypted == plaintext

def test_tampered_ciphertext(monkeypatch):
    test_key = Fernet.generate_key().decode('utf-8')
    monkeypatch.setattr("app.core.config.settings.CREDENTIAL_ENCRYPTION_KEY", test_key)
    
    ciphertext = encrypt_credential("valid-key")
    
    # Tamper with the ciphertext (assuming base64url encoded fernet token)
    tampered = ciphertext[:-4] + "AAAA"
    
    with pytest.raises(InvalidCiphertextError):
        decrypt_credential(tampered)

def test_missing_encryption_key_handling(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.CREDENTIAL_ENCRYPTION_KEY", None)
    
    with pytest.raises(MissingEncryptionKeyError):
        encrypt_credential("some-key")
        
    with pytest.raises(MissingEncryptionKeyError):
        decrypt_credential("some-ciphertext")

def test_empty_credential_rejected(monkeypatch):
    test_key = Fernet.generate_key().decode('utf-8')
    monkeypatch.setattr("app.core.config.settings.CREDENTIAL_ENCRYPTION_KEY", test_key)
    
    with pytest.raises(ValueError):
        encrypt_credential("")
        
    with pytest.raises(ValueError):
        decrypt_credential("")
