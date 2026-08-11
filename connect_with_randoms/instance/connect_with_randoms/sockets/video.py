from flask import request, session
from flask_socketio import emit

from services.matchmaking import (
    match_user,
    end_match,
    get_partner,
)

from services.presence import (
    set_online,
    set_offline,
    refresh_online,
)


def register_video_events(socketio):

    @socketio.on("connect")
    def handle_connect():

        user = session.get("user")

        if not user:
            emit("auth_required")
            return

        set_online(
            request.sid
        )

        print(
            "SOCKET CONNECTED:",
            request.sid
        )


    @socketio.on("heartbeat")
    def handle_heartbeat():

        refresh_online(
            request.sid
        )


    @socketio.on("find_random")
    def handle_find_random():

        user = session.get("user")

        if not user:
            emit("auth_required")
            return

        result = match_user(
            request.sid,
            user
        )

        status = result.get(
            "status"
        )

        if status == "waiting":

            emit("waiting")

            return

        if status == "already_connected":

            emit(
                "already_connected",
                {
                    "partner_sid":
                    result.get("partner_sid")
                }
            )

            return

        if status == "matched":

            partner_sid = result.get(
                "partner_sid"
            )

            emit(
                "matched",
                {
                    "initiator": True,
                    "partner_sid": partner_sid
                }
            )

            socketio.emit(
                "matched",
                {
                    "initiator": False,
                    "partner_sid": request.sid
                },
                to=partner_sid
            )


    @socketio.on("offer")
    def handle_offer(data):

        if not data:
            return

        target = data.get(
            "target"
        )

        offer = data.get(
            "offer"
        )

        if not target or not offer:
            return

        if get_partner(
            request.sid
        ) != target:
            return

        socketio.emit(
            "offer",
            {
                "offer": offer,
                "from": request.sid
            },
            to=target
        )


    @socketio.on("answer")
    def handle_answer(data):

        if not data:
            return

        target = data.get(
            "target"
        )

        answer = data.get(
            "answer"
        )

        if not target or not answer:
            return

        if get_partner(
            request.sid
        ) != target:
            return

        socketio.emit(
            "answer",
            {
                "answer": answer,
                "from": request.sid
            },
            to=target
        )


    @socketio.on("ice_candidate")
    def handle_ice_candidate(data):

        if not data:
            return

        target = data.get(
            "target"
        )

        candidate = data.get(
            "candidate"
        )

        if not target or not candidate:
            return

        if get_partner(
            request.sid
        ) != target:
            return

        socketio.emit(
            "ice_candidate",
            {
                "candidate": candidate,
                "from": request.sid
            },
            to=target
        )


    @socketio.on("end_call")
    def handle_end_call(data=None):

        current_sid = request.sid

        partner_sid = end_match(
            current_sid
        )

        if partner_sid:

            socketio.emit(
                "partner_ended",
                {},
                to=partner_sid
            )


    @socketio.on("disconnect")
    def handle_disconnect():

        current_sid = request.sid

        partner_sid = end_match(
            current_sid
        )

        set_offline(
            current_sid
        )

        if partner_sid:

            socketio.emit(
                "partner_ended",
                {},
                to=partner_sid
            )

        print(
            "SOCKET DISCONNECTED:",
            current_sid
        )