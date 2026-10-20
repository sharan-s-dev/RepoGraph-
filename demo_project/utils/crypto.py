"""
Cryptographic utility functions and security hashing helpers.
"""
import hashlib
import secrets

def hash_secret(value: str) -> str:
    """Generate SHA256 hex digest for a secret string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def generate_token(prefix: str = "tok") -> str:
    """Generate high-entropy random token."""
    return f"{prefix}_{secrets.token_hex(16)}"
