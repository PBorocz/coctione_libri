#!/usr/bin/env python
"""."""
import argparse
import os

import mongoengine

from app import constants as c
from app import create_app
from app.models.users import Users, delete_user, query_user, update_user


def reset_password():
    """Reset the password of an existing user."""
    user = None
    while True:
        email = input("Email : ")
        user = query_user(email=email)
        if user:
            break
        print(f"Sorry, no user with email: '{email}'")

    password, password_2 = 1, 2
    while password != password_2:
        password = input("Password : ")
        password_2 = input("Confirm  : ")
        if password != password_2:
            print("Sorry, passwords don't match..try again")

    update_user(user, "password", password)
    print("Password reset.")


def add():
    """Add a new user to the database."""
    email = input("Email    : ")

    password, password_2 = 1, 2
    while password != password_2:
        password = input("Password : ")
        password_2 = input("Confirm  : ")
        if password != password_2:
            print("Sorry, passwords don't match..try again")

    user = Users.factory(email=email, password=password)
    try:
        user.save()
        print(f"New user successfully created [{user.id}]")
    except mongoengine.NotUniqueError:
        print("Sorry, unable to create new user; that email address has already been used!")


def delete():
    """Delete a user from the database."""
    email = input("Email : ")
    if delete_user(email=email):
        print("User deleted.")
    else:
        print("User NOT deleted, could not be found?")


def list_():
    """List db users."""
    found = False
    for user in Users.objects():
        from pprint import pprint

        pprint(user.to_mongo().to_dict())
        found = True
    if not found:
        print("Sorry, no users currently defined.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CoctioneLibri - User Manager")

    parser.add_argument(
        "-a",
        "--action",
        metavar="action",
        help="Action to be perform, ie. 'add', 'list', 'delete, 'reset-password'.",
        default="add",
    )

    parser.add_argument(
        "-d",
        "--database",
        help=f"Database environment, eg. {', '.join(c.DB_ENVS)}. Default is 'local'.",
        default="local",
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
        add()

    elif ARGS.action.casefold() == "list":
        list_()

    elif ARGS.action.casefold() == "reset-password":
        reset_password()

    elif ARGS.action.casefold() == "delete":
        delete()

    else:
        raise RuntimeError(f"Sorry, we don't support action '{ARGS.action}' yet, must be one of 'add' or 'delete'.")
