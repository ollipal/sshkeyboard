"""sshkeyboard"""

__version__ = "0.0.1"

import asyncio
import concurrent.futures
import fcntl
import os
import sys
import termios
import traceback
import tty
from contextlib import contextmanager
from time import time
from types import SimpleNamespace

# Global state

# Makes sure only listener can be started at a time
_running = False
# Makes sure listener stops if error has been raised
# inside thread pool executor or asyncio task or
# stop_listening() has been called
_should_run = True

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
    on_press=None,
    on_release=None,
    until="esc",
    sequental=False,
    delay_second_char=0.75,
    delay_others=0.05,
    lower=True,
    debug=False,
    thread_pool_max_workers=None,
):
    """Listen for keyboard events and fire callback functions

    Args:
        on_press (function, optional): function that gets called when key gets
            pressed. Defaults to None.
        on_release (function, optional): function that gets called when key
            gets released. Defaults to None.
        until (str, optional): a key that will end keyboard listening.
            Defaults to "esc".
        sequental (bool, optional): defines whether callback can be started
            while the previous is still running. Defaults to False.
        delay_second_char (float, optional): The timeout that depends on
            terminal. Defaults to 0.75.
        delay_others (float, optional): Another timeoput. Defaults to 0.05.
        lower (bool, optional): whether the callback 'key' parameter gets
            turned intop lower key or not. Defaults to True.
        debug (bool, optional): print debug messages. Defaults to False.
        thread_pool_max_workers (None|int, optional): Define the number of
            ThreadPoolWrokers, None means that a default value will get used.
            Defaults to None.
    """

    assert not asyncio.iscoroutinefunction(
        on_press
    ), "Use listen_keyboard_async if you have async on_press"
    assert not asyncio.iscoroutinefunction(
        on_release
    ), "Use listen_keyboard_async if you have async on_release"

    asyncio.run(
        listen_keyboard_async_manual(
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


def listen_keyboard_async(
    on_press=None,
    on_release=None,
    until="esc",
    sequental=False,
    delay_second_char=0.75,
    delay_others=0.05,
    lower=True,
    debug=False,
    thread_pool_max_workers=None,
    sleep=0.05,
):
    asyncio.run(
        listen_keyboard_async_manual(
            on_press,
            on_release,
            until,
            sequental,
            delay_second_char,
            delay_others,
            lower,
            debug,
            thread_pool_max_workers,
            sleep,
        )
    )


async def listen_keyboard_async_manual(
    on_press=None,
    on_release=None,
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
    global _should_run
    assert not _running, "Only one listener allowed at a time"
    assert _should_run, "Should not have errors in the beginning already"
    assert (
        on_press is not None or on_release is not None
    ), "Either on_press or on_release should be defined"

    _running = True
    _should_run = True

    # Create thread pool executor only if it will get used
    executor = None
    if not asyncio.iscoroutinefunction(
        on_press
    ) or not asyncio.iscoroutinefunction(on_release):
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=thread_pool_max_workers
        )

    def done(task):
        if not task.cancelled() and task.exception() is not None:
            ex = task.exception()
            traceback.print_exception(type(ex), ex, ex.__traceback__)
            global _should_run
            _should_run = False

    def callback(cb_function):
        async def _callback(key):
            if cb_function is None:
                return

            if sequental:
                if asyncio.iscoroutinefunction(cb_function):
                    await cb_function(key)
                else:
                    cb_function(key)
            else:
                if asyncio.iscoroutinefunction(cb_function):
                    task = asyncio.create_task(cb_function(key))
                    task.add_done_callback(done)
                else:
                    future = executor.submit(cb_function, key)
                    future.add_done_callback(done)

        return _callback

    # Package parameters into namespaces so they are easier to pass around
    # Options do not change
    options = SimpleNamespace(
        on_press_callback=callback(on_press),
        on_release_callback=callback(on_release),
        until=until,
        delay_second_char=delay_second_char,
        delay_others=delay_others,
        lower=lower,
        debug=debug,
    )
    # State does change
    state = SimpleNamespace(
        press_time=time(),
        initial_press_time=time(),
        previous="",
        current="",
    )

    # Listen
    with _raw(sys.stdin), _nonblocking(sys.stdin):
        while _should_run:
            state = await _react_to_input(state, options)
            if sleep is not None:
                await asyncio.sleep(sleep)

    # Cleanup
    if executor is not None:
        executor.shutdown()
    _running = False
    _should_run = True


def stop_listening():
    global _should_run
    _should_run = False


# Raw and _nonblocking inspiration from:
# http://ballingt.com/_nonblocking-stdin-in-python-3/
@contextmanager
def _raw(stream):
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


# '\x' at the start is a good indicator for ansi character
def _is_ansi(char):
    rep = repr(char)
    return len(rep) >= 2 and rep[1] == "\\" and rep[2] == "x"


def _read_and_parse_ansi(char):
    char += _read_chars(5)
    if char in _ANSI_CHAR_TO_READABLE:
        return _ANSI_CHAR_TO_READABLE[char], char
    else:
        return None, char


async def _react_to_input(state, options):
    # Read next character
    state.current = _read_chars(1)

    # Skip and continue if read failed
    if state.current is None:
        return state

    # Handle any character
    elif state.current != "":
        # Read more if ansi character, skip and continue if unknown
        if _is_ansi(state.current):
            state.current, raw = _read_and_parse_ansi(state.current)
            if state.current is None:
                if options.debug:
                    print(f"Non-supported ansi char: {repr(raw)}")
                return state
        # Change some character representations to readable strings
        elif state.current in _CHAR_TO_READABLE:
            state.current = _CHAR_TO_READABLE[state.current]

        # Make lower case if requested
        if options.lower:
            state.current = state.current.lower()

        # Stop if until character has been read
        if state.current == options.until:
            stop_listening()
            return state

        # Release state.previous if new pressed
        if state.previous != "" and state.current != state.previous:
            await options.on_release_callback(state.previous)

        # Press if new character, update state.previous
        if state.current != state.previous:
            await options.on_press_callback(state.current)
            state.initial_press_time = time()
            state.previous = state.current

        # Update press time
        if state.current == state.previous:
            state.press_time = time()

    # Handle empty
    # - Release the state.previous character if nothing is read
    # and enough time has passed
    # - The second character comes slower than the rest on terminal
    elif state.previous != "" and (
        time() - state.initial_press_time > options.delay_second_char
        and time() - state.press_time > options.delay_others
    ):
        await options.on_release_callback(state.previous)
        state.previous = state.current

    return state


if __name__ == "__main__":

    def press(key):
        print(f"'{key}' pressed")

    def release(key):
        print(f"'{key}' released")

    # Sync version
    print("listening_keyboard() running, press keys, and press 'esc' to exit")
    listen_keyboard(on_press=press, on_release=release)

    # Async version
    print(
        "\nlistening_keyboard_async() running, press keys,"
        "and press 'esc' to exit"
    )
    listen_keyboard_async(on_press=press, on_release=release)
    # ^this is the same as
    # asyncio.run(listen_keyboard_async_manual(press, release))
