import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.routers import auth, organizations, admin, chat, integrations, contacts

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("khidmati")

app = FastAPI(title="KhidmatAI", version="0.1.0")

# CORS middleware (allow all for now, adjust in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for HTTPException to return consistent JSON
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException: {exc.detail} (status {exc.status_code})")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# Simple health check endpoints
@app.get("/health", tags=["monitoring"])
async def health_check():
    return {"status": "ok"}

@app.get("/ready", tags=["monitoring"])
async def readiness_check():
    # Could add DB ping here
    return {"ready": True}

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"]) 
app.include_router(organizations.router, prefix="/api/organizations", tags=["organizations"]) 
app.include_router(admin.router, prefix="/api/admin", tags=["admin"]) 
app.include_router(chat.router, prefix="/api/chat", tags=["chat"]) 
app.include_router(integrations.router, prefix="/api/integrations", tags=["integrations"])
app.include_router(contacts.router, prefix="/api", tags=["contacts"]) 

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
