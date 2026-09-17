import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as config.py
load_dotenv(Path(__file__).parent / '.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')

    if not SECRET_KEY:
        raise RuntimeError(
            'SECRET_KEY environment variable is required.'
        )
        # Customer ordering session
    SESSION_COOKIE_NAME = 'cafe_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get(
        'SESSION_COOKIE_SECURE',
        'false'
    ).lower() == 'true'
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_PATH = '/'
    PERMANENT_SESSION_LIFETIME = 86400
    SESSION_REFRESH_EACH_REQUEST = True
    _db_path = Path(__file__).parent / 'cafe.db'
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'CAFE_DATABASE_URL', f'sqlite:///{_db_path}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Razorpay
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')

    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise RuntimeError(
            'RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET environment variables are required.'
        )

    # WhatsApp
    WHATSAPP_ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')
    WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
    WHATSAPP_VERIFY_TOKEN = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'cafe_webhook_token')

    # SMTP / Email
    SMTP_HOST = os.environ.get('SMTP_HOST', '')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_FROM = os.environ.get('SMTP_FROM', 'noreply@cafe.com')
# Local network URL used by table QR codes
    BASE_URL = os.environ.get('BASE_URL')

    if not BASE_URL:
        raise RuntimeError(
            'BASE_URL environment variable is required.'
        )
    # Cafe
    CAFE_NAME = os.environ.get('CAFE_NAME', 'The Brew Spot')
    CAFE_PHONE = os.environ.get('CAFE_PHONE', '+91 98765 43210')
    CAFE_ADDRESS = os.environ.get('CAFE_ADDRESS', '123 Coffee Lane, Bangalore')

    # Admin demo credentials (dev only)
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise RuntimeError(
            'ADMIN_USERNAME and ADMIN_PASSWORD environment variables are required.'
        )
