"""Sole "Application" Creator Factory Method."""

import logging as log
import shutil
import warnings

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import flask as f

import boto3
from dynaconf import FlaskDynaconf
from flask.app import Flask  # Typing
from flask_debugtoolbar import DebugToolbarExtension
from flask_htmx import HTMX
from flask_login import LoginManager
from mongoengine import connect
from pymongo import MongoClient

import app.constants as c
from app.models.user import query_user

TERM_SIZE = shutil.get_terminal_size(fallback=(80, 24))

htmx = HTMX()


def terminal_update(msg: str, done: bool = False) -> None:
    """Update to our terminal but with line "over-writing" unless we're 'done'."""
    padding = f"{' '*(TERM_SIZE.columns - len(msg))}"
    print(f"\r{msg}{padding}")  # , end="")
    if done:
        print()


def _create_app_configuration(application: Flask) -> Flask:
    dynaconf = FlaskDynaconf()
    dynaconf.init_app(application, load_dotenv=True)

    # Set booleans for ease in checking our environment.
    application.config["production"] = True if application.config.get("ENV").casefold() == "production" else False
    application.config["development"] = not application.config["production"]
    terminal_update(f"...configured configuration environment: {application.config.get('ENV')}")
    return application


def _create_app_logging(logging: bool, log_level: str | None, application: Flask) -> Flask:
    if logging is None:
        log.getLogger().setLevel(log.CRITICAL)  # Effectively turn logging OFF!

    elif logging:
        level = {"info": log.INFO, "debug": log.DEBUG}.get(application.config.get("LOG_LEVEL").lower())
        # log.basicConfig(level=level, format=c.LOGGING_FORMAT, force=True, style="{")
        log.basicConfig(level=level, force=True, style="{")

        # See *all* inbound requests for local/development environment (but not in production)
        log.getLogger("werkzeug").disabled = True if application.config["production"] else False

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

        terminal_update(f"...setup logging environment: {log.getLevelName(log.getLogger().getEffectiveLevel())}")
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

    terminal_update("...initialised extension: flask_login")
    return application


def _create_app_extensions(application: Flask) -> Flask:
    htmx.init_app(application)  # HTMX environment (for selected endpoints)

    if application.config["development"]:
        toolbar = DebugToolbarExtension()
        toolbar.init_app(application)

        application.config["DEBUG_TB_PANELS"] = [
            "flask_debugtoolbar.panels.timer.TimerDebugPanel",
            "flask_debugtoolbar.panels.headers.HeaderDebugPanel",
            "flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel",
            "flask_debugtoolbar.panels.template.TemplateDebugPanel",
            "flask_debugtoolbar.panels.logger.LoggingPanel",
        ]
        terminal_update("...initialised extension: flask_debug_toolbar")
    return application


def _create_app_connections(application: Flask) -> Flask:
    """Connect to our external service connections."""
    ################################################################################
    # "Document" metadata first...
    ################################################################################
    vendor = application.config["storage_meta_vendor"]
    app_db_settings = application.config["storage_meta_url"]
    # application.config["MONGODB_SETTINGS"] = [
    #     {"host": app_db_settings, "alias": "default"},
    # ]
    connect(host=app_db_settings)
    db_name = app_db_settings.split("?")[0].split("/")[-1]
    terminal_update(f"...connected to {vendor}: {db_name}")

    ################################################################################
    # "Document" file/object store next...
    ################################################################################
    vendor = application.config["storage_file_vendor"]
    endpoint_url = application.config["storage_file_endpoint_url"]
    region_name = application.config["storage_file_region_name"]
    access_key_id = application.config["storage_file_access_key_id"]
    secret_access_key = application.config["storage_file_secret_access_key"]
    application.config["STORAGE_FILE"] = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region_name,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
    )
    terminal_update(f"...connected to {vendor}: {endpoint_url}:{region_name}")

    return application


def _create_app_blueprints(application: Flask) -> Flask:
    from app.blueprints.admin import bp as blueprint_admin
    from app.blueprints.auth import bp as blueprint_auth
    from app.blueprints.main import bp as blueprint_main
    from app.blueprints.stats import bp as blueprint_stats

    application.register_blueprint(blueprint_auth)
    application.register_blueprint(blueprint_main)
    application.register_blueprint(blueprint_stats)
    application.register_blueprint(blueprint_admin)

    from app.blueprints.main import render_display_column

    application.jinja_env.globals.update(render_display_column=render_display_column)

    terminal_update("...registered blueprints")
    return application


def _create_app_context_processors(application: Flask) -> Flask:
    @application.context_processor
    def inject_watermark():
        if application.config["development"]:
            return {"watermark": "Development"}
        return {}

    terminal_update("...defined context processors")
    return application


def create_app(logging=True, log_level: str | None = None) -> Flask:
    """Create and return our core Flask application object instance."""
    application = f.Flask(__name__, template_folder="templates")
    application.jinja_env.line_statement_prefix = "#"  # Simplify our templates!
    with application.app_context():
        # Get configuration
        application = _create_app_configuration(application)

        # Setup Logging
        application = _create_app_logging(logging, log_level, application)

        # Initialise our login/authentication extension
        application = _create_app_login(application)

        # Configure extensions (if necessary)
        application = _create_app_extensions(application)

        # Connect and setup our database environments
        application = _create_app_connections(application)

        # Setup static resources..
        # application.config["SOURCES"] = Sources.factory()

        # Finally, setup and register all our application blueprints
        application = _create_app_blueprints(application)

        # Add our "context processers"
        application = _create_app_context_processors(application)

        terminal_update("Ready...", done=True)

    return application
