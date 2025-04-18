#!/usr/bin/env python
"""Import a set of pdf's, in 2 passes."""

import argparse
import os
import time
from pathlib import Path

import boto3
from mongoengine.context_managers import switch_collection

import app.constants as c
from app import create_app
from app.cli import setup_logging
from app.models.documents import Documents
from app.models.user import query_user


def get_wasabi_connection(app):
    wasabi = boto3.client(
        "s3",
        endpoint_url="https://s3.us-west-1.wasabisys.com",
        region_name="us-east-1",
        aws_access_key_id=app.config["wasabi_access_key_id"],
        aws_secret_access_key=app.config["wasabi_secret_access_key"],
    )
    print("Connected to wasabi...")
    return wasabi


def clear_pdf_from_mongo(document: Documents) -> bool:
    try:
        document.file_.delete()
        document.file_ = None
        document.save()
        return True
    except Exception as exc:
        print(f"Unable to delete mongodb file? {exc}")
        return False


def get_pdf_from_mongo(document: Documents) -> Path:
    file_name: str = str(document.id) + ".pdf"
    file_path: Path = Path("/tmp/coctione_libri") / Path(file_name)
    with open(file_path, "wb") as fh_:
        fh_.write(document.file_.read())
    return file_path


def push_file_to_wasabi(wasabi, document: Documents, file_path: Path) -> bool:
    # Open file in binary mode and read all content
    bucket_name = "coctione-libri-development"
    object_key = file_path.stem
    print(f"Pushing {file_path} to wasabi...")
    try:
        wasabi.upload_file(file_path, bucket_name, object_key)
        return True
    except Exception as exc:
        print(f"Upload failed: {exc=}")
        return False


def transfer_document(wasabi, document: Documents) -> bool:
    """..."""
    if file_path := get_pdf_from_mongo(document):
        if push_file_to_wasabi(wasabi, document, file_path):
            clear_pdf_from_mongo(document)

    return True


# Use the following code to connect directly via raw credentials.
def main(args: argparse.Namespace):
    """Do our action."""
    setup_logging(True)

    # Setup our application/db connection
    os.environ["FLASK_ENV"] = args.database
    app = create_app(logging=None)
    with app.app_context():
        wasabi = get_wasabi_connection(app)
        user = query_user(email="peter.borocz@gmail.com")

        # Get each document in our repository..
        with switch_collection(Documents, Documents.as_user(user)) as user_documents:
            documents = user_documents.objects()
            print(f"{len(documents):4d} documents found.")
            for document in documents:
                if document.file_:  # Just to make sure, there ARE some empties or those we've already done. :-)
                    transfer_document(wasabi, document)
                break
                time.sleep(0.5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CoctioneLibri - Transfer PDF's to Wasabi")

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
