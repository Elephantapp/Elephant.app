import json
import time
import uuid

from .redis_service import get_redis


QUEUE_KEY = "random_match_queue"
USER_KEY_PREFIX = "random_user:"
PAIR_KEY_PREFIX = "random_pair:"
USER_TTL = 300


def user_key(sid):
    return f"{USER_KEY_PREFIX}{sid}"


def pair_key(sid):
    return f"{PAIR_KEY_PREFIX}{sid}"


def register_user(sid, user_data):
    redis_client = get_redis()

    data = {
        "sid": sid,
        "name": user_data.get("name", "Anonymous"),
        "email": user_data.get("email", ""),
        "created_at": time.time(),
    }

    redis_client.setex(
        user_key(sid),
        USER_TTL,
        json.dumps(data)
    )


def remove_user(sid):
    redis_client = get_redis()

    redis_client.delete(
        user_key(sid)
    )

    redis_client.zrem(
        QUEUE_KEY,
        sid
    )


def get_user(sid):
    redis_client = get_redis()

    value = redis_client.get(
        user_key(sid)
    )

    if not value:
        return None

    try:
        return json.loads(value)
    except Exception:
        return None


def get_partner(sid):
    redis_client = get_redis()

    return redis_client.get(
        pair_key(sid)
    )


def remove_pair(sid):
    redis_client = get_redis()

    partner = get_partner(sid)

    redis_client.delete(
        pair_key(sid)
    )

    if partner:
        redis_client.delete(
            pair_key(partner)
        )

    return partner


def add_to_queue(sid):
    redis_client = get_redis()

    register_time = time.time()

    redis_client.zadd(
        QUEUE_KEY,
        {
            sid: register_time
        }
    )

    return True


def remove_from_queue(sid):
    redis_client = get_redis()

    redis_client.zrem(
        QUEUE_KEY,
        sid
    )


def find_waiting_user(current_sid):
    redis_client = get_redis()

    candidates = redis_client.zrange(
        QUEUE_KEY,
        0,
        49
    )

    for candidate in candidates:

        if candidate == current_sid:
            continue

        if get_user(candidate) is None:
            redis_client.zrem(
                QUEUE_KEY,
                candidate
            )
            continue

        if get_partner(candidate):
            redis_client.zrem(
                QUEUE_KEY,
                candidate
            )
            continue

        removed = redis_client.zrem(
            QUEUE_KEY,
            candidate
        )

        if removed == 1:
            return candidate

    return None


def create_pair(sid_a, sid_b):
    redis_client = get_redis()

    pair_id = str(uuid.uuid4())

    redis_client.set(
        pair_key(sid_a),
        sid_b
    )

    redis_client.set(
        pair_key(sid_b),
        sid_a
    )

    return pair_id


def match_user(sid, user_data):
    register_user(
        sid,
        user_data
    )

    existing_partner = get_partner(sid)

    if existing_partner:
        return {
            "status": "already_connected",
            "partner_sid": existing_partner
        }

    partner_sid = find_waiting_user(
        sid
    )

    if not partner_sid:
        add_to_queue(sid)

        return {
            "status": "waiting"
        }

    create_pair(
        sid,
        partner_sid
    )

    return {
        "status": "matched",
        "partner_sid": partner_sid
    }


def end_match(sid):
    redis_client = get_redis()

    remove_from_queue(
        sid
    )

    partner = remove_pair(
        sid
    )

    return partner