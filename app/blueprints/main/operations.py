"""Main/home view, essentially the master table itself, either all or from search."""
import logging as log
import shlex
import sys
from collections.abc import Callable
from datetime import datetime
from functools import reduce

from bson.objectid import ObjectId
from mongoengine.queryset.queryset import QuerySet
from mongoengine.queryset.visitor import QCombination
from werkzeug.utils import secure_filename

from app import constants as c
from app.models.cookies import Cookies
from app.models.documents import Documents


def get_all_documents(cookies: Cookies) -> tuple[list[Documents], dict]:
    """Return *all* documents."""
    documents = Documents.objects()
    log.info(f"{len(documents):,d} documents found.")
    return _sort(documents, cookies)


def get_search_documents(cookies: Cookies, search: str) -> tuple[list[Documents], dict]:
    """Return any documents matching the search term(s).

    Note: We use shlex.split to handle case of quoted strings in search input, e.g.: '"coconut milk" burmese'
    """
    # We do an implicit "AND", thus, we want to capture the set of ids for each search term
    # and then "AND" them together.
    id_sets: list[set[str]] = []
    for search_term in shlex.split(search):
        ids = set()
        for search_method in SEARCH_METHODS:
            ids.update(search_method(search_term))
        id_sets.append(ids)

    ids_to_query = reduce(lambda a, b: a & b, id_sets)

    # Return all the documents associated with the matching id's.
    documents = Documents.objects(id__in=ids_to_query)
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
# Factory method to create/return a new Document from inbound form.
################################################################################
def new_doc_from_form(current_user, request) -> Documents:
    """Create a *new* document from the respective form."""
    form = request.form
    # Simple attributes:
    # fmt: off
    document = Documents(
        user       = current_user,       # Required
        title      = form.get("title" ), # "
        source     = form.get("source"),
        url_       = form.get("url_"  ),
        notes      = form.get("notes" ),
        quality    = int(form.get("quality"))    if form.get("quality")    else None,
        complexity = int(form.get("complexity")) if form.get("complexity") else None,
    )
    # fmt: on

    ################
    # Special cases
    ################
    if form.get("tags"):
        document.set_tags_from_str(form.get("tags"))

    # Last Cooked date (as first/only entry in list)"
    if form.get("last_cooked"):
        dt_last_cooked = datetime.strptime(form.get("last_cooked"))
        document.dates_cooked.append(dt_last_cooked)

    # Did we also get a new file to upload along with it (we may not!)
    if file := request.files["file_"]:
        filename = secure_filename(file.filename)  # Important! cleanse to remove bad characters!
        log.info(f"Saving a *new* file...{filename=}!")
        document.file_.put(file, filename=filename, content_type="application/pdf")

    return document


def update_doc_from_form(request, document: Documents) -> tuple[Documents, bool]:
    """Update the document attributes from the flask form in the request, returning the doc and changed flag."""
    form_document_attrs = (
        (None, "title"),
        (None, "notes"),
        (None, "source"),
        (None, "url_"),
        ("to_list", "tags"),
        ("to_int", "quality"),
        ("to_int", "complexity"),
    )

    # Get Flask's packaging of the inbound form
    form = request.form

    # Start on the assumption that NO attribute have actually changed...
    changed = False

    # Handle all the "simple" attributes on a generic basis..
    for conversion, attr in form_document_attrs:
        curr_value = getattr(document, attr)  # Value in the current document, ie. in db.
        form_value = form.get(attr)  # Value coming back from the form.
        if conversion == "to_int":
            form_value = int(form_value)
        elif conversion == "to_list":
            form_value = [x.strip().title() for x in form_value.split(",")]

        ################################################################################
        # Case 1: Have both a form_value and current document value
        #         -> Check for match and update if necessary
        ################################################################################
        if form_value and curr_value:
            if form_value != curr_value:
                changed = True
                setattr(document, attr, form_value)
                log.debug(f"{attr=} was updated to {form_value} (from {curr_value})")

        ################################################################################
        # Case 2: Have a new form_value but not current document value
        #         -> Update document with new value.
        ################################################################################
        elif form_value and not curr_value:
            changed = True
            setattr(document, attr, form_value)
            log.debug(f"{attr=} was newly set to {form_value}")

        ################################################################################
        # Case 3: Don't have a new form_value but do have a current document value
        #         -> Update document value to None.
        ################################################################################
        elif not form_value and curr_value:
            changed = True
            setattr(document, attr, None)
            log.debug(f"{attr=} was cleared")

        # Case 4: Don't have a new form_value and don't have a current document value
        #         -> Do Nothing!
        else:
            assert not form_value and not curr_value, f"Sorry, unhandled case: {form_value=} {curr_value=}"

    #################
    # Special cases #
    #################
    # Last cooked date onto list.."
    if form.get("last_cooked"):
        dt_last_cooked = datetime.strptime(form.get("last_cooked"), "%Y-%m-%d")
        if dt_last_cooked not in document.dates_cooked:
            log.debug(f"attr=last_cooked was appended to with {dt_last_cooked}")
            document.dates_cooked.append(dt_last_cooked)
            changed = True

    # Did we get a new file to upload?
    if file := request.files["file_"]:
        filename = secure_filename(file.filename)  # Important! cleanse to remove bad characters!
        msg = (
            f"Saving a new file: {filename=}!"
            if document.file_
            else f"Replacing existing file {document.file_.filename=} with: {filename=}!"
        )
        log.debug(msg)
        document.file_.replace(file, filename=filename, content_type="application/pdf")
        changed = True

    return document, changed


def remove_tag(id_: str, tag: str) -> Documents:
    """Remove the specified tag from the document with the specified id."""
    document = Documents.objects(id=id_)[0]
    document.update(pull__tags=tag)
    return Documents.objects(id=id_)[0]


def delete_document(document: Documents | None = None, id_: str | None = None) -> None:
    """Delete the specified document (or the one with the specified id)."""
    assert document or id_, "Sorry, we need EITHER a document or a document id!"
    if not document:
        document = Documents.objects(id=id_)[0]
    if document.file_:
        document.file_.delete()
    document.delete()


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
