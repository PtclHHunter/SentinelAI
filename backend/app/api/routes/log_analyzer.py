import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import validate_file_extension, validate_file_size, validate_file_signature, sanitize_filename
from app.services.log_parser import LogParser
from app.services.ioc_extractor import IOCExtractor
from app.services.analysis_engine import RuleBasedAnalysisEngine
from app.models import Event, Alert
from app.schemas import (
    UploadResponse, ParseResult, EventResponse, AlertResponse, SampleLogFile,
    SeverityLevel, AlertStatus, EventType
)

router = APIRouter(prefix="/logs", tags=["log-analyzer"])

# In-memory job storage (in production, use Redis or database)
parse_jobs: dict = {}


@router.post("/upload", response_model=UploadResponse)
async def upload_log_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and parse a log file."""
    # Validate
    validate_file_extension(file.filename)
    validate_file_size(file)
    validate_file_signature(file, file.filename)
    
    # Sanitize filename
    safe_filename = sanitize_filename(file.filename)
    
    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    
    # Save file temporarily
    upload_dir = settings.get_abs_database_path().parent / "uploads"
    upload_dir.mkdir(exist_ok=True)
    file_path = upload_dir / f"{job_id}_{safe_filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create job record
    parse_jobs[job_id] = {
        "job_id": job_id,
        "filename": safe_filename,
        "file_path": str(file_path),
        "status": "processing",
        "created_at": datetime.utcnow(),
        "result": None
    }
    
    # Process in background
    background_tasks.add_task(process_log_file, job_id, str(file_path), db)
    
    return UploadResponse(
        job_id=job_id,
        filename=safe_filename,
        status="processing",
        message="File uploaded successfully. Processing started."
    )


def process_log_file(job_id: str, file_path: str, db: Session):
    """Background task to parse log file and generate alerts."""
    from app.core.database import SessionLocal
    bg_db = SessionLocal()
    try:
        parser = LogParser()
        result = parser.parse_file(Path(file_path))
        
        saved_events = []
        for event_data in result.events:
            event = Event(
                source_file=event_data.source_file,
                source_line=event_data.source_line,
                timestamp=event_data.timestamp,
                event_type=event_data.event_type.value,
                severity=event_data.severity.value,
                raw_data=event_data.raw_data,
                normalized_data=event_data.normalized_data,
                message=event_data.message
            )
            bg_db.add(event)
            saved_events.append(event)
        
        bg_db.commit()
        
        for event in saved_events:
            bg_db.refresh(event)
        
        events_with_ids = []
        for i, event_data in enumerate(result.events):
            if i < len(saved_events):
                event_data.id = saved_events[i].id
            events_with_ids.append(event_data)
        
        ioc_extractor = IOCExtractor()
        all_text = " ".join([
            f"{e.message or ''} {e.raw_data or ''} {e.normalized_data or ''}"
            for e in events_with_ids
        ])
        extracted_iocs = ioc_extractor.extract_all(all_text)
        
        engine = RuleBasedAnalysisEngine(bg_db)
        detection_settings = {
            "failed_login_threshold": 5,
            "failed_login_window_minutes": 15,
            "brute_force_threshold": 10,
            "brute_force_window_minutes": 5,
            "multi_account_threshold": 5,
            "multi_account_window_minutes": 10,
            "business_hours_start": 8,
            "business_hours_end": 18,
        }
        
        from app.schemas import IOCMatch, IOCType
        from app.models import IOC as IOCModel
        
        ioc_matches = []
        for ioc_type, ioc_list in extracted_iocs.items():
            for ioc in ioc_list:
                db_ioc = bg_db.query(IOCModel).filter(
                    IOCModel.ioc_type == ioc_type.value,
                    IOCModel.value == ioc.value,
                    IOCModel.is_active == True
                ).first()
                
                if db_ioc:
                    from app.schemas import IOCRecord
                    matched = IOCRecord(
                        id=db_ioc.id,
                        ioc_type=ioc_type,
                        value=db_ioc.value,
                        description=db_ioc.description,
                        source=db_ioc.source,
                        tags=db_ioc.tags,
                        is_active=db_ioc.is_active
                    )
                    ioc_matches.append(IOCMatch(
                        ioc_type=ioc_type,
                        value=ioc.value,
                        matched_ioc=matched,
                        context=ioc.context
                    ))
        
        alerts = engine.analyze_events(events_with_ids, ioc_matches, detection_settings)
        
        saved_alerts = []
        for alert_data in alerts:
            ev_id = alert_data.event_id
            if ev_id is None and alert_data.source_event_id:
                try:
                    ev_id = int(alert_data.source_event_id)
                except (ValueError, TypeError):
                    ev_id = None
            alert = Alert(
                event_id=ev_id,
                rule_id=alert_data.rule_id,
                title=alert_data.title,
                severity=alert_data.severity.value,
                confidence=alert_data.confidence,
                evidence=alert_data.evidence,
                source_file=alert_data.source_file,
                source_event_id=alert_data.source_event_id,
                timestamp=alert_data.timestamp,
                recommendation=alert_data.recommendation,
                status=alert_data.status.value,
                meta_data=alert_data.meta_data
            )
            bg_db.add(alert)
            saved_alerts.append(alert)
        
        bg_db.commit()
        
        for alert in saved_alerts:
            bg_db.refresh(alert)
        
        alerts_with_ids = []
        for i, alert_data in enumerate(alerts):
            if i < len(saved_alerts):
                alert_data.id = saved_alerts[i].id
            alerts_with_ids.append(alert_data)
        
        parse_jobs[job_id].update({
            "status": "completed",
            "result": ParseResult(
                job_id=job_id,
                filename=parse_jobs[job_id]["filename"],
                total_lines=result.total_lines,
                parsed_events=len(events_with_ids),
                alerts_generated=len(alerts_with_ids),
                parse_errors=len(result.errors),
                events=events_with_ids,
                alerts=alerts_with_ids
            )
        })
        
    except Exception as e:
        parse_jobs[job_id].update({
            "status": "failed",
            "error": str(e)
        })
    finally:
        bg_db.close()
        try:
            p = Path(file_path)
            if p.parent.name == "uploads":
                p.unlink(missing_ok=True)
        except:
            pass


@router.get("/parse-result/{job_id}", response_model=ParseResult)
def get_parse_result(job_id: str):
    """Get parse job result."""
    job = parse_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] == "processing":
        raise HTTPException(status_code=202, detail="Job still processing")
    
    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=job.get("error", "Processing failed"))
    
    return job["result"]


@router.get("/sample", response_model=List[SampleLogFile])
def list_sample_logs():
    """List available sample log files."""
    sample_dir = settings.get_abs_database_path().parent / "sample_logs"
    if not sample_dir.exists():
        return []
    
    files = []
    for f in sample_dir.glob("*"):
        if f.is_file() and f.suffix.lower() in {".log", ".txt", ".json", ".csv"}:
            stat = f.stat()
            files.append(SampleLogFile(
                filename=f.name,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime),
                description=get_sample_description(f.name)
            ))
    
    return files


@router.post("/parse-sample/{filename}", response_model=UploadResponse)
async def parse_sample_log(
    filename: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Parse a sample log file."""
    sample_dir = settings.get_abs_database_path().parent / "sample_logs"
    file_path = sample_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Sample file not found")
    
    # Validate extension
    validate_file_extension(filename)
    
    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    
    # Create job record
    parse_jobs[job_id] = {
        "job_id": job_id,
        "filename": filename,
        "file_path": str(file_path),
        "status": "processing",
        "created_at": datetime.utcnow(),
        "result": None
    }
    
    # Process in background
    background_tasks.add_task(process_log_file, job_id, str(file_path), db)
    
    return UploadResponse(
        job_id=job_id,
        filename=filename,
        status="processing",
        message="Sample file processing started."
    )


@router.delete("/results/{job_id}")
def clear_job_results(job_id: str, db: Session = Depends(get_db)):
    """Clear a specific job's results from memory and database."""
    job = parse_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    filename = job.get("filename", "")

    # Delete associated events from DB
    deleted_events = db.query(Event).filter(Event.source_file == filename).delete(synchronize_session=False)
    # Delete associated alerts from DB
    deleted_alerts = db.query(Alert).filter(Alert.source_file == filename).delete(synchronize_session=False)
    db.commit()

    # Remove from in-memory dict
    del parse_jobs[job_id]

    return {"message": "Job cleared", "deleted_events": deleted_events, "deleted_alerts": deleted_alerts}


@router.delete("/results")
def clear_all_results(db: Session = Depends(get_db)):
    """Clear all parse job results from memory and database."""
    job_count = len(parse_jobs)
    deleted_events = db.query(Event).delete(synchronize_session=False)
    deleted_alerts = db.query(Alert).delete(synchronize_session=False)
    db.commit()

    parse_jobs.clear()

    return {"message": "All results cleared", "deleted_jobs": job_count, "deleted_events": deleted_events, "deleted_alerts": deleted_alerts}


def get_sample_description(filename: str) -> str:
    """Get description for sample file."""
    descriptions = {
        "auth_sample.log": "SSH authentication logs with failed/successful logins",
        "syslog_sample.log": "System logs with various events",
        "web_sample.log": "Web server access logs with suspicious requests",
    }
    return descriptions.get(filename, "Sample log file")