import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from sqlalchemy import URL
from dotenv import load_dotenv

# Root directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "SmartServe GIS API"
    PROJECT_DESCRIPTION: str = "High-Performance Geospatial REST API for Location-Based Multi-Service WebGIS Portal in Pune and PCMC"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database Configuration
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_NAME: str = Field(default="smartserve_db")
    DB_USER: str = Field(default="postgres")
    DB_PASSWORD: str = Field(default="postgres")
    
    # CORS Origins (allow local dev & standard ports)
    CORS_ORIGINS: list[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5500",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
        "*"
    ]
    
    @property
    def database_url(self) -> URL:
        """Construct a safe SQLAlchemy connection URL with properly escaped special characters."""
        return URL.create(
            drivername="postgresql",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )

settings = Settings()
