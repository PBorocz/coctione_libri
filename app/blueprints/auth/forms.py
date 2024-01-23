"""."""
import wtforms
from flask_wtf import FlaskForm
from wtforms import validators

from app.models.users import query_user


class LoginForm(FlaskForm):
    """."""
    email = wtforms.EmailField(
        "Email Address",
        validators=[validators.DataRequired(), validators.Email()],
        render_kw={"class": "input is-danger", "type": "email", "autocomplete": "username"},
    )

    password = wtforms.PasswordField(
        "Password",
        validators=[validators.DataRequired()],
        render_kw={"class": "input", "type": "password", "autocomplete": "new-password"},
    )

    remember_me = wtforms.BooleanField("Remember Me")

    submit = wtforms.SubmitField("Sign In", render_kw={"class": "button is-link"})


class RegistrationForm(FlaskForm):
    """."""
    email = wtforms.EmailField(
        "Email Address",
        render_kw={
            "class": "input is-danger",
            "type": "email",
            "placeholder": "email...",
            "autocomplete": "email",
        },
        validators=[validators.DataRequired(), validators.Email()],
    )

    password = wtforms.PasswordField(
        "Password",
        validators=[validators.DataRequired()],
        render_kw={
            "class": "input",
            "type": "password",
            "placeholder": "...password...",
            "autocomplete": "new-password",
        },
    )

    password2 = wtforms.PasswordField(
        "Confirm Password",
        validators=[validators.DataRequired(), validators.EqualTo("password")],
        render_kw={
            "class": "input",
            "type": "password",
            "placeholder": "...confirm password...",
            "autocomplete": "new-password",
        },
    )

    submit = wtforms.SubmitField("Register", render_kw={"class": "button is-link"})

    def validate_email(self, email):
        """."""
        if query_user(email=email.data):
            raise validators.ValidationError("Please use a different email address, that one is already taken.")
