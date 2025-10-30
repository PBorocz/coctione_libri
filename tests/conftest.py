import logging as log
import os
import subprocess

import pytest

from app import create_app
from app.models import Category
from app.models.document import Document
from app.models.user_rdb import User

log.getLogger("peewee").setLevel(log.INFO)  # or log.WARNING


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
    application = create_app(logging=False, config_overrides={"SQLITE_DB": test_db_url})
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
    """Yield up a NON-SAVED user instance."""
    user = User.factory(email="test@foo.com", password="aPassword", user_id="aUserId")
    # print(f"created {user.email=}")
    yield user
    user.delete_instance()
    # print(f"deleted {user.email=}")


@pytest.fixture
def document_and_user(app, user):
    """Yield up a NON-SAVED document instance."""
    user.save()  # Can't use as a foreign key until id is assigned on save!
    document = Document(user=user, title="a Document Title", category=Category.COOKING_RECIPES)
    # print(f"created {document.title=}")
    yield document, user
    if document._pk is not None:
        document.delete_instance()
        # print(f"deleted {document.title=}")
    user.delete_instance()


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
