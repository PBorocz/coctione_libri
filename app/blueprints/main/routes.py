"""Core Application Routes."""
import logging as log
from io import BytesIO

import flask_login as fl
from flask import make_response, send_file
from flask.wrappers import Response
from flask_login import login_required
from flask_wtf import FlaskForm

from app import constants as c
from app.blueprints.main import bp
from app.blueprints.main.operations import (
    delete_document,
    get_all_documents,
    get_search_documents,
    new_document,
    update_document_attribute,
)
from app.models.cookies import Cookies
from app.models.documents import Documents, sources_available


################################################################################
@bp.get("/")
@login_required
def render_main(template="main/main.html") -> Response:
    """Render our main page on a full refresh."""
    import flask as f

    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    # Pull the user-state/query parameters from the (cookie and form) obo the current user:
    cookies: Cookies = Cookies.factory_from_cookie(fl.current_user, f.request)

    # Query the documents (and sort by last sort field/dir if we have one)
    documents, sort_state = get_all_documents(cookies)

    # Render our template, set our cookie and we're done!
    template = f.render_template(template, documents=documents, cookies=cookies, sort_state=sort_state)
    response: Response = make_response(template)
    response.set_cookie(c.COOKIE_NAME, cookies.as_cookie())

    log.info("*" * 80)
    return response


################################################################################
@bp.get("/sort")
@login_required
def partial_main_sorted(template="main/partials/table.html") -> Response:
    """Re-render our main table based on a new sort field and/or direction."""
    import flask as f

    # Make sure we're coming in from an HTMX call..
    assert "Hx-Trigger" in f.request.headers
    trigger = f.request.headers.get("Hx-Trigger")
    log.info(f"Hx-Trigger:{trigger}")

    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    # Make sure we're coming in from an HTMX call..
    assert "Hx-Trigger" in f.request.headers
    trigger = f.request.headers.get("Hx-Trigger")
    log.info(f"Hx-Trigger:{trigger}")

    # Pull the user-state/query parameters from the (cookie and form) obo the current user:
    cookies: Cookies = Cookies.factory_from_cookie(fl.current_user, f.request, update_sort=True)

    # Query all the documents and sort based on our state requested.
    documents, sort_state = get_all_documents(cookies)

    # Render our template, set our cookie and we're done!
    template = f.render_template(template, documents=documents, cookies=cookies, sort_state=sort_state)
    response: Response = make_response(template)
    response.set_cookie(c.COOKIE_NAME, cookies.as_cookie())

    log.info("*" * 80)
    return response


################################################################################
@bp.post("/search")
@login_required
def partial_search(template="main/partials/table.html") -> Response:
    """Render just the results table based on a *SEARCH* request."""
    import flask as f

    # Pull the user-state/query parameters from the (cookie and form) obo the current user:
    cookies: Cookies = Cookies.factory_from_cookie(fl.current_user, f.request)

    search_term_s: str = f.request.form["search"]

    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /search ['{search_term_s}']")

    if search_term_s == "*" or not search_term_s:
        # Sometimes a "search" is not a "search" after all!
        documents, sort_state = get_all_documents(cookies)
    else:
        documents, sort_state = get_search_documents(cookies, search_term_s)

    log.info("*" * 80)
    return f.render_template(template, documents=documents, sort_state=sort_state)


################################################################################
@bp.get("/view/<doc_id>")
@login_required
def route_view_document(doc_id: str, template: str = "main.render_main") -> Response:
    """Render a file (for now, usually a pdf)."""
    import flask as f

    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    document = Documents.objects(id=doc_id)[0]
    if document.file_:
        file_contents = document.file_.read()
        log.info(f"{len(file_contents)=}")
        contents = BytesIO(file_contents)
        name = f"{doc_id}.pdf"
        mimetype = document.file_.content_type
        return send_file(contents, download_name=name, mimetype=mimetype)
    elif document.url_:
        f.redirect(document.url_)
    else:
        log.error("Sorry, document without either PDF file OR a link?")

    return f.redirect(f.url_for(template))


################################################################################
@bp.post("/document/delete")
@login_required
def render_delete_document(template: str = "main.render_main") -> Response:
    """Delete the specified Document."""
    import flask as f

    log.info("*" * 80)
    log.info(f"{f.request.method.upper()}")
    delete_document(f.request.values["doc_id"])
    log.info("*" * 80)
    return f.redirect(f.url_for(template))


################################################################################
@bp.get("/edit/<doc_id>")
@login_required
def render_edit_document(doc_id: str) -> Response:
    """Display the Document edit page."""
    import flask as f

    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")
    log.info(f"{doc_id=}")
    document = Documents.objects(id=doc_id)[0]

    # Default return values for BOTH GET and POST Calls
    return_ = {
        "form": FlaskForm(),  # Need for CSRF rendering,
        "sources": sources_available(),
        "no_search": True,
        "title": "Edit Document",
    }
    log.info("*" * 80)
    return_["document"] = document
    return f.render_template("main/edit_document.html", **return_)


################################################################################
@bp.get("/document/last_updated/<doc_id>")
@login_required
def partial_last_updated(doc_id: str) -> Response:
    """Partial render of document's last update value."""
    import flask as f

    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")
    log.info(f"{doc_id=}")
    document = Documents.objects(id=doc_id)[0]
    return f.render_template("main/partials/edit_last_updated.html", document=document)


################################################################################
@bp.route("/edit/<field>/<doc_id>", methods=["POST", "DELETE"])
@login_required
def partial_edit_field(field: str, doc_id: str) -> Response:
    """Edit an particular field/attribute of an Document."""
    import flask as f

    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")
    log.info(f"{field=}")
    log.info(f"{doc_id=}")
    document = Documents.objects(id=doc_id)[0]

    # Default return values
    return_args = {
        "sources": sources_available(),
        "form": FlaskForm(),  # Need for CSRF rendering obo the "file" field (rest don't use form)
        "status": {  # We start with/assume a successful operation.
            "icon": {"color": "has-text-success", "icon": "fa-solid fa-circle-check"},
        },
    }

    # Update the specified field in the document based on the inbound request, get doc and optional error msg
    return_args["document"], error_msg = update_document_attribute(document, field, f.request)

    if error_msg:
        return_args["status"] = {
            "icon": {"color": "has-text-danger-dark", "icon": "fa-solid fa-circle-exclamation"},
            "error_msg": error_msg,
        }

    # (naming the templates after the respective field makes this easy!)
    template = f.render_template(f"main/partials/edit_field_{field}.html", **return_args)
    response: Response = make_response(template)
    response.headers["HX-Trigger"] = "updatedDocument"
    return response


################################################################################
@bp.route("/add", methods=["POST", "GET"])
@login_required
def render_add_document(template="main/add_document.html") -> Response:
    """Add/create a *new* Document."""
    import flask as f

    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    # On GET, simply present the page to fill out...
    if f.request.method == "GET":
        log.info("*" * 80)
        return f.render_template(
            template,
            title="Add Document",
            form=FlaskForm(),
            sources=sources_available(),
            document=None,
            errors={},
            no_search=True,
        )

    # On POST, we need to create & save a new document unless we've canceled
    if f.request.form.get("cancel"):
        return f.redirect(f.url_for("main.render_main"))

    # Create a new doc
    new_document(fl.current_user, f.request)

    log.info("*" * 80)
    return f.redirect(f.url_for("main.render_main"))
