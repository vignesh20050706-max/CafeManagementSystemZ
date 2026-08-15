from models.cafe import Cafe


def get_default_cafe():
    """Return the first active cafe.

    Used for the current single-cafe customer flow.
    Super Admin / multi-cafe selection will be added later.
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