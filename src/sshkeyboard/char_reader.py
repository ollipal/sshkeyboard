"""Platform independent char reader."""
from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from platform import system
from typing import Any, Optional

from . import char_maps as cmap

_is_windows = system().lower() == "windows"

if _is_windows:
    import msvcrt


class CharReader(ABC):
    @abstractmethod
    def read(self, debug: bool = False) -> Optional[str]:
        ...


class WinCharReader(CharReader):
    def read(self, debug: bool = False) -> Optional[str]:
        # Return if nothing to read
        if not msvcrt.kbhit():
            return ""

        char = msvcrt.getwch()
        if char in cmap.WIN_SPECIAL_CHAR_STARTS:
            # Check if requires one more read
            if char in cmap.WIN_REQUIRES_TWO_READS_STARTS:
                char += msvcrt.getwch()

            if char in cmap.WIN_CHAR_TO_READABLE:
                return cmap.WIN_CHAR_TO_READABLE[char]
            else:
                if debug:
                    print(f"Non-supported win char: {repr(char)}")
                return None

        # Change some character representations to readable strings
        elif char in cmap.CHAR_TO_READABLE:
            char = cmap.CHAR_TO_READABLE[char]

        return char


class UnixCharReader(CharReader):
    def read(self, debug: bool = False) -> Optional[str]:
        raw: Any
        char: Optional[str] = self._read_unix_stdin(1)

        # Skip and continue if read failed
        if char is None:
            return None

        # Handle any character
        elif char != "":
            # Read more if ansi character, skip and continue if unknown
            if self._is_unix_ansi(char):
                char, raw = self._read_and_parse_unix_ansi(char)
                if char is None:
                    if debug:
                        print(f"Non-supported ansi char: {repr(raw)}")
                    return None
            # Change some character representations to readable strings
            elif char in cmap.CHAR_TO_READABLE:
                char = cmap.CHAR_TO_READABLE[char]

        return char

    def _read_unix_stdin(self, amount: int) -> str:
        try:
            return sys.stdin.read(amount)
        except IOError:
            return ""

    # '\x' at the start is a good indicator for ansi character
    def _is_unix_ansi(self, char: str):
        rep = repr(char)
        return len(rep) >= 2 and rep[1] == "\\" and rep[2] == "x"

    def _read_and_parse_unix_ansi(self, char: str):
        char += self._read_unix_stdin(5)
        if char in cmap.UNIX_ANSI_CHAR_TO_READABLE:
            return cmap.UNIX_ANSI_CHAR_TO_READABLE[char], char
        else:
            return None, char


class CharReaderFactory:
    @staticmethod
    def create() -> CharReader:
        if system().lower() == "windows":
            return WinCharReader()
        return UnixCharReader()
