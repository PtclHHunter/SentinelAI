from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    NEW = "new"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"


class InvestigationStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class EventType(str, Enum):
    LOGIN = "login"
    PROCESS = "process"
    NETWORK = "network"
    FILE = "file"
    SYSTEM = "system"
    AUTH = "auth"
    OTHER = "other"


class IOCType(str, Enum):
    IPV4 = "ipv4"
    DOMAIN = "domain"
    URL = "url"
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"


class ReportFormat(str, Enum):
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"


# Dashboard Schemas
class DashboardStats(BaseModel):
    total_events: int
    total_alerts: int
    critical_alerts: int
    total_investigations: int
    severity_breakdown: Dict[str, int]
    recent_alerts_count: int


class RecentAlert(BaseModel):
    id: int
    title: str
    severity: SeverityLevel
    confidence: int
    timestamp: datetime
    source_file: str
    rule_id: str
    status: AlertStatus


class ThreatTrendPoint(BaseModel):
    timestamp: datetime
    count: int
    severity: SeverityLevel


class SeverityDistribution(BaseModel):
    severity: SeverityLevel
    count: int


# Log Analyzer Schemas
class UploadResponse(BaseModel):
    job_id: str
    filename: str
    status: str
    message: str


class ParseResult(BaseModel):
    job_id: str
    filename: str
    total_lines: int
    parsed_events: int
    alerts_generated: int
    parse_errors: int
    events: List["EventResponse"]
    alerts: List["AlertResponse"]


class EventResponse(BaseModel):
    id: Optional[int] = None
    source_file: str
    source_line: Optional[int] = None
    timestamp: datetime
    event_type: EventType
    severity: SeverityLevel
    message: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    normalized_data: Optional[Dict[str, Any]] = None


class AlertResponse(BaseModel):
    id: Optional[int] = None
    event_id: Optional[int] = None
    rule_id: str
    title: str
    severity: SeverityLevel
    confidence: int
    evidence: List[str]
    source_file: str
    source_event_id: Optional[str] = None
    timestamp: datetime
    recommendation: str
    status: AlertStatus
    meta_data: Optional[Dict[str, Any]] = None


class SampleLogFile(BaseModel):
    filename: str
    size: int
    modified: datetime
    description: Optional[str] = None


# IOC Scanner Schemas
class IOCRecord(BaseModel):
    id: Optional[int] = None
    ioc_type: IOCType
    value: str
    description: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IOCScanRequest(BaseModel):
    content: str


class IOCMatch(BaseModel):
    ioc_type: IOCType
    value: str
    matched_ioc: IOCRecord
    context: str  # Surrounding text where IOC was found


class IOCScanResponse(BaseModel):
    extracted_iocs: Dict[IOCType, List[str]]
    matches: List[IOCMatch]
    scan_time_ms: float


class IOCStats(BaseModel):
    total: int
    by_type: Dict[str, int]
    active: int


# Hash Analyzer Schemas
class HashResult(BaseModel):
    filename: str
    file_size: int
    md5: str
    sha1: str
    sha256: str
    sha512: str
    ioc_matches: List[IOCMatch]
    scan_time_ms: float


class HashHistoryItem(BaseModel):
    id: int
    filename: str
    file_size: int
    sha256: str
    created_at: datetime
    ioc_matches_count: int


# Investigation Schemas
class InvestigationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    severity: SeverityLevel = SeverityLevel.MEDIUM
    assigned_to: Optional[str] = None


class InvestigationCreate(InvestigationBase):
    alert_ids: List[int] = Field(default_factory=list)


class InvestigationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    severity: Optional[SeverityLevel] = None
    status: Optional[InvestigationStatus] = None
    assigned_to: Optional[str] = None


class InvestigationResponse(InvestigationBase):
    id: int
    status: InvestigationStatus
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    alert_count: int = 0
    evidence_count: int = 0


class InvestigationDetail(InvestigationResponse):
    alerts: List[AlertResponse] = []
    evidence: List["InvestigationEvidenceResponse"] = []
    timeline: List["InvestigationTimelineResponse"] = []
    notes: List["InvestigationNoteResponse"] = []


class InvestigationAlertLink(BaseModel):
    investigation_id: int
    alert_ids: List[int]


class InvestigationEvidenceCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    evidence_type: str = Field(..., pattern="^(log|hash|ioc|screenshot|other)$")
    content: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None


class InvestigationEvidenceResponse(BaseModel):
    id: int
    investigation_id: int
    title: str
    description: Optional[str] = None
    evidence_type: str
    content: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    created_at: datetime


class InvestigationTimelineResponse(BaseModel):
    id: int
    investigation_id: int
    timestamp: datetime
    event_type: str
    title: str
    description: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None


class InvestigationNoteCreate(BaseModel):
    content: str = Field(..., min_length=1)


class InvestigationNoteResponse(BaseModel):
    id: int
    investigation_id: int
    content: str
    created_by: Optional[str] = None
    created_at: datetime


# Report Schemas
class ReportGenerateRequest(BaseModel):
    investigation_id: Optional[int] = None
    alert_id: Optional[int] = None
    format: ReportFormat
    title: Optional[str] = None


class ReportResponse(BaseModel):
    id: int
    investigation_id: Optional[int] = None
    alert_id: Optional[int] = None
    title: str
    format: ReportFormat
    file_path: str
    file_size: Optional[int] = None
    generated_by: Optional[str] = None
    created_at: datetime


# Pagination
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# Health check
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str