"""Statistics Routes."""

import flask as f
import flask_login as fl
from flask.wrappers import Response
from flask_login import login_required

from app.blueprints.stats import bp
from app.blueprints.stats.operations import create_bar_chart, get_all_sources
from app.blueprints.tags.operations import get_all_tags
from app.models import categories_available


################################################################################
@bp.route("/statistics", methods=["GET"])
@login_required
def statistics(template: str = "stats/stats.html") -> Response:
    """Render our statistics page."""
    # Get the figure associated with the distribution/count of TAGS:
    config = {
        "data_name": "tag",
        "title": "Tag Popularity",
    }

    fn_tag_chart = create_bar_chart(get_all_tags(fl.current_user), config)

    # Get the figure associated with the distribution/count of SOURCES:
    config = {
        "data_name": "source",
        "title": "Source Popularity",
    }
    fn_source_chart = create_bar_chart(get_all_sources(fl.current_user), config)

    return f.render_template(
        template,
        fn_tag_chart=fn_tag_chart,
        fn_source_chart=fn_source_chart,
        categories=categories_available(),
    )
