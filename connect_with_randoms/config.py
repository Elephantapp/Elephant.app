import os


class Config:
    """
    Central configuration for Connect With Randoms.

    All production-sensitive values are loaded from
    environment variables.
    """

    # =====================================================
    # FLASK
    # =====================================================

    SECRET_KEY = os.getenv(
        "FLASK_SECRET_KEY",
        "change-this-secret-key"
    )

    # =====================================================
    # DATABASE
    # =====================================================

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///elephant.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database connection pool settings.
    #
    # These become important when we move from SQLite
    # to PostgreSQL in production.

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # =====================================================
    # REDIS
    # =====================================================

    REDIS_URL = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0"
    )

    # =====================================================
    # SOCKET.IO
    # =====================================================

    SOCKETIO_MESSAGE_QUEUE = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0"
    )

    # =====================================================
    # SESSION
    # =====================================================

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"

    SESSION_COOKIE_SECURE = os.getenv(
        "SESSION_COOKIE_SECURE",
        "false"
    ).lower() == "true"

    # =====================================================
    # APPLICATION
    # =====================================================

    APP_NAME = os.getenv(
        "APP_NAME",
        "Connect With Randoms"
    )

    # =====================================================
    # MATCHMAKING
    # =====================================================

    MATCHMAKING_QUEUE = os.getenv(
        "MATCHMAKING_QUEUE",
        "random_users"
    )

    MATCH_TTL_SECONDS = int(
        os.getenv(
            "MATCH_TTL_SECONDS",
            "300"
        )
    )

    # =====================================================
    # PRESENCE
    # =====================================================

    PRESENCE_TTL_SECONDS = int(
        os.getenv(
            "PRESENCE_TTL_SECONDS",
            "90"
        )
    )

    # =====================================================
    # CORS
    # =====================================================

    CORS_ALLOWED_ORIGINS = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "*"
    )
