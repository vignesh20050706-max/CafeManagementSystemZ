import enum
from database.database import db
from datetime import datetime, timezone


class OrderStatus(str, enum.Enum):
    RECEIVED = 'received'
    ACCEPTED = 'accepted'
    PREPARING = 'preparing'
    READY = 'ready'
    DELIVERED = 'delivered'
    REJECTED = 'rejected'


VALID_TRANSITIONS = {
    OrderStatus.RECEIVED: [OrderStatus.ACCEPTED, OrderStatus.REJECTED],
    OrderStatus.ACCEPTED: [OrderStatus.PREPARING, OrderStatus.REJECTED],
    OrderStatus.PREPARING: [OrderStatus.READY, OrderStatus.REJECTED],
    OrderStatus.READY: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [],
    OrderStatus.REJECTED: [],
}


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    cafe_id = db.Column(
        db.Integer,
        db.ForeignKey('cafes.id'),
        nullable=True,
        index=True
    )
    order_type = db.Column(db.String(10), nullable=False)  # 'takeaway' or 'dine_in'
    status = db.Column(db.String(20), nullable=False, default=OrderStatus.RECEIVED.value)
    total_amount = db.Column(db.Float, nullable=False)
    special_instructions = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    refund_status = db.Column(db.String(30), nullable=True)
    estimated_minutes = db.Column(db.Integer, nullable=True)
    estimated_ready_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    payment = db.relationship('Payment', backref='order', uselist=False, lazy=True)

    def __repr__(self):
        return f'<Order {self.order_id}>'

    def can_transition_to(self, new_status: OrderStatus) -> bool:
        current = OrderStatus(self.status)
        return new_status in VALID_TRANSITIONS.get(current, [])

    def to_dict(self):
        return {
            'order_id': self.order_id,
            'order_type': self.order_type,
            'status': self.status,
            'total_amount': self.total_amount,
            'special_instructions': self.special_instructions,
            'rejection_reason': self.rejection_reason,
            'refund_status': self.refund_status,
            'estimated_minutes': self.estimated_minutes,
            'estimated_ready_time': (
    self.estimated_ready_time.replace(
        tzinfo=timezone.utc
    ).isoformat()
    if self.estimated_ready_time
    else None
),
            'customer_name': self.customer.name if self.customer else None,
            'customer_mobile': self.customer.mobile if self.customer else None,
            'items': [item.to_dict() for item in self.items],
            'payment_status': self.payment.status if self.payment else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=True)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<OrderItem {self.item_name} x{self.quantity}>'

    def to_dict(self):
        return {
            'item_name': self.item_name,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'subtotal': self.subtotal,
        }
