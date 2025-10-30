"""Base application document model (in relational form)."""

import datetime as dt
import json
import re
import unicodedata
from zoneinfo import ZoneInfo

import humanize
import sqids
from peewee import CharField, Check, DateTimeField, ForeignKeyField, Model, SmallIntegerField, TextField

from app.models import Category, RatingComplexity, RatingQuality
from app.models.user_rdb import User


class ListField(TextField):
    def db_value(self, value):
        if not value:
            return "[]"
        # Convert to lower, remove duplicates, and sort
        unique_values = sorted(dict.fromkeys(str(item).lower() for item in value))
        return json.dumps(unique_values)

    def python_value(self, value):
        return json.loads(value) if value else []


class DateTimeListField(TextField):
    def db_value(self, value):
        if not value:
            return "[]"
        # Convert remove duplicates, and sort
        sorted_values = sorted(dict.fromkeys(item for item in value))
        return json.dumps([d.isoformat() for d in sorted_values])

    def python_value(self, value):
        if not value:
            return []
        dates_str = json.loads(value)
        return [dt.datetime.fromisoformat(d) for d in dates_str]


class Document(Model):
    # fmt: off
    id           = SmallIntegerField(primary_key=True, help_text="DB auto increment id")
    public_id    = CharField(null=True, help_text="Public slug/sqid")
    user         = ForeignKeyField(User, backref="documents")
    title        = CharField(help_text="Document title")
    category     = CharField(help_text="Document category",choices=[(c.value, c.name) for c in Category])
    created      = DateTimeField(default=dt.datetime.now(), help_text="Datetime first saved.")
    updated      = DateTimeField(null=True, help_text="Dt.Datetime last updated.")
    fileid       = CharField(null=True)
    filename     = CharField(null=True)
    filesize     = SmallIntegerField(null=True)
    mimetype     = CharField(default="application/pdf")
    source       = CharField(null=True)
    url          = CharField(null=True)
    tags         = ListField(default=list)

    # Recipe category-specific fields
    dates_cooked = DateTimeListField(default=list)
    quality      = SmallIntegerField(null=True, constraints=[Check("0 <= quality <= 5")])
    complexity   = SmallIntegerField(null=True, constraints=[Check("0 <= quality <= 5")])
    # fmt: on

    def save(self, *args, **kwargs) -> int:
        """Override save method to set updated attr on actual updates."""
        self.updated = dt.datetime.now() if self._pk is not None else None
        app = None
        if "app" in kwargs:
            app = kwargs["app"]
            del kwargs["app"]  # We need to remove so peewee's save method doesn't bug out on us

        count_rows_modified = super().save(*args, **kwargs)

        # Do we need to generate a new public slug?
        if not self.public_id:
            assert self.id, "Sorry, just saved a document but don't have an ID yet?"
            assert app, "Sorry, we need an app instance argument for configuration value: 'SQID_KEY'!"
            encoder = sqids.Sqids(alphabet=app.config["SQID_KEY"])
            self.public_id = encoder.encode([self.id])
            self.save()
        return count_rows_modified

    def update_sqid(self, app) -> bool:
        """Update the sqid using the app configuration for the current id."""

    @property
    def title_as_file(self) -> str:
        """Convert title to a file-safe filename when we download/display a pdf."""
        # Start with the title
        if not self.title:
            return "-document-.pdf"  # FIXME: What about other mimetypes?
        safe_name = self.title

        # Normalize unicode characters
        safe_name = unicodedata.normalize("NFKD", safe_name)

        # Remove/replace unsafe characters
        safe_name = re.sub(r'[<>:"/\\|?*]', "", safe_name)  # Windows forbidden chars
        safe_name = re.sub(r"[^\w\s\-_.]", "", safe_name)  # Keep only word chars, spaces, hyphens, underscores, dots
        safe_name = re.sub(r"\s+", "_", safe_name)  # Replace spaces with underscores
        safe_name = re.sub(r"_+", "_", safe_name)  # Collapse multiple underscores
        safe_name = safe_name.strip("_.")  # Remove leading/trailing underscores and dots

        # Limit length (leave room for .pdf extension)
        max_length = 90
        if len(safe_name) > max_length:
            safe_name = safe_name[:max_length].rstrip("_.")

        return f"{safe_name}.pdf"  # FIXME: What about other mimetypes?

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
    def tags_for_sort(self) -> list[str] | None:
        """Convert the list of tags to a lower-case, sorted comma-separated list."""
        # This is only used for sorting documents by the "tags" column, NOT for display!
        if not self.tags:
            return None
        normalised = [tag.lower() for tag in sorted(self.tags)]
        return "|".join(normalised)

    @property
    def cooked(self) -> int:
        """Return number of times we've cooked this."""
        return len(self.dates_cooked)

    @property
    def created_display(self) -> str:
        """Return created attr in local and nicely formatted."""
        return dt_as_local(self.created)

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
            return str(len(self.dates_cooked))
        return None

    @property
    def dates_cooked_display(self) -> list[str]:
        """Return a list of tuples of dates last cooked, eg. [("2024-02-01", "Monday, February 2nd 2024")...]."""
        return [(lc_.strftime("%Y-%m-%d"), dt_as_date(lc_)) for lc_ in sorted(self.dates_cooked, reverse=True)]


################################################################################
# Utilities
################################################################################
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
