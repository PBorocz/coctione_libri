from __future__ import annotations

import json
import logging as log

from flask import Request
from flask_login import UserMixin
from pydantic import BaseModel

from app import constants as c


class Cookies(BaseModel):

    """Cookies model."""

    # fmt: off
    sort_dir   : str | None = None  # This comes from comparing request with previous cookie
    sort_field : str | None = None  # This comes from the respective column header selected
    search     : str | None = None  # OPTIONAL/private field of search str IF THERE IS ONE!
    # fmt: on

    def attrs(self) -> list[str]:
        """Return the attributes (hide the pydantic dunder access)."""
        return [attr for attr in Cookies.__annotations__.keys() if not attr.startswith("_")]

    def as_cookie(self) -> str:
        """Return the instance as a string suitable for send back as a cookie."""
        return json.dumps(self.__dict__)

    def print_(self, label: str, space: bool = True) -> None:
        log.info(label)
        for attr in self.attrs():
            log.info(f"{attr:10} : {getattr(self, attr)}")
        if space:
            log.info("")

    def _get_sort_direction_from_header(self, headers: dict) -> tuple[str, str]:
        """Return possible new sort-direction & sort-field and direction based on current user-state and new request."""
        _debug = True
        if headers.get("Hx-Trigger", "").startswith("th_"):
            previous_sort_field, previous_sort_direction = self.sort_field, self.sort_dir
            if _debug:
                log.debug(f"{previous_sort_field=}, {previous_sort_direction=}")

            sort_field_requested: str = headers.get("Hx-Trigger").split("_", maxsplit=1)[1]
            if _debug:
                log.debug(f"{sort_field_requested=}")

            if sort_field_requested != previous_sort_field:
                # Sorting on a new field, default to ascending..
                sort_direction: str = c.SORT_ASCENDING
                if _debug:
                    log.debug("new field, default to ASC")
            else:
                # Sorting on the same field as before, flip the direction!
                sort_direction: str = (
                    c.SORT_DESCENDING if previous_sort_direction == c.SORT_ASCENDING else c.SORT_ASCENDING
                )
                if _debug:
                    log.debug(f"existing field!, now {sort_direction=}")

            log.debug(
                f"Overrode {previous_sort_field}|{previous_sort_direction} with "
                f"{sort_field_requested}|{sort_direction}"
            )
            return sort_direction, sort_field_requested
        else:
            return self.sort_dir, self.sort_field

    @classmethod
    def factory_from_user_view(cls, user: UserMixin, request: Request) -> Cookies:
        """Return a new user-state/query param instance from selected view."""
        instance = Cookies()

        # First, set from the selected view
        selected_view = user.get_default_view()
        for attr, value in selected_view:
            if attr not in ("name"):
                setattr(instance, attr, value)  # Easy as we're consistent with attr names..

        # Check: are any missing? If so, get from the inbound cookie from the user's last query.
        missing: list[str] = selected_view.get_missing_attr_values()
        if missing:
            log.error(f"Sorry, the following attrs are missing from the view: {missing}")

        return instance

    @classmethod
    def factory_from_cookie(cls, user: UserMixin, request: Request, update_sort: bool = False) -> Cookies:
        """Return a new user-state/query param instance from browser cookies."""
        instance = Cookies(**get_cookies(request))
        if update_sort:
            instance.sort_dir, instance.sort_field = instance._get_sort_direction_from_header(request.headers)
        return instance


################################################################################
# Utilities
################################################################################
def get_cookies(request: Request) -> dict:
    """Get and convert cookies from the request."""
    return dict(json.loads(request.cookies.get(c.COOKIE_NAME, "{}")))
