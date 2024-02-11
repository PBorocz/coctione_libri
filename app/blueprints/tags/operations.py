"""Tag Management Operations."""
import logging as log
from collections import defaultdict

from app.models.documents import Documents


def get_all_tags() -> list[str]:
    """Return a sorted list of all current tags (ie. those attached to documents)."""
    tags = defaultdict(int)
    for document in Documents.objects().only("tags"):
        for tag in document.tags:
            tags[tag] += 1
    log.info(f"{len(tags):,d} unique tags found.")
    return list(tags.items())


def get_tag_count(tag: str) -> int:
    """Return the count of documents that have the specified tag."""
    return Documents.objects(tags__in=[tag]).count()


def remove_tag(tag: str) -> int:
    """Remove specified tag from all documents."""
    log.debug(f"Removing {tag=}")
    return Documents.objects(tags__in=[tag]).update(pull__tags=tag)


def update_tag(old: str, new: str) -> int:
    """Update all document with "old" tag to have "new" on instead."""
    log.debug(f"Updating {old=} {new=}")
    ids = [doc.id for doc in Documents.objects(tags__in=[old]).only("id")]
    count_pulled = Documents.objects(id__in=ids).update(pull__tags=old)
    count_pushed = Documents.objects(id__in=ids).update(push__tags=new)
    if count_pulled != count_pushed:
        msg = f"Sorry, we 'should' have pulled {count_pulled=} as many document as we pushed {count_pushed=}"
        log.error(msg)
    return count_pushed
