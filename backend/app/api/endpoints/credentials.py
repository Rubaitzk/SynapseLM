from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import httpx

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.credential import CredentialCreate, CredentialResponse
from app.crud import crud_credential
from app.services.llm.orchestrator import SUPPORTED_MODELS

router = APIRouter()

async def validate_provider_key(provider_name: str, api_key: str):
    if provider_name == "gemini":
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        headers = {"x-goog-api-key": api_key}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10.0)
                if resp.status_code != 200:
                    raise HTTPException(status_code=400, detail="Invalid Gemini API key.")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to validate Gemini API key due to network error.")
    elif provider_name == "openai":
        url = "https://api.openai.com/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10.0)
                if resp.status_code != 200:
                    raise HTTPException(status_code=400, detail="Invalid OpenAI API key.")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to validate OpenAI API key due to network error.")
    elif provider_name == "mock":
        pass
    else:
        raise HTTPException(status_code=400, detail=f"Validation not supported for {provider_name}")

@router.get("/", response_model=List[CredentialResponse])
def get_credentials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creds = crud_credential.get_user_credentials(db, current_user.id)
    # Return all supported providers and their configured status
    result = []
    configured_providers = {c.provider_name: c for c in creds}
    
    for provider in SUPPORTED_MODELS.keys():
        if provider == "mock":
            continue
            
        if provider in configured_providers:
            c = configured_providers[provider]
            result.append(CredentialResponse(
                id=c.id,
                provider_name=c.provider_name,
                is_configured=True,
                created_at=c.created_at,
                updated_at=c.updated_at
            ))
        else:
            from datetime import datetime, timezone
            result.append(CredentialResponse(
                id="unconfigured",
                provider_name=provider,
                is_configured=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ))
    return result

@router.post("/", response_model=CredentialResponse)
async def set_credential(
    cred_in: CredentialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    provider = cred_in.provider_name.lower()
    if provider not in SUPPORTED_MODELS or provider == "mock":
        raise HTTPException(status_code=400, detail="Unsupported provider.")
        
    await validate_provider_key(provider, cred_in.api_key)
    
    c = crud_credential.set_credential(db, current_user.id, provider, cred_in.api_key)
    return CredentialResponse(
        id=c.id,
        provider_name=c.provider_name,
        is_configured=True,
        created_at=c.created_at,
        updated_at=c.updated_at
    )

@router.delete("/{provider_name}")
def delete_credential(
    provider_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deleted = crud_credential.delete_credential(db, current_user.id, provider_name.lower())
    if not deleted:
        raise HTTPException(status_code=404, detail="Credential not found.")
    return {"status": "deleted"}
