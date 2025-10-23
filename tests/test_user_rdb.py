"""Test User data type."""

import json

import peewee
import pydantic
import pytest
from box import Box
from werkzeug.security import check_password_hash

from app import db
from app.models.user_rdb import User


################################################################################
# Utility methods
################################################################################
def get_current_row_count():
    return len(list(User.select()))


################################################################################
# Tests
################################################################################
def test_init_missing_attrs(app):
    """Test that a simple class instantiation won't work as there ARE required fields."""
    User()
    # with pytest.raises(pydantic.ValidationError):
    #     User()


def test_user_factory(app, user):
    # Test
    assert user.last_login is None
    assert user.updated is None
    assert user.id is None

    # Confirm: Check user_id handling (must match info in conftest.py!)
    assert user.email == "test@foo.com"
    assert user.user_id

    # Confirm: Check password handling (ie, we have a hash and NOT the password itself)
    assert not hasattr(user, "password")
    assert user.password_hash
    assert check_password_hash(user.password_hash, "aPassword")  # Note hardcode to match conftest.py
    assert user.check_password("aPassword")  # ibid


def test_user_save(app, user: User):
    """Test that we can successfully save a user instance."""
    row_count = get_current_row_count()
    assert not user.id
    assert not user.updated

    # Test
    user.save()

    # Confirm
    assert isinstance(user, User)
    assert user.id
    assert not user.updated  # We haven't done any updates yet!
    assert get_current_row_count() == row_count + 1


def test_user_delete_existing(app, user: User):
    # Setup
    user.save()

    assert get_current_row_count() == 1

    # Test
    count = User.delete().execute()

    # Confirm
    assert count == 1
    assert get_current_row_count() == 0


def test_user_delete_non_existing(app):
    """Test that delete an instance that hasn't been saved yet is OK."""
    # Setup
    tst_user_parms = {
        "id": 99,
        "email": "test@foo.com",
        "password": "aPassword",
    }
    user = User.factory(**tst_user_parms)

    # Test
    count = user.delete_instance()

    # Confirm
    assert 0 == count


def test_query_user_email(app, user: User):
    # Setup
    user.save()
    assert user.email

    # Test
    q_users = User.select().where(User.email == user.email)

    # Confirm
    assert len(q_users) == 1
    q_user = q_users[0]

    assert isinstance(q_user, User)
    assert q_user.id
    assert q_user.email == user.email


def test_query_user_user_id(app, user: User):
    # Setup
    user.save()

    # Test
    users = User.select().where(User.user_id == user.user_id)

    # Confirm
    assert len(users) == 1
    q_user = users[0]
    assert isinstance(q_user, User)
    assert q_user.id
    assert q_user.email == user.email


def test_non_existent_user(app):
    results = User.select().where(User.email == "asdfasdfasdf@asdfasdfadsf.com")
    assert not results


def tst_update_user_direct(app, user):
    """Test ability to update attributes of a user instance."""
    # Setup
    user.save()

    # Test (by updating a single attribute)
    user.state_last_category = "Cooking-Skills"
    user.save()

    # Confirm by requerying
    updated_user = User.select().where(User.email == user.email)[0]
    assert updated_user.updated
    assert "Cooking-Skills" == updated_user.state_last_category


def test_payload_str(app, user):
    """Test ability to update payload of a string."""
    # Setup
    user.save()
    assert not user.payload

    # Test (by updating a single payload str attribute.)
    user.payload = Box({"user_state": {"last_search": "search term 1"}})

    user.payload.user_state.last_search = "search term 1"
    user.save()

    # Confirm
    user_saved = User.select().where(User.email == user.email)[0]
    assert "search term 1" == user_saved.payload.user_state.last_search


def test_payload_list_set(app, user):
    """Test ability to update payload of a list."""
    # Setup
    user.save()
    assert not user.payload

    # Test (by updating a single payload str attribute.)
    user.payload = Box({"user_state": {"last_searches": ["search entry 1 of 1"]}})
    user.save()

    # Confirm
    user_saved = User.select().where(User.email == user.email)[0]
    assert ["search entry 1 of 1"] == user_saved.payload.user_state.last_searches


def test_payload_list_append(app, user):
    """Test ability to update payload of a list."""
    # Setup
    user.payload = Box({"user_state": {"last_searches": ["entry 1 of 2"]}})
    user.save()
    assert ["entry 1 of 2"] == user.payload.user_state.last_searches

    # Test (by updating a single payload str attribute.)
    b_payload = user.payload
    b_payload.user_state.last_searches.append("entry 2 of 2")
    user.payload = b_payload
    user.save()

    # Confirm
    user_saved = User.select().where(User.email == user.email)[0]
    assert ["entry 1 of 2", "entry 2 of 2"] == user_saved.payload.user_state.last_searches


def test_update_on_save(app, user):
    """Test overridden save method obo "updated" attribute."""
    # Setup
    user.save()
    assert user.updated is None

    # Test (by updating a single attribute)
    user.payload = Box()
    user.save()

    assert user.updated


def tst_update_complex_state_attributes_dict(app, user):
    """Test ability to update dict state attribute of a user instance."""
    # Setup
    Users.save(user)

    # Test (by updating a single attribute)
    Users.update(user, "last_sort", {"by": "title", "order": "asc"})

    # Confirm (user in the database is actually created and matching)
    updated_user = Users.query(email=user.email)
    assert updated_user.updated
    assert {"by": "title", "order": "asc"} == updated_user.last_sort


def tst_user_update_password(app, user):
    # Setup
    Users.save(user)
    old_password_hash = user.password_hash

    # Test
    Users.update(user, "password", "newPassword")

    # Confirm
    q_user = Users.query(email=user.email)
    assert q_user.password_hash != old_password_hash
    assert user.password_hash == q_user.password_hash


def tst_user_update_email(app, user):
    # Setup
    Users.save(user)
    old_user_id = user.user_id

    # Test
    Users.update(user, "email", "bar@foo.com")
    assert user.email == "bar@foo.com"
    assert user.user_id != old_user_id

    # Confirm
    q_user = Users.query(email="bar@foo.com")
    assert q_user.email == "bar@foo.com"
    assert user.user_id == q_user.user_id


def tst_user_update_other_attribute(app, user):
    # Setup
    Users.save(user)
    old_category = user.last_category

    # Test
    Users.update(user, "last_category", "Cooking-Skills")

    # Confirm
    assert user.last_category != old_category
    assert user.last_category == "Cooking-Skills"


# def tst_get_default_view(app, user):
#     # Setup
#     user.insert()

#     # Test
#     view = user.get_default_view()
#     assert view
#     assert isinstance(view, UserView)
