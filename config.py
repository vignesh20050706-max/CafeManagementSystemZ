import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as config.py
load_dotenv(Path(__file__).parent / '.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    _db_path = Path(__file__).parent / 'cafe.db'
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'CAFE_DATABASE_URL', f'sqlite:///{_db_path}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Razorpay
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_XXXXXXXXXXXXXX')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'XXXXXXXXXXXXXXXX')

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

    # Cafe
    CAFE_NAME = os.environ.get('CAFE_NAME', 'The Brew Spot')
    CAFE_PHONE = os.environ.get('CAFE_PHONE', '+91 98765 43210')
    CAFE_ADDRESS = os.environ.get('CAFE_ADDRESS', '123 Coffee Lane, Bangalore')

    # Admin demo credentials (dev only)
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
