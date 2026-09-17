import re

from flask import session

from models.cafe import Cafe


def slugify_cafe_name(name):
    """Create a URL-safe cafe slug from its name."""
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

    return slug or 'cafe'


def generate_unique_slug(name, cafe_id=None):
    """Generate a unique website slug for a cafe."""
    base_slug = slugify_cafe_name(name)
    slug = base_slug
    counter = 2

    while True:
        query = Cafe.query.filter_by(website_slug=slug)

        if cafe_id is not None:
            query = query.filter(Cafe.id != cafe_id)

        if not query.first():
            return slug

        slug = f'{base_slug}-{counter}'
        counter += 1


def get_cafe_by_slug(slug):
    """Return an active cafe matching the requested website slug."""
    if not slug:
        return None

    return (
        Cafe.query
        .filter_by(
            website_slug=slug.lower(),
            status='active'
        )
        .first()
    )


def set_active_cafe(cafe):
    """Bind the customer session to a specific cafe."""
    if not cafe:
        return

    session['active_cafe_id'] = cafe.id
    session['active_cafe_slug'] = cafe.website_slug
    session.modified = True


def get_current_cafe():
    """
    Return the cafe selected by the customer website session.

    Falls back to the existing default-cafe behavior so the current
    application continues working during the migration.
    """
    cafe_id = session.get('active_cafe_id')

    if cafe_id:
        cafe = (
            Cafe.query
            .filter_by(
                id=cafe_id,
                status='active'
            )
            .first()
        )

        if cafe:
            return cafe

        session.pop('active_cafe_id', None)
        session.pop('active_cafe_slug', None)

    return get_default_cafe()


def get_default_cafe():
    """
    Return the first active cafe.

    Kept as a compatibility fallback for the existing customer flow.
    """
    cafe = (
        Cafe.query
        .filter_by(status='active')
        .order_by(Cafe.id.asc())
        .first()
    )

    if not cafe:
        cafe = (
            Cafe.query
            .order_by(Cafe.id.asc())
            .first()
        )

    return cafe