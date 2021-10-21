#!/bin/bash

# Github actions has all: 'py37,py38,py39,py310'
# For faster runtime, you can choose subset here
TOX_ENVS='py37'

# Optionally run ruby based markdown lint locally
# After installing ruby:
#   gem install mdl -v 0.11.0
#   mdl --style '.mdl-style.rb' .
RUN_MDL=false

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
if [ "$RUN_MDL" = true ] ; then
    echo "mdl:"
    mdl --style '.mdl-style.rb' .
fi