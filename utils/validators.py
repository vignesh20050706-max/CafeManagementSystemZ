import re


def validate_mobile(mobile):
    """Validate Indian mobile number."""
    cleaned = re.sub(r'[^0-9]', '', mobile)
    return len(cleaned) == 10 and cleaned.isdigit(), cleaned


def validate_email(email):
    """Basic email validation."""
    if not email:
        return True, ''
    pattern = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
    return bool(re.match(pattern, email)), email


def validate_cart_items(cart_items):
    """Validate cart items structure."""
    if not cart_items:
        return False, 'Cart is empty'
    for item in cart_items:
        if not isinstance(item.get('menu_item_id'), int) or item.get('menu_item_id') < 1:
            return False, 'Invalid item'
        if not isinstance(item.get('quantity'), int) or item.get('quantity') < 1:
            return False, 'Invalid quantity'
    return True, ''
