from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from app.schemas import AlertResponse, EventResponse, IOCType, IOCMatch


@dataclass
class DetectionContext:
    """Context passed to detection rules."""
    events: List[EventResponse]
    ioc_matches: List[IOCMatch]
    settings: Dict[str, Any]


class AnalysisEngine(ABC):
    """Abstract base class for analysis engines.
    
    This interface allows swapping between rule-based, ML-based, or hybrid
    analysis implementations without changing the API layer.
    """
    
    @abstractmethod
    def analyze_events(
        self,
        events: List[EventResponse],
        ioc_matches: List[IOCMatch],
        settings: Dict[str, Any]
    ) -> List[AlertResponse]:
        """Analyze events and return detected alerts."""
        pass
    
    @abstractmethod
    def get_supported_rules(self) -> List[str]:
        """Return list of supported rule IDs."""
        pass
    
    @abstractmethod
    def get_rule_description(self, rule_id: str) -> Optional[str]:
        """Get human-readable description of a rule."""
        pass


class RuleBasedAnalysisEngine(AnalysisEngine):
    """Deterministic rule-based threat detection engine.
    
    Implements all detection rules using configurable thresholds
    and pattern matching. No external dependencies or AI/ML.
    """
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self._rules = {
            "R001": self._rule_repeated_failed_logins,
            "R002": self._rule_brute_force,
            "R003": self._rule_suspicious_ip_login,
            "R004": self._rule_privilege_escalation,
            "R005": self._rule_suspicious_process,
            "R006": self._rule_ioc_match,
            "R007": self._rule_anomalous_time_access,
            "R008": self._rule_multiple_account_access,
            "R009": self._rule_log_clearing,
        }
    
    def analyze_events(
        self,
        events: List[EventResponse],
        ioc_matches: List[IOCMatch],
        settings: Dict[str, Any]
    ) -> List[AlertResponse]:
        """Run all detection rules against events."""
        context = DetectionContext(
            events=events,
            ioc_matches=ioc_matches,
            settings=settings
        )
        
        all_alerts = []
        for rule_id, rule_func in self._rules.items():
            try:
                alerts = rule_func(context)
                all_alerts.extend(alerts)
            except Exception as e:
                # Log error but continue with other rules
                print(f"Rule {rule_id} failed: {e}")
        
        return all_alerts
    
    def get_supported_rules(self) -> List[str]:
        return list(self._rules.keys())
    
    def get_rule_description(self, rule_id: str) -> Optional[str]:
        descriptions = {
            "R001": "Repeated failed logins from same IP (≥5 in 15 minutes)",
            "R002": "Brute force attack (≥10 failed logins from same IP in 5 minutes)",
            "R003": "Login from IP in local IOC database",
            "R004": "Privilege escalation indicators (sudo, root, admin, unauthorized access)",
            "R005": "Suspicious process execution (netcat, encoded PowerShell, wget/curl)",
            "R006": "IOC match (IP, domain, hash, URL in local database)",
            "R007": "Anomalous time access (successful login outside business hours)",
            "R008": "Multiple account access from single IP (≥5 accounts in 10 minutes)",
            "R009": "Log clearing activity (truncate, wevtutil, clear commands)",
        }
        return descriptions.get(rule_id)
    
    # --- Detection Rules ---
    
    def _rule_repeated_failed_logins(self, ctx: DetectionContext) -> List[AlertResponse]:
        """R001: ≥5 failed logins from same IP in 15 minutes."""
        from collections import defaultdict
        
        threshold = ctx.settings.get("failed_login_threshold", 5)
        window_minutes = ctx.settings.get("failed_login_window_minutes", 15)
        window_seconds = window_minutes * 60
        
        # Group failed logins by IP
        failed_by_ip = defaultdict(list)
        for event in ctx.events:
            if (event.event_type.value in ("login", "auth") and 
                event.severity.value in ("low", "medium", "high", "critical") and
                event.normalized_data):
                outcome = event.normalized_data.get("outcome", "").lower()
                if outcome in ("failed", "failure", "invalid", "denied"):
                    ip = event.normalized_data.get("source_ip")
                    if ip:
                        failed_by_ip[ip].append(event)
        
        alerts = []
        for ip, events in failed_by_ip.items():
            # Sort by timestamp
            events.sort(key=lambda e: e.timestamp)
            
            # Sliding window check
            for i in range(len(events)):
                window_start = events[i].timestamp
                window_events = [
                    e for e in events 
                    if (e.timestamp - window_start).total_seconds() <= window_seconds
                ]
                
                if len(window_events) >= threshold:
                    # Create alert for this cluster
                    alert = AlertResponse(
                        rule_id="R001",
                        title=f"Repeated Failed Logins from {ip}",
                        severity=SeverityLevel.HIGH,
                        confidence=85,
                        evidence=[
                            f"{len(window_events)} failed login attempts from {ip}",
                            f"Time window: {window_minutes} minutes",
                            f"Accounts targeted: {len(set(e.normalized_data.get('username') for e in window_events if e.normalized_data))}"
                        ],
                        source_file=window_events[0].source_file,
                        source_event_id=str(window_events[0].id),
                        timestamp=window_events[-1].timestamp,
                        recommendation=(
                            "Block IP at firewall. Review targeted accounts for compromise. "
                            "Enable MFA for affected accounts. Check for password spray patterns."
                        ),
                        status=AlertStatus.NEW,
                        meta_data={
                            "source_ip": ip,
                            "attempt_count": len(window_events),
                            "window_minutes": window_minutes,
                            "targeted_accounts": list(set(
                                e.normalized_data.get("username") 
                                for e in window_events if e.normalized_data
                            ))
                        }
                    )
                    alerts.append(alert)
                    break  # One alert per IP cluster
        
        return alerts
    
    def _rule_brute_force(self, ctx: DetectionContext) -> List[AlertResponse]:
        """R002: ≥10 failed logins from same IP in 5 minutes."""
        from collections import defaultdict
        
        threshold = ctx.settings.get("brute_force_threshold", 10)
        window_minutes = ctx.settings.get("brute_force_window_minutes", 5)
        window_seconds = window_minutes * 60
        
        failed_by_ip = defaultdict(list)
        for event in ctx.events:
            if (event.event_type.value in ("login", "auth") and
                event.normalized_data):
                outcome = event.normalized_data.get("outcome", "").lower()
                if outcome in ("failed", "failure", "invalid", "denied"):
                    ip = event.normalized_data.get("source_ip")
                    if ip:
                        failed_by_ip[ip].append(event)
        
        alerts = []
        for ip, events in failed_by_ip.items():
            events.sort(key=lambda e: e.timestamp)
            
            for i in range(len(events)):
                window_start = events[i].timestamp
                window_events = [
                    e for e in events
                    if (e.timestamp - window_start).total_seconds() <= window_seconds
                ]
                
                if len(window_events) >= threshold:
                    alert = AlertResponse(
                        rule_id="R002",
                        title=f"Brute Force Attack from {ip}",
                        severity=SeverityLevel.CRITICAL,
                        confidence=95,
                        evidence=[
                            f"{len(window_events)} failed login attempts from {ip}",
                            f"Time window: {window_minutes} minutes (high velocity)",
                            f"Rate: {len(window_events) / window_minutes:.1f} attempts/minute"
                        ],
                        source_file=window_events[0].source_file,
                        source_event_id=str(window_events[0].id),
                        timestamp=window_events[-1].timestamp,
                        recommendation=(
                            "IMMEDIATE: Block IP at firewall/IDS. Force password reset for all targeted accounts. "
                            "Enable account lockout policies. Review authentication logs for successful logins from this IP."
                        ),
                        status=AlertStatus.NEW,
                        meta_data={
                            "source_ip": ip,
                            "attempt_count": len(window_events),
                            "window_minutes": window_minutes,
                            "attempts_per_minute": round(len(window_events) / window_minutes, 1)
                        }
                    )
                    alerts.append(alert)
                    break
        
        return alerts
    
    def _rule_suspicious_ip_login(self, ctx: DetectionContext) -> List[AlertResponse]:
        """R003: Successful login from IP in local IOC database."""
        # Get IPs from IOC matches
        malicious_ips = {
            match.matched_ioc.value 
            for match in ctx.ioc_matches 
            if match.ioc_type == IOCType.IPV4
        }
        
        if not malicious_ips:
            return []
        
        alerts = []
        for event in ctx.events:
            if (event.event_type.value in ("login", "auth") and
                event.normalized_data):
                outcome = event.normalized_data.get("outcome", "").lower()
                if outcome in ("success", "accepted", "logged in"):
                    ip = event.normalized_data.get("source_ip")
                    if ip in malicious_ips:
                        matched_ioc = next(
                            m for m in ctx.ioc_matches 
                            if m.matched_ioc.value == ip and m.ioc_type == IOCType.IPV4
                        )
                        alert = AlertResponse(
                            rule_id="R003",
                            title=f"Login from Known Malicious IP: {ip}",
                            severity=SeverityLevel.MEDIUM,
                            confidence=75,
                            evidence=[
                                f"Successful authentication from {ip}",
                                f"IP found in local IOC database: {matched_ioc.matched_ioc.description or 'No description'}"
                            ],
                            source_file=event.source_file,
                            source_event_id=str(event.id),
                            timestamp=event.timestamp,
                            recommendation=(
                                "Investigate account for compromise. Force password reset. "
                                "Review session activity. Block IP at perimeter."
                            ),
                            status=AlertStatus.NEW,
                            meta_data={
                                "source_ip": ip,
                                "ioc_description": matched_ioc.matched_ioc.description,
                                "username": event.normalized_data.get("username")
                            }
                        )
                        alerts.append(alert)
        
        return alerts
    
    def _rule_privilege_escalation(self, ctx: DetectionContext) -> List[AlertResponse]:
        """R004: Privilege escalation keywords in logs."""
        keywords = [
            "sudo", "su:", "pkexec", "runas", "root", "admin", "administrator",
            "unauthorized access", "permission denied", "access denied",
            "privilege escalation", "elevation", "bypass uac", "token manipulation"
        ]
        
        alerts = []
        for event in ctx.events:
            message = (event.message or "").lower()
            raw_str = str(event.raw_data or "").lower()
            normalized_str = str(event.normalized_data or "").lower()
            combined = f"{message} {raw_str} {normalized_str}"
            
            matches = [kw for kw in keywords if kw in combined]
            if matches:
                # Determine severity based on keywords
                critical_keywords = ["unauthorized access", "bypass uac", "token manipulation"]
                high_keywords = ["sudo", "su:", "pkexec", "runas", "privilege escalation"]
                
                if any(kw in combined for kw in critical_keywords):
                    severity = SeverityLevel.CRITICAL
                    confidence = 90
                elif any(kw in combined for kw in high_keywords):
                    severity = SeverityLevel.HIGH
                    confidence = 80
                else:
                    severity = SeverityLevel.MEDIUM
                    confidence = 65
                
                alert = AlertResponse(
                    rule_id="R004",
                    title=f"Privilege Escalation Indicator: {', '.join(matches[:3])}",
                    severity=severity,
                    confidence=confidence,
                    evidence=[
                        f"Keywords detected: {', '.join(matches)}",
                        f"Event type: {event.event_type.value}",
                        f"Source: {event.source_file}"
                    ],
                    source_file=event.source_file,
                    source_event_id=str(event.id),
                    timestamp=event.timestamp,
                    recommendation=(
                        "Review user activity for unauthorized privilege escalation. "
                        "Check sudo logs, Windows Event ID 4672/4673. Verify legitimate admin activity."
                    ),
                    status=AlertStatus.NEW,
                    metadata={
                        "matched_keywords": matches,
                        "event_type": event.event_type.value
                    }
                )
                alerts.append(alert)
        
        return alerts
    
    def _rule_suspicious_process(self, ctx: DetectionContext) -> List[AlertResponse]:
        """R005: Suspicious process execution patterns."""
        patterns = [
            (r"nc\s+-\w*[ecl]", "netcat listener/reverse shell"),
            (r"ncat\s+-\w*[ecl]", "ncat listener/reverse shell"),
            (r"socat\s+", "socat relay"),
            (r"powershell.*-enc", "encoded PowerShell command"),
            (r"powershell.*-e\s", "encoded PowerShell command"),
            (r"base64\s+-d", "base64 decode"),
            (r"wget\s+http", "wget download"),
            (r"curl\s+http.*\|", "curl pipe to shell"),
            (r"curl\s+.*-o\s+/tmp", "curl download to /tmp"),
            (r"/dev/tcp/", "bash TCP redirection"),
            (r"mshta\s+http", "mshta HTTP execution"),
            (r"regsvr32\s+/s\s+/u\s+http", "regsvr32 scriptlet execution"),
        ]
        
        import re
        alerts = []
        for event in ctx.events:
            if event.event_type.value != "process":
                continue
            
            message = (event.message or "").lower()
            command = (event.normalized_data or {}).get("command", "").lower()
            combined = f"{message} {command}"
            
            for pattern, desc in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    alert = AlertResponse(
                        rule_id="R005",
                        title=f"Suspicious Process: {desc}",
                        severity=SeverityLevel.MEDIUM,
                        confidence=70,
                        evidence=[
                            f"Pattern matched: {desc}",
                            f"Command: {command[:200]}" if command else f"Message: {message[:200]}"
                        ],
                        source_file=event.source_file,
                        source_event_id=str(event.id),
                        timestamp=event.timestamp,
                        recommendation=(
                            "Investigate process origin and parent process. Check for lateral movement. "
                            "Review command line arguments. Isolate host if confirmed malicious."
                        ),
                        status=AlertStatus.NEW,
                        meta_data={
                            "pattern": pattern,
                            "description": desc,
                            "command": command[:500] if command else None
                        }
                    )
                    alerts.append(alert)
                    break  # One alert per event
        
        return alerts
    
    def _rule_ioc_match(self, ctx: DetectionContext) -> List[AlertResponse]:
        """R006: IOC match from local database."""
        if not ctx.ioc_matches:
            return []
        
        alerts = []
        # Group matches by event
        from collections import defaultdict
        matches_by_event = defaultdict(list)
        for match in ctx.ioc_matches:
            # Find which event this IOC came from
            for event in ctx.events:
                event_str = f"{event.message or ''} {event.raw_data or ''} {event.normalized_data or ''}"
                if match.value in event_str:
                    matches_by_event[event.id].append(match)
                    break
        
        for event_id, matches in matches_by_event.items():
            event = next((e for e in ctx.events if e.id == event_id), None)
            if not event:
                continue
            
            # Determine highest severity from matches
            severity_map = {
                IOCType.IPV4: SeverityLevel.CRITICAL,
                IOCType.DOMAIN: SeverityLevel.HIGH,
                IOCType.URL: SeverityLevel.HIGH,
                IOCType.MD5: SeverityLevel.HIGH,
                IOCType.SHA1: SeverityLevel.HIGH,
                IOCType.SHA256: SeverityLevel.CRITICAL,
                IOCType.SHA512: SeverityLevel.CRITICAL,
            }
            
            max_severity = max(
                (severity_map.get(m.ioc_type, SeverityLevel.MEDIUM) for m in matches),
                key=lambda s: ["low", "medium", "high", "critical"].index(s.value)
            )
            
            alert = AlertResponse(
                rule_id="R006",
                title=f"IOC Match: {len(matches)} indicator(s) found",
                severity=max_severity,
                confidence=90,
                evidence=[
                    f"Matched {m.ioc_type.value}: {m.value} ({m.matched_ioc.description or 'no description'})"
                    for m in matches[:5]
                ],
                source_file=event.source_file,
                source_event_id=str(event.id),
                timestamp=event.timestamp,
                recommendation=(
                    "Investigate context of IOC appearance. Check for related alerts. "
                    "Block indicators at perimeter. Run endpoint scans for file hashes."
                ),
                status=AlertStatus.NEW,
                metadata={
                    "ioc_count": len(matches),
                    "ioc_types": list(set(m.ioc_type.value for m in matches)),
                    "matched_values": [m.value for m in matches]
                }
            )
            alerts.append(alert)
        
        return alerts
    
    def _rule_anomalous_time_access(self, ctx: DetectionContext) -> List[AlertResponse]:
        """R007: Successful login outside business hours."""
        start_hour = ctx.settings.get("business_hours_start", 8)
        end_hour = ctx.settings.get("business_hours_end", 18)
        
        alerts = []
        for event in ctx.events:
            if (event.event_type.value in ("login", "auth") and
                event.normalized_data):
                outcome = event.normalized_data.get("outcome", "").lower()
                if outcome in ("success", "accepted", "logged in"):
                    hour = event.timestamp.hour
                    if hour < start_hour or hour >= end_hour:
                        alert = AlertResponse(
                            rule_id="R007",
                            title=f"Off-Hours Login: {event.normalized_data.get('username', 'unknown')}",
                            severity=SeverityLevel.LOW,
                            confidence=50,
                            evidence=[
                                f"Login at {event.timestamp.strftime('%H:%M')} (outside {start_hour}:00-{end_hour}:00)",
                                f"User: {event.normalized_data.get('username', 'unknown')}",
                                f"Source IP: {event.normalized_data.get('source_ip', 'unknown')}"
                            ],
                            source_file=event.source_file,
                            source_event_id=str(event.id),
                            timestamp=event.timestamp,
                            recommendation=(
                                "Verify if off-hours access is expected for this user. "
                                "Check for compromised credentials or unauthorized access."
                            ),
                            status=AlertStatus.NEW,
                            meta_data={
                                "hour": hour,
                                "username": event.normalized_data.get("username"),
                                "source_ip": event.normalized_data.get("source_ip")
                            }
                        )
                        alerts.append(alert)
        
        return alerts
    
    def _rule_multiple_account_access(self, ctx: DetectionContext) -> List[AlertResponse]:
        """R008: Single IP accessing ≥5 different accounts in 10 minutes."""
        from collections import defaultdict
        
        threshold = ctx.settings.get("multi_account_threshold", 5)
        window_minutes = ctx.settings.get("multi_account_window_minutes", 10)
        window_seconds = window_minutes * 60
        
        # Group successful logins by IP
        logins_by_ip = defaultdict(list)
        for event in ctx.events:
            if (event.event_type.value in ("login", "auth") and
                event.normalized_data):
                outcome = event.normalized_data.get("outcome", "").lower()
                if outcome in ("success", "accepted", "logged in"):
                    ip = event.normalized_data.get("source_ip")
                    username = event.normalized_data.get("username")
                    if ip and username:
                        logins_by_ip[ip].append(event)
        
        alerts = []
        for ip, events in logins_by_ip.items():
            events.sort(key=lambda e: e.timestamp)
            
            for i in range(len(events)):
                window_start = events[i].timestamp
                window_events = [
                    e for e in events
                    if (e.timestamp - window_start).total_seconds() <= window_seconds
                ]
                
                unique_accounts = set(
                    e.normalized_data.get("username") 
                    for e in window_events if e.normalized_data
                )
                
                if len(unique_accounts) >= threshold:
                    alert = AlertResponse(
                        rule_id="R008",
                        title=f"Multiple Account Access from {ip}",
                        severity=SeverityLevel.HIGH,
                        confidence=85,
                        evidence=[
                            f"{len(unique_accounts)} different accounts accessed from {ip}",
                            f"Time window: {window_minutes} minutes",
                            f"Accounts: {', '.join(sorted(unique_accounts)[:10])}"
                        ],
                        source_file=window_events[0].source_file,
                        source_event_id=str(window_events[0].id),
                        timestamp=window_events[-1].timestamp,
                        recommendation=(
                            "Investigate for credential stuffing or password spray. "
                            "Force password reset for all affected accounts. Block IP. Enable MFA."
                        ),
                        status=AlertStatus.NEW,
                        meta_data={
                            "source_ip": ip,
                            "account_count": len(unique_accounts),
                            "accounts": list(unique_accounts),
                            "window_minutes": window_minutes
                        }
                    )
                    alerts.append(alert)
                    break
        
        return alerts
    
    def _rule_log_clearing(self, ctx: DetectionContext) -> List[AlertResponse]:
        """R009: Log clearing activity."""
        keywords = [
            "clear", "truncate", "> /var/log", "wevtutil cl", 
            "auditpol /clear", "Remove-Item.*\\.log", "del.*\\.log",
            "echo.*>.*\\.log", "history -c", "HISTFILE="
        ]
        
        import re
        alerts = []
        for event in ctx.events:
            message = (event.message or "").lower()
            command = (event.normalized_data or {}).get("command", "").lower()
            combined = f"{message} {command}"
            
            for kw in keywords:
                if re.search(kw.replace(".", r"\.").replace("*", ".*"), combined, re.IGNORECASE):
                    alert = AlertResponse(
                        rule_id="R009",
                        title=f"Log Clearing Activity Detected",
                        severity=SeverityLevel.CRITICAL,
                        confidence=90,
                        evidence=[
                            f"Keyword matched: {kw}",
                            f"Command: {command[:200]}" if command else f"Message: {message[:200]}"
                        ],
                        source_file=event.source_file,
                        source_event_id=str(event.id),
                        timestamp=event.timestamp,
                        recommendation=(
                            "IMMEDIATE: This indicates potential evidence destruction. "
                            "Isolate host. Preserve memory/image. Check for other anti-forensics activity. "
                            "Review recent alerts from this host."
                        ),
                        status=AlertStatus.NEW,
                        meta_data={
                            "matched_keyword": kw,
                            "command": command[:500] if command else None
                        }
                    )
                    alerts.append(alert)
                    break
        
        return alerts


# Import SeverityLevel and AlertStatus for use in rules
from app.schemas import SeverityLevel, AlertStatus