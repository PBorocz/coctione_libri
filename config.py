"""Base configuration environment, may be overriden for testing."""
import os

import pretty_errors

from app import constants as c


class Config:
    """."""
    # Standard Flask variable..
    SECRET_KEY: bool = os.getenv("SECRET_KEY")

    # Bunny Content Delivery Network
    CDN_DEBUG: bool = os.getenv("RENDER") != "true"  # Default is to run *without* debug (ie. in production mode)
    CDN_DOMAIN: str = os.getenv("CDN_DOMAIN")
    CDN_TIMESTAMP: bool = False
    SESSION_COOKIE_SECURE: bool = True
    REMEMBER_COOKIE_SECURE: bool = True

    # Are we running on Render? (ie. in our production environement)
    PRODUCTION: bool = os.getenv("PRODUCTION") == "true"

    # Flask DebugToolbar configuration (essentially, no SQL or version)
    DEBUG_TB_PANELS = [
        "flask_debugtoolbar.panels.timer.TimerDebugPanel",
        "flask_debugtoolbar.panels.headers.HeaderDebugPanel",
        "flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel",
        "flask_debugtoolbar.panels.template.TemplateDebugPanel",
        "flask_debugtoolbar.panels.logger.LoggingPanel",
    ]

    # MongoDB database environment to connect to
    DB_ENV = os.getenv("DB_ENV")
    if DB_ENV not in c.DB_ENVS:
        msg = f"Sorry, DB_ENV='{DB_ENV}' is not recognised, must be one of {', '.join(list(c.DB_ENVS))}."
        raise RuntimeError(msg)

    MONGODB_SETTINGS = [
        {
            "host"  : os.getenv(f"DB_{DB_ENV.upper()}"),
            "alias" : "default",
        },
    ]

###############################################################################
# Pretty-Errors Configuration
# https://github.com/onelivesleft/PrettyErrors/
###############################################################################
pretty_errors.configure(
    filename_display    = pretty_errors.FILENAME_EXTENDED,
    line_number_first   = True,
    display_link        = True,
    lines_before        = 5,
    lines_after         = 2,
    line_color          = pretty_errors.RED + "> " + pretty_errors.default_config.line_color,
    code_color          = "  " + pretty_errors.default_config.line_color,
    truncate_code       = True,
    display_locals      = True,
)
