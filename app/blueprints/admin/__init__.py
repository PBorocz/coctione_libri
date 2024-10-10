"""Administration Blueprint."""

from flask import Blueprint

bp = Blueprint("admin", __name__, template_folder="admin")

import app.blueprints.admin.routes
