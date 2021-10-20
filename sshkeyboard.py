import asyncio
import fcntl
import sys
import os
import tty
import termios
from time import time
from contextlib import contextmanager


async def listen_async(
    on_press,
    on_release,
    until="esc",
    lower=True,
    debug=False,
    sleep=0.05,
):
    with _raw(sys.stdin), _nonblocking(sys.stdin):
        while _should_listen(on_press, on_release, until, lower, debug):
            await asyncio.sleep(sleep)


def listen_sync(
    on_press,
    on_release,
    until="esc",
    lower=True,
    debug=False,
):
    with _raw(sys.stdin), _nonblocking(sys.stdin):
        while _should_listen(on_press, on_release, until, lower, debug):
            pass


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
_ANSI_START = "\x1b"
# All possible characters here: https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/prompt_toolkit/input/ansi_escape_sequences.py
# This supports only the simple ones for now
_ANSI_CHARS = {
    # 'Regular' characters
    "\x1b": "esc",
    "\x7f": "backspace",
    "\x1b[2~": "insert",
    "\x1b[3~": "delete",
    "\x1b[5~": "page_up",
    "\x1b[6~": "page_down",
    "\x1b[H": "home",
    "\x1b[F": "end",
    "\x1b[A": "up",
    "\x1b[B": "down",
    "\x1b[C": "right",
    "\x1b[D": "left",
    "\x1bOP": "f1",
    "\x1bOQ": "f2",
    "\x1bOR": "f3",
    "\x1bOS": "f4",
    "\x1b[15~": "f5",
    "\x1b[17~": "f6",
    "\x1b[18~": "f7",
    "\x1b[19~": "f8",
    "\x1b[20~": "f9",
    "\x1b[21~": "f10",
    "\x1b[23~": "f11",
    "\x1b[24~": "f12",
    "\x1b[25~": "f13",
    "\x1b[26~": "f14",
    "\x1b[28~": "f15",
    "\x1b[29~": "f16",
    "\x1b[31~": "f17",
    "\x1b[32~": "f18",
    "\x1b[33~": "f19",
    "\x1b[34~": "f20",
    # Special/duplicate:
    # Tmux, Emacs
    "\x1bOH": "home",
    "\x1bOF": "end",
    "\x1bOA": "up",
    "\x1bOB": "down",
    "\x1bOC": "right",
    "\x1bOD": "left",
    # Rrvt
    "\x1b[1~": "home",
    "\x1b[4~": "end",
    "\x1b[11~": "f1",
    "\x1b[12~": "f2",
    "\x1b[13~": "f3",
    "\x1b[14~": "f4",
    # Linux console
    "\x1b[[A": "f1",
    "\x1b[[B": "f2",
    "\x1b[[C": "f3",
    "\x1b[[D": "f4",
    "\x1b[[E": "f5",
    # Xterm
    "\x1b[1;2P": "f13",
    "\x1b[1;2Q": "f14",
    "\x1b[1;2S": "f16",
    "\x1b[15;2~": "f17",
    "\x1b[17;2~": "f18",
    "\x1b[18;2~": "f19",
    "\x1b[19;2~": "f20",
    "\x1b[20;2~": "f21",
    "\x1b[21;2~": "f22",
    "\x1b[23;2~": "f23",
    "\x1b[24;2~": "f24",
}
_CHAR_TO_READABLE = {
    "\t": "tab",
    "\n": "enter",
    " ": "space",
}


def _is_ansi(char):
    rep = repr(char)
    return len(rep) >= 2 and rep[1] == "\\" and rep[2] == "x"


def _read_and_parse_ansi(char):
    char += _read_chars(5)
    if char in _ANSI_CHARS:
        return _ANSI_CHARS[char], char
    else:
        return None, char


def _should_listen(on_press, on_release, until, lower, debug):
    global _previous
    global _press_time
    global _initial_press_time
    global _current

    # Read next character
    _current = _read_chars(1)

    # Skip and continue if read failed
    if _current is None:
        return True

    # Handle any character
    elif _current != "":
        # Read more if ansi character, skip and continue if unknown
        if _is_ansi(_current):
            _current, raw = _read_and_parse_ansi(_current)
            if _current is None:
                if debug:
                    print(f"Non-supported ansi char: {repr(raw)}")
                return True
        # Change some character representations to readable strings
        elif _current in _CHAR_TO_READABLE:
            _current = _CHAR_TO_READABLE[_current]

        # Make lower case if requested
        if lower:
            _current = _current.lower()

        # Stop if until character has been read
        if _current == until:
            _previous = ""
            _current = ""
            return False

        # Release _previous if new pressed
        if _previous is not "" and _current != _previous:
            on_release(_previous)

        # Press if new character, update _previous
        if _current != _previous:
            on_press(_current)
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
        on_release(_previous)
        _previous = _current

    return True


if __name__ == "__main__":

    def press(key):
        print(f"'{key}' pressed")

    def release(key):
        print(f"'{key}' released")

    # Sync version
    print("Listening keyboard, sync version, press 'esc' to exit")
    listen_sync(press, release)

    # Async version
    print("\nListening keyboard, async version, press 'esc' to exit")
    asyncio.run(listen_async(press, release))
