"""Holds character mapping constants."""
from typing import Final

# Readable representations for selected ansi characters
# All possible ansi characters here:
# https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/prompt_toolkit/input/ansi_escape_sequences.py
# Listener does not support modifier keys for now


class CharMaps:
    """Holds character mapping constants."""

    UNIX_ANSI_CHAR_TO_READABLE: Final = {
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

    WIN_CHAR_TO_READABLE: Final = {
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
    CHAR_TO_READABLE: Final = {
        "\t": "tab",
        "\n": "enter",
        "\r": "enter",
        " ": "space",
    }

    WIN_SPECIAL_CHAR_STARTS: Final = {"\x1b", "\x08", "\x00", "\xe0"}
    WIN_REQUIRES_TWO_READS_STARTS: Final = {"\x00", "\xe0"}
