from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.core.database import get_db
from app.api.deps import get_pagination
from app.services.ioc_extractor import IOCExtractor
from app.models import IOC as IOCModel
from app.schemas import (
    IOCRecord, IOCScanRequest, IOCScanResponse, IOCMatch, IOCStats,
    IOCType, PaginatedResponse
)

router = APIRouter(prefix="/ioc", tags=["ioc-scanner"])


@router.post("/scan", response_model=IOCScanResponse)
def scan_iocs(request: IOCScanRequest, db: Session = Depends(get_db)):
    """Extract and scan IOCs from provided text."""
    import time
    start_time = time.time()
    
    extractor = IOCExtractor()
    extracted = extractor.extract_all(request.content)
    
    # Check against local database
    matches = []
    
    for ioc_type, ioc_list in extracted.items():
        for ioc in ioc_list:
            db_ioc = db.query(IOCModel).filter(
                IOCModel.ioc_type == ioc_type.value,
                IOCModel.value == ioc.value,
                IOCModel.is_active == True
            ).first()
            
            if db_ioc:
                matches.append(IOCMatch(
                    ioc_type=ioc_type,
                    value=ioc.value,
                    matched_ioc=IOCRecord(
                        id=db_ioc.id,
                        ioc_type=ioc_type,
                        value=db_ioc.value,
                        description=db_ioc.description,
                        source=db_ioc.source,
                        tags=db_ioc.tags,
                        is_active=db_ioc.is_active,
                        created_at=db_ioc.created_at,
                        updated_at=db_ioc.updated_at
                    ),
                    context=ioc.context
                ))
    
    scan_time_ms = (time.time() - start_time) * 1000
    
    # Convert extracted to simple values for response
    extracted_values = {
        ioc_type: [ioc.value for ioc in ioc_list]
        for ioc_type, ioc_list in extracted.items()
    }
    
    return IOCScanResponse(
        extracted_iocs=extracted_values,
        matches=matches,
        scan_time_ms=scan_time_ms
    )


@router.get("/database", response_model=PaginatedResponse)
def list_iocs(
    ioc_type: IOCType = Query(None),
    search: str = Query(None),
    is_active: bool = Query(None),
    pagination=Depends(get_pagination),
    db: Session = Depends(get_db)
):
    """List IOC records from local database."""
    query = db.query(IOCModel)
    
    if ioc_type:
        query = query.filter(IOCModel.ioc_type == ioc_type.value)
    if search:
        query = query.filter(
            or_(
                IOCModel.value.ilike(f"%{search}%"),
                IOCModel.description.ilike(f"%{search}%")
            )
        )
    if is_active is not None:
        query = query.filter(IOCModel.is_active == is_active)
    
    total = query.count()
    iocs = query.order_by(IOCModel.created_at.desc()).offset(pagination.offset).limit(pagination.limit).all()
    
    items = [
        IOCRecord(
            id=i.id,
            ioc_type=IOCType(i.ioc_type),
            value=i.value,
            description=i.description,
            source=i.source,
            tags=i.tags,
            is_active=i.is_active,
            created_at=i.created_at,
            updated_at=i.updated_at
        )
        for i in iocs
    ]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size
    )


@router.post("/database", response_model=IOCRecord)
def create_ioc(record: IOCRecord, db: Session = Depends(get_db)):
    """Add IOC record to local database."""
    # Check for duplicate
    existing = db.query(IOCModel).filter(
        IOCModel.ioc_type == record.ioc_type.value,
        IOCModel.value == record.value
    ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail="IOC already exists")
    
    ioc = IOCModel(
        ioc_type=record.ioc_type.value,
        value=record.value,
        description=record.description,
        source=record.source or "manual",
        tags=record.tags,
        is_active=record.is_active
    )
    
    db.add(ioc)
    db.commit()
    db.refresh(ioc)
    
    return IOCRecord(
        id=ioc.id,
        ioc_type=IOCType(ioc.ioc_type),
        value=ioc.value,
        description=ioc.description,
        source=ioc.source,
        tags=ioc.tags,
        is_active=ioc.is_active,
        created_at=ioc.created_at,
        updated_at=ioc.updated_at
    )


@router.delete("/database/{ioc_id}")
def delete_ioc(ioc_id: int, db: Session = Depends(get_db)):
    """Remove IOC record from local database."""
    ioc = db.query(IOCModel).filter(IOCModel.id == ioc_id).first()
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC not found")
    
    db.delete(ioc)
    db.commit()
    
    return {"message": "IOC deleted successfully"}


@router.get("/stats", response_model=IOCStats)
def get_ioc_stats(db: Session = Depends(get_db)):
    """Get IOC database statistics."""
    total = db.query(func.count(IOCModel.id)).scalar() or 0
    active = db.query(func.count(IOCModel.id)).filter(IOCModel.is_active == True).scalar() or 0
    
    by_type = {}
    for ioc_type in IOCType:
        count = db.query(func.count(IOCModel.id)).filter(
            IOCModel.ioc_type == ioc_type.value
        ).scalar() or 0
        by_type[ioc_type.value] = count
    
    return IOCStats(
        total=total,
        by_type=by_type,
        active=active
    )