import hashlib
import secrets


def hash_token(token: str) -> str:
    """Hash the token using SHA256 (fast and secure for random tokens)."""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    """Securely compare token with stored hash."""
    return secrets.compare_digest(hash_token(token), token_hash)
