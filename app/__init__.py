"""Sole "Application" Creator Factory Method."""

import logging as log
import warnings

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import flask as f

from dynaconf import FlaskDynaconf
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager
from flask_mongoengine import MongoEngine

import app.constants as c
from app.models.users import query_user


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

            # Some of our underlying modules are quite "chatty"...shut 'em up ;-)
            for module in ("pymongo.command", "pymongo.serverSelection", "matplotlib"):
                log.getLogger(module).setLevel(log.WARNING)

            log.debug(f"...setup logging environment: {log.getLevelName(log.getLogger().getEffectiveLevel())}")

        log.debug(f"...configured configuration environment: {application.config.get('ENV')}")

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

        log.debug("...initialised extension: flask_login")

        ################################################################################
        # Configure extensions (if necessary)
        ################################################################################
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
            log.debug("...initialised extension: flask_debug_toolbar")

        ################################################################################
        # Connect and setup our database environment.
        ################################################################################
        app_db_settings = application.config["mongo_db"]
        application.config["MONGODB_SETTINGS"] = [
            {"host": app_db_settings, "alias": "default"},
        ]
        MongoEngine().init_app(application)
        log.debug(f"...connected to MongoDB: {app_db_settings[0:40]}")

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

        application.register_blueprint(blueprint_admin)
        application.register_blueprint(blueprint_auth)
        application.register_blueprint(blueprint_main)
        application.register_blueprint(blueprint_stats)

        from app.blueprints.main import render_display_column

        application.jinja_env.globals.update(render_display_column=render_display_column)

        log.debug("...registered blueprints")

        ################################################################################
        # Add our "context processers"
        ################################################################################
        @application.context_processor
        def inject_watermark():
            if application.config["development"]:
                return {"watermark": "Development"}
            return {}

        log.debug("...defined context processors")

        log.debug("setup done, ready to go!...")
    return application
