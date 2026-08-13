from datetime import datetime, timezone
from database.database import db
from models.admin import Admin
from models.menu import MenuCategory, MenuItem
from models.cafe_status import CafeStatus


def seed():
    """Seed the database with demo data. Idempotent."""

    # Admin
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(username='admin', created_at=datetime.now(timezone.utc))
        admin.set_password('admin123')
        db.session.add(admin)
        print('Created admin account: admin / admin123')

    # Cafe status
    if not CafeStatus.query.first():
        db.session.add(CafeStatus(status='open'))
        print('Set cafe status: open')

    # Menu categories
    categories_data = [
        ('Coffee', 1),
        ('Tea', 2),
        ('Cold Drinks', 3),
        ('Snacks', 4),
        ('Sandwiches', 5),
        ('Desserts', 6),
    ]

    categories = {}
    for cat_name, display_order in categories_data:
        cat = MenuCategory.query.filter_by(name=cat_name).first()
        if not cat:
            cat = MenuCategory(name=cat_name, display_order=display_order)
            db.session.add(cat)
        categories[cat_name] = cat

    db.session.flush()

    # Menu items
    items_data = [
        # Coffee
        ('C001', 'Espresso', 'Strong concentrated coffee shot', 149, 'Coffee', True, False),
        ('C002', 'Cappuccino', 'Espresso with steamed milk and foam', 179, 'Coffee', True, True),
        ('C003', 'Latte', 'Espresso with steamed milk', 179, 'Coffee', True, False),
        ('C004', 'Americano', 'Espresso diluted with hot water', 149, 'Coffee', True, False),
        ('C005', 'Mocha', 'Espresso, chocolate, and steamed milk', 199, 'Coffee', True, False),
        ('C006', 'Cold Brew', 'Slow-steeped for 12 hours, smooth and bold', 199, 'Coffee', True, False),
        ('C007', 'Filter Coffee', 'Traditional South Indian filter coffee', 99, 'Coffee', True, True),

        # Tea
        ('T001', 'Masala Chai', 'Spiced Indian tea with ginger and cardamom', 79, 'Tea', True, False),
        ('T002', 'Green Tea', 'Light and refreshing green tea', 89, 'Tea', True, False),
        ('T003', 'Lemon Honey Tea', 'Hot tea with lemon and honey', 99, 'Tea', True, False),
        ('T004', 'Iced Tea', 'Chilled black tea with lemon', 109, 'Tea', True, False),
        ('T005', 'Matcha Latte', 'Japanese matcha with steamed milk', 179, 'Tea', True, False),

        # Cold Drinks
        ('D001', 'Lemonade', 'Fresh squeezed lemonade', 109, 'Cold Drinks', True, False),
        ('D002', 'Mango Smoothie', 'Fresh mango blended with yogurt', 149, 'Cold Drinks', True, True),
        ('D003', 'Berry Blast', 'Mixed berry smoothie', 159, 'Cold Drinks', True, False),
        ('D004', 'Oreo Shake', 'Creamy Oreo milkshake', 169, 'Cold Drinks', True, False),
        ('D005', 'Cold Coffee', 'Chilled coffee with ice cream', 149, 'Cold Drinks', True, False),

        # Snacks
        ('S001', 'Vada Pav', 'Mumbai-style spiced potato fritter bun', 59, 'Snacks', True, False),
        ('S002', 'Samosa', 'Crispy pastry with spiced potato filling', 49, 'Snacks', True, False),
        ('S003', 'French Fries', 'Crispy golden fries with ketchup', 129, 'Snacks', True, False),
        ('S004', 'Cheese Toast', 'Grilled bread with melted cheese', 139, 'Snacks', True, False),
        ('S005', 'Paneer Tikka', 'Grilled marinated cottage cheese', 189, 'Snacks', True, False),

        # Sandwiches
        ('SW001', 'Club Sandwich', 'Triple decker with chicken, egg, and veggies', 229, 'Sandwiches', True, False),
        ('SW002', 'Grilled Cheese', 'Classic grilled cheese sandwich', 149, 'Sandwiches', True, True),
        ('SW003', 'Paneer Sandwich', 'Grilled paneer with veggies', 179, 'Sandwiches', True, False),
        ('SW004', 'Chicken Tikka Sandwich', 'Spiced chicken tikka in a sandwich', 199, 'Sandwiches', True, False),
        ('SW005', 'Veggie Wrap', 'Fresh vegetables in a tortilla wrap', 169, 'Sandwiches', True, False),

        # Desserts
        ('DS001', 'Chocolate Brownie', 'Warm fudgy chocolate brownie', 149, 'Desserts', True, True),
        ('DS002', 'Cheesecake', 'Classic New York cheesecake', 199, 'Desserts', True, False),
        ('DS003', 'Tiramisu', 'Italian coffee-flavored dessert', 219, 'Desserts', True, False),
        ('DS004', 'Ice Cream Scoop', 'Vanilla, chocolate, or strawberry', 99, 'Desserts', True, False),
    ]

    for item_number, name, desc, price, cat_name, available, daily_special in items_data:
        existing = MenuItem.query.filter_by(item_number=item_number).first()
        if not existing:
            item = MenuItem(
                category_id=categories[cat_name].id,
                item_number=item_number,
                name=name,
                description=desc,
                price=price,
                is_available=available,
                is_daily_special=daily_special,
            )
            db.session.add(item)

    db.session.commit()
    print('Database seeded successfully.')


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        db.create_all()
        seed()
