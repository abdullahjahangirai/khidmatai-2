from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app import models, database, auth

router = APIRouter()

class SearchRequest(BaseModel):
    query: str

@router.post("/search", response_model=dict)
async def search(request: SearchRequest, db: AsyncSession = Depends(database.get_db), current_user: models.Profile = Depends(auth.get_current_user)):
    # Simple RAG‑style search over services and branches using ILIKE
    svc_stmt = select(models.ServiceCourse).where(
        or_(
            models.ServiceCourse.title.ilike(f"%{request.query}%"),
            models.ServiceCourse.description.ilike(f"%{request.query}%"),
            models.ServiceCourse.category.ilike(f"%{request.query}%"),
        )
    )
    svc_res = await db.execute(svc_stmt)
    services = svc_res.scalars().all()

    br_stmt = select(models.Branch).where(
        or_(
            models.Branch.city.ilike(f"%{request.query}%"),
            models.Branch.address.ilike(f"%{request.query}%"),
        )
    )
    br_res = await db.execute(br_stmt)
    branches = br_res.scalars().all()

    services_out = [
        {
            "id": str(s.id),
            "title": s.title,
            "category": s.category.value,
            "description": s.description,
            "deadline": s.deadline.isoformat() if s.deadline else None,
            "eligibility": s.eligibility,
            "cost": s.cost,
        }
        for s in services
    ]
    branches_out = [
        {
            "id": str(b.id),
            "city": b.city,
            "address": b.address,
            "phone": b.phone,
            "latitude": b.latitude,
            "longitude": b.longitude,
        }
        for b in branches
    ]
    return {"services": services_out, "branches": branches_out}

@router.get("/", summary="Chat router health")
async def chat_home():
    return {"message": "Chat router is active"}