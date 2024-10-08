"""Tag Management Routes."""

import flask as f
import flask_login as fl
from flask import request
from flask.wrappers import Response
from flask_login import login_required

from app.blueprints.tags import bp
from app.blueprints.tags.operations import get_all_tags, get_tag_count, remove_tag, update_tag
from app.models import categories_available


################################################################################
@bp.route("/tags", methods=["GET"])
@login_required
def manage_tags(template: str = "tags/tags.html") -> Response:
    """Render our tag management page."""
    sort = request.args.get("sort", "tag")
    order = request.args.get("order", "asc")
    tags = get_all_tags(fl.current_user, sort, order)
    tags = split_list(tags)  # Return a list of the tags "subsetted".
    return f.render_template(
        template,
        tags=tags,
        sort=sort,
        order=order,
        no_search=True,
        categories=categories_available(),
    )


################################################################################
@bp.get("/tag/edit")
@login_required
def render_tag_edit(template: str = "tags/hx/tr_edit.html") -> Response:
    """Return our tag editor form for a single tag table cell."""
    tag = request.values.get("name")
    return f.render_template(template, tag=tag)


################################################################################
@bp.route("/tag/delete", methods=["DELETE"])
@login_required
def delete_tag() -> Response:
    """Delete the specified tag and return to the tag management page."""
    tag = request.values.get("name")
    remove_tag(fl.current_user, tag)
    return "", 200


################################################################################
@bp.post("/tag/update")
@login_required
def render_tag_update(template: str = "tags/hx/tr.html") -> Response:
    """Process a potentially updated tag value and display the entry with the new value."""
    action = request.values.get("action")
    tag_new = request.form.get("tag_new")
    tag_old = request.form.get("tag_old")

    if action == "save":
        tag_return = tag_new
        update_tag(fl.current_user, tag_old, tag_new)
    elif action == "cancel":
        tag_return = tag_old

    # Irrespective of whether or not we did an update, we still need to redisplay the count as well:
    tag_count = get_tag_count(fl.current_user, tag_return)

    return f.render_template(template, tag=tag_return, count=tag_count)


################################################################################
def split_list(input_list, split=3):
    """Split the input list to the specified number of parts."""
    # Calculate the base size of each part and how many have one extra item.
    size_base = len(input_list) // split
    extra_items = len(input_list) % split
    sublists = []
    start = 0
    for i in range(split):
        end = start + size_base + (1 if i < extra_items else 0)
        sublists.append(input_list[start:end])
        start = end
    return sublists
