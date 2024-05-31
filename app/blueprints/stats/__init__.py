"""Statistics Display Blueprint."""

from flask import Blueprint

bp = Blueprint("stats", __name__, template_folder="stats")

import app.blueprints.stats.routes
