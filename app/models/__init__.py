"""."""
from flask.wrappers import Request  # Typing


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
