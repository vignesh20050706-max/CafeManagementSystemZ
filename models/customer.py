from database.database import db
from datetime import datetime, timezone


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(200), nullable=True)
    whatsapp_number = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    orders = db.relationship('Order', backref='customer', lazy=True)

    @staticmethod
    def find_or_create(name, mobile, email=None, whatsapp_number=None):
        customer = Customer.query.filter_by(mobile=mobile).first()
        if customer:
            if email and not customer.email:
                customer.email = email
            if whatsapp_number and not customer.whatsapp_number:
                customer.whatsapp_number = whatsapp_number
            return customer
        customer = Customer(
            name=name, mobile=mobile, email=email, whatsapp_number=whatsapp_number
        )
        db.session.add(customer)
        db.session.commit()
        return customer
