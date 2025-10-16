"""User model."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, validator
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models import Category

PASSWORD_HASH_METHOD = "pbkdf2:sha256"


class User(BaseModel):
    """User model."""

    # fmt: off
    ############################################################
    # Primary key (for SQLite)
    ############################################################
    id: int | None = None

    ############################################################
    # Required attributes
    ############################################################
    email         : str      = Field(..., description="Model primary/unique key, eg. foo@bar.com")
    user_id       : str      = Field(..., description="Email hash (used as a 'private' user_id on UI and for Flask UI)")
    password_hash : str      = Field(..., description="Password *HASH*")
    created       : datetime = Field(
        default_factory=datetime.now,
        description="When user instance was created & saved.",
    )

    ############################################################
    # State attributes (broken out from HJSON-based db storage)
    ############################################################
    state_last_search  : str | None     = Field(None, description="Last search term used")
    state_last_searches: list[str]      = Field(default_factory=list, description="Last 10 search terms used")
    state_last_sort    : dict[str, Any] = Field(None, description="Last sort selected")
    state_last_category: Category       = Field(None, description="Current category user is working on")
    # Defaults for the last 2 entries previously were:
    # default={"by": "title", "order": "desc"},
    # default=Category.COOKING_RECIPES,

    ############################################################
    # Other attributes
    ############################################################
    updated   : datetime | None = Field(None, description="When user was last updated (None if just created)")
    last_login: datetime | None = Field(None, description="Last login time (None if still a new user)")
    # fmt: on

    model_config = {
        "use_enum_values": True,
        "arbitrary_types_allowed": True,
        "from_attributes": True,
    }  # For ORM compatibility
    # json_encoders = {datetime: lambda v: v.isoformat() if v else None}

    @classmethod
    def get_or_create(cls, key: str, **kwargs) -> tuple[User, bool]:
        """."""
        try:
            return User.objects.get(email=kwargs.get("email")), False
        except User.DoesNotExist:
            return User(**kwargs).save(), True

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

    def update_search(self, search_term: str) -> bool:
        """Update the user's search state."""
        # Minimally, update the last search the user performed.
        update_user(self, "state_last_search", search_term)

        # If this is the first search performed, easy!
        if not self.state_last_searches:
            update_user(self, "state_last_searches", [search_term])
            return True

        # Convert from string to list...
        print(f"{self.state_last_searches=}")
        print(f"{type(self.state_last_searches)=}")

        # If it's already there, delete it first, then push to the top.
        if search_term in self.state_last_searches:
            self.state_last_searches.remove(search_term)

        # Push the most recent search to the front of the list.
        self.state_last_searches.insert(0, search_term)

        # Save the most recent 10 searches performed.
        update_user(self, "state_last_searches", self.state_last_searches[0:10])

        return True

    @classmethod
    def create(cls, **kwargs) -> User:
        """Do a bit massaging on inbound kwargs before creating a persistable user, specifically:.

        - Create a unique id from a hash of the user's email address (used for url management).
        - Set created timestamp accordingly.
        - Don't store the actual password but a *hash* of it (and delete the password attribute)
        """
        # Required fields:
        kwargs["user_id"] = email_to_hash(kwargs.get("email"))
        kwargs["password_hash"] = generate_password_hash(kwargs.get("password"), method=PASSWORD_HASH_METHOD)
        del kwargs["password"]

        return cls(**kwargs)

    @classmethod
    def factory(cls, **kwargs) -> User:
        """Return a new instance (usually from the database)."""
        # Break out user_state for ease-of-use later
        if user_state_json := kwargs.get("user_state"):
            user_state = json.loads(user_state_json)
            kwargs["state_last_category"] = user_state.get("state_last_category")
            kwargs["state_last_sort"] = user_state.get("state_last_sort")
            del kwargs["user_state"]

        return cls(**kwargs)

    ################################################################################
    # Database Methods
    ################################################################################
    def insert(self) -> int | None:
        if id_ := db.add_user(
            email=self.email,
            user_id=self.user_id,
            created=self.created,
            password_hash=self.password_hash,
            user_state="",
        ):
            return id_
        return None


################################################################################
# Utility Methods
################################################################################
def email_to_hash(email: str) -> str:
    """Return the hash of the specified email address."""
    return hashlib.blake2s(email.encode("utf-8")).hexdigest()


def query_user(email: str | None = None, user_id: str | None = None) -> User | None:
    """Query for the user given either an email-address or a hashed email key."""
    assert email or user_id, "Sorry, at least one of email or user_id must be provided!"
    try:
        if email:
            return db.get_user_by_email(email=email)
            # return User.objects.get(email=email)

        else:
            return db.get_user_by_user_id(user_id=user_id)
            # return User.objects.get(user_id=user_id)
    except User.DoesNotExist:
        ...
    return None


def query_users() -> list[User]:
    """Return all users."""
    return db.get_all_users()
    # return User.objects()


def update_user(user: User, attr, value) -> User:
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
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return 0
    return user.delete()  # Returns the number of rows deleted
