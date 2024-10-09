"""Source Management Operations."""

import logging as log
from collections import defaultdict

from mongoengine.context_managers import switch_collection

from app.models.documents import Documents
from app.models.users import Users


def get_all_sources(user: Users, sort: str = "source", order: str = "asc") -> list[str, int]:
    """Return a sorted list of all current sources & counts (ie. those attached to documents)."""
    sources = defaultdict(int)
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        for document in user_documents.objects().only("source"):
            if document.source:
                sources[document.source] += 1

    log.info(f"{len(sources):,d} unique sources found.")
    offset = 0 if sort == "source" else 1
    return sorted(sources.items(), key=lambda entry: entry[offset], reverse=(order == "desc"))


def get_source_count(user: Users, source: str) -> int:
    """Return the count of documents that have the specified source."""
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        return user_documents.objects(source=source).count()


def remove_source(user: Users, source: str) -> int:
    """Remove specified source from all documents."""
    log.debug(f"Removing {source=}")
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        return user_documents.objects(source=source).update(source=None)


def update_source(user: Users, old: str, new: str) -> int:
    """Update all document with "old" source to have "new" one instead."""
    log.debug(f"Updating {old=} {new=}")
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        ids = [doc.id for doc in user_documents.objects(source=old).only("id")]
        return user_documents.objects(id__in=ids).update(source=new)
