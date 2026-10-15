
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, validator
from uuid import UUID
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete

from app import models, database, auth

router = APIRouter()

# Dependency to ensure branch belongs to organization owned by current user
async def branch_admin_required(branch_id: UUID, current_user: models.Profile = Depends(auth.get_current_user), db: AsyncSession = Depends(database.get_db)):
    # Find branch and its organization
    result = await db.execute(select(models.Branch).where(models.Branch.id == branch_id))
    branch = result.scalar_one_or_none()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    # Super admin can manage any branch
    if current_user.role == models.RoleEnum.admin:
        return branch
    # Otherwise ensure the branch belongs to an org owned by the user
    org_result = await db.execute(select(models.Organization).where(models.Organization.id == branch.org_id, models.Organization.user_id == current_user.id))
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this branch")
    return branch

class ContactCreate(BaseModel):
    type: models.ContactTypeEnum
    value: str
    label: str | None = None
    is_primary: bool = False
    is_public: bool = True

    @validator('value')
    def validate_value(cls, v, values):
        # Basic validation: if email, ensure @ present; if phone, ensure digits
        contact_type = values.get('type')
        if contact_type == models.ContactTypeEnum.email and '@' not in v:
            raise ValueError('Invalid email address')
        if contact_type in (models.ContactTypeEnum.phone, models.ContactTypeEnum.whatsapp):
            # Very simple numeric check; real implementation would use phonenumbers lib
            digits = ''.join(filter(str.isdigit, v))
            if len(digits) < 7:
                raise ValueError('Invalid phone number')
        return v

@router.post("/branches/{branch_id}/contacts", response_model=dict)
async def create_contact(branch_id: UUID, contact: ContactCreate, current_user: models.Profile = Depends(auth.get_current_user), db: AsyncSession = Depends(database.get_db)):
    branch = await branch_admin_required(branch_id, current_user, db)
    # Enforce only one primary per type per branch
    if contact.is_primary:
        stmt = select(models.Contact).where(models.Contact.branch_id == branch_id, models.Contact.type == contact.type, models.Contact.is_primary == True)
        existing = await db.execute(stmt)
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Primary contact for this type already exists")
    new_contact = models.Contact(
        branch_id=branch_id,
        type=contact.type,
        value=contact.value,
        label=contact.label,
        is_primary=contact.is_primary,
    )
    db.add(new_contact)
    await db.commit()
    await db.refresh(new_contact)
    return {"id": str(new_contact.id)}

@router.get("/branches/{branch_id}/contacts", response_model=List[dict])
async def list_contacts(branch_id: UUID, db: AsyncSession = Depends(database.get_db)):
    # No auth needed for public listing, but we filter public contacts only
    result = await db.execute(select(models.Contact).where(models.Contact.branch_id == branch_id, models.Contact.is_public == True))
    contacts = result.scalars().all()
    return [{
        "id": str(c.id),
        "type": c.type.value,
        "value": c.value,
        "label": c.label,
        "is_primary": c.is_primary,
    } for c in contacts]

@router.patch("/contacts/{contact_id}", response_model=dict)
async def update_contact(contact_id: UUID, contact: ContactCreate, current_user: models.Profile = Depends(auth.get_current_user), db: AsyncSession = Depends(database.get_db)):
    # Find contact and verify ownership via branch_admin_required
    result = await db.execute(select(models.Contact).where(models.Contact.id == contact_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")
    # Verify branch ownership
    await branch_admin_required(existing.branch_id, current_user, db)
    # Enforce primary rule
    if contact.is_primary:
        stmt = select(models.Contact).where(models.Contact.branch_id == existing.branch_id, models.Contact.type == contact.type, models.Contact.is_primary == True, models.Contact.id != contact_id)
        other = await db.execute(stmt)
        if other.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Another primary contact of this type exists")
    stmt = (
        update(models.Contact)
        .where(models.Contact.id == contact_id)
        .values(
            type=contact.type,
            value=contact.value,
            label=contact.label,
            is_primary=contact.is_primary,
        )
    )
    await db.execute(stmt)
    await db.commit()
    return {"msg": "Contact updated"}

@router.delete("/contacts/{contact_id}", response_model=dict)
async def delete_contact(contact_id: UUID, current_user: models.Profile = Depends(auth.get_current_user), db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Contact).where(models.Contact.id == contact_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")
    await branch_admin_required(existing.branch_id, current_user, db)
    stmt = delete(models.Contact).where(models.Contact.id == contact_id)
    await db.execute(stmt)
    await db.commit()
    return {"msg": "Contact deleted"}
