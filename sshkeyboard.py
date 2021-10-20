import asyncio
import fcntl
import sys
import os
import tty
import termios
from time import time
from contextlib import contextmanager

# Raw and _nonblocking inspiration from: http://ballingt.com/_nonblocking-stdin-in-python-3/
@contextmanager
def _raw(stream):
    fd = stream.fileno()
    original_stty = termios.tcgetattr(stream)
    try:
        tty.setcbreak(stream)
        yield
    finally:
        termios.tcsetattr(stream, termios.TCSANOW, original_stty)


@contextmanager
def _nonblocking(stream):
    fd = stream.fileno()
    orig_fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    try:
        fcntl.fcntl(fd, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)
        yield
    finally:
        fcntl.fcntl(fd, fcntl.F_SETFL, orig_fl)


async def listen_async(on_press, on_release, sleep=0.05):
    with _raw(sys.stdin), _nonblocking(sys.stdin):
        while _should_listen(on_press, on_release):
            await asyncio.sleep(sleep)


def listen_sync(on_press, on_release):
    with _raw(sys.stdin), _nonblocking(sys.stdin):
        while _should_listen(on_press, on_release):
            pass

def _read_chars(amount):
    try:
        return sys.stdin.read(amount)
    except IOError:
        return None


# Global variables to share state between sync and async versions.
# Really the only option to access each loop cleanly.
_press_time = time()
_initial_press_time = time()
_previous = ""
_current = ""
_LONG_CHARS = {
    "\x1b[A": "up",
    "\x1b[B": "down",
    "\x1b[C": "right",
    "\x1b[D": "left",
    "\x1b": "esc",
}



def _should_listen(on_press, on_release, debug=False):
    global _previous
    global _press_time
    global _initial_press_time
    global _current

    _current = _read_chars(1)

    # Skip and continue if read failed
    if _current is None:
        return True

    # Handle any character
    elif _current != "":
        # Parse supported long characters that require more reads
        if _current == "\x1b":
            _current += _read_chars(2)
            if _current in _LONG_CHARS:
                _current = _LONG_CHARS[_current]
            elif debug:
                print(f"Non-supported long char: {repr(_current)}")

        # Release _previous if new pressed
        if _previous is not "" and _current != _previous:
            on_release(repr(_previous))

        # Press if new character, update _previous
        if _current != _previous:
            on_press(repr(_current))
            _initial_press_time = time()
            _previous = _current

        # Update press time
        if _current == _previous:
            _press_time = time()

    # Handle empty
    # - Release the _previous character if nothing is read
    # and enough time has passed
    # - The second character comes slower than the rest on terminal
    elif _previous is not "" and (
        time() - _initial_press_time > 0.75 and time() - _press_time > 0.05
    ):
        on_release(repr(_previous))
        _previous = _current

    return True


if __name__ == "__main__":

    def press(key):
        print(f"{key} pressed")

    def release(key):
        print(f"{key} released")

    # Async version
    # asyncio.run(listen_async(press, release))

    # Sync version
    listen_sync(press, release)
