import os
import logging
import threading
import webbrowser

from flask import Flask, app, redirect, url_for
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
    from routes.super_admin_routes import super_admin_bp

    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(super_admin_bp, url_prefix='/super-admin')
    # Context processors
    @app.context_processor
    def inject_helpers():
        from models.cafe_status import CafeStatus
        from services.cafe_service import get_current_cafe
        from utils.helpers import format_currency, status_label, status_color, time_ago

        current_cafe = get_current_cafe()

        if current_cafe:
            cafe_status = CafeStatus.get(current_cafe.id).status
        else:
            cafe_status = 'closed'
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
        # Import all models before create_all() so SQLAlchemy knows
        # about every table and relationship.
        from models import (
    Cafe,
    Admin,
    Customer,
    MenuCategory,
    MenuItem,
    Order,
    OrderItem,
    Payment,
    Notification,
    CafeStatus,
    CafeTable,
)

        db.create_all()

        # Lightweight, idempotent migrations for the existing SQLite
        # prototype database.
        #
        # db.create_all() creates missing tables but does NOT add new
        # columns to tables that already exist.

        inspector = inspect(db.engine)

        migrations = []

        def add_column_if_missing(table_name, column_name, column_definition):
            existing_columns = {
                column['name']
                for column in inspector.get_columns(table_name)
            }

            if column_name not in existing_columns:
                migrations.append(
                    text(
                        f'ALTER TABLE {table_name} '
                        f'ADD COLUMN {column_name} {column_definition}'
                    )
                )

       # Existing order migrations
        add_column_if_missing(
    'orders',
    'rejection_reason',
    'TEXT'
)

        add_column_if_missing(
    'orders',
    'refund_status',
    'VARCHAR(30)'
)

# Phase 6 - Table QR ordering
        add_column_if_missing(
            'orders',
            'table_number',
            'INTEGER'
)

        # Multi-cafe foundation
        add_column_if_missing(
            'admins',
            'cafe_id',
            'INTEGER'
        )
        
        add_column_if_missing(
            'admins',
            'role',
            "VARCHAR(20) DEFAULT 'cafe_admin'"
        )
        
        add_column_if_missing(
            'cafes',
            'website_slug',
            'VARCHAR(160)'
        )

        add_column_if_missing(
            'customers',
            'cafe_id',
            'INTEGER'
        )

        add_column_if_missing(
            'orders',
            'cafe_id',
            'INTEGER'
        )

        add_column_if_missing(
            'menu_categories',
            'cafe_id',
            'INTEGER'
        )

        add_column_if_missing(
            'menu_items',
            'cafe_id',
            'INTEGER'
        )

        add_column_if_missing(
            'cafe_status',
            'cafe_id',
            'INTEGER'
        )
        
                # Super Admin - Cafe maintenance management
        add_column_if_missing(
            'cafes',
            'maintenance_amount',
            'NUMERIC(10, 2) DEFAULT 0'
        )

        add_column_if_missing(
            'cafes',
            'maintenance_due_date',
            'DATE'
        )

        add_column_if_missing(
            'cafes',
            'maintenance_paid',
            'BOOLEAN DEFAULT 0'
        )

        add_column_if_missing(
            'cafes',
            'maintenance_paid_date',
            'DATE'
        )

        add_column_if_missing(
            'cafes',
            'grace_period_end',
            'DATE'
        )

        if migrations:
            try:
                for migration in migrations:
                    db.session.execute(migration)

                db.session.commit()

            except Exception:
                db.session.rollback()
                raise

        # ---------------------------------------------------------
        # PHASE 3 - STAGE 2
        # Migrate existing single-cafe data into the first cafe.
        # This is idempotent and safe to run repeatedly.
        # ---------------------------------------------------------

        from models.cafe import Cafe

        default_cafe = Cafe.query.order_by(Cafe.id.asc()).first()

        if not default_cafe:
            default_cafe = Cafe(
                name=app.config.get(
                    'CAFE_NAME',
                    'The Brew Spot'
                ),
                phone=app.config.get(
                    'CAFE_PHONE',
                    ''
                ),
                address=app.config.get(
                    'CAFE_ADDRESS',
                    ''
                ),
                status='active'
            )

            db.session.add(default_cafe)
            db.session.flush()
            
                    # Generate website slugs for existing cafes.
        from services.cafe_service import generate_unique_slug

        cafes_without_slugs = Cafe.query.filter(
            Cafe.website_slug.is_(None)
        ).order_by(Cafe.id.asc()).all()

        for cafe in cafes_without_slugs:
            cafe.website_slug = generate_unique_slug(
                cafe.name,
                cafe.id
            )

        db.session.commit()

        # Existing admins
        Admin.query.filter(
            Admin.cafe_id.is_(None)
        ).update(
            {
                Admin.cafe_id: default_cafe.id
            },
            synchronize_session=False
        )

        # Existing customers
        Customer.query.filter(
            Customer.cafe_id.is_(None)
        ).update(
            {
                Customer.cafe_id: default_cafe.id
            },
            synchronize_session=False
        )

        # Existing orders
        Order.query.filter(
            Order.cafe_id.is_(None)
        ).update(
            {
                Order.cafe_id: default_cafe.id
            },
            synchronize_session=False
        )

        # Existing menu categories
        MenuCategory.query.filter(
            MenuCategory.cafe_id.is_(None)
        ).update(
            {
                MenuCategory.cafe_id: default_cafe.id
            },
            synchronize_session=False
        )

        # Existing menu items
        MenuItem.query.filter(
            MenuItem.cafe_id.is_(None)
        ).update(
            {
                MenuItem.cafe_id: default_cafe.id
            },
            synchronize_session=False
        )

        # Existing cafe status
        cafe_status = CafeStatus.query.filter(
            CafeStatus.cafe_id.is_(None)
        ).first()

        if cafe_status:
            cafe_status.cafe_id = default_cafe.id

        db.session.commit()

    return app


if __name__ == '__main__':
    app = create_app()

    # Seed on first run
    with app.app_context():
        from database.seed import seed
        seed()

    # Open the Admin Login page when starting the app.
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        threading.Timer(
            1.0,
            lambda: webbrowser.open_new(
                'http://127.0.0.1:5000/admin/login'
            )
        ).start()

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )