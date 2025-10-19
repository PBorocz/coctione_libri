"""Test User data type."""

import pydantic
import pytest
from werkzeug.security import check_password_hash

from app import db
from app.models.user_rdb import User, Users


################################################################################
# Utility methods
################################################################################
def get_current_row_count():
    return len(list(db.get_all_users()))


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
    assert user.id is None
    assert user.created

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
    user = Users.save(user)

    # Confirm
    assert isinstance(user, User)
    assert user.id
    assert not user.updated  # We haven't done any updates yet!
    assert get_current_row_count() == row_count + 1


def test_user_delete(app, user: User):
    # Setup
    user = Users.save(user)
    assert get_current_row_count() == 1

    # Test
    count = Users.delete(user)

    # Confirm
    assert count == 1
    assert get_current_row_count() == 0


def test_user_delete_non_existing(app):
    # Setup
    tst_user_parms = {
        "id": 99,
        "email": "test@foo.com",
        "password": "aPassword",
        "state_last_search": "burmese",
        "state_last_category": "Recipes",
    }
    user = User.create(**tst_user_parms)

    # Test
    count = Users.delete(user)

    # Confirm
    assert 0 == count


def test_query_user_email(app, user: User):
    # Setup
    Users.save(user)

    # Test
    q_user = Users.query(email=user.email)

    # Confirm
    assert isinstance(q_user, User)
    assert q_user.id
    assert q_user.email == user.email
    assert q_user.state_last_search == user.state_last_search
    assert q_user.state_last_category == user.state_last_category


def test_query_user_user_id(app, user: User):
    # Setup
    Users.save(user)

    # Test
    q_user = Users.query(user_id=user.user_id)

    # Confirm
    assert isinstance(q_user, User)
    assert q_user.id
    assert q_user.email == user.email
    assert q_user.state_last_search == user.state_last_search
    assert q_user.state_last_category == user.state_last_category


def test_query_user_nonexistent(app):
    # Test
    q_user = Users.query(email="foo.bar@gmail.com")

    # Confirm
    assert q_user is None


def test_non_existent_user(app):
    results = Users.query(email="asdfasdfasdf@asdfasdfadsf.com")
    assert not results


def test_update_user_direct(app, user):
    """Test ability to update attributes of a user instance."""
    # Setup
    Users.save(user)

    # Test (by updating a single attribute)
    Users.update(user, "state_last_category", "Cooking-Skills")

    # Confirm by requerying
    updated_user = Users.query(email=user.email)
    assert updated_user.updated
    assert "Cooking-Skills" == updated_user.state_last_category


def test_update_complex_state_attributes_list(app, user):
    """Test ability to update list state attribute of a user instance."""
    # Setup
    Users.save(user)

    # Test (by updating a single attribute)
    Users.update(user, "state_last_searches", ["search term 1", "search term 2"])

    # Confirm (user in the database is actually created and matching)
    updated_user = Users.query(email=user.email)
    assert updated_user.updated
    assert ["search term 1", "search term 2"] == updated_user.state_last_searches


def test_update_complex_state_attributes_dict(app, user):
    """Test ability to update dict state attribute of a user instance."""
    # Setup
    Users.save(user)

    # Test (by updating a single attribute)
    Users.update(user, "state_last_sort", {"by": "title", "order": "asc"})

    # Confirm (user in the database is actually created and matching)
    updated_user = Users.query(email=user.email)
    assert updated_user.updated
    assert {"by": "title", "order": "asc"} == updated_user.state_last_sort


def test_user_update_password(app, user):
    # Setup
    Users.save(user)
    old_password_hash = user.password_hash

    # Test
    Users.update(user, "password", "newPassword")

    # Confirm
    q_user = Users.query(email=user.email)
    assert q_user.password_hash != old_password_hash
    assert user.password_hash == q_user.password_hash


def test_user_update_email(app, user):
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


def test_user_update_other_attribute(app, user):
    # Setup
    Users.save(user)
    old_category = user.state_last_category

    # Test
    Users.update(user, "state_last_category", "Cooking-Skills")

    # Confirm
    assert user.state_last_category != old_category
    assert user.state_last_category == "Cooking-Skills"


# def tst_get_default_view(app, user):
#     # Setup
#     user.insert()

#     # Test
#     view = user.get_default_view()
#     assert view
#     assert isinstance(view, UserView)
