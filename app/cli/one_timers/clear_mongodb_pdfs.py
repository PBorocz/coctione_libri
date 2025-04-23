#!/usr/bin/env python
"""Import a set of pdf's, in 2 passes."""

import argparse
import os
import time

from mongoengine.context_managers import switch_collection

import app.constants as c
from app import create_app
from app.cli import setup_logging
from app.models.documents import Category, Documents
from app.models.user import query_user


def clear_pdf_from_mongo(document: Documents) -> bool:
    try:
        document.file_.delete()
        document.file_ = None
        document.save()
        print(".", flush=True, end="")
        return True
    except Exception as exc:
        print(f"Unable to delete mongodb file? {exc}")
        return False


# Use the following code to connect directly via raw credentials.
def main(args: argparse.Namespace):
    """Do our action."""
    setup_logging(True)

    # Setup our application/db connection
    os.environ["FLASK_ENV"] = args.database
    app = create_app(logging=None)
    with app.app_context():
        user = query_user(email="peter.borocz@gmail.com")

        for collection in (Category.COOKING_SKILLS, Category.COOKING_PRODUCTS):
            # Get each document in our repository..
            with switch_collection(Documents, Documents.as_user(user, collection)) as user_documents:
                documents = user_documents.objects()
                print(f"{len(documents):4d} documents found.")
                for document in documents:
                    if document.file_:  # Just to make sure, there ARE some empties or those we've already done. :-)
                        clear_pdf_from_mongo(document)
                    time.sleep(0.1)
            print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CoctioneLibri - Clear PDF's from MongoDB")

    parser.add_argument(
        "-d",
        "--database",
        help=f"Database environment, eg. {', '.join(c.DB_ENVS)}. Default is 'development'.",
        default="development",
    )
    ARGS = parser.parse_args()

    # Validate..
    assert ARGS.database in ("production", "development")

    main(ARGS)
