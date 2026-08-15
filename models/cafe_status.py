from database.database import db


class CafeStatus(db.Model):
    __tablename__ = 'cafe_status'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    cafe_id = db.Column(
        db.Integer,
        db.ForeignKey('cafes.id'),
        nullable=True,
        unique=True,
        index=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default='open'
    )

    @staticmethod
    def get(cafe_id=None):
        query = CafeStatus.query

        if cafe_id is not None:
            entry = query.filter_by(
                cafe_id=cafe_id
            ).first()
        else:
            entry = query.first()

        if not entry:
            entry = CafeStatus(
                cafe_id=cafe_id,
                status='open'
            )

            db.session.add(entry)
            db.session.commit()

        return entry

    @staticmethod
    def set_status(new_status, cafe_id=None):
        entry = CafeStatus.get(cafe_id)

        entry.status = new_status

        db.session.commit()

        return entry

    @staticmethod
    def is_accepting_orders(cafe_id=None):
        entry = CafeStatus.get(cafe_id)

        return entry.status == 'open'