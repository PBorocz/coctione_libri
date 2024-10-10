"""Tag and Source Administration Routes."""

import flask as f
import flask_login as fl
from flask import request
from flask.wrappers import Response
from flask_login import login_required

from app.blueprints.admin import bp
from app.blueprints.admin import operations as op
from app.models import categories_available

TAG = "tag"
SOURCE = "source"
ENTITIES = (TAG, SOURCE)


################################################################################
@bp.get("/admin/<string:entity>")
@login_required
def manage_st(entity: str, template: str = "admin/st.html") -> Response:
    """Render our source/tag primary display page."""
    if entity not in ENTITIES:
        f.abort(404)
    sort = request.args.get("sort", entity)
    order = request.args.get("order", "asc")

    # Query all the current values of the respective entity..
    method_get_all = op.get_all_tags if entity == TAG else op.get_all_sources
    entities = method_get_all(fl.current_user, sort, order)

    return f.render_template(
        template,
        order=order,
        entity=entity,
        entity_display=f"{entity.title()}s",
        entities_split=split_list(entities),  # Return a sub-setted list for multi-column display
        no_search=True,
        categories=categories_available(),
    )


# ################################################################################
@bp.get("/admin/<string:entity>/edit")
@login_required
def render_st_edit(entity: str, template: str = "admin/hx/tr_edit.html") -> Response:
    """Return our editor form for a single tag table cell."""
    if entity not in ENTITIES:
        f.abort(404)
    entity_value = request.values.get("name")
    return f.render_template(template, entity=entity, entity_value=entity_value)


################################################################################
@bp.post("/admin/<string:entity>/update")
@login_required
def render_st_update(entity: str, template: str = "admin/hx/tr.html") -> Response:
    """Process a potentially updated tag value and display the entry with the new value."""
    if entity not in ENTITIES:
        f.abort(404)
    action = request.values.get("action")
    entity_new = request.form.get("entity_new")
    entity_old = request.form.get("entity_old")

    if action == "save":
        entity_return = entity_new
        method_update = op.update_tag if entity == TAG else op.update_source
        method_update(fl.current_user, entity_old, entity_new)
    elif action == "cancel":
        entity_return = entity_old

    # Irrespective of whether or not we did an update, we still need to redisplay the count as well:
    method_count = op.get_tag_count if entity == TAG else op.get_source_count
    entity_count = method_count(fl.current_user, entity_return)

    return f.render_template(template, entity=entity, entity_value=entity_return, count=entity_count)


################################################################################
@bp.route("/tag/<string:entity>/delete", methods=["DELETE"])
@login_required
def delete_st(entity: str) -> Response:
    """Delete the specified tag and return to the tag management page."""
    if entity not in ENTITIES:
        f.abort(404)
    entity_value = request.values.get("name")
    method_remove = op.remove_tag if entity == TAG else op.remove_source
    method_remove(fl.current_user, entity_value)
    return "", 200


################################################################################
# Utility methods
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
