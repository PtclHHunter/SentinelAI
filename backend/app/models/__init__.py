from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from datetime import datetime
from typing import Optional


class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    source_file = Column(String(500), nullable=False, index=True)
    source_line = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)  # login, process, network, etc.
    severity = Column(String(20), nullable=False, default="info")  # info, low, medium, high, critical
    raw_data = Column(JSON, nullable=True)  # Original parsed data
    normalized_data = Column(JSON, nullable=True)  # Normalized fields
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    alerts = relationship("Alert", back_populates="event", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_events_timestamp_type", "timestamp", "event_type"),
        Index("ix_events_source_file_time", "source_file", "timestamp"),
    )


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String(50), nullable=False, index=True)  # R001, R002, etc.
    title = Column(String(500), nullable=False)
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    confidence = Column(Integer, nullable=False)  # 0-100
    evidence = Column(JSON, nullable=False)  # List of evidence strings
    source_file = Column(String(500), nullable=False)
    source_event_id = Column(String(100), nullable=True)  # Original event ID from log
    timestamp = Column(DateTime, nullable=False, index=True)
    recommendation = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="new", index=True)  # new, investigating, resolved
    meta_data = Column("metadata", JSON, nullable=True)  # Additional rule-specific data
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    event = relationship("Event", back_populates="alerts")
    investigation_alerts = relationship("InvestigationAlert", back_populates="alert")
    
    __table_args__ = (
        Index("ix_alerts_severity_status", "severity", "status"),
        Index("ix_alerts_timestamp_severity", "timestamp", "severity"),
    )


class IOC(Base):
    __tablename__ = "iocs"
    
    id = Column(Integer, primary_key=True, index=True)
    ioc_type = Column(String(20), nullable=False, index=True)  # ipv4, domain, url, md5, sha1, sha256, sha512
    value = Column(String(500), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)  # manual, import, detection
    tags = Column(JSON, nullable=True)  # List of tags
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index("ix_iocs_type_value", "ioc_type", "value"),
    )


class Investigation(Base):
    __tablename__ = "investigations"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    status = Column(String(20), nullable=False, default="open", index=True)  # open, in_progress, closed
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime, nullable=True)
    created_by = Column(String(100), nullable=True)
    assigned_to = Column(String(100), nullable=True)
    
    # Relationships
    alerts = relationship("InvestigationAlert", back_populates="investigation", cascade="all, delete-orphan")
    evidence = relationship("InvestigationEvidence", back_populates="investigation", cascade="all, delete-orphan")
    timeline = relationship("InvestigationTimeline", back_populates="investigation", cascade="all, delete-orphan")
    notes = relationship("InvestigationNote", back_populates="investigation", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="investigation")


class InvestigationAlert(Base):
    __tablename__ = "investigation_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    added_at = Column(DateTime, default=func.now())
    
    # Relationships
    investigation = relationship("Investigation", back_populates="alerts")
    alert = relationship("Alert", back_populates="investigation_alerts")


class InvestigationEvidence(Base):
    __tablename__ = "investigation_evidence"
    
    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    evidence_type = Column(String(50), nullable=False)  # log, hash, ioc, screenshot, other
    content = Column(JSON, nullable=True)  # Structured evidence data
    file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    investigation = relationship("Investigation", back_populates="evidence")


class InvestigationTimeline(Base):
    __tablename__ = "investigation_timeline"
    
    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # alert, evidence, note, status_change, assignment
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    meta_data = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    investigation = relationship("Investigation", back_populates="timeline")


class InvestigationNote(Base):
    __tablename__ = "investigation_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    investigation = relationship("Investigation", back_populates="notes")


class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="SET NULL"), nullable=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    format = Column(String(20), nullable=False)  # pdf, json, csv
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    generated_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Relationships
    investigation = relationship("Investigation", back_populates="reports")


class Setting(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())