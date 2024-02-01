"""Core Application Routes."""
import logging as log
from io import BytesIO

from flask import current_app, send_file
from flask.wrappers import Response
from flask_login import login_required

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
    file_contents = document.file_.read()

    log.info(f"{len(file_contents)=}")

    return send_file(
        BytesIO(file_contents),
        download_name=f"{doc_id}.pdf",
        mimetype=document.file_.content_type,
    )


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

    form = forms.DocumentEditForm(
        source=document.source,
        title=document.title,
        notes=document.notes,
    )

    log.info("*" * 80)

    if form.validate_on_submit():
        if form.cancel.data:  # if cancel button is clicked, the form.cancel.data will be True
            return f.redirect(f.url_for("main.render_main"))

        save_doc = False
        if form.title.data and form.title.data.casefold() != document.title:
            # user = update_user(fl.current_user, "email", form.email.data)
            document.title = form.title.data
            save_doc = True
            msg = f"Title was updated to {form.title.data}"
            f.flash(msg, "is-primary")
            log.info(msg)

        if form.quality.data and form.quality.data.casefold() != document.quality:
            # user = update_user(fl.current_user, "email", form.email.data)
            document.quality = int(form.quality.data)
            save_doc = True
            msg = f"Quality was updated to a {form.quality.data}"
            f.flash(msg, "is-primary")
            log.info(msg)

        if save_doc:
            document.save()

        return f.redirect(f.url_for("main.render_main"))

    return f.render_template("edit.html", title="Edit Document", form=form)
