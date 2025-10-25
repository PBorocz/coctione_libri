#!/usr/bin/env python
"""Migrate documents and users to a sqlite DB from MongoDB."""

import argparse
import logging as log
import os
import re
import time
import tomllib
from pathlib import Path

import tomli_w
from mongoengine.context_managers import switch_collection
from peewee import IntegrityError

import app.constants as c
from app import create_app, db
from app.cli import setup_logging
from app.models import Category, categories_available
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
    user_sql = UserRDB.get(UserRDB.email == EMAIL)
    with app.app_context():
        for category in categories_available():
            migrate_documents(app, user_sql, category)


def migrate_documents(app, user_sql: User, category: str):
    user_mongo = User.objects.get(email=EMAIL)
    o_category = CategoryField().to_python(category)
    with switch_collection(Documents, Documents.as_user(user_mongo, o_category)) as user_documents:
        for document in user_documents.objects():
            emit_to_sql(app, user_mongo, user_sql, document)


def emit_to_sql(app, user_mongo, user_sql, mongo_document):
    # fmt: off
    doc = Document(
        user         = user_sql,
        category     = mongo_document.category,
        title        = mongo_document.title,
        filename     = mongo_document.filename,
        filesize     = mongo_document.filesize,
        mimetype     = mongo_document.mimetype,
        notes        = mongo_document.notes,
        source       = mongo_document.source,
        url          = mongo_document.url_,
        quality      = mongo_document.quality,
        complexity   = mongo_document.complexity,
        tags         = mongo_document.tags,
        dates_cooked = mongo_document.dates_cooked,
    )
    # fmt: on
    try:
        doc.save()
        # print(f"{mongo_document.title[:30]:<30}...✅")
    except IntegrityError as exc:
        print(f"{mongo_document.title[:30]:<30}...❌ {exc}")


def import_pdfs(args):
    user = User.objects.get(email="peter.borocz@gmail.com")
    assert args.category, f"Sorry, you need to specify a valid category: {','.join(categories_available())}"
    o_category = CategoryField().to_python(args.category)

    with open(Path(args.directory) / Path(args.file), "rb") as fh_toml:
        pdfs = tomllib.load(fh_toml)

    print("Checking: ", end="")
    for pdf in pdfs.get("pdfs"):
        assert "name" in pdf, f"Sorry, no 'name' attribute in entry?: {pdf['path']}"
        assert "path" in pdf, f"Sorry, no 'path' attribute in entry?: {pdf['name']}"
        assert Path(pdf["path"]).exists(), f"Sorry, can't find file for: {pdf['name']} from: ({pdf['path']})"
        print("•", end="", flush=True)
    print()

    print("Importing: ", end="")
    for pdf in pdfs.get("pdfs"):
        __import_pdf(user, o_category, pdf)
        print("•", end="", flush=True)
        time.sleep(0.25)
    print()


def __import_pdf(user, o_category: Category, pdf: dict) -> str:
    with switch_collection(Documents, Documents.as_user(user, o_category)) as user_documents:
        doc = user_documents(user=user, title=pdf.get("name"), category=o_category)
        if "source" in pdf:
            doc.source = pdf["source"]
        if "tags" in pdf:
            doc.tags = [tag for tag in pdf["tags"] if "*" not in tag]
        if "url" in pdf:
            doc.url_ = pdf["url"]

        path_pdf = Path(pdf.get("path"))
        with open(Path(path_pdf), "rb") as fd:
            doc.file_.put(fd, fileName=path_pdf.name, contentType="application/pdf")

        doc.save()

    time.sleep(0.25)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CoctioneLibri - Migrate to SQLite")

    parser.add_argument(
        "-d",
        "--database",
        help=f"Database environment, eg. {', '.join(c.DB_ENVS)}. Default is 'development'.",
        default="production",
    )

    # parser.add_argument(
    #     "--directory",
    #     help="Directory to read from (no default)",
    # )

    # parser.add_argument(
    #     "-a",
    #     "--action",
    #     help="Action to be performed, ie. 1_create_toml, 2_import_pdfs",
    #     default="1_create_toml",
    # )

    # parser.add_argument(
    #     "-f",
    #     "--file",
    #     help="Specific file to import, e.g. my_pdfs.toml",
    #     default="import.toml",
    # )

    parser.add_argument(
        "-c",
        "--category",
        help="What specific category should these documents be added as?",
    )

    ARGS = parser.parse_args()

    # Validate..
    # assert ARGS.database in ("production", "development")
    # assert ARGS.action in ("1_create_toml", "2_import_pdfs")
    main(ARGS)
