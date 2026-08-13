import os
import logging
from flask import Flask, redirect, url_for
from sqlalchemy import inspect, text
from config import Config
from database.database import db


def create_app(config_class=Config):
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.config.from_object(config_class)

    # Logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)

    # Extensions+++++++++++++++++
    db.init_app(app)

    # Register routes
    from routes.customer_routes import customer_bp
    from routes.admin_routes import admin_bp

    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Context processors
    @app.context_processor
    def inject_helpers():
        from models.cafe_status import CafeStatus
        from utils.helpers import format_currency, status_label, status_color, time_ago
        cafe_status = CafeStatus.get().status
        return {
            'cafe_name': app.config.get('CAFE_NAME', 'The Brew Spot'),
            'cafe_status': cafe_status,
            'cafe_closed': cafe_status == 'closed',
            'high_order_mode': cafe_status == 'high_order_mode',
            'format_currency': format_currency,
            'status_label': status_label,
            'status_color': status_color,
            'time_ago': time_ago,
        }

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return redirect(url_for('customer_routes.home'))

    @app.errorhandler(500)
    def server_error(e):
        return 'Server error', 500

    # Init DB
    with app.app_context():
        db.create_all()

        # Lightweight, idempotent migration for the existing SQLite prototype database.
        # db.create_all() does not add new columns to existing tables.
        inspector = inspect(db.engine)
        order_columns = {column['name'] for column in inspector.get_columns('orders')}
        migrations = []

        if 'rejection_reason' not in order_columns:
            migrations.append(
                text('ALTER TABLE orders ADD COLUMN rejection_reason TEXT')
            )

        if 'refund_status' not in order_columns:
            migrations.append(
                text('ALTER TABLE orders ADD COLUMN refund_status VARCHAR(30)')
            )

        if migrations:
            try:
                for migration in migrations:
                    db.session.execute(migration)
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

    return app


if __name__ == '__main__':
    app = create_app()
    # Seed on first run
    with app.app_context():
        from database.seed import seed
        seed()
    app.run(debug=True, port=5000)
