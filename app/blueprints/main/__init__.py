"""Main Page Blueprint."""
from flask import Blueprint

bp = Blueprint("main", __name__, template_folder="main")

import app.blueprints.main.routes
