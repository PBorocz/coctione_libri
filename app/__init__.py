"""Sole "Application" Creator Factory Method."""
import logging as log
import warnings

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import flask as f

import flask_login
from dotenv import load_dotenv
from flask_mongoengine import MongoEngine
from secure import Secure

# from app.types.sd_stations import SDStations
# from app.types.search import search_factory
# from app.types.sport_s import Sports

load_dotenv(verbose=True)

import app.constants as c

# htmx = HTMX()  # HTMX environment (for selected endpoints)
secure_headers = Secure()  # Secure headers
login = flask_login.LoginManager()  # Login/authentication environment
login.login_message = None
login.login_view = "auth.login"


def create_app(config_override=None, setup_logging=True, log_level: str | None = None):
    application = f.Flask(__name__, template_folder="templates")

    if config_override:
        config = config_override
    else:
        # Import here instead of above to allow for pytest environment to
        # stuff vars into the environment *before* we configure the
        # application.
        from config import Config

        config = Config()

    application.config.from_object(config)

    application.debug = not application.config.get("PRODUCTION")

    ################################################################################
    # If requested, setup Logging and default log level (DEBUG here locally,  INFO
    # for production usage) There are cases where we call create_app NOT part of
    # wsgi, eg. testing, cli etc. in those cases, we don't want to step on their
    # own logging configurations!)
    ################################################################################
    if setup_logging:
        if log_level:
            level = log_level
        else:
            level = log.INFO if application.config.get("PRODUCTION") else log.DEBUG
        log.basicConfig(level=level, format=c.LOGGING_FORMAT, force=True, style="{")

        # See all inbound requests for local/development environment (but not in production)
        log.getLogger("werkzeug").disabled = False if application.config.get("PRODUCTION") else True

    log.debug("Created application object.")

    ################################################################################
    # Initialise our extensions
    ################################################################################
    # htmx.init_app(application)
    login.init_app(application)
    log.debug("Initialised extensions.")

    ################################################################################
    # Connect and setup our database environment.
    ################################################################################
    db = MongoEngine()
    db.init_app(application)
    log.debug(f"Connected to MongoDB -> {application.config.get('DB_ENV').upper()}")

    ################################################################################
    # Finally, setup and register all our application blueprints
    ################################################################################
    from app.blueprints.auth import bp as bp_auth
    from app.blueprints.main import bp as bp_main

    application.register_blueprint(bp_auth)
    application.register_blueprint(bp_main)

    log.debug("Registered blueprints.")

    return application
