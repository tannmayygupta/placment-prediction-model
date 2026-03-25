from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Literal, Optional, List

from app.db.database import get_db
from app.db.models import LOR, HackathonCert, StudentProfile
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/extras", tags=["extras"])


# ─────────────────────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────────────────────

class LORCreate(BaseModel):
    source_type: Literal["industry", "academic_strong", "academic_standard"]
    institution: Optional[str] = None


class LOROut(LORCreate):
    id: str
    verified: bool

    class Config:
        from_attributes = True


class HackathonCertCreate(BaseModel):
    event_name: str
    prize_level: Literal["first", "second", "third", "participation"]


class HackathonCertOut(HackathonCertCreate):
    id: str
    verified: bool

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# LOR Routes
# ─────────────────────────────────────────────────────────────

@router.get("/lors", response_model=List[LOROut])
async def list_lors(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    profile = await db.get(StudentProfile, user.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = await db.execute(
        select(LOR).where(LOR.profile_id == profile.id)
    )
    return result.scalars().all()


@router.post("/lors", response_model=LOROut, status_code=201)
async def add_lor(
    body: LORCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    profile = await db.get(StudentProfile, user.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # limit to max 3 LORs
    existing = await db.execute(
        select(func.count()).where(LOR.profile_id == profile.id)
    )
    if existing.scalar() >= 3:
        raise HTTPException(status_code=400, detail="Maximum 3 LORs allowed")

    lor = LOR(
        **body.model_dump(),
        profile_id=profile.id
    )

    db.add(lor)
    await db.commit()
    await db.refresh(lor)

    return lor


@router.delete("/lors/{lor_id}", status_code=204)
async def delete_lor(
    lor_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    lor = await db.get(LOR, lor_id)
    if not lor:
        raise HTTPException(status_code=404, detail="LOR not found")

    if lor.profile_id != user.profile_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    await db.delete(lor)
    await db.commit()


# ─────────────────────────────────────────────────────────────
# Hackathon Certificate Routes
# ─────────────────────────────────────────────────────────────

@router.get("/hackathon-certs", response_model=List[HackathonCertOut])
async def list_certs(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    profile = await db.get(StudentProfile, user.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = await db.execute(
        select(HackathonCert).where(HackathonCert.profile_id == profile.id)
    )
    return result.scalars().all()


@router.post("/hackathon-certs", response_model=HackathonCertOut, status_code=201)
async def add_cert(
    body: HackathonCertCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    profile = await db.get(StudentProfile, user.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    cert = HackathonCert(
        **body.model_dump(),
        profile_id=profile.id
    )

    db.add(cert)
    await db.commit()
    await db.refresh(cert)

    return cert


@router.delete("/hackathon-certs/{cert_id}", status_code=204)
async def delete_cert(
    cert_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    cert = await db.get(HackathonCert, cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    if cert.profile_id != user.profile_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    await db.delete(cert)
    await db.commit()