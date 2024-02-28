"""Tag Management Routes."""
import logging as log

import flask as f
import flask_login as fl
from flask.wrappers import Response
from flask_login import login_required

from app.blueprints.tags import bp
from app.blueprints.tags.operations import get_all_tags, get_tag_count, remove_tag, update_tag


################################################################################
@bp.route("/tags", methods=["GET"])
@login_required
def manage_tags(template: str = "tags/tags.html") -> Response:
    """Render our tag management page."""
    sort = f.request.args.get("sort", "tag")
    order = f.request.args.get("order", "asc")
    tags = get_all_tags(fl.current_user, sort, order)
    return f.render_template(template, tags=tags, sort=sort, order=order, no_search=True)


################################################################################
@bp.get("/tag/edit")
@login_required
def render_tag_edit(template: str = "tags/partials/edit.html") -> Response:
    """Return our tag editor form for a single tag table cell."""
    tag = f.request.values.get("name")
    return f.render_template(template, tag=tag)


################################################################################
@bp.route("/tag/delete", methods=["DELETE"])
@login_required
def delete_tag() -> Response:
    """Delete the specified tag and return to the tag management page."""
    tag = f.request.values.get("name")
    log.info(f"Delete ENTIRE {tag=}")
    remove_tag(fl.current_user, tag)
    return "", 200


################################################################################
@bp.post("/tag/update")
@login_required
def render_tag_update(template: str = "tags/partials/tr.html") -> Response:
    """Process a potentially updated tag value and display the entry with the new value."""
    action = f.request.values.get("action")
    tag_new = f.request.form.get("tag_new")
    tag_old = f.request.form.get("tag_old")

    if action == "save":
        tag_return = tag_new
        update_tag(fl.current_user, tag_old, tag_new)
    elif action == "cancel":
        tag_return = tag_old

    # Irrespective of whether or not we did an update, we still need to redisplay the count as well:
    tag_count = get_tag_count(fl.current_user, tag_return)

    return f.render_template(template, tag=tag_return, count=tag_count)
