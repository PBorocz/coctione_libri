#!/usr/bin/env python
"""."""

import argparse
import getpass
import logging
import os
from pprint import pprint

from box import Box

from app import constants as c
from app import create_app
from app.models import categories
from app.models.user_rdb import User

logging.getLogger("peewee").setLevel(logging.INFO)  # or logging.WARNING


def reset_password():
    """Reset the password of an existing user."""
    user = None
    while True:
        email = input("Email : ")
        try:
            user = User.get(User.email == email)
            break
        except User.DoesNotExist:
            print(f"Sorry, no user with {email=}")

    password_1, password_2 = 1, 2
    while password_1 != password_2:
        password_1 = getpass.getpass("New Password : ")
        password_2 = getpass.getpass("Confirm      : ")
        if password_1 != password_2:
            print("Sorry, passwords don't match..try again")

    user.set_password(password_1)
    user.save()
    print("Password reset.")


def get_category():
    category = None
    while True:
        category = input("Category : ")
        if category in categories():
            return category
        categories_available = ", ".join(categories())
        print(f"Sorry, no {category=}, must be one of: {categories_available}")
    return None


def set_category():
    """Reset the category of an existing user."""
    user = None
    while True:
        email = input("Email : ")
        try:
            user = User.get(User.email == email)
            break
        except User.DoesNotExist:
            print(f"Sorry, no user with {email=}")

    payload = user.payload
    if payload.user_state.last_category:
        print(f"Current category={payload.user_state.last_category}")

    new_category = get_category()
    if new_category:
        payload.user_state.last_category = new_category
        user.payload = payload
        user.save()
        print("Category reset.")
    else:
        print("Nothing done.")


def add(app):
    """Add a new user to the database."""
    email = input("Email    : ")

    # Check if exists already..
    try:
        User.get(User.email == email)
        print(f"\nSorry, user with email {email} already exists!")
        return None
    except User.DoesNotExist:
        pass

    # Get user password..
    password, password_2 = 1, 2
    while password != password_2:
        password = getpass.getpass("Password : ")
        password_2 = getpass.getpass("Confirm  : ")
        if password != password_2:
            print("Sorry, passwords don't match..try again")

    # Get selected category
    category = get_category()

    user = User.factory(email=email, password=password)
    user.payload = Box(
        {
            "user_state": {
                "last_category": category,
                "last_sort": {"by": "title", "order": "asc"},
            }
        }
    )
    user.save()
    print(f"New user successfully created, {user.id=}")


def delete():
    """Delete a user from the database."""
    email = input("Email : ")
    try:
        user = User.get(User.email == email)
        user.delete_instance()
        return None
    except User.DoesNotExist:
        print("User NOT deleted, could not be found?")


def list_(app):
    """List db users."""
    found = False
    for o_user in User.select():
        print(f"\n{o_user.email}")
        pprint(o_user.__dict__)
        found = True
    if not found:
        print("Sorry, no users currently defined.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CoctioneLibri - User Manager")

    parser.add_argument(
        "-a",
        "--action",
        metavar="action",
        help="Action to be perform, ie. 'add', 'list', 'delete, 'reset-password', 'set-category'.",
        default="add",
    )

    parser.add_argument(
        "-d",
        "--database",
        help=f"Database environment, eg. {', '.join(c.DB_ENVS)}. Default is 'development'.",
        default="development",
    )

    ARGS = parser.parse_args()

    # Validate..
    assert ARGS.database in ("production", "development")

    # Setup our db connection
    os.environ["FLASK_ENV"] = ARGS.database
    app = create_app()
    app.app_context().push()

    # Dispatch accordingly..
    if ARGS.action.casefold() == "add":
        add(app)

    elif ARGS.action.casefold() == "list":
        list_(app)

    elif ARGS.action.casefold() == "reset-password":
        reset_password()

    elif ARGS.action.casefold() == "set-category":
        set_category()

    elif ARGS.action.casefold() == "delete":
        delete()

    else:
        raise RuntimeError(f"Sorry, we don't support action '{ARGS.action}' yet, must be one of 'add' or 'delete'.")
