import re
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass

from app.schemas import IOCType


@dataclass
class ExtractedIOC:
    ioc_type: IOCType
    value: str
    context: str  # Surrounding text (up to 100 chars before/after)


class IOCExtractor:
    """Extract IOCs from text using regex patterns."""
    
    # IPv4 pattern (excluding reserved ranges for detection, but we extract all)
    IPV4_PATTERN = re.compile(
        r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    )
    
    # Domain pattern
    DOMAIN_PATTERN = re.compile(
        r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
    )
    
    # URL pattern
    URL_PATTERN = re.compile(
        r'\bhttps?://[^\s/$.?#].[^\s]*\b'
    )
    
    # Hash patterns
    MD5_PATTERN = re.compile(r'\b[a-fA-F0-9]{32}\b')
    SHA1_PATTERN = re.compile(r'\b[a-fA-F0-9]{40}\b')
    SHA256_PATTERN = re.compile(r'\b[a-fA-F0-9]{64}\b')
    SHA512_PATTERN = re.compile(r'\b[a-fA-F0-9]{128}\b')
    
    # Patterns that are likely NOT IOCs (false positive reduction)
    FALSE_POSITIVE_PATTERNS = [
        # Version numbers
        re.compile(r'\b\d+\.\d+\.\d+\.\d+\b'),  # 1.2.3.4 version
        # Timestamps
        re.compile(r'\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}\b'),
        # UUIDs
        re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.IGNORECASE),
        # MAC addresses
        re.compile(r'\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b'),
    ]
    
    # Reserved/documentation IP ranges (RFC 5737, RFC 3849, etc.)
    RESERVED_IP_RANGES = [
        (0x00000000, 0x00FFFFFF),      # 0.0.0.0/8
        (0x0A000000, 0x0AFFFFFF),      # 10.0.0.0/8
        (0x64400000, 0x647FFFFF),      # 100.64.0.0/10
        (0x7F000000, 0x7FFFFFFF),      # 127.0.0.0/8
        (0xA9FE0000, 0xA9FEFFFF),      # 169.254.0.0/16
        (0xAC100000, 0xAC1FFFFF),      # 172.16.0.0/12
        (0xC0000000, 0xC00000FF),      # 192.0.0.0/24
        (0xC0000200, 0xC00002FF),      # 192.0.2.0/24 (TEST-NET-1)
        (0xC0586300, 0xC05863FF),      # 192.88.99.0/24
        (0xC0A80000, 0xC0A8FFFF),      # 192.168.0.0/16
        (0xC6120000, 0xC613FFFF),      # 198.18.0.0/15
        (0xC6336400, 0xC63364FF),      # 198.51.100.0/24 (TEST-NET-2)
        (0xCB007100, 0xCB0071FF),      # 203.0.113.0/24 (TEST-NET-3)
        (0xE0000000, 0xEFFFFFFF),      # 224.0.0.0/4 (multicast)
        (0xF0000000, 0xFFFFFFFF),      # 240.0.0.0/4 (reserved)
    ]
    
    # Example domains (RFC 2606)
    EXAMPLE_DOMAINS = {
        "example.com", "example.org", "example.net", "example.edu",
        "localhost", "localhost.localdomain", "local", "test", "invalid",
        "example", "localhost.local"
    }
    
    def __init__(self):
        # Compile all hash patterns
        self.hash_patterns = {
            IOCType.MD5: self.MD5_PATTERN,
            IOCType.SHA1: self.SHA1_PATTERN,
            IOCType.SHA256: self.SHA256_PATTERN,
            IOCType.SHA512: self.SHA512_PATTERN,
        }
    
    def extract_all(self, text: str) -> Dict[IOCType, List[ExtractedIOC]]:
        """Extract all IOC types from text."""
        results = {
            IOCType.IPV4: [],
            IOCType.DOMAIN: [],
            IOCType.URL: [],
            IOCType.MD5: [],
            IOCType.SHA1: [],
            IOCType.SHA256: [],
            IOCType.SHA512: [],
        }
        
        # Extract each type
        results[IOCType.IPV4] = self._extract_ipv4(text)
        results[IOCType.DOMAIN] = self._extract_domains(text)
        results[IOCType.URL] = self._extract_urls(text)
        
        for ioc_type, pattern in self.hash_patterns.items():
            results[ioc_type] = self._extract_hashes(text, pattern, ioc_type)
        
        return results
    
    def _extract_ipv4(self, text: str) -> List[ExtractedIOC]:
        """Extract IPv4 addresses."""
        results = []
        seen = set()
        for match in self.IPV4_PATTERN.finditer(text):
            ip = match.group()
            
            if ip in seen:
                continue
            seen.add(ip)
            
            # Skip version-like patterns (e.g., 1.2.3.4 as version)
            if self._looks_like_version(text, match.start()):
                continue
            
            context = self._get_context(text, match.start(), match.end())
            results.append(ExtractedIOC(
                ioc_type=IOCType.IPV4,
                value=ip,
                context=context
            ))
        
        return results
    
    def _extract_domains(self, text: str) -> List[ExtractedIOC]:
        """Extract domain names."""
        results = []
        for match in self.DOMAIN_PATTERN.finditer(text):
            domain = match.group().lower()
            
            # Skip example domains
            if domain in self.EXAMPLE_DOMAINS:
                continue
            
            # Skip if it looks like a file path or email
            if self._is_false_positive_domain(text, match.start(), match.end()):
                continue
            
            # Skip common TLDs that are likely not malicious in context
            # But we still extract them - filtering happens at match time
            
            context = self._get_context(text, match.start(), match.end())
            results.append(ExtractedIOC(
                ioc_type=IOCType.DOMAIN,
                value=domain,
                context=context
            ))
        
        return results
    
    def _extract_urls(self, text: str) -> List[ExtractedIOC]:
        """Extract URLs."""
        results = []
        for match in self.URL_PATTERN.finditer(text):
            url = match.group()
            
            # Skip data URLs
            if url.startswith("data:"):
                continue
            
            context = self._get_context(text, match.start(), match.end())
            results.append(ExtractedIOC(
                ioc_type=IOCType.URL,
                value=url,
                context=context
            ))
        
        return results
    
    def _extract_hashes(self, text: str, pattern: re.Pattern, ioc_type: IOCType) -> List[ExtractedIOC]:
        """Extract hash values."""
        results = []
        for match in pattern.finditer(text):
            hash_val = match.group().lower()
            
            # Skip if it looks like a false positive
            if self._is_false_positive_hash(text, match.start(), match.end()):
                continue
            
            context = self._get_context(text, match.start(), match.end())
            results.append(ExtractedIOC(
                ioc_type=ioc_type,
                value=hash_val,
                context=context
            ))
        
        return results
    
    def _get_context(self, text: str, start: int, end: int, window: int = 100) -> str:
        """Get surrounding context for an IOC match."""
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)
        context = text[ctx_start:ctx_end]
        # Clean up whitespace
        context = re.sub(r'\s+', ' ', context).strip()
        return context
    
    def _is_reserved_ip(self, ip: str) -> bool:
        """Check if IP is in reserved/documentation ranges."""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            ip_int = (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])
            
            for start, end in self.RESERVED_IP_RANGES:
                if start <= ip_int <= end:
                    return True
        except (ValueError, IndexError):
            pass
        return False
    
    def _looks_like_version(self, text: str, pos: int) -> bool:
        """Check if IP-like pattern is actually a version number."""
        # Look for version keywords nearby
        window = text[max(0, pos-30):pos+30].lower()
        version_keywords = ["version", "v.", "ver", "release", "build", "update"]
        return any(kw in window for kw in version_keywords)
    
    def _is_false_positive_domain(self, text: str, start: int, end: int) -> bool:
        """Check if domain match is likely a false positive."""
        # Check if it's part of an email
        if start > 0 and text[start-1] == '@':
            return True
        if end < len(text) and text[end] in ('/', '\\', ':', '.'):
            return True
        
        # Check if it's a file extension-like pattern
        context = text[max(0, start-10):end+10]
        if re.search(r'\.(exe|dll|pdf|doc|txt|log|json|csv|xml|html?|js|css)\b', context, re.IGNORECASE):
            # Might be a filename
            pass  # Still extract, let matching decide
        
        return False
    
    def _is_false_positive_hash(self, text: str, start: int, end: int) -> bool:
        """Check if hash match is likely a false positive."""
        # Check for version-like context
        context = text[max(0, start-20):end+20].lower()
        if any(kw in context for kw in ["version", "ver=", "v=", "build", "release"]):
            return True
        
        # Check for UUID context (already filtered by pattern but double-check)
        if re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', context):
            return True
        
        return False
    
    def extract_unique_values(self, text: str) -> Dict[IOCType, Set[str]]:
        """Extract unique IOC values (without context)."""
        extracted = self.extract_all(text)
        return {k: {ioc.value for ioc in v} for k, v in extracted.items()}


def extract_iocs_from_events(events: List[Dict]) -> Dict[IOCType, Set[str]]:
    """Extract IOCs from a list of event dictionaries."""
    extractor = IOCExtractor()
    all_iocs = {t: set() for t in IOCType}
    
    for event in events:
        # Combine all text fields
        text_parts = []
        for key, value in event.items():
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, dict):
                text_parts.append(str(value))
            elif isinstance(value, list):
                text_parts.append(" ".join(str(v) for v in value))
        
        combined_text = " ".join(text_parts)
        event_iocs = extractor.extract_unique_values(combined_text)
        
        for ioc_type, values in event_iocs.items():
            all_iocs[ioc_type].update(values)
    
    return all_iocs