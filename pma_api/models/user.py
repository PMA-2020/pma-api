"""Metadata table."""
from flask_user import UserMixin

from . import db


class User(db.Model, UserMixin):
    """User

    Regarding collation: The collation='NOCASE' is required to search case
    insensitively when USER_IFIND_MODE is 'nocase_collation'.

    Example:
        username = db.Column(db.String(100, collation='NOCASE'), ...)

    Warnings:
        PostgreSQL does not allow for (utf-8) 'NOCASE' collation.
    """

    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column('is_active', db.Boolean(), nullable=False,
                       server_default='1')
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')
    email_confirmed_at = db.Column(db.DateTime())
    first_name = db.Column(db.String(100), nullable=False, server_default='')
    last_name = db.Column(db.String(100), nullable=False, server_default='')
