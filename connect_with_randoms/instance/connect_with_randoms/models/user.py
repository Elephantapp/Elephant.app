from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    google_id = db.Column(
        db.String(255),
        unique=True,
        nullable=False
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False
    )

    picture = db.Column(
        db.String(500)
    )

    date_of_birth = db.Column(
        db.Date,
        nullable=True
    )

    gender = db.Column(
        db.String(20),
        nullable=True
    )

    is_premium = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    connection_count = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):

        return (
            f"<User {self.email}>"
        )