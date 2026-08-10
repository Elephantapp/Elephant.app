import os
import threading

from flask import Flask, render_template, redirect, url_for, session, request
from flask_socketio import SocketIO, emit
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

load_dotenv()


# =========================================================
# APP
# =========================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "change-this-secret-key"
)

app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


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
    ping_interval=25
)


# =========================================================
# GOOGLE OAUTH
# =========================================================

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=(
        "https://accounts.google.com/"
        ".well-known/openid-configuration"
    ),
    client_kwargs={
        "scope": "openid email profile"
    }
)


# =========================================================
# RANDOM MATCHING STATE
# =========================================================

waiting_user = None

active_pairs = {}

match_lock = threading.Lock()


# =========================================================
# PAGES
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


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


# =========================================================
# GOOGLE LOGIN
# =========================================================

@app.route("/login/google")
def google_login():

    redirect_uri = (
        "https://elephant-app.onrender.com"
        "/login/google/authorized"
    )

    return google.authorize_redirect(
        redirect_uri
    )


@app.route("/login/google/authorized")
def google_authorized():

    try:

        token = google.authorize_access_token()

        user_info = token.get("userinfo")

        if not user_info:

            return (
                "Google user information not received.",
                400
            )

        session["user"] = {
            "name": user_info.get("name"),
            "email": user_info.get("email"),
            "picture": user_info.get("picture")
        }

        if token.get("id_token"):

            session["id_token"] = token.get(
                "id_token"
            )

        return redirect(
            url_for("profile")
        )

    except Exception as error:

        print(
            "GOOGLE LOGIN ERROR:",
            repr(error)
        )

        return (
            "Google login failed. Check Render logs.",
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
        "socketio": True
    }


# =========================================================
# RANDOM MATCHING
# =========================================================

@socketio.on("find_random")
def find_random():

    global waiting_user

    current_user = session.get("user")

    if not current_user:

        emit("auth_required")

        return

    current_sid = request.sid

    with match_lock:

        # ---------------------------------------------
        # Already connected
        # ---------------------------------------------

        if current_sid in active_pairs:

            emit(
                "already_connected",
                {
                    "partner_sid":
                    active_pairs[current_sid]
                }
            )

            return

        # ---------------------------------------------
        # Already waiting
        # ---------------------------------------------

        if waiting_user is not None:

            if waiting_user["sid"] == current_sid:

                emit("waiting")

                return

            partner_sid = waiting_user["sid"]

            waiting_user = None

            active_pairs[current_sid] = partner_sid
            active_pairs[partner_sid] = current_sid

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

        # ---------------------------------------------
        # Nobody waiting
        # ---------------------------------------------

        waiting_user = {
            "sid": current_sid,
            "name": current_user.get("name")
        }

        print(
            "WAITING:",
            current_sid
        )

        emit("waiting")


# =========================================================
# WEBRTC OFFER
# =========================================================

@socketio.on("offer")
def handle_offer(data):

    if not data:
        return

    target = data.get("target")
    offer = data.get("offer")

    if not target or not offer:
        return

    socketio.emit(
        "offer",
        {
            "offer": offer,
            "from": request.sid
        },
        to=target
    )


# =========================================================
# WEBRTC ANSWER
# =========================================================

@socketio.on("answer")
def handle_answer(data):

    if not data:
        return

    target = data.get("target")
    answer = data.get("answer")

    if not target or not answer:
        return

    socketio.emit(
        "answer",
        {
            "answer": answer,
            "from": request.sid
        },
        to=target
    )


# =========================================================
# ICE CANDIDATE
# =========================================================

@socketio.on("ice_candidate")
def handle_ice_candidate(data):

    if not data:
        return

    target = data.get("target")
    candidate = data.get("candidate")

    if not target or not candidate:
        return

    socketio.emit(
        "ice_candidate",
        {
            "candidate": candidate,
            "from": request.sid
        },
        to=target
    )


# =========================================================
# END CALL
# =========================================================

@socketio.on("end_call")
def end_call(data=None):

    global waiting_user

    current_sid = request.sid

    target = None

    if data:

        target = data.get("target")

    with match_lock:

        if target:

            active_pairs.pop(
                current_sid,
                None
            )

            active_pairs.pop(
                target,
                None
            )

            socketio.emit(
                "partner_ended",
                {},
                to=target
            )

        else:

            partner = active_pairs.pop(
                current_sid,
                None
            )

            if partner:

                active_pairs.pop(
                    partner,
                    None
                )

                socketio.emit(
                    "partner_ended",
                    {},
                    to=partner
                )

        # Remove from waiting queue
        if (
            waiting_user is not None
            and waiting_user["sid"] == current_sid
        ):

            waiting_user = None


# =========================================================
# DISCONNECT
# =========================================================

@socketio.on("disconnect")
def disconnect():

    global waiting_user

    current_sid = request.sid

    partner = None

    with match_lock:

        # Remove waiting user
        if (
            waiting_user is not None
            and waiting_user["sid"] == current_sid
        ):

            waiting_user = None

            print(
                "WAITING USER LEFT:",
                current_sid
            )

        # Remove active pair
        partner = active_pairs.pop(
            current_sid,
            None
        )

        if partner:

            active_pairs.pop(
                partner,
                None
            )

    if partner:

        socketio.emit(
            "partner_ended",
            {},
            to=partner
        )

        print(
            "PARTNER DISCONNECTED:",
            current_sid,
            "<->",
            partner
        )


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    print(
        f"Starting Connect With Randoms on port {port}"
    )

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,
        allow_unsafe_werkzeug=True
    )
