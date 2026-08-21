import os

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


INVOICE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "invoices",
)


def _format_currency(amount):
    """Format an amount consistently for the invoice."""
    return f"Rs.{float(amount or 0):,.2f}"


def _draw_wrapped_text(c, text, x, y, max_width, font_name, font_size):
    """Draw text with simple wrapping and return the final Y position."""
    text = str(text or "").strip()

    if not text:
        return y

    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        candidate = (
            word
            if not current_line
            else f"{current_line} {word}"
        )

        if stringWidth(
            candidate,
            font_name,
            font_size,
        ) <= max_width:
            current_line = candidate
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    for line in lines:
        c.drawString(
            x,
            y,
            line,
        )
        y -= font_size + 2

    return y


def generate_invoice(order):
    """
    Generate a professional customer-facing PDF invoice.

    The existing function signature and invoice file location
    are preserved so the rest of the order flow remains unchanged.
    """
    os.makedirs(
        INVOICE_DIR,
        exist_ok=True,
    )

    filename = f"invoice_{order.order_id}.pdf"
    filepath = os.path.join(
        INVOICE_DIR,
        filename,
    )

    c = canvas.Canvas(
        filepath,
        pagesize=A5,
    )

    width, height = A5

    # ---------------------------------------------------------
    # Theme
    # ---------------------------------------------------------

    primary = colors.HexColor("#7C3F2C")
    primary_dark = colors.HexColor("#5F2F22")
    accent = colors.HexColor("#F4E8E2")
    background = colors.HexColor("#FAF9F7")
    border = colors.HexColor("#E5E0DC")
    text = colors.HexColor("#222222")
    muted = colors.HexColor("#6B6B6B")
    white = colors.white
    success = colors.HexColor("#2E7D32")
    success_background = colors.HexColor("#E8F5E9")

    margin = 15 * mm
    content_width = width - (2 * margin)

    # ---------------------------------------------------------
    # Background
    # ---------------------------------------------------------

    c.setFillColor(background)
    c.rect(
        0,
        0,
        width,
        height,
        stroke=0,
        fill=1,
    )

    # ---------------------------------------------------------
    # Header
    # ---------------------------------------------------------

    header_height = 38 * mm

    c.setFillColor(white)
    c.roundRect(
        margin,
        height - margin - header_height,
        content_width,
        header_height,
        4 * mm,
        stroke=0,
        fill=1,
    )

    cafe_name = current_app.config.get(
        "CAFE_NAME",
        "The Brew Spot",
    )

    cafe_address = current_app.config.get(
        "CAFE_ADDRESS",
        "",
    )

    cafe_phone = current_app.config.get(
        "CAFE_PHONE",
        "",
    )

    # Cafe name
    c.setFillColor(primary)
    c.setFont(
        "Helvetica-Bold",
        17,
    )

    c.drawString(
        margin + 7 * mm,
        height - margin - 11 * mm,
        cafe_name,
    )

    # Contact information
    c.setFillColor(muted)
    c.setFont(
        "Helvetica",
        7.5,
    )

    contact_y = height - margin - 18 * mm

    if cafe_address:
        contact_y = _draw_wrapped_text(
            c,
            cafe_address,
            margin + 7 * mm,
            contact_y,
            content_width * 0.52,
            "Helvetica",
            7.5,
        )

    if cafe_phone:
        c.drawString(
            margin + 7 * mm,
            contact_y - 1 * mm,
            cafe_phone,
        )

    # Invoice label
    c.setFillColor(primary_dark)
    c.setFont(
        "Helvetica-Bold",
        16,
    )

    c.drawRightString(
        width - margin - 7 * mm,
        height - margin - 12 * mm,
        "INVOICE",
    )

    # Order ID
    c.setFillColor(muted)
    c.setFont(
        "Helvetica-Bold",
        7.5,
    )

    c.drawRightString(
        width - margin - 7 * mm,
        height - margin - 19 * mm,
        f"#{order.order_id}",
    )

    # Date
    date_str = (
        order.created_at.strftime(
            "%d %b %Y, %I:%M %p"
        )
        if order.created_at
        else ""
    )

    c.setFont(
        "Helvetica",
        7.5,
    )

    c.drawRightString(
        width - margin - 7 * mm,
        height - margin - 25 * mm,
        date_str,
    )

    # ---------------------------------------------------------
    # Customer / Order Information
    # ---------------------------------------------------------

    info_top = (
        height
        - margin
        - header_height
        - 7 * mm
    )

    info_height = 38 * mm

    c.setFillColor(white)
    c.roundRect(
        margin,
        info_top - info_height,
        content_width,
        info_height,
        4 * mm,
        stroke=0,
        fill=1,
    )

    # Section title
    c.setFillColor(primary)
    c.setFont(
        "Helvetica-Bold",
        8,
    )

    c.drawString(
        margin + 7 * mm,
        info_top - 8 * mm,
        "CUSTOMER",
    )

    customer_name = (
        order.customer.name
        if order.customer
        else "Customer"
    )

    customer_mobile = (
        order.customer.mobile
        if order.customer
        else ""
    )

    customer_email = (
        getattr(order.customer, "email", None)
        if order.customer
        else None
    )

    c.setFillColor(text)
    c.setFont(
        "Helvetica-Bold",
        10,
    )

    c.drawString(
        margin + 7 * mm,
        info_top - 15 * mm,
        customer_name,
    )

    c.setFillColor(muted)
    c.setFont(
        "Helvetica",
        7.5,
    )

    if customer_mobile:
        c.drawString(
            margin + 7 * mm,
            info_top - 21 * mm,
            customer_mobile,
        )

    if customer_email:
        c.drawString(
            margin + 7 * mm,
            info_top - 26 * mm,
            customer_email,
        )

    # Order type
    right_column_x = (
        margin
        + content_width * 0.58
    )

    c.setFillColor(primary)
    c.setFont(
        "Helvetica-Bold",
        8,
    )

    c.drawString(
        right_column_x,
        info_top - 8 * mm,
        "ORDER TYPE",
    )

    order_type = (
        str(order.order_type or "")
        .replace("_", " ")
        .title()
    )

    c.setFillColor(text)
    c.setFont(
        "Helvetica-Bold",
        10,
    )

    c.drawString(
        right_column_x,
        info_top - 15 * mm,
        order_type,
    )

    # Table information
    if (
        order.order_type == "dine_in"
        and order.table_number is not None
    ):
        c.setFillColor(primary)
        c.setFont(
            "Helvetica-Bold",
            8,
        )

        c.drawString(
            right_column_x,
            info_top - 22 * mm,
            "TABLE",
        )

        c.setFillColor(text)
        c.setFont(
            "Helvetica-Bold",
            10,
        )

        c.drawString(
            right_column_x,
            info_top - 29 * mm,
            f"Table {order.table_number}",
        )

    # ---------------------------------------------------------
    # Items section
    # ---------------------------------------------------------

    items_top = (
        info_top
        - info_height
        - 7 * mm
    )

    row_height = 7 * mm

    # Estimate required height
    item_count = len(order.items)

    items_height = (
        15 * mm
        + max(item_count, 1) * row_height
        + 2 * mm
    )

    c.setFillColor(white)
    c.roundRect(
        margin,
        items_top - items_height,
        content_width,
        items_height,
        4 * mm,
        stroke=0,
        fill=1,
    )

    # Header background
    c.setFillColor(accent)
    c.roundRect(
        margin,
        items_top - 12 * mm,
        content_width,
        12 * mm,
        4 * mm,
        stroke=0,
        fill=1,
    )

    # Cover bottom corners of header rounding
    c.rect(
        margin,
        items_top - 12 * mm,
        content_width,
        4 * mm,
        stroke=0,
        fill=1,
    )

    item_x = margin + 6 * mm
    qty_x = width - margin - 57 * mm
    price_x = width - margin - 35 * mm
    total_x = width - margin - 6 * mm

    header_y = items_top - 8 * mm

    c.setFillColor(muted)
    c.setFont(
        "Helvetica-Bold",
        7,
    )

    c.drawString(
        item_x,
        header_y,
        "ITEM",
    )

    c.drawRightString(
        qty_x,
        header_y,
        "QTY",
    )

    c.drawRightString(
        price_x,
        header_y,
        "PRICE",
    )

    c.drawRightString(
        total_x,
        header_y,
        "TOTAL",
    )

    # Items
    y = items_top - 19 * mm

    c.setFont(
        "Helvetica",
        7.5,
    )

    for item in order.items:
        c.setFillColor(text)

        item_name = str(
            item.item_name or ""
        )

        # Keep item names inside their column.
        max_item_width = (
            qty_x
            - item_x
            - 8 * mm
        )

        if stringWidth(
            item_name,
            "Helvetica",
            7.5,
        ) > max_item_width:
            while (
                len(item_name) > 3
                and stringWidth(
                    item_name + "...",
                    "Helvetica",
                    7.5,
                )
                > max_item_width
            ):
                item_name = item_name[:-1]

            item_name += "..."

        c.drawString(
            item_x,
            y,
            item_name,
        )

        c.drawRightString(
            qty_x,
            y,
            str(item.quantity),
        )

        c.drawRightString(
            price_x,
            y,
            _format_currency(item.unit_price),
        )

        c.drawRightString(
            total_x,
            y,
            _format_currency(item.subtotal),
        )

        y -= row_height

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    summary_top = (
        items_top
        - items_height
        - 6 * mm
    )

    summary_height = 34 * mm

    c.setFillColor(white)
    c.roundRect(
        margin,
        summary_top - summary_height,
        content_width,
        summary_height,
        4 * mm,
        stroke=0,
        fill=1,
    )

    summary_x = width - margin - 7 * mm

    # Subtotal
    c.setFillColor(muted)
    c.setFont(
        "Helvetica",
        8,
    )

    c.drawRightString(
        summary_x - 32 * mm,
        summary_top - 9 * mm,
        "SUBTOTAL",
    )

    c.setFillColor(text)
    c.setFont(
        "Helvetica-Bold",
        8,
    )

    # Existing system does not currently expose
    # a separate tax/discount calculation.
    subtotal = sum(
        float(item.subtotal or 0)
        for item in order.items
    )

    c.drawRightString(
        summary_x,
        summary_top - 9 * mm,
        _format_currency(subtotal),
    )

    # Divider
    c.setStrokeColor(border)
    c.line(
        margin + 7 * mm,
        summary_top - 14 * mm,
        width - margin - 7 * mm,
        summary_top - 14 * mm,
    )

    # Total
    c.setFillColor(primary)
    c.setFont(
        "Helvetica-Bold",
        12,
    )

    c.drawString(
        margin + 7 * mm,
        summary_top - 24 * mm,
        "TOTAL",
    )

    c.drawRightString(
        summary_x,
        summary_top - 24 * mm,
        _format_currency(order.total_amount),
    )

    # ---------------------------------------------------------
    # Payment Status
    # ---------------------------------------------------------

    payment = getattr(
        order,
        "payment",
        None,
    )

    payment_status = (
        str(payment.status).upper()
        if payment and payment.status
        else "PAID"
    )

    status_width = 38 * mm
    status_height = 13 * mm

    status_x = (
        margin
        + (content_width - status_width) / 2
    )

    status_y = (
        summary_top
        - summary_height
        - 8 * mm
    )

    c.setFillColor(success_background)
    c.roundRect(
        status_x,
        status_y - status_height,
        status_width,
        status_height,
        6 * mm,
        stroke=0,
        fill=1,
    )

    c.setFillColor(success)
    c.setFont(
        "Helvetica-Bold",
        6.5,
    )

    c.drawCentredString(
        width / 2,
        status_y - 5 * mm,
        "PAYMENT STATUS",
    )

    c.setFont(
        "Helvetica-Bold",
        9,
    )

    c.drawCentredString(
        width / 2,
        status_y - 10 * mm,
        payment_status,
    )

    # ---------------------------------------------------------
    # Footer
    # ---------------------------------------------------------

    footer_y = 12 * mm

    c.setFillColor(primary)
    c.setFont(
        "Helvetica-Bold",
        9,
    )

    c.drawCentredString(
        width / 2,
        footer_y + 7 * mm,
        "Thank you for visiting!",
    )

    c.setFillColor(muted)
    c.setFont(
        "Helvetica",
        7.5,
    )

    c.drawCentredString(
        width / 2,
        footer_y + 2 * mm,
        "We hope to see you again.",
    )

    c.save()

    return filepath