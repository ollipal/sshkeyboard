"""Holds context managers."""

# Raw and _nonblocking inspiration from:
# http://ballingt.com/_nonblocking-stdin-in-python-3/
import os
from contextlib import contextmanager
from platform import system
from typing import IO, Any, Generator, List

_is_windows = system().lower() == "windows"

if not _is_windows:
    import fcntl
    import termios
    import tty


@contextmanager
def raw(stream: IO[Any]) -> Generator[None, None, None]:
    """Raw stdin from steam."""
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
            stream,
            termios.TCSANOW,  # type: ignore
            original_stty,  # type: ignore
        )


@contextmanager
def nonblocking(stream: IO[Any]) -> Generator[None, None, None]:
    """Non-blocking stdin from steam."""
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
