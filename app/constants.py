"""Constants."""

###############################################################################
# Logging infrastructure
###############################################################################
# LOGGING_FORMAT = "{levelname:8s} [{funcName:24s}:{lineno:3d}] {message}"
LOGGING_FORMAT = "{levelname:8s} {message}"
LOGGING_DATEFMT = "%Y-%m-%d %H:%M:%S"

###############################################################################
# Database Environments
###############################################################################
DB_ENVS = ("local", "production")

###############################################################################
# Client-side cookie management
###############################################################################
COOKIE_NAME = "coctioni_libri"
SORT_ASCENDING = "fa-sort-up"
SORT_DESCENDING = "fa-sort-down"
