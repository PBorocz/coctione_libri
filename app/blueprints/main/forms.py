import wtforms
from flask_wtf import FlaskForm
from wtforms import validators

from app.models.documents import Rating

RATING_CHOICES = [
    [5, Rating.FIV],
    [4, Rating.FOR],
    [3, Rating.THR],
    [2, Rating.TWO],
    [1, Rating.ONE],
    [0, Rating.ZER],
]


class DocumentEditForm(FlaskForm):
    title = wtforms.StringField(
        "Title",
        render_kw={
            "class": "input",
            "type": "text",
            "placeholder": "eg. A Really Good Recipe",
        },
        validators=[validators.DataRequired()],
    )

    source = wtforms.SelectField(
        "Source",
        choices=[],  # Will be populate when the form is instantiated
    )

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
