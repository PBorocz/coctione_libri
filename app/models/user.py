"""User model."""

from __future__ import annotations

import hashlib
from datetime import datetime

from box import Box
from peewee import CharField, DateField, Model, SmallIntegerField
from werkzeug.security import check_password_hash, generate_password_hash

PASSWORD_HASH_METHOD = "pbkdf2:sha256"


class User(Model):
    """User model."""

    # fmt: off
    id            = SmallIntegerField(primary_key=True, help_text="DB auto increment id")
    email         = CharField(unique=True, help_text="Model primary/unique key, eg. foo@bar.com")
    user_id       = CharField(help_text="Email hash (used as a 'private' user_id on UI and for Flask UI)")
    password_hash = CharField(help_text="Password *HASH*")
    created       = DateField(default=datetime.now(), help_text="Datetime first saved.")
    updated       = DateField(null=True, help_text="Datetime last updated.")
    last_login    = DateField(null=True, help_text="Datetime user last logged in.")
    s_payload     = CharField(null=True, help_text="JSON payload")
    # fmt: on

    def save(self, *args, **kwargs):
        """Override save method to set updated attr on actual updates."""
        self.updated = datetime.now() if self._pk is not None else None
        return super().save(*args, **kwargs)

    def set_email(self, new_email: str) -> bool:
        self.email = new_email
        self.user_id = email_to_hash(new_email)

    def set_password(self, new_password: str) -> bool:
        self.password_hash = generate_password_hash(new_password, method=PASSWORD_HASH_METHOD)

    ################################################################################
    # Payload Properties
    ################################################################################
    @property
    def payload(self):
        """Essentially, 'unpack' our string json payload."""
        return Box.from_json(self.s_payload, default_box=True) if self.s_payload else Box(default_box=True)

    @payload.setter
    def payload(self, b_payload):
        """Essentially, 'repack' our string json payload."""
        self.s_payload = b_payload.to_json()

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

    ################################################################################
    @classmethod
    def factory(cls, **kwargs) -> User:
        """Do a bit massaging on inbound kwargs before creating a persistable user, specifically:.

        - Create a unique id from a hash of the user's email address (used for url management).
        - Don't store the actual password but a *hash* of it (and delete the password attribute)
        """
        kwargs["user_id"] = email_to_hash(kwargs.get("email"))
        kwargs["password_hash"] = generate_password_hash(kwargs.get("password"), method=PASSWORD_HASH_METHOD)
        del kwargs["password"]  # Insurance...make sure this *NEVER* gets anywhere else!

        return cls(**kwargs)

    ################################################################################
    def update_search(self, search_term: str) -> bool:
        """Update the user's search state, add if not duplicate and limit to last 10."""
        payload = self.payload

        # Minimally, update the last search the user performed.
        payload.user_state.last_search = search_term

        # If this is the first search performed, easy
        if not payload.user_state.last_searches:
            payload.user_state.last_searches = [search_term]
        else:
            # If it's already there, delete it first, then push to the top.
            if search_term in payload.user_state.last_searches:
                payload.user_state.last_searches.remove(search_term)

            # Push the most recent search to the front of the list.
            payload.user_state.last_searches.insert(0, search_term)

            # Limit to the most recent 10 searches performed.
            payload.user_state.last_searches = payload.user_state.last_searches[0:10]

        self.payload = payload
        self.save()
        return True

    ################################################################################
    def can_delete(self) -> bool:
        if "peter" in self.email.casefold():
            return True
        return False


################################################################################
# Utility methods
################################################################################
def email_to_hash(email: str) -> str:
    """Return the hash of the specified email address."""
    return hashlib.blake2s(email.encode("utf-8")).hexdigest()


def query_user(email: str | None = None, user_id: str | None = None) -> User | None:
    """Query for the user given either an email-address or a hashed email key."""
    assert email or user_id, "Sorry, at least one of email or user_id must be provided!"
    try:
        if email:
            return User.get(User.email == email)
        else:
            return User.get(User.user_id == user_id)
    except User.DoesNotExist:
        ...
    return None
