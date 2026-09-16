from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
import pyotp
from app.database import get_db
from app.models import User
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])

class Setup2FARequest(BaseModel):
    email: str

class Verify2FARequest(BaseModel):
    email: str
    code: str

@router.post("/setup-2fa")
async def setup_2fa(req: Setup2FARequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalars().first()
    
    if not user:
        # Create a dummy user for the demo if none exists
        user = User(email=req.email, hashed_password="dummy_hash")
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.totp_secret:
        user.totp_secret = pyotp.random_base32()
        await db.commit()

    totp = pyotp.TOTP(user.totp_secret)
    uri = totp.provisioning_uri(name=user.email, issuer_name="LeakHunter V3")
    
    return {"secret": user.totp_secret, "provisioning_uri": uri}

@router.post("/verify-2fa")
async def verify_2fa(req: Verify2FARequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalars().first()
    
    if not user or not user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA not setup")

    totp = pyotp.TOTP(user.totp_secret)
    if totp.verify(req.code):
        user.is_totp_enabled = True
        await db.commit()
        # In a real app, generate JWT here
        return {"success": True, "token": "mock_jwt_token_12345"}
    else:
        raise HTTPException(status_code=401, detail="Invalid 2FA code")
