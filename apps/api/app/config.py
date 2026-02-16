from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "BorsaTakip API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "borsatakip"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # App
    API_PORT: int = 8000
    TIMEZONE: str = "Europe/Istanbul"
    LOG_LEVEL: str = "INFO"
    
    # Finance Defaults
    DEFAULT_FEE_BPS: int = 10
    DEFAULT_SLIPPAGE_BPS: int = 8
    MIN_LIQUIDITY_TURNOVER: float = 10_000_000.0

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()
