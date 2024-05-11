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
            "complexity"            : True,
            "edit"                  : True,
            "last_cooked"           : True,
            "quality"               : True,
            "quality_by_complexity" : True,
            "source"                : True,
            "tags"                  : True,
            "title"                 : True,
        },
        "default": { # All other categories..
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

    l_fields = display_fields.get(category, display_fields["default"])
    assert field in l_fields
    return l_fields.get(field)
