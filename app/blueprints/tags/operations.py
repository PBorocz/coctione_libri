"""Tag Management Operations."""
import logging as log
from collections import defaultdict

from mongoengine.context_managers import switch_collection

from app.models.documents import Documents, get_user_documents
from app.models.users import Users


def get_all_tags(user: Users, sort: str = "tag", order: str = "asc") -> list[str, int]:
    """Return a sorted list of all current tags & counts (ie. those attached to documents)."""
    tags = defaultdict(int)
    with switch_collection(Documents, get_user_documents(user)) as user_documents:
        for document in user_documents.objects().only("tags"):
            for tag in document.tags:
                tags[tag] += 1

    log.info(f"{len(tags):,d} unique tags found.")
    offset = 0 if sort == "tag" else 1
    return sorted(tags.items(), key=lambda entry: entry[offset], reverse=(order == "desc"))


def get_tag_count(user: Users, tag: str) -> int:
    """Return the count of documents that have the specified tag."""
    with switch_collection(Documents, get_user_documents(user)) as user_documents:
        return user_documents.objects(tags__in=[tag]).count()


def remove_tag(user: Users, tag: str) -> int:
    """Remove specified tag from all documents."""
    log.debug(f"Removing {tag=}")
    with switch_collection(Documents, get_user_documents(user)) as user_documents:
        return user_documents.objects(tags__in=[tag]).update(pull__tags=tag)


def update_tag(user: Users, old: str, new: str) -> int:
    """Update all document with "old" tag to have "new" on instead."""
    log.debug(f"Updating {old=} {new=}")
    with switch_collection(Documents, get_user_documents(user)) as user_documents:
        ids = [doc.id for doc in user_documents.objects(tags__in=[old]).only("id")]
        count_pulled = user_documents.objects(id__in=ids).update(pull__tags=old)
        count_pushed = user_documents.objects(id__in=ids).update(push__tags=new)
        if count_pulled != count_pushed:
            msg = f"Sorry, we 'should' have pulled {count_pulled=} as many document as we pushed {count_pushed=}"
            log.error(msg)

    return count_pushed
