"""Main/home view, essentially the master table itself, either all or from search."""

import logging as log
import mimetypes
import shlex
import sys
from collections.abc import Callable
from datetime import datetime
from functools import reduce

from botocore.exceptions import ClientError
from bson.objectid import ObjectId
from flask import current_app
from mongoengine.context_managers import switch_collection
from mongoengine.queryset.queryset import QuerySet
from mongoengine.queryset.visitor import QCombination
from werkzeug.utils import secure_filename

from app.models import Sort
from app.models.documents import Documents
from app.models.user import User


def get_documents(user: User, search: str | None = None) -> tuple[Sort, list[Documents]]:
    """CORE query to return documents, with or without search term(s).

    Note: We use shlex.split to handle case of quoted strings in search input, e.g.: '"coconut milk" burmese'
    """
    # We do an implicit "AND", thus, we want to capture the set of ids for each search term
    # and then "AND" them together.
    if search:
        id_sets: list[set[str]] = []
        for search_term in shlex.split(search):
            ids = set()
            for search_method in SEARCH_METHODS:
                ids.update(search_method(user, search_term))
            id_sets.append(ids)
        ids_to_query = reduce(lambda a, b: a & b, id_sets)

    # Return either *ALL* the documents or just those associated with the search matching id's:
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        kw_args = {"id__in": ids_to_query} if search else {}
        documents = user_documents.objects(**kw_args)
    log.debug(f"{len(documents):4d} documents found.")

    return _sort(user, documents)


################################################################################
# Sub-search methods
################################################################################
def _search_by_title(user: User, search: str) -> list[ObjectId]:
    """Search all documents by "title"."""
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        partials: QuerySet = user_documents.objects(title__icontains=search).only("id")
    if partials:
        log.debug(f"{len(partials):4d} documents matched against 'title'")
    return [doc.id for doc in partials]


def _search_by_source(user: User, search: str) -> list[ObjectId]:
    """Search all documents by "source"."""
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        partials: QuerySet = user_documents.objects(source__icontains=search).only("id")
    if partials:
        log.debug(f"{len(partials):4d} documents matched against 'source'")
    return [doc.id for doc in partials]


def _search_by_tag(user: User, search: str) -> list[ObjectId]:
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
            log.debug(f"{len(partials):3d} documents matched against multiple search terms")

    else:
        # No, use as is..
        with switch_collection(Documents, Documents.as_user(user)) as user_documents:
            partials: QuerySet = user_documents.objects(tags=search.title()).only("id")
        if partials:
            log.debug(f"{len(partials):4d} documents matched against single search")

    return [doc.id for doc in partials]


def delete_document(app, user: User, id_: str) -> None:
    """Delete the document with specified id for the specified user."""
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        document = user_documents.objects(id=id_)[0]
        s_doc_id = str(document.id)
        try:
            storage_handle = app.config["STORAGE_FILE"]
            storage_bucket = app.config["storage_file_bucket"]
            args = {"Bucket": storage_bucket, "Key": s_doc_id}
            storage_handle.head_object(**args)
            storage_handle.delete_object(**args)
        except ClientError as e:
            if e.response["Error"]["Code"] != "404":
                log.error(f"Error deleting object {s_doc_id} from bucket {storage_bucket}: {e}!")
        document.delete()


def update_document_attribute(app, document: Documents, field: str, request) -> [Documents, str | None]:
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
            # Yes, there's no error handling here....sue me
            file = request.files["file_"]
            document.filename = secure_filename(file.filename)  # Important! cleanse to remove bad characters!
            document.filesize = get_file_size(file)
            document.mimetype = mimetypes.guess_type(document.filename)[0]
            app.config["STORAGE_FILE"].upload_fileobj(
                file.stream, current_app.config["storage_file_bucket"], str(document.id)
            )

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
def get_file_size(file_handle) -> int:
    # Remember the current position
    current_position = file_handle.tell()

    # Seek to the end of the file
    file_handle.seek(0, 2)  # 2 means "from the end"

    # Get the position of the end of the file (which is the size)
    size = file_handle.tell()

    # Return to the original position
    file_handle.seek(current_position)

    return size


def _sort(user: User, documents: list[Documents]) -> tuple[list[Documents], dict]:
    """Return both a sorted list of documents by current cookies and sort-indicator status."""
    sort: Sort = Sort.factory_from_user(user)  # Unpack the sort info from user state.

    # fmt: off
    if sort.is_ascending():
        # These are a bit complex *but* allow us to make sure that "None" entries of the
        # respective `sort.by` field are always at the bottom, irrespective of `sort.order`.
        sort_lambdas = {
            "complexity"            : lambda doc: (doc.complexity            is None, doc.complexity            ),
            "times_cooked"          : lambda doc: (doc.times_cooked          is None, doc.times_cooked          ),
            "quality"               : lambda doc: (doc.quality               is None, doc.quality               ),
            "quality_by_complexity" : lambda doc: (doc.quality_by_complexity is None, doc.quality_by_complexity ),
            "source"                : lambda doc: (doc.source                is None, doc.source                ),
            "tags"                  : lambda doc: (doc.tags_for_sort         is None, doc.tags_for_sort         ),
            "url_"                  : lambda doc: (doc.url_                  is None, doc.url_                  ),
            "title"                 : lambda doc:  doc.title,
        }
    else:
        sort_lambdas = {
            "complexity"            : lambda doc: (doc.complexity            is not None, doc.complexity            ),
            "times_cooked"          : lambda doc: (doc.times_cooked          is not None, doc.times_cooked          ),
            "quality"               : lambda doc: (doc.quality               is not None, doc.quality               ),
            "quality_by_complexity" : lambda doc: (doc.quality_by_complexity is not None, doc.quality_by_complexity ),
            "source"                : lambda doc: (doc.source                is not None, doc.source                ),
            "tags"                  : lambda doc: (doc.tags_for_sort         is not None, doc.tags_for_sort         ),
            "url_"                  : lambda doc: (doc.url_                  is not None, doc.url_                  ),
            "title"                 : lambda doc:  doc.title,
        }
    # fmt: on

    if not (sort_lambda := sort_lambdas.get(sort.by)):
        log.error(f"Sorry, ran into a case where cookies.sort.by is unrecognized? '{sort.by}'")
        sort_lambda = sort_lambdas.get("title")

    # Apply sort order/direction:
    sorted_kwargs = {} if sort.is_ascending() else {"reverse": True}

    return sort, sorted(documents, key=sort_lambda, **sorted_kwargs)


def _find_search_methods(module: str, prefix: str) -> list[Callable]:
    """Do an "auto" lookup of all search methods so we don't have to manually maintain a list."""
    return [getattr(module, obj) for obj in dir(module) if callable(getattr(module, obj)) and obj.startswith(prefix)]


SEARCH_METHODS = _find_search_methods(sys.modules[__name__], "_search_")
