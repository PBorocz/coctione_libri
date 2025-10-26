#!/usr/bin/env python
"""Import a set of pdf's, in 2 passes."""

# from mongoengine.context_managers import switch_collection

import argparse
import os

import app.constants as c
from app import create_app
from app.cli import setup_logging
from app.models import categories
from app.models.document import Document
from app.models.user_rdb import User

FILE_STORAGE_ENTRIES = {}


def get_file_storage(app) -> int:
    storage_client = app.config["STORAGE_FILE"]
    response = storage_client.list_objects_v2(Bucket=storage_client.bucket)
    for entry in response["Contents"]:
        FILE_STORAGE_ENTRIES[entry["Key"]] = entry
    return len(FILE_STORAGE_ENTRIES)


def file_in_file_storage(app, document: Document) -> dict:
    return FILE_STORAGE_ENTRIES.get(str(document.fileid))


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


def _check_document_file_storage(app, doc: Document) -> list[str]:
    """Check if the file has appropriate file storage attributes."""
    issues = []
    if not (file_entry := file_in_file_storage(app, doc)):
        if doc.url:
            issues.append("FYI, entry only has a URL stored for it and not a file, can we find one?")
        else:
            issues.append("Sorry, entry doesn't have a file OR a URL stored for it.")
    else:
        if not doc.filename:
            issues.append("Sorry, entry has a file in storage but NO filename.")

        if not doc.mimetype:
            issues.append("Sorry, entry has a file in storage but NO mimetype.")

        if not doc.filesize:
            issues.append("Sorry, entry has a file in storage but NO filesize.")
        elif file_entry["Size"] != doc.filesize:
            issues.append(
                f"Sorry, entry's filesize: {doc.filesize} doesn't match with storage filesize: {file_entry['Size']}."
            )
    return issues


def _db_quality_for_a_document(app, document: Document) -> list[str]:
    issues = []
    if doc_issues := _check_document_attributes(app, document):
        issues.extend(doc_issues)
    if doc_issues := _check_document_file_storage(app, document):
        issues.extend(doc_issues)
    return issues


def _db_quality_for_a_collection(app, user: User, collection: str):
    results = {}
    print(f"\n{collection!s}:")
    for document in Document.select().where(Document.user == user, Document.category == collection):
        print(".", flush=True, end="")
        if issues := _db_quality_for_a_document(app, document):
            results[document] = issues
    print()
    if results:
        _report_issues(results)
    else:
        print(f"✅ No issues found in '{collection!s}'")


def _db_quality_file_storage(app, user: User):
    """See if we have any "orphaned" file storage entries with no associated entries!."""
    # We already have the list of file_storage entries in FILE_STORAGE_ENTRIES, now get
    # the list of all the document entries to cross match across *ALL* collections:
    document_fileids = []
    print("\nChecking for unknown file storage entries...", flush=True, end="")
    for collection in categories():
        docs = Document.select().where(Document.user == user, Document.category == collection)
        document_fileids.extend([str(doc.fileid) for doc in docs])

    file_storage_ids = {key for key in FILE_STORAGE_ENTRIES.keys() if not key.startswith("cl-dev--")}
    missing_docs = file_storage_ids - set(document_fileids)

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
        get_file_storage(app)

        for collection in categories():
            _db_quality_for_a_collection(app, user, collection)

        _db_quality_file_storage(app, user)


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
