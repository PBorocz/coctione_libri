"""Test User data type."""

import pydantic
import pytest
from werkzeug.security import check_password_hash

from app import db
from app.models.user_rdb import User, update_user


################################################################################
# Utility methods
################################################################################
def __get_row_count():
    return len(list(db.get_all_users()))


def __query_user(email: str) -> User:
    with db.with_row_factory(User) as dbq:
        return dbq.get_user_by_email(email=email)


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


def tst_delete_user(app, user: User):
    # Setup
    id_ = user.insert()
    assert __get_row_count() == 1

    # Test
    db.delete_user_by_id(id=id_)

    # Confirm
    assert __get_row_count() == 0


def test_insert(app, user: User):
    """Test that we can successfully save a user instance."""
    row_count = __get_row_count()
    assert not user.id
    assert not user.updated

    # Test
    id_ = user.save()

    # Confirm
    assert id_
    assert __get_row_count() == row_count + 1


def test_query_user(app, user: User):
    # Setup
    user.save()

    # Test
    q_user = __query_user(user.email)

    # Confirm
    assert isinstance(q_user, User)
    assert q_user.id
    assert q_user.email == user.email
    assert q_user.state_last_search == user.state_last_search
    assert q_user.state_last_category == user.state_last_category


def test_non_existent_user(app):
    results = db.get_user_by_email(email="asdfasdfasdf@asdfasdfadsf.com")
    assert not results


def test_update_user_direct(app, user):
    """Test ability to update attributes of a user instance."""
    # Setup
    user.save()

    # Test (by updating a single attribute)
    user.state_last_category = "Cooking-Skills"
    user.save()

    # Confirm (user in the database is actually created and matching)
    updated_user = __query_user(user.email)
    assert updated_user.updated
    assert "Cooking-Skills" == updated_user.state_last_category


def test_update_user_password(app, user):
    # Setup
    user.save()
    old_password_hash = user.password_hash

    # Test
    update_user(user, "password", "newPassword")

    # Confirm
    q_user = __query_user(user.email)
    assert q_user.password_hash != old_password_hash
    assert user.password_hash == q_user.password_hash


def test_update_user_email(app, user):
    # Setup
    user.save()
    old_user_id = user.user_id

    # Test
    update_user(user, "email", "bar@foo.com")
    assert user.email == "bar@foo.com"
    assert user.user_id != old_user_id

    # Confirm
    q_user = __query_user("bar@foo.com")
    assert q_user.email == "bar@foo.com"
    assert user.user_id == q_user.user_id


# def tst_get_default_view(app, user):
#     # Setup
#     user.insert()

#     # Test
#     view = user.get_default_view()
#     assert view
#     assert isinstance(view, UserView)
