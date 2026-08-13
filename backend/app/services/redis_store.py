import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None
_redis_available: Optional[bool] = None


async def _check_redis() -> bool:
    global _redis_available
    if _redis_available is not None:
        return _redis_available
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        await r.ping()
        await r.aclose()
        _redis_available = True
        logger.info("Redis available at %s:%d", settings.REDIS_HOST, settings.REDIS_PORT)
    except Exception as e:
        _redis_available = False
        logger.warning("Redis unavailable at %s:%d: %s", settings.REDIS_HOST, settings.REDIS_PORT, e)
    return _redis_available


async def get_redis() -> Optional[redis.Redis]:
    global _redis_client
    if not await _check_redis():
        return None
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await _redis_client.ping()
            logger.info("Redis connected %s:%d db=%d", settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
        except Exception as e:
            _redis_client = None
            logger.error("Redis connection failed: %s", e)
            return None
    return _redis_client


async def close_redis() -> None:
    global _redis_client, _redis_available
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
    _redis_available = None
    logger.info("Redis connection closed")


SESSION_PREFIX = "session:"


async def create_session(user_id: int, ttl: int | None = None) -> str:
    r = await get_redis()
    if r is None:
        return ""
    session_id = uuid.uuid4().hex
    key = f"{SESSION_PREFIX}{session_id}"
    data = {
        "user_id": str(user_id),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await r.hset(key, mapping=data)
    ttl = ttl if ttl is not None else settings.SESSION_TTL
    await r.expire(key, ttl)
    logger.debug("Session created sid=%s user=%d ttl=%d", session_id, user_id, ttl)
    return session_id


async def get_session(session_id: str) -> Optional[dict]:
    r = await get_redis()
    if r is None:
        return None
    key = f"{SESSION_PREFIX}{session_id}"
    data = await r.hgetall(key)
    if not data:
        return None
    return dict(data)


async def delete_session(session_id: str) -> bool:
    r = await get_redis()
    if r is None:
        return False
    key = f"{SESSION_PREFIX}{session_id}"
    deleted = await r.delete(key)
    if deleted:
        logger.debug("Session deleted sid=%s", session_id)
    return bool(deleted)


async def delete_user_sessions(user_id: int) -> int:
    r = await get_redis()
    if r is None:
        return 0
    count = 0
    cursor = 0
    while True:
        cursor, keys = await r.scan(cursor, f"{SESSION_PREFIX}*", 100)
        for key in keys:
            uid = await r.hget(key, "user_id")
            if uid == str(user_id):
                await r.delete(key)
                count += 1
        if cursor == 0:
            break
    if count:
        logger.info("Deleted %d sessions for user_id=%d", count, user_id)
    return count
