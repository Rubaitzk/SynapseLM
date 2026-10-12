import hashlib
from datetime import datetime, timedelta, timezone
from app.models.user import User, PasswordResetToken
from app.core.security import get_password_hash, create_access_token

def test_forgot_password_anti_enumeration(client):
    """
    Ensure requesting password reset for a non-existent email returns the identical
    generic success message to prevent user enumeration.
    """
    res = client.post("/api/auth/forgot-password", json={"email": "nonexistent_user_999@example.com"})
    assert res.status_code == 200
    data = res.json()
    assert "If an account with that email exists" in data["message"]

def test_password_reset_full_lifecycle_and_session_revocation(client, db_session):
    """
    End-to-end test of secure password reset:
    1. Create user and obtain a login session.
    2. Request password reset.
    3. Verify and consume reset token.
    4. Assert old password fails, new password succeeds.
    5. Assert previous active session token is revoked (401) due to token_version bump.
    6. Assert single-use: token cannot be reused.
    """
    # 1. Create user
    email = "charlie_reset@example.com"
    user = User(
        email=email,
        username="charlie_reset",
        hashed_password=get_password_hash("OldPassword123!"),
        token_version=1
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Obtain initial valid session token
    old_session_token = create_access_token(subject=user.id, token_version=1)
    # Verify old session token works
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_session_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 2. Request forgot password
    forgot_res = client.post("/api/auth/forgot-password", json={"email": email})
    assert forgot_res.status_code == 200
    assert "If an account with that email exists" in forgot_res.json()["message"]

    # Retrieve generated token from DB
    token_rec = db_session.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.is_used == False
    ).first()
    assert token_rec is not None
    assert token_rec.is_used is False

    # Simulate raw token by retrieving from test outbox or generating an explicit known token
    raw_token = "secure_test_reset_token_raw_value"
    token_rec.token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    db_session.commit()

    # 3. Verify token before submission
    verify_res = client.post("/api/auth/verify-reset-token", json={"token": raw_token})
    assert verify_res.status_code == 200
    assert verify_res.json()["valid"] is True

    # 4. Attempt reset with short password (policy check)
    short_res = client.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "short"})
    assert short_res.status_code == 400
    assert "at least 8 characters" in short_res.json()["detail"]

    # 5. Successfully reset password
    reset_res = client.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "NewSecretPassword456!"})
    assert reset_res.status_code == 200
    assert "successfully reset" in reset_res.json()["message"]

    # Verify token is consumed
    db_session.refresh(token_rec)
    assert token_rec.is_used is True

    # 6. Single-use check: reusing same token must fail
    reuse_res = client.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "AnotherPassword789!"})
    assert reuse_res.status_code == 400
    assert "Invalid or already used" in reuse_res.json()["detail"]

    # 7. Old password no longer works for login
    login_old = client.post("/api/auth/login", data={"username": email, "password": "OldPassword123!"})
    assert login_old.status_code == 400

    # 8. New password succeeds for login
    login_new = client.post("/api/auth/login", data={"username": email, "password": "NewSecretPassword456!"})
    assert login_new.status_code == 200
    new_token = login_new.json()["access_token"]
    assert new_token is not None

    # 9. Session Revocation: Old session token now rejected with 401
    me_revoked = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_session_token}"})
    assert me_revoked.status_code == 401

    # New session token works
    me_new = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert me_new.status_code == 200

def test_expired_reset_token_rejected(client, db_session):
    """
    Ensure expired tokens cannot be verified or used to reset password.
    """
    email = "david_expired@example.com"
    user = User(
        email=email,
        username="david_expired",
        hashed_password=get_password_hash("Password123!"),
        token_version=1
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    raw_token = "expired_raw_token_xyz"
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    token_rec = PasswordResetToken(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        expires_at=expired_time,
        is_used=False
    )
    db_session.add(token_rec)
    db_session.commit()

    # Verify fails
    verify_res = client.post("/api/auth/verify-reset-token", json={"token": raw_token})
    assert verify_res.status_code == 400
    assert "expired" in verify_res.json()["detail"].lower()

    # Reset fails
    reset_res = client.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "ValidNewPassword123!"})
    assert reset_res.status_code == 400
    assert "expired" in reset_res.json()["detail"].lower()

def test_forgot_password_rate_limiting(client):
    """
    Ensure rapid repeated requests for password reset are rate limited with 429.
    """
    target_email = "ratelimit_test@example.com"
    # Fire 5 requests (within limit)
    for _ in range(5):
        res = client.post("/api/auth/forgot-password", json={"email": target_email})
        assert res.status_code == 200

    # 6th request should trigger 429 Too Many Requests
    rate_limited_res = client.post("/api/auth/forgot-password", json={"email": target_email})
    assert rate_limited_res.status_code == 429
    assert "Too many password reset requests" in rate_limited_res.json()["detail"]
