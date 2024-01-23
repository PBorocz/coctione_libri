"""Core Application Routes."""
import logging as log
from io import BytesIO

import flask_login as fl
from flask import send_file
from flask.wrappers import Response

from app.blueprints.main import bp
from app.blueprints.main.render import render_main
from app.models import Documents


################################################################################
@bp.get("/")
@fl.login_required
def main() -> Response:
    """Render our main page on a full refresh.

    Get our query & display parameters from:
    - Cookies
    - If not available, selected view (for now, the default one).
    """
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    results = render_main()

    log.info("*" * 80)

    return f.render_template("main.html", **results)


################################################################################
@bp.get("/view/<doc_id>")
@fl.login_required
def main_view_pdf(doc_id: str) -> Response:
    """Render a pdf."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")

    doc = Documents.objects(id=doc_id)[0]
    contents = doc.file_.read()

    log.info(f"{len(contents)=}")

    return send_file(
        BytesIO(contents),
        download_name=f"{doc_id}.pdf",
        mimetype=doc.file_.content_type,
    )


################################################################################
@bp.post("/search")
@fl.login_required
def main_post_search() -> Response:
    """Render the results table based on a *SEARCH* request."""
    import flask as f

    search_term = f.request.form["search"]

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /search ['{search_term}']")

    results = render_main(search=search_term)

    log.info("*" * 80)
    return f.render_template("main/table.htmx", **results)
