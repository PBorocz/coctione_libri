"""Core Application Routes."""
import logging as log
from datetime import datetime
from io import BytesIO

import flask_login as fl
from flask import make_response, send_file
from flask.wrappers import Response
from flask_login import login_required
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename

from app import constants as c
from app.blueprints.main import bp
from app.blueprints.main.operations import (
    delete_document,
    get_all_documents,
    get_search_documents,
    new_doc_from_form,
    remove_tag,
    update_doc_from_form,
)
from app.models.cookies import Cookies
from app.models.documents import Documents, sources_available


class EmptyForm(FlaskForm):
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
def render_main_sorted(template="main/partials/table.html") -> Response:
    """Re-render our main table based on a new sort field and/or direction."""
    import flask as f

    # Make sure we're coming in from an HTMX call..
    assert "Hx-Trigger" in f.request.headers
    trigger = f.request.headers.get("Hx-Trigger")
    log.info(f"Hx-Trigger:{trigger}")

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
def render_view_document(doc_id: str) -> Response:
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
@bp.route("/manage/<doc_id>", methods=["POST", "GET"])
@login_required
def render_manage_document(doc_id: str, template: str = "main/manage_document.html") -> Response:
    """Edit the attributes of an existing Document."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    document = Documents.objects(id=doc_id)[0]

    ################################################################################
    # On GET, simply present the document for editing..
    ################################################################################
    if f.request.method == "GET":
        log.info("*" * 80)
        return f.render_template(
            template,
            title="Edit Document",
            document=document,
            sources=sources_available(),
            form=EmptyForm(),  # Essentially an empty form for CSRF rendering.
            errors={},
            no_search=True,
        )

    ################################################################################
    # On POST, we determine which of the 3 buttons was pressed:
    ################################################################################
    # Easiest case, we're outa here!
    if f.request.form.get("cancel"):
        log.info("Cancel...")
        log.info("*" * 80)
        return f.redirect(f.url_for("main.render_main"))

    # Easier case, delete the document!
    elif f.request.form.get("delete"):
        log.info("Delete...")
        delete_document(document=document)
        log.info("*" * 80)
        return f.redirect(f.url_for("main.render_main"))

    # Normal case, upsert all document attributes on the document (if any)
    elif f.request.form.get("save"):
        log.info("Save...")
        document, doc_changed = update_doc_from_form(f.request, document)
        if doc_changed:
            document.updated = datetime.utcnow()
            document.save()
        log.info("*" * 80)
        return f.redirect(f.url_for("main.render_main"))
    else:
        raise RuntimeError("Sorry, invalid action received! (expected: cancel, save or delete)")


################################################################################
@bp.get("/edit/<doc_id>")
@login_required
def render_edit_document(doc_id: str) -> Response:
    """Display the Document edit panel."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")
    log.info(f"{doc_id=}")
    document = Documents.objects(id=doc_id)[0]

    # Default return values for BOTH GET and POST Calls
    return_ = {
        "form": EmptyForm(),  # Need for CSRF rendering,
        "sources": sources_available(),
        "no_search": True,
        "title": "Edit Document",
    }
    log.info("*" * 80)
    return_["document"] = document
    return f.render_template("main/edit_document.html", **return_)


################################################################################
@bp.post("/edit/<field>/<doc_id>")
@login_required
def edit_document_field(field: str, doc_id: str) -> Response:
    """Edit an particular attribute of an Document."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")
    log.info(f"{field=}")
    log.info(f"{doc_id=}")
    document = Documents.objects(id=doc_id)[0]

    status_error = {"color": "has-text-danger-dark", "icon": "fa-solid fa-circle-exclamation"}
    status_icon = {"color": "has-text-success", "icon": "fa-solid fa-circle-check"}

    # Default return values for BOTH GET and POST Calls
    return_ = {
        "form": EmptyForm(),  # Need for CSRF rendering,
        "sources": sources_available(),
    }

    match field:
        case "title":
            template = "main/partials/edit_form_title.html"
            document.title = f.request.form.get("title")
            document.save()

        case "notes":
            template = "main/partials/edit_form_notes.html"
            document.notes = f.request.form.get("notes")
            document.save()

        case "quality":
            print("quality")
            print(f"{f.request.form.get('quality')=}")
            template = "main/partials/edit_form_quality.html"
            document.quality = int(f.request.form.get("quality")) if f.request.form.get("quality") else None
            document.save()

        case "complexity":
            template = "main/partials/edit_form_complexity.html"
            document.complexity = int(f.request.form.get("complexity")) if f.request.form.get("complexity") else None
            document.save()

        case "tag":
            template = "main/partials/edit_form_tags.html"
            tag = f.request.form.get("tag")
            if tag.title() not in document.tags:
                document.tags.append(tag.title())
                document.save()
            else:
                status_icon = status_error

        case "file_":
            template = "main/partials/edit_form_file.html"
            file = f.request.files["file_"]
            filename = secure_filename(file.filename)  # Important! cleanse to remove bad characters!
            document.file_.replace(file, filename=filename, content_type="application/pdf")
            document.save()
            msg = (
                f"Saving a new file: {filename=}!"
                if document.file_
                else f"Replacing existing file {document.file_.filename=} with: {filename=}!"
            )
            log.debug(msg)
        case "url_":
            template = "main/partials/edit_form_url.html"
            document.url_ = f.request.form.get("url_")
            document.save()
        case "source":
            template = "main/partials/edit_form_source.html"
            document.source = f.request.form.get("source")
            document.save()
        case _:
            raise RuntimeError(f"Unrecognised {f.request.form.get('field')=}")

    return f.render_template(template, document=document, status_icon=status_icon, **return_)


################################################################################
@bp.route("/add", methods=["POST", "GET"])
@login_required
def render_add_doc(template="main/manage_document.html") -> Response:
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
            form=EmptyForm(),
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


################################################################################
@bp.route("/document/tag/<id_>/<tag>", methods=["DELETE"])
@login_required
def delete_tag_from_document(id_: str, tag: str, template="main/partials/edit_form_tags.html") -> Response:
    """Delete the specified tag on the specified document and return the form."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")
    log.info(f"Deleting {tag=} on document={id_}")
    document = remove_tag(id_, tag)
    log.info("*" * 80)
    status_icon = {"color": "has-text-success", "icon": "fa-solid fa-circle-check"}
    return f.render_template(template, document=document, status_icon=status_icon, form=EmptyForm())


################################################################################
# CURRENTLY UNUSED AS WE DON'T RENDER A DELETE BUTTON on the Main table.
################################################################################
# Used to be:
# {# Delete Icon #}
# <td class="has-text-centered"  style="vertical-align: middle;">
#   <a onclick="confirm_deletion(event)" href="/delete/{{ document.id }}">
#     <span class="icon is-small is-right is-size-6">
#       <i class="fa-regular fa-trash-can"></i>
#     </span>
#   </a>
# </td>
# and:
# {% block js_local %}
# <script type="text/javascript">
#   function confirm_deletion(event) {
#    event.preventDefault();
#    var urlToRedirect = event.currentTarget.getAttribute('href');
#    Swal.fire({
#      title: "Are you sure you want to delete this entry?",
#      text: "You will not be able to revert this!",
#      icon: "warning",
#      confirmButtonColor: "#d33",
#      confirmButtonText: "Yes",
#      showCancelButton: true,
#      cancelButtonColor: "#3085d6",
#      cancelButtonText: "Cancel",
#    }).then((result) => {
#      if (result.isConfirmed) {
#        window.location.href = urlToRedirect;
#      }
#    });
#  }
# </script>
# {% endblock %}
################################################################################
@bp.route("/delete/<doc_id>", methods=["GET"])
@login_required
def render_delete_doc(doc_id: str) -> Response:
    """Delete a document."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")
    delete_document(doc_id)
    log.info("*" * 80)
    return f.redirect(f.url_for("main.render_main"))
