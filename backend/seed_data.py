"""Seed the database with demo IOC records for testing.

This script populates the local SQLite IOC database with safe,
documentation-only examples that use reserved IP ranges and
example domains. No real malicious indicators are used.

Run from the backend directory:
    cd backend
    python -m seed_data
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import init_db, SessionLocal
from app.models import IOC as IOCModel


# Safe demo IOCs using RFC 5737 documentation ranges and RFC 2606 example domains
DEMO_IOCS = [
    # IPs from documentation ranges (TEST-NET-1, TEST-NET-2, TEST-NET-3)
    {"ioc_type": "ipv4", "value": "192.0.2.1", "description": "TEST-NET-1 example host (RFC 5737)", "source": "demo", "tags": ["demo", "test-net"]},
    {"ioc_type": "ipv4", "value": "192.0.2.50", "description": "TEST-NET-1 example range", "source": "demo", "tags": ["demo", "test-net"]},
    {"ioc_type": "ipv4", "value": "198.51.100.50", "description": "TEST-NET-2 example range (RFC 5737)", "source": "demo", "tags": ["demo", "test-net"]},
    {"ioc_type": "ipv4", "value": "203.0.113.100", "description": "TEST-NET-3 example range (RFC 5737)", "source": "demo", "tags": ["demo", "test-net"]},
    
    # Example domains from RFC 2606
    {"ioc_type": "domain", "value": "malicious.example.com", "description": "Example malicious domain for testing", "source": "demo", "tags": ["demo", "example"]},
    {"ioc_type": "domain", "value": "evil.example.net", "description": "Example evil domain for IOC testing", "source": "demo", "tags": ["demo", "example"]},
    {"ioc_type": "domain", "value": "c2.example.org", "description": "Example C2 domain for demo", "source": "demo", "tags": ["demo", "c2"]},
    {"ioc_type": "domain", "value": "phish.example.com", "description": "Example phishing domain for testing", "source": "demo", "tags": ["demo", "phishing"]},
    
    # Example URLs
    {"ioc_type": "url", "value": "http://malicious.example.com/payload.sh", "description": "Example malicious URL for testing", "source": "demo", "tags": ["demo", "malware"]},
    {"ioc_type": "url", "value": "http://evil.example.net/steal", "description": "Example data exfil URL", "source": "demo", "tags": ["demo", "exfil"]},
    
    # Example file hashes (not real malware - just test strings)
    {"ioc_type": "md5", "value": "d41d8cd98f00b204e9800998ecf8427e", "description": "MD5 of empty file (demo test)", "source": "demo", "tags": ["demo", "test"]},
    {"ioc_type": "sha256", "value": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "description": "SHA256 of empty file (demo test)", "source": "demo", "tags": ["demo", "test"]},
    {"ioc_type": "sha1", "value": "da39a3ee5e6b4b0d3255bfef95601890afd80709", "description": "SHA1 of empty file (demo test)", "source": "demo", "tags": ["demo", "test"]},
    
    # Additional demo IPs for the sample log scenarios
    {"ioc_type": "ipv4", "value": "192.0.2.200", "description": "Demo suspicious IP for brute-force scenario", "source": "demo", "tags": ["demo", "brute-force"]},
    {"ioc_type": "ipv4", "value": "198.51.100.200", "description": "Demo suspicious IP for unauthorized access scenario", "source": "demo", "tags": ["demo", "unauthorized"]},
]


def seed_database():
    """Seed the IOC database with demo records."""
    init_db()
    
    db = SessionLocal()
    try:
        # Check if already seeded
        existing_count = db.query(IOCModel).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} IOC records. Skipping seed.")
            return
        
        # Insert demo IOCs
        for ioc_data in DEMO_IOCS:
            ioc = IOCModel(
                ioc_type=ioc_data["ioc_type"],
                value=ioc_data["value"],
                description=ioc_data["description"],
                source=ioc_data["source"],
                tags=ioc_data["tags"],
                is_active=True
            )
            db.add(ioc)
        
        db.commit()
        print(f"Successfully seeded {len(DEMO_IOCS)} demo IOC records.")
        
        # Verify
        total = db.query(IOCModel).count()
        print(f"Total IOCs in database: {total}")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()