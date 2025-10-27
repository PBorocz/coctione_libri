"""Base application document model (in relational form)."""

import json
from datetime import datetime
from enum import Enum

from peewee import CharField, Check, DateTimeField, ForeignKeyField, Model, SmallIntegerField, TextField

from app.models import Category
from app.models.user_rdb import User


class ListField(TextField):
    def db_value(self, value):
        if not value:
            return "[]"
        # Convert to lowercase, remove duplicates, and sort
        unique_value = sorted(dict.fromkeys(str(item).lower() for item in value))
        return json.dumps(unique_value)

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
        return [datetime.fromisoformat(d) for d in dates_str]


class Document(Model):
    # fmt: off
    id           = SmallIntegerField(primary_key=True, help_text="DB auto increment id")
    user         = ForeignKeyField(User, backref="documents")
    title        = CharField(help_text="Document title")
    category     = CharField(help_text="Document category",choices=[(c.value, c.name) for c in Category])
    created      = DateTimeField(default=datetime.now(), help_text="Datetime first saved.")
    updated      = DateTimeField(null=True, help_text="Datetime last updated.")
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

    def save(self, *args, **kwargs):
        """Override save method to set updated attr on actual updates."""
        self.updated = datetime.now() if self._pk is not None else None
        return super().save(*args, **kwargs)
