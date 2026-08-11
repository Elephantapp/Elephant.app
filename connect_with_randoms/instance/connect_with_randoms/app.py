import os
from datetime import date, datetime

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    session,
    request,
)

from flask_socketio import SocketIO

from authlib.integrations.flask_client import OAuth

from dotenv import load_dotenv

from config import Config

from models.user import db, User

from sockets.video import register_video_events


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# APP
# =========================================================

app = Flask(__name__)

app.config.from_object(Config)

app.secret_key = app.config["SECRET_KEY"]


# =========================================================
# DATABASE
# =========================================================

db.init_app(app)


# =========================================================
# SOCKET.IO
# =========================================================

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
)

# =========================================================
# GOOGLE OAUTH
# =========================================================

oauth = OAuth(app)

google = oauth.register(
    name="google",

    client_id=app.config.get(
        "GOOGLE_CLIENT_ID"
    ),

    client_secret=app.config.get(
        "GOOGLE_CLIENT_SECRET"
    ),

    server_metadata_url=(
        "https://accounts.google.com/"
        ".well-known/openid-configuration"
    ),

    client_kwargs={
        "scope": "openid email profile"
    },
)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

with app.app_context():
    db.create_all()


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_current_user():
    """
    Return the currently logged-in database user.
    """

    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.session.get(
        User,
        user_id
    )


def calculate_age(dob):
    """
    Calculate user's age from date of birth.
    """

    today = date.today()

    age = (
        today.year
        - dob.year
        - (
            (today.month, today.day)
            < (dob.month, dob.day)
        )
    )

    return age


def save_user_session(user):
    """
    Store required user information
    inside the Flask session.
    """

    session["user_id"] = user.id

    session["user"] = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "picture": user.picture,
    }


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    user = get_current_user()

    if user:

        if (
            user.date_of_birth is None
            or user.gender is None
        ):
            return redirect(
                url_for(
                    "complete_profile"
                )
            )

    return render_template(
        "index.html"
    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
def profile():

    user = get_current_user()

    if not user:
        return redirect(
            url_for("home")
        )

    if (
        user.date_of_birth is None
        or user.gender is None
    ):
        return redirect(
            url_for(
                "complete_profile"
            )
        )

    return render_template(
        "profile.html",
        user=user
    )


# =========================================================
# COMPLETE PROFILE
# =========================================================

@app.route(
    "/complete-profile",
    methods=["GET", "POST"]
)
def complete_profile():

    user = get_current_user()

    if not user:
        return redirect(
            url_for("home")
        )

    error = None

    if request.method == "POST":

        dob_string = request.form.get(
            "dob",
            ""
        ).strip()

        gender = request.form.get(
            "gender",
            ""
        ).strip().lower()

        # -------------------------------------------------
        # Validate DOB
        # -------------------------------------------------

        dob = None

        if not dob_string:

            error = (
                "Please select your date of birth."
            )

        else:

            try:

                dob = datetime.strptime(
                    dob_string,
                    "%Y-%m-%d"
                ).date()

            except ValueError:

                error = (
                    "Invalid date of birth."
                )

        # -------------------------------------------------
        # Validate DOB / AGE
        # -------------------------------------------------

        if not error and dob:

            if dob > date.today():

                error = (
                    "Date of birth cannot be "
                    "in the future."
                )

            else:

                age = calculate_age(
                    dob
                )

                if age < 18:

                    error = (
                        "Only users aged 18+ "
                        "are allowed."
                    )

        # -------------------------------------------------
        # Validate gender
        # -------------------------------------------------

        if not error:

            if gender not in (
                "male",
                "female"
            ):

                error = (
                    "Please select your gender."
                )

        # -------------------------------------------------
        # Save profile
        # -------------------------------------------------

        if not error:

            user.date_of_birth = dob

            user.gender = gender

            db.session.commit()

            save_user_session(
                user
            )

            return redirect(
                url_for(
                    "profile"
                )
            )

    return render_template(
        "complete_profile.html",
        profile=user,
        error=error
    )


# =========================================================
# CONNECT PAGE
# =========================================================

@app.route("/connect")
def connect():

    user = get_current_user()

    if not user:
        return redirect(
            url_for("home")
        )

    if (
        user.date_of_birth is None
        or user.gender is None
    ):
        return redirect(
            url_for(
                "complete_profile"
            )
        )

    return render_template(
        "connect.html",
        user=user
    )


# =========================================================
# GOOGLE LOGIN
# =========================================================

@app.route("/login/google")
def google_login():

    if not app.config.get(
        "GOOGLE_CLIENT_ID"
    ):

        return (
            "GOOGLE_CLIENT_ID is missing.",
            500
        )

    redirect_uri = os.getenv(
        "GOOGLE_REDIRECT_URI"
    )

    if not redirect_uri:

        redirect_uri = url_for(
            "google_authorized",
            _external=True
        )

    return google.authorize_redirect(
        redirect_uri
    )


# =========================================================
# GOOGLE CALLBACK
# =========================================================

@app.route(
    "/login/google/authorized"
)
def google_authorized():

    try:

        token = (
            google.authorize_access_token()
        )

        user_info = token.get(
            "userinfo"
        )

        if not user_info:

            return (
                "Google user information "
                "not received.",
                400
            )

        google_id = user_info.get(
            "sub"
        )

        name = user_info.get(
            "name"
        )

        email = user_info.get(
            "email"
        )

        picture = user_info.get(
            "picture"
        )

        if not google_id or not email:

            return (
                "Google account information "
                "is incomplete.",
                400
            )

        # -------------------------------------------------
        # Find existing user by Google ID
        # -------------------------------------------------

        user = User.query.filter_by(
            google_id=google_id
        ).first()

        # -------------------------------------------------
        # If Google ID not found, try email
        # -------------------------------------------------

        if not user:

            user = User.query.filter_by(
                email=email
            ).first()

        # -------------------------------------------------
        # Create new user
        # -------------------------------------------------

        if not user:

            user = User(
                google_id=google_id,
                name=name or "User",
                email=email,
                picture=picture,
            )

            db.session.add(
                user
            )

        else:

            user.google_id = google_id

            user.name = (
                name
                or user.name
            )

            user.picture = (
                picture
                or user.picture
            )

        db.session.commit()

        # -------------------------------------------------
        # Create session
        # -------------------------------------------------

        save_user_session(
            user
        )

        if token.get("id_token"):

            session["id_token"] = token.get(
                "id_token"
            )

        # -------------------------------------------------
        # Profile incomplete
        # -------------------------------------------------

        if (
            user.date_of_birth is None
            or user.gender is None
        ):

            return redirect(
                url_for(
                    "complete_profile"
                )
            )

        # -------------------------------------------------
        # Profile complete
        # -------------------------------------------------

        return redirect(
            url_for(
                "profile"
            )
        )

    except Exception as error:

        print(
            "GOOGLE LOGIN ERROR:",
            repr(error)
        )

        return (
            "Google login failed. "
            "Check Render logs.",
            500
        )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return {
        "status": "ok",
        "socketio": True,
        "database": True,
    }


# =========================================================
# REGISTER SOCKET EVENTS
# =========================================================

register_video_events(
    socketio
)


# =========================================================
# START SERVER
# =========================================================

socketio.run(
    app,
    host="0.0.0.0",
    port=10000,
    debug=False,
    allow_unsafe_werkzeug=True
)