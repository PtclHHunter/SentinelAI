import json
import csv
import io
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib import colors

from app.models import Investigation, Alert, Event, Report as ReportModel
from app.schemas import ReportFormat, SeverityLevel, AlertStatus, InvestigationStatus


# Color palette
COLORS = {
    "bg_dark": HexColor("#0d1117"),
    "bg_card": HexColor("#161b22"),
    "border": HexColor("#30363d"),
    "text_primary": HexColor("#e6edf3"),
    "text_secondary": HexColor("#8b949e"),
    "accent_cyan": HexColor("#00d4ff"),
    "accent_purple": HexColor("#a371f7"),
    "severity_critical": HexColor("#f85149"),
    "severity_high": HexColor("#d29922"),
    "severity_medium": HexColor("#a371f7"),
    "severity_low": HexColor("#3fb950"),
    "white": white,
}


class ReportGenerator:
    """Generate professional reports in PDF, JSON, and CSV formats."""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(
        self,
        investigation: Optional[Investigation] = None,
        alert: Optional[Alert] = None,
        format: ReportFormat = ReportFormat.PDF,
        title: Optional[str] = None,
        generated_by: str = "SentinelAI"
    ) -> ReportModel:
        """Generate a report and save to database."""
        
        if not investigation and not alert:
            raise ValueError("Either investigation or alert must be provided")
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if investigation:
            base_name = f"investigation_{investigation.id}_{timestamp}"
        else:
            base_name = f"alert_{alert.id}_{timestamp}"
        
        ext = format.value
        filename = f"{base_name}.{ext}"
        file_path = self.reports_dir / filename
        
        # Generate content based on format
        if format == ReportFormat.PDF:
            file_size = self._generate_pdf(investigation, alert, file_path, title, generated_by)
        elif format == ReportFormat.JSON:
            file_size = self._generate_json(investigation, alert, file_path, title, generated_by)
        elif format == ReportFormat.CSV:
            file_size = self._generate_csv(investigation, alert, file_path, title, generated_by)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Create report record
        report = ReportModel(
            investigation_id=investigation.id if investigation else None,
            alert_id=alert.id if alert else None,
            title=title or f"{'Investigation' if investigation else 'Alert'} Report",
            format=format.value,
            file_path=str(file_path),
            file_size=file_size,
            generated_by=generated_by
        )
        
        return report
    
    def _generate_pdf(
        self,
        investigation: Optional[Investigation],
        alert: Optional[Alert],
        file_path: Path,
        title: Optional[str],
        generated_by: str
    ) -> int:
        """Generate professional PDF report."""
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
        )
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=styles['Title'],
            fontSize=24,
            leading=28,
            textColor=COLORS["text_primary"],
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
        ))
        
        styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            textColor=COLORS["text_secondary"],
            spaceAfter=20,
            alignment=TA_CENTER,
        ))
        
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            leading=18,
            textColor=COLORS["accent_cyan"],
            spaceBefore=16,
            spaceAfter=8,
            borderWidth=0,
            borderPadding=0,
            fontName='Helvetica-Bold',
        ))
        
        styles.add(ParagraphStyle(
            name='BodyText2',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=COLORS["text_primary"],
            spaceAfter=6,
            alignment=TA_JUSTIFY,
        ))
        
        styles.add(ParagraphStyle(
            name='TableHeader',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=COLORS["white"],
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
        ))
        
        styles.add(ParagraphStyle(
            name='TableCell',
            parent=styles['Normal'],
            fontSize=8,
            leading=11,
            textColor=COLORS["text_primary"],
            alignment=TA_LEFT,
        ))
        
        styles.add(ParagraphStyle(
            name='SeverityCritical',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=COLORS["severity_critical"],
            fontName='Helvetica-Bold',
        ))
        
        styles.add(ParagraphStyle(
            name='SeverityHigh',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=COLORS["severity_high"],
            fontName='Helvetica-Bold',
        ))
        
        styles.add(ParagraphStyle(
            name='SeverityMedium',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=COLORS["severity_medium"],
            fontName='Helvetica-Bold',
        ))
        
        styles.add(ParagraphStyle(
            name='SeverityLow',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=COLORS["severity_low"],
            fontName='Helvetica-Bold',
        ))
        
        story = []
        
        # Header
        story.append(Paragraph("SentinelAI", styles['ReportTitle']))
        story.append(Paragraph("Cybersecurity Incident Report", styles['ReportSubtitle']))
        story.append(HRFlowable(width="100%", thickness=2, color=COLORS["accent_cyan"], spaceAfter=20))
        
        # Report metadata
        meta_data = [
            ["Field", "Value"],
            ["Report Title", title or ("Investigation Report" if investigation else "Alert Report")],
            ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")],
            ["Generated By", generated_by],
            ["Project", "SentinelAI v1.0.0"],
        ]
        
        if investigation:
            meta_data.extend([
                ["Investigation ID", str(investigation.id)],
                ["Investigation Title", investigation.title],
                ["Severity", investigation.severity.upper()],
                ["Status", investigation.status.replace("_", " ").title()],
                ["Created", investigation.created_at.strftime("%Y-%m-%d %H:%M:%S") if investigation.created_at else "N/A"],
            ])
        elif alert:
            meta_data.extend([
                ["Alert ID", str(alert.id)],
                ["Alert Title", alert.title],
                ["Severity", alert.severity.value.upper()],
                ["Confidence", f"{alert.confidence}%"],
                ["Status", alert.status.value.title()],
                ["Rule ID", alert.rule_id],
                ["Timestamp", alert.timestamp.strftime("%Y-%m-%d %H:%M:%S") if alert.timestamp else "N/A"],
            ])
        
        meta_table = Table(meta_data, colWidths=[1.8*inch, 4.7*inch])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLORS["bg_card"]),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLORS["accent_cyan"]),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 1), (0, -1), COLORS["bg_card"]),
            ('TEXTCOLOR', (0, 1), (0, -1), COLORS["text_secondary"]),
            ('TEXTCOLOR', (1, 1), (-1, -1), COLORS["text_primary"]),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS["border"]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 20))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", styles['SectionHeader']))
        
        if investigation:
            summary_text = (
                f"This report details the findings of investigation <b>{investigation.title}</b> "
                f"(ID: {investigation.id}). The investigation was initiated with "
                f"<b>{len(investigation.alerts)} associated alert(s)</b> and contains "
                f"<b>{len(investigation.evidence)} piece(s) of evidence</b>. "
                f"Current status: <b>{investigation.status.replace('_', ' ').title()}</b>."
            )
            if investigation.description:
                summary_text += f" <b>Description:</b> {investigation.description}"
        else:
            summary_text = (
                f"This report documents alert <b>{alert.title}</b> (ID: {alert.id}), "
                f"triggered by rule <b>{alert.rule_id}</b> with "
                f"<b>{alert.severity.value.upper()}</b> severity and "
                f"<b>{alert.confidence}%</b> confidence. "
                f"Current status: <b>{alert.status.value.title()}</b>."
            )
        
        story.append(Paragraph(summary_text, styles['BodyText2']))
        story.append(Spacer(1, 12))
        
        # Alerts section
        if investigation and investigation.alerts:
            story.append(Paragraph("Associated Alerts", styles['SectionHeader']))
            
            alert_headers = ["ID", "Rule", "Title", "Severity", "Confidence", "Timestamp", "Status"]
            alert_rows = [alert_headers]
            
            for ia in investigation.alerts:
                a = ia.alert
                sev_style = {
                    SeverityLevel.CRITICAL: 'SeverityCritical',
                    SeverityLevel.HIGH: 'SeverityHigh',
                    SeverityLevel.MEDIUM: 'SeverityMedium',
                    SeverityLevel.LOW: 'SeverityLow',
                }.get(a.severity, 'TableCell')
                
                alert_rows.append([
                    str(a.id),
                    a.rule_id,
                    a.title[:50] + "..." if len(a.title) > 50 else a.title,
                    Paragraph(a.severity.value.upper(), styles[sev_style]),
                    f"{a.confidence}%",
                    a.timestamp.strftime("%Y-%m-%d %H:%M") if a.timestamp else "N/A",
                    a.status.value.title(),
                ])
            
            alert_table = Table(alert_rows, colWidths=[0.4*inch, 0.6*inch, 1.8*inch, 0.7*inch, 0.6*inch, 1.0*inch, 0.8*inch])
            alert_table.setStyle(self._get_table_style())
            story.append(alert_table)
            story.append(Spacer(1, 12))
        
        # Evidence section
        if investigation and investigation.evidence:
            story.append(Paragraph("Evidence", styles['SectionHeader']))
            
            ev_headers = ["ID", "Type", "Title", "Description", "Created"]
            ev_rows = [ev_headers]
            
            for ev in investigation.evidence:
                ev_rows.append([
                    str(ev.id),
                    ev.evidence_type.title(),
                    ev.title[:40] + "..." if len(ev.title) > 40 else ev.title,
                    (ev.description[:60] + "...") if ev.description and len(ev.description) > 60 else (ev.description or ""),
                    ev.created_at.strftime("%Y-%m-%d %H:%M") if ev.created_at else "N/A",
                ])
            
            ev_table = Table(ev_rows, colWidths=[0.4*inch, 0.8*inch, 1.5*inch, 2.8*inch, 1.0*inch])
            ev_table.setStyle(self._get_table_style())
            story.append(ev_table)
            story.append(Spacer(1, 12))
        
        # Timeline section
        if investigation and investigation.timeline:
            story.append(Paragraph("Timeline", styles['SectionHeader']))
            
            tl_headers = ["Timestamp", "Event Type", "Title", "Description"]
            tl_rows = [tl_headers]
            
            for tl in sorted(investigation.timeline, key=lambda x: x.timestamp):
                tl_rows.append([
                    tl.timestamp.strftime("%Y-%m-%d %H:%M:%S") if tl.timestamp else "N/A",
                    tl.event_type.replace("_", " ").title(),
                    tl.title[:40] + "..." if len(tl.title) > 40 else tl.title,
                    (tl.description[:80] + "...") if tl.description and len(tl.description) > 80 else (tl.description or ""),
                ])
            
            tl_table = Table(tl_rows, colWidths=[1.1*inch, 1.0*inch, 1.5*inch, 2.9*inch])
            tl_table.setStyle(self._get_table_style())
            story.append(tl_table)
            story.append(Spacer(1, 12))
        
        # Notes section
        if investigation and investigation.notes:
            story.append(Paragraph("Investigation Notes", styles['SectionHeader']))
            
            for note in investigation.notes:
                note_text = f"<b>[{note.created_at.strftime('%Y-%m-%d %H:%M')}]</b> {note.content}"
                if note.created_by:
                    note_text = f"<b>[{note.created_by}]</b> {note_text}"
                story.append(Paragraph(note_text, styles['BodyText2']))
                story.append(Spacer(1, 6))
        
        # Single alert details (if no investigation)
        if alert and not investigation:
            story.append(Paragraph("Alert Details", styles['SectionHeader']))
            
            # Evidence
            if alert.evidence:
                story.append(Paragraph("Evidence", styles['SectionHeader']))
                story.append(Paragraph(alert.evidence, styles['BodyText2']))
                story.append(Spacer(1, 8))
            
            # Recommendation
            story.append(Paragraph("Recommended Action", styles['SectionHeader']))
            story.append(Paragraph(alert.recommendation, styles['BodyText2']))
            story.append(Spacer(1, 8))
            
            # Metadata
            if alert.meta_data:
                story.append(Paragraph("Additional Metadata", styles['SectionHeader']))
                meta_items = []
                for k, v in alert.meta_data.items():
                    meta_items.append([k.replace("_", " ").title(), str(v)])
                
                if meta_items:
                    meta_table = Table([["Key", "Value"]] + meta_items, colWidths=[2.0*inch, 4.5*inch])
                    meta_table.setStyle(self._get_table_style())
                    story.append(meta_table)
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(HRFlowable(width="100%", thickness=1, color=COLORS["border"], spaceAfter=10))
        story.append(Paragraph(
            f"<i>Report generated by SentinelAI on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}. "
            f"This is an automated report for educational/demo purposes.</i>",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=COLORS["text_secondary"], alignment=TA_CENTER)
        ))
        
        # Build PDF
        doc.build(story)
        
        return file_path.stat().st_size
    
    def _get_table_style(self) -> TableStyle:
        """Get consistent table style for PDF."""
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLORS["bg_card"]),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLORS["accent_cyan"]),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), COLORS["bg_dark"]),
            ('TEXTCOLOR', (0, 1), (-1, -1), COLORS["text_primary"]),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS["border"]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLORS["bg_dark"], COLORS["bg_card"]]),
        ])
    
    def _generate_json(
        self,
        investigation: Optional[Investigation],
        alert: Optional[Alert],
        file_path: Path,
        title: Optional[str],
        generated_by: str
    ) -> int:
        """Generate JSON report."""
        data = {
            "report": {
                "title": title or ("Investigation Report" if investigation else "Alert Report"),
                "generated_at": datetime.now().isoformat(),
                "generated_by": generated_by,
                "project": "SentinelAI",
                "version": "1.0.0",
            }
        }
        
        if investigation:
            data["investigation"] = self._investigation_to_dict(investigation)
        elif alert:
            data["alert"] = self._alert_to_dict(alert)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        return file_path.stat().st_size
    
    def _generate_csv(
        self,
        investigation: Optional[Investigation],
        alert: Optional[Alert],
        file_path: Path,
        title: Optional[str],
        generated_by: str
    ) -> int:
        """Generate CSV report."""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(["SentinelAI Report"])
            writer.writerow([title or ("Investigation Report" if investigation else "Alert Report")])
            writer.writerow(["Generated", datetime.now().isoformat()])
            writer.writerow(["Generated By", generated_by])
            writer.writerow([])
            
            if investigation:
                # Investigation summary
                writer.writerow(["Investigation Summary"])
                writer.writerow(["Field", "Value"])
                writer.writerow(["ID", investigation.id])
                writer.writerow(["Title", investigation.title])
                writer.writerow(["Severity", investigation.severity])
                writer.writerow(["Status", investigation.status])
                writer.writerow(["Created", investigation.created_at.isoformat() if investigation.created_at else ""])
                writer.writerow(["Description", investigation.description or ""])
                writer.writerow([])
                
                # Alerts
                if investigation.alerts:
                    writer.writerow(["Associated Alerts"])
                    writer.writerow(["ID", "Rule ID", "Title", "Severity", "Confidence", "Timestamp", "Status"])
                    for ia in investigation.alerts:
                        a = ia.alert
                        writer.writerow([
                            a.id, a.rule_id, a.title, a.severity.value, a.confidence,
                            a.timestamp.isoformat() if a.timestamp else "", a.status.value
                        ])
                    writer.writerow([])
                
                # Evidence
                if investigation.evidence:
                    writer.writerow(["Evidence"])
                    writer.writerow(["ID", "Type", "Title", "Description", "Created"])
                    for ev in investigation.evidence:
                        writer.writerow([
                            ev.id, ev.evidence_type, ev.title, ev.description or "",
                            ev.created_at.isoformat() if ev.created_at else ""
                        ])
                    writer.writerow([])
                
                # Timeline
                if investigation.timeline:
                    writer.writerow(["Timeline"])
                    writer.writerow(["Timestamp", "Event Type", "Title", "Description"])
                    for tl in sorted(investigation.timeline, key=lambda x: x.timestamp):
                        writer.writerow([
                            tl.timestamp.isoformat() if tl.timestamp else "",
                            tl.event_type, tl.title, tl.description or ""
                        ])
                    writer.writerow([])
                
                # Notes
                if investigation.notes:
                    writer.writerow(["Notes"])
                    writer.writerow(["Timestamp", "Author", "Content"])
                    for note in investigation.notes:
                        writer.writerow([
                            note.created_at.isoformat() if note.created_at else "",
                            note.created_by or "",
                            note.content
                        ])
            
            elif alert:
                writer.writerow(["Alert Details"])
                writer.writerow(["Field", "Value"])
                writer.writerow(["ID", alert.id])
                writer.writerow(["Rule ID", alert.rule_id])
                writer.writerow(["Title", alert.title])
                writer.writerow(["Severity", alert.severity.value])
                writer.writerow(["Confidence", alert.confidence])
                writer.writerow(["Timestamp", alert.timestamp.isoformat() if alert.timestamp else ""])
                writer.writerow(["Status", alert.status.value])
                writer.writerow(["Source File", alert.source_file])
                writer.writerow(["Recommendation", alert.recommendation])
                writer.writerow(["Evidence", "; ".join(alert.evidence)])
                
                if alert.meta_data:
                    writer.writerow([])
                    writer.writerow(["Metadata"])
                    writer.writerow(["Key", "Value"])
                    for k, v in alert.meta_data.items():
                        writer.writerow([k, str(v)])
        
        return file_path.stat().st_size
    
    def _investigation_to_dict(self, inv: Investigation) -> Dict[str, Any]:
        """Convert investigation to dictionary."""
        return {
            "id": inv.id,
            "title": inv.title,
            "description": inv.description,
            "severity": inv.severity,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
            "closed_at": inv.closed_at.isoformat() if inv.closed_at else None,
            "created_by": inv.created_by,
            "assigned_to": inv.assigned_to,
            "alerts": [self._alert_to_dict(ia.alert) for ia in inv.alerts],
            "evidence": [
                {
                    "id": ev.id,
                    "type": ev.evidence_type,
                    "title": ev.title,
                    "description": ev.description,
                    "content": ev.content,
                    "file_path": ev.file_path,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                }
                for ev in inv.evidence
            ],
            "timeline": [
                {
                    "id": tl.id,
                    "timestamp": tl.timestamp.isoformat() if tl.timestamp else None,
                    "event_type": tl.event_type,
                    "title": tl.title,
                    "description": tl.description,
                    "metadata": tl.meta_data,
                }
                for tl in inv.timeline
            ],
            "notes": [
                {
                    "id": note.id,
                    "content": note.content,
                    "created_by": note.created_by,
                    "created_at": note.created_at.isoformat() if note.created_at else None,
                }
                for note in inv.notes
            ],
        }
    
    def _alert_to_dict(self, alert: Alert) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "id": alert.id,
            "rule_id": alert.rule_id,
            "title": alert.title,
            "severity": alert.severity.value,
            "confidence": alert.confidence,
            "evidence": alert.evidence,
            "source_file": alert.source_file,
            "source_event_id": alert.source_event_id,
            "timestamp": alert.timestamp.isoformat() if alert.timestamp else None,
            "recommendation": alert.recommendation,
            "status": alert.status.value,
            "metadata": alert.meta_data,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "updated_at": alert.updated_at.isoformat() if alert.updated_at else None,
        }