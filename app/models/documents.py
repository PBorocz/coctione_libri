"""Base application document model."""
import datetime as dt
from enum import Enum
from zoneinfo import ZoneInfo

import mongoengine as me_

from app.models.users import Users

TAG_SEP: str = ","  # Separator for adding/editing tags..


class Rating(Enum):
    ZER = 0
    ONE = 1
    TWO = 2
    THR = 3
    FOR = 4
    FIV = 5

    def __str__(self):
        return "★" * self.value  # "•"


class History(me_.EmbeddedDocument):

    """Sub-document for Recipe Documents representing cooking history."""

    # fmt: off
    cooked  = me_.DateTimeField(required=True)                              # Date on which we cooked/prepared the doc
    notes   = me_.StringField()                                             # Document "notes" (in Markdown format)
    created = me_.DateTimeField(required=True, default=dt.datetime.utcnow)  # Date stamp when created in Raindrop!
    # fmt: on


class Documents(me_.Document):

    """Base Recipe Document."""

    # fmt: off
    ################################################################################
    # Required Fields
    ################################################################################
    user             = me_.ReferenceField(Users, required=True)            # FK to user
    title            = me_.StringField(max_length=120, required=True)      # Display title, eg. SomethingGoodToCook.pdf
    created          = me_.DateTimeField(default=dt.datetime.utcnow)       # Date stamp when created in Raindrop!

    ################################################################################
    # Optional Fields
    ################################################################################
    # Generic fields..
    source           = me_.StringField()                                   # Logical source of doc, e.g. NY, FN, etc.
    file_            = me_.FileField()                                     # GridFS link to actual pdf/file content.
    mimetype         = me_.StringField(default="application/pdf")          # Mimetype associated with the file type.
    raindrop_created = me_.DateTimeField()                                 # Original creation date in Raindrop
    raindrop_id      = me_.IntField()                                      # Original ID in Raindrop
    tags             = me_.SortedListField(me_.StringField(max_length=50)) # List of tags in "Titled" display format
    updated          = me_.DateTimeField()                                 # When doc was last "touched"
    url_             = me_.StringField(max_length=2038)                    # Originating URL associated with the doc.

    # "Recipe"-specific fields..
    notes            = me_.StringField()                                   # General document "notes" in Markdown format
    dates_cooked     = me_.ListField(me_.DateTimeField())                  # List of "cooked" dates
    quality          = me_.IntField(min_value=0, max_value=5, choices=[e.value for e in Rating]) # Quality rating
    complexity       = me_.IntField(min_value=0, max_value=5, choices=[e.value for e in Rating]) # Complexity rating
    # fmt: on

    meta = {"indexes": ["tags"]}

    @property
    def quality_enum(self) -> Rating | None:
        """Uptype the quality field from an int to a "Rating"."""
        if self.quality:
            return Rating(self.quality)
        return None

    @property
    def complexity_enum(self) -> Rating | None:
        """Uptype the complexity field from an int to a "Rating"."""
        if self.complexity:
            return Rating(self.complexity)
        return None

    @property
    def tags_as_str(self) -> list[str] | None:
        """Convert the list of tags to a lower-case, sorted comma-separated list."""
        if not self.tags:
            return None
        normalised = [tag.lower() for tag in sorted(self.tags)]
        return TAG_SEP.join(normalised)

    @property
    def cooked(self) -> int:
        """Return number of times we've cooked this."""
        return len(self.dates_cooked)

    @property
    def created_local(self) -> str:
        """Return created attr in local and nicely formatted."""
        return dt_as_local(self.created)

    @property
    def updated_local(self) -> str:
        """Return updated attr in local and nicely formatted if available."""
        if self.updated:
            return dt_as_local(self.updated)
        return ""

    @property
    def last_cooked(self) -> str | None:
        """Return the most recent date we've cooked this."""
        if self.dates_cooked:
            count = len(self.dates_cooked)
            sdate = max(self.dates_cooked).strftime("%Y-%m-%d")
            return f"{sdate} ({count})"
        return None

    @property
    def dates_cooked_local(self) -> list[str]:
        return [dt_as_date(lc_) for lc_ in sorted(self.dates_cooked, reverse=True)]

    def set_tags_from_str(self, s_tags: str):
        """Set the tags in this document based on a comma-delimited list."""
        self.tags = [tag.strip().title() for tag in s_tags.split(TAG_SEP)]

    def source_choices(self) -> list[list[str, str]]:
        """Return the current list of sources across all documents as a Choice list."""
        choices = [["", ""]]  # Choices are a list of lists..
        docs = Documents.objects(source__ne=None).only("source")
        sources = sorted({doc.source for doc in docs})
        choices.extend([[source, source] for source in sources])
        return choices


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


def sources_available() -> list[str]:
    """Return the current list of sources across all documents as a Choice list."""
    sources_available = [""]
    docs = Documents.objects(source__ne=None).only("source")
    sources = sorted({doc.source for doc in docs})
    sources_available.extend(sources)
    return sources_available
