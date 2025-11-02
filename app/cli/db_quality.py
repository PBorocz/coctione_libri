#!/usr/bin/env python

import argparse
import os
from pathlib import Path

import app.constants as c
from app import create_app
from app.cli import setup_logging
from app.models import categories
from app.models.document import Document, generate_file_storage_path
from app.models.user import User


def get_file_public_ids(app) -> set[str]:
    path_file_storage = Path(app.config["PATH_DATA"]) / Path(app.config["STORAGE_DOCS_DIR_NAME"])
    assert path_file_storage.exists()
    return {path_.stem for path_ in path_file_storage.glob("*")}


def _report_issues(issues: dict) -> None:
    """Report on all issues encountered for this document."""
    for doc, doc_issues in issues.items():
        print(f"\n{doc.title} [{doc.id!s}]")
        for issue in doc_issues:
            print(f"\t❌ {issue}")


def _check_document_attributes(app, doc: Document) -> list[str]:
    """Check the document entry's attributes (sorta like pydantic but more user-focused."""
    issues = []
    if doc.dates_cooked and not doc.quality:
        issues.append(f"Sorry, entry was cooked on {doc.dates_cooked[-1].date()} but has no associated Quality metric.")
    ...  # Any more???
    return issues


def _check_document_file_storage(app, file_public_ids: set[str], doc: Document) -> list[str]:
    """Check if the file has appropriate file storage attributes."""
    issues = []
    if doc.public_id in file_public_ids:
        if not doc.mimetype:
            issues.append("Sorry, entry has a file in storage but NO mimetype.")

        if not doc.filesize:
            issues.append("Sorry, entry has a file in storage but NO filesize.")
        else:
            file_path = generate_file_storage_path(app, doc)
            if file_path.stat().st_size != doc.filesize:
                msg = (
                    f"Sorry, entry's filesize: {doc.filesize} ",
                    "doesn't match with storage filesize: {file_path.stat().st_size}",
                )
                issues.append(msg)
    elif doc.url:
        issues.append("FYI, entry only has a URL stored for it and not a file, can we find one?")
    else:
        issues.append("Sorry, entry doesn't have a file OR a URL stored for it.")
    return issues


def _db_quality_for_a_document(app, file_public_ids: set[str], document: Document) -> list[str]:
    issues = []
    if doc_issues := _check_document_attributes(app, document):
        issues.extend(doc_issues)
    if doc_issues := _check_document_file_storage(app, file_public_ids, document):
        issues.extend(doc_issues)
    return issues


def _db_quality_for_a_collection(app, user: User, collection: str, file_public_ids: set[str]):
    results = {}
    print(f"\n{collection!s}:")
    for document in Document.select().where(Document.user == user, Document.category == collection):
        print(".", flush=True, end="")
        if issues := _db_quality_for_a_document(app, file_public_ids, document):
            results[document] = issues
    print()
    if results:
        _report_issues(results)
    else:
        print(f"✅ No issues found in '{collection!s}'")


def _db_quality_file_storage(app, user: User, file_public_ids: set[str]):
    """See if we have any "orphaned" file storage entries with no associated entries!."""
    # We already have the list of file_storage entries in FILE_STORAGE_ENTRIES, now get
    # the list of all the document entries to cross match across *ALL* collections:
    document_public_ids = []
    print("\nChecking for unknown file storage entries...", flush=True, end="")
    for collection in categories():
        docs = Document.select(Document.public_id).where(Document.user == user, Document.category == collection)
        document_public_ids.extend([str(doc.public_id) for doc in docs])

    missing_docs = file_public_ids - set(document_public_ids)
    if missing_docs:
        print(f"❌ Found {len(missing_docs)} file storage entries with NO matching document entries!")
    else:
        print("✅ All entries accounted for!")


def main(args: argparse.Namespace):
    """Do a database reconciliation/quality set of checks."""
    setup_logging(True)

    # Setup our application/db connection
    os.environ["FLASK_ENV"] = args.database
    app = create_app(logging=None)
    with app.app_context():
        user = User.get(User.email == "peter.borocz@gmail.com")

        # Get a listing of all the current entries in our file storage..
        file_public_ids = get_file_public_ids(app)

        for collection in categories():
            _db_quality_for_a_collection(app, user, collection, file_public_ids)

        _db_quality_file_storage(app, user, file_public_ids)


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
