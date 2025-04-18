"""Sole "Application" Creator Factory Method."""

import logging as log
import shutil
import warnings

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import flask as f

from dynaconf import FlaskDynaconf
from flask_debugtoolbar import DebugToolbarExtension
from flask_htmx import HTMX
from flask_login import LoginManager
from mongoengine import connect
from pymongo import MongoClient

import app.constants as c
from app.models.user import query_user

TERM_SIZE = shutil.get_terminal_size(fallback=(80, 24))

htmx = HTMX()


def terminal_update(msg: str, last: bool = False) -> None:
    padding = f"{' '*(TERM_SIZE.columns - len(msg))}"
    print(f"\r{msg}{padding}", end="")
    if last:
        print()


def create_app(logging=True, log_level: str | None = None):
    """Set our Flask application object and configure the hell out of it!."""
    application = f.Flask(__name__, template_folder="templates")
    application.jinja_env.line_statement_prefix = "#"  # Simplify our templates!

    with application.app_context():
        ################################################################################
        # Get configuration
        ################################################################################
        dynaconf = FlaskDynaconf()
        dynaconf.init_app(application, load_dotenv=True)

        # Set booleans for ease in checking our environment.
        application.config["production"] = True if application.config.get("ENV").casefold() == "production" else False
        application.config["development"] = not application.config["production"]

        ################################################################################
        # Setup Logging and default log level if requested. There are cases where we
        # call create_app NOT part of wsgi, eg. testing, cli etc. hence, the override.
        ################################################################################
        if logging is None:
            log.getLogger().setLevel(log.CRITICAL)  # Effectively turn logging OFF!

        elif logging:
            level = {"info": log.INFO, "debug": log.DEBUG}.get(application.config.get("LOG_LEVEL").lower())
            log.basicConfig(level=level, format=c.LOGGING_FORMAT, force=True, style="{")

            # See *all* inbound requests for local/development environment (but not in production)
            log.getLogger("werkzeug").disabled = True if application.config["production"] else False
            log.getLogger("pymongo").setLevel(log.WARNING)
            # (use the following to see all mongodb command traffic:)
            # log.getLogger("pymongo.command").setLevel(log.DEBUG)

            # Some of our underlying modules are quite "chatty"...shut 'em up ;-)
            for module in ("pymongo.command", "pymongo.serverSelection", "matplotlib"):
                log.getLogger(module).setLevel(log.WARNING)

            terminal_update(f"...setup logging environment: {log.getLevelName(log.getLogger().getEffectiveLevel())}")

        terminal_update(f"...configured configuration environment: {application.config.get('ENV')}")

        ################################################################################
        # Initialise our login/authentication extension
        ################################################################################
        login = LoginManager()  # Login/authentication environment
        login.login_message = None
        login.login_view = "auth.login"
        login.init_app(application)

        @login.user_loader
        def load_user(user_id):
            """Load the User for the user_id-> SPECIAL METHOD FOR FLASKLOGIN!."""
            return query_user(user_id=user_id)

        terminal_update("...initialised extension: flask_login")

        ################################################################################
        # Configure extensions (if necessary)
        ################################################################################
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

        ################################################################################
        # Connect and setup our database environment.
        ################################################################################
        app_db_settings = application.config["mongo_db"]
        application.config["MONGODB_SETTINGS"] = [
            {"host": app_db_settings, "alias": "default"},
        ]
        connect(host=app_db_settings)

        terminal_update(f'...connected to MongoDB: {app_db_settings.split("?")[0].split("/")[-1]}')

        ################################################################################
        # Setup static resources..
        ################################################################################
        # application.config["SOURCES"] = Sources.factory()

        ################################################################################
        # Finally, setup and register all our application blueprints
        ################################################################################
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

        ################################################################################
        # Add our "context processers"
        ################################################################################
        @application.context_processor
        def inject_watermark():
            if application.config["development"]:
                return {"watermark": "Development"}
            return {}

        terminal_update("...defined context processors")
        terminal_update("Ready...", last=True)
    return application
