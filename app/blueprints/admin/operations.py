"""Source Management Operations."""

import logging as log
from collections import defaultdict


from app.models.document import Document
from app.models.user import User


################################################################################
# Source Operations
################################################################################
def get_all_sources(user: User, sort: str = "source", order: str = "asc") -> list[str, int]:
    """Return a sorted list of all current sources & counts (ie. those attached to documents)."""
    sources = defaultdict(int)
    for document in Document.select().where(Document.user == user):
        if document.source:
            sources[document.source] += 1
    log.info(f"{len(sources):,d} unique sources found.")
    offset = 0 if sort == "source" else 1
    return sorted(sources.items(), key=lambda entry: entry[offset], reverse=(order == "desc"))


def get_source_count(user: User, source: str) -> int:
    """Return the count of documents that have the specified source."""
    return Document.select().where(Document.user == user, Document.source == source).count()


def remove_source(user: User, source: str) -> int:
    """Remove specified source from all documents."""
    log.debug(f"Removing {source=}")
    return Document.update(source=None).where(Document.user == user, Document.source == source)


def update_source(user: User, old: str, new: str) -> int:
    """Update all document with "old" source to have "new" one instead."""
    log.debug(f"Updating {old=} {new=}")
    return Document.update(source=new).where(Document.user == user, Document.source == old)


################################################################################
# Tag Operations
################################################################################
def get_all_tags(user: User, sort: str = "tag", order: str = "asc") -> list[str, int]:
    """Return a sorted list of all current tags & counts (ie. those attached to documents)."""
    tags = defaultdict(int)
    for document in Document.select().where(Document.user == user):
        for tag in document.tags:
            tags[tag] += 1

    log.info(f"{len(tags):,d} unique tags found.")
    offset = 0 if sort == "tag" else 1
    return sorted(tags.items(), key=lambda entry: entry[offset], reverse=(order == "desc"))


def get_tag_count(user: User, tag: str) -> int:
    """Return the count of documents that have the specified tag."""
    docs = [
        document
        for document in Document.select(Document.id).where(Document.user == user)
        if tag.title() in document.tags
    ]
    return len(docs)


def remove_tag(user: User, tag: str) -> int:
    """Remove specified tag from all documents."""
    log.debug(f"Removing {tag.title()=}")
    for document in Document.select().where(Document.user == user):
        if tag.title() in document.tags:
            document.tags.remove(tag.title())
            document.save()


def update_tag(user: User, old: str, new: str) -> int:
    """Update all document with "old" tag to have "new" on instead."""
    log.debug(f"Updating {old=} {new=}")
    count = 0
    for document in Document.select().where(Document.user == user):
        # Granular save logic but we don't do this very often.
        if old.title() in document.tags:
            document.tag.remove(old.title())
            document.tag.append(new.title())
            document.save()
            count += 1
    return count
