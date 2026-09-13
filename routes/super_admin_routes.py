from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, session

from database.database import db
from models.admin import Admin
from models.cafe import Cafe


super_admin_bp = Blueprint(
    'super_admin_routes',
    __name__,
    url_prefix='/super-admin'
)


def super_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_routes.login'))

        admin = Admin.query.get(session['admin_id'])

        if not admin or admin.role != 'super_admin':
            return redirect(url_for('admin_routes.dashboard'))

        return f(*args, **kwargs)

    return decorated


@super_admin_bp.route('/')
@super_admin_bp.route('/dashboard')
@super_admin_required
def dashboard():
    cafes = Cafe.query.order_by(Cafe.id.asc()).all()

    return render_template(
        'super_admin/dashboard.html',
        cafes=cafes,
        cafe_name='Super Admin'
    )