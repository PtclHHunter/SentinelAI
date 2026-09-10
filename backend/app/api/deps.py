from fastapi import Depends, HTTPException

from app.core.database import get_db, SessionLocal
from app.core.config import settings
from app.services.analysis_engine import RuleBasedAnalysisEngine


def get_analysis_engine() -> RuleBasedAnalysisEngine:
    """Get analysis engine instance."""
    return RuleBasedAnalysisEngine()


def get_settings() -> dict:
    """Get detection settings as dictionary."""
    return {
        "failed_login_threshold": settings.failed_login_threshold,
        "failed_login_window_minutes": settings.failed_login_window_minutes,
        "brute_force_threshold": settings.brute_force_threshold,
        "brute_force_window_minutes": settings.brute_force_window_minutes,
        "multi_account_threshold": settings.multi_account_threshold,
        "multi_account_window_minutes": settings.multi_account_window_minutes,
        "business_hours_start": settings.business_hours_start,
        "business_hours_end": settings.business_hours_end,
    }


def validate_file_upload(file: "UploadFile") -> "UploadFile":
    """Validate uploaded file."""
    from app.core.security import (
        validate_file_extension, validate_file_size, validate_file_signature, sanitize_filename
    )
    
    validate_file_extension(file.filename)
    validate_file_size(file)
    validate_file_signature(file, file.filename)
    
    # Sanitize filename
    file.filename = sanitize_filename(file.filename)
    
    return file


class PaginationParams:
    """Pagination parameters."""
    def __init__(
        self,
        page: int = 1,
        page_size: int = 20
    ):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), settings.max_page_size)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size


def get_pagination(page: int = 1, page_size: int = 20) -> PaginationParams:
    """FastAPI dependency for pagination."""
    return PaginationParams(page, page_size)