import os
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from unicodedata import category
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, send_file, current_app, stream_with_context
from database.database import db
from models import order
from models.admin import Admin
from models.order import Order, OrderItem, OrderStatus, VALID_TRANSITIONS
from models.payment import Payment, PaymentStatus
from models.menu import MenuCategory, MenuItem
from models.cafe_status import CafeStatus
from models.table import CafeTable
from services import order_service, payment_service, notification_service, invoice_service
from functools import wraps

logger = logging.getLogger(__name__)

PREDEFINED_REJECTION_REASONS = {
    'Cafe is currently closed',
    'Item(s) unavailable',
    'High order volume',
    'Unable to prepare the order at this time',
    'Delivery/pickup issue',
    'Payment/order verification issue',
    'Technical problem',
}

admin_bp = Blueprint('admin_routes', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_routes.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        admin = Admin.query.filter_by(
            username=username
        ).first()

        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            session['admin_cafe_id'] = admin.cafe_id

            return redirect(
                url_for('admin_routes.dashboard')
            )

        return render_template(
            'admin/login.html',
            error='Invalid credentials'
        )

    if 'admin_id' in session:
        return redirect(
            url_for('admin_routes.dashboard')
        )

    return render_template(
        'admin/login.html'
    )


def get_admin_cafe_id():
    """Return the cafe assigned to the logged-in admin."""
    cafe_id = session.get('admin_cafe_id')

    if cafe_id is None:
        return None

    return int(cafe_id)


@admin_bp.route('/logout')
def logout():
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    session.pop('admin_cafe_id', None)
    return redirect(url_for('admin_routes.login'))


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    cafe_id = get_admin_cafe_id()

    today_orders = order_service.get_today_orders(
        cafe_id=cafe_id
    )

    today_revenue = order_service.get_today_revenue(
        cafe_id=cafe_id
    )

    active_orders = order_service.get_active_orders(
        cafe_id=cafe_id
    )

    new_count = len([o for o in active_orders if o.status == 'received'])
    preparing_count = len([o for o in active_orders if o.status == 'preparing'])
    ready_count = len([o for o in active_orders if o.status == 'ready'])

    return render_template('admin/dashboard.html',
                           today_orders=len(today_orders),
                           today_revenue=today_revenue,
                           new_count=new_count,
                           preparing_count=preparing_count,
                           ready_count=ready_count,
                           active_orders=active_orders)


@admin_bp.route('/orders')
@admin_required
def orders():
    status_filter = request.args.get('status', '')
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    cafe_id = get_admin_cafe_id()
    if cafe_id is not None:
        query = query.filter(Order.cafe_id == cafe_id)
    all_orders = query.order_by(Order.created_at.desc()).limit(100).all()
    return render_template('admin/orders.html', orders=all_orders, current_filter=status_filter)


@admin_bp.route('/orders/<int:order_db_id>')
@admin_required
def order_detail(order_db_id):
    cafe_id = get_admin_cafe_id()

    order = (
        Order.query
        .filter_by(
            id=order_db_id,
            cafe_id=cafe_id
        )
        .first_or_404()
    )

    return render_template(
        'admin/order_details.html',
        order=order
    )


@admin_bp.route('/api/orders/<int:order_db_id>/status', methods=['PATCH'])
@admin_required
def update_order_status(order_db_id):
    cafe_id = get_admin_cafe_id()

    order = (
        Order.query
        .filter_by(
            id=order_db_id,
            cafe_id=cafe_id
        )
        .first_or_404()
    )
    data = request.get_json(silent=True) or request.form
    new_status_str = data.get('status')
    estimated_minutes = data.get('estimated_minutes')
    rejection_reason = str(data.get('rejection_reason', '')).strip()

    if not new_status_str:
        return jsonify({'error': 'Status is required'}), 400

    try:
        new_status = OrderStatus(new_status_str)
    except ValueError:
        return jsonify({'error': 'Invalid status'}), 400

    if new_status == OrderStatus.REJECTED and not rejection_reason:
        return jsonify({'error': 'A rejection reason is required.'}), 400

    try:
        order_service.update_order_status(order, new_status, estimated_minutes)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    refund_status = order.refund_status or 'not_required'

    # Handle rejection: record reason and auto-refund.
    if new_status == OrderStatus.REJECTED:
        order.rejection_reason = rejection_reason
        refund_status = 'not_required'
        if order.payment:
            refund_status = 'pending'
            order.refund_status = refund_status
            db.session.commit()
            try:
                payment_service.initiate_refund(order.payment)
                refund_status = 'refunded'
            except Exception as e:
                logger.error(f'Refund failed for order {order.order_id}: {e}')
                refund_status = 'refund_failed'
            order.refund_status = refund_status
        else:
            order.refund_status = 'not_required'
            refund_status = 'not_required'
        db.session.commit()

    # Notify customer
    try:
        notification_service.notify_order_status_change(order)
    except Exception:
        pass

    # Generate invoice on acceptance
    if new_status == OrderStatus.ACCEPTED:
        try:
            invoice_service.generate_invoice(order)
        except Exception:
            pass

    return jsonify({
        'success': True,
        'status': order.status,
        'rejection_reason': order.rejection_reason,
        'refund_status': refund_status,
    })


@admin_bp.route('/menu')
@admin_required
def menu_management():
    cafe_id = get_admin_cafe_id()

    categories = (
        MenuCategory.query
        .filter_by(cafe_id=cafe_id)
        .order_by(MenuCategory.display_order)
        .all()
    )

    return render_template(
        'admin/menu.html',
        categories=categories
    )


@admin_bp.route('/api/menu/categories', methods=['POST'])
@admin_required
def add_category():
    data = request.get_json(silent=True) or request.form
    name = str(data.get('name', '')).strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400

    cafe_id = get_admin_cafe_id()

    cat = MenuCategory(
    cafe_id=cafe_id,
    name=name,
    display_order=(
        MenuCategory.query
        .filter_by(cafe_id=cafe_id)
        .count() + 1
    ),
)
    db.session.add(cat)
    db.session.commit()
    return jsonify({'success': True, 'id': cat.id})

@admin_bp.route('/api/menu/categories/<int:category_id>', methods=['DELETE'])
@admin_required
def delete_category(category_id):
    cafe_id = get_admin_cafe_id()

    category = (
    MenuCategory.query
    .filter_by(
        id=category_id,
        cafe_id=cafe_id
    )
    .first_or_404()
)

    item_count = (
        MenuItem.query
        .filter(MenuItem.category_id == category.id)
        .count()
    )

    if item_count > 0:
        return jsonify({
            'error': (
                f'Cannot delete "{category.name}" because it contains '
                f'{item_count} menu item(s). Delete or move the items first.'
            )
        }), 409

    category_name = category.name

    db.session.delete(category)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Category "{category_name}" deleted successfully.'
    })


@admin_bp.route('/api/menu/items', methods=['POST'])
@admin_required
def add_menu_item():
    data = request.get_json(silent=True) or request.form

    name = str(data.get('name', '')).strip()
    category_raw = data.get('category_id')
    price_raw = data.get('price')
    item_number = str(data.get('item_number', '')).strip()
    description = str(data.get('description', '')).strip()

    try:
        category_id = int(category_raw) if category_raw not in (None, '') else None
        price = float(price_raw) if price_raw not in (None, '') else None
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid category or price'}), 400

    if not name or category_id is None or price is None or not item_number:
        return jsonify({'error': 'Required fields missing'}), 400

    cafe_id = get_admin_cafe_id()

    category = (
    MenuCategory.query
    .filter_by(
        id=category_id,
        cafe_id=cafe_id
    )
    .first()
)

    if not category:
        return jsonify({
        'error': 'Invalid category for this cafe'
    }), 400

    image_path = None
    if 'image' in request.files and request.files['image'].filename:
        from werkzeug.utils import secure_filename
        filename = secure_filename(request.files['image'].filename)
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        request.files['image'].save(filepath)
        image_path = f'uploads/{filename}'

    item = MenuItem(
        cafe_id=cafe_id,
        category_id=category_id,
        item_number=item_number,
        name=name,
        description=description or None,
        price=price,
        image=image_path,
        is_available=True,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'id': item.id})


@admin_bp.route('/api/menu/items/<int:item_id>', methods=['GET', 'PATCH'])
@admin_required
def update_menu_item(item_id):
    cafe_id = get_admin_cafe_id()

    item = (
        MenuItem.query
        .filter_by(
            id=item_id,
            cafe_id=cafe_id
        )
        .first_or_404()
    )

    if request.method == 'GET':
        return jsonify(item.to_dict())

    data = request.get_json(silent=True) or request.form

    for field in [
        'name',
        'description',
        'item_number',
        'is_available',
        'is_daily_special',
        'category_id'
    ]:
        if field not in data:
            continue

        value = data.get(field)

        if field == 'category_id' and value not in (None, ''):
            try:
                value = int(value)
            except (TypeError, ValueError):
                return jsonify({
                    'error': 'Invalid category'
                }), 400

            category = (
                MenuCategory.query
                .filter_by(
                    id=value,
                    cafe_id=cafe_id
                )
                .first()
            )

            if not category:
                return jsonify({
                    'error': 'Invalid category for this cafe'
                }), 400

        elif field in [
            'is_available',
            'is_daily_special'
        ] and isinstance(value, str):
            value = value.lower() in (
                'true',
                '1',
                'yes',
                'on'
            )

        setattr(item, field, value)

    if 'price' in data:
        try:
            item.price = float(data.get('price'))
        except (TypeError, ValueError):
            return jsonify({
                'error': 'Invalid price'
            }), 400

    if (
        'image' in request.files
        and request.files['image'].filename
    ):
        from werkzeug.utils import secure_filename

        filename = secure_filename(
            request.files['image'].filename
        )

        upload_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'uploads'
        )

        os.makedirs(
            upload_dir,
            exist_ok=True
        )

        filepath = os.path.join(
            upload_dir,
            filename
        )

        request.files['image'].save(filepath)

        item.image = f'uploads/{filename}'

    elif 'image' in data and data.get('image'):
        item.image = data.get('image')

    db.session.commit()

    return jsonify({
        'success': True
    })


@admin_bp.route('/api/menu/items/<int:item_id>', methods=['DELETE'])
@admin_required
def delete_menu_item(item_id):
    cafe_id = get_admin_cafe_id()
    item = (
        MenuItem.query
        .filter_by(
            id=item_id,
            cafe_id=cafe_id
        )
        .first_or_404()
    )
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})


# ==========================================================
# TABLE MANAGEMENT
# ==========================================================

@admin_bp.route('/tables')
@admin_required
def table_management():
    cafe_id = get_admin_cafe_id()

    tables = (
        CafeTable.query
        .filter_by(cafe_id=cafe_id)
        .order_by(CafeTable.table_number.asc())
        .all()
    )

    return render_template(
        'admin/tables.html',
        tables=tables
    )


@admin_bp.route('/api/tables', methods=['POST'])
@admin_required
def add_table():
    data = request.get_json(silent=True) or request.form

    table_raw = data.get('table_number')

    try:
        table_number = int(table_raw)
    except (TypeError, ValueError):
        return jsonify({
            'error': 'Table number must be a valid number.'
        }), 400

    if table_number <= 0:
        return jsonify({
            'error': 'Table number must be greater than 0.'
        }), 400

    cafe_id = get_admin_cafe_id()

    existing = (
        CafeTable.query
        .filter_by(
            cafe_id=cafe_id,
            table_number=table_number
        )
        .first()
    )

    if existing:
        return jsonify({
            'error': f'Table {table_number} already exists.'
        }), 409

    table = CafeTable(
        cafe_id=cafe_id,
        table_number=table_number,
        is_active=True
    )

    db.session.add(table)
    db.session.commit()

    return jsonify({
        'success': True,
        'table': table.to_dict()
    }), 201


@admin_bp.route('/api/tables/<int:table_id>', methods=['PATCH'])
@admin_required
def update_table(table_id):
    cafe_id = get_admin_cafe_id()

    table = (
        CafeTable.query
        .filter_by(
            id=table_id,
            cafe_id=cafe_id
        )
        .first_or_404()
    )

    data = request.get_json(silent=True) or request.form

    if 'is_active' in data:
        value = data.get('is_active')

        if isinstance(value, str):
            value = value.lower() in (
                'true',
                '1',
                'yes',
                'on'
            )

        table.is_active = bool(value)

    db.session.commit()

    return jsonify({
        'success': True,
        'table': table.to_dict()
    })


@admin_bp.route('/api/tables/<int:table_id>', methods=['DELETE'])
@admin_required
def delete_table(table_id):
    cafe_id = get_admin_cafe_id()

    table = (
        CafeTable.query
        .filter_by(
            id=table_id,
            cafe_id=cafe_id
        )
        .first_or_404()
    )

    table_number = table.table_number

    db.session.delete(table)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Table {table_number} deleted successfully.'
    })
    
@admin_bp.route('/tables/<int:table_id>/qr')
@admin_required
def table_qr(table_id):
    cafe_id = get_admin_cafe_id()

    table = (
        CafeTable.query
        .filter_by(
            id=table_id,
            cafe_id=cafe_id
        )
        .first_or_404()
    )

    from services import qr_service

    filepath = qr_service.generate_table_qr(table)

    return send_file(
        filepath,
        mimetype='image/png',
        as_attachment=False,
        download_name=(
            f'Table_{table.table_number}_QR.png'
        )
    )


@admin_bp.route('/history')
@admin_required
def history():
    query = request.args.get('q', '').strip()
    cafe_id = get_admin_cafe_id()

    if query:
        orders = order_service.search_orders(
            query,
            cafe_id=cafe_id
        )
    else:
        orders = (
            Order.query
            .filter(Order.cafe_id == cafe_id)
            .order_by(Order.created_at.desc())
            .limit(50)
            .all()
        )

    return render_template(
        'admin/history.html',
        orders=orders,
        query=query
    )


@admin_bp.route('/api/cafe-status', methods=['PATCH'])
@admin_required
def set_cafe_status():
    data = request.get_json()
    new_status = data.get('status')
    if new_status not in ['open', 'closed', 'high_order_mode']:
        return jsonify({'error': 'Invalid status'}), 400

    cafe_id = get_admin_cafe_id()

    CafeStatus.set_status(
        new_status,
        cafe_id=cafe_id
    )

    return jsonify({'success': True})


@admin_bp.route('/api/orders/events')
@admin_required
def order_events():
    """SSE endpoint for real-time new-paid-order notifications.

    Waits for events from the process-wide OrderEventBus.
    A new_paid_order event is published only after a successful
    payment has been verified and the order has been committed.

    The application context is explicitly retained inside the
    streaming generator so SQLAlchemy queries remain valid for
    the entire lifetime of the SSE connection.
    """

    from services.order_events import order_event_bus
    admin_cafe_id = get_admin_cafe_id()
    # Capture the actual Flask application object BEFORE the
    # response starts streaming.
    app = current_app._get_current_object()

    raw_last_id = request.args.get('last_id')

    if raw_last_id is not None:
        try:
            last_seen_id = int(raw_last_id)
        except (TypeError, ValueError):
            last_seen_id = 0
    else:
        # First connection:
        # Start after the latest already-paid order so old orders
        # never trigger a notification.
        latest_paid = (
            Order.query
            .join(Payment, Payment.order_id == Order.id)
            .filter(
                Payment.status == PaymentStatus.SUCCESS.value,
                Order.cafe_id == admin_cafe_id
            )
            .order_by(Order.id.desc())
            .first()
        )

        last_seen_id = latest_paid.id if latest_paid else 0

    def generate():
        import time as _time

        # IMPORTANT:
        # Keep an explicit application context alive for the entire
        # lifetime of this streaming generator.
        with app.app_context():

            yield ": connected\n\n"

            current_last_id = last_seen_id

            # ==========================================================
            # CATCH-UP AFTER RECONNECT
            # ==========================================================

            if raw_last_id is not None:

                missed = (
                    Order.query
                    .join(
                        Payment,
                        Payment.order_id == Order.id
                    )
                    .filter(
                        Payment.status ==
                        PaymentStatus.SUCCESS.value,
                        Order.cafe_id == admin_cafe_id
                    )
                    .filter(
                        Order.id > current_last_id
                    )
                    .order_by(Order.id.asc())
                    .all()
                )

                for order in missed:

                    payload = {
                        'type': 'new_order',
                        'order': {
                            **order.to_dict(),
                            'id': order.id
                        }
                    }

                    yield (
                        f"data: {json.dumps(payload)}\n\n"
                    )

                    current_last_id = max(
                        current_last_id,
                        order.id
                    )

                since_timestamp = _time.time()

            else:
                since_timestamp = _time.time()

            # ==========================================================
            # LIVE EVENT LOOP
            # ==========================================================

            while True:

                try:
                    cafe = CafeStatus.get(
                        admin_cafe_id
                    )

                    # --------------------------------------------------
                    # CAFE CLOSED
                    # --------------------------------------------------

                    if cafe.status != 'open':

                        yield ": cafe_closed\n\n"

                        _time.sleep(5)

                        since_timestamp = _time.time()

                        continue

                    # --------------------------------------------------
                    # WAIT FOR NEW PAID ORDER
                    # --------------------------------------------------

                    events = (
                        order_event_bus.wait_for_events(
                            since_timestamp,
                            timeout=3
                        )
                    )

                    if events:

                        for ev in events:

                            if (
                                ev['type'] ==
                                'new_paid_order'
                                and
                                ev['order_db_id'] >
                                current_last_id
                            ):

                                order = (
                                    db.session.get(
                                        Order,
                                        ev['order_db_id']
                                    )
                                )

                                if not order:
                                    continue

                                if order.cafe_id != admin_cafe_id:
                                    continue

                                payload = {
                                    'type': 'new_order',
                                    'order': {
                                        **order.to_dict(),
                                        'id': order.id
                                    }
                                }

                                yield (
                                    f"data: "
                                    f"{json.dumps(payload)}\n\n"
                                )

                                current_last_id = max(
                                    current_last_id,
                                    order.id
                                )

                        since_timestamp = _time.time()

                    else:

                        # Keep the browser connection alive.
                        yield ": heartbeat\n\n"

                except GeneratorExit:
                    # Browser closed the SSE connection.
                    break

                except Exception as exc:
                    logger.exception(
                        "Admin SSE generator error: %s",
                        exc
                    )

                    # Send an SSE comment so the connection stays
                    # well-formed, then retry instead of killing
                    # the stream.
                    yield ": server_error\n\n"

                    _time.sleep(2)

                    since_timestamp = _time.time()

    return current_app.response_class(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )
