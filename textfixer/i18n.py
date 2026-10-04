"""UI localization.

Strings live in textfixer/locales/<code>.py as a flat STRINGS dict. English is the
reference and the fallback for missing keys. To add a language: copy locales/en.py,
translate the values (keep the {placeholders}), register it in locales/__init__.py.
tests/test_i18n.py checks that every locale has the same keys and placeholders.
"""

from .locales import LANGUAGES

DEFAULT = "en"
_current = DEFAULT


def set_language(code: str) -> None:
    global _current
    _current = code if code in LANGUAGES else DEFAULT


def current() -> str:
    return _current


def languages() -> dict[str, str]:
    """{code: native name} for the language picker."""
    return {code: name for code, (name, _) in LANGUAGES.items()}


def t(key: str, /, **kwargs) -> str:  # positional-only: "{key}" is a valid placeholder
    text = LANGUAGES[_current][1].get(key) or LANGUAGES[DEFAULT][1].get(key) or key
    return text.format(**kwargs) if kwargs else text
