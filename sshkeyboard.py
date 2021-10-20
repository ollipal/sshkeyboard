import asyncio
import concurrent.futures
import fcntl
import os
import sys
import termios
import tty
import traceback

from contextlib import contextmanager
from time import time, sleep
from types import SimpleNamespace

# Global state

# Makes sure only listener can be started at a time
_running = False
# Makes sure listener stops if error has been raised
# inside thread pool excecutor or asyncio task
_has_not_raised_errors = True

# All possible characters here:
# https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/prompt_toolkit/input/ansi_escape_sequences.py
# Listener does not support modifier keys for now
_ANSI_CHAR_TO_READABLE = {
    # 'Regular' characters
    "\x1b": "esc",
    "\x7f": "backspace",
    "\x1b[2~": "insert",
    "\x1b[3~": "delete",
    "\x1b[5~": "pageup",
    "\x1b[6~": "pagedown",
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


def listen_keyboard(
    on_press,
    on_release,
    until="esc",
    sequental=False,
    delay_second_char=0.75,
    delay_others=0.05,
    lower=True,
    debug=False,
    thread_pool_max_workers=None,
):
    assert not _running, "Only one listener allowed at a time"
    assert _has_not_raised_errors, "Should not have errors in the beginning already"
    assert not asyncio.iscoroutinefunction(
        on_press
    ), "Use listen_keyboard_async if you have async on_press"
    assert not asyncio.iscoroutinefunction(
        on_release
    ), "Use listen_keyboard_async if you have async on_release"

    asyncio.run(
        listen_keyboard_async(
            on_press,
            on_release,
            until,
            sequental,
            delay_second_char,
            delay_others,
            lower,
            debug,
            thread_pool_max_workers,
            sleep=None,
        )
    )


async def listen_keyboard_async(
    on_press,
    on_release,
    until="esc",
    sequental=False,
    delay_second_char=0.75,
    delay_others=0.05,
    lower=True,
    debug=False,
    thread_pool_max_workers=None,
    sleep=0.05,
):
    global _running
    global _has_not_raised_errors
    assert not _running, "Only one listener allowed at a time"
    assert _has_not_raised_errors, "Should not have errors in the beginning already"
    
    _running = True
    _has_not_raised_errors = True

    # Create thread pool executor only if it will get used
    if not asyncio.iscoroutinefunction(on_press) or not asyncio.iscoroutinefunction(
        on_release
    ):
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=thread_pool_max_workers
        )

    state = SimpleNamespace(
        press_time=time(),
        initial_press_time=time(),
        previous="",
        current="",
    )

    def done(task):
        if not task.cancelled() and task.exception() is not None:
            ex = task.exception()
            traceback.print_exception(type(ex), ex, ex.__traceback__)
            global _has_not_raised_errors
            _has_not_raised_errors = False

    async def on_press_callback(key):
        if sequental:
            if asyncio.iscoroutinefunction(on_press):
                await on_press(key)
            else:
                on_press(key)
        else:
            if asyncio.iscoroutinefunction(on_press):
                task = asyncio.create_task(on_press(key))
                task.add_done_callback(done)
            else:
                future = executor.submit(on_press, key)
                future.add_done_callback(done)

    async def on_release_callback(key):
        if sequental:
            if asyncio.iscoroutinefunction(on_release):
                await on_release(key)
            else:
                on_release(key)
        else:
            if asyncio.iscoroutinefunction(on_release):
                task = asyncio.create_task(on_release(key))
                task.add_done_callback(done)
            else:
                future = executor.submit(on_release, key)
                future.add_done_callback(done)

    with _raw(sys.stdin), _nonblocking(sys.stdin):
        while _has_not_raised_errors:
            should_stop, state = await _react_to_key_input(
                state,
                on_press_callback,
                on_release_callback,
                until,
                delay_second_char,
                delay_others,
                lower,
                debug,
            )
            if should_stop:
                break
            if sleep is not None:
                await asyncio.sleep(sleep)

    executor.shutdown()
    _running = False


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


def _is_ansi(char):
    rep = repr(char)
    return len(rep) >= 2 and rep[1] == "\\" and rep[2] == "x"


def _read_and_parse_ansi(char):
    char += _read_chars(5)
    if char in _ANSI_CHAR_TO_READABLE:
        return _ANSI_CHAR_TO_READABLE[char], char
    else:
        return None, char


async def _react_to_key_input(
    state, on_press, on_release, until, delay_second_char, delay_others, lower, debug
):
    # Read next character
    state.current = _read_chars(1)

    # Skip and continue if read failed
    if state.current is None:
        return False, state

    # Handle any character
    elif state.current != "":
        # Read more if ansi character, skip and continue if unknown
        if _is_ansi(state.current):
            state.current, raw = _read_and_parse_ansi(state.current)
            if state.current is None:
                if debug:
                    print(f"Non-supported ansi char: {repr(raw)}")
                return False, state
        # Change some character representations to readable strings
        elif state.current in _CHAR_TO_READABLE:
            state.current = _CHAR_TO_READABLE[state.current]

        # Make lower case if requested
        if lower:
            state.current = state.current.lower()

        # Stop if until character has been read
        if state.current == until:
            state.previous = ""
            state.current = ""
            return True, state

        # Release state.previous if new pressed
        if state.previous is not "" and state.current != state.previous:
            await on_release(state.previous)

        # Press if new character, update state.previous
        if state.current != state.previous:
            await on_press(state.current)
            state.initial_press_time = time()
            state.previous = state.current

        # Update press time
        if state.current == state.previous:
            state.press_time = time()

    # Handle empty
    # - Release the state.previous character if nothing is read
    # and enough time has passed
    # - The second character comes slower than the rest on terminal
    elif state.previous is not "" and (
        time() - state.initial_press_time > delay_second_char
        and time() - state.press_time > delay_others
    ):
        await on_release(state.previous)
        state.previous = state.current

    return False, state


if __name__ == "__main__":

    def press(key):
        print(f"'{key}' pressed")

    def release(key):
        print(f"'{key}' released")

    # Sync version
    print("Listening keyboard, sync version, press 'esc' to exit")
    listen_keyboard(press, release)

    # Async version
    print("\nListening keyboard, async version, press 'esc' to exit")
    asyncio.run(listen_keyboard_async(press, release))
