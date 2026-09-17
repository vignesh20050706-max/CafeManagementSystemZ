from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database.database import db
from models.admin import Admin
from models.cafe import Cafe
from models.cafe_status import CafeStatus
from services.cafe_service import generate_unique_slug


# app.py already registers this blueprint with /super-admin
super_admin_bp = Blueprint(
    'super_admin_routes',
    __name__
)


def super_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        admin_id = session.get('admin_id')

        if not admin_id:
            return redirect(url_for('admin_routes.login'))

        admin = Admin.query.get(admin_id)

        if not admin or admin.role != 'super_admin':
            return redirect(url_for('admin_routes.dashboard'))

        return f(*args, **kwargs)

    return decorated


def _parse_date(value):
    """Convert YYYY-MM-DD form input into a date object."""
    if not value:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_amount(value):
    """Convert maintenance amount into Decimal safely."""
    if value is None or value.strip() == '':
        return Decimal('0.00')

    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError):
        return None

    if amount < 0:
        return None

    return amount.quantize(Decimal('0.01'))


def _set_cafe_order_status(cafe_id, status):
    """
    Keep the platform cafe status and customer-facing order status
    synchronized.
    """
    cafe_status = CafeStatus.query.filter_by(cafe_id=cafe_id).first()

    if not cafe_status:
        cafe_status = CafeStatus(
            cafe_id=cafe_id,
            status=status
        )
        db.session.add(cafe_status)
    else:
        cafe_status.status = status


@super_admin_bp.route('/')
@super_admin_bp.route('/dashboard')
@super_admin_required
def dashboard():
    cafes = Cafe.query.order_by(Cafe.id.asc()).all()

    total_cafes = len(cafes)
    active_cafes = sum(
        1 for cafe in cafes if cafe.status == 'active'
    )
    on_hold_cafes = sum(
        1 for cafe in cafes if cafe.status == 'on_hold'
    )
    inactive_cafes = sum(
        1 for cafe in cafes if cafe.status == 'inactive'
    )

    today = date.today()

    maintenance_due = sum(
        1
        for cafe in cafes
        if (
            cafe.maintenance_due_date
            and not cafe.maintenance_paid
            and cafe.maintenance_due_date >= today
        )
    )

    overdue_or_grace = sum(
        1
        for cafe in cafes
        if (
            cafe.maintenance_due_date
            and not cafe.maintenance_paid
            and cafe.maintenance_due_date < today
        )
    )

    return render_template(
        'super_admin/dashboard.html',
        cafes=cafes,
        cafe_name='Super Admin',
        total_cafes=total_cafes,
        active_cafes=active_cafes,
        on_hold_cafes=on_hold_cafes,
        inactive_cafes=inactive_cafes,
        maintenance_due=maintenance_due,
        overdue_or_grace=overdue_or_grace,
    )


@super_admin_bp.route('/cafes/new', methods=['GET', 'POST'])
@super_admin_required
def create_cafe():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()

        maintenance_amount = _parse_amount(
            request.form.get('maintenance_amount', '')
        )

        maintenance_due_date = _parse_date(
            request.form.get('maintenance_due_date', '')
        )

        if not name:
            flash('Cafe name is required.', 'danger')
            return render_template(
                'super_admin/cafe_form.html',
                cafe=None,
                page_title='Add Cafe'
            )

        if maintenance_amount is None:
            flash('Maintenance amount must be a valid non-negative number.', 'danger')
            return render_template(
                'super_admin/cafe_form.html',
                cafe=None,
                page_title='Add Cafe'
            )

        if request.form.get('maintenance_due_date') and not maintenance_due_date:
            flash('Invalid maintenance due date.', 'danger')
            return render_template(
                'super_admin/cafe_form.html',
                cafe=None,
                page_title='Add Cafe'
            )

        existing_cafe = Cafe.query.filter_by(name=name).first()

        if existing_cafe:
            flash('A cafe with this name already exists.', 'danger')
            return render_template(
                'super_admin/cafe_form.html',
                cafe=None,
                page_title='Add Cafe'
            )

        grace_period_end = None

        if maintenance_due_date:
            grace_period_end = maintenance_due_date + timedelta(days=7)

        cafe = Cafe(
            name=name,
            website_slug=generate_unique_slug(name),
            phone=phone or None,
            address=address or None,
            status='active',
            maintenance_amount=maintenance_amount,
            maintenance_due_date=maintenance_due_date,
            maintenance_paid=False,
            maintenance_paid_date=None,
            grace_period_end=grace_period_end,
        )

        try:
            db.session.add(cafe)
            db.session.flush()

            # New cafes start accepting orders.
            _set_cafe_order_status(cafe.id, 'open')

            db.session.commit()

            flash(f'Cafe "{cafe.name}" created successfully.', 'success')
            return redirect(
                url_for(
                    'super_admin_routes.view_cafe',
                    cafe_id=cafe.id
                )
            )

        except Exception:
            db.session.rollback()
            flash('Unable to create cafe. Please try again.', 'danger')

    return render_template(
        'super_admin/cafe_form.html',
        cafe=None,
        page_title='Add Cafe'
    )


@super_admin_bp.route('/cafes/<int:cafe_id>')
@super_admin_required
def view_cafe(cafe_id):
    cafe = Cafe.query.get_or_404(cafe_id)

    admin_count = Admin.query.filter_by(
        cafe_id=cafe.id
    ).count()

    customer_count = 0

    try:
        from models.customer import Customer

        customer_count = Customer.query.filter_by(
            cafe_id=cafe.id
        ).count()
    except Exception:
        customer_count = 0

    return render_template(
        'super_admin/cafe_detail.html',
        cafe=cafe,
        admin_count=admin_count,
        customer_count=customer_count,
        cafe_name='Super Admin'
    )


@super_admin_bp.route('/cafes/<int:cafe_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_cafe(cafe_id):
    cafe = Cafe.query.get_or_404(cafe_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()

        maintenance_amount = _parse_amount(
            request.form.get('maintenance_amount', '')
        )

        maintenance_due_date = _parse_date(
            request.form.get('maintenance_due_date', '')
        )

        if not name:
            flash('Cafe name is required.', 'danger')
            return render_template(
                'super_admin/cafe_form.html',
                cafe=cafe,
                page_title='Edit Cafe'
            )

        if maintenance_amount is None:
            flash('Maintenance amount must be a valid non-negative number.', 'danger')
            return render_template(
                'super_admin/cafe_form.html',
                cafe=cafe,
                page_title='Edit Cafe'
            )

        if request.form.get('maintenance_due_date') and not maintenance_due_date:
            flash('Invalid maintenance due date.', 'danger')
            return render_template(
                'super_admin/cafe_form.html',
                cafe=cafe,
                page_title='Edit Cafe'
            )

        duplicate = (
            Cafe.query
            .filter(
                Cafe.name == name,
                Cafe.id != cafe.id
            )
            .first()
        )

        if duplicate:
            flash('Another cafe already uses this name.', 'danger')
            return render_template(
                'super_admin/cafe_form.html',
                cafe=cafe,
                page_title='Edit Cafe'
            )

        cafe.name = name
        cafe.phone = phone or None
        cafe.address = address or None
        cafe.maintenance_amount = maintenance_amount
        cafe.maintenance_due_date = maintenance_due_date

        if maintenance_due_date:
            cafe.grace_period_end = (
                maintenance_due_date + timedelta(days=7)
            )
        else:
            cafe.grace_period_end = None

        try:
            db.session.commit()

            flash(f'Cafe "{cafe.name}" updated successfully.', 'success')
            return redirect(
                url_for(
                    'super_admin_routes.view_cafe',
                    cafe_id=cafe.id
                )
            )

        except Exception:
            db.session.rollback()
            flash('Unable to update cafe. Please try again.', 'danger')

    return render_template(
        'super_admin/cafe_form.html',
        cafe=cafe,
        page_title='Edit Cafe'
    )


@super_admin_bp.route('/cafes/<int:cafe_id>/hold', methods=['POST'])
@super_admin_required
def hold_cafe(cafe_id):
    cafe = Cafe.query.get_or_404(cafe_id)

    if cafe.status == 'inactive':
        flash('An inactive cafe cannot be placed on hold.', 'warning')
        return redirect(
            url_for(
                'super_admin_routes.view_cafe',
                cafe_id=cafe.id
            )
        )

    cafe.status = 'on_hold'

    try:
        _set_cafe_order_status(cafe.id, 'closed')
        db.session.commit()

        flash(
            f'Cafe "{cafe.name}" has been placed on hold.',
            'warning'
        )

    except Exception:
        db.session.rollback()
        flash('Unable to place cafe on hold.', 'danger')

    return redirect(
        url_for(
            'super_admin_routes.view_cafe',
            cafe_id=cafe.id
        )
    )


@super_admin_bp.route('/cafes/<int:cafe_id>/reactivate', methods=['POST'])
@super_admin_required
def reactivate_cafe(cafe_id):
    cafe = Cafe.query.get_or_404(cafe_id)

    if cafe.status == 'inactive':
        flash(
            'An inactive cafe must be activated through the cafe management process.',
            'warning'
        )
        return redirect(
            url_for(
                'super_admin_routes.view_cafe',
                cafe_id=cafe.id
            )
        )

    cafe.status = 'active'

    try:
        _set_cafe_order_status(cafe.id, 'open')
        db.session.commit()

        flash(
            f'Cafe "{cafe.name}" has been reactivated.',
            'success'
        )

    except Exception:
        db.session.rollback()
        flash('Unable to reactivate cafe.', 'danger')

    return redirect(
        url_for(
            'super_admin_routes.view_cafe',
            cafe_id=cafe.id
        )
    )


@super_admin_bp.route('/cafes/<int:cafe_id>/deactivate', methods=['POST'])
@super_admin_required
def deactivate_cafe(cafe_id):
    cafe = Cafe.query.get_or_404(cafe_id)

    cafe.status = 'inactive'

    try:
        _set_cafe_order_status(cafe.id, 'closed')
        db.session.commit()

        flash(
            f'Cafe "{cafe.name}" has been deactivated.',
            'danger'
        )

    except Exception:
        db.session.rollback()
        flash('Unable to deactivate cafe.', 'danger')

    return redirect(
        url_for(
            'super_admin_routes.view_cafe',
            cafe_id=cafe.id
        )
    )