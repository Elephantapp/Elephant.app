import os

from dotenv import load_dotenv


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# DATABASE URL
# =========================================================

database_url = os.getenv("DATABASE_URL")


if database_url:

    if database_url.startswith("postgres://"):

        database_url = database_url.replace(
            "postgres://",
            "postgresql://",
            1
        )

else:

    database_url = "sqlite:///elephant.db"


# =========================================================
# APPLICATION CONFIG
# =========================================================

class Config:

    # -----------------------------------------------------
    # SECRET KEY
    # -----------------------------------------------------

    SECRET_KEY = os.getenv(
        "FLASK_SECRET_KEY",
        "change-this-secret-key"
    )


    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

    SQLALCHEMY_DATABASE_URI = database_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False


    # -----------------------------------------------------
    # SESSION COOKIE
    # -----------------------------------------------------

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"

    SESSION_COOKIE_SECURE = (
        os.getenv(
            "SESSION_COOKIE_SECURE",
            "false"
        ).lower()
        == "true"
    )


    # -----------------------------------------------------
    # SQLALCHEMY ENGINE OPTIONS
    # -----------------------------------------------------

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }


    # -----------------------------------------------------
    # GOOGLE OAUTH
    # -----------------------------------------------------

    GOOGLE_CLIENT_ID = os.getenv(
        "GOOGLE_CLIENT_ID"
    )

    GOOGLE_CLIENT_SECRET = os.getenv(
        "GOOGLE_CLIENT_SECRET"
    )


    # -----------------------------------------------------
    # REDIS
    # -----------------------------------------------------

    REDIS_URL = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0"
    )