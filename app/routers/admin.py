from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from uuid import UUID

from app import models, database, auth

router = APIRouter()

# Dependency to ensure admin role
async def admin_required(current_user: models.Profile = Depends(auth.get_current_user)):
    if current_user.role != models.RoleEnum.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user

# Dashboard analytics
@router.get("/dashboard", summary="Admin dashboard analytics")
async def get_dashboard(admin: models.Profile = Depends(admin_required), db: AsyncSession = Depends(database.get_db)):
    total_users = (await db.execute(select(func.count(models.Profile.id)))).scalar_one()
    total_ngos = (await db.execute(select(func.count(models.Organization.id)).where(models.Organization.type == models.OrgTypeEnum.NGO))).scalar_one()
    total_universities = (await db.execute(select(func.count(models.Organization.id)).where(models.Organization.type == models.OrgTypeEnum.University))).scalar_one()
    total_hospitals = (await db.execute(select(func.count(models.Organization.id)).where(models.Organization.type == models.OrgTypeEnum.Hospital))).scalar_one()
    total_pro_accounts = (await db.execute(select(func.count(models.Organization.id)).where(models.Organization.subscription_tier == models.SubscriptionTierEnum.pro))).scalar_one()
    return {
        "total_users": total_users,
        "total_ngos": total_ngos,
        "total_universities": total_universities,
        "total_hospitals": total_hospitals,
        "total_pro_accounts": total_pro_accounts,
    }

# Block/unblock profile
@router.patch("/profiles/{profile_id}/block", summary="Block a profile")
async def block_profile(profile_id: UUID, admin: models.Profile = Depends(admin_required), db: AsyncSession = Depends(database.get_db)):
    stmt = update(models.Profile).where(models.Profile.id == profile_id).values(status=models.StatusEnum.blocked)
    await db.execute(stmt)
    await db.commit()
    return {"msg": "Profile blocked"}

@router.patch("/profiles/{profile_id}/unblock", summary="Unblock a profile")
async def unblock_profile(profile_id: UUID, admin: models.Profile = Depends(admin_required), db: AsyncSession = Depends(database.get_db)):
    stmt = update(models.Profile).where(models.Profile.id == profile_id).values(status=models.StatusEnum.active)
    await db.execute(stmt)
    await db.commit()
    return {"msg": "Profile unblocked"}

# Approve organization (set is_verified true)
@router.patch("/organizations/{org_id}/approve", summary="Approve organization")
async def approve_org(org_id: UUID, admin: models.Profile = Depends(admin_required), db: AsyncSession = Depends(database.get_db)):
    stmt = update(models.Organization).where(models.Organization.id == org_id).values(is_verified=True)
    await db.execute(stmt)
    await db.commit()
    return {"msg": "Organization approved"}

# List organizations with pagination (optional)
@router.get("/organizations", summary="List organizations")
async def list_organizations(skip: int = 0, limit: int = 100, admin: models.Profile = Depends(admin_required), db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Organization).offset(skip).limit(limit))
    orgs = result.scalars().all()
    return orgs
