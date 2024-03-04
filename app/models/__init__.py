"""."""
from __future__ import annotations

from enum import IntEnum, StrEnum

from flask.wrappers import Request  # Typing


################################################################################
# Enumerators
################################################################################
class Category(StrEnum):
    # Extra attributes over and above implicit "value":
    collection_root: str  # Eg. recipes in "recipes_<user_id>"

    def __new__(cls, display: str, collection_root: str | None = None) -> Category:
        obj = str.__new__(cls, display)
        obj.collection_root = collection_root if collection_root else display.lower()
        return obj

    COOKING_RECIPES = "Recipes"
    COOKING_SKILLS = "Cooking-Skills"
    COOKING_PRODUCTS = "Cooking-Products"


def categories() -> list[str]:
    return [category._value_ for category in Category]


class Rating(IntEnum):
    ZER = 0
    ONE = 1
    TWO = 2
    THR = 3
    FOR = 4
    FIV = 5

    def __str__(self):
        return "★" * self.value  # "•"


################################################################################
# Miscellaneous/utility classes
################################################################################
class Sort:

    """Encapsulate all semantics controlling sorting on from/main page."""

    def __init__(self):
        self.by = "title"  # Default values...
        self.order = "asc"  # "

    def is_ascending(self) -> bool:
        return self.order == "asc"

    def __str__(self):
        arrow = "↑" if self.order == "asc" else "↓"
        return f"Sort: by={self.by} order={arrow}"

    @classmethod
    def factory(cls, request: Request):
        instance = cls()
        if request.values.get("sort_by"):
            instance.by = request.values.get("sort_by")
        if request.values.get("sort_order"):
            instance.order = request.values.get("sort_order")
        return instance
