"""User model."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator, validator
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models import Category

PASSWORD_HASH_METHOD = "pbkdf2:sha256"


class User(BaseModel):
    """User model."""

    model_config = ConfigDict(use_enum_values=True, arbitrary_types_allowed=True)

    # fmt: off
    ############################################################
    # Primary key (for SQLite)
    ############################################################
    id: int | None = None # Won't exist until we save to db.

    ############################################################
    # Required attributes
    ############################################################
    email         : str      = Field(..., description="Model primary/unique key, eg. foo@bar.com")
    user_id       : str      = Field(..., description="Email hash (used as a 'private' user_id on UI and for Flask UI)")
    password_hash : str      = Field(..., description="Password *HASH*")
    created       : datetime = Field(default_factory=datetime.now, description="When user instance was created & saved")

    ############################################################
    # State attributes (derived from 'user_state' text db field)
    ############################################################
    state_last_search  : str | None     = Field(None, description="Last search term used")
    state_last_searches: list[str]      = Field(default_factory=list, description="Last 10 search terms used")
    state_last_sort    : dict[str, str] = Field(default_factory=dict, description="Last sort selected")
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

    @model_validator(mode="before")
    @classmethod
    def explode_json_fields(cls, data: Any) -> Any:
        if isinstance(data, dict) and "user_state" in data:
            # Coming from DB - explode the JSON
            user_state_json = data.get("user_state", "{}")
            if isinstance(user_state_json, str):
                user_state = json.loads(user_state_json)
            else:
                user_state = user_state_json

            # fmt: off
            data.update({
                "state_last_search"   : user_state.get("state_last_search"   , ""),
                "state_last_searches" : user_state.get("state_last_searches" , []),
                "state_last_sort"     : user_state.get("state_last_sort"     , {}),
                "state_last_category" : user_state.get("state_last_category" , ""),
            })
            # fmt: on

            # Remove the raw JSON field
            data.pop("user_state", None)
        return data

    def implode_json_fields(self) -> dict[str, Any]:
        """Serialize for database storage."""
        user_state = {
            key: value
            for key, value in {
                "state_last_search": self.state_last_search,
                "state_last_searches": self.state_last_searches,
                "state_last_sort": self.state_last_sort,
                "state_last_category": self.state_last_category,
            }.items()
            if value is not None
        }
        return {
            "id": self.id,
            "email": self.email,
            "user_id": self.user_id,
            "password_hash": self.password_hash,
            "user_state": json.dumps(user_state),
            "created": self.created,
            "updated": self.updated,
        }

    # @classmethod
    # def get_or_create(cls, key: str, **kwargs) -> tuple[User, bool]:
    #     """."""
    #     try:
    #         return User.objects.get(email=kwargs.get("email")), False
    #     except User.DoesNotExist:
    #         return User(**kwargs).save(), True

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
        - Don't store the actual password but a *hash* of it (and delete the password attribute)
        """
        kwargs["user_id"] = email_to_hash(kwargs.get("email"))
        kwargs["password_hash"] = generate_password_hash(kwargs.get("password"), method=PASSWORD_HASH_METHOD)
        del kwargs["password"]  # Insurance...make sure this *NEVER* gets near the db

        return cls(**kwargs)

    ################################################################################
    # Database Methods
    ################################################################################
    @classmethod
    def factory(cls, **kwargs) -> User:
        """Return a new application instance from a database instance."""
        return cls(**User.explode_json_fields(kwargs))


################################################################################
# Utility Methods
################################################################################
def email_to_hash(email: str) -> str:
    """Return the hash of the specified email address."""
    return hashlib.blake2s(email.encode("utf-8")).hexdigest()


def query_user(email: str | None = None, user_id: str | None = None) -> User | None:
    """Query for the user given either an email-address or a hashed email key."""
    assert email or user_id, "Sorry, at least one of email or user_id must be provided!"
    if email:
        with db.with_row_factory(User) as db_user:
            return db.get_user_by_email(email=email)
    else:
        with db.with_row_factory(User) as db_user:
            return db.get_user_by_user_id(user_id=user_id)
    return None  # IS THIS CORRECT HERE?


def query_users() -> list[User]:
    """Return all users."""
    with db.with_row_factory(User) as db_user:
        return db_user.get_all_users()


def user_save(user: User) -> User | None:
    """Save instance back to DB."""
    db_data = user.implode_json_fields()
    try:
        if user.id is None:
            # Insert new record
            result = db.insert_user(
                email=db_data["email"],
                user_id=db_data["user_id"],
                password_hash=db_data["password_hash"],
                user_state=db_data["user_state"],
                created=datetime.now(),
            )
            user.id = result  # aiosql returns lastrowid for insert
        else:
            # Update existing record
            db.update_user(
                id=user.id,
                email=db_data["email"],
                user_id=db_data["user_id"],
                password_hash=db_data["password_hash"],
                user_state=db_data["user_state"],
                created=db_data["created"],
                updated=datetime.now(),
            )
        return user

    except Exception as e:
        print(f"Database error: {e}")
        return None


def user_update(user: User, attr, value) -> User:
    """Update the specified user's attribute with the specified new value."""
    if attr == "password":
        # Password update needs to calculate and store a hash, ie. *not* the password itself!
        user.password_hash = generate_password_hash(value, method=PASSWORD_HASH_METHOD)
        user.updated = datetime.utcnow
        user_save(user)

    else:
        # All other attributes..
        setattr(user, attr, value)
        user.updated = datetime.utcnow
        user_save(user)

    if attr == "email":
        # Since we use email hash as our core internal ID, we *also* need
        # to calculate a new user id and save it away as well.
        user.email = value
        user.user_id = email_to_hash(user.email)
        user.updated = datetime.utcnow
        user_save(user)

    return user


def user_delete(user: User) -> int:
    """Delete the user with given email address, return 1 if successfully done."""
    return db.delete_user_by_id(id=user.id)
