import os
import redis

from dotenv import load_dotenv

load_dotenv()


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0"
)


redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    health_check_interval=30,
)


def redis_available():
    try:
        return redis_client.ping()
    except Exception as error:
        print("REDIS ERROR:", repr(error))
        return False


def get_redis():
    return redis_client