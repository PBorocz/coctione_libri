"""User-Management Blueprint."""
from flask import Blueprint

bp = Blueprint("auth", __name__)

import app.blueprints.auth.handlers
