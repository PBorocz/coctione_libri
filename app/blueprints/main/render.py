"""Main/home view, essentially the master table itself."""
import logging as log

from app.models.documents import Documents


def render_main(search: str | None = None) -> dict:
    if not search or search == "*":
        documents = Documents.objects()
        log.info(f"{len(documents):,d} documents found.")

    elif any(chr.isspace() for chr in search):
        # Split and "title" the search terms to match those within the database.
        l_search = list(map(str.title, search.split()))

        # Yes..."or" and "and" semantic between the elements provided??

        ########################################
        # For an "or" semantic:
        # documents = Documents.objects(tags__in=search.split())
        ########################################

        ########################################
        # However, for the *and* semantic:
        ########################################
        from functools import reduce
        from operator import and_

        from mongoengine.queryset.visitor import Q

        queries = [Q(tags=tag) for tag in l_search]
        query = reduce(and_, queries)
        documents = Documents.objects(query)

    else:
        # No, use as is..
        documents = Documents.objects(tags=search.title())

    # Sort!
    documents_sorted = sorted(documents, key=lambda doc: (doc.rating if doc.rating else "", doc.title), reverse=True)

    log.info(f"{len(documents):,d} matching documents found for {search=}")

    return {
        "documents": documents_sorted,
    }
