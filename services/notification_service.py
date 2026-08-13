import json
import logging
from flask import current_app
from database.database import db
from models.notification import Notification

logger = logging.getLogger(__name__)


def send_notification(order_id, channel, notification_type, payload=None):
    """Queue and attempt to send a notification."""
    notif = Notification(
        order_id=order_id,
        channel=channel,
        notification_type=notification_type,
        status='pending',
        payload=json.dumps(payload) if payload else None,
    )
    db.session.add(notif)
    db.session.commit()

    try:
        if channel == 'whatsapp':
            _send_whatsapp(notification_type, payload)
        elif channel == 'email':
            _send_email(notification_type, payload)

        notif.status = 'sent'
    except Exception as e:
        logger.warning(f'Notification failed ({channel}/{notification_type}): {e}')
        notif.status = 'failed'
    finally:
        db.session.commit()

    return notif


def notify_order_status_change(order):
    """Send appropriate notifications when order status changes."""
    payload = {
        'order_id': order.order_id,
        'customer_name': order.customer.name,
        'status': order.status,
        'mobile': order.customer.mobile,
        'rejection_reason': order.rejection_reason,
        'refund_status': order.refund_status if order.status == 'rejected' else None,
    }

    # WhatsApp
    send_notification(order.id, 'whatsapp', f'order_{order.status}', payload)

    # Email (if available)
    if order.customer.email:
        send_notification(order.id, 'email', f'order_{order.status}', payload)


def _send_whatsapp(notification_type, payload):
    """Send WhatsApp message via Cloud API. Dev fallback: log only."""
    access_token = current_app.config.get('WHATSAPP_ACCESS_TOKEN')
    phone_number_id = current_app.config.get('WHATSAPP_PHONE_NUMBER_ID')

    if not access_token or not phone_number_id:
        logger.info(f'[WhatsApp DEV] Would send {notification_type} to {payload}')
        return

    # Production WhatsApp Cloud API call would go here
    logger.info(f'WhatsApp notification: {notification_type}')


def _send_email(notification_type, payload):
    """Send email notification. Dev fallback: log only."""
    smtp_host = current_app.config.get('SMTP_HOST')
    if not smtp_host:
        logger.info(f'[Email DEV] Would send {notification_type} to {payload}')
        return

    # Production SMTP email would go here
    logger.info(f'Email notification: {notification_type}')
