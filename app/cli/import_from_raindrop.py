#!/usr/bin/env python
"""Run either delete or import of a set of pdf's to our collection."""
import argparse
import os
import time
import tomllib
from collections import defaultdict
from pathlib import Path
from pprint import pprint

import tomli_w
from mongoengine.context_managers import switch_collection

import app.constants as c
from app import create_app
from app.cli import setup_logging
from app.models.documents import Documents, Rating, get_user_documents
from app.models.users import Users


def main(args: argparse.Namespace):
    """Do our action, ie. either delete or import."""
    setup_logging(True)

    # Setup our application/db connection
    os.environ["DB_ENV"] = args.database
    app = create_app(setup_logging=False)
    with app.app_context():
        if args.action == "import_existing_pdfs":
            import_existing_pdfs()
        elif args.action == "import_new_pdfs":
            import_new_pdfs()
        elif args.action == "delete":
            delete_()


def delete_():
    user = Users.objects.get(email="peter.borocz@gmail.com")
    count = 0
    with switch_collection(Documents, get_user_documents(user)) as user_documents:
        for doc in user_documents.objects(user=user):
            doc.file_.delete()
            doc.delete()
            count += 1
    print(f"Deleted {count} documents for {user.id=}")


def import_new_pdfs():
    user = Users.objects.get(email="peter.borocz@gmail.com")

    path_toml = Path("__raindrop_data__/RaindropPDF-New")
    with open(path_toml / Path("recipes.toml"), "rb") as fh_toml:
        raindrops = tomllib.load(fh_toml)

    raindrops = {str(raindrop.get("id")): raindrop for raindrop in raindrops.get("links")}

    sources = defaultdict(int)
    print("Importing..", end="")

    for path_pdf in path_toml.glob("*.pdf"):
        pieces = path_pdf.name.split("|")
        length = 3
        if len(pieces) != length:
            print(f"Invalid pdf name: {path_pdf}")
            continue
        (id, _, source) = pieces

        if id not in raindrops:
            print(f"Can't find pdf id in raindrops: {id}")
            continue

        raindrop = raindrops[id]

        raindrop["file_name"] = path_pdf.name
        raindrop["source"] = source.replace(".pdf", "")
        raindrop["__path_pdf"] = path_pdf

        __import_raindrop(user, raindrop)

        sources[raindrop["source"]] += 1

    print()
    print(f"Imported {sum(list(sources.values()))} total files from the following sources:")
    pprint(dict(sources))


def import_existing_pdfs():
    user = Users.objects.get(email="peter.borocz@gmail.com")

    path_toml = Path("__raindrop_data__/RaindropPDF-Existing")
    with open(path_toml / Path("recipes.toml"), "rb") as fh_toml:
        raindrops = tomllib.load(fh_toml)

    sources = defaultdict(int)
    non_documents = []
    print("Importing..", end="")
    for raindrop in raindrops.get("export"):
        path_pdf = path_toml / Path(f"{raindrop['id']}.pdf")

        # Filter down to only entries for whom we ALREADY have pdfs
        if raindrop["type"] != "RaindropType.document":
            non_documents.append(raindrop)
            continue

        if not path_pdf.exists():
            print(f'\nSkipping: {raindrop.get("file").get("name")}')
            continue

        raindrop["__path_pdf"] = path_pdf

        name = raindrop.get("file").get("name")
        if "|" in name:
            raindrop["title"], raindrop["source"] = name.split("|")
            sources[raindrop["source"]] += 1
        else:
            raindrop["title"] = name

        __import_raindrop(user, raindrop)

    print()
    print(f"Imported {sum(list(sources.values()))} total files from the following sources:")
    pprint(dict(sources))

    # Write out the documents that still have to be converted
    if True:
        with open(path_toml / Path("recipes_non_documents.toml"), "wb") as fh_toml:
            tomli_w.dump({"links": non_documents}, fh_toml)
        print(f"Wrote {len(non_documents)} non-document entries to recipes_non_documents.TOML")

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
        print(f"Wrote {len(non_documents)} non-document entries to recipes_non_documents.HTML")


def __import_raindrop(user, raindrop: dict) -> str:
    # Parse name<|source> -> name, source

    with switch_collection(Documents, get_user_documents(user)) as user_documents:
        doc = user_documents(
            user=user,
            title=raindrop["title"],
        )
        if "source" in raindrop:
            doc.source = raindrop["source"]

        if raindrop["tags"]:
            all_tags = list(map(str.title, raindrop["tags"]))

            doc.tags = [tag for tag in all_tags if "*" not in tag]

            tags_rating = [tag for tag in all_tags if "*" in tag]
            if tags_rating:
                doc.quality = Rating(len(tags_rating[0])).value

        # Save the new "document"
        with open(raindrop["__path_pdf"], "rb") as fd:
            doc.file_.put(fd, fileName=raindrop.get("__path_pdf").name, contentType="application/pdf")
        doc.save()

    print("•", end="", flush=True)

    time.sleep(0.25)


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
        help="Action to be performed, ie. import_existing_pdfs, import_new_pdfs, delete",
        default="import",
    )

    ARGS = parser.parse_args()

    # Validate..
    assert ARGS.database in ("production", "local")
    assert ARGS.action.startswith("import") or ARGS.action.startswith("delete")

    main(ARGS)
