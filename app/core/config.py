import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise Operations Management System"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "supersecretjwtkeythatislongandsecureforenterprisemanagement"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root123"
    MYSQL_DB: str = "eoms_db"
    DATABASE_URL: str | None = None

    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    EXTERNAL_API_URL: str = "https://jsonplaceholder.typicode.com/posts/1"
    UPLOAD_DIR: str = "./uploads"
    EXPORT_DIR: str = "./exports"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"


settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.EXPORT_DIR, exist_ok=True)
