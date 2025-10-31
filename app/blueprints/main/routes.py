"""Core Application Routes."""

import logging as log
from functools import wraps
from pathlib import Path

import flask_login as fl
from flask import current_app, redirect, render_template, request, send_file, url_for
from flask.wrappers import Response
from flask_htmx import make_response
from flask_login import login_required
from flask_wtf import FlaskForm

from app.blueprints.main import bp
from app.blueprints.main.operations import delete_document, get_documents, update_document_attribute
from app.models import Sort, categories_available
from app.models.document import Document, sources_available, tags_available


def log_route(path=""):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            log.info("-" * 80)
            log.info(f" {request.method:4s} {path} -> {func.__name__}")
            log.info("-" * 80)
            return func(*args, **kwargs)

        return wrapper

    return decorator


################################################################################
# Primary full-page home page query and display
################################################################################
@bp.get("/")
@login_required
@log_route(path="/")
def render_display() -> Response:
    """Render our main page on a full page/refresh basis."""
    # Query & sort the documents..
    sort, documents = get_documents(fl.current_user, fl.current_user.payload.user_state.last_search)

    return render_template(
        "main/display.html",
        documents=documents,
        search=fl.current_user.payload.user_state.last_search,
        search_history=fl.current_user.payload.user_state.last_searches,
        sort=sort,
        category=fl.current_user.payload.user_state.last_category,
        categories=categories_available(),
    )


################################################################################
# Render JUST the main document table (ie. on an hx-post basis)
################################################################################
@bp.post("/")
@login_required
@log_route(path="/")
def hx_query() -> Response:
    """Render *just* our display table on an htmx-post call."""
    # Query & sort the documents..
    sort, documents = get_documents(fl.current_user, fl.current_user.payload.user_state.last_search)

    # Send back the id's of the docs in case user want's to delete 'em!
    public_ids = [str(doc.public_id) for doc in documents]

    rendered_template: str = render_template(
        "main/hx/display_table.html",
        documents=documents,
        search=fl.current_user.payload.user_state.last_search,
        sort=sort,
        form=FlaskForm(),
        num_docs=len(documents),
        public_ids=public_ids,
        category=fl.current_user.payload.user_state.last_category,
        categories=categories_available(),
    )
    return make_response(rendered_template, trigger="refresh-document-count")


################################################################################
# Reset page by clearing search and going directly back to the "main" route.
################################################################################
@bp.post("/reset")
@login_required
@log_route(path="/reset")
def reset() -> Response:
    """Render our display table (and controls) *AFTER* resetting user's search criteria."""
    payload = fl.current_user.payload
    payload.user_state.last_search = None
    fl.current_user.payload = payload
    fl.current_user.save()
    return hx_query()


################################################################################
@bp.get("/sort")
@login_required
@log_route(path="/sort")
def hx_display(template="main/hx/display_table.html") -> Response:
    """Re-render just our partial/main table for new sort field or direction."""
    sort = Sort.factory_from_request(request)
    payload = fl.current_user.payload
    payload.user_state.last_sort = sort.__dict__
    fl.current_user.payload = payload
    fl.current_user.save()

    # Query respective documents for the respective category and sort based on our state requested.
    sort, documents = get_documents(fl.current_user, fl.current_user.payload.user_state.last_search)

    # Render our partial template of the main display table:
    return render_template(
        template, documents=documents, sort=sort, search=fl.current_user.payload.user_state.last_search
    )


################################################################################
@bp.post("/user/category")
@login_required
@log_route(path="/user/category")
def hx_user_category_change() -> Response:
    """Change the display to the document category specified."""
    payload = fl.current_user.payload
    payload.user_state.last_category = request.values.get("category")
    fl.current_user.payload = payload
    fl.current_user.save()
    log.info(
        f"Changed user: {fl.current_user.id}'s document category to {fl.current_user.payload.user_state.last_category}"
    )
    return redirect(url_for("main.hx_display"))


################################################################################
@bp.get("/update-search-history")
@login_required
@log_route(path="/update-search-history")
def hx_update_search(template="main/hx/display_search_history.html") -> Response:
    return render_template(template, search_history=fl.current_user.payload.user_state.last_searches)


################################################################################
@bp.post("/search")
@login_required
@log_route(path="/search")
def hx_search(template="main/hx/display_table.html") -> Response:
    """Render the results table (only) based on a *SEARCH* request."""
    # Search could come in directly from the search dialog box (ie. request.form)
    # *or*
    # from clicking a selected tag or source (ie. request.values)
    if request.values.get("search"):
        search_term_s = request.values.get("search")
        log.debug(f"  direct search: {search_term_s}")
    else:
        search_term_s: str = request.form["search"]
        log.debug(f"  general search: {search_term_s}")

    # Query for all matching documents!
    sort, documents = get_documents(fl.current_user, search_term_s)

    # Update the user state regarding their last search performed.
    fl.current_user.update_search(search_term_s.casefold())

    # Send back the id's of the docs in case user want's to delete 'em!
    public_ids = [str(doc.public_id) for doc in documents]

    render_args = {
        "documents": documents,
        "category": fl.current_user.payload.user_state.last_category,
        "sort": sort,
        "search": search_term_s,
        "form": FlaskForm(),
        "public_ids": "|".join(public_ids),
        "num_docs": len(documents),
    }
    rendered_template = render_template(template, **render_args)
    return make_response(rendered_template, trigger="refresh-document-count")


################################################################################
@bp.get("/view/<public_id>")
@login_required
@log_route(path="/view")
def route_view_document(public_id: str, url: str = "main.render_display") -> Response:
    """Render a file (usually a pdf but could be a link/url as well)."""
    import flask as f  # noqa: PLC0415

    try:
        document = Document.get(Document.public_id == public_id)
    except Document.DoesNotExist:
        f.flash("Sorry, no document exists at the specified address.")
        return redirect(url_for(url))

    # Do we think we have a document to display?
    # if not document.fileid:
    #     # No, do we have a url instead?
    #     if document.url:
    #         # Yes, go there..
    #         return redirect(document.url)
    #     # Otherwise, stay here..
    #     return redirect(url_for(url))

    # Return from our "local" file directory...
    file_path = current_app.config["PATH_DATA"] / Path("documents") / Path(f"{public_id}.pdf")
    download_name = f"{document.id}.pdf"  # Better than the slug and any other options!
    try:
        return send_file(file_path, download_name=download_name, mimetype=document.mimetype)
    except FileNotFoundError:
        log.error(f"Sorry, unable to find the file associated with that document [{file_path}]")
        f.flash("Sorry, unable to find the file associated with that document.")
    except Exception as exc:
        log.error(str(exc))
        msg = "Sorry, we encountered an error serving that particular document's file."
        log.error(msg)
        f.flash(msg)

    return redirect(url_for(url))


################################################################################
@bp.post("/document/delete")
@login_required
@log_route(path="/document/delete")
def render_delete_document(url: str = "main.render_display") -> Response:
    """Delete the specified Document."""
    log.debug(f"{request.values=}")
    delete_document(current_app, fl.current_user, request.values["doc_id"])
    return redirect(url_for(url))


################################################################################
@bp.post("/documents/delete")
@login_required
@log_route(path="/documents/delete")
def render_delete_documents(url: str = "main.render_display") -> Response:
    """Delete the specified documents."""
    public_ids = request.values["public_ids"]
    for public_id in public_ids.split("|"):
        delete_document(current_app, fl.current_user, public_id)
    return redirect(url_for(url))


################################################################################
##
@bp.route("/new", methods=["GET", "POST"])
@login_required
@log_route(path="/new")
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
    document = Document(
        user=fl.current_user, title=request.form.get("title"), category=fl.current_user.payload.user_state.last_category
    )
    document.save()
    return redirect(url_for("main.render_edit_document", public_id_safe=document.public_id_safe))


################################################################################
@bp.get("/edit/<public_id_safe>")
@login_required
@log_route(path="/edit")
def render_edit_document(public_id_safe: str | None, template: str = "main/edit.html") -> Response:
    """Display the Document edit page (and nothing else, updates come in partial_edit_field!)."""
    document = Document.get_safe(public_id_safe)
    return_ = {
        "form": FlaskForm(),  # Needed for CSRF rendering on file input widget.
        "sources": sources_available(),  # Source pulldown options for user
        "tags": tags_available(),  # Tag pulldown options
        "no_search": True,
        "document": document,
    }
    return render_template(template, **return_)


################################################################################
@bp.route("/edit/<field>/<public_id_safe>", methods=["POST", "DELETE"])
@login_required
@log_route(path="/edit")
def hx_edit_field(field: str, public_id_safe: str) -> Response:
    """Edit an particular field/attribute of an Document."""
    document = Document.get_safe(public_id_safe)

    # Update the specified field in the document based on the inbound request, get doc and optional error msg
    document, error_msg = update_document_attribute(current_app, document, field, request)

    return_args = {
        "document": document,
        "sources": sources_available(),
        "tags": tags_available(),
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
    rendered_template: str = render_template(f"main/hx/edit_field_{field}.html", **return_args)

    # Also trigger any other events based on an newly updated document...
    # (for example, redisplay the last_updated datetime stamp at the top of the page)
    return make_response(rendered_template, trigger="updatedDocument")


################################################################################
@bp.get("/document/last_updated/<public_id_safe>")
@login_required
@log_route(path="/document/last_updated")
def hx_last_updated(public_id_safe: str, template: str = "main/hx/edit_last_updated.html") -> Response:
    """Partial render of particular document id's last update value."""
    document = Document.get_safe(public_id_safe)
    return render_template(template, document=document)
