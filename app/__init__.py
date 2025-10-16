"""Sole "Application" Creator Factory Method."""

import logging as log
import shutil
import warnings
from pathlib import Path

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import flask as f

import anodb
import boto3
from dotenv import dotenv_values
from flask.app import Flask  # Typing
from flask_htmx import HTMX
from flask_login import LoginManager
from mongoengine import connect
from secure import Secure

import app.constants as c
from app.models.user import query_user
from app.types.database import Database

TERM_SIZE = shutil.get_terminal_size(fallback=(80, 24))

htmx = HTMX()
secure_headers = Secure()  # Secure headers
db = Database()


def _create_app_configuration(application: Flask, config_overrides: dict | None = dict) -> Flask:
    application.config.update(**dotenv_values(".env", verbose=True))
    application.config.update(**config_overrides)
    log.info(f"...configuration environment: {application.config.get('ENV')}")
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
    def load_user(user_id):
        """Load the User for the user_id-> SPECIAL METHOD FOR FLASKLOGIN!."""
        return query_user(user_id=user_id)

    log.info("...initialised extension: flask_login")
    return application


def _create_app_extensions(application: Flask) -> Flask:
    htmx.init_app(application)  # HTMX environment (for selected endpoints)
    log.info("...initialised extension: htmx")
    return application


def _create_app_connections(application: Flask) -> Flask:
    """Connect to our external service connections."""
    ################################################################################
    # MongoDB "Document" metadata first...
    ################################################################################
    vendor = application.config["STORAGE_META_VENDOR"]
    app_db_settings = application.config["STORAGE_META_URL"]
    connect(host=app_db_settings, uuidRepresentation="standard")
    db_name = app_db_settings.split("?")[0].split("/")[-1]
    log.info(f"...connected to {vendor}: {db_name}")

    ################################################################################
    # Sqlite "Document" metadata...
    ################################################################################
    # path_ = init_db(application)
    path_ = db.init_app(application)
    log.info(f"...connected to SQLite: {path_}")

    ################################################################################
    # "Document" file/object store next...
    ################################################################################
    vendor = application.config["STORAGE_FILE_VENDOR"]
    endpoint_url = application.config["STORAGE_FILE_ENDPOINT_URL"]
    region_name = application.config["STORAGE_FILE_REGION_NAME"]
    access_key_id = application.config["STORAGE_FILE_ACCESS_KEY_ID"]
    secret_access_key = application.config["STORAGE_FILE_SECRET_ACCESS_KEY"]
    boto_client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region_name,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
    )
    # Workaround, stuff the name of the bucket onto the boto client so we don't have
    # to look it up everwhere else..
    boto_client.bucket = application.config["STORAGE_FILE_BUCKET"]
    application.config["STORAGE_FILE"] = boto_client
    log.info(f"...connected to {vendor}: {endpoint_url} -> {boto_client.bucket} ")

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


def _create_app_ctx_processors(application: Flask) -> Flask:
    @application.context_processor
    def inject_watermark():
        if application.config["ENV"] == "development":
            return {"watermark": "Development"}
        elif application.config["ENV"] == "testing":
            return {"watermark": "Deployment Testing"}
        elif application.config["ENV"] == "production":
            return {"watermark": ""}
        return {}

    log.info("...defined context processors")
    return application


def create_app(logging=True, log_level: str | None = None, config_overrides: dict | None = dict) -> Flask:
    """Create and return our core Flask application object instance."""
    application = f.Flask(__name__, template_folder="templates")
    application.jinja_env.line_statement_prefix = "#"  # Simplify our templates!
    with application.app_context():
        # Setup initial logging configuration to get us going
        log.basicConfig(
            level=log.INFO,
            format=c.LOGGING_FORMAT_FLASK,
            force=True,
            style="{",
            datefmt=c.LOGGING_FORMAT_DATETIME,
        )

        # Get configuration
        application = _create_app_configuration(application, config_overrides)

        # Setup Logging
        application = _create_app_logging(logging, log_level, application)

        # Initialise our login/authentication extension
        application = _create_app_login(application)

        # Configure extensions (if necessary)
        application = _create_app_extensions(application)

        # Connect and setup our database environments
        application = _create_app_connections(application)

        # Finally, setup and register all our application blueprints
        application = _create_app_blueprints(application)

        # Add our "context processers"
        application = _create_app_ctx_processors(application)

        log.info("Ready...")  # , done=True)

    return application
