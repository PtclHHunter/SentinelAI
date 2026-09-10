from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "SentinelAI"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Database - absolute path to project root
    database_path: Path = Field(
        default=Path("data/sentinel.db"),
        description="Path to SQLite database"
    )
    
    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent
    
    def get_abs_database_path(self) -> Path:
        if self.database_path.is_absolute():
            return self.database_path
        return self.project_root / self.database_path
    
    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    
    # File upload
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: set[str] = Field(
        default={".log", ".txt", ".json", ".csv"},
        description="Allowed file extensions for upload"
    )
    
    # Detection thresholds
    brute_force_threshold: int = 10
    brute_force_window_minutes: int = 5
    failed_login_threshold: int = 5
    failed_login_window_minutes: int = 15
    multi_account_threshold: int = 5
    multi_account_window_minutes: int = 10
    
    # Business hours (for anomalous time detection)
    business_hours_start: int = 8  # 8 AM
    business_hours_end: int = 18   # 6 PM
    
    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()