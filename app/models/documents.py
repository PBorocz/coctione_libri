"""Base application document model."""
from datetime import datetime
from enum import Enum

import mongoengine as me_

from app.models.users import Users


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
    cooked  = me_.DateTimeField(required=True)                           # Date on which we cooked/prepared the doc
    notes   = me_.StringField()                                          # Document "notes" (in Markdown format)
    created = me_.DateTimeField(required=True, default=datetime.utcnow)  # Date stamp when created in Raindrop!
    # fmt: on


class Documents(me_.Document):

    """Base Recipe Document."""

    # fmt: off
    ################################################################################
    # Required Fields
    ################################################################################
    user             = me_.ReferenceField(Users, required=True)            # FK to user
    title            = me_.StringField(max_length=120, required=True)      # Display title, eg. SomethingGoodToCook.pdf
    created          = me_.DateTimeField(default=datetime.utcnow)          # Date stamp when created in Raindrop!

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
    dates_cooked     = me_.EmbeddedDocumentListField("History")            # List of "cooked" dates and notes
    quality          = me_.IntField(min_value=0, max_value=5, choices=[e.value for e in Rating]) # Quality rating
    complexity       = me_.IntField(min_value=0, max_value=5, choices=[e.value for e in Rating]) # Complexity rating

    # fmt: on

    meta = {"indexes": ["tags"]}

    @property
    def quality_enum(self):
        if self.quality:
            return Rating(self.quality)
        return None

    @property
    def complexity_enum(self):
        if self.complexity:
            return Rating(self.complexity)
        return None

    @property
    def tags_as_str(self):
        if not self.tags:
            return None
        normalised = [tag.lower() for tag in sorted(self.tags)]
        return ",".join(normalised)

    @property
    def cooked(self):
        """Return number of times we've cooked this."""
        return len(self.dates_cooked)

    def source_choices(self):
        """Return the current list of sources across all documents as a Choice list."""
        choices = [["", ""]]  # Choices are a list of lists..
        docs = Documents.objects(source__ne=None).only("source")
        sources = sorted({doc.source for doc in docs})
        choices.extend([[source, source] for source in sources])
        return choices
