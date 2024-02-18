"""Core Application Routes."""
import logging as log
from datetime import datetime
from io import BytesIO

import flask_login as fl
from flask import make_response, send_file
from flask.wrappers import Response
from flask_login import login_required
from werkzeug.utils import secure_filename

from app import constants as c
from app.blueprints.main import bp, forms
from app.blueprints.main.operations import get_all_documents, get_search_documents
from app.models.cookies import Cookies
from app.models.documents import Documents


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
def render_edit_doc(doc_id: str) -> Response:
    """Edit the attributes of an existing Document."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    # Get the document we're going to be editing...
    document = Documents.objects(id=doc_id)[0]

    form_complexity = 0 if document.complexity is None else document.complexity
    form_quality = 0 if document.quality is None else document.quality

    form = forms.DocumentEditForm(
        source=document.source,
        title=document.title,
        quality=form_quality,
        complexity=form_complexity,
        url_=document.url_,
        notes=document.notes,
        tags=document.tags,
    )

    # Get the list of source choices from the DB..
    form.source.choices = Documents().source_choices()
    if form.source.choices:
        form.source.default = form.source.choices[0][0]

    # Pass the filename into the form field as well for display
    form.file_.filename = document.file_.filename

    # Is the form we recieved on a POST valid?
    if form.validate_on_submit():
        if form.cancel.data:  # if cancel button is clicked, the form.cancel.data will be True
            return f.redirect(f.url_for("main.render_main"))

        # First handle all simple attributes of the document:
        document, save = update_doc_from_form(form, document)

        # Now, let's see if we got a new file to upload
        if file := f.request.files["file_"]:
            filename = secure_filename(file.filename)  # Important! cleanse to remove bad characters!
            log.info(f"Saving a new file...{filename=}!")
            document.file_.replace(file, content_type="application/pdf")
            save = True

        if save:
            document.save()

        return f.redirect(f.url_for("main.render_main"))

    log.info("*" * 80)
    return f.render_template("main/add_edit.html", title="Edit Document", form=form, no_search=True)


################################################################################
@bp.route("/add", methods=["POST", "GET"])
@login_required
def render_add_doc() -> Response:
    """Create a *new* Document."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    form = forms.DocumentEditForm()

    if form.cancel.data:  # If cancel button is clicked, the form.cancel.data will be True and we're done!
        return f.redirect(f.url_for("main.render_main"))

    # Get the list of source choices from the DB
    form.source.choices = Documents().source_choices()
    if form.source.choices:
        form.source.default = form.source.choices[0][0]

    # Is the form we recieved on a POST valid?
    if form.validate_on_submit():
        # First handle all simple attributes of the document:
        document = add_doc_from_form(form)

        # Now let's see if we got a new file to upload along with it (we may not)
        if file := f.request.files["file_"]:
            filename = secure_filename(file.filename)  # Important! cleanse to remove bad characters!
            log.info(f"Saving a new file...{filename=}!")
            document.file_.replace(file, content_type="application/pdf")
            document.save()

        return f.redirect(f.url_for("main.render_main"))

    log.info("*" * 80)
    return f.render_template("main/add_edit.html", title="Add Document", form=form, no_search=True)


def add_doc_from_form(form) -> tuple[Documents, bool]:
    """Add (and return) a *new* document from the respective form."""
    # fmt: off
    document = Documents(
        user       = fl.current_user,  # Required
        title      = form.title.data,  # "
        source     = form.source.data          if form.source     else None,
        url_       = form.url_.data            if form.url_       else None,
        notes      = form.notes.data           if form.notes      else None,
        quality    = int(form.quality.data)    if form.quality    else None,
        complexity = int(form.complexity.data) if form.complexity else None,
    )
    # fmt: on
    document.save()

    return document


def update_doc_from_form(form, document: Documents) -> tuple[Documents, bool]:
    """Update the document attributes from the respective form, returning the doc if changed."""
    form_document_attrs = (
        (None, "title"),
        (None, "notes"),
        (None, "source"),
        (None, "url_"),
        (None, "tags"),
        ("to_int", "quality"),
        ("to_int", "complexity"),
    )

    save_doc = False
    for conversion, attr in form_document_attrs:
        curr_value = getattr(document, attr)  # Value in the current document, ie. in db.
        form_value = getattr(form, attr).data  # Value coming back from the form.
        if conversion == "to_int":
            form_value = int(form_value)

        ################################################################################
        # Case 1: Have both a form_value and current document value
        #         -> Check for match and update if necessary
        ################################################################################
        if form_value and curr_value:
            if form_value != curr_value:
                save_doc = True
                setattr(document, attr, form_value)
                log.info(f"{attr=} was updated to {form_value} (from {curr_value})")

        ################################################################################
        # Case 2: Have a new form_value but not current document value
        #         -> Update document with new value.
        ################################################################################
        elif form_value and not curr_value:
            save_doc = True
            setattr(document, attr, form_value)
            log.info(f"{attr=} was newly set to {form_value}")

        ################################################################################
        # Case 3: Don't have a new form_value but do have a current document value
        #         -> Update document value to None.
        ################################################################################
        elif not form_value and curr_value:
            save_doc = True
            setattr(document, attr, None)
            log.info(f"{attr=} was cleared")

        # Case 4: Don't have a new form_value and don't have a current document value
        #         -> Do Nothing!
        else:
            assert not form_value and not curr_value, f"Sorry, unhandled case: {form_value=} {curr_value=}"

    if save_doc:
        document.updated = datetime.utcnow()
        return document, True
    return document, False
