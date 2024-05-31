[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)


# Coctione-Libri

Several years ago, our family needed a single place to store links and pdf's of our most commonly cooked recipes (and those we'd /like/ to cook).

After trying Evernote, Notion and a few others, I picked Raindrop due to its pricing model, simple tagging scheme and multi-platform support. However, after a few years, I became disenchanted (inability to export my own data, ui inconsistencies et cetera).

Now...how hard could it *really* be to store a set of pdf's with some meta-data access through a simple web front-end? Thus was `Coctione Libri` (literally *cooking books* in Latin) conceived and developed.

## Salient Features:

- Uses [MongoDB](https://www.mongodb.com/) for both storage (of both meta data *and* uploaded files).

- Uses [MongoEngine](http://mongoengine.org/) for python bindings.

- Uses [Flask / gunicorn](https://flask.palletsprojects.com/en/3.0.x/) for web server.

- Uses [HTMX](https://htmx.org/) for the few dynamic interactions required.

- Supports user authentication (and registration) with [Flask-Login](https://github.com/maxcountryman/flask-login).

- Supports "simple" multi-tenancy by storing meta-data on a per-user basis.

- Support multiple document categories. Right now, I store PDF's on behalf of recipes, cooking /skills/ and cooking /products/.

- Customised fields for each document include (all optional):
  - URL to source
  - Name of the source (eg. NewYorkTimes-Recipes)
  - Any number of tags
  - Scoring metrics obo "Quality" of the respective dish and "Complexity" associated with it's preparation.
  - Any number of "dates cooked" (I like to track when and how often I've cooked something).

- My personal production deployment is hosted on [Render](https://render.com) (primarily due to it's trivially simple deployment model and reasonable pricing model) with database hosting on [Atlas](https://www.mongodb.com/products/platform/atlas-database).

## Screen Shot

![Home Page](https://github.com/PBorocz/coctione_libri/blob/trunk/app/static/images/readme_use/MainScreen-2024-05-31.png)

## Repository

I've made this repository public simply to provide anyone else with a sample to learn from and/or build upon. Provided with *NO* guarantees beyond *works for me*!
