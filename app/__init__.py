"""Application Creator Factory Method."""

import logging as log
import shutil
import warnings
from pathlib import Path

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import flask as f

from environs import Env
from flask.app import Flask  # Typing
from flask_htmx import HTMX
from flask_login import LoginManager
from flask_talisman import Talisman
from peewee import SqliteDatabase
from secure import Secure

import app.constants as c

db = None

from app.models.document import Document
from app.models.user import User

TERM_SIZE = shutil.get_terminal_size(fallback=(80, 24))

htmx = HTMX()
secure_headers = Secure()  # Secure headers


def _create_app_configuration(application: Flask, config_overrides: dict | None = None) -> Flask:
    env = Env(expand_vars=True)
    env.read_env()

    for env_var in [
            "DEBUG_TB_ENABLED",
            "DEBUG_TB_INTERCEPT_REDIRECTS",
            "ENV",
            "FLASK_DEBUG",
            "FLASK_RUN_PORT",
            "LOG_LEVEL",
            "PATH_DATA",
            "REMEMBER_COOKIE_SECURE",
            "SECRET_KEY",
            "SESSION_COOKIE_SECURE",
            "STORAGE_DOCS_DIR_NAME",
            "STORAGE_META_DB_NAME",
    ]:
        application.config[env_var]  = env.str(env_var)

    if config_overrides:
        application.config.update(**config_overrides)

    return application


def _create_app_logging(logging: bool, log_level: str | None, application: Flask) -> Flask:
    if logging is None:
        log.getLogger().setLevel(log.CRITICAL)  # Effectively turn logging OFF!

    elif logging:
        level = {"info": log.INFO, "debug": log.DEBUG}.get(application.config.get("LOG_LEVEL").lower())

        if application.config.get("ENV") == "development":
            format = c.LOGGING_FORMAT_FLASK
        else:
            format = c.LOGGING_FORMAT_GUNICORN

        log.basicConfig(level=level, format=format, force=True, style="{", datefmt=c.LOGGING_FORMAT_DATETIME)

        # See *all* inbound requests for local/development environment (but not in production)
        log.getLogger("werkzeug").disabled = True if application.config["ENV"] == "production" else False

        # Some of our underlying modules are quite "chatty"...shut 'em up ;-)
        for module in (
            "pymongo",
            "pymongo.command",
            "pymongo.serverSelection",
            "matplotlib",
            "botocore",
            "boto3",
            "s3transfer",
            "urllib3",
            "peewee",  # Take out if we want actual sql statements logged...
        ):
            log.getLogger(module).setLevel(log.WARNING)

        # (FYI FWIW: use the following to see all mongodb command traffic)
        # log.getLogger("pymongo.command").setLevel(log.DEBUG)

        log.info(f"...setup logging environment: {log.getLevelName(log.getLogger().getEffectiveLevel())}")
    return application


def _create_app_login(application: Flask) -> Flask:
    login = LoginManager()  # Login/authentication environment
    login.login_message = None
    login.login_view = "auth.login"
    login.init_app(application)

    @login.user_loader
    def load_user(user_id) -> User | None:
        """Load the User for the user_id-> SPECIAL METHOD FOR FLASKLOGIN!."""
        try:
            return User.get(User.user_id == user_id)
        except User.DoesNotExist:
            return None

    log.info("...initialised extension: flask_login")
    return application


def _create_app_htmx(application: Flask) -> Flask:
    htmx.init_app(application)  # HTMX environment (for selected endpoints)
    log.info("...initialised extension: htmx")
    return application


def _create_app_db_connection(application: Flask) -> Flask:
    """Connect to our sqlLite "document" metadata database."""
    global db  # noqa: PLW0603 (sue me)
    models = [User, Document]
    db_path = Path(application.config["PATH_DATA"]) / Path(application.config["STORAGE_META_DB_NAME"])
    db = SqliteDatabase(db_path, pragmas={"autocommit": True, "check_same_thread": False})
    db.bind(models)
    log.info(f"...connected to {db_path.name=} with {len(models)} models defined.")

    return application


def _create_app_blueprints(application: Flask) -> Flask:
    from app.blueprints.admin import bp as blueprint_admin  # noqa: PLC0415
    from app.blueprints.auth import bp as blueprint_auth  # noqa: PLC0415
    from app.blueprints.main import bp as blueprint_main  # noqa: PLC0415
    from app.blueprints.stats import bp as blueprint_stats  # noqa: PLC0415

    application.register_blueprint(blueprint_auth)
    application.register_blueprint(blueprint_main)
    application.register_blueprint(blueprint_stats)
    application.register_blueprint(blueprint_admin)

    from app.blueprints.main import render_display_column  # noqa: PLC0415

    application.jinja_env.globals.update(render_display_column=render_display_column)

    log.info("...registered blueprints")
    return application


def _create_app_ctx_prcssrs(application: Flask) -> Flask:
    @application.context_processor
    def inject_watermark():
        match application.config["ENV"]:
            case "development":
                return {"watermark": "Development"}
            case "testing":
                return {"watermark": "Deployment Testing"}
            case "production":
                return {"watermark": ""}
            case _:
                return {}

    @application.before_request
    def before_request():
        if db.is_closed():
            db.connect()

    @application.teardown_request
    def teardown_request(exception):
        if not db.is_closed():
            db.close()

    log.info("...context processors")

    return application

def create_app(logging=True, log_level: str | None = log.INFO, config_overrides: dict | None = None) -> Flask:
    """Create and return our core Flask application object instance."""
    application = f.Flask(__name__, template_folder="templates")

    # Before anything else, setup our secure-header environment
    Talisman(
        application,
        force_https=True,
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        referrer_policy='strict-origin-when-cross-origin',
        content_security_policy={
            'default-src': "'self'",
            'script-src': [
                "'self'",
                "'unsafe-inline'",              # Allow inline scripts
                "unpkg.com",                    # HTMX
                "kit.fontawesome.com",          # Font Awesome library
                "cdn.jsdelivr.net",             # Other JS libraries
            ],
            'style-src': [
                "'self'",
                "'unsafe-inline'",              # Allow inline styles
                "unpkg.com",                    # Flatpicker's CSS
                "fonts.googleapis.com",         # Google Fonts CSS
                "fonts.bunny.net",              # Bunny CDN delivered font(s)
            ],
            'font-src': [
                "'self'",
                "fonts.bunny.net",              # Bunny CDN delivered font(s)
                "https://ka-p.fontawesome.com",  # Explicit HTTPS
            ],
            'img-src': [
                "'self'",
                "data:",                        # For inline images
            ],
            'connect-src': [
                "'self'",
                "ka-p.fontawesome.com",         # Font Awesome dynamic loading
                "unpkg.com",                    # Hyperscript source maps
            ],
        }
    )

    application.jinja_env.line_statement_prefix = "#"  # Simplify our templates!
    with application.app_context():
        # Setup initial logging configuration to get us going
        if logging:
            log.basicConfig(
                level=log_level,
                format=c.LOGGING_FORMAT_FLASK,
                force=True,
                style="{",
                datefmt=c.LOGGING_FORMAT_DATETIME,
            )

        # Get configuration
        application = _create_app_configuration(application, config_overrides)

        # Setup Logging
        application = _create_app_logging(logging, log_level, application)

        # Initialise our login/authentication environment
        application = _create_app_login(application)

        # Configure HTMX extension
        application = _create_app_htmx(application)

        # Connect and setup our database environments
        application = _create_app_db_connection(application)

        # Setup and register all our application blueprints
        application = _create_app_blueprints(application)

        # Add our "context processers"
        application = _create_app_ctx_prcssrs(application)

        log.info("Ready...")  # , done=True)

    return application
