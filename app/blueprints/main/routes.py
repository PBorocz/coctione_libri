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
    delete_document,
    get_all_documents,
    get_search_documents,
    new_doc_from_form,
    remove_tag,
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
@bp.route("/edit/<doc_id>", methods=["POST", "GET"])
@login_required
def render_edit_doc(doc_id: str, template: str = "main/add_edit.html") -> Response:
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
            form=DocumentEditForm(),  # Essentially an empty form for CSRF rendering.
            errors={},
            no_search=True,
        )

    ################################################################################
    # On POST, we determine which of the 3 buttons was pressed:
    ################################################################################
    if f.request.form.get("cancel"):
        # Easiest case, we're outa here!
        log.info("Cancel...")
        log.info("*" * 80)
        return f.redirect(f.url_for("main.render_main"))

    elif f.request.form.get("delete"):
        # Easier case, delete the document!
        log.info("Delete...")
        delete_document(document=document)
        log.info("*" * 80)
        return f.redirect(f.url_for("main.render_main"))

    elif f.request.form.get("save"):
        # Normal case, upsert all document attributes on the document (if any)
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


################################################################################
@bp.route("/document/tag", methods=["DELETE"])
@login_required
def delete_tag(template="main/partials/tr.html") -> Response:
    """Delete the specified tag on the specified document and return the row."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")
    tag = f.request.values.get("name")
    id_ = f.request.values.get("id")
    log.info(f"Deleting {tag=} on document={id_}")
    document = remove_tag(id_, tag)
    log.info("*" * 80)
    return f.render_template(template, document=document)


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
