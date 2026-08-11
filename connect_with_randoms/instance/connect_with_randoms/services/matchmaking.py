import json
import time
import uuid

from .redis_service import get_redis


QUEUE_KEY = "random_match_queue"
USER_KEY_PREFIX = "random_user:"
PAIR_KEY_PREFIX = "random_pair:"
USER_TTL = 300


# =========================================================
# KEYS
# =========================================================

def user_key(sid):
    return f"{USER_KEY_PREFIX}{sid}"


def pair_key(sid):
    return f"{PAIR_KEY_PREFIX}{sid}"


# =========================================================
# REGISTER USER
# =========================================================

def register_user(sid, user_data):

    redis_client = get_redis()

    data = {
        "sid": sid,
        "name": user_data.get("name", "Anonymous"),
        "email": user_data.get("email", ""),
        "is_premium": bool(user_data.get("is_premium", False)),
        "gender": user_data.get("gender", ""),
        "created_at": time.time(),
    }

    redis_client.setex(
        user_key(sid),
        USER_TTL,
        json.dumps(data)
    )

    return data


# =========================================================
# REMOVE USER
# =========================================================

def remove_user(sid):

    redis_client = get_redis()

    redis_client.delete(
        user_key(sid)
    )

    redis_client.zrem(
        QUEUE_KEY,
        sid
    )


# =========================================================
# GET USER
# =========================================================

def get_user(sid):

    redis_client = get_redis()

    value = redis_client.get(
        user_key(sid)
    )

    if not value:
        return None

    try:
        if isinstance(value, bytes):
            value = value.decode("utf-8")

        return json.loads(value)

    except Exception:
        return None


# =========================================================
# GET PARTNER
# =========================================================

def get_partner(sid):

    redis_client = get_redis()

    partner = redis_client.get(
        pair_key(sid)
    )

    if not partner:
        return None

    if isinstance(partner, bytes):
        partner = partner.decode("utf-8")

    return partner


# =========================================================
# REMOVE PAIR
# =========================================================

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


# =========================================================
# ADD TO QUEUE
# =========================================================

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


# =========================================================
# REMOVE FROM QUEUE
# =========================================================

def remove_from_queue(sid):

    redis_client = get_redis()

    redis_client.zrem(
        QUEUE_KEY,
        sid
    )


# =========================================================
# FIND WAITING USER
# =========================================================

def find_waiting_user(current_sid):

    redis_client = get_redis()

    current_user = get_user(current_sid)

    if not current_user:
        return None

    current_is_premium = bool(
        current_user.get("is_premium", False)
    )

    candidates = redis_client.zrange(
        QUEUE_KEY,
        0,
        49
    )

    for candidate in candidates:

        if isinstance(candidate, bytes):
            candidate = candidate.decode("utf-8")

        if candidate == current_sid:
            continue

        candidate_user = get_user(candidate)

        if candidate_user is None:

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

        # -------------------------------------------------
        # PREMIUM PRIORITY
        # -------------------------------------------------
        #
        # Premium users are allowed to match normally.
        # We do not block free users from matching.
        #
        # Premium priority is handled by checking premium
        # candidates first in the queue.
        # -------------------------------------------------

        candidate_is_premium = bool(
            candidate_user.get("is_premium", False)
        )

        if current_is_premium and candidate_is_premium:
            removed = redis_client.zrem(
                QUEUE_KEY,
                candidate
            )

            if removed == 1:
                return candidate

    # -----------------------------------------------------
    # NORMAL MATCHING
    # -----------------------------------------------------

    for candidate in candidates:

        if isinstance(candidate, bytes):
            candidate = candidate.decode("utf-8")

        if candidate == current_sid:
            continue

        candidate_user = get_user(candidate)

        if candidate_user is None:
            continue

        if get_partner(candidate):
            continue

        removed = redis_client.zrem(
            QUEUE_KEY,
            candidate
        )

        if removed == 1:
            return candidate

    return None


# =========================================================
# CREATE PAIR
# =========================================================

def create_pair(sid_a, sid_b):

    redis_client = get_redis()

    pair_id = str(
        uuid.uuid4()
    )

    redis_client.set(
        pair_key(sid_a),
        sid_b
    )

    redis_client.set(
        pair_key(sid_b),
        sid_a
    )

    return pair_id


# =========================================================
# MATCH USER
# =========================================================

def match_user(sid, user_data):

    registered_user = register_user(
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

        add_to_queue(
            sid
        )

        return {
            "status": "waiting",
            "is_premium": registered_user.get(
                "is_premium",
                False
            )
        }

    create_pair(
        sid,
        partner_sid
    )

    return {
        "status": "matched",
        "partner_sid": partner_sid,
        "is_premium": registered_user.get(
            "is_premium",
            False
        )
    }


# =========================================================
# END MATCH
# =========================================================

def end_match(sid):

    redis_client = get_redis()

    remove_from_queue(
        sid
    )

    partner = remove_pair(
        sid
    )

    return partner