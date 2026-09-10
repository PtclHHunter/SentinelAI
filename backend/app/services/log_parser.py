import re
import json
import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass
from pathlib import Path

from app.schemas import EventResponse, EventType, SeverityLevel
from app.core.security import validate_file_extension, sanitize_filename


@dataclass
class ParseResult:
    events: List[EventResponse]
    errors: List[str]
    total_lines: int


class LogParser:
    """Parse various log formats into normalized events."""
    
    # Common log patterns
    PATTERNS = {
        "ssh": re.compile(
            r'(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
            r'(?P<host>\S+)\s+'
            r'(?P<process>\S+?)\[?(?P<pid>\d+)?\]?:\s+'
            r'(?P<message>.*)'
        ),
        "windows_security": re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
            r'(?P<event_id>\d+)\s+'
            r'(?P<message>.*)'
        ),
        "apache_access": re.compile(
            r'(?P<ip>\S+)\s+\S+\s+\S+\s+'
            r'\[(?P<timestamp>[^\]]+)\]\s+'
            r'"(?P<method>\S+)\s+(?P<url>\S+)\s+\S+"\s+'
            r'(?P<status>\d+)\s+(?P<size>\S+)'
        ),
        "nginx_access": re.compile(
            r'(?P<ip>\S+)\s+\S+\s+\S+\s+'
            r'\[(?P<timestamp>[^\]]+)\]\s+'
            r'"(?P<method>\S+)\s+(?P<url>\S+)\s+\S+"\s+'
            r'(?P<status>\d+)\s+(?P<size>\S+)'
        ),
        "syslog": re.compile(
            r'(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
            r'(?P<host>\S+)\s+'
            r'(?P<message>.*)'
        ),
        "json": None,  # Handled separately
        "csv": None,   # Handled separately
    }
    
    # Event type keywords
    EVENT_TYPE_KEYWORDS = {
        EventType.LOGIN: ["login", "logon", "authentication", "auth", "signin", "sign in"],
        EventType.AUTH: ["failed", "invalid", "denied", "error", "failure", "unauthorized"],
        EventType.PROCESS: ["process", "exec", "spawn", "command", "cmd", "powershell", "bash"],
        EventType.NETWORK: ["connection", "connect", "tcp", "udp", "http", "https", "ssh", "ftp"],
        EventType.FILE: ["file", "open", "read", "write", "delete", "create", "modify"],
        EventType.SYSTEM: ["system", "service", "daemon", "kernel", "reboot", "shutdown"],
    }
    
    # Severity keywords
    SEVERITY_KEYWORDS = {
        SeverityLevel.CRITICAL: ["critical", "emergency", "alert", "panic", "fatal"],
        SeverityLevel.HIGH: ["error", "fail", "denied", "unauthorized", "attack", "intrusion", "breach"],
        SeverityLevel.MEDIUM: ["warning", "warn", "suspicious", "anomaly", "violation"],
        SeverityLevel.LOW: ["info", "notice", "debug", "trace"],
    }
    
    def __init__(self):
        self.line_number = 0
    
    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a log file based on extension."""
        ext = file_path.suffix.lower()
        
        if ext == ".json":
            return self._parse_json(file_path)
        elif ext == ".csv":
            return self._parse_csv(file_path)
        else:
            return self._parse_text(file_path)
    
    def _parse_text(self, file_path: Path) -> ParseResult:
        """Parse plain text log files (.log, .txt)."""
        events = []
        errors = []
        total_lines = 0
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                total_lines += 1
                self.line_number = total_lines
                line = line.rstrip('\n\r')
                
                if not line.strip():
                    continue
                
                try:
                    event = self._parse_text_line(line, file_path.name)
                    if event:
                        events.append(event)
                except Exception as e:
                    errors.append(f"Line {total_lines}: {str(e)}")
        
        return ParseResult(events=events, errors=errors, total_lines=total_lines)
    
    def _parse_text_line(self, line: str, source_file: str) -> Optional[EventResponse]:
        """Parse a single log line using known patterns."""
        # Try each pattern
        for pattern_name, pattern in self.PATTERNS.items():
            if pattern is None:
                continue
            
            match = pattern.search(line)
            if match:
                return self._create_event_from_match(match, pattern_name, line, source_file)
        
        # Fallback: generic parsing
        return self._parse_generic_line(line, source_file)
    
    def _parse_generic_line(self, line: str, source_file: str) -> EventResponse:
        """Generic fallback parser."""
        # Try to extract timestamp
        timestamp = self._extract_timestamp(line) or datetime.now()
        
        # Determine event type and severity
        event_type = self._classify_event_type(line)
        severity = self._classify_severity(line)
        
        return EventResponse(
            source_file=source_file,
            source_line=self.line_number,
            timestamp=timestamp,
            event_type=event_type,
            severity=severity,
            message=line[:1000],
            raw_data={"original_line": line},
            normalized_data={}
        )
    
    def _create_event_from_match(
        self, 
        match: re.Match, 
        pattern_name: str, 
        original_line: str, 
        source_file: str
    ) -> EventResponse:
        """Create event from regex match."""
        groups = match.groupdict()
        
        # Parse timestamp
        timestamp = self._parse_timestamp(groups.get("timestamp"), pattern_name)
        
        # Extract normalized fields based on pattern
        normalized = {}
        event_type = EventType.OTHER
        severity = SeverityLevel.LOW
        
        if pattern_name == "ssh":
            normalized = {
                "host": groups.get("host"),
                "process": groups.get("process"),
                "pid": groups.get("pid"),
                "message": groups.get("message"),
            }
            message = groups.get("message", "").lower()
            if "failed" in message or "invalid" in message:
                event_type = EventType.AUTH
                normalized["outcome"] = "failed"
                if "password" in message:
                    normalized["auth_method"] = "password"
                elif "publickey" in message:
                    normalized["auth_method"] = "publickey"
            elif "accepted" in message or "session opened" in message:
                event_type = EventType.LOGIN
                normalized["outcome"] = "success"
            else:
                event_type = self._classify_event_type(groups.get("message", ""))
            severity = self._classify_severity(message)
            
            # Extract IP and username
            ip_match = re.search(r'from\s+(\d+\.\d+\.\d+\.\d+)', message)
            if ip_match:
                normalized["source_ip"] = ip_match.group(1)
            
            user_match = re.search(r'(?:user|for)\s+(\S+)', message)
            if user_match:
                normalized["username"] = user_match.group(1)
        
        elif pattern_name in ("apache_access", "nginx_access"):
            normalized = {
                "source_ip": groups.get("ip"),
                "method": groups.get("method"),
                "url": groups.get("url"),
                "status": int(groups.get("status", 0)),
                "size": groups.get("size"),
            }
            event_type = EventType.NETWORK
            status = int(groups.get("status", 0))
            if status >= 500:
                severity = SeverityLevel.HIGH
            elif status >= 400:
                severity = SeverityLevel.MEDIUM
            else:
                severity = SeverityLevel.LOW
        
        elif pattern_name == "windows_security":
            normalized = {
                "event_id": int(groups.get("event_id", 0)),
                "message": groups.get("message"),
            }
            event_id = int(groups.get("event_id", 0))
            # Common Windows security event IDs
            if event_id == 4624:  # Logon
                event_type = EventType.LOGIN
                normalized["outcome"] = "success"
            elif event_id == 4625:  # Failed logon
                event_type = EventType.AUTH
                normalized["outcome"] = "failed"
            elif event_id == 4672:  # Special logon
                event_type = EventType.AUTH
                severity = SeverityLevel.HIGH
            elif event_id == 4688:  # Process creation
                event_type = EventType.PROCESS
            severity = self._classify_severity(groups.get("message", ""))
        
        elif pattern_name == "syslog":
            normalized = {
                "host": groups.get("host"),
                "message": groups.get("message"),
            }
            event_type = self._classify_event_type(groups.get("message", ""))
            severity = self._classify_severity(groups.get("message", ""))
        
        return EventResponse(
            source_file=source_file,
            source_line=self.line_number,
            timestamp=timestamp,
            event_type=event_type,
            severity=severity,
            message=original_line[:1000],
            raw_data={"original_line": original_line, "pattern": pattern_name},
            normalized_data=normalized
        )
    
    def _parse_json(self, file_path: Path) -> ParseResult:
        """Parse JSON/JSONL log files."""
        events = []
        errors = []
        total_lines = 0
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read().strip()
            
            # Try JSONL first (one JSON per line)
            if '\n' in content:
                for line in content.split('\n'):
                    total_lines += 1
                    self.line_number = total_lines
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        event = self._parse_json_object(data, file_path.name)
                        if event:
                            events.append(event)
                    except json.JSONDecodeError as e:
                        errors.append(f"Line {total_lines}: JSON decode error: {e}")
            else:
                # Single JSON object or array
                total_lines = 1
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        total_lines = len(data)
                        for i, item in enumerate(data):
                            self.line_number = i + 1
                            event = self._parse_json_object(item, file_path.name)
                            if event:
                                events.append(event)
                    else:
                        event = self._parse_json_object(data, file_path.name)
                        if event:
                            events.append(event)
                except json.JSONDecodeError as e:
                    errors.append(f"JSON decode error: {e}")
        
        return ParseResult(events=events, errors=errors, total_lines=total_lines)
    
    def _parse_json_object(self, data: Dict[str, Any], source_file: str) -> Optional[EventResponse]:
        """Parse a single JSON log object."""
        # Common timestamp fields
        timestamp = None
        for field in ["timestamp", "time", "@timestamp", "datetime", "date"]:
            if field in data:
                timestamp = self._parse_iso_timestamp(data[field])
                if timestamp:
                    break
        
        if not timestamp:
            timestamp = datetime.now()
        
        # Extract message
        message = data.get("message", data.get("msg", data.get("log", "")))
        if not isinstance(message, str):
            message = json.dumps(message)
        
        # Determine event type and severity
        event_type = self._classify_event_type(message)
        severity = self._classify_severity(message)
        
        # Check for explicit level/severity
        for field in ["level", "severity", "priority"]:
            if field in data:
                severity = self._parse_severity(data[field])
                break
        
        return EventResponse(
            source_file=source_file,
            source_line=self.line_number,
            timestamp=timestamp,
            event_type=event_type,
            severity=severity,
            message=message[:1000],
            raw_data=data,
            normalized_data=self._extract_normalized_fields(data)
        )
    
    def _parse_csv(self, file_path: Path) -> ParseResult:
        """Parse CSV log files."""
        events = []
        errors = []
        total_lines = 0
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            # Detect delimiter
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                total_lines += 1
                self.line_number = total_lines
                
                try:
                    event = self._parse_csv_row(row, file_path.name)
                    if event:
                        events.append(event)
                except Exception as e:
                    errors.append(f"Line {total_lines}: {str(e)}")
        
        return ParseResult(events=events, errors=errors, total_lines=total_lines)
    
    def _parse_csv_row(self, row: Dict[str, str], source_file: str) -> EventResponse:
        """Parse a single CSV row."""
        # Try to find timestamp column
        timestamp = None
        for field in ["timestamp", "time", "datetime", "date", "@timestamp"]:
            if field in row and row[field]:
                timestamp = self._parse_iso_timestamp(row[field])
                if timestamp:
                    break
        
        if not timestamp:
            timestamp = datetime.now()
        
        # Find message column
        message = ""
        for field in ["message", "msg", "log", "description", "event"]:
            if field in row and row[field]:
                message = row[field]
                break
        
        if not message:
            message = " | ".join(f"{k}={v}" for k, v in row.items() if v)
        
        event_type = self._classify_event_type(message)
        severity = self._classify_severity(message)
        
        # Check for severity column
        for field in ["level", "severity", "priority"]:
            if field in row and row[field]:
                severity = self._parse_severity(row[field])
                break
        
        return EventResponse(
            source_file=source_file,
            source_line=self.line_number,
            timestamp=timestamp,
            event_type=event_type,
            severity=severity,
            message=message[:1000],
            raw_data=row,
            normalized_data=self._extract_normalized_fields(row)
        )
    
    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extract timestamp from log line."""
        patterns = [
            r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}',  # ISO
            r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}',       # Syslog
            r'\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}',       # Apache
            r'\d{2}-\w{3}-\d{2}\s+\d{2}:\d{2}:\d{2}',     # Custom
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return self._parse_timestamp(match.group(), "generic")
        
        return None
    
    def _parse_timestamp(self, ts_str: Optional[str], pattern_name: str) -> datetime:
        """Parse timestamp string to datetime."""
        if not ts_str:
            return datetime.now()
        
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%b %d %H:%M:%S",
            "%d/%b/%Y:%H:%M:%S",
            "%d-%b-%y %H:%M:%S",
        ]
        
        # Try to parse with year for syslog format
        if pattern_name in ("ssh", "syslog") and len(ts_str.split()) == 3:
            current_year = datetime.now().year
            ts_str = f"{current_year} {ts_str}"
            formats.insert(0, "%Y %b %d %H:%M:%S")
        
        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        
        # Try ISO format
        return self._parse_iso_timestamp(ts_str) or datetime.now()
    
    def _parse_iso_timestamp(self, value: Any) -> Optional[datetime]:
        """Parse ISO format timestamp."""
        if not isinstance(value, str):
            return None
        try:
            # Handle Z suffix and timezone
            value = value.replace('Z', '+00:00')
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    
    def _parse_severity(self, value: Any) -> SeverityLevel:
        """Parse severity from string/number."""
        if isinstance(value, int):
            # Syslog severity: 0=emerg, 1=alert, 2=crit, 3=err, 4=warn, 5=notice, 6=info, 7=debug
            if value <= 2:
                return SeverityLevel.CRITICAL
            elif value == 3:
                return SeverityLevel.HIGH
            elif value == 4:
                return SeverityLevel.MEDIUM
            else:
                return SeverityLevel.LOW
        
        if isinstance(value, str):
            value = value.lower()
            if value in ("critical", "emergency", "alert", "panic", "fatal", "emerg"):
                return SeverityLevel.CRITICAL
            elif value in ("error", "err", "fail", "high"):
                return SeverityLevel.HIGH
            elif value in ("warning", "warn", "medium"):
                return SeverityLevel.MEDIUM
            elif value in ("info", "notice", "low", "debug", "trace"):
                return SeverityLevel.LOW
        
        return SeverityLevel.LOW
    
    def _classify_event_type(self, message: str) -> EventType:
        """Classify event type from message content."""
        message_lower = message.lower()
        
        for event_type, keywords in self.EVENT_TYPE_KEYWORDS.items():
            if any(kw in message_lower for kw in keywords):
                return event_type
        
        return EventType.OTHER
    
    def _classify_severity(self, message: str) -> SeverityLevel:
        """Classify severity from message content."""
        message_lower = message.lower()
        
        for severity, keywords in self.SEVERITY_KEYWORDS.items():
            if any(kw in message_lower for kw in keywords):
                return severity
        return SeverityLevel.LOW


    def _extract_normalized_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract commonly used normalized fields from log data."""
        normalized = {}
        
        # Common field mappings
        field_mappings = {
            "source_ip": ["source_ip", "src_ip", "client_ip", "ip", "remote_addr", "sourceip"],
            "destination_ip": ["dest_ip", "dst_ip", "destination_ip", "target_ip"],
            "username": ["user", "username", "account", "login", "userid"],
            "outcome": ["outcome", "result", "status", "action"],
            "command": ["command", "cmd", "cmdline", "command_line", "process_command"],
            "process_name": ["process", "process_name", "image", "executable"],
            "pid": ["pid", "process_id"],
            "parent_pid": ["ppid", "parent_pid", "parent_process_id"],
        }
        
        for norm_field, possible_fields in field_mappings.items():
            for field in possible_fields:
                if field in data and data[field]:
                    normalized[norm_field] = data[field]
                    break
        
        return normalized