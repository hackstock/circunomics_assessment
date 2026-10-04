from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+pysqlite:///:memory:"
    github_token: str = ""
    github_api_base: str = "https://api.github.com"
    commit_import_limit: int = 1000
    log_level: str = "INFO"


settings = Settings()
