from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./timesaving.db"
    secret_key: str = "change-me-to-a-long-random-string-in-production"
    session_max_age: int = 86400
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:8001"
    init_admin_username: str = "admin"
    init_admin_password: str = "admin1234"
    algorithm_timeout_seconds: int = 120

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
