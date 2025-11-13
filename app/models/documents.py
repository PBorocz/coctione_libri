"""Documents class (mostly a wrapper around some common methods across documents."""

import logging as log
from collections import defaultdict

from app.models.document import Document
from app.models.user import User


class Documents:
    """Namespace manager for methods that span all documents."""

    @classmethod
    def sources(cls, user: User) -> list[str]:
        """Return the current list of sources across all documents for the specified user."""
        return [source_ for source_, _ in Documents.source_counts(user)]

    @classmethod
    def tags(cls, user: User) -> list[str]:
        """Return a sorted list of *all* tags attached to documents for the specified user."""
        return [tag_ for tag_, _ in Documents.tag_counts(user)]

    @classmethod
    def tag_counts(cls, user: User, sort: str = "tag", order: str = "asc") -> list[str, int]:
        """Return a list of (tag,counts) of all tags for the specified user."""
        tags = defaultdict(int)
        for document in Document.select(Document.tags).where(Document.user == user):
            for tag in document.tags_split:
                tags[tag.title()] += 1

        log.info(f"{len(tags):,d} unique tags found.")
        offset = 0 if sort == "tag" else 1
        return sorted(tags.items(), key=lambda entry: entry[offset], reverse=(order == "desc"))

    @classmethod
    def source_counts(cls, user: User, sort: str = "count", order: str = "desc") -> list[str, int]:
        """Return a list of (source,counts) of all sources for the specified user."""
        sources = defaultdict(int)
        for document in Document.select(Document.source).where(Document.user == user):
            if document.source:
                sources[document.source] += 1

        log.info(f"{len(sources):,d} unique sources found.")
        offset = 0 if sort == "source" else 1
        return sorted(sources.items(), key=lambda entry: entry[offset], reverse=(order == "desc"))
