from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case

from app.core.database import get_db
from app.api.deps import get_pagination, get_settings, PaginationParams
from app.models import Event, Alert, Investigation
from app.schemas import (
    DashboardStats, RecentAlert, ThreatTrendPoint, SeverityDistribution,
    SeverityLevel, AlertStatus, PaginatedResponse
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard summary statistics."""
    # Total events
    total_events = db.query(func.count(Event.id)).scalar() or 0
    
    # Total alerts
    total_alerts = db.query(func.count(Alert.id)).scalar() or 0
    
    # Critical alerts
    critical_alerts = db.query(func.count(Alert.id)).filter(
        Alert.severity == SeverityLevel.CRITICAL.value
    ).scalar() or 0
    
    # Total investigations
    total_investigations = db.query(func.count(Investigation.id)).scalar() or 0
    
    # Severity breakdown
    severity_breakdown = {}
    for severity in SeverityLevel:
        count = db.query(func.count(Alert.id)).filter(
            Alert.severity == severity.value
        ).scalar() or 0
        severity_breakdown[severity.value] = count
    
    # Recent alerts (last 24 hours)
    recent_cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_alerts_count = db.query(func.count(Alert.id)).filter(
        Alert.timestamp >= recent_cutoff
    ).scalar() or 0
    
    return DashboardStats(
        total_events=total_events,
        total_alerts=total_alerts,
        critical_alerts=critical_alerts,
        total_investigations=total_investigations,
        severity_breakdown=severity_breakdown,
        recent_alerts_count=recent_alerts_count
    )


@router.get("/recent-alerts", response_model=PaginatedResponse)
def get_recent_alerts(
    severity: SeverityLevel = Query(None),
    status: AlertStatus = Query(None),
    hours: int = Query(24, ge=1, le=168),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db)
):
    """Get recent alerts with filtering."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(Alert).filter(Alert.timestamp >= cutoff)
    
    if severity:
        query = query.filter(Alert.severity == severity.value)
    if status:
        query = query.filter(Alert.status == status.value)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    alerts = query.order_by(desc(Alert.timestamp)).offset(pagination.offset).limit(pagination.limit).all()
    
    items = [
        RecentAlert(
            id=a.id,
            title=a.title,
            severity=SeverityLevel(a.severity),
            confidence=a.confidence,
            timestamp=a.timestamp,
            source_file=a.source_file,
            rule_id=a.rule_id,
            status=AlertStatus(a.status)
        )
        for a in alerts
    ]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size
    )


@router.get("/trends", response_model=List[ThreatTrendPoint])
def get_threat_trends(
    hours: int = Query(24, ge=1, le=168),
    interval_minutes: int = Query(60, ge=5, le=1440),
    db: Session = Depends(get_db)
):
    """Get threat trend data for charting."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    # Get alerts in time range
    alerts = db.query(Alert).filter(Alert.timestamp >= cutoff).all()
    
    # Group by interval
    interval_seconds = interval_minutes * 60
    buckets: Dict[int, Dict[SeverityLevel, int]] = {}
    
    for alert in alerts:
        if not alert.timestamp:
            continue
        # Calculate bucket start
        ts = alert.timestamp.timestamp()
        bucket = int(ts // interval_seconds) * interval_seconds
        bucket_dt = datetime.fromtimestamp(bucket)
        
        if bucket not in buckets:
            buckets[bucket] = {s: 0 for s in SeverityLevel}
        
        sev = SeverityLevel(alert.severity)
        buckets[bucket][sev] += 1
    
    # Convert to trend points
    points = []
    for bucket_ts in sorted(buckets.keys()):
        for severity, count in buckets[bucket_ts].items():
            if count > 0:
                points.append(ThreatTrendPoint(
                    timestamp=datetime.fromtimestamp(bucket_ts),
                    count=count,
                    severity=severity
                ))
    
    return points


@router.get("/severity-distribution", response_model=List[SeverityDistribution])
def get_severity_distribution(db: Session = Depends(get_db)):
    """Get severity distribution for doughnut/bar chart."""
    results = []
    for severity in SeverityLevel:
        count = db.query(func.count(Alert.id)).filter(
            Alert.severity == severity.value
        ).scalar() or 0
        results.append(SeverityDistribution(severity=severity, count=count))
    
    return results