"""Locale consistency: same keys and {placeholders} everywhere, every used key exists."""

import re
import string
from pathlib import Path

from textfixer.locales import LANGUAGES

ROOT = Path(__file__).resolve().parent.parent
# Keys built dynamically with f-strings in settings_ui.py
DYNAMIC = {
    "settings.hk.{key}": ["fix", "fix_and_send", "layout"],
    "settings.hk.{key}.hint": ["fix", "fix_and_send", "layout"],
    "settings.timing.{name}": ["select_delay", "copy_timeout", "enter_copy_timeout", "paste_settle", "clipboard_restore"],
    "settings.timing.{name}.hint": ["select_delay", "copy_timeout", "enter_copy_timeout"],
}


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def used_keys() -> set[str]:
    keys = set()
    for path in (ROOT / "textfixer").glob("*.py"):
        for key in re.findall(r"""\bt\(f?["']([\w.{}]+)["']""", path.read_text(encoding="utf-8")):
            if "{" in key:
                var = key.split("{")[1].split("}")[0]
                keys.update(key.replace("{" + var + "}", v) for v in DYNAMIC[key])
            else:
                keys.add(key)
    return keys


def main() -> int:
    errors = []
    ref = LANGUAGES["en"][1]
    for code, (name, strings) in LANGUAGES.items():
        if missing := ref.keys() - strings.keys():
            errors.append(f"{code}: missing {sorted(missing)}")
        if extra := strings.keys() - ref.keys():
            errors.append(f"{code}: unknown keys {sorted(extra)}")
        for key in ref.keys() & strings.keys():
            if placeholders(ref[key]) != placeholders(strings[key]):
                errors.append(f"{code}: placeholders differ in {key}")
    if unknown := used_keys() - ref.keys():
        errors.append(f"used in code but missing in en: {sorted(unknown)}")
    if unused := ref.keys() - used_keys():
        errors.append(f"defined but never used: {sorted(unused)}")
    for e in errors:
        print("FAIL", e)
    print(f"{len(LANGUAGES)} locales, {len(ref)} keys, {len(errors)} problems")
    return len(errors)


if __name__ == "__main__":
    raise SystemExit(main())
