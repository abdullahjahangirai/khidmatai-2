from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models, database, auth

router = APIRouter()

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: models.RoleEnum = models.RoleEnum.user

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(database.get_db)):
    # Check if user exists
    result = await db.execute(select(models.Profile).where(models.Profile.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth.get_password_hash(req.password)
    new_user = models.Profile(email=req.email, role=req.role, status=models.StatusEnum.active, password_hash=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    access_token = auth.create_access_token(data={"sub": str(new_user.id), "role": new_user.role.value})
    return TokenResponse(access_token=access_token)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Profile).where(models.Profile.email == req.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    # Verify the provided password against the stored hash
    if not auth.verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = auth.create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=access_token)
