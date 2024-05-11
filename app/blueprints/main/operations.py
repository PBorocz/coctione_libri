"""Main/home view, essentially the master table itself, either all or from search."""

import logging as log
import shlex
import sys
from collections.abc import Callable
from datetime import datetime
from functools import reduce

from bson.objectid import ObjectId
from mongoengine.context_managers import switch_collection
from mongoengine.queryset.queryset import QuerySet
from mongoengine.queryset.visitor import QCombination
from werkzeug.utils import secure_filename

from app.models import Sort
from app.models.documents import Documents
from app.models.users import Users


def get_all_documents(user: Users, sort: Sort) -> tuple[list[Documents], dict]:
    """Return *all* documents."""
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        documents = user_documents.objects()
    log.debug(f"{len(documents):,d} documents found.")
    return _sort(documents, sort)


def get_search_documents(user: Users, search: str, sort: Sort) -> tuple[list[Documents], dict]:
    """Return any documents matching the search term(s).

    Note: We use shlex.split to handle case of quoted strings in search input, e.g.: '"coconut milk" burmese'
    """
    # We do an implicit "AND", thus, we want to capture the set of ids for each search term
    # and then "AND" them together.
    id_sets: list[set[str]] = []
    for search_term in shlex.split(search):
        ids = set()
        for search_method in SEARCH_METHODS:
            ids.update(search_method(user, search_term))
        id_sets.append(ids)

    ids_to_query = reduce(lambda a, b: a & b, id_sets)

    # Return all the documents associated with the matching id's.
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        documents = user_documents.objects(id__in=ids_to_query)
    log.info(f"{len(documents):,d} documents found.")

    return _sort(documents, sort)


################################################################################
# Sub-search methods
################################################################################
def _search_by_title(user: Users, search: str) -> list[ObjectId]:
    """Search all documents by "title"."""
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        partials: QuerySet = user_documents.objects(title__icontains=search).only("id")
    if partials:
        log.debug(f"{len(partials):,d} documents matched against 'title'")
    return [doc.id for doc in partials]


def _search_by_source(user: Users, search: str) -> list[ObjectId]:
    """Search all documents by "source"."""
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        partials: QuerySet = user_documents.objects(source__icontains=search).only("id")
    if partials:
        log.debug(f"{len(partials):,d} documents matched against 'source'")
    return [doc.id for doc in partials]


def _search_by_tag(user: Users, search: str) -> list[ObjectId]:
    """Search all documents by tag(s)."""
    if any(chr.isspace() for chr in search):
        # Split and "title" the search terms to match those within the database.
        l_search: list[str] = list(map(str.title, search.split()))

        # Yes..."or" and "and" semantic between the elements provided??

        ########################################
        # For an "or" semantic (which is what Raindrop does! :-()
        # documents = user_documents.objects(tags__in=search.split())
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
        with switch_collection(Documents, Documents.as_user(user)) as user_documents:
            partials: QuerySet = user_documents.objects(query).only("id")
        if partials:
            log.debug(f"{len(partials):,d} documents matched against multiple search terms")

    else:
        # No, use as is..
        with switch_collection(Documents, Documents.as_user(user)) as user_documents:
            partials: QuerySet = user_documents.objects(tags=search.title()).only("id")
        if partials:
            log.debug(f"{len(partials):,d} documents matched against single search")

    return [doc.id for doc in partials]


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
        document.file_.replace(file, fileName=filename, contentType="application/pdf")
        changed = True

    return document, changed


def delete_document(user: Users, id_: str) -> None:
    """Delete the document with specified id for the specified user."""
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        document = user_documents.objects(id=id_)[0]
        if document.file_:
            document.file_.delete()
        document.delete()


def update_document_attribute(document: Documents, field: str, request) -> [Documents, str | None]:
    """Update the specified field attribute of the document request.form the specified request.form."""
    error_msg = None
    match field:
        ##############################
        # Simple attributes: Str
        ##############################
        case "title" | "notes" | "url_" | "source":
            setattr(document, field, request.form.get(field))

        ##############################
        # Simple attributes: Int
        ##############################
        case "quality" | "complexity":
            try:
                new_value = int(request.form.get(field)) if request.form.get(field) else None
                setattr(document, field, new_value)
            except TypeError:
                error_msg = f"Sorry, {request.form.get(field)} is not a valid integer value."

        ##############################
        # Special Handling: File upload
        ##############################
        case "file_":
            file = request.files["file_"]
            filename = secure_filename(file.filename)  # Important! cleanse to remove bad characters!
            document.file_.replace(file, fileName=filename, contentType="application/pdf")

        ##############################
        # Special Attribute: List of string obo Tag
        ##############################
        case "tag":
            document, error_msg = _update_document_tags(document, request)

        ##############################
        # Special Attribute: List of dates obo dates_cooked
        ##############################
        case "dates_cooked":
            document, error_msg = _update_document_dates_cooked(document, request)

        case _:
            raise RuntimeError(f"Unrecognised {request.form.get('field')=}")

    # If we haven't run into an issue thus far, try to save the document.
    if not error_msg:
        try:
            document.save()
        except Exception as exc:
            error_msg = str(exc)

    return document, error_msg


def _update_document_tags(document: Documents, request) -> [Documents, str | None]:
    """Update the "tags" attribute of the specified document for the specified request."""
    if request.method == "POST":
        # NEW tag to be added to the document
        tag = request.form.get("tag")
        if tag.title() not in document.tags:
            document.tags.append(tag.title())
        else:
            return document, "Tag already appears for this document."
    elif request.method == "DELETE":
        # DELETE existing tag from the document
        tag = request.values.get("tag")
        document.update(pull__tags=tag)
        document.reload()
    return document, None


def _update_document_dates_cooked(document: Documents, request) -> [Documents, str | None]:
    """Update the "dates_cooked" attribute of the specified document for the specified request."""
    if request.method == "POST":
        # NEW date to be added to the document
        date_cooked = request.form.get("date_cooked")
        date_cooked = datetime.strptime(date_cooked, "%Y-%m-%d")
        if date_cooked not in document.dates_cooked:
            document.dates_cooked.append(date_cooked)
        else:
            return document, "Sorry, your already have this date entered."

    elif request.method == "DELETE":
        # DELETE existing date from the document
        date_cooked = request.values.get("date_cooked")
        document.update(pull__dates_cooked=date_cooked)
        document.reload()
    return document, None


################################################################################
# Utility methods
################################################################################
def _sort(documents: list[Documents], sort: Sort) -> tuple[list[Documents], dict]:
    """Return both a sorted list of documents by current cookies and sort-indicator status."""
    # fmt: off
    if sort.is_ascending():
        # These are a bit complex *but* allow us to make sure that "None" entries of the
        # respective `sort.by` field are always at the bottom, irrespective of `sort.order`.
        sort_lambdas = {
            "complexity"            : lambda doc: (doc.complexity            is None, doc.complexity            ),
            "last_cooked"           : lambda doc: (doc.last_cooked           is None, doc.last_cooked           ),
            "quality"               : lambda doc: (doc.quality               is None, doc.quality               ),
            "quality_by_complexity" : lambda doc: (doc.quality_by_complexity is None, doc.quality_by_complexity ),
            "source"                : lambda doc: (doc.source                is None, doc.source                ),
            "tags"                  : lambda doc: (doc.tags_for_sort         is None, doc.tags_for_sort         ),
            "title"                 : lambda doc:  doc.title,
        }
    else:
        sort_lambdas = {
            "complexity"            : lambda doc: (doc.complexity            is not None, doc.complexity            ),
            "last_cooked"           : lambda doc: (doc.last_cooked           is not None, doc.last_cooked           ),
            "quality"               : lambda doc: (doc.quality               is not None, doc.quality               ),
            "quality_by_complexity" : lambda doc: (doc.quality_by_complexity is not None, doc.quality_by_complexity ),
            "source"                : lambda doc: (doc.source                is not None, doc.source                ),
            "tags"                  : lambda doc: (doc.tags_for_sort         is not None, doc.tags_for_sort         ),
            "title"                 : lambda doc:  doc.title,
        }
    # fmt: on

    if not (sort_lambda := sort_lambdas.get(sort.by)):
        log.error(f"Sorry, ran into a case where cookies.sort.by is unrecognized? '{sort.by}'")
        sort_lambda = sort_lambdas.get("title")

    # Apply sort order/direction:
    sorted_kwargs = {} if sort.is_ascending() else {"reverse": True}

    return sorted(documents, key=sort_lambda, **sorted_kwargs)


def _find_search_methods(module: str, prefix: str) -> list[Callable]:
    """Do an "auto" lookup of all search methods so we don't have to manually maintain a list."""
    return [getattr(module, obj) for obj in dir(module) if callable(getattr(module, obj)) and obj.startswith(prefix)]


SEARCH_METHODS = _find_search_methods(sys.modules[__name__], "_search_")
