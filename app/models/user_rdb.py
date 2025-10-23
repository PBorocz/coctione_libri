"""User model."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from box import Box
from peewee import CharField, DateField, Model, SmallIntegerField
from pydantic import BaseModel, ConfigDict, Field, model_validator, validator
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models import Category

PASSWORD_HASH_METHOD = "pbkdf2:sha256"


class User(Model):
    """User model."""

    # fmt: off
    ############################################################
    # Required attributes
    ############################################################
    # email         : str      = Field(..., description="Model primary/unique key, eg. foo@bar.com")
    # user_id       : str      = Field(..., description="Email hash (used as a 'private' user_id on UI and for Flask UI)")
    # password_hash : str      = Field(..., description="Password *HASH*")
    # created       : datetime = Field(default_factory=datetime.now, description="When user instance was created & saved")
    id            = SmallIntegerField(null=True)
    email         = CharField(unique=True)
    user_id       = CharField()
    password_hash = CharField()
    created       = DateField(default=datetime.now())
    updated       = DateField(null=True)
    last_login    = DateField(null=True)
    s_payload     = CharField(null=True)
    # state_last_search  : str | None     = Field(None, description="Last search term used")
    # state_last_searches: list[str]      = Field(default_factory=list, description="Last 10 search terms used")
    # state_last_sort    : dict[str, str] = Field(default_factory=dict, description="Last sort selected")
    # state_last_category: Category       = Field(default=Category.COOKING_RECIPES, description="Current category user is working on")

    # Defaults for the last 2 entries previously were:
    # default={"by": "title", "order": "desc"},
    # default=Category.COOKING_RECIPES,

    ############################################################
    # Other attributes
    ############################################################
    # updated   : datetime | None = Field(None, description="When user was last updated (None if just created)")
    # last_login: datetime | None = Field(None, description="Last login time (None if still a new user)")
    # id        : int      | None = None # Won't exist until we save to disk
    # id        : int      | None = None # Won't exist until we save to disk
    # fmt: on

    def save(self, *args, **kwargs):
        # Only update last_updated on existing records (updates)
        if self._pk is not None:  # Record exists, this is an update
            self.updated = datetime.now()
        return super().save(*args, **kwargs)

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
# Utility methods
################################################################################
def email_to_hash(email: str) -> str:
    """Return the hash of the specified email address."""
    return hashlib.blake2s(email.encode("utf-8")).hexdigest()


################################################################################
# Database namespace..
################################################################################
# class Users:
#     @classmethod
#     def factory(cls, **kwargs) -> User:
#         """Return a new application instance from a database instance."""
#         print("Users.factory...")
#         return User(**cls.explode_json_fields(kwargs))

#     @classmethod
#     def implode_json_fields(cls: Users, user: User) -> dict[str, Any]:
#         """Serialize JSON fields in preparation database storage."""
#         # fmt: off
#         user_state = {
#             key: value
#             for key, value in {
#                 "state_last_search"   : user.state_last_search,
#                 "state_last_searches" : user.state_last_searches,
#                 "state_last_sort"     : user.state_last_sort,
#                 "state_last_category" : user.state_last_category,
#             }.items()
#             if value is not None
#         }
#         return {
#             "id"            : user.id,
#             "email"         : user.email,
#             "user_id"       : user.user_id,
#             "password_hash" : user.password_hash,
#             "user_state"    : json.dumps(user_state),
#             "created"       : user.created,
#             "updated"       : user.updated,
#         }
#         # fmt: off

#     @classmethod
#     def explode_json_fields(cls, data: Any) -> Any:
#         if isinstance(data, dict) and "user_state" in data:
#             # Coming from DB - explode the JSON
#             user_state_json = data.get("user_state", "{}")
#             if isinstance(user_state_json, str):
#                 user_state = json.loads(user_state_json)
#             else:
#                 user_state = user_state_json

#             # fmt: off
#             data.update({
#                 "state_last_search"   : user_state.get("state_last_search"   , ""),
#                 "state_last_searches" : user_state.get("state_last_searches" , []),
#                 "state_last_sort"     : user_state.get("state_last_sort"     , {}),
#                 "state_last_category" : user_state.get("state_last_category" , ""),
#             })
#             # fmt: on

#             # Remove the raw JSON field
#             data.pop("user_state", None)
#         return data

#     @classmethod
#     def users(cls: Users) -> list[User]:
#         """Return all users."""
#         with db.with_row_factory(Users) as db_user:
#             print(f"{db_user._anodb._conn.row_factory=}")
#             breakpoint()

#             return db_user.get_all_users()

#     # @classmethod
#     # def query(cls: Users, attr: str, value: Any) -> User | None:
#     #     """Query for the user given either an email-address or a hashed email key."""
#     #     sql_ = f"SELECT * FROM user WHERE {attr} = ?"
#     #     cursor = db._conn.cursor()
#     #     for row in cursor.execute(sql_, [value]):
#     #         columns = [col[0] for col in cursor.description]
#     #         return cls.factory(**dict(zip(columns, row, strict=True)))
#     #     return None

#     @classmethod
#     def query(cls: Users, **kwargs) -> User | None:
#         """Query for a single user (or None) given any number of attribute-value pairs.

#         We're not using the template-based SQL as we want this to have dynamic args.
#         """
#         if not kwargs:
#             raise ValueError("At least one query parameter must be provided")

#         # Build sql with WHERE clause of ANDed conditions
#         where_conditions = [f"{attr} = ?" for attr in kwargs.keys()]
#         where_clause = " AND ".join(where_conditions)
#         sql_ = f"SELECT * FROM user WHERE {where_clause}"
#         cursor = db._conn.cursor()
#         for row in cursor.execute(sql_, list(kwargs.values())):
#             columns = [col[0] for col in cursor.description]
#             return cls.factory(**dict(zip(columns, row, strict=True)))
#         return None

#     @classmethod
#     def save(cls: Users, user: User) -> User | None:
#         """Save instance back to DB (either new or existing)."""
#         db_data = cls.implode_json_fields(user)
#         if user.id is None:
#             # Insert new record
#             result = db.insert_user(
#                 email=db_data["email"],
#                 user_id=db_data["user_id"],
#                 password_hash=db_data["password_hash"],
#                 user_state=db_data["user_state"],
#                 created=datetime.now(),
#             )
#             user.id = result  # aiosql returns lastrowid for insert
#         else:
#             # Update existing record (note some fields may not be set yet)
#             now_ = datetime.now()
#             db.update_user(
#                 email=db_data["email"],
#                 user_id=db_data["user_id"],
#                 created=db_data["created"],
#                 password_hash=db_data["password_hash"],
#                 user_state=db_data.get("user_state", None),
#                 last_login=db_data.get("last_login", None),
#                 updated=now_,
#                 id=user.id,
#             )
#             user.updated = now_

#         return user

#     @classmethod
#     def update(cls: Users, user: User, attr, value) -> User:
#         """Update the specified user's attribute with the specified new value."""
#         if attr == "password":
#             # Password update needs to calculate and store a hash, ie. *not* the password itself!
#             user.password_hash = generate_password_hash(value, method=PASSWORD_HASH_METHOD)

#         elif attr == "email":
#             # Since we use email hash as our core internal ID, we *also* need
#             # to calculate a new user id and save it away as well.
#             user.email = value
#             user.user_id = email_to_hash(user.email)

#         else:
#             # All other attributes..
#             setattr(user, attr, value)

#         cls.save(user)

#         return user

#     @classmethod
#     def update_search(cls: Users, user: User, search_term: str) -> User:
#         """Update the user's search state."""
#         # Minimally, update the last search the user performed.
#         db.update_user(user, "state_last_search", search_term)

#         # If this is the first search performed, easy!
#         if not user.state_last_searches:
#             db.update_user(user, "state_last_searches", [search_term])
#             return True

#         # Convert from string to list...
#         print(f"{user.state_last_searches=}")
#         print(f"{type(user.state_last_searches)=}")

#         # If it's already there, delete it first, then push to the top.
#         if search_term in user.state_last_searches:
#             user.state_last_searches.remove(search_term)

#         # Push the most recent search to the front of the list.
#         user.state_last_searches.insert(0, search_term)

#         # Save the most recent 10 searches performed.
#         db.update_user(user, "state_last_searches", user.state_last_searches[0:10])

#         return user

#     @classmethod
#     def delete(cls: Users, user: User) -> int:
#         """Delete the user with given email address, return 1 if successfully done."""
#         return db.delete_user_by_id(id=user.id)
