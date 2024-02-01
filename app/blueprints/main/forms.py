import wtforms
from flask_wtf import FlaskForm
from wtforms import validators

RATING_CHOICES = [
    [0, ""],
    [5, "*****"],
    [4, "****"],
    [3, "***"],
    [2, "**"],
    [1, "*"],
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

    source = wtforms.StringField(
        "Source",
        render_kw={
            "class": "input",
            "type": "text",
            "placeholder": "eg. NYT",
        },
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
        default=RATING_CHOICES[0][0],
        choices=RATING_CHOICES,
        # validators=[validators.DataRequired()],
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
