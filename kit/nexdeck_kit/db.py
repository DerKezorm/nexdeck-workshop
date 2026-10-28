"""No database in the kit."""

from contextlib import contextmanager


@contextmanager
def db_session():
    yield None
