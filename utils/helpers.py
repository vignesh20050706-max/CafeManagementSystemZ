from datetime import datetime, timezone


def format_currency(amount):
    """Format amount as INR."""
    return f'Rs.{amount:.0f}'


def time_ago(dt):
    """Human-readable time ago."""
    if not dt:
        return ''

    if dt.tzinfo is None:
        now = datetime.utcnow()
    else:
        now = datetime.now(timezone.utc)

    diff = now - dt
    minutes = int(diff.total_seconds() // 60)

    if minutes < 1:
        return 'Just now'

    if minutes < 60:
        return f'{minutes}m ago'

    hours = minutes // 60

    if hours < 24:
        return f'{hours}h ago'

    return dt.strftime('%d %b')


def status_label(status):
    """Get display-friendly status label."""
    labels = {
        'received': 'Order Received',
        'accepted': 'Accepted',
        'preparing': 'Preparing',
        'ready': 'Ready for Pickup',
        'delivered': 'Delivered',
        'rejected': 'Rejected',
    }
    return labels.get(status, status.title())


def status_color(status):
    """Get Bootstrap color class for status badge."""
    colors = {
        'received': 'info',
        'accepted': 'primary',
        'preparing': 'warning',
        'ready': 'success',
        'delivered': 'secondary',
        'rejected': 'danger',
    }
    return colors.get(status, 'secondary')
