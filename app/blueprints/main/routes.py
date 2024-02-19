"""Core Application Routes."""
import logging as log
from datetime import datetime
from io import BytesIO

import flask_login as fl
from flask import make_response, send_file
from flask.wrappers import Response
from flask_login import login_required
from flask_wtf import FlaskForm

from app import constants as c
from app.blueprints.main import bp
from app.blueprints.main.operations import (
    get_all_documents,
    get_search_documents,
    new_doc_from_form,
    update_doc_from_form,
)
from app.models.cookies import Cookies
from app.models.documents import Documents, sources_available


class DocumentEditForm(FlaskForm):
    pass


################################################################################
@bp.get("/")
@login_required
def render_main(template="main/main.html") -> Response:
    """Render our main page on a full refresh."""
    import flask as f

    log.info("")
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
def render_table_sorted(template="main/partials/table.html") -> Response:
    """Re-render our main table based on a new sort field and/or direction."""
    import flask as f

    log.info("")
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
def render_search(template="main/partials/table.html") -> Response:
    """Render just the results table based on a *SEARCH* request."""
    import flask as f

    # Pull the user-state/query parameters from the (cookie and form) obo the current user:
    cookies: Cookies = Cookies.factory_from_cookie(fl.current_user, f.request)

    search_term_s: str = f.request.form["search"]

    log.info("")
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
def render_view_doc(doc_id: str) -> Response:
    """Render a file (for now, usually a pdf)."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    document = Documents.objects(id=doc_id)[0]
    if document.file_:
        file_contents = document.file_.read()
        log.info(f"{len(file_contents)=}")

        return send_file(
            BytesIO(file_contents),
            download_name=f"{doc_id}.pdf",
            mimetype=document.file_.content_type,
        )
    elif document.url_:
        f.redirect(document.url_)
    else:
        log.error("Sorry, document without either PDF file OR a link?")

    return f.redirect(f.url_for("main.render_main"))


################################################################################
@bp.route("/delete/<doc_id>", methods=["GET"])
@login_required
def render_delete_doc(doc_id: str) -> Response:
    """Delete a document."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    document = Documents.objects(id=doc_id)[0]

    if document.file_:
        document.file_.delete()

    document.delete()

    return f.redirect(f.url_for("main.render_main"))


################################################################################
@bp.route("/edit/<doc_id>", methods=["POST", "GET"])
@login_required
def render_edit_doc(doc_id: str, template: str = "main/add_edit.html") -> Response:
    """Edit the attributes of an existing Document."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    # Get the document we might be changing...
    document = Documents.objects(id=doc_id)[0]

    # On GET, simply present the document for editing..
    if f.request.method == "GET":
        log.info("*" * 80)
        return f.render_template(
            template,
            title="Edit Document",
            document=document,
            sources=sources_available(),
            form=DocumentEditForm(),  # Essentially an empty form for CSRF rendering.
            errors={},
            no_search=True,
        )

    # On POST, we need to process any changes encountered (unless we've canceled)
    if f.request.form.get("cancel"):
        return f.redirect(f.url_for("main.render_main"))

    # Upset all document attributes on the document (if any)
    document, doc_changed = update_doc_from_form(f.request, document)
    if doc_changed:
        document.updated = datetime.utcnow()
        document.save()

    return f.redirect(f.url_for("main.render_main"))


################################################################################
@bp.route("/add", methods=["POST", "GET"])
@login_required
def render_add_doc(template="main/add_edit.html") -> Response:
    """Create a *new* Document."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    # On GET, simply present the page to fill out...
    if f.request.method == "GET":
        log.info("*" * 80)
        return f.render_template(
            template,
            title="Add Document",
            form=DocumentEditForm(),
            sources=sources_available(),
            document=None,
            errors={},
            no_search=True,
        )

    # On POST, we need to create a new document and save it (unless we've canceled)
    if f.request.form.get("cancel"):
        return f.redirect(f.url_for("main.render_main"))

    document = new_doc_from_form(fl.current_user, f.request)
    document.save()

    log.info("*" * 80)
    return f.redirect(f.url_for("main.render_main"))
