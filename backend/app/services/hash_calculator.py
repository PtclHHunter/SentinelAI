import hashlib
import os
from pathlib import Path
from typing import BinaryIO
from dataclasses import dataclass


@dataclass
class HashResult:
    """Result of hash calculation."""
    md5: str
    sha1: str
    sha256: str
    sha512: str
    file_size: int
    filename: str


class HashCalculator:
    """Calculate file hashes using Python's hashlib."""
    
    # Chunk size for reading large files
    CHUNK_SIZE = 8192
    
    def __init__(self):
        pass
    
    def calculate_file_hashes(self, file_path: Path) -> HashResult:
        """Calculate all hashes for a file."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        # Initialize hash objects
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()
        sha256_hash = hashlib.sha256()
        sha512_hash = hashlib.sha512()
        
        file_size = 0
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(self.CHUNK_SIZE):
                file_size += len(chunk)
                md5_hash.update(chunk)
                sha1_hash.update(chunk)
                sha256_hash.update(chunk)
                sha512_hash.update(chunk)
        
        return HashResult(
            md5=md5_hash.hexdigest(),
            sha1=sha1_hash.hexdigest(),
            sha256=sha256_hash.hexdigest(),
            sha512=sha512_hash.hexdigest(),
            file_size=file_size,
            filename=file_path.name
        )
    
    def calculate_stream_hashes(self, stream: BinaryIO, filename: str) -> HashResult:
        """Calculate hashes from a file-like object."""
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()
        sha256_hash = hashlib.sha256()
        sha512_hash = hashlib.sha512()
        
        file_size = 0
        
        # Save position
        pos = stream.tell()
        stream.seek(0)
        
        try:
            while chunk := stream.read(self.CHUNK_SIZE):
                file_size += len(chunk)
                md5_hash.update(chunk)
                sha1_hash.update(chunk)
                sha256_hash.update(chunk)
                sha512_hash.update(chunk)
        finally:
            # Restore position
            stream.seek(pos)
        
        return HashResult(
            md5=md5_hash.hexdigest(),
            sha1=sha1_hash.hexdigest(),
            sha256=sha256_hash.hexdigest(),
            sha512=sha512_hash.hexdigest(),
            file_size=file_size,
            filename=filename
        )
    
    def verify_hash(self, file_path: Path, expected_hash: str, algorithm: str = "sha256") -> bool:
        """Verify a file against an expected hash."""
        result = self.calculate_file_hashes(file_path)
        
        algo_map = {
            "md5": result.md5,
            "sha1": result.sha1,
            "sha256": result.sha256,
            "sha512": result.sha512,
        }
        
        actual = algo_map.get(algorithm.lower())
        if not actual:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        return actual.lower() == expected_hash.lower()


def calculate_string_hashes(text: str) -> HashResult:
    """Calculate hashes for a string (for testing)."""
    md5_hash = hashlib.md5(text.encode()).hexdigest()
    sha1_hash = hashlib.sha1(text.encode()).hexdigest()
    sha256_hash = hashlib.sha256(text.encode()).hexdigest()
    sha512_hash = hashlib.sha512(text.encode()).hexdigest()
    
    return HashResult(
        md5=md5_hash,
        sha1=sha1_hash,
        sha256=sha256_hash,
        sha512=sha512_hash,
        file_size=len(text.encode()),
        filename="string_input"
    )