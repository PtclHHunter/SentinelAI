from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.database import get_db
from app.api.deps import get_pagination
from app.services.report_generator import ReportGenerator
from app.models import Investigation, Alert, Report as ReportModel
from app.schemas import (
    ReportGenerateRequest, ReportResponse, ReportFormat, PaginatedResponse
)
from app.core.config import settings

router = APIRouter(prefix="/reports", tags=["reports"])

# Initialize report generator
reports_dir = settings.get_abs_database_path().parent / "reports"
report_generator = ReportGenerator(reports_dir)


@router.post("/generate", response_model=ReportResponse)
def generate_report(
    request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate report for investigation or alert."""
    investigation = None
    alert = None
    
    if request.investigation_id:
        investigation = db.query(Investigation).filter(
            Investigation.id == request.investigation_id
        ).first()
        if not investigation:
            raise HTTPException(status_code=404, detail="Investigation not found")
    
    if request.alert_id:
        alert = db.query(Alert).filter(Alert.id == request.alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
    
    if not investigation and not alert:
        raise HTTPException(status_code=400, detail="Either investigation_id or alert_id required")
    
    # Generate report
    report = report_generator.generate(
        investigation=investigation,
        alert=alert,
        format=request.format,
        title=request.title,
        generated_by="analyst"  # TODO: get from auth
    )
    
    # Save to database
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return ReportResponse(
        id=report.id,
        investigation_id=report.investigation_id,
        alert_id=report.alert_id,
        title=report.title,
        format=ReportFormat(report.format),
        file_path=report.file_path,
        file_size=report.file_size,
        generated_by=report.generated_by,
        created_at=report.created_at
    )


@router.get("", response_model=PaginatedResponse)
def list_reports(
    investigation_id: int = Query(None),
    format: ReportFormat = Query(None),
    pagination=Depends(get_pagination),
    db: Session = Depends(get_db)
):
    """List generated reports."""
    query = db.query(ReportModel)
    
    if investigation_id:
        query = query.filter(ReportModel.investigation_id == investigation_id)
    if format:
        query = query.filter(ReportModel.format == format.value)
    
    total = query.count()
    reports = query.order_by(desc(ReportModel.created_at)).offset(pagination.offset).limit(pagination.limit).all()
    
    items = [
        ReportResponse(
            id=r.id,
            investigation_id=r.investigation_id,
            alert_id=r.alert_id,
            title=r.title,
            format=ReportFormat(r.format),
            file_path=r.file_path,
            file_size=r.file_size,
            generated_by=r.generated_by,
            created_at=r.created_at
        )
        for r in reports
    ]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size
    )


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    """Download generated report file."""
    report = db.query(ReportModel).filter(ReportModel.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    file_path = Path(report.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    
    media_type = {
        "pdf": "application/pdf",
        "json": "application/json",
        "csv": "text/csv"
    }.get(report.format, "application/octet-stream")
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name
    )


@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    """Delete report record and file."""
    report = db.query(ReportModel).filter(ReportModel.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Delete file
    try:
        Path(report.file_path).unlink(missing_ok=True)
    except:
        pass
    
    db.delete(report)
    db.commit()
    
    return {"message": "Report deleted successfully"}