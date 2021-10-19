import asyncio
import fcntl
import sys
import os
import time
import tty
import termios
from contextlib import contextmanager
 
# raw and nonblocking inspiration from: http://ballingt.com/nonblocking-stdin-in-python-3/
@contextmanager
def raw(stream):
    fd = stream.fileno()
    original_stty = termios.tcgetattr(stream)
    try:
        tty.setcbreak(stream)
        yield
    finally:
        termios.tcsetattr(stream, termios.TCSANOW, original_stty)
 
@contextmanager
def nonblocking(stream):
    fd = stream.fileno()
    orig_fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    try:
        fcntl.fcntl(fd, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)
        yield
    finally:
        fcntl.fcntl(fd, fcntl.F_SETFL, orig_fl)

def listen(on_press, on_release):
    previous = None
    current = None
    press_time = time.time()
    initial_press_time = time.time()
    with raw(sys.stdin), nonblocking(sys.stdin):
        while True:
            try:
                c = sys.stdin.read(1)
                if c != '':
                    if c == '\x1b': # handle arrows and Esc
                        character = sys.stdin.read(1) + sys.stdin.read(1)
                        if character == "[A":
                            c = "up"
                        elif character == "[B":
                            c = "down"
                        elif character == "[C":
                            c = "right"
                        elif character == "[D":
                            c = "left"
                        else:
                            break # Esc -> exit
                    if previous is not None and c != previous:
                        on_release(repr(previous))
                    if c != previous:
                        on_press(repr(c))
                        initial_press_time = time.time()
                        current = c
                    if c == current:
                        press_time = time.time()
                    previous = c
                elif previous is not None and (time.time() - initial_press_time > 0.75 and time.time() - press_time > 0.05): # the second character comes slower than the rest
                    on_release(repr(previous))
                    previous = None
            except IOError:
                pass
 
if __name__ == "__main__":
    def press(key):
        print(f"{key} pressed")
 
    def release(key):
        print(f"{key} released")
 
    listen(press, release)
