#!/bin/bash

# Github actions has all: 'py37,py38,py39,py310'
# For faster runtime, you can choose subset here
TOX_ENVS='py37'

echo "tox:"
tox -e $TOX_ENVS --parallel
echo "isort:"
isort --settings-file pyproject.toml .
echo "black:"
black --config=pyproject.toml .
echo "pflake8:"
pflake8 --config=pyproject.toml
echo "codespell:"
codespell ./src ./tests