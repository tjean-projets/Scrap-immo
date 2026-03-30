from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./scrap_immo.db"
    scrape_postal_codes: list[str] = ["75001"]
    scrape_hours: list[int] = [8, 13, 19]
    scrape_enabled_sites: list[str] = ["pap"]
    rgpd_retention_days: int = 30
    jwt_secret: str = "change-me-in-production-scrap-immo-2024"
    jwt_expiration_days: int = 7
    admin_email: str = "admin@scrapimmo.fr"
    admin_password: str = "admin123"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
