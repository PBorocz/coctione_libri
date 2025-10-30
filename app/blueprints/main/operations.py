"""Main/home view, essentially the master table itself, either all or from search."""

import logging as log
import mimetypes
import shlex
import sys
from collections.abc import Callable
from datetime import datetime
from functools import reduce
from pathlib import Path

from bson.objectid import ObjectId
from flask import current_app
from mongoengine.context_managers import switch_collection
from mongoengine.queryset.queryset import QuerySet
from mongoengine.queryset.visitor import QCombination
from peewee import SQL
from werkzeug.utils import secure_filename

from app.models import Sort
from app.models.document import Document
from app.models.documents import Documents
from app.models.user_rdb import User


def get_documents(user: User, search: str | None = None) -> tuple[Sort, list[Document]]:
    """CORE query to return documents, with or without search term(s).

    Note: We use shlex.split to handle case of quoted strings in search input, e.g.: '"coconut milk" burmese'
    """
    # We do an implicit "AND", thus, we want to capture the set of ids for each search term
    # and then "AND" them together.
    ids_to_query = None
    if search:
        id_sets: list[set[str]] = []
        for search_term in shlex.split(search):
            ids = set()
            for search_method in SEARCH_METHODS:
                ids.update(search_method(user, search_term))
            id_sets.append(ids)
        ids_to_query = reduce(lambda a, b: a & b, id_sets)

    # Return either *ALL* the documents or just those associated with the search matching id's:
    documents = Document.select().where(
        Document.user == user, Document.category == user.payload.user_state.last_category
    )

    if ids_to_query:
        documents = documents.where(Document.id.in_(ids_to_query))
    log.debug(f"{len(documents):4d} documents found.")

    return _sort(user, documents)


################################################################################
# Sub-search methods
################################################################################
def _sch_by_title(user: User, search: str) -> list[ObjectId]:
    """Search all documents by "title"."""
    partials = Document.select().where(Document.user == user, Document.title.contains(search))
    if partials:
        log.debug(f"{len(partials):4d} documents matched against 'title'")
    return [doc.id for doc in partials]


def _sch_by_source(user: User, search: str) -> list[ObjectId]:
    """Search all documents by "source"."""
    partials = Document.select().where(Document.user == user, Document.source.contains(search))
    if partials:
        log.debug(f"{len(partials):4d} documents matched against 'source'")
    return [doc.id for doc in partials]


def _search_by_tag(user: User, search: str) -> list[int]:
    """Search all documents by tag(s)."""
    l_search: list[str] = [search.lower()] if " " not in search else list(map(str.lower, search.split()))
    log.debug(f"{l_search=}")

    partials = Document.select(Document.id).where(Document.user == user.id)
    for tag in l_search:
        partials = partials.where(Document.tags % f"*{tag}*")

    if len(l_search) > 1:
        log.debug(f"{len(partials):3d} documents matched against multiple search terms {l_search}")
    else:
        log.debug(f"{len(partials):4d} documents matched against single search: {l_search}")

    return [doc.id for doc in partials]


def delete_document(app, user: User, public_id: str) -> None:
    """Delete the document with specified id."""
    document = Document.get(Document.public_id == public_id)
    file_path = app.config["PATH_DATA"] / Path("documents") / Path(f"{document.id}.pdf")
    try:
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            document.delete()
            return True
        else:
            log.error(f"Sorry, unable to find {file_path=}?")
            return False
    except (OSError, PermissionError) as exc:
        log.error(f"Failed to delete file {file_path}: {exc}")
        return False


def update_document_attribute(app, document: Document, field: str, request) -> [Document, str | None]:
    """Update the specified field attribute of the document request.form the specified request.form."""
    error_msg = None
    match field:
        ##############################
        # Simple attributes: Str
        ##############################
        case "title" | "notes" | "url" | "source":
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
            document.fileid = str(document.id)
            document.filename = secure_filename(file.filename)  # Important! cleanse to remove bad characters!
            document.filesize = get_file_size(file)
            document.mimetype = mimetypes.guess_type(document.filename)[0]
            app.config["STORAGE_FILE"].upload_fileobj(
                file.stream, current_app.config["STORAGE_FILE_BUCKET"], str(document.id)
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


def _update_document_tags(document: Document, request) -> [Document, str | None]:
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
        document.tags.remove(tag.title())

    document.save()
    return document, None


def _update_document_dates_cooked(document: Document, request) -> [Document, str | None]:
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
        document.dates_cooked.remove(date_cooked)

    document.save()
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


def _sort(user: User, documents: list[Document]) -> tuple[list[Document], dict]:
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
            "tags"                  : lambda doc: (doc.tags                  is None, doc.tags                  ),
            "url"                   : lambda doc: (doc.url                   is None, doc.url                   ),
            "title"                 : lambda doc:  doc.title,
        }
    else:
        sort_lambdas = {
            "complexity"            : lambda doc: (doc.complexity            is not None, doc.complexity            ),
            "times_cooked"          : lambda doc: (doc.times_cooked          is not None, doc.times_cooked          ),
            "quality"               : lambda doc: (doc.quality               is not None, doc.quality               ),
            "quality_by_complexity" : lambda doc: (doc.quality_by_complexity is not None, doc.quality_by_complexity ),
            "source"                : lambda doc: (doc.source                is not None, doc.source                ),
            "tags"                  : lambda doc: (doc.tags                  is not None, doc.tags                  ),
            "url"                   : lambda doc: (doc.url                   is not None, doc.url                   ),
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
