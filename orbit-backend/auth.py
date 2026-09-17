import os
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
from database import get_db
from logging_config import logger

# No hardcoded fallback secret: a static default that ships in a public repo
# is effectively a published secret. If ORBIT_SECRET_KEY isn't set, generate a
# random one for this process instead — safe, but every existing token becomes
# invalid whenever the process restarts, which is your signal to set the env
# var for real.
_env_secret = os.environ.get("ORBIT_SECRET_KEY")
if _env_secret:
    SECRET_KEY = _env_secret
else:
    SECRET_KEY = secrets.token_urlsafe(48)
    print(
        "\n[orbit] WARNING: ORBIT_SECRET_KEY is not set.\n"
        "[orbit] Generated a random secret key for THIS PROCESS ONLY.\n"
        "[orbit] All existing tokens will be invalidated on the next restart,\n"
        "[orbit] and this is not safe for any real deployment.\n"
        "[orbit] Set ORBIT_SECRET_KEY as an environment variable to fix this.\n"
    )

ALGORITHM = "HS256"
# Shortened from 7 days: a stolen token this long-lived is a standing risk.
# There's no refresh-token flow yet, so this trades some convenience (users
# re-authenticate daily) for a much smaller exposure window. Worth adding
# refresh tokens later if the daily re-login becomes annoying.
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

FAILED_LOGIN_LIMIT = 5
LOCKOUT_MINUTES = 15
VERIFICATION_TOKEN_HOURS = 24
PASSWORD_RESET_TOKEN_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    # jti (JWT ID) gives each token a unique identifier so a specific token
    # can be revoked on logout without invalidating every other session.
    # iat (issued at) lets us invalidate every token issued before a given
    # moment — used when a password is reset, so an old leaked token can't
    # keep working just because it hasn't technically expired yet.
    to_encode.update({"exp": expire, "iat": int(now.timestamp()), "jti": secrets.token_urlsafe(16)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def revoke_token(token: str, db: Session) -> None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return  # already invalid/garbage — nothing to revoke
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        return
    if not db.query(models.RevokedToken).filter(models.RevokedToken.jti == jti).first():
        db.add(models.RevokedToken(jti=jti, expires_at=datetime.utcfromtimestamp(exp)))
        db.commit()


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")
        iat: int = payload.get("iat")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if jti and db.query(models.RevokedToken).filter(models.RevokedToken.jti == jti).first():
        raise credentials_exception  # token was revoked (e.g. user logged out)

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if user.sessions_invalidated_at and iat:
        if datetime.utcfromtimestamp(iat) < user.sessions_invalidated_at:
            raise credentials_exception  # issued before a password reset — treat as stale

    return user


def generate_verification_token() -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_HOURS)
    return token, expires


def generate_password_reset_token() -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    # Deliberately much shorter-lived than email verification — this token
    # grants a full account takeover if intercepted, not just a "verified"
    # flag, so it should be usable for minutes, not a full day.
    expires = datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TOKEN_MINUTES)
    return token, expires


def _send_email(to_email: str, subject: str, body: str, fallback_label: str, fallback_url: str) -> None:
    """
    Shared SMTP sender used by both verification and password-reset emails.
    Sends via SMTP if configured, otherwise prints the link so development
    still works with zero setup. Plain SMTP (not a vendor SDK) works
    unmodified with SES, Postmark, SendGrid, Mailgun, or Gmail — see the
    README for provider-specific values.
    """
    smtp_host = os.environ.get("SMTP_HOST")
    if not smtp_host:
        print(f"\n[orbit] SMTP_HOST not set — printing the {fallback_label} link instead of emailing it.")
        print(f"[orbit] {fallback_label} link for {to_email}:\n[orbit]   {fallback_url}\n")
        return

    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM", smtp_user or "no-reply@orbit.app")
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() != "false"

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp_from
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if use_tls:
                server.starttls(context=ssl.create_default_context())
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(message)
        logger.info("Sent %s email to %s", fallback_label, to_email)
    except Exception as exc:
        # A flaky email provider shouldn't break the request — log it and
        # fall back to printing the link so the flow is still usable.
        logger.warning("Failed to send %s email to %s: %s", fallback_label, to_email, exc)
        print(f"[orbit] Email send failed — {fallback_label} link for {to_email}:\n[orbit]   {fallback_url}\n")


def send_verification_email(email: str, token: str) -> None:
    public_api_url = os.environ.get("ORBIT_PUBLIC_API_URL", "http://localhost:8000")
    verify_url = f"{public_api_url}/auth/verify?token={token}"
    body = (
        "Welcome to Orbit!\n\n"
        f"Verify your email by opening this link:\n{verify_url}\n\n"
        f"This link expires in {VERIFICATION_TOKEN_HOURS} hours. "
        "If you didn't create this account, you can ignore this message."
    )
    _send_email(email, "Verify your Orbit account", body, "verification", verify_url)


def send_password_reset_email(email: str, token: str) -> None:
    # This one MUST point at the frontend, not the backend — resetting a
    # password needs a form for the person to type a new one into, unlike
    # verification which is a one-click confirm handled entirely by the API.
    public_frontend_url = os.environ.get("ORBIT_PUBLIC_FRONTEND_URL", "http://localhost:5173")
    reset_url = f"{public_frontend_url}/?resetToken={token}"
    body = (
        "Someone requested a password reset for your Orbit account.\n\n"
        f"Choose a new password by opening this link:\n{reset_url}\n\n"
        f"This link expires in {PASSWORD_RESET_TOKEN_MINUTES} minutes. "
        "If you didn't request this, you can safely ignore this message — your password won't change."
    )
    _send_email(email, "Reset your Orbit password", body, "password reset", reset_url)


def is_locked(user: models.User) -> bool:
    return bool(user.locked_until and user.locked_until > datetime.utcnow())


def register_failed_login(user: models.User, db: Session) -> None:
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= FAILED_LOGIN_LIMIT:
        user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
        user.failed_login_attempts = 0
        logger.warning("Account locked after repeated failed logins: %s", user.email)
    db.commit()


def register_successful_login(user: models.User, db: Session) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
