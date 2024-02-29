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

    @classmethod
    def factory(cls, user: UserMixin, request: Request) -> Cookies:
        """Return a new user-state/query param instance from browser cookies."""
        return Cookies(**get_cookies(request))


################################################################################
# Utilities
################################################################################
def get_cookies(request: Request) -> dict:
    """Get and convert cookies from the request."""
    return dict(json.loads(request.cookies.get(c.COOKIE_NAME, "{}")))
