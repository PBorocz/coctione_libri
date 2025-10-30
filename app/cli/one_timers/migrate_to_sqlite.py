#!/usr/bin/env python
"""Migrate documents and users to a sqlite DB from MongoDB."""

import argparse
import hashlib
import logging as log
import sys
import time
from io import BytesIO
from pathlib import Path

from botocore.exceptions import ClientError
from mongoengine.context_managers import switch_collection
from peewee import IntegrityError

from app import create_app
from app.cli import setup_logging
from app.models import categories_available
from app.models.document import Document
from app.models.documents import CategoryField, Documents
from app.models.user import User
from app.models.user_rdb import User as UserRDB

EMAIL = "peter.borocz@gmail.com"

log.getLogger("peewee").setLevel(log.INFO)  # or log.WARNING


def main(args: argparse.Namespace):
    """Do our action, ie. either delete or import."""
    setup_logging(True)

    # Setup our application/db connection
    app = create_app()
    try:
        user_sql = UserRDB.get(UserRDB.email == EMAIL)
    except UserRDB.DoesNotExist:
        print(f"Sorry, you didn't create account for {EMAIL=} yet!")
        sys.exit(1)
    with app.app_context():
        for category in categories_available():
            migrate_documents(app, user_sql, category)


def migrate_documents(app, user_sql: User, category: str):
    user_mongo = User.objects.get(email=EMAIL)
    o_category = CategoryField().to_python(category)
    with switch_collection(Documents, Documents.as_user(user_mongo, o_category)) as user_documents:
        for mongo_document in user_documents.objects():
            print(f"{mongo_document.title[:35]:<35}...", end="")
            sql_document = generate(app, user_mongo, user_sql, mongo_document)
            if public_id := pull_pdf_from_wasabi(app, mongo_document, sql_document):
                try:
                    sql_document.public_id = public_id
                    sql_document.save()
                    print("✅")
                except IntegrityError as exc:
                    print(f"❌ {exc}")
            else:
                print()
            time.sleep(0.5)


def generate(app, user_mongo, user_sql, mongo_document):
    # fmt: off
    doc = Document(
        user       = user_sql,
        category   = mongo_document.category,
        title      = mongo_document.title,
        filesize   = mongo_document.filesize,
        mimetype   = mongo_document.mimetype,
        notes      = mongo_document.notes,
        source     = mongo_document.source,
        url        = mongo_document.url_,
        quality    = mongo_document.quality,
        complexity = mongo_document.complexity,
    )
    for tag in mongo_document.tags:
        doc.tags_add(tag.lower())

    for dc_ in mongo_document.dates_cooked:
        doc.dates_cooked_add(dc_)

    return doc

    # fmt: on


def pull_pdf_from_wasabi(app, mongo_document: Documents, sql_document: Document) -> str:
    """Pull the pdf document down as well and return the public_id/slug for the filename."""
    client_storage = app.config["STORAGE_FILE"]
    download_dir = Path(app.config["PATH_DATA"]) / Path("documents")
    contents: BytesIO = BytesIO()
    try:
        # Download file..
        client_storage.download_fileobj(client_storage.bucket, str(mongo_document.id), contents)
        contents.seek(0)

        # Generate hash from content
        content_data = contents.getvalue()
        content_hash = hashlib.sha256(content_data).hexdigest()

        # Use hash value as the filename and public_id/slug
        download_name: str = f"{content_hash}.pdf"
        download_path: Path = download_dir / Path(download_name)

        # If download already exists, we're done!
        if download_path.exists():
            print("∅", end="")
            return content_hash

        # Otherwise, save it away to local disk.
        with open(download_path, "wb") as f:
            f.write(contents.getvalue())
        print("✅", end="")
        return content_hash

    except ClientError as exc:
        log.error(str(exc))
        print(f"❌ {exc}", end="")
        log.error(f"Sorry, unable to pull document {mongo_document.filename}[{mongo_document.id!s}] from storage.")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CoctioneLibri - Migrate to SQLite")
    ARGS = parser.parse_args()
    main(ARGS)
