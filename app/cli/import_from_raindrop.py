"""Run either delete or import of a set of pdf's to our collection."""
import argparse
import os
import tomllib
from collections import defaultdict
from pathlib import Path
from pprint import pprint

import tomli_w

import app.constants as c
from app import create_app
from app.cli import setup_logging
from app.models.documents import Documents, Rating
from app.models.users import Users


def main(args: argparse.Namespace):
    """Do our action, ie. either delete or import."""
    setup_logging(True)

    # Setup our application/db connection
    os.environ["DB_ENV"] = args.database
    app = create_app(setup_logging=False)
    with app.app_context():
        if args.action == "import":
            import_()
        elif args.action == "delete":
            delete_()


def delete_():
    user = Users.objects.get(email="peter.borocz@gmail.com")
    count = 0
    for doc in Documents.objects(user=user):
        doc.file_.delete()
        doc.delete()
        count += 1

    print(f"Deleted {count} Documents.")


def import_():
    user = Users.objects.get(email="peter.borocz@gmail.com")

    path_toml = Path("/Users/peter/Downloads/raindrop_export_2024-01-20T09:54:50.423627")
    with open(path_toml / Path("recipes.toml"), "rb") as fh_toml:
        raindrops = tomllib.load(fh_toml)

    sources = defaultdict(int)
    non_documents = []
    print("Importing..", end="")
    for raindrop in raindrops.get("export"):
        path_pdf = Path(f"/Users/peter/Downloads/Raindrop/RaindropDownload/{raindrop['id']}.pdf")

        # Filter down to only entries for whom we ALREADY have pdfs
        if raindrop["type"] != "RaindropType.document":
            non_documents.append(raindrop)
            continue
        continue

        if not path_pdf.exists():
            print(f'\nSkipping: {raindrop.get("file").get("name")}')
            continue

        raindrop["__path_pdf"] = path_pdf
        source = __import_raindrop(user, raindrop)
        sources[source] += 1

    print()
    print(f"Imported {sum(list(sources.values()))} total files from the following sources:")
    pprint(dict(sources))

    # Write out the documents that still have to be converted
    with open(path_toml / Path("recipes_non_documents.toml"), "wb") as fh_toml:
        tomli_w.dump({"links": non_documents}, fh_toml)
    print(f"Wrote {len(non_documents)} non-document entries to recipes_non_documents.toml")

    # Write out the links that still have to be converted
    first_letters = {doc["title"][0] for doc in non_documents}
    with open(path_toml / Path("recipes_non_documents.html"), "w") as fh_html:
        fh_html.write("<html>\n")
        fh_html.write("<body>\n")

        for first_letter in sorted(first_letters):
            fh_html.write(f"<p>{first_letter}</p>\n")
            fh_html.write("<ul>\n")
            for raindrop in sorted(non_documents, key=lambda doc: doc["title"]):
                title = raindrop["title"]
                if title[0] != first_letter:
                    continue
                url = raindrop["link"]
                fh_html.write(f'<li><a href="{url}" target="_blank">{title}</a><br/></li>\n')
            fh_html.write("</ul>\n")
        fh_html.write("</body>\n")
        fh_html.write("</html>\n")
    print(f"Wrote {len(non_documents)} non-document entries to recipes_non_documents.html")


def __import_raindrop(user, raindrop: dict) -> str:
    # Parse name<|source> -> name, source
    name = raindrop.get("file").get("name")
    if "|" in name:
        title, source = name.split("|")
    else:
        title, source = name, None

    doc = Documents(
        user=user,
        title=title,
        mimetype="application/pdf",
        raindrop_id=raindrop["id"],
        raindrop_created=raindrop["created"],
    )
    if source:
        doc.source = source

    if raindrop["tags"]:
        all_tags = list(map(str.title, raindrop["tags"]))

        doc.tags = [tag for tag in all_tags if "*" not in tag]

        tags_rating = [tag for tag in all_tags if "*" in tag]
        if tags_rating:
            doc.quality = Rating(len(tags_rating[0])).value

    # Save the new "document"
    with open(raindrop["__path_pdf"], "rb") as fd:
        doc.file_.put(fd, content_type="application/pdf")
    doc.save()

    print("•", end="", flush=True)

    return source


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

    parser.add_argument(
        "-a",
        "--action",
        help="Action to be performed, ie. import (default), delete",
        default="import",
    )

    ARGS = parser.parse_args()

    # Validate..
    assert ARGS.database in ("production", "local")
    assert ARGS.action in ("import", "delete")

    main(ARGS)
