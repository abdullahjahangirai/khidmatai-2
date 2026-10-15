from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def integrations_home():
    return {"message": "Integrations router is active"}