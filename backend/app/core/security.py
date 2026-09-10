import re
from pathlib import Path
from fastapi import HTTPException, UploadFile


MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".log", ".txt", ".json", ".csv"}
ALLOWED_MIME_PREFIXES = ("text/", "application/json", "application/csv")


# File signature (magic bytes) for basic validation
FILE_SIGNATURES = {
    ".json": [b"{", b"["],  # JSON starts with { or [
    ".csv": [],  # CSV has no fixed signature
    ".log": [],  # Log files have no fixed signature
    ".txt": [],  # Text files have no fixed signature
}


def validate_file_extension(filename: str) -> None:
    """Validate file extension is allowed."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )


def validate_file_size(file: UploadFile) -> None:
    """Validate file size is within limits."""
    # Check content-length header if available
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size {file.size} bytes exceeds maximum {MAX_FILE_SIZE} bytes"
        )


def validate_file_signature(file: UploadFile, filename: str) -> None:
    """Basic file signature validation."""
    ext = Path(filename).suffix.lower()
    expected_signatures = FILE_SIGNATURES.get(ext, [])
    
    if not expected_signatures:
        return  # No signature check for this extension
    
    # Read first few bytes
    file.file.seek(0)
    header = file.file.read(8)
    file.file.seek(0)
    
    if not any(header.startswith(sig) for sig in expected_signatures):
        raise HTTPException(
            status_code=400,
            detail=f"File content does not match expected format for {ext}"
        )


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    # Remove path components
    name = Path(filename).name
    # Remove dangerous characters
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)
    # Limit length
    if len(name) > 255:
        name = name[:255]
    return name or "upload"


def validate_ipv4(ip: str) -> bool:
    """Validate IPv4 address format."""
    pattern = r'^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$'
    return bool(re.match(pattern, ip))


def validate_domain(domain: str) -> bool:
    """Validate domain name format."""
    if len(domain) > 253:
        return False
    pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    return bool(re.match(pattern, domain))


def validate_url(url: str) -> bool:
    """Validate URL format."""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def validate_hash(value: str, hash_type: str) -> bool:
    """Validate hash format."""
    patterns = {
        "md5": r'^[a-fA-F0-9]{32}$',
        "sha1": r'^[a-fA-F0-9]{40}$',
        "sha256": r'^[a-fA-F0-9]{64}$',
        "sha512": r'^[a-fA-F0-9]{128}$',
    }
    pattern = patterns.get(hash_type.lower())
    if not pattern:
        return False
    return bool(re.match(pattern, value))