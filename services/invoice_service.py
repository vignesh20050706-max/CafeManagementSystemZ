import os
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from flask import current_app


INVOICE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'invoices')


def generate_invoice(order):
    """Generate a PDF invoice for an order. Returns the file path."""
    os.makedirs(INVOICE_DIR, exist_ok=True)

    filename = f"invoice_{order.order_id}.pdf"
    filepath = os.path.join(INVOICE_DIR, filename)

    c = canvas.Canvas(filepath, pagesize=A5)
    width, height = A5
    primary = HexColor('#7C3F2C')
    text_color = HexColor('#222222')
    muted = HexColor('#6B6B6B')

    # Header
    c.setFont('Helvetica-Bold', 16)
    c.setFillColor(primary)
    cafe_name = current_app.config.get('CAFE_NAME', 'The Brew Spot')
    c.drawString(15 * mm, height - 20 * mm, cafe_name)

    c.setFont('Helvetica', 8)
    c.setFillColor(muted)
    c.drawString(15 * mm, height - 28 * mm, current_app.config.get('CAFE_ADDRESS', ''))
    c.drawString(15 * mm, height - 33 * mm, current_app.config.get('CAFE_PHONE', ''))

    # Divider
    c.setStrokeColor(HexColor('#E8E5E1'))
    c.line(15 * mm, height - 38 * mm, width - 15 * mm, height - 38 * mm)

    # Order details
    y = height - 48 * mm
    c.setFont('Helvetica', 9)
    c.setFillColor(text_color)

    c.drawString(15 * mm, y, f'Order ID: {order.order_id}')
    y -= 6 * mm
    c.drawString(15 * mm, y, f'Customer: {order.customer.name}')
    y -= 6 * mm
    c.drawString(15 * mm, y, f'Type: {order.order_type.replace("_", " ").title()}')
    y -= 6 * mm
    date_str = order.created_at.strftime('%d %b %Y, %I:%M %p') if order.created_at else ''
    c.drawString(15 * mm, y, f'Date: {date_str}')

    # Divider
    y -= 4 * mm
    c.line(15 * mm, y, width - 15 * mm, y)
    y -= 8 * mm

    # Table header
    c.setFont('Helvetica-Bold', 8)
    c.drawString(15 * mm, y, 'Item')
    c.drawRightString(width - 55 * mm, y, 'Qty')
    c.drawRightString(width - 35 * mm, y, 'Amount')
    y -= 2 * mm
    c.line(15 * mm, y, width - 15 * mm, y)
    y -= 6 * mm

    # Items
    c.setFont('Helvetica', 8)
    for item in order.items:
        c.drawString(15 * mm, y, item.item_name)
        c.drawRightString(width - 55 * mm, y, str(item.quantity))
        c.drawRightString(width - 15 * mm, y, f'Rs.{item.subtotal:.0f}')
        y -= 6 * mm

    # Total
    y -= 2 * mm
    c.line(15 * mm, y, width - 15 * mm, y)
    y -= 8 * mm
    c.setFont('Helvetica-Bold', 11)
    c.setFillColor(primary)
    c.drawRightString(width - 15 * mm, y, f'Total: Rs.{order.total_amount:.0f}')

    # Footer
    c.setFont('Helvetica', 7)
    c.setFillColor(muted)
    c.drawCentredString(width / 2, 12 * mm, 'Thank you for your order!')

    c.save()
    return filepath
