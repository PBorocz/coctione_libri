"""Base application document model (in relational form)."""

import datetime as dt
import hashlib
from zoneinfo import ZoneInfo

import humanize
from peewee import CharField, Check, DateTimeField, ForeignKeyField, IntegerField, Model

from app.models import Category, RatingComplexity, RatingQuality
from app.models.user_rdb import User


class Document(Model):
    # fmt: off
    id           = IntegerField(primary_key=True, help_text="DB auto increment id")
    title        = CharField(help_text="Document title")
    category     = CharField(help_text="Document category",choices=[(c.value, c.name) for c in Category])
    created      = DateTimeField(default=dt.datetime.now(), help_text="Datetime first saved.")

    public_id    = CharField(null=True, help_text="Public slug/sqid")
    updated      = DateTimeField(null=True, help_text="Datetime last updated.")
    filesize     = IntegerField(null=True)
    mimetype     = CharField(default="application/pdf")
    source       = CharField(null=True)
    url          = CharField(null=True)
    tags         = CharField(null=True) # "|" delimited list of lower-case tags

    # Recipe category-specific fields
    dates_cooked = CharField(null=True) # "|" delimited list of dates in YYYY-MM-DD.
    quality      = IntegerField(null=True, constraints=[Check("0 <= quality <= 5")])
    complexity   = IntegerField(null=True, constraints=[Check("0 <= quality <= 5")])

    user         = ForeignKeyField(User, backref="documents")
    # fmt: on

    def save(self, *args, **kwargs) -> int:
        """Override save method to handle updated and public_id attributes."""
        self.updated = dt.datetime.now() if self._pk is not None else None
        return super().save(*args, **kwargs)

    ################################################################################
    # Tag attribute management
    ################################################################################
    @property
    def tags_split(self) -> list[str]:
        if not self.tags:
            return []
        tags = set()
        for tag in self.tags.split("|"):
            tags.add(tag)
        return sorted(tags)

    def tags_add(self, tag: str):
        _list_add(self, "tags", self.tags_split, tag)

    def tags_remove(self, tag: str):
        _list_remove(self, "tags", self.tags_split, tag)

    ################################################################################
    # Dates_Cooked attribute management
    ################################################################################
    @property
    def dates_cooked_split(self) -> list[str]:
        """Return dates)cooked as a sorted list."""
        if not self.dates_cooked:
            return []
        dates_cooked = set()
        for s_date in self.dates_cooked.split("|"):
            dates_cooked.add(s_date)
        return sorted(dates_cooked)

    def dates_cooked_add(self, date_: dt):
        _list_add(self, "dates_cooked", self.dates_cooked_split, date_.strftime("%Y-%m-%d"))

    def dates_cooked_remove(self, date_: dt):
        _list_remove(self, "dates_cooked", self.dates_cooked_split, date_.strftime("%Y-%m-%d"))

    ################################################################################
    # Extended properties (all read-only)
    ################################################################################
    @property
    def quality_enum(self) -> RatingQuality | None:
        """Return the uptyped quality field as "Rating" instead of int."""
        return RatingQuality(self.quality) if self.quality else None

    @property
    def complexity_enum(self) -> RatingComplexity | None:
        """Return the uptyped complexity field as "Rating" instead of int."""
        return RatingComplexity(self.complexity) if self.complexity else None

    @property
    def quality_by_complexity(self) -> float | None:
        """Return the bang for buck, ie. quality / complexity."""
        try:
            return f"{self.quality / self.complexity:.2f}"
        except TypeError:
            return None

    @property
    def cooked(self) -> int:
        """Return number of times we've cooked this."""
        return len(self.dates_cooked)

    @property
    def created_display(self) -> str:
        """Return created attr in local and nicely formatted."""
        return dt_as_local(self.created)

    @property
    def tags_display(self) -> list[str]:
        """Return tags as a nicely formatted, sorted list."""
        return sorted([tag.title() for tag in self.tags_split])

    @property
    def dates_cooked_display(self) -> list[(str, str)]:
        """Return a list of tuples of dates last cooked, eg. [("2024-02-01", "Monday, February 2nd 2024")...]."""
        return [(lc_.strftime("%Y-%m-%d"), dt_as_date(lc_)) for lc_ in self.dates_cooked_split]

    @property
    def filesize_display(self) -> str | None:
        """Return the filesize of the current document in human-readable format (if file_ defined)."""
        if self.filesize:
            return humanize.naturalsize(self.filesize)
        return ""

    @property
    def updated_display(self) -> str:
        """Return updated attr in local and nicely formatted if available."""
        return dt_as_local(self.updated) if self.updated else ""

    @property
    def times_cooked(self) -> str | None:
        """Return the number of times we've cooked this."""
        if self.dates_cooked:
            return str(len(self.dates_cooked_as_list()))
        return None


################################################################################
# Utilities
################################################################################
def _list_add(document: Document, attr: str, existing: list[str], value: str) -> Document:
    value_ = value.strip().lower()
    if value_ not in existing:
        existing.append(value_)
    setattr(document, attr, "|".join(existing))
    return document


def _list_remove(document: Document, attr: str, existing: list[str], value: str) -> Document:
    value_ = value.strip().lower()
    if value_ in existing:
        existing.remove(value_)
    setattr(document, attr, "|".join(existing))
    return document


def sources_available(user: User) -> list[str]:
    """Return the current list of sources across all documents as a Choice list."""
    docs = Document.select(Document.source).where(Document.user == user)
    return sorted({doc.source for doc in docs if doc.source})


def tags_available(user: User) -> list[str]:
    """Return a sorted list of all current tags (ie. those attached to documents)."""
    tags = set()
    for document in Document.select(Document.tags).where(Document.user == user):
        for tag in document.tags:
            tags.add(tag)
    return sorted(tags)


def dt_as_local(datetime_naive: dt.datetime, timezone_: str = "America/Los_Angeles", date_only: bool = False) -> str:
    """Return naive datetime as a nicely formatted local date-time (`Wednesday, February 21st 02:15pm 2024`)."""
    datetime_utc = datetime_naive.replace(tzinfo=dt.UTC)
    datetime_local = datetime_utc.astimezone(ZoneInfo(timezone_))

    day = int(datetime_local.strftime("%d"))
    suffix = ["th", "st", "nd", "rd", "th"][min(day % 10, 4)]
    if 11 <= (day % 100) <= 13:  # noqa: PLR2004
        suffix = "th"

    strftime_ = f"%A, %B {day}{suffix} %Y" if date_only else f"%A, %B {day}{suffix} %I:%M%p %Y"
    return datetime_local.strftime(strftime_)


def dt_as_date(datetime_naive: dt.datetime) -> str:
    """Return naive datetime as a nicely formatted date (`Wednesday, February 21st 2024`)."""
    datetime_utc = datetime_naive.replace(tzinfo=dt.UTC)

    day = int(datetime_utc.strftime("%d"))
    suffix = ["th", "st", "nd", "rd", "th"][min(day % 10, 4)]
    if 11 <= (day % 100) <= 13:  # noqa: PLR2004
        suffix = "th"

    return datetime_utc.strftime(f"%A, %B {day}{suffix} %Y")
