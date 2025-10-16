"""Test User data type."""

import pydantic
import pytest
from werkzeug.security import check_password_hash

from app import db
from app.models.user_rdb import User


################################################################################
# Utility methods
################################################################################
def __get_row_count():
    return len(list(db.get_all_users()))


def __query_user(email: str) -> User:
    return User.find_one(User.email == email).run()


################################################################################
# Tests
################################################################################
def test_init_missing_attrs(app):
    """Test that a simple class instantiation won't work as there ARE required fields."""
    with pytest.raises(pydantic.ValidationError):
        User()


def test_user_factory(app, user):
    # Test
    assert user.last_login is None
    assert user.updated is None
    assert user.created

    # Confirm: Check user_id handling (must match info in conftest.py!)
    assert user.email == "test@foo.com"
    assert user.user_id

    # Confirm: Check password handling (ie, we have a hash and NOT the password itself)
    assert not hasattr(user, "password")
    assert user.password_hash
    assert check_password_hash(user.password_hash, "aPassword")  # Note hardcode to match conftest.py
    assert user.check_password("aPassword")  # ibid


def test_delete_user(app, user: User):
    # Setup
    id_ = user.insert()
    assert __get_row_count() == 1

    # Test
    db.delete_user_by_id(id=id_)

    # Confirm
    assert __get_row_count() == 0


def tst_insert_and_query_user_s(app, user: User):
    # Test
    row_count = __get_row_count()
    assert not user.updated
    user.insert()
    assert user.id
    assert user.updated

    # Confirm
    assert __get_row_count() == row_count + 1

    q_user = __query_user(user.email)
    assert q_user.id == user.id
    assert q_user.email == user.email
    assert q_user.timezone == user.timezone
    assert q_user.favorites == user.favorites
    assert q_user.views == user.views


def tst_non_existent_user(app):
    results = User.find(User.email == "asdfasdfasdf@asdfasdfadsf.com").run()
    assert not results


def tst_update_user_simple(app, user):
    # Setup
    assert not user.updated
    user.insert()
    assert __get_row_count() == 1

    # Test (by updating a single attribute)
    user.sd_lineup = "another"
    user.save()

    # Confirm that user in the database is actually created and matching.
    updated_user = __query_user(user.email)
    assert "another" == updated_user.sd_lineup
    assert updated_user.updated


def tst_update_user_password(app, user):
    # Setup
    user.insert()
    old_password_hash = user.password_hash

    # Test
    update_user(user, "password", "newPassword")
    assert user.password_hash != old_password_hash
    assert not hasattr(user, "password")

    # Confirm
    queried_user = __query_user(user.email)
    assert queried_user
    assert user.password_hash == queried_user.password_hash


def tst_update_user_email(app, user):
    # Setup
    user.insert()

    # Test
    old_user_id = user.user_id
    update_user(user, "email", "bar@foo.com")
    assert user.email == "bar@foo.com"
    assert user.user_id != old_user_id

    # Confirm
    queried_user = __query_user("bar@foo.com")
    assert queried_user.email == "bar@foo.com"
    assert user.user_id == queried_user.user_id


def tst_get_default_view(app, user):
    # Setup
    user.insert()

    # Test
    view = user.get_default_view()
    assert view
    assert isinstance(view, UserView)
