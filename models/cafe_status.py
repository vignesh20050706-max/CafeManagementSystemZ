from database.database import db


class CafeStatus(db.Model):
    __tablename__ = 'cafe_status'

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False, default='open')  # open, closed, high_order_mode

    @staticmethod
    def get():
        entry = CafeStatus.query.first()
        if not entry:
            entry = CafeStatus(status='open')
            db.session.add(entry)
            db.session.commit()
        return entry

    @staticmethod
    def set_status(new_status):
        entry = CafeStatus.get()
        entry.status = new_status
        db.session.commit()
        return entry

    @staticmethod
    def is_accepting_orders():
        entry = CafeStatus.get()
        return entry.status == 'open'
