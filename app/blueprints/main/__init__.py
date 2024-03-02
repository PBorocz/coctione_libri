"""Main Page Blueprint."""
import logging as log

from flask import Blueprint

bp = Blueprint("main", __name__, template_folder="main")

import app.blueprints.main.routes
from app.models import Category


def render_display_column(category: Category, field: str) -> bool:
    # fmt: off
    display_fields = {
        Category.COOKING_RECIPES: {
            "complexity"  : True,
            "edit"        : True,
            "last_cooked" : True,
            "quality"     : True,
            "source"      : True,
            "tags"        : True,
            "title"       : True,
        },
        Category.COOKING_GENERAL: {
            "complexity"  : False,
            "edit"        : True,
            "last_cooked" : False,
            "quality"     : False,
            "source"      : True,
            "tags"        : True,
            "title"       : True,
        },
    }
    # fmt: on

    # (no surprises...)
    assert category in display_fields
    assert field in display_fields.get(category)

    return display_fields.get(category).get(field)
