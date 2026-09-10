import uuid
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import validate_file_size, sanitize_filename
from app.services.hash_calculator import HashCalculator
from app.services.ioc_extractor import IOCExtractor
from app.models import IOC as IOCModel
from app.schemas import HashResult, HashHistoryItem, IOCMatch, IOCRecord, IOCType


class HashAnalyzeRequest(BaseModel):
    hash_value: str = Field(..., min_length=32, max_length=128)


class HashAnalyzeResponse(BaseModel):
    input_hash: str
    detected_type: str
    detected_algorithm: str
    ioc_matches: List[IOCMatch]
    in_database: bool
    scan_time_ms: float

router = APIRouter(prefix="/hash", tags=["hash-analyzer"])

# In-memory storage for hash analysis history
hash_history: list = []


@router.post("/analyze", response_model=HashResult)
async def analyze_file_hash(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload file and calculate hashes."""
    # Validate (allow any file for hash analysis)
    validate_file_size(file)
    safe_filename = sanitize_filename(file.filename)
    
    # Save file temporarily
    upload_dir = settings.get_abs_database_path().parent / "uploads"
    upload_dir.mkdir(exist_ok=True)
    file_id = str(uuid.uuid4())[:8]
    file_path = upload_dir / f"{file_id}_{safe_filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Calculate hashes
        calculator = HashCalculator()
        result = calculator.calculate_file_hashes(file_path)
        
        # Check against local IOC database
        ioc_matches = []
        for ioc_type in [IOCType.MD5, IOCType.SHA1, IOCType.SHA256, IOCType.SHA512]:
            hash_value = getattr(result, ioc_type.value)
            db_ioc = db.query(IOCModel).filter(
                IOCModel.ioc_type == ioc_type.value,
                IOCModel.value == hash_value,
                IOCModel.is_active == True
            ).first()
            
            if db_ioc:
                ioc_matches.append(IOCMatch(
                    ioc_type=ioc_type,
                    value=hash_value,
                    matched_ioc=type('obj', (object,), {
                        'id': db_ioc.id,
                        'value': db_ioc.value,
                        'description': db_ioc.description,
                        'ioc_type': ioc_type,
                        'source': db_ioc.source,
                        'tags': db_ioc.tags,
                        'is_active': db_ioc.is_active
                    })(),
                    context=f"File hash matches IOC in database"
                ))
        
        # Create response
        hash_result = HashResult(
            filename=result.filename,
            file_size=result.file_size,
            md5=result.md5,
            sha1=result.sha1,
            sha256=result.sha256,
            sha512=result.sha512,
            ioc_matches=ioc_matches,
            scan_time_ms=0  # Will be updated if we track time
        )
        
        # Add to history
        history_item = HashHistoryItem(
            id=len(hash_history) + 1,
            filename=result.filename,
            file_size=result.file_size,
            sha256=result.sha256,
            created_at=datetime.utcnow(),
            ioc_matches_count=len(ioc_matches)
        )
        hash_history.insert(0, history_item)
        # Keep only last 100
        if len(hash_history) > 100:
            hash_history.pop()
        
        return hash_result
        
    finally:
        # Clean up temp file
        try:
            file_path.unlink(missing_ok=True)
        except:
            pass


@router.get("/history", response_model=List[HashHistoryItem])
def get_hash_history(limit: int = 50):
    """Get hash analysis history."""
    return hash_history[:limit]


def _detect_hash_type(hash_val: str) -> Optional[IOCType]:
    """Detect hash type by length (hex chars only)."""
    h = hash_val.strip().lower()
    if not re.fullmatch(r'[0-9a-f]+', h):
        return None
    length = len(h)
    if length == 32:
        return IOCType.MD5
    elif length == 40:
        return IOCType.SHA1
    elif length == 64:
        return IOCType.SHA256
    elif length == 128:
        return IOCType.SHA512
    return None


@router.post("/analyze-hash", response_model=HashAnalyzeResponse)
def analyze_pasted_hash(request: HashAnalyzeRequest, db: Session = Depends(get_db)):
    """Analyze a pasted hash string against the local IOC database."""
    import time
    start = time.time()

    hash_val = request.hash_value.strip().lower()
    ioc_type = _detect_hash_type(hash_val)

    if ioc_type is None:
        raise HTTPException(status_code=400, detail="Unrecognized hash format. Must be a valid hex string of length 32 (MD5), 40 (SHA-1), 64 (SHA-256), or 128 (SHA-512).")

    algorithm_names = {
        IOCType.MD5: "MD5",
        IOCType.SHA1: "SHA-1",
        IOCType.SHA256: "SHA-256",
        IOCType.SHA512: "SHA-512",
    }

    # Check against IOC database
    db_ioc = db.query(IOCModel).filter(
        IOCModel.ioc_type == ioc_type.value,
        IOCModel.value == hash_val,
        IOCModel.is_active == True
    ).first()

    ioc_matches = []
    if db_ioc:
        ioc_matches.append(IOCMatch(
            ioc_type=ioc_type,
            value=hash_val,
            matched_ioc=IOCRecord(
                id=db_ioc.id,
                ioc_type=ioc_type,
                value=db_ioc.value,
                description=db_ioc.description,
                source=db_ioc.source,
                tags=db_ioc.tags,
                is_active=db_ioc.is_active
            ),
            context="Pasted hash matches IOC in local database"
        ))

    scan_time = (time.time() - start) * 1000

    return HashAnalyzeResponse(
        input_hash=hash_val,
        detected_type=ioc_type.value,
        detected_algorithm=algorithm_names[ioc_type],
        ioc_matches=ioc_matches,
        in_database=db_ioc is not None,
        scan_time_ms=scan_time
    )