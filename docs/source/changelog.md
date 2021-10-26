# Changelog

## 2.0.1

Release to get the PyPI page content updated

- README wording improved
- pyproject.toml more tags added

## 2.0.0

`listen_keyboard` supports now async callbacks directly

- `listen_keyboard_async` removed as it is no longer required
- `listen_keyboard_async_manual` renamed to `listen_keyboard_manual`

## 1.0.1

Release to get the PyPI page content updated

- README updated to be more mobile friendly

## 1.0.0

Well tested version ready for wider use:

- Support now expanded to Python 3.6 also
- `until` parameter can now be set to None to turn the feature off
- Assertions check now that the operating system and Python versions
  are supported during the runtime
- README rewritten

## 0.1.1

Readme updates

- Readme, keywords and tags added to pyproject.toml
- Readme codeblock higlighting fixed

## 0.1.0

Initial release for testing. Main functionality working but requires more testing.

Supported functions:

- listen_keyboard
- listen_keyboard_async
- listen_keyboard_async_manual

`listen_keyboard_async` supported parameters:

- on_press
- on_release
- until
- sequential
- delay_second_char
- delay_other_chars
- lower
- debug
- max_thread_pool_workers
- sleep