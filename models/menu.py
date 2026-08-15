from database.database import db
from datetime import datetime, timezone


class MenuCategory(db.Model):
    __tablename__ = 'menu_categories'

    id = db.Column(db.Integer, primary_key=True)
    cafe_id = db.Column(
        db.Integer,
        db.ForeignKey('cafes.id'),
        nullable=True,
        index=True
    )
    name = db.Column(db.String(50), nullable=False, unique=True)
    display_order = db.Column(db.Integer, default=0)

    items = db.relationship('MenuItem', backref='category', lazy=True, order_by='MenuItem.item_number')

    def __repr__(self):
        return f'<MenuCategory {self.name}>'


class MenuItem(db.Model):
    __tablename__ = 'menu_items'

    id = db.Column(db.Integer, primary_key=True)
    cafe_id = db.Column(
        db.Integer,
        db.ForeignKey('cafes.id'),
        nullable=True,
        index=True
    )
    category_id = db.Column(db.Integer, db.ForeignKey('menu_categories.id'), nullable=False)
    item_number = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(300), nullable=True)
    is_available = db.Column(db.Boolean, default=True)
    is_daily_special = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<MenuItem {self.item_number} {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'item_number': self.item_number,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'image': self.image,
            'is_available': self.is_available,
            'is_daily_special': self.is_daily_special,
            'category': self.category.name if self.category else None,
            'category_id': self.category_id,
        }
