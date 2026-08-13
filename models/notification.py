from database.database import db
from datetime import datetime, timezone


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    channel = db.Column(db.String(20), nullable=False)  # whatsapp, email, push, website
    notification_type = db.Column(db.String(50), nullable=False)  # order_accepted, preparing, ready, etc.
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, sent, failed
    payload = db.Column(db.Text, nullable=True)  # JSON string for notification content
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Notification {self.id} {self.channel} {self.notification_type}>'
