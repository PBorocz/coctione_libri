#!/usr/bin/env python
"""Import a set of pdf's, in 2 passes."""

import argparse
import os

from botocore.exceptions import ClientError
from mongoengine.context_managers import switch_collection

import app.constants as c
from app import create_app
from app.cli import setup_logging
from app.models import categories
from app.models.documents import Documents
from app.models.user import query_user


def file_in_file_storage(app, document: Documents) -> bool:
    storage_client = app.config["STORAGE_FILE"]
    try:
        storage_client.head_object(Bucket=storage_client.bucket, Key=str(document.id))
        return True
    except ClientError:
        return False


def _report_issues(issues: dict) -> None:
    """Report on all issues encountered for this document."""
    for doc, doc_issues in issues.items():
        print(doc.title)
        for issue in doc_issues:
            print(f"\t{issue}")


def _check_document_file_storage(app, doc: Documents) -> list[str]:
    """Check if the file has appropriate file storage attributes."""
    issues = []
    if not file_in_file_storage(app, doc):
        issues.append("Sorry, doc is missing a file from storage!")
    else:
        if not doc.filename:
            issues.append("Sorry, doc has a file in storage but NO filename.")
        if not doc.filesize:
            issues.append("Sorry, doc has a file in storage but NO filesize.")
        if not doc.mimetype:
            issues.append("Sorry, doc has a file in storage but NO mimetype.")
    return issues


def _db_quality_for_a_document(app, document: Documents) -> list[str]:
    issues = []
    if doc_issues := _check_document_file_storage(app, document):
        issues.extend(doc_issues)
    return issues


def _db_quality_for_a_collection(app, user, collection):
    with switch_collection(Documents, Documents.as_user(user, collection)) as user_documents:
        results = {}
        documents = user_documents.objects()
        print(f"Checking {len(documents):4d} documents {collection=}:")
        for document in documents:
            print(".", flush=True, end="")
            if issues := _db_quality_for_a_document(app, document):
                results[document] = issues
        if results:
            print()
            _report_issues(results)


def main(args: argparse.Namespace):
    """Do a database reconciliation/quality set of checks."""
    setup_logging(True)

    # Setup our application/db connection
    os.environ["FLASK_ENV"] = args.database
    app = create_app(logging=None)
    with app.app_context():
        user = query_user(email="peter.borocz@gmail.com")

        for collection in categories():
            _db_quality_for_a_collection(app, user, collection)


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
