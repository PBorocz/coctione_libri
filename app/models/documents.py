"""Base application document model."""
import datetime as dt
from zoneinfo import ZoneInfo

from mongoengine import (
    DateTimeField,
    Document,
    FileField,
    ListField,
    ReferenceField,
    SortedListField,
    StringField,
    errors,
    signals,
)
from mongoengine.context_managers import switch_collection
from mongoengine.fields import BaseField

from app.models import Category, Rating
from app.models.users import Users


class RatingField(BaseField):
    def to_python(self, value):
        """Convert the string value held in the DB to a strongly-typed Rating instance."""
        return Rating(value)

    def to_mongo(self, value):
        """Convert the strongly-typed Category Enum instance to an integer for storage."""
        if isinstance(value, Rating):
            return int(value)
        return value

    def validate(self, value):
        try:
            Rating(value)
        except ValueError as exc:
            raise errors.ValidationError(f"Invalid value for Rating: {value=}") from exc


class CategoryField(BaseField):
    def to_python(self, value):
        """Convert the string value held in the DB to a strongly-typed Category instance."""
        return Category(value)

    def to_mongo(self, value):
        """Convert the strongly-typed Category Enum instance to a string for storage."""
        if isinstance(value, Category):
            return str(value)
        return value

    def validate(self, value):
        try:
            Category(value)
        except ValueError as exc:
            raise errors.ValidationError(f"Invalid value for Category: {value=}") from exc


class Documents(Document):

    """Base Documents."""

    # fmt: off
    ################################################################################
    # Required Fields
    ################################################################################
    user     = ReferenceField(Users, required=True)                     # FK to user
    title    = StringField(max_length=120, required=True)               # Display title, eg. 'Cook Me!'
    category = CategoryField(required=True)                             # Document's category
    created  = DateTimeField(required=True, default=dt.datetime.utcnow) # Date stamp when created

    ################################################################################
    # Optional Fields
    ################################################################################
    # Generic (but optional) "document" fields, ie. common across all document categories:
    file_    = FileField()                                 # GridFS link to actual pdf/file content
    notes    = StringField()                               # "Notes" in MD format
    source   = StringField()                               # Logical source of doc, e.g. NY, FN, etc.
    tags     = SortedListField(StringField(max_length=50)) # List of tags in "Titled" display format
    updated  = DateTimeField()                             # When doc was last "touched"
    url_     = StringField(max_length=2038)                # URL associated with the document.

    ################################################################################
    # Recipe Category Specific Fields (and thus, all optional)
    ################################################################################
    dates_cooked = ListField(DateTimeField())                                               # List "cooked" dates
    quality      = RatingField(min_value=0, max_value=5, choices=[e.value for e in Rating]) # Quality rating
    complexity   = RatingField(min_value=0, max_value=5, choices=[e.value for e in Rating]) # Complexity rating
    # fmt: on

    meta = {"indexes": ["tags"]}

    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        """Perform any/all PRE-SAVE data updates/checks (ie. either on create or update)."""
        if document.id:  # Only update "updated" if we're saving an existing document
            document.updated = dt.datetime.utcnow()

    @property
    def quality_enum(self) -> Rating | None:
        """Return the uptyped quality field as "Rating" instead of int."""
        return Rating(self.quality) if self.quality else None

    @property
    def complexity_enum(self) -> Rating | None:
        """Return the uptyped complexity field as "Rating" instead of int."""
        return Rating(self.complexity) if self.complexity else None

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
    def updated_display(self) -> str:
        """Return updated attr in local and nicely formatted if available."""
        return dt_as_local(self.updated) if self.updated else ""

    @property
    def last_cooked(self) -> str | None:
        """Return the most recent date we've cooked this."""
        if self.dates_cooked:
            count = len(self.dates_cooked)
            sdate = max(self.dates_cooked).strftime("%Y-%m-%d")
            return f"{sdate} ({count})"
        return None

    @property
    def dates_cooked_display(self) -> list[str]:
        """Return a list of tuples of dates last cooked, eg. [("2024-02-01", "Monday, February 2nd 2024")...]."""
        return [(lc_.strftime("%Y-%m-%d"), dt_as_date(lc_)) for lc_ in sorted(self.dates_cooked, reverse=True)]

    @classmethod
    def as_user(cls, user: Users) -> str:
        """Return the user's current category's document partition/ollection name.

        Our convention is "documents-<userId>-<documentCategory" (obo of a hierarchical namespace).
        """
        return f"documents-{user.id}-{Category(user.category).collection_root}"


################################################################################
# Signal support (similar do django signals ;-)!)
################################################################################
signals.pre_save.connect(Documents.pre_save, sender=Documents)


################################################################################
# Utilities
################################################################################
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


def sources_available(user: Users) -> list[str]:
    """Return the current list of sources across all documents as a Choice list."""
    sources_available = []
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        docs = user_documents.objects(source__ne=None).only("source")
        sources = sorted({doc.source for doc in docs})
        sources_available.extend(sources)
    return sources_available


def tags_available(user: Users) -> list[str]:
    """Return a sorted list of all current tags (ie. those attached to documents)."""
    tags = set()
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        for document in user_documents.objects(tags__ne=None).only("tags"):
            for tag in document.tags:
                tags.add(tag)
    return sorted(tags)
