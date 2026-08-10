import time

from .redis_service import get_redis


PRESENCE_PREFIX = "presence:"
PRESENCE_TTL = 90


def presence_key(sid):
    return f"{PRESENCE_PREFIX}{sid}"


def set_online(sid):
    redis_client = get_redis()

    redis_client.setex(
        presence_key(sid),
        PRESENCE_TTL,
        str(int(time.time()))
    )


def refresh_online(sid):
    redis_client = get_redis()

    redis_client.expire(
        presence_key(sid),
        PRESENCE_TTL
    )


def set_offline(sid):
    redis_client = get_redis()

    redis_client.delete(
        presence_key(sid)
    )


def is_online(sid):
    redis_client = get_redis()

    return bool(
        redis_client.exists(
            presence_key(sid)
        )
    )


def online_count():
    redis_client = get_redis()

    keys = redis_client.keys(
        f"{PRESENCE_PREFIX}*"
    )

    return len(keys)