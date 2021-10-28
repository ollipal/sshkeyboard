# sshkeyboard

The only keyboard event callback library that works _everywhere_, even when
used through an [SSH](https://en.wikipedia.org/wiki/Secure_Shell) connection
(hence the name).

It works with headless computers and servers, or for example inside Windows
Subsystem for Linux (WSL 2). One good use case is controlling Raspberry Pi
based robots or RC cars through SSH. Note that this library can also be used
locally without an SSH connection.

It does not depend on X server, uinput, root access (sudo) or
any external dependencies.

Supports [asyncio](https://docs.python.org/3/library/asyncio.html) and
sequential/concurrent callback modes. For Python 3.6+.

[Documentation](https://sshkeyboard.readthedocs.io) -
[Github source](https://github.com/ollipal/sshkeyboard) -
[PyPI](https://pypi.org/project/sshkeyboard/) -
[Reference](https://sshkeyboard.readthedocs.io/en/latest/reference.html) -
[![Downloads](https://static.pepy.tech/personalized-badge/sshkeyboard?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads)](https://pepy.tech/project/sshkeyboard)

## Quick start

Installation:

```text
pip install sshkeyboard
```

Simple example to fire events when a key is pressed or released.
`esc` key ends listening by default:

```python
from sshkeyboard import listen_keyboard

def press(key):
    print(f"'{key}' pressed")

def release(key):
    print(f"'{key}' released")

listen_keyboard(
    on_press=press,
    on_release=release,
)
```

Output:

```text
$ python example.py
'a' pressed
'a' released
```

## How it works

The sshkeyboard library works without
[X server](https://en.wikipedia.org/wiki/X_Window_System)
and [uinput](https://www.kernel.org/doc/html/v4.12/input/uinput.html).

On Unix based systems (such as Linux, macOS) it works by parsing characters
from [sys.stdin](https://docs.python.org/3/library/sys.html#sys.stdin). This
is done with [fcntl](https://docs.python.org/3/library/fcntl.html) and
[termios](https://docs.python.org/3/library/termios.html) standard library
modules.

On Windows [msvcrt](https://docs.python.org/3/library/msvcrt.html) standard
library module is used to read user input. The Windows support is still new,
so please create [an issue](https://github.com/ollipal/sshkeyboard/issues)
if you run into problems.

This behaviour allows it to work where other libraries like
[pynput](#comparison-to-other-keyboard-libraries) or
[keyboard](#comparison-to-other-keyboard-libraries) do not work, but
it comes with some **limitations**, mainly:

1. Holding multiple keys down at the same time does not work, the library
   releases the previous keys when a new one is pressed. Releasing keys also
   happens after a short delay, and some key presses can get lost if the same
   key gets spammed fast.
2. Some keys do not write to `sys.stdin` when pressed, such as `Ctrl`,
   `Shift`, `Caps Lock`, `Alt` and `Windows`/`Command`/`Super` key. That is
   why this library does not attempt to parse those even if they could be
   technically be parsed in some cases

## Advanced use

### Sequential mode

Normally this library allows `on_press` and `on_release` callbacks to be run
concurrently. This means that by running:

```python
import time
from sshkeyboard import listen_keyboard

def press(key):
    print(f"'{key}' pressed")
    time.sleep(3)
    print(f"'{key}' slept")

listen_keyboard(on_press=press)
```

and pressing `"a"`, `"s"` and `"d"` keys will log:

```text
'a' pressed
's' pressed
'd' pressed
'a' slept
's' slept
'd' slept
```

But sometimes you don't want to allow the callbacks to overlap, then
you should set `sequential` parameter to `True`:

```python
# ...
listen_keyboard(
    on_press=press,
    sequential=True,
)
```

Then pressing `"a"`, `"s"` and `"d"` keys will log:

```text
'a' pressed
'a' slept
's' pressed
's' slept
'd' pressed
'd' slept
```

### Asyncio

You can also use asynchronous functions as `on_press` / `on_release` callbacks
with `listen_keyboard`:

```python
import asyncio
from sshkeyboard import listen_keyboard

async def press(key):
    print(f"'{key}' pressed")
    await asyncio.sleep(3)
    print(f"'{key}' slept")

listen_keyboard(on_press=press)
```

> **NOTE** remember to use `await asyncio.sleep(...)` in async callbacks
instead of `time.sleep(...)` or the timings will fail:

### Mixing asynchronous and concurrent callbacks

`listen_keyboard` also supports mixing asynchronous and concurrent callbacks:

```python
import asyncio
import time
from sshkeyboard import listen_keyboard

async def press(key):
    print(f"'{key}' pressed")
    await asyncio.sleep(3)
    print(f"'{key}' press slept")

def release(key):
    print(f"'{key}' relased")
    time.sleep(3)
    print(f"'{key}' release slept")

listen_keyboard(
    on_press=press,
    on_release=release,
)
```

Here pressing `"a"` and `"s"` will log:

```text
'a' pressed
'a' relased
's' pressed
's' relased
'a' press slept
's' press slept
'a' release slept
's' release slept
```

And with `sequential=True`:

```python
# ...
listen_keyboard(
    on_press=press,
    on_release=release,
    sequential=True,
)
```

will log:

```text
'a' pressed
'a' press slept
'a' relased
'a' release slept
's' pressed
's' press slept
's' relased
's' release slept
```

> **NOTE** remember to use `await asyncio.sleep(...)` in async callbacks
instead of `time.sleep(...)` or the timings will fail:

### Stop listening

You can change the key that ends the listening by giving `until` parameter,
which defaults to `"esc"`:

```python
# ...
listen_keyboard(
    on_press=press,
    until="space",
)
```

You also can manually stop listening by calling `stop_listening()` from the
callback or from some other function:

```python
from sshkeyboard import listen_keyboard, stop_listening

def press(key):
    print(f"'{key}' pressed")
    if key == "z":
        stop_listening()

listen_keyboard(on_press=press)
```

`until` can be also set to `None`. This means that listening ends only with
`stop_listening()` or if an error has been raised.

### Troubleshooting

If some keys do not seem to register correctly, try turning the debug mode on.
This will add logs if some keys are skipped intentionally:

```python
# ...
listen_keyboard(
    on_press=press,
    debug=True,
)
```

If one key press causes multiple `on_press` / `on_release` callbacks or if
releasing happens too slowly, you can try to tweak the default timing
parameters:

```python
# ...
listen_keyboard(
    on_press=press,
    delay_second_char=0.75,
    delay_other_chars=0.05,
)
```

### More

Check out the full
[reference](https://sshkeyboard.readthedocs.io/en/latest/reference.html)
for more functions and parameters such as:

- `lower` parameter
- `sleep` parameter
- `max_thread_pool_workers` parameter
- `listen_keyboard_manual` function

Direct links to functions:

- [listen_keyboard](https://sshkeyboard.readthedocs.io/en/latest/reference.html#sshkeyboard.listen_keyboard)
- [stop_listening](https://sshkeyboard.readthedocs.io/en/latest/reference.html#sshkeyboard.stop_listening)
- [listen_keyboard_manual](https://sshkeyboard.readthedocs.io/en/latest/reference.html#sshkeyboard.listen_keyboard_manual)

## Development

This sections explains how to build the documentation and how to run the
[pre-commit script](https://github.com/ollipal/sshkeyboard/blob/main/pre-commit)
locally. This helps if you want to create
[a pull request](https://github.com/ollipal/sshkeyboard/pulls)
or if you just want to try things out.

Building the documentations allows you to build all of the files served on the
[documentation](https://sshkeyboard.readthedocs.io) site locally.

The
[pre-commit script](https://github.com/ollipal/sshkeyboard/blob/main/pre-commit)
handles running tests, formatting and
linting before each Git commit. These same checks also run automatically on
[Github Actions](https://github.com/ollipal/sshkeyboard/blob/main/.github/workflows/main.yml).

Start by cloning this library, and change directory to the project root:

```text
git clone git@github.com:ollipal/sshkeyboard.git
cd sshkeyboard
```

Optionally, create and activate a virtual environment at the root of the
project (you might need to use `python3` keyword instead of `python`):

```text
python -m venv .env
source .env/bin/activate
```

(Later you can deactivate the virtual environment with: `deactivate`)

To build the documentation or run the pre-commit script locally, you need
to install the development dependencies:

```text
pip install -r dev-requirements.txt
```

### Documentation

To build the documentation locally, first change into `docs/` directory:

```text
cd docs
```

Then to build the documentation, call:

```text
make html
```

Now you should have a new `docs/build/` directory, and you can open
`<your-clone-path>/sshkeyboard/docs/build/html/index.html` from your browser.

You can force the rebuild by running:

```text
rm -rf build/ && make html
```

You can change the documentation content by changing `README.md` or files from
`src/` or `docs/source/`. If you are mainly changing contents from
`docs/source/`, you can enable automatic re-building by running:

```text
sphinx-autobuild ./source/ ./build/html/
```

### Running the pre-commit script

You can run the **tests**
([tox](https://tox.wiki/en/latest/index.html),
[pytest](https://docs.pytest.org)), **formatting**
([black](https://black.readthedocs.io/en/stable/),
[isort](https://pycqa.github.io/isort/)) and **linting**
([pflake8](https://github.com/csachs/pyproject-flake8),
[pep8-naming](https://github.com/PyCQA/pep8-naming),
[codespell](https://github.com/codespell-project/codespell),
[markdownlint](https://github.com/markdownlint/markdownlint)) simply by
executing:

```text
./pre-commit
```

Now if you want to automatically run these when you call `git commit`, copy
the script into `.git/hooks/` directory:

```text
cp pre-commit .git/hooks
```

> **NOTE**: this process does not run `markdownlint` by default as it
requires [Ruby](https://www.ruby-lang.org/en/) to be installed. If you want
to run `markdownlint` locally as well,
[install Ruby](https://www.ruby-lang.org/en/documentation/installation/)
and install markdown lint with `gem install mdl -v 0.11.0`. Then from
`pre-commit` change `RUN_MDL=false` to `RUN_MDL=true`. (You need to copy the
file again into `.git/hooks/` if you did that earlier)

## Comparison to other keyboard libraries

The other keyboard libraries work by reading proper keycodes from the system.

This means that they usually require either
[X server](https://en.wikipedia.org/wiki/X_Window_System) or
[uinput](https://www.kernel.org/doc/html/v4.12/input/uinput.html), so they do
not work over SSH. But this means they do not have the same
[limitations](#how-it-works) as this library.

They usually can also support more features such as pressing the keys instead
of just reacting to user input.

I have good experiences from these libraries:

- [pynput](https://pynput.readthedocs.io/en/latest/)
- [keyboard](https://github.com/boppreh/keyboard) (requires sudo)