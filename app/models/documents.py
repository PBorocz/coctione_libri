"""."""
from datetime import datetime

import mongoengine as me

from app.models.users import Users


class Documents(me.Document):
    """Coctioni-Libri Base Document."""
    # fmt: off
    user             = me.ReferenceField(Users, required=True)           # FK to user
    title            = me.StringField(max_length=120, required=True)     # Display title, eg. Something Good To Cook.pdf
    created          = me.DateTimeField(default=datetime.utcnow)         # Date stamp when created in Raindrop!
    updated          = me.DateTimeField()                                # When last updated (usually from CLI)
    tags             = me.SortedListField(me.StringField(max_length=50)) # List of tags (in "Title", ie. display format)
    raindrop_id      = me.IntField(required=True)                        # Original ID in Raindrop
    raindrop_created = me.DateTimeField()                                # Original creation date in Raindrop
    file_            = me.FileField()                                    # GridFS link to actual pdf/file content.
    # fmt: on

    meta = {'indexes': ["tags"]}
