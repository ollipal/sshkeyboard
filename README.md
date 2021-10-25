# sshkeyboard

The only keyboard event callback library that works in _all_ unix
environments.

It does not depend on X server, uinput, root access (sudo) or
any external dependencies.

This means it is suitable even when taking a SSH connection (hence the name),
using with headless computers/servers or for example inside Windows Subsystem
for Linux (WSL 2). One good use case is Raspberry Pi with Raspberry
Pi OS Lite.

Supports asyncio and sequential/concurrent callback modes. For Python versions
above 3.7.

[Documentation](https://sshkeyboard.readthedocs.io)  
[Github source](https://github.com/ollipal/sshkeyboard)  
[Reference](https://sshkeyboard.readthedocs.io/en/latest/reference.html)

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

listen_keyboard(on_press=press, on_release=release)
```

Output:

```text
$ python example.py
'a' pressed
'a' released
```

## How it works

The library works without X server and uinput because it calls the events
based on characters parsed from
[sys.stdin](https://docs.python.org/3/library/sys.html#sys.stdin). This is
done with [fcntl](https://docs.python.org/3/library/fcntl.html) and
[termios](https://docs.python.org/3/library/termios.html) standard library
modules.

This behaviour allows it to work where other libraries do not, but it comes
with some **limitations**, mainly:

1. Holding two keys down at the same time does not work, the library
   releases the first key when the second key is pressed
2. Some keys do not write to `sys.stdin` when pressed, such as Ctrl, Shift,
   Caps Lock, Alt and Windows/Command/Super key. That is why this library does
   not attempt to parse those even if they could be technically be parsed in
   some cases
3. `termios` and `fcntl` are not supported on Windows (except on WSL / WSL 2).
   If you figure out a workaround, please make a pull request!

## Advanced use

### Sequential mode

Normally this library allows `on_press` and `on_release` callback to be run
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

and pressing `a`, `s` and `d` keys will log:

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
listen_keyboard(on_press=press, sequential=True)
```

will log:

```text
'a' pressed
'a' slept
's' pressed
's' slept
'd' pressed
'd' slept
```

### Asyncio mode

You can also use asynchronous functions as `on_press`/`on_release` callbacks
with `listen_keyboard_async` function.

`listen_keyboard_async` also exposes a new optional parameter `sleep` that can
be used to change automatic `asyncio.sleep` times between async callbacks.

```python
import asyncio
from sshkeyboard import listen_keyboard_async

async def press(key):
    print(f"'{key}' pressed")
    await asyncio.sleep(3)
    print(f"'{key}' slept")

listen_keyboard_async(on_press=press, sleep=0.05)
```

> **NOTE** remember to use `await asyncio.sleep(...)` in async callbacks instead
of `time.sleep(...)` or the timings will fail:

### Mixing asynchronous and concurrent callbacks

This library also supports mixing asynchronous and concurrent callbacks
with `listen_keyboard_async` function.

```python
import asyncio
import time
from sshkeyboard import listen_keyboard_async

async def press(key):
    print(f"'{key}' pressed")
    await asyncio.sleep(3)
    print(f"'{key}' press slept")

def release(key):
    print(f"'{key}' relased")
    time.sleep(3)
    print(f"'{key}' release slept")

listen_keyboard_async(on_press=press, on_release=release)
```

Pressing `a` and `s` will log:

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
listen_keyboard_async(on_press=press, on_release=release, sequential=True)
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

> **NOTE** remember to use `await asyncio.sleep(...)` in async callbacks instead
of `time.sleep(...)` or the timings will fail:

### Stop listening

You can stop listening by simply calling `stop_listening()` from the callback
or from some other function:

```python
from sshkeyboard import listen_keyboard, stop_listening

def press(key):
    print(f"'{key}' pressed")
    stop_listening()

listen_keyboard(on_press=press)
```

You can also change the key that ends the listening by giving `until`
parameter, which defaults to `esc`:

```python
# ...
listen_keyboard(on_press=press, until="z")
```

### Troubleshooting

If some keys do not seem to register correctly, try turning the debug mode on.
This will add logs if some keys are skipped intentionally:

```python
# ...
listen_keyboard(on_press=press, debug=True)
```

If one key press causes multiple callbacks or if releasing happens too slowly,
you can try to tweak the default timing parameters:

```python
# ...
listen_keyboard(on_press=press, delay_second_char=0.75, delay_other_chars=0.05)
```

### More

Check the
[reference](https://sshkeyboard.readthedocs.io/en/latest/reference.html)
for more functions and  parameters:

- `lower` parameter
- `max_thread_pool_workers` parameter
- `listen_keyboard_async_manual` function

## Comparison to other Python keyboard libraries

Some other keyboard libraries work by reading proper keycodes from the system.

This means that they usually require either `X server` or `uinput`, so they do
not work over SSH. But this means they do not have the same limitations as
this library.

They also support more features such as pressing the keys instead of just
reacting to user input.

I have good experiences from:

- [pynput](https://pynput.readthedocs.io/en/latest/)
- [boppreh/keyboard](https://github.com/boppreh/keyboard) (requires sudo!)

## Development

In this section I'll explain how to build the documentation and run the
[pre-commit script](https://github.com/ollipal/sshkeyboard/blob/main/pre-commit)
locally. The pre-commit script handles running tests, formatting and
linting before each commit. These also run on
[Github Actions](https://github.com/ollipal/sshkeyboard/blob/main/.github/workflows/main.yml)
.

This helps if you want to create
[a pull request](https://github.com/ollipal/sshkeyboard/pulls)
or if you just want to try things out.

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

To build the documentation or run the pre-commit / pipelines locally, you need
to install the development dependencies by running:

```text
pip install -r dev-requirements.txt
```

### Documentation

To build the documentation locally, first change into `docs/` directory:

```text
cd docs
```

Then simply call

```text
make html
```

Now you shold have a new `docs/build/` directory, and you can open
`<your-clone-location>/sshkeyboard/docs/build/html/index.html` from your browser.

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

## Running pre-commit script / pipelines locally

You can run the **tests** (
[tox](https://tox.wiki/en/latest/index.html) +
[pytest](https://docs.pytest.org)), **formatting** (
[black](https://black.readthedocs.io/en/stable/),
[isort](https://pycqa.github.io/isort/)) and **linting** (
[pflake8](https://github.com/csachs/pyproject-flake8),
[pep8-naming](https://github.com/PyCQA/pep8-naming),
[codespell](https://github.com/codespell-project/codespell),
[markdownlint](https://github.com/markdownlint/markdownlint)) simply by
running:

```text
./pre-commit
```

If you want to automatically run these when you call `git commit`, copy the
script into `.git/hooks` directory:

```text
cp pre-commit .git/hooks
```

> **NOTE**: this process does not run `markdownlint` by default as it
requires Ruby to be installed. If you want to run that locally as well,
install Ruby and install markdown lint with `gem install mdl -v 0.11.0`.
Then from `pre-commit` change `RUN_MDL=false` to `RUN_MDL=true`. (You need to
copy the file again into `.git/hooks` if you did that earlier)
