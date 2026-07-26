from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://scan:scan@localhost:5432/scan_legacy"
    JWT_SECRET: str = "changeme-generate-a-real-256-bit-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PUBCHEM_BASE_URL: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
