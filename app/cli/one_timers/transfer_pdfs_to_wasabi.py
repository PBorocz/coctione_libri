#!/usr/bin/env python
"""Import a set of pdf's, in 2 passes."""

import argparse
import mimetypes
import os
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from mongoengine.context_managers import switch_collection
from werkzeug.utils import secure_filename

import app.constants as c
from app import create_app
from app.cli import setup_logging
from app.models.documents import Category, Documents
from app.models.user import query_user


def get_wasabi_connection(app):
    wasabi = boto3.client(
        "s3",
        endpoint_url="https://s3.us-west-1.wasabisys.com",
        region_name="us-east-1",
        aws_access_key_id=app.config["STORAGE_FILE_ACCESS_KEY_ID"],
        aws_secret_access_key=app.config["STORAGE_FILE_SECRET_ACCESS_KEY"],
    )
    wasabi.bucket = app.config["STORAGE_FILE_BUCKET"]
    print(f"Connected to wasabi, bucket: {wasabi.bucket}")
    return wasabi


def get_pdf_from_mongo(document: Documents) -> Path:
    file_name: str = str(document.id) + ".pdf"
    file_path: Path = Path("/tmp/coctione_libri") / Path(file_name)
    with open(file_path, "wb") as fh_:
        fh_.write(document.file_.read())
    return file_path


def push_file_to_wasabi(wasabi, document: Documents, file_path: Path) -> bool:
    # Open file in binary mode and read all content
    try:
        wasabi.upload_file(file_path, wasabi.bucket, str(document.id))

        document.filename = file_path.stem
        document.filesize = os.path.getsize(file_path)
        document.mimetype = mimetypes.guess_type(secure_filename(file_path.stem))[0]
        document.save()
        return True
    except Exception as exc:
        print(f"\nUpload failed: {exc=}")
        return False


def file_in_wasabi(wasabi, document: Documents) -> bool:
    args = {"Bucket": wasabi.bucket, "Key": str(document.id)}
    try:
        wasabi.head_object(**args)
        return True
    except ClientError:
        return False


def push_to_wasabi(wasabi, document: Documents) -> bool:
    """..."""
    if file_path := get_pdf_from_mongo(document):
        if not file_in_wasabi(wasabi, document):
            print(".", flush=True, end="")
            push_file_to_wasabi(wasabi, document, file_path)
        else:
            print("e", flush=True, end="")
    return True


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
                print(f"{len(documents):4d} documents found in {collection}:")
                for document in documents:
                    if document.file_:  # Just to make sure, there ARE some empties or those we've already done. :-)
                        push_to_wasabi(app.config["STORAGE_FILE"], document)
                    time.sleep(0.2)
            print()


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
