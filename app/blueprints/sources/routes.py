"""Source Management Routes."""

import flask as f
import flask_login as fl
from flask import request
from flask.wrappers import Response
from flask_login import login_required

from app.blueprints.sources import bp
from app.blueprints.sources.operations import get_all_sources, get_source_count, remove_source, update_source
from app.models import categories_available


################################################################################
@bp.route("/manage/sources", methods=["GET"])
@login_required
def manage_sources(template: str = "sources/sources.html") -> Response:
    """Render our source management page."""
    sort = request.args.get("sort", "source")
    order = request.args.get("order", "asc")
    sources = get_all_sources(fl.current_user, sort, order)
    sources = split_list(sources)  # Return a list of the sources "subsetted".
    return f.render_template(
        template,
        sources=sources,
        sort=sort,
        order=order,
        no_search=True,
        categories=categories_available(),
    )


################################################################################
@bp.get("/source/edit")
@login_required
def render_source_edit(template: str = "sources/hx/tr_edit.html") -> Response:
    """Return our source editor form for a single source table cell."""
    source = request.values.get("name")
    return f.render_template(template, source=source)


################################################################################
@bp.route("/source/delete", methods=["DELETE"])
@login_required
def delete_source() -> Response:
    """Delete the specified tag and return to the tag management page."""
    source = request.values.get("source")
    remove_source(fl.current_user, source)
    return "", 200


################################################################################
@bp.post("/source/update")
@login_required
def render_source_update(template: str = "sources/hx/tr.html") -> Response:
    """Process a potentially updated source value and display the entry with the new value."""
    action = request.values.get("action")
    source_new = request.form.get("source_new")
    source_old = request.form.get("source_old")

    if action == "save":
        source_return = source_new
        update_source(fl.current_user, source_old, source_new)
    elif action == "cancel":
        source_return = source_old

    # Irrespective of whether or not we did an update, we still need to redisplay the count as well:
    source_count = get_source_count(fl.current_user, source_return)

    return f.render_template(template, source=source_return, count=source_count)


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
