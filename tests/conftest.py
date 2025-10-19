import os
import subprocess

import pytest

from app import create_app, db
from app.models.user_rdb import User


@pytest.fixture(scope="session")
def app(request):
    # Setup test database path
    test_db_path = "/tmp/coctione_libri_testing.sqlite3"
    test_db_url = f"sqlite://{os.path.abspath(test_db_path)}"
    os.makedirs(os.path.dirname(test_db_path), exist_ok=True)

    # Run dbmate to create schema
    env = os.environ.copy()
    env["DATABASE_URL"] = test_db_url
    env["DBMATE_MIGRATIONS_DIR"] = "./app/db/migrations"
    env["DBMATE_SCHEMA_FILE"] = "/tmp/coctione_libri_testing.schema.sql"
    try:
        cmd = ["dbmate", "up"]
        subprocess.run(cmd, env=env, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        pytest.fail(f"dbmate up failed: {e.stderr.decode()}")

    # application = create_app(config_overrides={"SQLITE_DB": f"sqlite://{test_db_path}"})
    application = create_app(config_overrides={"SQLITE_DB": test_db_url})
    application.app_context().push()

    yield application

    # Cleanup!
    if os.path.exists(test_db_path):
        os.unlink(env["DBMATE_SCHEMA_FILE"])
        os.unlink(test_db_path)


################################################################################
# Data object fixtures
################################################################################
@pytest.fixture
def user(app):
    test_user_parms = {
        "email": "test@foo.com",
        "password": "aPassword",
        "state_last_search": "burmese",
        "state_last_category": "Recipes",
    }
    # Give back an instance that's NOT SAVED!!
    yield User.create(**test_user_parms)

    # Clean up just in case did another insert during the respective test.
    # (we don't use the user.delete approach so we don't rely upon code that we should be testing).
    cursor = db._conn.cursor()
    cursor.execute("delete from user where email='test@foo.com'")


################################################################################
# @pytest.fixture
# def sd_lineup(app):
#     sd_lineup = SDLineup.factory(
#         lineup="aLineup",
#         name="aName",
#         uri="aURI",
#     )
#     yield sd_lineup

#     # Clean up just in case did another insert during the respective test.
#     SDLineup.find({}).delete().run()


################################################################################
# @pytest.fixture
# def sd_stations(app):
#     """Set 2 SD TV stations to support test_listing's factory from a gem instance."""
#     for d_station in [
#         {
#             "stationID": "bs-az",
#             "sport": True,
#         },
#         {
#             "stationID": "root-nw",
#             "sport": True,
#         },
#     ]:
#         sd_station = SDStation.factory(d_station, "testLineupName")
#         sd_station.save()

#     # RE_READ the stations now that we have new ones entered:
#     app.config["SDSTATIONS"] = SDStations.query_all()

#     yield True

#     # Clean up just in case we did another insert during the respective test.
#     SDStation.find({}).delete().run()
