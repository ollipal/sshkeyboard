"""Key handler module."""
import asyncio
import concurrent.futures
import sys
from dataclasses import InitVar, dataclass
from platform import system
from time import time
from typing import TypeAlias, TypeVar

try:
    # Import PEP-agnostic type hints from "beartype.typing", a stand-in
    # replacement for the standard "typing" module providing improved forward
    # compatibility with future Python releases.
    # type ignore for pylance error, opened issue:
    # https://github.com/beartype/beartype/issues/126
    from beartype import beartype  # type: ignore

    # TypeAlias, seems to cause issues with pylance
    # opened issue https://github.com/beartype/beartype/issues/127
    # from beartype.typing import (
    #     Any,
    #     Awaitable,
    #     Callable,
    #     Coroutine,
    #     Dict,
    #     Optional,
    #     Union,
    # )
except ModuleNotFoundError:
    from typing import (
        Any,
        Awaitable,
        Callable,
        Coroutine,
        Dict,
        Optional,
        Union,
    )

    FuncT = TypeVar("FuncT", bound=Callable[..., Any])

    def noop_dec(func: FuncT) -> FuncT:
        return func

    beartype: Callable[..., Any] = noop_dec  # type: ignore[no-redef]


from .char_reader import CharReaderFactory
from .context_managers import nonblocking, raw
from .errors import MultipleListenerError

try:
    from ._asyncio_run_backport_36 import run36
except ImportError:  # this allows local testing: python __init__.py
    from _asyncio_run_backport_36 import run36  # type:ignore


Key: TypeAlias = str
CallbackFunction: TypeAlias = Callable[[Key], Any]
_is_windows = system().lower() == "windows"


# runtime type check, similar to original assert but more robust.
@beartype
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
        self.char_reader = CharReaderFactory.create()
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
            def _done(
                task: Union[
                    asyncio.Future[Any], concurrent.futures.Future[None]
                ]
            ) -> None:
                if not task.cancelled():
                    ex = task.exception()
                    if ex is not None:
                        raise ex

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

        # if python is version 3.6
        if sys.version_info.major == 3 and sys.version_info.minor == 6:
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
        with raw(sys.stdin), nonblocking(sys.stdin):
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
        current = self.char_reader.read(self.debug)

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
