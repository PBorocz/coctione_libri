#!/usr/bin/env bash
set -o errexit

echo "Creating a virtual env for both poetry and our packages..."
python -m venv venv

echo "Updating pip ;-)..."
./venv/bin/python -m pip install --upgrade pip

echo "Installing updated version of poetry into our virtual env..."
./venv/bin/pip install poetry==1.5.1

echo "Installing our production (ie. non-dev) packages..."
cd /opt/render/project/src
./venv/bin/poetry install --without dev

echo "Done"
