from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_

from app.core.database import get_db
from app.api.deps import get_pagination
from app.models import (
    Investigation, Alert, InvestigationAlert, InvestigationEvidence,
    InvestigationTimeline, InvestigationNote
)
from app.schemas import (
    InvestigationCreate, InvestigationUpdate, InvestigationResponse,
    InvestigationDetail, InvestigationAlertLink, InvestigationEvidenceCreate,
    InvestigationEvidenceResponse, InvestigationTimelineResponse,
    InvestigationNoteCreate, InvestigationNoteResponse,
    InvestigationStatus, SeverityLevel, PaginatedResponse
)

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.get("", response_model=PaginatedResponse)
def list_investigations(
    status: InvestigationStatus = Query(None),
    severity: SeverityLevel = Query(None),
    search: str = Query(None),
    pagination=Depends(get_pagination),
    db: Session = Depends(get_db)
):
    """List investigations with filtering."""
    query = db.query(Investigation)
    
    if status:
        query = query.filter(Investigation.status == status.value)
    if severity:
        query = query.filter(Investigation.severity == severity.value)
    if search:
        query = query.filter(
            or_(
                Investigation.title.ilike(f"%{search}%"),
                Investigation.description.ilike(f"%{search}%")
            )
        )
    
    total = query.count()
    investigations = query.order_by(desc(Investigation.created_at)).offset(pagination.offset).limit(pagination.limit).all()
    
    items = []
    for inv in investigations:
        alert_count = db.query(func.count(InvestigationAlert.id)).filter(
            InvestigationAlert.investigation_id == inv.id
        ).scalar() or 0
        
        evidence_count = db.query(func.count(InvestigationEvidence.id)).filter(
            InvestigationEvidence.investigation_id == inv.id
        ).scalar() or 0
        
        items.append(InvestigationResponse(
            id=inv.id,
            title=inv.title,
            description=inv.description,
            severity=SeverityLevel(inv.severity),
            status=InvestigationStatus(inv.status),
            created_at=inv.created_at,
            updated_at=inv.updated_at,
            closed_at=inv.closed_at,
            created_by=inv.created_by,
            assigned_to=inv.assigned_to,
            alert_count=alert_count,
            evidence_count=evidence_count
        ))
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size
    )


@router.post("", response_model=InvestigationResponse)
def create_investigation(data: InvestigationCreate, db: Session = Depends(get_db)):
    """Create investigation from alerts."""
    # Verify alerts exist
    alerts = db.query(Alert).filter(Alert.id.in_(data.alert_ids)).all() if data.alert_ids else []
    if data.alert_ids and len(alerts) != len(data.alert_ids):
        raise HTTPException(status_code=404, detail="One or more alerts not found")
    
    # Determine severity from alerts (highest)
    severity = data.severity
    if alerts:
        severity_order = {SeverityLevel.LOW: 1, SeverityLevel.MEDIUM: 2, SeverityLevel.HIGH: 3, SeverityLevel.CRITICAL: 4}
        max_sev = max((a.severity for a in alerts), key=lambda s: severity_order.get(SeverityLevel(s), 0), default=severity.value)
        severity = SeverityLevel(max_sev)
    
    inv = Investigation(
        title=data.title,
        description=data.description,
        severity=severity.value,
        status=InvestigationStatus.OPEN.value,
        created_by="analyst",  # TODO: get from auth
        assigned_to=data.assigned_to
    )
    
    db.add(inv)
    db.flush()
    
    # Link alerts
    for alert in alerts:
        link = InvestigationAlert(investigation_id=inv.id, alert_id=alert.id)
        db.add(link)
        
        # Add timeline entry
        timeline = InvestigationTimeline(
            investigation_id=inv.id,
            timestamp=alert.timestamp or datetime.utcnow(),
            event_type="alert",
            title=f"Alert added: {alert.title}",
            description=f"Rule {alert.rule_id}: {alert.title}",
            meta_data={"alert_id": alert.id, "rule_id": alert.rule_id}
        )
        db.add(timeline)
    
    # Add creation timeline
    timeline = InvestigationTimeline(
        investigation_id=inv.id,
        timestamp=datetime.utcnow(),
        event_type="creation",
        title="Investigation created",
        description=f"Created from {len(alerts)} alert(s)" if alerts else "Created manually"
    )
    db.add(timeline)
    
    db.commit()
    db.refresh(inv)
    
    return InvestigationResponse(
        id=inv.id,
        title=inv.title,
        description=inv.description,
        severity=SeverityLevel(inv.severity),
        status=InvestigationStatus(inv.status),
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        closed_at=inv.closed_at,
        created_by=inv.created_by,
        assigned_to=inv.assigned_to,
        alert_count=len(alerts),
        evidence_count=0
    )


@router.get("/{investigation_id}", response_model=InvestigationDetail)
def get_investigation(investigation_id: int, db: Session = Depends(get_db)):
    """Get full investigation with all related data."""
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Get alerts
    alert_links = db.query(InvestigationAlert).filter(
        InvestigationAlert.investigation_id == investigation_id
    ).all()
    
    alerts = []
    for link in alert_links:
        alert = db.query(Alert).filter(Alert.id == link.alert_id).first()
        if alert:
            alerts.append(type('obj', (object,), {
                'id': alert.id,
                'event_id': alert.event_id,
                'rule_id': alert.rule_id,
                'title': alert.title,
                'severity': alert.severity,
                'confidence': alert.confidence,
                'evidence': alert.evidence,
                'source_file': alert.source_file,
                'source_event_id': alert.source_event_id,
                'timestamp': alert.timestamp,
                'recommendation': alert.recommendation,
                'status': alert.status,
                'metadata': alert.meta_data
            })())
    
    # Get evidence
    evidence = db.query(InvestigationEvidence).filter(
        InvestigationEvidence.investigation_id == investigation_id
    ).order_by(InvestigationEvidence.created_at.desc()).all()
    
    evidence_list = [
        InvestigationEvidenceResponse(
            id=ev.id,
            investigation_id=ev.investigation_id,
            title=ev.title,
            description=ev.description,
            evidence_type=ev.evidence_type,
            content=ev.content,
            file_path=ev.file_path,
            created_at=ev.created_at
        )
        for ev in evidence
    ]
    
    # Get timeline
    timeline = db.query(InvestigationTimeline).filter(
        InvestigationTimeline.investigation_id == investigation_id
    ).order_by(InvestigationTimeline.timestamp).all()
    
    timeline_list = [
        InvestigationTimelineResponse(
            id=tl.id,
            investigation_id=tl.investigation_id,
            timestamp=tl.timestamp,
            event_type=tl.event_type,
            title=tl.title,
            description=tl.description,
            metadata=tl.meta_data
        )
        for tl in timeline
    ]
    
    # Get notes
    notes = db.query(InvestigationNote).filter(
        InvestigationNote.investigation_id == investigation_id
    ).order_by(InvestigationNote.created_at.desc()).all()
    
    notes_list = [
        InvestigationNoteResponse(
            id=n.id,
            investigation_id=n.investigation_id,
            content=n.content,
            created_by=n.created_by,
            created_at=n.created_at
        )
        for n in notes
    ]
    
    return InvestigationDetail(
        id=inv.id,
        title=inv.title,
        description=inv.description,
        severity=SeverityLevel(inv.severity),
        status=InvestigationStatus(inv.status),
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        closed_at=inv.closed_at,
        created_by=inv.created_by,
        assigned_to=inv.assigned_to,
        alert_count=len(alerts),
        evidence_count=len(evidence_list),
        alerts=alerts,
        evidence=evidence_list,
        timeline=timeline_list,
        notes=notes_list
    )


@router.patch("/{investigation_id}", response_model=InvestigationResponse)
def update_investigation(
    investigation_id: int,
    data: InvestigationUpdate,
    db: Session = Depends(get_db)
):
    """Update investigation."""
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Track changes for timeline
    changes = []
    
    if data.title is not None and data.title != inv.title:
        changes.append(("title", inv.title, data.title))
        inv.title = data.title
    
    if data.description is not None:
        inv.description = data.description
    
    if data.severity is not None and data.severity.value != inv.severity:
        changes.append(("severity", inv.severity, data.severity.value))
        inv.severity = data.severity.value
    
    if data.status is not None and data.status.value != inv.status:
        changes.append(("status", inv.status, data.status.value))
        old_status = inv.status
        inv.status = data.status.value
        
        if data.status == InvestigationStatus.CLOSED and old_status != InvestigationStatus.CLOSED.value:
            inv.closed_at = datetime.utcnow()
        elif data.status != InvestigationStatus.CLOSED:
            inv.closed_at = None
    
    if data.assigned_to is not None:
        if data.assigned_to != inv.assigned_to:
            changes.append(("assignment", inv.assigned_to, data.assigned_to))
            inv.assigned_to = data.assigned_to
    
    if changes:
        for field, old, new in changes:
            timeline = InvestigationTimeline(
                investigation_id=inv.id,
                timestamp=datetime.utcnow(),
                event_type="status_change" if field == "status" else "update",
                title=f"Updated {field}",
                description=f"Changed from '{old}' to '{new}'"
            )
            db.add(timeline)
    
    db.commit()
    db.refresh(inv)
    
    alert_count = db.query(func.count(InvestigationAlert.id)).filter(
        InvestigationAlert.investigation_id == inv.id
    ).scalar() or 0
    
    evidence_count = db.query(func.count(InvestigationEvidence.id)).filter(
        InvestigationEvidence.investigation_id == inv.id
    ).scalar() or 0
    
    return InvestigationResponse(
        id=inv.id,
        title=inv.title,
        description=inv.description,
        severity=SeverityLevel(inv.severity),
        status=InvestigationStatus(inv.status),
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        closed_at=inv.closed_at,
        created_by=inv.created_by,
        assigned_to=inv.assigned_to,
        alert_count=alert_count,
        evidence_count=evidence_count
    )


@router.delete("/{investigation_id}")
def delete_investigation(investigation_id: int, db: Session = Depends(get_db)):
    """Delete investigation."""
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    db.delete(inv)
    db.commit()
    
    return {"message": "Investigation deleted successfully"}


@router.post("/{investigation_id}/alerts")
def add_alerts_to_investigation(
    investigation_id: int,
    data: InvestigationAlertLink,
    db: Session = Depends(get_db)
):
    """Add alerts to investigation."""
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    alerts = db.query(Alert).filter(Alert.id.in_(data.alert_ids)).all()
    if len(alerts) != len(data.alert_ids):
        raise HTTPException(status_code=404, detail="One or more alerts not found")
    
    added = 0
    for alert in alerts:
        existing = db.query(InvestigationAlert).filter(
            InvestigationAlert.investigation_id == investigation_id,
            InvestigationAlert.alert_id == alert.id
        ).first()
        
        if not existing:
            link = InvestigationAlert(investigation_id=investigation_id, alert_id=alert.id)
            db.add(link)
            
            timeline = InvestigationTimeline(
                investigation_id=inv.id,
                timestamp=alert.timestamp or datetime.utcnow(),
                event_type="alert",
                title=f"Alert added: {alert.title}",
                description=f"Rule {alert.rule_id}: {alert.title}",
                meta_data={"alert_id": alert.id, "rule_id": alert.rule_id}
            )
            db.add(timeline)
            added += 1
    
    db.commit()
    
    return {"message": f"Added {added} alert(s) to investigation"}


@router.post("/{investigation_id}/evidence", response_model=InvestigationEvidenceResponse)
def add_evidence(
    investigation_id: int,
    data: InvestigationEvidenceCreate,
    db: Session = Depends(get_db)
):
    """Add evidence to investigation."""
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    ev = InvestigationEvidence(
        investigation_id=investigation_id,
        title=data.title,
        description=data.description,
        evidence_type=data.evidence_type,
        content=data.content,
        file_path=data.file_path
    )
    
    db.add(ev)
    
    timeline = InvestigationTimeline(
        investigation_id=inv.id,
        timestamp=datetime.utcnow(),
        event_type="evidence",
        title=f"Evidence added: {data.title}",
        description=data.description,
        meta_data={"evidence_type": data.evidence_type}
    )
    db.add(timeline)
    
    db.commit()
    db.refresh(ev)
    
    return InvestigationEvidenceResponse(
        id=ev.id,
        investigation_id=ev.investigation_id,
        title=ev.title,
        description=ev.description,
        evidence_type=ev.evidence_type,
        content=ev.content,
        file_path=ev.file_path,
        created_at=ev.created_at
    )


@router.post("/{investigation_id}/notes", response_model=InvestigationNoteResponse)
def add_note(
    investigation_id: int,
    data: InvestigationNoteCreate,
    db: Session = Depends(get_db)
):
    """Add note to investigation."""
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    note = InvestigationNote(
        investigation_id=investigation_id,
        content=data.content,
        created_by="analyst"  # TODO: get from auth
    )
    
    db.add(note)
    
    timeline = InvestigationTimeline(
        investigation_id=inv.id,
        timestamp=datetime.utcnow(),
        event_type="note",
        title="Note added",
        description=data.content[:100] + "..." if len(data.content) > 100 else data.content
    )
    db.add(timeline)
    
    db.commit()
    db.refresh(note)
    
    return InvestigationNoteResponse(
        id=note.id,
        investigation_id=note.investigation_id,
        content=note.content,
        created_by=note.created_by,
        created_at=note.created_at
    )