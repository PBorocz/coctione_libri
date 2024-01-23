"""Run an import of a set of pdf's to our collection."""
import argparse
import logging as log
import os
import tomllib
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)  # Ignore arning from flask and MarkupSafe (in flask-wtf)
# from flask import current_app

import app.constants as c
from app import create_app
from app.cli import setup_logging
from app.models import Documents, Users


def main(args: argparse.Namespace):
    """Do our import."""
    setup_logging(True)

    # Setup our application/db connection
    os.environ["DB_ENV"] = args.database
    app = create_app(setup_logging=False)
    app.app_context().push()

    go()

def go():

    user, created = Users.get_or_create(email='peter@example.com', first_name='Peter', last_name='Borocz')

    # title = "aTitle"
    # if not (doc := Documents.objects(title=title)):
    #     doc = Documents(title=title)
    #     path_pdf = Path("/Users/peter/Downloads/Raindrop/RaindropDownload/480061400.pdf")
    #     with open(path_pdf, 'rb') as fd:
    #         doc.file_.put(fd, content_type = 'application/pdf')
    #     doc.save()

    # Clean out the database
    # Documents.objects().delete() # CAN'T USE THIS AS IT LEAVES THE UNDERLYING FILES!
    # Use this instead:
    # for doc in Documents.objects:
    #     doc.file_.delete()
    #     doc.delete()

    path_toml = Path("/Users/peter/Downloads/raindrop_export_2024-01-20T09:54:50.423627")
    with open(path_toml / Path("recipes.toml"), "rb") as fh_toml:
        raindrops = tomllib.load(fh_toml)

    for raindrop in raindrops.get("export"):

        path_pdf = Path(f"/Users/peter/Downloads/Raindrop/RaindropDownload/{raindrop['id']}.pdf")
        if not path_pdf.exists():
            continue

        doc = Documents(
            user=user,
            title=raindrop["title"],
            raindrop_id=raindrop["id"],
            raindrop_created=raindrop["created"],
        )
        if raindrop["tags"]:
            doc.tags = raindrop["tags"]
        with open(path_pdf, 'rb') as fd:
            doc.file_.put(fd, content_type = 'application/pdf')
        doc.save()
        print(f"Saved {raindrop['id']}")


    ################################################################################
    # Cleanup: delete all *superfluous* gem's that have passed.
    ################################################################################
    # Gem.cleanup()

    # ################################################################################
    # # Perform any/all pre-usage data validation (will exit if errors encountered!)
    # ################################################################################
    # validate_team_files()

    # ################################################################################
    # # Get list of sports to refresh based on either current day of week or by request.
    # ################################################################################
    # sports_to_refresh = current_app.config.get("SPORTS").get_sports_to_refresh(args)
    # if not sports_to_refresh:
    #     log.warning("No sports are scheduled or overridden to be processed")

    # ################################################################################
    # # GO! -> Perform the refresh method for the specific sport(s)
    # ################################################################################
    # success: bool = True
    # for sport in sports_to_refresh:
    #     log.info(f"{'-'*78}")
    #     log.info(sport.id)
    #     if not refresh(args, sport):
    #         success = False
    # log.info(f"{'-'*78}")

    # # Send logging results by email if requested (e.g. when running as a cron-job)
    # if args.email_log:
    #     email_log("Listings Refresh", log_file)

    # if not success:
    #     sys.exit(1)


# def refresh(args: argparse.Namespace, sport: Sport) -> bool:
#     """Refresh the database for the specified sport, return True if no errors."""
#     try:
#         time_start = time.perf_counter()
#         refresh_sport(args, sport)
#     except Exception:  # pylint: disable=broad-exception-caught
#         msg = f"Sorry, unable to complete refresh of {sport.id}: {traceback.format_exc()}"
#         log.critical(msg)
#         return False
#     log.info(f"{time.perf_counter() - time_start:8.4f} seconds")
#     return True


# def refresh_sport(args: argparse.Namespace, sport: Sport) -> bool:
#     """Perform a "generic" refresh based on the site attributes in the sport's definition."""
#     methods = _get_methods(sport)
#     if "combined" in methods:
#         if args.dry_run:
#             meth: typing.Callable = methods.get("combined")
#             name: str = meth.__name__
#             log.info(f"DRY-RUN: {sport.id:38s} -> {name}")
#         else:
#             combined(sport, methods.get("combined"))
#     else:
#         assert "schedule" in methods, "Sorry, 'schedule' must exist in build_method_s if 'combined' doesn't!"
#         if args.dry_run:
#             meth_sch: typing.Callable = methods.get("schedule")
#             name_sch: str = meth_sch.__name__
#             if methods.get("scoring"):
#                 meth_scr: typing.Callable = methods.get("scoring")
#                 name_scr: str = meth_scr.__name__
#                 msg = f"DRY-RUN: {sport.id:38s} -> {name_sch} & {name_scr}"
#             else:
#                 msg = f"DRY-RUN: {sport.id:38s} -> {name_sch}"
#             log.info(msg)
#         else:
#             split(sport, methods.get("schedule"), methods.get("scoring"))

#     return True


# def _get_methods(sport: Sport) -> dict[str, typing.Callable]:
#     """Import and return the respective update methods based on the sport's 'site' configuration."""

#     def _get_module(module_name):
#         try:
#             return import_module(module_name)
#         except ModuleNotFoundError as exc:
#             msg = f"<pre>{exc} - Sorry, we couldn't import module {module_name}</pre>'"
#             log.critical(msg)
#             raise RuntimeError(msg) from exc

#     refresh_methods = {}
#     for type_, build_method_s in sport.build_method_s.items():
#         module_name, method_name = build_method_s.split("|")  # eg. mlb_com|get_schedule
#         module = _get_module(f"app.sites.{module_name}")
#         refresh_methods[type_] = getattr(module, method_name)
#     return refresh_methods


# ################################################################################
# # PRIMARY Build/Refresh methods.
# ################################################################################
# def split(sport: Sport, sports_schedule_refresh_method, sports_standing_refresh_method=None) -> None:
#     """Refresh in case where we have *separate* methods for standings vs schedule!."""
#     # Query, process and save away the sport's full schedule
#     if not (schedule := sports_schedule_refresh_method(sport)):
#         log.warning(f"Sorry, sport: '{sport.display}' doesn't have a schedule anymore, could it be out of season?")
#         return

#     # If we have an appropriate method, gather the current standings for each team and save.
#     if sports_standing_refresh_method:
#         standings = sports_standing_refresh_method(sport)
#         # Calculate the *standings*-based score for each item in the schedule
#         schedule.score_schedule_from_standings("standings", standings)

#     # If available, calculate *538*-based score for each item in the schedule
#     if sport.fivethirtyeight:
#         scores_538 = get_538_scores(sport, schedule)
#         schedule.score_schedule_from_standings("538", scores_538)

#     schedule.save()


# def combined(sport: Sport, standings_schedule_method):
#     """Refresh in case where we have *single* method for standings and schedule information."""
#     standings, schedule = standings_schedule_method(sport)
#     # FIXME: Would be nice to get back an actual types/standings instance above instead of a dict by team_id

#     if not schedule:
#         log.warning(f"Sorry, '{sport.id}' doesn't seem to have a schedule anymore!")
#         return

#     # Use the standings to "score" each gem in the schedule..
#     schedule.score_schedule_from_standings("standings", standings)

#     # # If available, calculate and store the *538*-based score for each item in the schedule
#     # if sport.fivethirtyeight:
#     #     schedule.score_schedule_from_standings("538", get_538_scores(sport, schedule))

#     # Finally, we can save (upsert) all the gems in the schedule:
#     schedule.save()

#     # FIXME: Move this to the relevant "site" schedule method
#     # if sport.id == c.SPORT_FOOTBALL_ENGLISH_PREMIER_LEAGUE:
#     #     # Some sport schedule sites don't give us broadcasting information,
#     #     # for those, we can try and laminate tv/radio/streaming from another site:
#     #     update_broadcast(sport, schedule)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CoctioneLibri - Import Raindrops")

    default_directory = Path("~/Downloads/Raindrop/RaindropDownload")

    parser.add_argument(
        "-d",
        "--database",
        help=f"Database environment, eg. {', '.join(c.DB_ENVS)}. Default is 'local'.",
        default="local",
    )

    parser.add_argument(
        "--directory",
        help=f"Directory to read from (default is '{default_directory}')",
        default=default_directory,
    )

    parser.add_argument(
        "--file",
        help="Specific file to import, e.g. recipes.toml",
    )

    ARGS = parser.parse_args()

    # Validate..
    assert ARGS.database in ("production", "local")

    main(ARGS)
