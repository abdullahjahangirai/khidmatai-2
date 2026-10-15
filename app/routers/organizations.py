from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
from typing import List
from uuid import UUID

from app import models, database, auth

router = APIRouter()

# Dependency to ensure organization admin (owner) or super admin
async def org_admin_required(org_id: UUID, current_user: models.Profile = Depends(auth.get_current_user), db: AsyncSession = Depends(database.get_db)):
    # Super admin can manage any org
    if current_user.role == models.RoleEnum.admin:
        return current_user
    # Otherwise check ownership
    result = await db.execute(select(models.Organization).where(models.Organization.id == org_id, models.Organization.user_id == current_user.id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this organization")
    return current_user

# ----- Organization CRUD -----
class OrgCreate(BaseModel):
    name: str
    type: models.OrgTypeEnum
    google_business_id: str | None = None
    subscription_tier: models.SubscriptionTierEnum = models.SubscriptionTierEnum.free

@router.post("/", response_model=dict)
async def create_organization(org: OrgCreate, current_user: models.Profile = Depends(auth.get_current_user), db: AsyncSession = Depends(database.get_db)):
    new_org = models.Organization(
        user_id=current_user.id,
        name=org.name,
        type=org.type,
        google_business_id=org.google_business_id,
        subscription_tier=org.subscription_tier,
    )
    db.add(new_org)
    await db.commit()
    await db.refresh(new_org)
    return {"id": str(new_org.id)}

@router.get("/{org_id}", response_model=dict)
async def get_organization(org_id: UUID, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Organization).where(models.Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {
        "id": str(org.id),
        "name": org.name,
        "type": org.type.value,
        "subscription_tier": org.subscription_tier.value,
        "is_verified": org.is_verified,
        "status": org.status.value,
    }

@router.patch("/{org_id}", response_model=dict)
async def update_organization(org_id: UUID, org: OrgCreate, current_user: models.Profile = Depends(auth.get_current_user), db: AsyncSession = Depends(database.get_db)):
    await org_admin_required(org_id, current_user, db)
    stmt = (
        update(models.Organization)
        .where(models.Organization.id == org_id)
        .values(
            name=org.name,
            type=org.type,
            google_business_id=org.google_business_id,
            subscription_tier=org.subscription_tier,
        )
    )
    await db.execute(stmt)
    await db.commit()
    return {"msg": "Organization updated"}

@router.delete("/{org_id}", response_model=dict)
async def delete_organization(org_id: UUID, current_user: models.Profile = Depends(auth.get_current_user), db: AsyncSession = Depends(database.get_db)):
    await org_admin_required(org_id, current_user, db)
    stmt = delete(models.Organization).where(models.Organization.id == org_id)
    await db.execute(stmt)
    await db.commit()
    return {"msg": "Organization deleted"}

# ----- Branch CRUD -----
class BranchCreate(BaseModel):
    name: str
    type: str | None = None
    country: str | None = None
    province: str | None = None
    city: str
    area: str | None = None
    address: str
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    is_primary: bool = False
    is_active: bool = True
    is_public: bool = True
    google_place_id: str | None = None
    google_business_location_id: str | None = None

@router.post("/{org_id}/branches", response_model=dict)
async def create_branch(org_id: UUID, branch: BranchCreate, current_user: models.Profile = Depends(auth.get_current_user), db: AsyncSession = Depends(database.get_db)):
    await org_admin_required(org_id, current_user, db)
    new_branch = models.Branch(
        org_id=org_id,
        name=branch.name,
        type=branch.type,
        country=branch.country,
        province=branch.province,
        city=branch.city,
        area=branch.area,
        address=branch.address,
        postal_code=branch.postal_code,
        latitude=branch.latitude,
        longitude=branch.longitude,
        description=branch.description,
        is_primary=branch.is_primary,
        is_active=branch.is_active,
        is_public=branch.is_public,
        google_place_id=branch.google_place_id,
        google_business_location_id=branch.google_business_location_id,
    )
    db.add(new_branch)
    await db.commit()
    await db.refresh(new_branch)
    return {"id": str(new_branch.id)}

@router.get("/{org_id}/branches", response_model=List[dict])
async def list_branches(org_id: UUID, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Branch).where(models.Branch.org_id == org_id))
    branches = result.scalars().all()
    return [{
        "id": str(b.id),
        "city": b.city,
        "address": b.address,
        "phone": b.phone,
        "latitude": b.latitude,
        "longitude": b.longitude,
    } for b in branches]

# ----- Service/Course CRUD -----
class ServiceCreate(BaseModel):
    title: str
    category: models.ServiceCategoryEnum
    description: str | None = None
    deadline: str | None = None  # ISO format string
    eligibility: str | None = None
    cost: float | None = None

@router.post("/{org_id}/services", response_model=dict)
async def create_service(org_id: UUID, svc: ServiceCreate, current_user: models.Profile = Depends(auth.get_current_user), db: AsyncSession = Depends(database.get_db)):
    await org_admin_required(org_id, current_user, db)
    new_svc = models.ServiceCourse(
        org_id=org_id,
        title=svc.title,
        category=svc.category,
        description=svc.description,
        deadline=svc.deadline,
        eligibility=svc.eligibility,
        cost=svc.cost,
    )
    db.add(new_svc)
    await db.commit()
    await db.refresh(new_svc)
    return {"id": str(new_svc.id)}

@router.get("/{org_id}/services", response_model=List[dict])
async def list_services(org_id: UUID, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.ServiceCourse).where(models.ServiceCourse.org_id == org_id))
    services = result.scalars().all()
    return [{
        "id": str(s.id),
        "title": s.title,
        "category": s.category.value,
        "description": s.description,
        "deadline": s.deadline.isoformat() if s.deadline else None,
        "eligibility": s.eligibility,
        "cost": s.cost,
    } for s in services]
