"""Main Page Blueprint."""
from flask import Blueprint

bp = Blueprint("main", __name__)

import app.blueprints.main.routes
