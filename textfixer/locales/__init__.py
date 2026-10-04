"""Registered UI languages: code -> (native name, strings).

Imports are explicit on purpose: PyInstaller only bundles modules it can see imported.
"""

from . import en, ru

LANGUAGES: dict[str, tuple[str, dict[str, str]]] = {
    "en": ("English", en.STRINGS),
    "ru": ("Русский", ru.STRINGS),
}
