"""Base application document model (in relational form)."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, validator

# START HERE and convert to peewee!


# Assuming these are your enum definitions
class Category(str, Enum):
    # Add your category values here
    pass


class Document(BaseModel):
    # fmt: off
    ######################################################################
    # Primary key
    ######################################################################
    id: int | None = None

    ######################################################################
    # Required fields
    ######################################################################
    user_id  : int
    title    : str      = Field(..., max_length=120)
    category : str
    created  : datetime = Field(default_factory=datetime.utcnow)

    ######################################################################
    # Optional generic document fields
    ######################################################################
    file_content : bytes | None    = None
    filename     : str | None      = None
    filesize     : int             = 0
    mimetype     : str             = "application/pdf"
    notes        : str | None      = None
    source       : str | None      = None
    tags         : list[str]       = Field(default_factory=list)
    updated      : datetime | None = None
    url          : str | None      = Field(None, max_length=2038)

    ######################################################################
    # Recipe category specific fields
    ######################################################################
    dates_cooked: list[datetime] = Field(default_factory=list)
    quality     : int | None     = Field(None, ge=0, le=5)
    complexity  : int | None     = Field(None, ge=0, le=5)
    # fmt: on

    # @validator("tags")
    # def validate_tags(self, v):
    #     """Ensure each tag is max 50 characters."""
    #     for tag in v:
    #         if len(tag) > 50:
    #             raise ValueError(f"Tag '{tag}' exceeds 50 character limit")
    #     return v

    class Config:
        """Set pydantic configuration values."""

        # Allow enum values to be used directly
        use_enum_values = True
        # Enable ORM mode for SQLAlchemy/similar
        from_attributes = True
        # JSON encoders for special types
        json_encoders = {datetime: lambda v: v.isoformat(), bytes: lambda v: v.decode("utf-8") if v else None}
