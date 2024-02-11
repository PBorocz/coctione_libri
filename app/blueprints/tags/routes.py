"""Tag Management Routes."""
import logging as log

from flask.wrappers import Response
from flask_login import login_required

from app.blueprints.tags import bp
from app.blueprints.tags.operations import get_all_tags, get_tag_count, remove_tag, update_tag


################################################################################
@bp.route("/tags", methods=["GET"])
@login_required
def manage_tags() -> Response:
    """Render our tag management page."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")
    tags = get_all_tags()
    log.info("*" * 80)
    return f.render_template("tags/tags.html", tags=tags, no_search=True)


################################################################################
@bp.get("/tag/edit")
@login_required
def render_tag_edit() -> Response:
    """Return our tag editor form for a single tag table cell."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")
    tag = f.request.values.get("name")
    log.info(f"{tag=}")
    log.info("*" * 80)
    return f.render_template("tags/partials/edit.html", tag=tag)


################################################################################
@bp.route("/tag/delete", methods=["DELETE"])
@login_required
def delete_tag() -> Response:
    """Delete the specified tag and return to the tag management page."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")
    tag = f.request.values.get("name")
    log.info(f"To be deleted: {tag=}")
    remove_tag(tag)
    log.info("*" * 80)
    return "", 200


################################################################################
@bp.post("/tag/update")
@login_required
def render_tag_update() -> Response:
    """Process a potentially updated tag value and display the entry with the new value."""
    import flask as f

    log.info("")
    log.info("*" * 80)
    log.info(f"{f.request.method.upper()} /")
    action = f.request.values.get("action")
    tag_new = f.request.form.get("tag_new")
    tag_old = f.request.form.get("tag_old")
    log.info(f"{action=}")

    if action == "save":
        tag_return = tag_new
        update_tag(tag_old, tag_new)
    elif action == "cancel":
        tag_return = tag_old

    log.info("*" * 80)

    # Irrespective of whether or not we did an update, we still need to redisplay the count as well:
    tag_count = get_tag_count(tag_return)

    return f.render_template("tags/partials/tag_row.html", tag=tag_return, count=tag_count)
