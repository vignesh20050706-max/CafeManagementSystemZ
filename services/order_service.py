from datetime import datetime, timezone, timedelta
import secrets
from database.database import db
from models.order import Order, OrderItem, OrderStatus
from models.menu import MenuItem
from models.customer import Customer
from models.payment import Payment, PaymentStatus


def generate_order_id():
    """Generate a collision-resistant public order ID.

    The previous implementation read the latest order and added 1. Two
    simultaneous checkouts could therefore receive the same ID before
    either order was committed. Keep the human-readable date prefix, but
    use a cryptographically random suffix so IDs do not depend on a
    read-then-increment race.
    """
    today = datetime.now(timezone.utc).strftime('%Y%m%d')
    prefix = f'ORD-{today}-'

    # 8 hexadecimal characters provide 32 bits of entropy while keeping
    # the ID short and easy to read. The database unique constraint remains
    # the final authority on uniqueness.
    return f'{prefix}{secrets.token_hex(4).upper()}'


def create_order(customer_name, customer_mobile, order_type, cart_items, total_amount,
                 special_instructions=None, email=None, whatsapp_number=None,
                 cafe_id=None):
    """Create a new order with items from cart."""
    customer = Customer.find_or_create(
    name=customer_name,
    mobile=customer_mobile,
    email=email,
    whatsapp_number=whatsapp_number,
    cafe_id=cafe_id,
)

    order_id = generate_order_id()
    order = Order(
    order_id=order_id,
    customer_id=customer.id,
    cafe_id=cafe_id,
    order_type=order_type,
        status=OrderStatus.RECEIVED.value,
        total_amount=total_amount,
        special_instructions=special_instructions,
    )
    db.session.add(order)
    db.session.flush()

    for item in cart_items:
        menu_item = MenuItem.query.get(item['menu_item_id'])
        if not menu_item:
            continue
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            item_name=menu_item.name,
            quantity=item['quantity'],
            unit_price=menu_item.price,
            subtotal=menu_item.price * item['quantity'],
        )
        db.session.add(order_item)

    db.session.commit()
    return order


def get_order_by_public_id(public_id):
    """Get order by the human-readable order_id."""
    return Order.query.filter_by(order_id=public_id).first()


def update_order_status(order, new_status: OrderStatus, estimated_minutes=None):
    """Update order status with validation."""
    if not order.can_transition_to(new_status):
        raise ValueError(
            f'Cannot transition from {order.status} to {new_status.value}'
        )

    order.status = new_status.value

    if estimated_minutes is not None:
        order.estimated_minutes = estimated_minutes
        order.estimated_ready_time = datetime.now(timezone.utc) + timedelta(minutes=estimated_minutes)

    db.session.commit()
    return order


def get_active_orders(cafe_id=None):
    """Get active orders for a cafe."""
    active_statuses = [
        OrderStatus.RECEIVED.value,
        OrderStatus.ACCEPTED.value,
        OrderStatus.PREPARING.value,
        OrderStatus.READY.value,
    ]

    query = Order.query.filter(
        Order.status.in_(active_statuses)
    )

    if cafe_id is not None:
        query = query.filter(
            Order.cafe_id == cafe_id
        )

    return query.order_by(
        Order.created_at.desc()
    ).all()


def get_today_orders(cafe_id=None):
    """Get today's orders for a cafe."""
    today_start = datetime.now(
        timezone.utc
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    query = Order.query.filter(
        Order.created_at >= today_start
    )

    if cafe_id is not None:
        query = query.filter(
            Order.cafe_id == cafe_id
        )

    return query.order_by(
        Order.created_at.desc()
    ).all()


def get_today_revenue(cafe_id=None):
    """Get today's revenue for a cafe."""
    today_start = datetime.now(
        timezone.utc
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    query = Order.query.filter(
        Order.created_at >= today_start,
        Order.status.notin_([
            OrderStatus.REJECTED.value
        ]),
    )

    if cafe_id is not None:
        query = query.filter(
            Order.cafe_id == cafe_id
        )

    paid_orders = query.all()

    return sum(
        order.total_amount
        for order in paid_orders
    )


def get_last_7_days_revenue(cafe_id=None):
    """Get revenue for each of the last 7 days for a cafe."""
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=6)

    start_datetime = datetime.combine(
        start_date,
        datetime.min.time(),
        tzinfo=timezone.utc
    )

    end_datetime = datetime.combine(
        today + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone.utc
    )

    query = Order.query.filter(
        Order.created_at >= start_datetime,
        Order.created_at < end_datetime,
        Order.status.notin_([
            OrderStatus.REJECTED.value
        ]),
    )

    if cafe_id is not None:
        query = query.filter(
            Order.cafe_id == cafe_id
        )

    orders = query.all()

    revenue_by_date = {}

    for offset in range(7):
        current_date = start_date + timedelta(days=offset)
        revenue_by_date[current_date.isoformat()] = 0.0

    for order in orders:
        if not order.created_at:
            continue

        order_date = order.created_at.date().isoformat()

        if order_date in revenue_by_date:
            revenue_by_date[order_date] += float(
                order.total_amount or 0
            )

    return [
        {
            'date': date,
            'revenue': round(revenue, 2)
        }
        for date, revenue in revenue_by_date.items()
    ]


def search_orders(query, cafe_id=None):
    """Search orders by order_id, customer name, or mobile."""
    q = f'%{query}%'

    filters = [
        (Order.order_id.ilike(q)) |
        (Order.customer.has(Customer.name.ilike(q))) |
        (Order.customer.has(Customer.mobile.ilike(q)))
    ]

    if cafe_id is not None:
        filters.append(
            Order.cafe_id == cafe_id
        )

    return (
        Order.query
        .filter(*filters)
        .order_by(Order.created_at.desc())
        .limit(50)
        .all()
    )


def cleanup_old_orders():
    """Delete orders older than 30 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    old_orders = Order.query.filter(Order.created_at < cutoff).all()
    for order in old_orders:
        db.session.delete(order)
    db.session.commit()
    return len(old_orders)
