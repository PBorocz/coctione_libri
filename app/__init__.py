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


def create_app(config_override=None, setup_logging=True, log_level: str | None = None):
    application = f.Flask(__name__, template_folder="templates")
    log.debug("...created application object")

    with application.app_context():
        ################################################################################
        # Get configuration
        ################################################################################
        dynaconf = FlaskDynaconf()
        dynaconf.init_app(application)

        # Set our environmen
        application.config["production"] = True if application.config.get("ENV").casefold() == "production" else False
        application.config["development"] = not application.config["production"]
        log.debug(f"...configured configuration environment -> {application.config.get('ENV')}")

        ################################################################################
        # Setup Logging and default log level if requested. There are cases where we
        # call create_app NOT part of wsgi, eg. testing, cli etc. hence, the override.
        ################################################################################
        if setup_logging:
            level = {"info": log.INFO, "debug": log.DEBUG}.get(application.config.get("LOG_LEVEL").lower())
            log.basicConfig(level=level, format=c.LOGGING_FORMAT, force=True, style="{")

            # See *all* inbound requests for local/development environment (but not in production)
            log.getLogger("werkzeug").disabled = True if application.config["production"] else False

            log.debug(f"...setup logging environment -> '{log.getLevelName(log.getLogger().getEffectiveLevel())}'")

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
            from app.models.users import query_user

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
        db = MongoEngine()
        app_db_settings = application.config["mongo_db"]
        application.config["MONGODB_SETTINGS"] = [
            {"host": app_db_settings, "alias": "default"},
        ]
        db.init_app(application)
        log.debug(f"...connected to MongoDB -> '{app_db_settings[0:40]}'")

        ################################################################################
        # Setup static resources..
        ################################################################################
        # application.config["SOURCES"] = Sources.factory()

        ################################################################################
        # Finally, setup and register all our application blueprints
        ################################################################################
        from app.blueprints.auth import bp as blueprint_auth
        from app.blueprints.main import bp as blueprint_main
        from app.blueprints.tags import bp as blueprint_tags

        application.register_blueprint(blueprint_auth)
        application.register_blueprint(blueprint_main)
        application.register_blueprint(blueprint_tags)

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
