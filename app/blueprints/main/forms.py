import wtforms
from flask_wtf import FlaskForm
from wtforms import validators

import app.constants as c
from app.models.gem import convert_relative_to_absolute


class DisplayPreferencesForm(FlaskForm):

    """Documentation for DisplayPreferencesForm."""

    sport = wtforms.SelectField(
        label="Sport",
        validators=[validators.DataRequired()],
    )

    # fmt: off
    date = wtforms.SelectField(
        label="Date Range",
        validators=[validators.DataRequired() ],
        default=c.SPAN_TODAY,
        choices=( # We don't care about the description, these are only for validation!
            (c.SPAN_TODAY      , "..."),
            (c.SPAN_TOMORROW   , "..."),
            (c.SPAN_THIS_WEEK  , "..."),
            (c.SPAN_NEXT_WEEK  , "..."),
            (c.SPAN_WEEKEND    , "..."),
            (c.SPAN_THIS_MONTH , "..."),
            (c.SPAN_NEXT_MONTH , "..."),
            (c.QUERY_FORM_ALL  , "..."),
        ),
    )

    quartile = wtforms.SelectField(
        label="Quartile",
        choices=( # We don't care about the description, these are only for validation!
            (c.QUERY_FORM_ALL , "..."),
            ("top"            , "..."),
            ("top-half"       , "..."),
            ("bottom-half"    , "..."),
            ("bottom"         , "..."),
        ),
        default="top",
        validators=[validators.DataRequired() ],
    )

    broadcast = wtforms.SelectField(
        label="TV Coverage?",
        default=c.QUERY_FORM_ALL,
        choices=( # We don't care about the description, these are only for validation!
            (c.QUERY_FORM_ALL , "..."),
            ("broadcast"      , "..."),
            ("available_to_me", "..."),
        ),
        validators=[validators.DataRequired() ],
    )

    favorites = wtforms.SelectField(
        label="Favorites?",
        default=c.QUERY_FORM_ALL,
        choices=( # We don't care about the description, these are only for validation!
            (c.QUERY_FORM_ALL , "..."),
            ("on"             , "..."),
        ),
        validators=[validators.DataRequired() ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from flask import current_app
        sports = current_app.config.get("SPORTS")
        self.sport.default=sports.sport_choices_ui[0][0]  # Should be c.QUERY_FORM_ALL on behalf of "All Sports"
        self.sport.choices=sports.sport_choices_ui

    # fmt: on


# Calculate the "date" pulldown's choices *dynamically* based on today's date and using the same
# logic as when we'll query for the appropriate pulldown.
# FIXME: Can't we get this from any other of the methods that calculate these???
def get_date_selector_choices(user_tz):
    return_ = []

    dow = "%A"
    m_d = "%b-%d"

    (
        fr_,
        to_,
    ) = convert_relative_to_absolute(user_tz, c.SPAN_TODAY)
    return_.append((c.SPAN_TODAY, f"Today ({fr_.strftime(dow)})"))

    fr_, to_ = convert_relative_to_absolute(user_tz, c.SPAN_TOMORROW)
    return_.append((c.SPAN_TOMORROW, f"Tomorrow ({fr_.strftime(dow)})"))

    fr_, to_ = convert_relative_to_absolute(user_tz, c.SPAN_THIS_WEEK)
    return_.append((c.SPAN_THIS_WEEK, f"This Week ({fr_.strftime(m_d)}-{to_.strftime(m_d)})"))

    fr_, to_ = convert_relative_to_absolute(user_tz, c.SPAN_WEEKEND)
    return_.append((c.SPAN_WEEKEND, f"This Weekend ({fr_.strftime(m_d)}-{to_.strftime(m_d)})"))

    fr_, to_ = convert_relative_to_absolute(user_tz, c.SPAN_NEXT_WEEK)
    return_.append((c.SPAN_NEXT_WEEK, f"Next Week ({fr_.strftime(m_d)}-{to_.strftime(m_d)})"))

    fr_, to_ = convert_relative_to_absolute(user_tz, c.SPAN_THIS_MONTH)
    return_.append((c.SPAN_THIS_MONTH, f"This Month ({fr_.strftime(m_d)}-{to_.strftime(m_d)})"))

    fr_, to_ = convert_relative_to_absolute(user_tz, c.SPAN_NEXT_MONTH)
    return_.append((c.SPAN_NEXT_MONTH, f"Next Month ({fr_.strftime(m_d)}-{to_.strftime(m_d)})"))

    return_.append((c.QUERY_FORM_ALL, "All"))

    return return_


class SearchForm(FlaskForm):
    search = wtforms.StringField(
        "Search",
        render_kw={
            "class": "input",
            "type": "text",
            "placeholder": "search...",
        },
    )
