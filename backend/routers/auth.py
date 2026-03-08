from fastapi import APIRouter, HTTPException
from backend import db
from backend.auth_utils import (
    create_access_token,
    create_verification_token,
    hash_password,
    verify_password,
)
from backend.schemas import (
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    TokenResponse,
)
from backend.email_utils import send_verification_email
import uuid
import time

router = APIRouter()

# simple in-memory rate limit: email -> [timestamps]
RESEND_LIMIT = 3
RESEND_WINDOW_SECONDS = 60 * 60
_resend_attempts: dict[str, list[float]] = {}

db.init_db()


def _check_resend_rate(email: str) -> None:
    now = time.time()
    attempts = _resend_attempts.get(email, [])
    attempts = [t for t in attempts if now - t < RESEND_WINDOW_SECONDS]
    if len(attempts) >= RESEND_LIMIT:
        raise HTTPException(status_code=429, detail="Too many verification requests. Try later.")
    attempts.append(now)
    _resend_attempts[email] = attempts


@router.post("/register")
def register(payload: RegisterRequest):
    existing = db.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    token = create_verification_token()
    user_id = str(uuid.uuid4())
    db.create_user(
        user_id=user_id,
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        verification_token=token,
    )

    try:
        send_verification_email(payload.email, token)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send verification email: {exc}")

    return {"message": "Check your email to verify your account."}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    user = db.get_user_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    if not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    if not user["is_verified"]:
        raise HTTPException(status_code=403, detail="Email not verified. Check your inbox.")

    token = create_access_token(user["id"])
    return TokenResponse(access_token=token)


@router.get("/verify", response_model=TokenResponse)
def verify(token: str):
    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token.")

    db.mark_verified(user["id"])
    access_token = create_access_token(user["id"])
    return TokenResponse(access_token=access_token)


@router.post("/resend-verification")
def resend_verification(payload: ResendVerificationRequest):
    _check_resend_rate(payload.email)

    user = db.get_user_by_email(payload.email)
    if not user:
        return {"message": "Verification email resent."}

    if user["is_verified"]:
        return {"message": "Email already verified."}

    token = create_verification_token()
    db.update_verification_token(user["id"], token)

    try:
        send_verification_email(payload.email, token)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send verification email: {exc}")

    return {"message": "Verification email resent."}
