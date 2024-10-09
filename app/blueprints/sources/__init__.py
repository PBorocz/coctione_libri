"""Source Management Blueprint."""

from flask import Blueprint

bp = Blueprint("sources", __name__, template_folder="sources")

import app.blueprints.sources.routes
