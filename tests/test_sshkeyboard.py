import sys
import asyncio

sys.path.append("../src")
from sshkeyboard import listen_keyboard, listen_keyboard_async, stop_listening

print("Press 'a' multiple times to run the manual tests")


def empty(key):
    pass


def returns_a(key):
    if key == "a":
        print("SUCCESS")
    else:
        print("FAIL")
    stop_listening()


def press_listen(key):
    try:
        listen_keyboard(empty, empty)
        print("FAIL")
    except AssertionError:
        print("SUCCESS")
    stop_listening()


def press_listen_async(key):
    try:
        asyncio.run(listen_keyboard_async(empty, empty))
        print("FAIL")
    except AssertionError:
        print("SUCCESS")
    stop_listening()


# Return value
print("listen_keyboard pressing 'a' returns 'a'")
listen_keyboard(returns_a, empty)
print("listen_keyboard releasing 'a' returns 'a'")
listen_keyboard(empty, returns_a)
print("listen_keyboard_async pressing 'a' returns 'a'")
asyncio.run(listen_keyboard_async(returns_a, empty))
print("listen_keyboard_async releasing 'a' returns 'a'")
asyncio.run(listen_keyboard_async(empty, returns_a))

# Multiple running failure
print("listen_keyboard inside listen_keyboard fails")
listen_keyboard(press_listen, empty)
print("listen_keyboard_async inside listen_keyboard fails")
listen_keyboard(press_listen_async, empty)
print("listen_keyboard inside listen_keyboard_async fails")
asyncio.run(listen_keyboard_async(press_listen, empty))
print("listen_keyboard_async inside listen_keyboard_async fails")
asyncio.run(listen_keyboard_async(press_listen_async, empty))

# TODO, assert async fails listen, test sleeps, schedule orders etc.
