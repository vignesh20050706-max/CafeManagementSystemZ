import json
import logging
from urllib import response
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    current_app,
    make_response,
)
from sqlalchemy import table
from database.database import db
from models.table import CafeTable
from models.menu import MenuCategory, MenuItem
from models.order import Order, OrderItem, OrderStatus
from models.payment import Payment, PaymentStatus
from models.cafe_status import CafeStatus
from services import order_service, payment_service, notification_service, invoice_service, qr_service
from services.cafe_service import get_default_cafe
from utils.validators import validate_mobile, validate_email, validate_cart_items
from utils.helpers import format_currency

logger = logging.getLogger(__name__)

customer_bp = Blueprint('customer_routes', __name__)


@customer_bp.route('/')
def home():
    """Customer home page."""
    cafe = get_default_cafe()

    if not cafe:
        return render_template(
            'customer/home.html',
            daily_specials=[],
            categories=[],
            cafe_status='closed'
        )

    daily_specials = (
        MenuItem.query
        .filter_by(
            cafe_id=cafe.id,
            is_daily_special=True,
            is_available=True
        )
        .limit(6)
        .all()
    )

    categories = (
        MenuCategory.query
        .filter_by(cafe_id=cafe.id)
        .order_by(MenuCategory.display_order)
        .all()
    )

    cafe_status_obj = CafeStatus.get(cafe.id)

    response = make_response(
        render_template(
            'customer/home.html',
            daily_specials=daily_specials,
            categories=categories,
            cafe_status=cafe_status_obj.status,
            table_number=session.get('table_number')
        )
    )

    response.headers['Cache-Control'] = (
        'no-store, no-cache, must-revalidate, max-age=0'
    )
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response
    
@customer_bp.route('/table/<int:table_id>')
def table_entry(table_id):
    """Enter the cafe ordering flow from a physical table QR code."""

    cafe = get_default_cafe()

    if not cafe:
        response = redirect(
            url_for('customer_routes.home')
        )

        response.headers['Cache-Control'] = (
            'no-store, no-cache, must-revalidate, max-age=0'
        )
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response

    table = (
        CafeTable.query
        .filter_by(
            id=table_id,
            cafe_id=cafe.id,
            is_active=True
        )
        .first()
    )

    if not table:
        response = redirect(
            url_for('customer_routes.home')
        )

        response.headers['Cache-Control'] = (
            'no-store, no-cache, must-revalidate, max-age=0'
        )
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response

    cafe_status_obj = CafeStatus.get(cafe.id)

    if cafe_status_obj.status != 'open':
        return redirect(
            url_for('customer_routes.home')
        )

    # Reset any previous customer ordering state.
    session.pop('order_type', None)
    session.pop('table_id', None)
    session.pop('table_number', None)
    session.pop('pending_order', None)

    # Lock this session to the scanned physical table.
    session.permanent = True
    session['table_id'] = table.id
    session['table_number'] = table.table_number
    session['order_type'] = 'dine_in'

    # Make sure Flask writes the updated session.
    session.modified = True

    response = redirect(
        url_for('customer_routes.home')
    )

    response.headers['Cache-Control'] = (
        'no-store, no-cache, must-revalidate, max-age=0'
    )
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response
    
@customer_bp.route('/order-type')
def order_type():
    """Choose takeaway or dine-in."""

    # Customers who entered through a table QR code
    # must remain in the dine-in flow.
    if session.get('table_id'):
        return redirect(
            url_for('customer_routes.menu')
        )

    cafe = get_default_cafe()

    if not cafe:
        return redirect(
            url_for('customer_routes.home')
        )

    cafe_status_obj = CafeStatus.get(cafe.id)

    if cafe_status_obj.status != 'open':
        return redirect(
            url_for('customer_routes.home')
        )

    return render_template(
        'customer/order_type.html'
    )

@customer_bp.route('/order-now')
def order_now():
    """Start customer ordering only when the cafe is accepting orders."""
    cafe = get_default_cafe()

    if not cafe:
        return redirect(
            url_for('customer_routes.home')
        )

    cafe_status_obj = CafeStatus.get(cafe.id)

    if cafe_status_obj.status != 'open':
        return redirect(
            url_for('customer_routes.home')
        )

    return redirect(
        url_for('customer_routes.menu')
    )


@customer_bp.route('/menu')
def menu():
    """Browse the menu for the active cafe."""
    cafe = get_default_cafe()

    if not cafe:
        return render_template(
            'customer/menu.html',
            categories=[],
            items=[],
            cafe_status='closed'
        )

    categories = (
        MenuCategory.query
        .filter_by(cafe_id=cafe.id)
        .order_by(MenuCategory.display_order)
        .all()
    )

    items = (
        MenuItem.query
        .filter_by(cafe_id=cafe.id)
        .order_by(MenuItem.item_number)
        .all()
    )

    cafe_status_obj = CafeStatus.get(cafe.id)

    return render_template(
        'customer/menu.html',
        categories=categories,
        items=items,
        cafe_status=cafe_status_obj.status
    )

@customer_bp.route('/api/menu/items')
def api_menu_items():
    """Return menu items for the active cafe as JSON."""
    cafe = get_default_cafe()

    if not cafe:
        return jsonify([])

    category_id = request.args.get('category_id')

    query = MenuItem.query.filter_by(
        cafe_id=cafe.id
    )

    if category_id:
        query = query.filter_by(
            category_id=int(category_id)
        )

    items = (
        query
        .order_by(MenuItem.item_number)
        .all()
    )

    return jsonify([
        item.to_dict()
        for item in items
    ])


@customer_bp.route('/cart')
def cart():
    """Show cart page without allowing stale customer state."""

    table_id = session.get('table_id')
    table_number = session.get('table_number')

    # If the QR table number exists, this is a table order.
    is_table_order = (
        table_id is not None
        and table_number is not None
    )

    response = make_response(
        render_template(
            'customer/cart.html',
            table_id=table_id if is_table_order else None,
            table_number=table_number if is_table_order else None
        )
    )

    response.headers['Cache-Control'] = (
        'no-store, no-cache, must-revalidate, max-age=0'
    )
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response


@customer_bp.route('/checkout')
def checkout():
    """Checkout page."""
    cafe = get_default_cafe()
    if not cafe:
        return redirect(url_for('customer_routes.home'))

    cafe_status_obj = CafeStatus.get(cafe.id)
    if cafe_status_obj.status != 'open':
        return redirect(url_for('customer_routes.home'))
    table_number = session.get('table_number')

    response = make_response(
        render_template(
            'customer/checkout.html',
            cafe_status=cafe_status_obj.status,
            table_number=table_number
        )
    )

    response.headers['Cache-Control'] = (
        'no-store, no-cache, must-revalidate, max-age=0'
    )
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response


@customer_bp.route('/api/payment/create', methods=['POST'])
def create_payment():
    """Create Razorpay order without creating the cafe order yet."""
    data = request.get_json(silent=True) or {}

    # Cafe must be accepting orders
    cafe = get_default_cafe()

    if not cafe:
        return jsonify({
        'error': 'Cafe is currently unavailable.'
    }), 400

    cafe_status_obj = CafeStatus.get(cafe.id)

    if cafe_status_obj.status != 'open':
        return jsonify({
        'error': 'The cafe is currently not accepting orders.'
    }), 400

    # Validate cart
    cart_items = data.get('cart_items', [])
    valid, msg = validate_cart_items(cart_items)
    if not valid:
        return jsonify({'error': msg}), 400

    # Validate customer information
    name = data.get('name', '').strip()
    mobile = data.get('mobile', '').strip()

    if not name or not mobile:
        return jsonify({'error': 'Name and mobile are required'}), 400

    mobile_valid, mobile_clean = validate_mobile(mobile)
    if not mobile_valid:
        return jsonify({'error': 'Invalid mobile number'}), 400

    email = data.get('email', '').strip() or None
    whatsapp = data.get('whatsapp_number', '').strip()

    # WhatsApp number is mandatory for customer orders.
    whatsapp_valid, whatsapp_clean = validate_mobile(whatsapp)
    if not whatsapp_valid:
        return jsonify({'error': 'WhatsApp number is required and must be 10 digits'}), 400

    table_id = session.get('table_id')

    if table_id:
        table = (
            CafeTable.query
            .filter_by(
                id=table_id,
                cafe_id=cafe.id,
            is_active=True
            )
            .first()
        )

        if not table:
            session.pop('table_id', None)
            session.pop('table_number', None)
            session.pop('order_type', None)

            return jsonify({
                'error': 'The selected table is no longer available.'
            }), 400

        # QR/table order: server is authoritative.
        order_type = 'dine_in'
        table_number = table.table_number

    else:
        # Normal website order.
        order_type = data.get(
            'order_type',
            'takeaway'
        )

        if order_type not in (
            'dine_in',
            'takeaway'
        ):
            return jsonify({
                'error': 'Invalid order type'
            }), 400

        table_number = None

    special_instructions = (
        data.get('special_instructions', '').strip() or None
    )

    if email:
        email_valid, _ = validate_email(email)
        if not email_valid:
            return jsonify({'error': 'Invalid email'}), 400

    # Verify current menu prices and availability on the server
    total = 0
    verified_items = []

    for item in cart_items:
        try:
            menu_item_id = int(item['menu_item_id'])
            quantity = int(item['quantity'])
        except (KeyError, TypeError, ValueError):
            return jsonify({'error': 'Invalid cart item'}), 400

        if quantity <= 0:
            return jsonify({'error': 'Invalid item quantity'}), 400

        menu_item = (
    MenuItem.query
    .filter_by(
        id=menu_item_id,
        cafe_id=cafe.id
    )
    .first()
)

        if not menu_item or not menu_item.is_available:
            return jsonify({
                'error': f'{item.get("name", "Item")} is not available'
            }), 400

        total += menu_item.price * quantity

        verified_items.append({
            'menu_item_id': menu_item.id,
            'quantity': quantity,
        })

    if total <= 0:
        return jsonify({'error': 'Order total must be greater than zero'}), 400

    # Generate the public order ID that will become the real order ID
    temp_order_id = order_service.generate_order_id()

    # Create Razorpay order ONLY.
    # No cafe Order is created until payment is verified successfully.
    amount_paise = int(round(total * 100))

    rzp_order = payment_service.create_razorpay_order(
        amount_paise,
        temp_order_id
    )

    if not rzp_order:
        return jsonify({
            'error': 'Payment gateway error. Please try again.'
        }), 500

    # Store only the verified checkout information in the server session
    session['pending_order'] = {
    'name': name,
    'mobile': mobile_clean,
    'cafe_id': cafe.id,
        'email': email,
        'whatsapp_number': whatsapp_clean,
        'order_type': order_type,
'table_id': table_id,
'table_number': table_number,
'special_instructions': special_instructions,
        'cart_items': verified_items,
        'total_amount': total,
        'temp_order_id': temp_order_id,
        'razorpay_order_id': rzp_order['id'],
    }

    return jsonify({
        'razorpay_order_id': rzp_order['id'],
        'amount': amount_paise,
        'currency': 'INR',
        'key': current_app.config['RAZORPAY_KEY_ID'],
        'order_id': temp_order_id,
    })

@customer_bp.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    """Verify Razorpay payment and create the cafe order only after success."""
    data = request.get_json(silent=True) or {}

    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')

    if not all([
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature
    ]):
        return jsonify({'error': 'Missing payment data'}), 400

    pending_order = session.get('pending_order')

    if not pending_order:
        return jsonify({
            'error': 'Payment session expired. Please start checkout again.'
        }), 400

    # Make sure the payment belongs to this checkout session
    if pending_order.get('razorpay_order_id') != razorpay_order_id:
        return jsonify({'error': 'Invalid payment order'}), 400

    # Verify Razorpay signature
    if not payment_service.verify_payment(
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature
    ):
        return jsonify({'error': 'Payment verification failed'}), 400

    # Verify the actual Razorpay payment status and amount
    gateway_payment = payment_service.fetch_razorpay_payment(
        razorpay_payment_id
    )

    if not gateway_payment:
        return jsonify({
            'error': 'Unable to confirm payment status.'
        }), 400

    if gateway_payment.get('status') != 'captured':
        return jsonify({
            'error': 'Payment has not been captured.'
        }), 400

    expected_amount = int(
        round(float(pending_order['total_amount']) * 100)
    )

    if int(gateway_payment.get('amount', 0)) != expected_amount:
        return jsonify({
            'error': 'Payment amount does not match the order.'
        }), 400

    # Check whether this payment was already processed
    existing_payment = payment_service.find_payment_by_razorpay_order(
        razorpay_order_id
    )

    if existing_payment:
        if existing_payment.status == PaymentStatus.SUCCESS.value:
            order = Order.query.get(existing_payment.order_id)

            if order:
                active_orders = session.get('active_orders', [])

                if order.order_id not in active_orders:
                    active_orders.append(order.order_id)

                session['active_orders'] = active_orders
                session.pop('pending_order', None)
                session.pop('table_id', None)
                session.pop('table_number', None)
                session.pop('order_type', None)

                return jsonify({
                    'success': True,
                    'order_id': order.order_id,
                    'already_processed': True,
                })

        return jsonify({
            'error': 'This payment is already being processed.'
        }), 409

    # Create the real cafe order NOW — payment has already been verified.
    from models.customer import Customer

    try:
        customer = Customer.find_or_create(
    name=pending_order['name'],
    mobile=pending_order['mobile'],
    email=pending_order.get('email'),
    whatsapp_number=pending_order.get('whatsapp_number'),
    cafe_id=pending_order['cafe_id'],
)

        order = Order(
    order_id=pending_order['temp_order_id'],
    customer_id=customer.id,
    cafe_id=pending_order['cafe_id'],
    order_type=pending_order['order_type'],
    table_number=pending_order.get('table_number'),
            status=OrderStatus.RECEIVED.value,
            total_amount=pending_order['total_amount'],
            special_instructions=pending_order.get('special_instructions'),
        )

        db.session.add(order)
        db.session.flush()

        for item in pending_order['cart_items']:
            menu_item = (
    MenuItem.query
    .filter_by(
        id=item['menu_item_id'],
        cafe_id=pending_order['cafe_id']
    )
    .first()
)

            if not menu_item or not menu_item.is_available:
                raise ValueError(
                    f'Menu item {item["menu_item_id"]} is no longer available.'
                )

            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=menu_item.id,
                item_name=menu_item.name,
                quantity=item['quantity'],
                unit_price=menu_item.price,
                subtotal=menu_item.price * item['quantity'],
            )

            db.session.add(order_item)

        payment = Payment(
            order_id=order.id,
            amount=pending_order['total_amount'],
            status=PaymentStatus.SUCCESS.value,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
            payment_reference=razorpay_payment_id,
        )

        db.session.add(payment)
        db.session.commit()

        # Publish event for real-time admin notification.
        # This is the single source of truth that a new PAID
        # order exists — the SSE endpoint waits on this bus.
        from services.order_events import order_event_bus
        order_event_bus.publish('new_paid_order', order.id)

    except Exception as e:
        db.session.rollback()

        logger.exception(
            'Payment succeeded but order creation failed.'
        )

        # Payment succeeded at Razorpay but local order creation failed.
        # Attempt refund so the customer is not charged without an order.
        try:
            payment_service.refund_razorpay_payment(
                razorpay_payment_id,
                expected_amount
            )
        except Exception:
            logger.exception(
                'Automatic refund failed after order creation failure.'
            )

        return jsonify({
            'error': (
                'Payment was successful, but we could not place the order. '
                'A refund has been initiated.'
            )
        }), 500

    # Generate QR code
    try:
        qr_service.generate_order_qr(order)
    except Exception as e:
        logger.warning(f'QR generation failed: {e}')

    # Generate invoice
    try:
        invoice_service.generate_invoice(order)
    except Exception as e:
        logger.warning(f'Invoice generation failed: {e}')

    # Send notifications
    try:
        notification_service.notify_order_status_change(order)
    except Exception as e:
        logger.warning(f'Notification failed: {e}')

    # Store active order in session
    active_orders = session.get('active_orders', [])

    if order.order_id not in active_orders:
        active_orders.append(order.order_id)

    session['active_orders'] = active_orders

    # Clear pending checkout
    session.pop('pending_order', None)
    session.pop('table_id', None)
    session.pop('table_number', None)
    session.pop('order_type', None)

    return jsonify({
        'success': True,
        'order_id': order.order_id,
    })


@customer_bp.route('/track/<order_id>')
def track_order(order_id):
    """Track a specific order."""
    order = order_service.get_order_by_public_id(order_id)
    if not order:
        return render_template('customer/tracking.html', order=None, error='Order not found')
    return render_template('customer/tracking.html', order=order)


@customer_bp.route('/orders')
def active_orders():
    """Show all active orders for this customer."""
    active_order_ids = session.get('active_orders', [])
    orders = []
    for oid in active_order_ids:
        order = order_service.get_order_by_public_id(oid)
        if order and order.status not in ['delivered', 'rejected']:
            orders.append(order)
    return render_template('customer/active_orders.html', orders=orders)


@customer_bp.route('/api/orders/<order_id>')
def api_order_detail(order_id):
    """Return order details as JSON."""
    order = order_service.get_order_by_public_id(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    return jsonify(order.to_dict())


@customer_bp.route('/api/cafe-status')
def api_cafe_status():
    """Return current cafe accepting-orders status."""
    status_obj = CafeStatus.get()
    return jsonify({
        'status': status_obj.status,
        'accepting_orders': status_obj.status == 'open',
    })


@customer_bp.route('/payment/callback', methods=['POST'])
def payment_callback():
    """Razorpay webhook endpoint."""
    # In production, verify webhook signature here
    data = request.get_json(force=True)
    logger.info(f'Payment webhook received: {data.get("payload", {}).get("payment", {}).get("entity", {}).get("id")}')
    return jsonify({'status': 'ok'}), 200


@customer_bp.route('/invoice/<order_id>')
def download_invoice(order_id):
    """Download invoice PDF."""
    from flask import send_file
    order = order_service.get_order_by_public_id(order_id)
    if not order:
        return 'Order not found', 404

    import os
    invoice_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'invoices')
    filepath = os.path.join(invoice_dir, f'invoice_{order_id}.pdf')

    if not os.path.exists(filepath):
        try:
            invoice_service.generate_invoice(order)
        except Exception:
            return 'Invoice not available', 404

    return send_file(filepath, as_attachment=True, download_name=f'Invoice_{order_id}.pdf')
