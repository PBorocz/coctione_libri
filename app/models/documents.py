"""Base application document model."""
from datetime import datetime

import mongoengine as me_

from app.models.users import Users


class Documents(me_.Document):
    """Coctioni-Libri Base Document."""

    # fmt: off
    user             = me_.ReferenceField(Users, required=True)            # FK to user
    title            = me_.StringField(max_length=120, required=True)      # Display title, eg. SomethingGoodToCook.pdf
    created          = me_.DateTimeField(default=datetime.utcnow)          # Date stamp when created in Raindrop!
    updated          = me_.DateTimeField()                                 # When last updated (usually from CLI)
    tags             = me_.SortedListField(me_.StringField(max_length=50)) # List of tags in "Titled" display format)
    raindrop_id      = me_.IntField(required=True)                         # Original ID in Raindrop
    raindrop_created = me_.DateTimeField()                                 # Original creation date in Raindrop
    file_            = me_.FileField()                                     # GridFS link to actual pdf/file content.
    # fmt: on

    meta = {"indexes": ["tags"]}
