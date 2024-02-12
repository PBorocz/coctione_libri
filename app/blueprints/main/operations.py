"""Main/home view, essentially the master table itself, either all or from search."""
import logging as log
import sys
from collections.abc import Callable

from bson.objectid import ObjectId
from mongoengine.queryset.queryset import QuerySet
from mongoengine.queryset.visitor import QCombination

from app import constants as c
from app.models.cookies import Cookies
from app.models.documents import Documents


def get_all_documents(cookies: Cookies) -> tuple[list[Documents], dict]:
    """Return *all* documents."""
    documents = Documents.objects()
    log.info(f"{len(documents):,d} documents found.")
    return _sort(documents, cookies)


def get_search_documents(cookies: Cookies, search: str) -> tuple[list[Documents], dict]:
    """Return any documents matching the search term(s)."""
    ids = set()
    for search_method in SEARCH_METHODS:
        ids.update(search_method(search))

    # Return all the documents associated with the matching id's.
    documents = Documents.objects(id__in=ids)
    log.info(f"{len(documents):,d} documents found.")

    return _sort(documents, cookies)


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
def _sort(documents: list[Documents], cookies: Cookies) -> tuple[list[Documents], dict]:
    """Return both a sorted list of documents by current cookies and sort-indicator status."""
    sort_field = cookies.sort_field
    sort_ascending = True if cookies.sort_dir == c.SORT_ASCENDING else False

    # fmt: off
    if sort_ascending:
        sort_lambdas = {
            "complexity" : lambda doc: (doc.complexity  is None, doc.complexity),
            "quality"    : lambda doc: (doc.quality     is None, doc.quality),
            "source"     : lambda doc: (doc.source      is None, doc.source),
            "tags"       : lambda doc: (doc.tags_as_str is None, doc.tags_as_str),
            "title"      : lambda doc:  doc.title,
        }
    else:
        sort_lambdas = {
            "complexity" : lambda doc: (doc.complexity  is not None, doc.complexity),
            "quality"    : lambda doc: (doc.quality     is not None, doc.quality),
            "source"     : lambda doc: (doc.source      is not None, doc.source),
            "tags"       : lambda doc: (doc.tags_as_str is not None, doc.tags_as_str),
            "title"      : lambda doc:  doc.title,
        }
    # fmt: on

    if not (sort_lambda := sort_lambdas.get(sort_field)):
        log.error(f"Sorry, ran into a case where cookies.sort_field is unrecognized? '{sort_field}'")
        sort_lambda = sort_lambdas.get("title")

    # Sort indicator is a dict keyed by the respective sort column with the right icon to
    # display This allows us to render the sort up/down arrow for EACH field (as
    # {{ sort_indicators.aField }}) and only the column that matches the key field will
    # actually have it's arrow displayed.
    if sort_ascending:
        sort_state = {sort_field: '<span class="icon is-size-6"><i class="fa-solid fa-sort-up"></i></span>'}
    else:
        sort_state = {sort_field: '<span class="icon is-size-6"><i class="fa-solid fa-sort-down"></i></span>'}

    # Apply sort direction..
    sorted_kwargs = {} if sort_ascending else {"reverse": True}

    return sorted(documents, key=sort_lambda, **sorted_kwargs), sort_state


def _find_search_methods(module: str, prefix: str) -> list[Callable]:
    """Do an "auto" lookup of all search methods so we don't have to manually maintain a list."""
    return [getattr(module, obj) for obj in dir(module) if callable(getattr(module, obj)) and obj.startswith(prefix)]


SEARCH_METHODS = _find_search_methods(sys.modules[__name__], "_search_")
