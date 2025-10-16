import os
import subprocess

import pytest

from app import create_app, db
from app.models.user_rdb import User

# from app.types.sd_stations import SDStations
# from app.types.user_favorites import UserFavorites

# If we want to test against a client?
# https://stackoverflow.com/questions/63584554/how-do-i-import-my-flask-app-into-my-pytest-tests
# with application.app_context():
#     with application.test_client() as client:
#         yield client


@pytest.fixture(scope="session")
def app(request):
    # Setup test database path
    test_db_path = "db/coctione_libri_testing.sqlite3"
    os.makedirs(os.path.dirname(test_db_path), exist_ok=True)

    # Run dbmate to create schema
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite://{os.path.abspath(test_db_path)}"  # Use absolute path
    env["SQLITE_DB"] = f"sqlite://{test_db_path}"
    try:
        subprocess.run(["dbmate", "up"], env=env, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        pytest.fail(f"dbmate up failed: {e.stderr.decode()}")

    application = create_app()
    application.app_context().push()

    yield application

    # Cleanup!
    if os.path.exists(test_db_path):
        os.unlink(test_db_path)


################################################################################
# Data object fixtures
################################################################################
@pytest.fixture
def user(app):
    test_user_parms = {
        "email": "test@foo.com",
        "password": "aPassword",
    }
    # Give back an instance that's NOT SAVED!!
    yield User.create(**test_user_parms)

    # Clean up just in case did another insert during the respective test.
    db.delete_all_users()


################################################################################
@pytest.fixture
def sd_lineup(app):
    sd_lineup = SDLineup.factory(
        lineup="aLineup",
        name="aName",
        uri="aURI",
    )
    yield sd_lineup

    # Clean up just in case did another insert during the respective test.
    SDLineup.find({}).delete().run()


################################################################################
@pytest.fixture
def sd_stations(app):
    """Set 2 SD TV stations to support test_listing's factory from a gem instance."""
    for d_station in [
        {
            "stationID": "bs-az",
            "sport": True,
        },
        {
            "stationID": "root-nw",
            "sport": True,
        },
    ]:
        sd_station = SDStation.factory(d_station, "testLineupName")
        sd_station.save()

    # RE_READ the stations now that we have new ones entered:
    app.config["SDSTATIONS"] = SDStations.query_all()

    yield True

    # Clean up just in case we did another insert during the respective test.
    SDStation.find({}).delete().run()
