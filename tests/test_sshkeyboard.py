from contextlib import contextmanager

import pytest

import sshkeyboard

i = -1
return_chars = ("a", "a", "b", "")


def setup_testing():
    @contextmanager
    def _raw(stream):
        yield

    @contextmanager
    def _nonblocking(stream):
        yield

    def _read_chars(amount):
        global i
        i += 1
        return return_chars[i % len(return_chars)]

    sshkeyboard._raw = _raw
    sshkeyboard._nonblocking = _nonblocking
    sshkeyboard._read_chars = _read_chars


setup_testing()


def empty(key):
    pass


def stops(key):
    sshkeyboard.stop_listening()


def returns_char(key):
    if key not in return_chars:
        raise RuntimeError(f"Not correct char {key}")
    sshkeyboard.stop_listening()


def press_listen(key):
    try:
        sshkeyboard.listen_keyboard(empty, empty)
        raise RuntimeError("Error not raised")
    except AssertionError:
        pass
    sshkeyboard.stop_listening()


def press_listen_async(key):
    try:
        sshkeyboard.listen_keyboard_async(empty, empty)
        raise RuntimeError("Error not raised")
    except AssertionError:
        pass
    sshkeyboard.stop_listening()


def test_listen_returns_char():
    # listen_keyboard press
    sshkeyboard.listen_keyboard(returns_char, empty)
    # listen_keyboard release
    sshkeyboard.listen_keyboard(empty, returns_char)
    # listen_keyboard press
    sshkeyboard.listen_keyboard_async(returns_char, empty)
    # listen_keyboard release
    sshkeyboard.listen_keyboard_async(empty, returns_char)


def test_multiple_listens_raises_error():
    # listen_keyboard inside listen_keyboard fails
    sshkeyboard.listen_keyboard(press_listen, empty)
    # listen_keyboard_async inside listen_keyboard fails
    sshkeyboard.listen_keyboard(press_listen_async, empty)
    # listen_keyboard inside listen_keyboard_async fails
    sshkeyboard.listen_keyboard_async(press_listen, empty)
    # listen_keyboard_async inside listen_keyboard_async fails
    sshkeyboard.listen_keyboard_async(press_listen_async, empty)


def test_callback_parameters():
    def too_many_params_without_default(key, key2):
        pass

    def no_params():
        pass

    def ok1(key):
        pass

    def ok2(custom_key_name):
        pass

    def ok3(key="a"):
        pass

    def ok4(key="a", key2="s"):
        pass

    with pytest.raises(AssertionError):
        sshkeyboard.listen_keyboard(too_many_params_without_default, stops)

    with pytest.raises(AssertionError):
        sshkeyboard.listen_keyboard(no_params, stops)

    sshkeyboard.listen_keyboard(ok1, stops)
    sshkeyboard.listen_keyboard(ok2, stops)
    sshkeyboard.listen_keyboard(ok3, stops)
    sshkeyboard.listen_keyboard(ok4, stops)


# TODO add tests for: sleeps and print orders, throwing errors, assertions
