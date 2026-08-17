import os
import qrcode
from flask import url_for, current_app

QR_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'qr_codes')


def generate_order_qr(order, external=False):
    """Generate a QR code for an order's tracking page."""
    os.makedirs(QR_DIR, exist_ok=True)

    filename = f"qr_{order.order_id}.png"
    filepath = os.path.join(QR_DIR, filename)

    if external:
        tracking_url = f"{current_app.config.get('BASE_URL', 'http://localhost:5000')}/track/{order.order_id}"
    else:
        tracking_url = url_for('customer_routes.track_order', order_id=order.order_id, _external=False)

    img = qrcode.make(tracking_url)
    img.save(filepath)
    return filepath


def generate_cafe_qr():
    """Generate a QR code that links to the cafe homepage."""
    os.makedirs(QR_DIR, exist_ok=True)

    filepath = os.path.join(QR_DIR, 'cafe_home.png')
    url = current_app.config.get('BASE_URL', 'http://localhost:5000')

    img = qrcode.make(url)
    img.save(filepath)
    return filepath

def generate_table_qr(table):
    """Generate a QR code for a specific cafe table."""
    table_qr_dir = os.path.join(
        QR_DIR,
        'tables'
    )

    os.makedirs(
        table_qr_dir,
        exist_ok=True
    )

    filename = (
        f'cafe_{table.cafe_id}_table_{table.table_number}.png'
    )

    filepath = os.path.join(
        table_qr_dir,
        filename
    )

    base_url = current_app.config.get(
        'BASE_URL',
        'http://localhost:5000'
    ).rstrip('/')

    table_url = (
        f'{base_url}/table/{table.id}'
    )

    img = qrcode.make(table_url)
    img.save(filepath)

    return filepath
