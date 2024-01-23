"""User-Management Blueprint."""
import logging as log
from datetime import datetime
from urllib.parse import urljoin, urlparse

import flask_login
import mongoengine

from app import login, secure_headers
from app.blueprints.auth import bp
from app.blueprints.auth.forms import LoginForm, RegistrationForm
from app.models.users import Users, query_user


def is_safe_url(target):
    import flask as f

    ref_url = urlparse(f.request.host_url)
    test_url = urlparse(urljoin(f.request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


################################################################################
# Create "secure" environment...
################################################################################
@bp.after_request
def set_secure_headers(response):
    secure_headers.framework.flask(response)
    return response


@login.user_loader
def load_user(user_id):
    """Load the User for the user_id-> SPECIAL METHOD FOR FLASKLOGIN!."""
    return query_user(user_id=user_id)


@bp.get("/logout")
@flask_login.login_required
def logout():
    import flask as f

    flask_login.logout_user()
    next_ = f.request.args.get("next")
    if not is_safe_url(next_):
        return f.abort(400)
    return f.redirect(next_ or f.url_for("main.main"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Process a request to either render the login page (GET) or handle login request (POST)."""
    import flask as f

    if flask_login.current_user.is_authenticated:
        return f.redirect(f.url_for("main.main"))

    form = LoginForm()
    if form.validate_on_submit():
        log.info(f"Login request: {form.email.data=}")
        user = query_user(email=form.email.data)

        # Does user exist or not match on password?
        if not user or not user.check_password(form.password.data):
            f.flash("Invalid email address or password, please try again.", "is-danger")
            return f.redirect(f.url_for("auth.login"))

        # Yep, log'em in!
        flask_login.login_user(user, remember=form.remember_me.data)

        # Where are we going next?
        next_ = f.request.args.get("next")
        if not is_safe_url(next_):
            return f.abort(400)

        # f.flash("You were successfully logged in.")
        return f.redirect(next_ or f.url_for("main.main"))

    # First time in, render the login page
    return f.render_template("login.html", title="Sign In", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    import flask as f

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = Users.factory(
                email=form.email.data,
                last_login=datetime.utcnow().isoformat(),
                password=form.password.data,
            )
            user.save()
            flask_login.login_user(user)
            f.flash("Congratulations, you are now a registered user!", "is-primary")
            return f.redirect(f.url_for("main.main"))
        except mongoengine.NotUniqueError:
            f.flash("Sorry, unable to create new user as that email address has already been used!")

    return f.render_template("register.html", title="Register", form=form)
