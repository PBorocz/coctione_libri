"""Main/home view, essentially the master table itself."""
import logging as log

from app.models import Documents


def render_main(search: str = None) -> dict:
    return_ = {}

    if not search or search == "*":
        return_["documents"] = Documents.objects()
        log.info(f"{len(return_['documents']):,d} documents found.")
        return return_

    # Any whitespace in our string to be split?
    if any(chr.isspace() for chr in search):
        # Split and "title" the search terms to match those within the database.
        l_search = list(map(str.title, search.split()))

        # Yes..."or" and "and" semantic between the elements provided??

        ########################################
        # For an "or" semantic:
        # return_["documents"] = Documents.objects(tags__in=search.split())
        ########################################

        ########################################
        # However, for the *and* semantic:
        ########################################
        from functools import reduce
        from operator import and_
        from mongoengine.queryset.visitor import Q

        queries = [Q(tags=tag) for tag in l_search]
        query = reduce(and_, queries)
        return_["documents"] = Documents.objects(query)

    else:
        # No, use as is..
        return_["documents"] = Documents.objects(tags=search.title())

    log.info(f"{len(return_['documents']):,d} matching documents found for {search=}")
    return return_
