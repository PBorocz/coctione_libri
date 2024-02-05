"""Core Application Routes."""
import logging as log
from io import BytesIO

import flask_login as fl
from flask import current_app, send_file
from flask.wrappers import Response
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.blueprints.main import bp, forms
from app.blueprints.main.operations import get_all_documents, get_search_documents
from app.models.documents import Documents


################################################################################
@bp.get("/")
@login_required
def render_main() -> Response:
    """Render our main page on a full refresh.

    Get our query & display parameters from:
    - Cookies
    - If not available, selected view (for now, the default one).
    """
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    documents = get_all_documents()

    # Set caption based on environment
    watermark = "Development" if current_app.config["development"] else ""

    log.info("*" * 80)

    return f.render_template(
        "main.html",
        documents=documents,
        watermark=watermark,
    )


################################################################################
@bp.post("/search")
@login_required
def render_search() -> Response:
    """Render just the results table based on a *SEARCH* request."""
    import flask as f

    search_term_s = f.request.form["search"]

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /search ['{search_term_s}']")

    if not search_term_s or search_term_s == "*":
        # Sometimes a "search" is not a "search" after all!
        documents = get_all_documents()
    else:
        documents = get_search_documents(search_term_s)

    log.info("*" * 80)
    return f.render_template("main_table.htmx", documents=documents, search=search_term_s)


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
@bp.get("/delete/<doc_id>")
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
    return f.render_template("document_edit.html", title="Edit Document", form=form, no_search=True)


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

    # Get the list of source choices from the DB..
    form.source.choices = Documents().source_choices()
    if form.source.choices:
        form.source.default = form.source.choices[0][0]

    # Is the form we recieved on a POST valid?
    if form.validate_on_submit():
        if form.cancel.data:  # if cancel button is clicked, the form.cancel.data will be True
            return f.redirect(f.url_for("main.render_main"))

        # First handle all simple attributes of the document:
        document = add_doc_from_form(form)

        # Now let's see if we got a new file to upload along with it.
        if file := f.request.files["file_"]:
            filename = secure_filename(file.filename)  # Important! cleanse to remove bad characters!
            log.info(f"Saving a new file...{filename=}!")
            document.file_.replace(file, content_type="application/pdf")
            document.save()

        return f.redirect(f.url_for("main.render_main"))

    log.info("*" * 80)
    return f.render_template("document_add.html", title="Add Document", form=form, no_search=True)


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
        return document, True
    return document, False
