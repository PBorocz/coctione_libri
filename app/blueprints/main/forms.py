"""."""
import wtforms
from flask_wtf import FlaskForm
from wtforms import ValidationError, validators

from app.models.documents import Rating

RATING_CHOICES = [
    [5, Rating.FIV],
    [4, Rating.FOR],
    [3, Rating.THR],
    [2, Rating.TWO],
    [1, Rating.ONE],
    [0, Rating.ZER],
]


class TagListField(wtforms.StringField):

    """Stringfield for a list of separated tags."""

    def __init__(self, label="", validators=None, separator=",", **kwargs):
        """Construct a new field.

        :param label: The label of the field.
        :param validators: A sequence of validators to call when validate is called.
        :param separator: The separator that splits the individual tags.
        """
        super().__init__(label, validators, **kwargs)
        self.separator = separator
        self.data = []

    def _value(self):
        return self.separator.join(self.data) if self.data else ""

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [x.strip().title() for x in valuelist[0].split(self.separator)]


class DocumentEditForm(FlaskForm):
    title = wtforms.StringField(
        "Title",
        render_kw={
            "class": "input",
            "type": "text",
            "placeholder": "eg. A Really Good Recipe",
        },
        validators=[
            validators.DataRequired(message="Sorry, this field is required."),
        ],
    )

    source = wtforms.SelectField(
        "Source",
        choices=[],  # Will be populate when the form is instantiated
    )

    tags = TagListField("Tags")

    notes = wtforms.TextAreaField(
        "Notes",
        render_kw={
            "class": "textarea",
            "type": "text",
            "rows": 10,
            "cols": 63,
        },
    )

    quality = wtforms.SelectField(
        "Quality",
        default=RATING_CHOICES[-1][0],
        choices=RATING_CHOICES,
    )

    complexity = wtforms.SelectField(
        "Complexity",
        default=RATING_CHOICES[-1][0],
        choices=RATING_CHOICES,
    )

    url_ = wtforms.URLField(
        "Link",
        render_kw={
            "class": "input",
            "type": "text",
        },
        validators=[
            validators.Optional(),
            validators.URL(message="Sorry, this isn't a valid URL."),
        ],
    )

    file_ = wtforms.FileField(
        "File",
        render_kw={
            "id": "file_",
            "class": "file-input",
            "script": "on change put me.files[0].name into #file-name",
        },
    )

    ################################################################################
    submit = wtforms.SubmitField(
        "Save",
        render_kw={"class": "button is-link"},
    )

    cancel = wtforms.SubmitField(
        "Cancel",
        render_kw={"class": "button is-link is-light", "formnovalidate": True},
    )

    def validate_file_(self, field):
        """Validate that either File or URL are required."""
        if not field.data and not self.url_.data:
            raise ValidationError("Sorry, if a File isn't provided, a Link must be.")

    def validate_url_(self, field):
        """Validate that either File or URL are required."""
        if not field.data and not self.file_.data:
            raise ValidationError("Sorry, if a Link isn't provided, a File must be.")
