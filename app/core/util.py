import asyncio
from passlib.context import CryptContext
import hashlib
import secrets


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    return secrets.compare_digest(hash_token(token), token_hash)


def hashed_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_hashed_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def async_hashed_password(password: str) -> str:
    """
    Run the synchronous, CPU-bound password hashing in a separate thread.
    """
    return await asyncio.to_thread(hashed_password, password)


async def async_verify_hashed_password(plain_password: str, hashed_password_str: str) -> bool:
    """
    Run the synchronous, CPU-bound password verification in a separate thread.
    """
    return await asyncio.to_thread(verify_hashed_password, plain_password, hashed_password_str)
