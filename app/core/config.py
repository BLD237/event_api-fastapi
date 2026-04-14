from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "event_api"
    app_env: str = "development"
    app_debug: bool = False

    mongodb_uri: str = ""
    mongodb_db: str = "event_api"

    jwt_secret_key: str = "placeholder_key_change_me_in_production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    otp_length: int = 6
    otp_expire_minutes: int = 10

    # Used only to decide whether we include otp_code in API responses.
    # For production you should not expose otp_code.
    otp_expose_in_response_when_debug: bool = True

    storage_upload_max_mb: int = 15
    storage_upload_max_bytes: int = 15 * 1024 * 1024

    # Email Settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    mail_from: str | None = None
    mail_from_name: str = "Event Application"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
