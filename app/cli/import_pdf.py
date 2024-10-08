#!/usr/bin/env python
"""Import a set of pdf's, in 2 passes."""

import argparse
import os
import re
import time
import tomllib
from pathlib import Path

import tomli_w
from mongoengine.context_managers import switch_collection

import app.constants as c
from app import create_app
from app.cli import setup_logging
from app.models import Category, categories_available
from app.models.documents import CategoryField, Documents
from app.models.users import Users


def main(args: argparse.Namespace):
    """Do our action, ie. either delete or import."""
    setup_logging(True)

    # Setup our application/db connection
    os.environ["FLASK_ENV"] = args.database
    app = create_app(logging=None)
    with app.app_context():
        if args.action == "1_create_toml":
            create_toml(args)
        elif args.action == "2_import_pdfs":
            import_pdfs(args)


def create_toml(args):
    path_pdfs = Path(args.directory)
    pdfs = []
    pattern = re.compile(r"(?<!^)(?=[A-Z])")
    for path_pdf in path_pdfs.glob("*.pdf"):
        name = pattern.sub(" ", path_pdf.name.replace(".pdf", "").replace("_", " "))
        pdf = {
            "path": str(path_pdf),
            "name": name,
            "tags": [],
            "source": "<aSource>",
        }
        pdfs.append(pdf)

    print(tomli_w.dumps({"pdfs": pdfs}))


def import_pdfs(args):
    user = Users.objects.get(email="peter.borocz@gmail.com")
    assert args.category, f"Sorry, you need to specify a valid category: {','.join(categories_available())}"
    o_category = CategoryField().to_python(args.category)

    with open(Path(args.file), "rb") as fh_toml:
        pdfs = tomllib.load(fh_toml)

    print("Checking: ", end="")
    for pdf in pdfs.get("pdfs"):
        assert "name" in pdf, f"Sorry, no 'name' attribute in entry?: {pdf['path']}"
        assert "path" in pdf, f"Sorry, no 'path' attribute in entry?: {pdf['name']}"
        if not Path(pdf["path"]).exists():
            print(f"Sorry, can't find file for: {pdf['name']} from: ({pdf['path']})")
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

        path_pdf = Path(pdf.get("path"))
        with open(Path(path_pdf), "rb") as fd:
            doc.file_.put(fd, fileName=path_pdf.name, contentType="application/pdf")

        doc.save()

    time.sleep(0.25)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CoctioneLibri - Import PDF's")

    parser.add_argument(
        "-d",
        "--database",
        help=f"Database environment, eg. {', '.join(c.DB_ENVS)}. Default is 'development'.",
        default="development",
    )

    parser.add_argument(
        "--directory",
        help="Directory to read from (no default)",
    )

    parser.add_argument(
        "-a",
        "--action",
        help="Action to be performed, ie. 1_create_toml, 2_import_pdfs",
        default="1_create_toml",
    )

    parser.add_argument(
        "-f",
        "--file",
        help="Specific file to import, e.g. my_pdfs.toml",
    )

    parser.add_argument(
        "-c",
        "--category",
        help="What specific category should these documents be added as?",
    )

    ARGS = parser.parse_args()

    # Validate..
    assert ARGS.database in ("production", "development")
    assert ARGS.action in ("1_create_toml", "2_import_pdfs")

    main(ARGS)
