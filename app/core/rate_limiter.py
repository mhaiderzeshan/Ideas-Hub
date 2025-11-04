import redis.asyncio as redis
from fastapi import Request, HTTPException, status
from app.core.config import settings


REDIS_URL = settings.REDIS_URL

# Redis configuration
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

RATE_LIMIT = 5
TIME_WINDOW = 60  # seconds


async def rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    redis_key = f"rate_limit:{client_ip}"

    # Increment the count for this IP
    current_count = await redis_client.incr(redis_key)

    # If first request, set expiry window
    if current_count == 1:
        await redis_client.expire(redis_key, TIME_WINDOW)

    # If exceeded
    if current_count > RATE_LIMIT:
        ttl = await redis_client.ttl(redis_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Try again in {ttl} seconds."
        )
