# sshkeyboard

The only keyboard event callback  library that works in _all_ unix environments.

This means that it does not depend on X server, uinput, root access (sudo) or
any third party libraries or programs.

For Python 3.7+.

[Documentation](https://sshkeyboard.readthedocs.io)

## Quick start

Installation:

```
pip install sshkeyboard
```

Simple examble to fire events when a key is pressed or released
`esc` ends listening by default:

```python
from sshkeyboard import listen_keyboard


def press(key):
    print(f"'{key}' pressed")

def release(key):
    print(f"'{key}' released")

listen_keyboard(on_press=press, on_release=release)
```
Output:
```
$ python example.py
'a' pressed
'a' released
```

## Limitations

But... it has some drawbacks due to the limitations

My own usecase is to use this when I want to have some keyboard
callback through ssh on machines
without x server or when I'm using

-- relation to pynput and keyboard

-- graph

Some keys do not fire

## Comparison to other Python keyboard libraries

-

## Advanced use

- sequental
- async (also manual version)
- on_press fires multiple times / on_release is too slow
- end listening on some other key
- key output looks wrong (debug, lower, skips modifier keys as they cause confusion)

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