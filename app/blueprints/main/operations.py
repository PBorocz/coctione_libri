"""Main/home view, essentially the master table itself, either all or from search."""
import logging as log
import sys
from collections import defaultdict
from collections.abc import Callable

from bson.objectid import ObjectId
from mongoengine.queryset.queryset import QuerySet
from mongoengine.queryset.visitor import QCombination

from app.models.documents import Documents


def get_all_documents() -> QuerySet:
    """Return *all* documents."""
    documents = Documents.objects()
    log.info(f"{len(documents):,d} documents found.")
    return _sort(documents)


def get_search_documents(search: str) -> QuerySet:
    """Return any documents matching the search term(s)."""
    ids = set()
    for search_method in SEARCH_METHODS:
        ids.update(search_method(search))

    # Return all the documents associated with the matching id's.
    documents = Documents.objects(id__in=ids)
    log.info(f"{len(documents):,d} documents found.")

    return _sort(documents)


def get_all_tags() -> list[str]:
    """Return a sorted list of all current tags (ie. those attached to documents)."""
    tags = defaultdict(int)
    for document in Documents.objects().only("tags"):
        for tag in document.tags:
            tags[tag] += 1
    log.info(f"{len(tags):,d} unique tags found.")
    return list(tags.items())


################################################################################
# Sub-search methods
################################################################################
def _search_by_title(search: str) -> list[ObjectId]:
    """Search all documents by "title"."""
    partials: QuerySet = Documents.objects(title__icontains=search).only("id")
    if partials:
        log.info(f"{len(partials):,d} documents matched against 'title'")
    return [doc.id for doc in partials]


def _search_by_source(search: str) -> list[ObjectId]:
    """Search all documents by "source"."""
    partials: QuerySet = Documents.objects(source__icontains=search).only("id")
    if partials:
        log.info(f"{len(partials):,d} documents matched against 'source'")
    return [doc.id for doc in partials]


def _search_by_tag(search: str) -> list[ObjectId]:
    """Search all documents by tag(s)."""
    if any(chr.isspace() for chr in search):
        # Split and "title" the search terms to match those within the database.
        l_search: list[str] = list(map(str.title, search.split()))

        # Yes..."or" and "and" semantic between the elements provided??

        ########################################
        # For an "or" semantic:
        # documents = Documents.objects(tags__in=search.split())
        ########################################
        ...

        ########################################
        # However, for the *and* semantic:
        ########################################
        from functools import reduce
        from operator import and_

        from mongoengine.queryset.visitor import Q

        queries: list[Q] = [Q(tags=tag) for tag in l_search]
        query: QCombination = reduce(and_, queries)
        partials: QuerySet = Documents.objects(query).only("id")
        if partials:
            log.info(f"{len(partials):,d} documents matched against multiple search terms")

    else:
        # No, use as is..
        partials: QuerySet = Documents.objects(tags=search.title()).only("id")
        if partials:
            log.info(f"{len(partials):,d} documents matched against single search")

    return [doc.id for doc in partials]


################################################################################
# Utility methods
################################################################################
def _sort(documents: list[Documents]) -> list[Documents]:
    """Return a sorted list of documents provided: quality and then by title."""
    return sorted(documents, key=lambda doc: (-doc.quality if doc.quality else 0, doc.title))


# Do an "auto" lookup of all search methods so we don't have to manually maintain a list...
def _find_search_methods(module: str, prefix: str) -> list[Callable]:
    return [getattr(module, obj) for obj in dir(module) if callable(getattr(module, obj)) and obj.startswith(prefix)]


SEARCH_METHODS = _find_search_methods(sys.modules[__name__], "_search_")
