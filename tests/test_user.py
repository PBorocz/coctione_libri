"""Test User data type."""

from box import Box
from werkzeug.security import check_password_hash

from app.models.user import User


################################################################################
# Utility methods
################################################################################
def get_current_row_count():
    return len(list(User.select()))


################################################################################
# Tests
################################################################################
def test_user_init_missing_attrs(app):
    """Test that a simple class instantiation won't work as there ARE required fields."""
    User()


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
    test_user_parms = {
        "id": 99,
        "email": "test@foo.com",
        "password": "aPassword",
    }
    user = User.factory(**test_user_parms)

    # Test
    count = user.delete_instance()

    # Confirm
    assert 0 == count


def test_user_query_email(app, user: User):
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


def test_user_query_user_id(app, user: User):
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


def test_user_non_existent(app):
    results = User.select().where(User.email == "asdfasdfasdf@asdfasdfadsf.com")
    assert not results


def test_user_payload_str(app, user):
    """Test ability to update payload of a string."""
    # Setup
    user.save()
    assert not user.payload

    # Test (by updating a single payload str attribute.)
    user.payload = Box({"user_state": {"last_search": "search term 1"}})
    user.save()

    # Confirm - First save..
    user_saved = User.get(User.email == user.email)
    assert "search term 1" == user_saved.payload.user_state.last_search

    # Confirm - Update
    updated_search = "Updated Search"

    payload = user_saved.payload
    payload.user_state.last_search = updated_search
    user_saved.payload = payload
    assert updated_search == user_saved.payload.user_state.last_search

    user_saved.save()
    assert updated_search == user_saved.payload.user_state.last_search


def test_user_payload_list_set(app, user):
    """Test ability to update payload of a list."""
    # Setup
    user.save()
    assert not user.payload

    # Test (by updating a single payload str attribute.)
    user.payload = Box({"user_state": {"last_searches": ["search entry 1 of 1"]}})
    user.save()

    # Confirm
    user_saved = User.get(User.email == user.email)
    assert ["search entry 1 of 1"] == user_saved.payload.user_state.last_searches


def test_user_payload_list_append(app, user):
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
    user_saved = User.get(User.email == user.email)
    assert ["entry 1 of 2", "entry 2 of 2"] == user_saved.payload.user_state.last_searches


def test_user_payload_dict_append(app, user):
    """Test ability to update payload of a dict."""
    # Setup
    d_last_sort = {"by": "title", "order": "asc"}
    user.payload = Box({"user_state": {"last_sort": d_last_sort}})
    user.save()
    assert d_last_sort == user.payload.user_state.last_sort

    # Test (by updating a single payload str attribute.)
    b_payload = user.payload
    b_payload.user_state.last_sort.by = "name"
    b_payload.user_state.last_sort.order = "desc"
    user.payload = b_payload
    user.save()

    # Confirm
    user_saved = User.get(User.email == user.email)
    assert "name" == user_saved.payload.user_state.last_sort.by
    assert "desc" == user_saved.payload.user_state.last_sort.order


def test_user_update_on_save(app, user):
    """Test overridden save method obo "updated" attribute."""
    # Setup
    user.save()
    assert user.updated is None

    # Test (by updating a single attribute)
    user.payload = Box()
    user.save()

    assert user.updated


def test_user_update_password(app, user):
    # Setup
    user.save()
    old_password_hash = user.password_hash

    # Test
    user.set_password("newPassword")
    user.save()

    # Confirm
    q_user = User.get(User.email == user.email)
    assert q_user.password_hash != old_password_hash
    assert user.password_hash == q_user.password_hash


def test_user_update_email(app, user):
    # Setup
    user.save()
    old_user_id = user.user_id

    # Test
    new_email = "bar@foo.com"
    user.set_email(new_email)
    assert new_email == user.email
    assert user.user_id != old_user_id

    # Confirm
    user.save()
    q_user = User.get(User.email == user.email)
    assert new_email == q_user.email
    assert user.user_id == q_user.user_id
