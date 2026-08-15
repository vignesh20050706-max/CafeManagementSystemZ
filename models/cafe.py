from datetime import datetime, timezone

from database.database import db


class Cafe(db.Model):
    __tablename__ = 'cafes'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(150), nullable=False, unique=True)
    phone = db.Column(db.String(30), nullable=True)
    address = db.Column(db.String(300), nullable=True)

    status = db.Column(
        db.String(20),
        nullable=False,
        default='active'
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    admins = db.relationship(
        'Admin',
        backref='cafe',
        lazy=True
    )

    customers = db.relationship(
        'Customer',
        backref='cafe',
        lazy=True
    )

    orders = db.relationship(
        'Order',
        backref='cafe',
        lazy=True
    )

    categories = db.relationship(
        'MenuCategory',
        backref='cafe',
        lazy=True
    )

    status_record = db.relationship(
        'CafeStatus',
        backref='cafe',
        uselist=False,
        lazy=True
    )

    def __repr__(self):
        return f'<Cafe {self.name}>'