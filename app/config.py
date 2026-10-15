import os
from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn

class Settings(BaseSettings):
    # General
    PROJECT_NAME: str = "KhidmatAI"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./khidmatai.db"
    
    # JWT
    SECRET_KEY: str = "super-secret-jwt-key-goes-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Supabase
    SUPABASE_URL: str = "https://your-supabase-project.supabase.co"
    SUPABASE_KEY: str = "your-supabase-anon-key"

    class Config:
        case_sensitive = True

settings = Settings()