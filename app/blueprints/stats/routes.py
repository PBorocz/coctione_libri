"""Statistics Routes."""

import flask as f
import flask_login as fl
from flask.wrappers import Response
from flask_login import login_required

from app.blueprints.stats import bp
from app.blueprints.stats.operations import create_bar_chart, get_all_reviews, get_all_sources, top_files
from app.models import categories_available
from app.models.documents import Documents


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

    fn_tag_chart = create_bar_chart(Documents.tag_counts(fl.current_user), config)

    # Get the figure associated with the distribution/count of SOURCES:
    config = {
        "data_name": "source",
        "title": "Source Popularity",
    }
    fn_source_chart = create_bar_chart(Documents.source_counts(fl.current_user), config)

    # Get the figure associated with the distribution/count of REVIEWS:
    d_reviews = get_all_reviews(fl.current_user)
    config = {
        "data_name": "review",
        "title": "Quality Reviews",
        "render_top_n": len(d_reviews),
    }
    fn_review_chart = create_bar_chart(d_reviews, config)

    return f.render_template(
        template,
        fn_tag_chart=fn_tag_chart,
        fn_source_chart=fn_source_chart,
        fn_review_chart=fn_review_chart,
        top_files=top_files(fl.current_user),
        categories=categories_available(),
    )
