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


def categories() -> list[Category]:
    return list(Category)


def categories_available() -> list[str]:
    return [category._value_ for category in Category]


class RatingQuality(IntEnum):
    ZER = 0
    ONE = 1
    TWO = 2
    THR = 3
    FOR = 4
    FIV = 5

    # If we want to have a repeating character instead of the number itself:
    # def __str__(self):
    #     return "★" * self.value


class RatingComplexity(IntEnum):
    ZER = 0
    ONE = 1
    TWO = 2
    THR = 3
    FOR = 4
    FIV = 5

    # def __str__(self):
    #     return "⚙" * self.value


################################################################################
# Miscellaneous/utility classes
################################################################################
class Sort:
    """Encapsulate all semantics controlling sorting on from/main page."""

    def __init__(self):
        self.by: str = "title"
        self.order: str = "asc"

    def is_ascending(self) -> bool:
        return self.order == "asc"

    def __str__(self):
        arrow = "↑" if self.order == "asc" else "↓"
        return f"Sort: by={self.by} order={arrow}"

    @classmethod
    def factory_from_request(cls, request: Request):
        instance = cls()
        instance.by = request.values.get("sort_by", instance.by)
        instance.order = request.values.get("sort_order", instance.order)
        return instance

    @classmethod
    def factory_from_user(cls, user):
        instance = cls()  # Will set defaults if nothing on the user record..
        if user.payload.state_last_sort:
            instance.by = user.payload.state_last_sort.get("by", instance.by)
            instance.order = user.payload.state_last_sort.get("order", instance.order)
        return instance
