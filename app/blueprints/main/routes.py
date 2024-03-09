"""Core Application Routes."""
import logging as log
from functools import wraps
from io import BytesIO

import flask_login as fl
from flask import make_response, redirect, render_template, request, send_file, url_for
from flask.wrappers import Response
from flask_login import login_required
from flask_wtf import FlaskForm
from mongoengine.context_managers import switch_collection

from app.blueprints.main import bp
from app.blueprints.main.operations import (
    delete_document,
    get_all_documents,
    get_search_documents,
    update_document_attribute,
)
from app.models import Sort, categories_available
from app.models.documents import Documents, sources_available, tags_available


def log_route_info(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        log.info("-" * 80)
        # For now, we don't need more information...
        # log.info(f"{request.method:4s} -> {func.__name__}")
        # log.info("-" * 80)
        return func(*args, **kwargs)

    return wrapper


################################################################################
@bp.get("/")
@login_required
@log_route_info
def render_display(template="main/display.html") -> Response:
    """Render our main page on a full refresh."""
    # Get any sort info (probably not on initial display)
    sort = Sort.factory(request)
    log.debug(sort)

    # Query the documents (and sort by last sort field/dir if we have one)
    documents = get_all_documents(fl.current_user, sort)

    # Render our template
    return render_template(template, documents=documents, sort=sort, categories=categories_available())


################################################################################
@bp.get("/sort")
@login_required
@log_route_info
def partial_display(template="main/partials/display_table.html") -> Response:
    """Re-render just our partial/main table for re-sort."""
    sort = Sort.factory(request)  # Get any sort info (probably not on initial display)

    # Query all the documents for the respective category and sort based on our state requested.
    documents = get_all_documents(fl.current_user, sort)

    # Render our partial template of the main display table:
    return render_template(template, documents=documents, sort=sort)


################################################################################
@bp.post("/user/category")
@login_required
@log_route_info
def partial_user_category_change() -> Response:
    """Change the display to the document category specified."""
    fl.current_user.category = request.values.get("category")
    fl.current_user.save()
    log.info(f"Changed user: {fl.current_user.id}'s document category to {fl.current_user.category}")
    return redirect(url_for("main.partial_display"))


################################################################################
@bp.post("/search")
@login_required
@log_route_info
def partial_search(template="main/partials/display_table.html") -> Response:
    """Render just the results table based on a *SEARCH* request."""
    sort = Sort.factory(request)
    log.debug(sort)

    search_term_s: str = request.form["search"]
    log.debug(f"{search_term_s=}")

    if search_term_s == "*" or not search_term_s:
        # Sometimes a "search" is not a "search" after all!
        documents = get_all_documents(fl.current_user, sort)
    else:
        documents = get_search_documents(fl.current_user, search_term_s, sort)

    return render_template(template, documents=documents, sort=sort, search=search_term_s)


################################################################################
@bp.get("/view/<doc_id>")
@login_required
@log_route_info
def route_view_document(doc_id: str, url: str = "main.render_display") -> Response:
    """Render a file (usually a pdf but could be a link/url as well)."""
    with switch_collection(Documents, Documents.as_user(fl.current_user)) as user_documents:
        document = user_documents.objects(id=doc_id)[0]

    if document.file_:
        file_contents = document.file_.read()
        log.debug(f"{len(file_contents)=}")
        contents: BytesIO = BytesIO(file_contents)
        name: str = f"{doc_id}.pdf"
        mimetype: str = document.file_.contentType
        return send_file(contents, download_name=name, mimetype=mimetype)

    elif document.url_:
        return redirect(document.url_)

    else:
        # FIXME: Would be nice to flash a message here..
        log.error("Sorry, document without either PDF file OR a link?")

    return redirect(url_for(url))


################################################################################
@bp.post("/document/delete")
@login_required
@log_route_info
def render_delete_document(url: str = "main.render_display") -> Response:
    """Delete the specified Document."""
    delete_document(fl.current_user, request.values["doc_id"])
    return redirect(url_for(url))


################################################################################
##
@bp.route("/new", methods=["GET", "POST"])
@login_required
@log_route_info
def render_new_document() -> Response:
    """Display/Process the Document edit page in 'new' mode.

    In "GET" mode, we simply render a page with a title entry input form.

    On successful POST of this, we create a new document (title only) of the
    user's respective category and redirect to the atomic edit page to get all
    the rest of the attributes.
    """
    if request.method == "GET":
        return render_template(
            "main/new.html", no_search=True, document=None, form=FlaskForm(), categories=categories_available()
        )

    # POST, create a new document and go to the field-based/atomic edit page to get all other attributes.
    with switch_collection(Documents, Documents.as_user(fl.current_user)) as user_documents:
        document = user_documents(
            user=fl.current_user, title=request.form.get("title"), category=fl.current_user.category
        )
        document.save()
    return redirect(url_for("main.render_edit_document", doc_id=document.id))


################################################################################
@bp.get("/edit/<doc_id>")
@login_required
@log_route_info
def render_edit_document(doc_id: str | None, template: str = "main/edit.html") -> Response:
    """Display the Document edit page (and nothing else, updates come in partial_edit_field!)."""
    with switch_collection(Documents, Documents.as_user(fl.current_user)) as user_documents:
        document = user_documents.objects(id=doc_id)[0]
        return_ = {
            "form": FlaskForm(),  # Needed for CSRF rendering on file input widget.
            "sources": sources_available(fl.current_user),  # Source pulldown options for user
            "tags": tags_available(fl.current_user),  # Tag pulldown options for user
            "no_search": True,
            "document": document,
        }
        return render_template(template, **return_)


################################################################################
@bp.route("/edit/<field>/<doc_id>", methods=["POST", "DELETE"])
@login_required
@log_route_info
def partial_edit_field(field: str, doc_id: str) -> Response:
    """Edit an particular field/attribute of an Document."""
    with switch_collection(Documents, Documents.as_user(fl.current_user)) as user_documents:
        document = user_documents.objects(id=doc_id)[0]

        # Update the specified field in the document based on the inbound request, get doc and optional error msg
        document, error_msg = update_document_attribute(document, field, request)

    return_args = {
        "document": document,
        "sources": sources_available(fl.current_user),
        "tags": tags_available(fl.current_user),
        "form": FlaskForm(),  # Need for CSRF rendering obo the "file" field (rest don't use form)
    }

    if error_msg:
        return_args["status"] = {
            "icon": {"color": "has-text-danger-dark", "icon": "fa-solid fa-circle-exclamation"},
            "error_msg": error_msg,
        }
    else:
        return_args["status"] = {"icon": {"color": "has-text-success", "icon": "fa-solid fa-circle-check"}}

    # (naming the templates after the respective field makes this easy!)
    template = render_template(f"main/partials/edit_field_{field}.html", **return_args)
    response: Response = make_response(template)

    # Trigger any other events based on an newly updated document...
    # (for example, redisplay the last_updated datetime stamp at the top of the page)
    response.headers["HX-Trigger"] = "updatedDocument"

    return response


################################################################################
@bp.get("/document/last_updated/<doc_id>")
@login_required
@log_route_info
def partial_last_updated(doc_id: str, template: str = "main/partials/edit_last_updated.html") -> Response:
    """Partial render of particular document id's last update value."""
    with switch_collection(Documents, Documents.as_user(fl.current_user)) as user_documents:
        document = user_documents.objects(id=doc_id)[0]
    return render_template(template, document=document)
