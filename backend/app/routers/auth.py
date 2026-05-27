"""
Mr. Scrapper — Auth Router
Registration, login, email confirmation, and user info.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import (
    MessageResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import (
    create_access_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ─────────────────────────────────────────────────────────────────
# POST /api/auth/register
# ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Register a new user. Sends a confirmation email to activate the account.
    """
    # Check if email already exists
    existing = await db.execute(
        select(User).where(User.email == payload.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Um usuário com este email já existe.",
        )

    # Create user (verified immediately)
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()

    return MessageResponse(
        message="Conta criada com sucesso!",
        detail="Agora você pode fazer login.",
    )


# ─────────────────────────────────────────────────────────────────
# POST /api/auth/login
# ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and return a JWT access token.
    """
    result = await db.execute(
        select(User).where(User.email == payload.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada. Entre em contato com o administrador.",
        )

    access_token = create_access_token(str(user.id), user.email)
    return TokenResponse(access_token=access_token)


# ─────────────────────────────────────────────────────────────────
# GET /api/auth/confirm/{token}
# ─────────────────────────────────────────────────────────────────

@router.get("/confirm/{token}", response_model=MessageResponse)
async def confirm_email(token: str, db: AsyncSession = Depends(get_db)):
    """
    Confirm a user's email address using the token sent via email.
    """
    payload = decode_token(token)

    if payload.get("type") != "email_confirm":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido para confirmação de email.",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    if user.is_verified:
        return MessageResponse(message="Email já foi confirmado anteriormente.")

    user.is_verified = True
    await db.commit()

    return MessageResponse(
        message="Email confirmado com sucesso! Agora você pode fazer login.",
    )


# ─────────────────────────────────────────────────────────────────
# GET /api/auth/me
# ─────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
