"""Key handler module."""


# Readable representations for selected ansi characters
# All possible ansi characters here:
# https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/prompt_toolkit/input/ansi_escape_sequences.py
# Listener does not support modifier keys for now
import asyncio
import concurrent.futures
import os
import sys
from contextlib import contextmanager
from dataclasses import InitVar, dataclass
from platform import system
from time import time
from typing import (
    IO,
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    TypeAlias,
    Union,
)

try:
    from ._asyncio_run_backport_36 import run36
except ImportError:  # this allows local testing: python __init__.py
    from _asyncio_run_backport_36 import run36  # type:ignore

_is_windows = system().lower() == "windows"

if _is_windows:
    import msvcrt
else:
    import fcntl
    import termios
    import tty

Key: TypeAlias = str
CallbackFunction: TypeAlias = Callable[[Key], Any]

_UNIX_ANSI_CHAR_TO_READABLE = {
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

_WIN_CHAR_TO_READABLE = {
    "\x1b": "esc",
    "\x08": "backspace",
    "àR": "insert",
    "àS": "delete",
    "àI": "pageup",
    "àQ": "pagedown",
    "àG": "home",
    "àO": "end",
    "àH": "up",
    "àP": "down",
    "àM": "right",
    "àK": "left",
    "\x00;": "f1",
    "\x00<": "f2",
    "\x00=": "f3",
    "\x00>": "f4",
    "\x00?": "f5",
    "\x00@": "f6",
    "\x00A": "f7",
    "\x00B": "f8",
    "\x00C": "f9",
    "\x00D": "f10",
    # "": "f11", ?
    "à†": "f12",
}

# Some non-ansi characters that need a readable representation
_CHAR_TO_READABLE = {
    "\t": "tab",
    "\n": "enter",
    "\r": "enter",
    " ": "space",
}

_WIN_SPECIAL_CHAR_STARTS = {"\x1b", "\x08", "\x00", "\xe0"}
_WIN_REQUIRES_TWO_READS_STARTS = {"\x00", "\xe0"}


def _is_python_36():
    return sys.version_info.major == 3 and sys.version_info.minor == 6


def _done(
    task: Union[asyncio.Future[Any], concurrent.futures.Future[None]]
) -> None:
    if not task.cancelled():
        ex = task.exception()
        if ex is not None:
            raise ex
            # traceback.print_exception(type(ex), ex, ex.__traceback__)


# Raw and _nonblocking inspiration from:
# http://ballingt.com/_nonblocking-stdin-in-python-3/
@contextmanager
def _raw(stream: IO[Any]):
    # Not required on windows
    if _is_windows:
        yield
        return

    original_stty: List[Any] = termios.tcgetattr(stream)  # type: ignore
    try:
        tty.setcbreak(stream)  # type: ignore
        yield
    finally:
        termios.tcsetattr(  # type: ignore
            stream, termios.TCSANOW, original_stty  # type: ignore
        )


@contextmanager
def _nonblocking(stream: IO[Any]):
    # Not required on windows
    if _is_windows:
        yield
        return

    fd = stream.fileno()
    orig_fl = fcntl.fcntl(fd, fcntl.F_GETFL)  # type: ignore
    try:
        fcntl.fcntl(fd, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)  # type: ignore
        yield
    finally:
        fcntl.fcntl(fd, fcntl.F_SETFL, orig_fl)  # type: ignore


class MultipleListenerError(Exception):
    pass


def _read_char(debug: bool) -> Optional[str]:
    if _is_windows:
        return _read_char_win(debug)
    else:
        return _read_char_unix(debug)


def _read_char_win(debug: bool) -> Optional[str]:
    # Return if nothing to read
    if not msvcrt.kbhit():
        return ""

    char = msvcrt.getwch()
    if char in _WIN_SPECIAL_CHAR_STARTS:
        # Check if requires one more read
        if char in _WIN_REQUIRES_TWO_READS_STARTS:
            char += msvcrt.getwch()

        if char in _WIN_CHAR_TO_READABLE:
            return _WIN_CHAR_TO_READABLE[char]
        else:
            if debug:
                print(f"Non-supported win char: {repr(char)}")
            return None

    # Change some character representations to readable strings
    elif char in _CHAR_TO_READABLE:
        char = _CHAR_TO_READABLE[char]

    return char


def _read_unix_stdin(amount: int) -> str:
    try:
        return sys.stdin.read(amount)
    except IOError:
        return ""


# '\x' at the start is a good indicator for ansi character
def _is_unix_ansi(char: str):
    rep = repr(char)
    return len(rep) >= 2 and rep[1] == "\\" and rep[2] == "x"


def _read_and_parse_unix_ansi(char: str):
    char += _read_unix_stdin(5)
    if char in _UNIX_ANSI_CHAR_TO_READABLE:
        return _UNIX_ANSI_CHAR_TO_READABLE[char], char
    else:
        return None, char


def _read_char_unix(debug: bool) -> Optional[str]:
    raw: Any
    char: Optional[str] = _read_unix_stdin(1)

    # Skip and continue if read failed
    if char is None:
        return None

    # Handle any character
    elif char != "":
        # Read more if ansi character, skip and continue if unknown
        if _is_unix_ansi(char):
            char, raw = _read_and_parse_unix_ansi(char)
            if char is None:
                if debug:
                    print(f"Non-supported ansi char: {repr(raw)}")
                return None
        # Change some character representations to readable strings
        elif char in _CHAR_TO_READABLE:
            char = _CHAR_TO_READABLE[char]

    return char


@dataclass
class KeyListener:
    """Key listener class.

    Args:
        on_press: Function that gets called when a key is pressed. The
            function takes the pressed key as parameter. Defaults to None.
        on_release: Function that gets called when a key is released. The
            function takes the released key as parameter. Defaults to None.
        until: A key that will end keyboard listening. None means that
            listening will stop only when :func:`~sshkeyboard.stop_listening`
            has been called or an error has been raised. Defaults to "esc".
        sequential: If enabled, callbacks will be forced to happen one by
            one instead of concurrently or asynchronously. Defaults to False.
        delay_second_char: The timeout between first and second character when
            holding down a key. Depends on terminal and is used for parsing
            the input. Defaults to 0.75.
        delay_other_chars: The timeout between all other characters when
            holding down a key. Depends on terminal and is used for parsing
            the input. Defaults to 0.05.
        lower: If enabled, the callback 'key' parameter gets turned into lower
            case key even if it was upper case, for example "A" -> "a".
            Defaults to True.
        debug: Print debug messages. Defaults to False.
        max_thread_pool_workers: Define the number of workers in
            ThreadPoolExecutor, None means that a default value will get used.
            Will get ignored if sequential=True. Defaults to None.
        sleep: asyncio.sleep() amount between attempted keyboard input reads.
            Defaults to 0.01.
    """

    on_press_func: InitVar[Optional[CallbackFunction]] = None
    on_release_func: InitVar[Optional[CallbackFunction]] = None
    until: Optional[str] = "esc"
    sequential: bool = False
    delay_second_char: float = 0.75
    delay_other_chars: float = 0.05
    lower: bool = True
    debug: bool = False
    max_thread_pool_workers: Optional[int] = None
    sleep: float = 0.01

    def __post_init__(
        self,
        on_press_func: Optional[CallbackFunction],
        on_release_func: Optional[CallbackFunction],
    ) -> None:
        # Check the system
        if sys.version_info < (3, 6):
            raise RuntimeError(
                "sshkeyboard requires Python version 3.6+, you have "
                f"{sys.version_info.major}.{sys.version_info.minor}"
            )
        self.on_press = self._callback(on_press_func)
        self.on_release = self._callback(on_release_func)
        self.executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self._running = False
        # Create thread pool executor only if it will get used
        # executor = None
        if not self.sequential and (
            not asyncio.iscoroutinefunction(self.on_press)
            or not asyncio.iscoroutinefunction(self.on_release)
        ):
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_thread_pool_workers
            )

    def _callback(
        self, cb_function: Optional[CallbackFunction]
    ) -> Callable[[str], Coroutine[Any, Any, Any]]:
        async def _cb(key: Key):
            if cb_function is None:
                return

            if self.sequential or self.executor is None:
                if asyncio.iscoroutinefunction(cb_function):
                    if isinstance(cb_function, Awaitable):
                        await cb_function(key)
                else:
                    cb_function(key)
            else:
                if asyncio.iscoroutinefunction(cb_function):
                    task: asyncio.Task[None] = asyncio.create_task(
                        cb_function(key)
                    )
                    task.add_done_callback(_done)
                else:
                    future = self.executor.submit(cb_function, key)
                    future.add_done_callback(_done)

        return _cb

    @property
    def running(self) -> bool:
        return self._running

    def listen_keyboard(
        self,
    ) -> None:

        """Listen for keyboard events and fire `on_press` and `on_release`
         callback functions

        Supports asynchronous callbacks also.

        Blocks the thread until the key in `until` parameter has been pressed,
        an error has been raised or :func:`~sshkeyboard.stop_listening` has
        been called.

        Simple example with asynchronous and regular callbacks:

        .. code-block:: python

            from sshkeyboard import listen_keyboard

            async def press(key):
                print(f"'{key}' pressed")

            def release(key):
                print(f"'{key}' released")

            listen_keyboard(
                on_press=press,
                on_release=release,
            )
        """

        coro = self.listen_keyboard_manual()

        if _is_python_36():
            run36(coro)
        else:
            asyncio.run(coro)

    async def listen_keyboard_manual(
        self,
    ) -> None:
        """The same as :func:`~sshkeyboard.listen_keyboard`, but now the
        awaiting must be handled by the caller

        .. code-block:: python

            from sshkeyboard import listen_keyboard_manual

            # ...
            asyncio.run(listen_keyboard_manual(...))

        is the same as

        .. code-block:: python

            from sshkeyboard import listen_keyboard

            # ...
            listen_keyboard(...)

        (Python version 3.6 which does not have `asyncio.run` is handled
        differently internally)

        Has the same parameters as :func:`~sshkeyboard.listen_keyboard`
        """
        if self.running:
            raise MultipleListenerError("Listener is already running.")
        self._running = True
        if self.on_press is None and self.on_release is None:
            raise ValueError("Either on_press or on_release should be defined")
        # Listen
        with _raw(sys.stdin), _nonblocking(sys.stdin):
            state: Dict[str, Any] = {}
            while self.running:
                state = await self._react_to_input(**state)
                await asyncio.sleep(self.sleep)

        self._clean_up()

    async def _react_to_input(
        self,
        press_time: float = time(),
        initial_press_time: float = time(),
        previous: str = "",
        current: Optional[str] = "",
    ) -> Dict[str, Any]:
        # Read next character
        current = _read_char(self.debug)

        # Skip and continue if read failed
        if current is None:
            return {
                "press_time": press_time,
                "initial_press_time": initial_press_time,
                "previous": previous,
                "current": current,
            }

        # Handle any character
        elif current != "":

            # Make lower case if requested
            if self.lower:
                current = current.lower()

            # Stop if until character has been read
            if self.until is not None and current == self.until:
                self.stop_listening()
                return {
                    "press_time": press_time,
                    "initial_press_time": initial_press_time,
                    "previous": previous,
                    "current": current,
                }

            # Release previous if new pressed
            if previous != "" and current != previous:
                await self.on_release(previous)
                # Weirdly on_release fires too late on Windows unless there is
                # an extra sleep here when sequential=False...
                if _is_windows and not self.sequential:
                    await asyncio.sleep(self.sleep)

            # Press if new character, update state.previous
            if current != previous:
                await self.on_press(current)
                initial_press_time = time()
                previous = current

            # Update press time
            if current == previous:
                press_time = time()

        # Handle empty
        # - Release the state.previous character if nothing is read
        # and enough time has passed
        # - The second character comes slower than the rest on terminal
        elif previous != "" and (
            time() - initial_press_time > self.delay_second_char
            and time() - press_time > self.delay_other_chars
        ):
            await self.on_release(previous)
            previous = current

        return {
            "press_time": press_time,
            "initial_press_time": initial_press_time,
            "previous": previous,
            "current": current,
        }

    def _clean_up(self):
        if self.executor is not None:
            self.executor.shutdown()
        self._running = False

    def stop_listening(self) -> None:
        """Stops the ongoing keyboard listeners

        Can be called inside the callbacks or from outside. Does not do
        anything if listener is not running.

        Example to stop after some condition is met,
        ("z" pressed in this case):

        .. code-block:: python

            from sshkeyboard import listen_keyboard, stop_listening

            def press(key):
                print(f"'{key}' pressed")
                if key == "z":
                    stop_listening()

            listen_keyboard(on_press=press)
        """
        if self.running:
            self._clean_up()
