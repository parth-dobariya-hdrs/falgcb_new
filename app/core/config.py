# ================================
# FILE: app/core/config.py
# ================================

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # API Settings
    PROJECT_NAME: str = "FastAPI LangGraph Chatbot"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database Settings
    PSQL_USERNAME: str = os.getenv("PSQL_USERNAME", "postgres")
    PSQL_PASSWORD: str = os.getenv("PSQL_PASSWORD", "")
    PSQL_HOST: str = os.getenv("PSQL_HOST", "localhost")
    PSQL_PORT: str = os.getenv("PSQL_PORT", "5432")
    PSQL_DATABASE: str = os.getenv("PSQL_DATABASE", "chatbot_db")
    PSQL_SSLMODE: str = os.getenv("PSQL_SSLMODE", "prefer")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.PSQL_USERNAME}:{self.PSQL_PASSWORD}"
            f"@{self.PSQL_HOST}:{self.PSQL_PORT}/{self.PSQL_DATABASE}"
        )

    # AI API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Clerk Authentication Settings
    CLERK_INSTANCE_URL: str = os.getenv("CLERK_INSTANCE_URL", "")
    CLERK_JWT_VERIFICATION_KEY: str = os.getenv("CLERK_JWT_VERIFICATION_KEY", "")

    class Config:
        case_sensitive = True


settings = Settings()
