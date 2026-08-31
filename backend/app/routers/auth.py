import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.core.deps import get_current_user
from app.models.email_verification_token import EmailVerificationToken
from app.models.user import User
from app.schemas.user import TokenOut, UserLogin, UserOut, UserRegister
from app.services.email import ConsoleEmailService

router = APIRouter(prefix="/api/auth", tags=["auth"])

_email_service = ConsoleEmailService()

VERIFICATION_TOKEN_EXPIRE_HOURS = 24


class MessageOut(BaseModel):
    message: str


def _issue_verification_token(db: Session, user: User) -> EmailVerificationToken:
    token = EmailVerificationToken(
        user_id=user.id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def _send_verification_email(user: User, token: EmailVerificationToken) -> None:
    url = f"{settings.FRONTEND_BASE_URL}/verify-email?token={token.token}"
    _email_service.send_verification_email(user.email, url)


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="user",
        dietary_preferences=[],
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    db.refresh(user)

    verification_token = _issue_verification_token(db, user)
    _send_verification_email(user, verification_token)

    token = create_access_token(user.id)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    # Same 401 for "no such user" and "wrong password" -- deliberately not
    # distinguishing the two, so this endpoint can't be used to enumerate
    # which emails have accounts.
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(user.id)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/verify", response_model=MessageOut)
def verify_email(token: str, db: Session = Depends(get_db)):
    record = db.query(EmailVerificationToken).filter(EmailVerificationToken.token == token).first()
    if not record:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    if record.used_at is not None:
        raise HTTPException(status_code=400, detail="This verification link has already been used")
    if record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This verification link has expired")

    user = db.query(User).filter(User.id == record.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    user.is_verified = True
    record.used_at = datetime.now(timezone.utc)
    db.commit()

    return MessageOut(message="Email verified successfully")


@router.post("/resend-verification", response_model=MessageOut)
def resend_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.is_verified:
        raise HTTPException(status_code=409, detail="Email is already verified")

    # Invalidate any outstanding unused tokens before issuing a new one, so
    # only the most recently sent link is valid.
    outstanding = (
        db.query(EmailVerificationToken)
        .filter(
            EmailVerificationToken.user_id == current_user.id,
            EmailVerificationToken.used_at.is_(None),
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    for record in outstanding:
        record.used_at = now
    db.commit()

    verification_token = _issue_verification_token(db, current_user)
    _send_verification_email(current_user, verification_token)

    return MessageOut(message="Verification email sent")
