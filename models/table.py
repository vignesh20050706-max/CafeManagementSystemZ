from datetime import datetime, timezone

from database.database import db


class CafeTable(db.Model):
    __tablename__ = 'cafe_tables'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    cafe_id = db.Column(
        db.Integer,
        db.ForeignKey('cafes.id'),
        nullable=False,
        index=True
    )

    table_number = db.Column(
        db.Integer,
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    cafe = db.relationship(
        'Cafe',
        backref=db.backref(
            'tables',
            lazy=True,
            cascade='all, delete-orphan'
        )
    )

    __table_args__ = (
        db.UniqueConstraint(
            'cafe_id',
            'table_number',
            name='uq_cafe_table_number'
        ),
    )

    def __repr__(self):
        return (
            f'<CafeTable cafe={self.cafe_id} '
            f'table={self.table_number}>'
        )

    def to_dict(self):
        return {
            'id': self.id,
            'cafe_id': self.cafe_id,
            'table_number': self.table_number,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
            if self.created_at else None,
        }