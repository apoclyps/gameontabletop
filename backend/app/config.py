from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/app"
    cors_origins: str = "http://localhost:5173"

    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    verification_token_expire_hours: int = 24
    password_reset_expire_hours: int = 2

    sendgrid_api_key: str = ""
    sendgrid_from_email: str = ""
    sendgrid_from_name: str = "Game On Tabletop"
    frontend_url: str = "http://localhost:5173"

    supabase_url: str = ""
    supabase_anon_key: str = ""

    bgg_application_token: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def get_cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
