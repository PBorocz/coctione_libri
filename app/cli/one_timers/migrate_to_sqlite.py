#!/usr/bin/env python
"""Migrate documents and users to a sqlite DB from MongoDB."""

import argparse
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
            sql_document = emit_to_sql(app, user_mongo, user_sql, mongo_document)
            pull_pdf_from_wasabi(app, mongo_document, sql_document)
            time.sleep(1)


def emit_to_sql(app, user_mongo, user_sql, mongo_document):
    # fmt: off
    doc = Document(
        user         = user_sql,
        category     = mongo_document.category,
        title        = mongo_document.title,
        fileid       = str(mongo_document.id),
        filename     = mongo_document.filename,
        filesize     = mongo_document.filesize,
        mimetype     = mongo_document.mimetype,
        notes        = mongo_document.notes,
        source       = mongo_document.source,
        url          = mongo_document.url_,
        quality      = mongo_document.quality,
        complexity   = mongo_document.complexity,
        tags         = [tag.title() for tag in mongo_document.tags],
        dates_cooked = mongo_document.dates_cooked,
    )
    # fmt: on
    try:
        doc.save(app=app)
        print(f"{mongo_document.title[:30]:<30}...✅", end="")
        return doc
    except IntegrityError as exc:
        print(f"{mongo_document.title[:30]:<30}...❌ {exc}")
        return None


def pull_pdf_from_wasabi(app, mongo_document: Documents, sql_document: Document) -> bool:
    """Pull the pdf document down as well!."""
    if not mongo_document.id:
        print("Sorry, no fileid to work from?")
        return False

    client_storage = app.config["STORAGE_FILE"]
    download_dir = Path(app.config["PATH_DATA"]) / Path("documents")
    contents: BytesIO = BytesIO()
    download_name: str = f"{sql_document.id}.pdf"  # NEW NAMING CONVENTION!
    download_path: Path = download_dir / Path(download_name)
    try:
        client_storage.download_fileobj(client_storage.bucket, str(mongo_document.id), contents)
        contents.seek(0)
        print("✅")
        with open(download_path, "wb") as f:
            f.write(contents.getvalue())
        return True
    except ClientError as exc:
        log.error(str(exc))
        print(f"❌ {exc}")
        log.error(f"Sorry, unable to pull document {mongo_document.filename}[{mongo_document.id!s}] from storage.")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CoctioneLibri - Migrate to SQLite")
    ARGS = parser.parse_args()
    main(ARGS)
