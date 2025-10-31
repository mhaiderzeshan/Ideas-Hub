from passlib.context import CryptContext
import hashlib
import secrets


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# token
def hash_token(token: str) -> str:
    """Hash the token using SHA256 (fast and secure for random tokens)."""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    """Securely compare token with stored hash."""
    return secrets.compare_digest(hash_token(token), token_hash)


# password
def hashed_password(password: str) -> str:
    """convert the plain password into a hashed password"""
    return pwd_context.hash(password)


def verify_hashed_password(plain_password: str, hashed_password: str) -> bool:
    """verify the plain password against the hashed password"""
    return pwd_context.verify(plain_password, hashed_password)
