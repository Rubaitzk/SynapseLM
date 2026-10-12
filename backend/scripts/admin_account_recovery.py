#!/usr/bin/env python3
"""
SynapseLM Administrative Account Recovery Tool.
Allows safe, controlled recovery of user accounts by authorized administrators.
Usage:
  python scripts/admin_account_recovery.py --list-accounts
  python scripts/admin_account_recovery.py --email user@example.com --generate-link
  python scripts/admin_account_recovery.py --email user@example.com --set-password <new_password>
"""
import sys
import os
import argparse
import secrets
import hashlib
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.models.user import User, PasswordResetToken
from app.core.security import get_password_hash
from app.core.config import settings

def list_accounts(db):
    users = db.query(User).order_by(User.created_at.desc()).all()
    print(f"\n[+] Total Accounts Found: {len(users)}")
    print("-" * 65)
    print(f"{'User ID':<38} | {'Username':<15} | {'Email'}")
    print("-" * 65)
    for u in users:
        print(f"{u.id:<38} | {u.username:<15} | {u.email}")
    print("-" * 65)

def generate_reset_link(db, email: str):
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user:
        # Fallback to username
        user = db.query(User).filter(User.username == email.strip()).first()
    if not user:
        print(f"[!] Error: No account found matching '{email}'")
        sys.exit(1)

    # Invalidate previous unused tokens
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.is_used == False
    ).update({"is_used": True})

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=60) # 60 mins for admin link

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        is_used=False
    )
    db.add(reset_token)
    db.commit()

    frontend_base = settings.FRONTEND_URL.rstrip("/")
    reset_url = f"{frontend_base}/reset-password?token={raw_token}"
    print(f"\n[+] Single-use Password Reset Link generated for {user.username} ({user.email}):")
    print(f"    {reset_url}")
    print(f"    (Valid for 60 minutes)\n")

def set_password(db, email: str, new_password: str):
    if len(new_password) < 8:
        print("[!] Error: New password must be at least 8 characters long.")
        sys.exit(1)

    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user:
        user = db.query(User).filter(User.username == email.strip()).first()
    if not user:
        print(f"[!] Error: No account found matching '{email}'")
        sys.exit(1)

    user.hashed_password = get_password_hash(new_password)
    user.token_version = (getattr(user, "token_version", 1) or 1) + 1

    # Invalidate outstanding tokens
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id
    ).update({"is_used": True})

    db.commit()
    print(f"\n[+] Password successfully updated for account {user.username} ({user.email})!")
    print(f"    Previous active sessions have been invalidated.\n")

def main():
    parser = argparse.ArgumentParser(description="SynapseLM Administrative Account Recovery")
    parser.add_argument("--list-accounts", action="store_true", help="List registered user accounts (emails and usernames)")
    parser.add_argument("--email", type=str, help="Target account email or username")
    parser.add_argument("--generate-link", action="store_true", help="Generate single-use password reset link")
    parser.add_argument("--set-password", type=str, help="Directly set a new secure password for the account")

    args = parser.parse_args()
    db = SessionLocal()

    try:
        if args.list_accounts:
            list_accounts(db)
        elif args.email and args.generate_link:
            generate_reset_link(db, args.email)
        elif args.email and args.set_password:
            set_password(db, args.email, args.set_password)
        else:
            parser.print_help()
    finally:
        db.close()

if __name__ == "__main__":
    main()
