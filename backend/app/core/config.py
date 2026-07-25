from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    CORS_ORIGINS: list[str] = []  # Optional for later Frontend Connection

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if self.DATABASE_URL:
            return self

        if not all([self.POSTGRES_USER, self.POSTGRES_PASSWORD, self.POSTGRES_DB]):
            raise ValueError(
                "Set DATABASE_URL or all of POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB."
            )

        self.DATABASE_URL = (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        return self

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


settings = Settings()
