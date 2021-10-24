# sshkeyboard

The only keyboard that works in _all_ unix environments

No dependencies

Works without sudo and without x server

But... it has some drawbacks due to the limitations

My own usecase is to use this when I want to have some keyboard
callback through ssh on machines
without x server or when I'm using

-- relation to pynput and keyboard

-- graph

## How it works

It captures, and parses the terminal input in real time,
and fires callbacks based on the user input

Supports normal syncronous, concurrent and asyncrynous modes!

## why does not support windows

Requires [fcntl](https://docs.python.org/3/library/fcntl.html) module.

Anyways in my experience other libraries know how to handle Windows

## Development

### Before commiting / pipelines

If you want to check locally that the Github pipelines work, first install
dependencies with

```
pip install -r dev-requirements.txt
```

Then you can run the pipelines locally with

```
./pre-commit
```

If you want to automatically run these when commiting, copy the
script into .git/hooks directory:

```
cp pre-commit .git/hooks/
```

Note: this process does not run markdown lint as it requires Ruby to be
installed. If you want to run that locally as well, install Ruby and install
markdown lint with `gem install mdl -v 0.11.0`. Then from `pre-commit`
change `RUN_MDL=false` to `RUN_MDL=true`. (You need to copy the file again
into .git/hooks if you did that earlier)

### Documentation

python3 -m venv .env
source .env/bin/activate
pip install -r dev-requirements.txt
cd docs
make html
sphinx-autobuild ./source/ ./build/html/
deactivate