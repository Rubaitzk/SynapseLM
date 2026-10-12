import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.api import deps
from app.crud import crud_user
from app.models.user import User, PasswordResetToken
from app.services.email import send_password_reset_email
from app.schemas.user import (
    UserCreate, 
    UserResponse, 
    ForgotPasswordRequest, 
    VerifyResetTokenRequest, 
    ResetPasswordRequest, 
    PasswordResetResponse
)
from app.schemas.token import Token

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(deps.get_db)):
    """
    Register a new user.
    """
    user = crud_user.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists."
        )
    user_by_username = crud_user.get_user_by_username(db, username=user_in.username)
    if user_by_username:
        raise HTTPException(
            status_code=400,
            detail="A user with this username already exists."
        )
    user = crud_user.create_user(db, user=user_in)
    return user

@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    # form_data.username can be email or username in our logic, let's treat it as email
    user = crud_user.get_user_by_email(db, email=form_data.username)
    if not user:
        # Fallback to username
        user = crud_user.get_user_by_username(db, username=form_data.username)
        
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email/username or password")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires, token_version=getattr(user, "token_version", 1)
    )
    return {"access_token": access_token, "token_type": "bearer"}

from fastapi import Request

_forgot_password_history: dict[str, list[datetime]] = {}

def _check_rate_limit(key: str, limit: int = 5, window_seconds: int = 900):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=window_seconds)
    timestamps = [t for t in _forgot_password_history.get(key, []) if t > cutoff]
    if len(timestamps) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Please try again later."
        )
    timestamps.append(now)
    _forgot_password_history[key] = timestamps

@router.post("/forgot-password", response_model=PasswordResetResponse)
def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    """
    Request a password-reset email.
    Always returns a generic success message to prevent account enumeration.
    Protected by rate limiting.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{req.email.strip().lower()}"
    _check_rate_limit(rate_key, limit=5, window_seconds=900)

    email_clean = req.email.strip().lower()
    user = crud_user.get_user_by_email(db, email=email_clean)
    if user:
        # Invalidate any existing unused tokens for this user
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_used == False
        ).update({"is_used": True})

        # Generate a cryptographically secure, unpredictable, single-use reset token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_used=False
        )
        db.add(reset_token)
        db.commit()

        # Send transactional email with production frontend link
        send_password_reset_email(user.email, user.username, raw_token)

    return {"message": "If an account with that email exists, password reset instructions have been sent."}

@router.post("/verify-reset-token")
def verify_reset_token(
    req: VerifyResetTokenRequest,
    db: Session = Depends(deps.get_db)
):
    """
    Verify if a password reset token is valid and unexpired before presenting the reset form.
    """
    token_str = req.token.strip()
    token_hash = hashlib.sha256(token_str.encode("utf-8")).hexdigest()
    
    token_rec = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.is_used == False
    ).first()

    if not token_rec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used password reset token."
        )

    expires_at = token_rec.expires_at.replace(tzinfo=timezone.utc) if token_rec.expires_at.tzinfo is None else token_rec.expires_at
    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired."
        )

    return {"valid": True}

@router.post("/reset-password", response_model=PasswordResetResponse)
def reset_password(
    req: ResetPasswordRequest,
    db: Session = Depends(deps.get_db)
):
    """
    Validate and consume a reset token while atomically updating the password and revoking old sessions.
    """
    if len(req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )

    token_str = req.token.strip()
    token_hash = hashlib.sha256(token_str.encode("utf-8")).hexdigest()

    # Lock token row to prevent concurrent reuse
    token_rec = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash
    ).with_for_update().first()

    if not token_rec or token_rec.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used password reset token."
        )

    expires_at = token_rec.expires_at.replace(tzinfo=timezone.utc) if token_rec.expires_at.tzinfo is None else token_rec.expires_at
    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired."
        )

    user = db.query(User).filter(User.id == token_rec.user_id).with_for_update().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    # 1. Update password using established secure bcrypt hashing
    user.hashed_password = get_password_hash(req.new_password)

    # 2. Invalidate all active sessions via token_version increment
    user.token_version = (getattr(user, "token_version", 1) or 1) + 1

    # 3. Atomically consume token
    token_rec.is_used = True

    # 4. Invalidate any other outstanding reset tokens for this account
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.id != token_rec.id
    ).update({"is_used": True})

    db.commit()

    return {"message": "Password has been successfully reset. You may now log in with your new password."}

@router.post("/logout")
def logout():
    """
    Logout route.
    For JWT, true logout means deleting token on client side, but we provide this for API completeness.
    """
    return {"msg": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user = Depends(deps.get_current_user)):
    """
    Get current user details.
    """
    return current_user
