import razorpay
from flask import current_app
from database.database import db
from models.payment import Payment, PaymentStatus
from models.order import Order, OrderStatus


def get_razorpay_client():
    return razorpay.Client(
        auth=(
            current_app.config['RAZORPAY_KEY_ID'],
            current_app.config['RAZORPAY_KEY_SECRET']
        )
    )


def create_razorpay_order(amount_paise, order_public_id):
    """Create a Razorpay order. Amount in paise."""
    client = get_razorpay_client()
    try:
        razorpay_order = client.order.create({
            'amount': int(amount_paise),
            'currency': 'INR',
            'receipt': order_public_id,
            'payment_capture': 1,
        })
        return razorpay_order
    except Exception as e:
        current_app.logger.error(f'Razorpay order creation failed: {e}')
        return None


def verify_payment(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    """Verify Razorpay payment signature server-side."""
    client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
    except Exception as e:
        current_app.logger.error(f'Payment verification error: {e}')
        return False

def fetch_razorpay_payment(razorpay_payment_id):
    """Fetch payment details directly from Razorpay."""
    client = get_razorpay_client()

    try:
        return client.payment.fetch(razorpay_payment_id)
    except Exception as e:
        current_app.logger.error(
            f'Razorpay payment fetch failed: {e}'
        )
        return None


def create_payment_record(order_db_id, amount, razorpay_order_id=None):
    """Create a pending payment record."""
    payment = Payment(
        order_id=order_db_id,
        amount=amount,
        status=PaymentStatus.PENDING.value,
        razorpay_order_id=razorpay_order_id,
    )
    db.session.add(payment)
    db.session.commit()
    return payment


def mark_payment_success(payment, razorpay_payment_id, razorpay_signature):
    """Mark payment as successful after verification."""
    payment.status = PaymentStatus.SUCCESS.value
    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.payment_reference = razorpay_payment_id
    db.session.commit()
    return payment


def mark_payment_failed(payment):
    """Mark payment as failed."""
    payment.status = PaymentStatus.FAILED.value
    db.session.commit()
    return payment


def initiate_refund(payment):
    """Initiate refund for a payment."""
    client = get_razorpay_client()
    if not payment.razorpay_payment_id:
        payment.status = PaymentStatus.REFUNDED.value
        db.session.commit()
        return {'status': 'recorded_no_gateway_refund'}

    try:
        refund = client.payment.refund(payment.razorpay_payment_id, {
            'amount': int(payment.amount * 100),
        })
        payment.status = PaymentStatus.REFUNDED.value
        db.session.commit()
        return refund
    except Exception as e:
        current_app.logger.error(f'Refund failed for payment {payment.id}: {e}')
        raise


def refund_razorpay_payment(razorpay_payment_id, amount_paise):
    """Refund a captured Razorpay payment by payment ID.

    Used when a payment succeeds at Razorpay but local order creation
    cannot be completed. The amount is supplied in paise to match
    Razorpay's API.
    """
    client = get_razorpay_client()

    if not razorpay_payment_id:
        raise ValueError('Razorpay payment ID is required for refund.')

    amount_paise = int(amount_paise)
    if amount_paise <= 0:
        raise ValueError('Refund amount must be greater than zero.')

    try:
        return client.payment.refund(
            razorpay_payment_id,
            {'amount': amount_paise}
        )
    except Exception as e:
        current_app.logger.error(
            f'Razorpay recovery refund failed for payment {razorpay_payment_id}: {e}'
        )
        raise


def recover_payment(razorpay_payment_id):
    """Try to recover order state from a Razorpay payment ID.
    Used when redirect fails after successful payment.
    """
    client = get_razorpay_client()
    try:
        payment_data = client.payment.fetch(razorpay_payment_id)
        return payment_data
    except Exception:
        return None


def find_payment_by_razorpay_order(razorpay_order_id):
    """Find a payment record by razorpay order ID."""
    return Payment.query.filter_by(razorpay_order_id=razorpay_order_id).first()
