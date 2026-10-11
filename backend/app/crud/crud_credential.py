from sqlalchemy.orm import Session
from app.models.credential import UserCredential
from app.core.encryption import encrypt_credential, decrypt_credential
from typing import List, Optional

def get_user_credentials(db: Session, user_id: str) -> List[UserCredential]:
    return db.query(UserCredential).filter(UserCredential.user_id == user_id).all()

def get_credential(db: Session, user_id: str, provider_name: str) -> Optional[UserCredential]:
    return db.query(UserCredential).filter(
        UserCredential.user_id == user_id,
        UserCredential.provider_name == provider_name
    ).first()

def set_credential(db: Session, user_id: str, provider_name: str, api_key: str) -> UserCredential:
    encrypted = encrypt_credential(api_key)
    
    cred = get_credential(db, user_id, provider_name)
    if cred:
        cred.encrypted_api_key = encrypted
        cred.key_version = "v1"
    else:
        cred = UserCredential(
            user_id=user_id,
            provider_name=provider_name,
            encrypted_api_key=encrypted,
            key_version="v1"
        )
        db.add(cred)
        
    db.commit()
    db.refresh(cred)
    return cred

def delete_credential(db: Session, user_id: str, provider_name: str) -> bool:
    cred = get_credential(db, user_id, provider_name)
    if cred:
        db.delete(cred)
        db.commit()
        return True
    return False

def get_decrypted_credential(db: Session, user_id: str, provider_name: str) -> Optional[str]:
    cred = get_credential(db, user_id, provider_name)
    if cred:
        return decrypt_credential(cred.encrypted_api_key)
    return None
