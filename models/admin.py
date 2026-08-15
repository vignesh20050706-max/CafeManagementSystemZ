from database.database import db
from werkzeug.security import generate_password_hash, check_password_hash


class Admin(db.Model):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)

    cafe_id = db.Column(
        db.Integer,
        db.ForeignKey('cafes.id'),
        nullable=True,
        index=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(300),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )

    def __repr__(self):
        return f'<Admin {self.username}>'