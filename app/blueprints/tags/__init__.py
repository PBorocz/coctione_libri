"""Tag Management Blueprint."""
from flask import Blueprint

bp = Blueprint("tags", __name__, template_folder="tags")

import app.blueprints.tags.routes
