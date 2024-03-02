"""User model."""
from __future__ import annotations

import hashlib
from datetime import datetime

import mongoengine as me_
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import Category

PASSWORD_HASH_METHOD = "pbkdf2:sha256"


class Users(me_.Document):

    """User model."""

    # ---------------------
    # Required attributes:
    # ---------------------
    # Model primary/unique key, eg. foo@bar.com
    email = me_.EmailField(required=True, unique=True)

    # Email hash (used as a "private" user_id on UI)
    user_id = me_.StringField(required=True)

    # Password *HASH*
    password_hash = me_.StringField(required=True)

    # When user was first saved to database.
    created = me_.DateTimeField(required=True, default=datetime.utcnow)

    # Current category user is working on.
    category = me_.StringField(required=True, choices=[d.value for d in Category], default=Category.COOKING_RECIPES)

    # ---------------------
    # Optional attributes:
    # ---------------------
    # When user was last updated (None if just created
    updated = me_.DateTimeField()
    # Last login time, eg. # 2022-02-02T03:00:00+00:00
    last_login = me_.DateTimeField()

    @classmethod
    def get_or_create(cls, key: str, **kwargs) -> tuple[Users, bool]:
        """."""
        try:
            return Users.objects.get(email=kwargs.get("email")), False
        except Users.DoesNotExist:
            return Users(**kwargs).save(), True

    ################################################################################
    # Flask Login Methods
    ################################################################################
    def get_id(self):
        """Get the user's id...SPECIAL METHOD FOR FLASKLOGIN, DON'T DELETE!."""
        return self.user_id

    def check_password(self, password) -> bool:
        """Is the password provided a match with that stored?."""
        return check_password_hash(self.password_hash, password)

    def is_authenticated(self):
        """Is the user authenticated?."""
        return True

    def is_active(self):
        """Is the user active?."""
        return True

    def is_anonymous(self):
        """Is the user anonymous?."""
        return False

    def save(self, *args, **kwargs):
        """Override to get updated attr set."""
        self.updated = datetime.utcnow()
        return super().save(*args, **kwargs)

    @classmethod
    def factory(cls, **kwargs) -> Users:
        """Do a bit massaging on inbound kwargs before creating a persistable user, specifically:.

        - Create a unique id from a hash of the user's email address (used for url management).
        - Set created timestamp accordingly.
        - Don't store the actual password but a *hash* of it (and delete the password attribute)
        """
        # Required fields:
        kwargs["user_id"] = email_to_hash(kwargs.get("email"))
        kwargs["created"] = datetime.utcnow()
        kwargs["password_hash"] = generate_password_hash(kwargs.get("password"), method=PASSWORD_HASH_METHOD)
        del kwargs["password"]

        # Fields that can only come from updates...
        kwargs["updated"] = None
        kwargs["last_login"] = None

        return cls(**kwargs)


################################################################################
# Utility Methods
################################################################################
def email_to_hash(email: str) -> str:
    """Return the hash of the specified email address."""
    return hashlib.blake2s(email.encode("utf-8")).hexdigest()


def query_user(email: str | None = None, user_id: str | None = None) -> Users | None:
    """Query for the user given either an email-address or a hashed email key."""
    assert email or user_id, "Sorry, at least one of email or user_id must be provided!"
    try:
        if email:
            return Users.objects.get(email=email)
        else:
            return Users.objects.get(user_id=user_id)
    except Users.DoesNotExist:
        ...
    return None


def query_users() -> list[Users]:
    """Return all users."""
    return Users.objects()


def update_user(user: Users, attr, value) -> Users:
    """Update the specified user's attribute with the specified new value."""
    if attr == "password":
        # Password update needs to calculate and store a hash, ie. *not* the password itself!
        user.password_hash = generate_password_hash(value, method=PASSWORD_HASH_METHOD)
        user.updated = datetime.utcnow
        user.save()

    else:
        # All other attributes..
        setattr(user, attr, value)
        user.updated = datetime.utcnow
        user.save()

    if attr == "email":
        # Since we use email hash as our core internal ID, we *also* need
        # to calculate a new user id and save it away as well.
        user.email = value
        user.user_id = email_to_hash(user.email)
        user.updated = datetime.utcnow
        user.save()

    return user


def delete_user(email: str) -> int:
    """Delete the user with given email address, return 1 if successfully done."""
    try:
        user = Users.objects.get(email=email)
    except Users.DoesNotExist:
        return 0
    return user.delete()  # Returns the number of rows deleted
