import os

from flask import Flask, render_template, redirect, url_for, session, request
from flask_socketio import SocketIO, emit
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

app.config["SESSION_COOKIE_SECURE"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    }
)


# =========================
# PAGES
# =========================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login/google")
def google_login():

    redirect_uri = url_for(
        "google_authorized",
        _external=True
    )

    return google.authorize_redirect(redirect_uri)


@app.route("/login/google/authorized")
def google_authorized():

    token = google.authorize_access_token()

    user_info = token.get("userinfo")

    if user_info:

        session["user"] = {
            "name": user_info.get("name"),
            "email": user_info.get("email"),
            "picture": user_info.get("picture")
        }

    return redirect(url_for("profile"))


@app.route("/profile")
def profile():

    user = session.get("user")

    if not user:
        return redirect(url_for("home"))

    return render_template(
        "profile.html",
        user=user
    )


@app.route("/connect")
def connect():

    user = session.get("user")

    if not user:
        return redirect(url_for("home"))

    return render_template(
        "connect.html",
        user=user
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# =========================
# RANDOM MATCHING
# =========================

waiting_user = None


@socketio.on("find_random")
def find_random():

    global waiting_user

    current_user = session.get("user")

    if not current_user:
        return

    current_sid = request.sid

    # User already waiting
    if waiting_user is not None:

        if waiting_user["sid"] == current_sid:
            emit("waiting")
            return

        # Existing waiting user
        partner_sid = waiting_user["sid"]

        # Clear waiting user
        waiting_user = None

        print(
            "MATCHED:",
            current_sid,
            "<->",
            partner_sid
        )

        # Current user becomes initiator
        emit(
            "matched",
            {
                "initiator": True,
                "partner_sid": partner_sid
            }
        )

        # Waiting user becomes receiver
        socketio.emit(
            "matched",
            {
                "initiator": False,
                "partner_sid": current_sid
            },
            to=partner_sid
        )

        return

    # Nobody waiting
    waiting_user = {
        "sid": current_sid,
        "name": current_user.get("name")
    }

    print(
        "WAITING:",
        current_sid
    )

    emit("waiting")


# =========================
# WEBRTC OFFER
# =========================

@socketio.on("offer")
def handle_offer(data):

    target = data.get("target")

    if not target:
        return

    socketio.emit(
        "offer",
        {
            "offer": data.get("offer"),
            "from": request.sid
        },
        to=target
    )


# =========================
# WEBRTC ANSWER
# =========================

@socketio.on("answer")
def handle_answer(data):

    target = data.get("target")

    if not target:
        return

    socketio.emit(
        "answer",
        {
            "answer": data.get("answer"),
            "from": request.sid
        },
        to=target
    )


# =========================
# ICE CANDIDATE
# =========================

@socketio.on("ice_candidate")
def handle_ice_candidate(data):

    target = data.get("target")

    if not target:
        return

    socketio.emit(
        "ice_candidate",
        {
            "candidate": data.get("candidate"),
            "from": request.sid
        },
        to=target
    )


# =========================
# END CALL
# =========================

@socketio.on("end_call")
def end_call(data=None):

    if not data:
        return

    target = data.get("target")

    if target:

        socketio.emit(
            "partner_ended",
            {},
            to=target
        )


# =========================
# DISCONNECT
# =========================

@socketio.on("disconnect")
def disconnect():

    global waiting_user

    if waiting_user is not None:

        if waiting_user["sid"] == request.sid:

            waiting_user = None

            print(
                "WAITING USER LEFT:",
                request.sid
            )


# =========================
# START SERVER
# =========================

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=8000,
        debug=False
    )