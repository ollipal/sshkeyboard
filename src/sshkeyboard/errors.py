"""Module that holds custom error classes."""


class MultipleListenerError(Exception):
    """An error if multiple listeners are trying to run at same time."""

    pass
