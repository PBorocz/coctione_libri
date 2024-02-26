"""Core Application Routes."""
import logging as log
from functools import wraps
from io import BytesIO

import flask_login as fl
from flask import make_response, redirect, render_template, request, send_file, url_for
from flask.wrappers import Response
from flask_login import login_required
from flask_wtf import FlaskForm

from app import constants as c
from app.blueprints.main import bp
from app.blueprints.main.operations import (
    delete_document,
    get_all_documents,
    get_search_documents,
    update_document_attribute,
)
from app.models.cookies import Cookies
from app.models.documents import Documents, sources_available, tags_available


def log_route_info(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        log.info("*" * 80)
        log.info(f"{request.method:4s} -> {func.__name__}")
        log.info("*" * 80)
        return func(*args, **kwargs)

    return wrapper


################################################################################
@bp.get("/")
@login_required
@log_route_info
def render_display(template="main/display.html") -> Response:
    """Render our main page on a full refresh."""
    # Pull the user-state/query parameters from the (cookie and form) obo the current user:
    cookies: Cookies = Cookies.factory_from_cookie(fl.current_user, request)

    # Query the documents (and sort by last sort field/dir if we have one)
    documents, sort_state = get_all_documents(cookies)

    # Render our template, set our cookie and we're done!
    template = render_template(template, documents=documents, cookies=cookies, sort_state=sort_state)
    response: Response = make_response(template)
    response.set_cookie(c.COOKIE_NAME, cookies.as_cookie())

    return response


################################################################################
@bp.get("/sort")
@login_required
@log_route_info
def partial_main_sorted(template="main/partials/display_table.html") -> Response:
    """Re-render our main table based on a new sort field and/or direction."""
    # Make sure we're coming in from an HTMX call..
    assert "Hx-Trigger" in request.headers
    trigger = request.headers.get("Hx-Trigger")
    log.debug(f"Hx-Trigger:{trigger}")

    # Pull the user-state/query parameters from the (cookie and form) obo the current user:
    cookies: Cookies = Cookies.factory_from_cookie(fl.current_user, request, update_sort=True)

    # Query all the documents and sort based on our state requested.
    documents, sort_state = get_all_documents(cookies)

    # Render our template, set our cookie and we're done!
    template: str = render_template(template, documents=documents, cookies=cookies, sort_state=sort_state)
    response: Response = make_response(template)
    response.set_cookie(c.COOKIE_NAME, cookies.as_cookie())

    return response


################################################################################
@bp.post("/search")
@login_required
@log_route_info
def partial_search(template="main/partials/display_table.html") -> Response:
    """Render just the results table based on a *SEARCH* request."""
    # Pull the user-state/query parameters from the (cookie and form) obo the current user:
    cookies: Cookies = Cookies.factory_from_cookie(fl.current_user, request)

    search_term_s: str = request.form["search"]

    log.debug(f"{search_term_s=}]")

    if search_term_s == "*" or not search_term_s:
        # Sometimes a "search" is not a "search" after all!
        documents, sort_state = get_all_documents(cookies)
    else:
        documents, sort_state = get_search_documents(cookies, search_term_s)

    return render_template(template, documents=documents, sort_state=sort_state)


################################################################################
@bp.get("/view/<doc_id>")
@login_required
@log_route_info
def route_view_document(doc_id: str, url: str = "main.render_display") -> Response:
    """Render a file (usually a pdf but could be a link/url as well)."""
    document = Documents.objects(id=doc_id)[0]
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
    delete_document(request.values["doc_id"])
    return redirect(url_for(url))


################################################################################
@bp.route("/new", methods=["GET", "POST"])
@login_required
@log_route_info
def render_new_document() -> Response:
    """Display/Process the Document edit page in 'new' mode."""
    if request.method == "GET":
        return render_template("main/manage.html", no_search=True, document=None, form=FlaskForm())

    # POST, create a new document and go back to the normal /edit to get all other attributes.
    document = Documents(user=fl.current_user, title=request.form.get("title"))
    document.save()
    return redirect(url_for("main.render_edit_document", doc_id=document.id))


################################################################################
@bp.get("/edit/<doc_id>")
@login_required
@log_route_info
def render_edit_document(doc_id: str | None, template: str = "main/manage.html") -> Response:
    """Display the Document edit page (and nothing else, updates come in partial_edit_field!)."""
    document = Documents.objects(id=doc_id)[0]
    return_ = {
        "form": FlaskForm(),  # Needed for CSRF rendering on file input widget.
        "sources": sources_available(),  # Source pulldown options
        "tags": tags_available(),  # Tag pulldown options
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
    document = Documents.objects(id=doc_id)[0]

    return_args = {
        "sources": sources_available(),
        "tags": tags_available(),
        "form": FlaskForm(),  # Need for CSRF rendering obo the "file" field (rest don't use form)
        "status": {  # We start with/assume a successful operation.
            "icon": {"color": "has-text-success", "icon": "fa-solid fa-circle-check"},
        },
    }

    # Update the specified field in the document based on the inbound request, get doc and optional error msg
    return_args["document"], error_msg = update_document_attribute(document, field, request)

    if error_msg:
        return_args["status"] = {
            "icon": {"color": "has-text-danger-dark", "icon": "fa-solid fa-circle-exclamation"},
            "error_msg": error_msg,
        }

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
    document = Documents.objects(id=doc_id)[0]
    return render_template(template, document=document)
