import redis.asyncio as redis
from fastapi import Request, HTTPException, status
from app.core.config import settings

REDIS_URL = settings.REDIS_URL

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

RATE_LIMIT = 5
TIME_WINDOW = 60  # seconds


async def rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    redis_key = f"rate_limit:{client_ip}"

    async with redis_client.pipeline() as pipe:
        # Queue up the commands. These don't send the request yet.
        pipe.incr(redis_key)
        pipe.expire(redis_key, TIME_WINDOW)

        # Execute the pipeline and get the results back in a list
        results = await pipe.execute()

    # The result of the first command (INCR) is the first item in the list
    current_count = results[0]

    # If exceeded
    if current_count > RATE_LIMIT:
        ttl = await redis_client.ttl(redis_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Try again in {ttl if ttl > 0 else TIME_WINDOW} seconds."
        )
