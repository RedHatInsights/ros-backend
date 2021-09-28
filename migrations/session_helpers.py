from contextlib import contextmanager

from alembic import op
from sqlalchemy.orm.session import Session


__all__ = ("session")


@contextmanager
def session():
    """Provide a transactional scope around a series of operations."""
    bind = op.get_bind()
    session = Session(bind)
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    else:
        session.commit()
