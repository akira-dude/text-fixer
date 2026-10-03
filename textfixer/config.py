import os
import re
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.toml"
EXAMPLE_PATH = ROOT / "config.example.toml"
LOG_PATH = ROOT / "textfixer.log"


@dataclass
class Style:
    key: str
    name: str
    prompt: str
    rewrite: bool = False
    strip_final_period: bool = False


DEFAULT_STYLES = {
    "my": Style("my", "Мой стиль", "Исправь только орфографию, грамматику, запятые и заглавные буквы. "
                "Сохрани формулировки, сленг и тон. В конце последнего предложения точку не ставь.",
                strip_final_period=True),
}


@dataclass
class Config:
    base_url: str = "https://api.groq.com/openai/v1"
    api_key: str = ""
    model: str = "openai/gpt-oss-120b"
    reasoning_effort: str = "low"
    timeout_s: float = 8
    max_chars: int = 4000
    hotkey_fix: str = "ctrl+shift+space"
    hotkey_fix_and_send: str = "ctrl+shift+enter"
    hotkey_layout: str = "pause"
    auto_enter: bool = True
    auto_enter_apps: list[str] = field(default_factory=lambda: ["discord.exe", "telegram.exe"])
    select_delay_ms: int = 40
    copy_timeout_ms: int = 400
    enter_copy_timeout_ms: int = 150
    paste_settle_ms: int = 80
    clipboard_restore_ms: int = 400
    styles: dict[str, Style] = field(default_factory=lambda: dict(DEFAULT_STYLES))
    active_style: str = "my"

    @property
    def style(self) -> Style:
        return self.styles.get(self.active_style) or next(iter(self.styles.values()))


def ensure_config() -> bool:
    """Create config.toml from the example. Returns True if it was just created."""
    if CONFIG_PATH.exists():
        return False
    shutil.copyfile(EXAMPLE_PATH, CONFIG_PATH)
    return True


def load() -> Config:
    with open(CONFIG_PATH, "rb") as f:
        raw = tomllib.load(f)
    api, hk, ae, tm = (raw.get(k, {}) for k in ("api", "hotkeys", "auto_enter", "timing"))
    d = Config()
    styles = {
        key: Style(key, s.get("name", key), s.get("prompt", "").strip(),
                   bool(s.get("rewrite", False)), bool(s.get("strip_final_period", False)))
        for key, s in raw.get("styles", {}).items()
    } or dict(DEFAULT_STYLES)
    return Config(
        styles=styles,
        active_style=raw.get("style", {}).get("active", next(iter(styles))),
        base_url=api.get("base_url", d.base_url).rstrip("/"),
        api_key=os.environ.get("TEXTFIXER_API_KEY") or api.get("api_key", ""),
        model=api.get("model", d.model),
        reasoning_effort=api.get("reasoning_effort", d.reasoning_effort),
        timeout_s=float(api.get("timeout_s", d.timeout_s)),
        max_chars=int(api.get("max_chars", d.max_chars)),
        hotkey_fix=hk.get("fix", d.hotkey_fix),
        hotkey_fix_and_send=hk.get("fix_and_send", d.hotkey_fix_and_send),
        hotkey_layout=hk.get("layout", d.hotkey_layout),
        auto_enter=bool(ae.get("enabled", d.auto_enter)),
        auto_enter_apps=[a.lower() for a in ae.get("apps", d.auto_enter_apps)],
        select_delay_ms=int(tm.get("select_delay_ms", d.select_delay_ms)),
        copy_timeout_ms=int(tm.get("copy_timeout_ms", d.copy_timeout_ms)),
        enter_copy_timeout_ms=int(tm.get("enter_copy_timeout_ms", d.enter_copy_timeout_ms)),
        paste_settle_ms=int(tm.get("paste_settle_ms", d.paste_settle_ms)),
        clipboard_restore_ms=int(tm.get("clipboard_restore_ms", d.clipboard_restore_ms)),
    )


def save_active_style(key: str) -> None:
    """Rewrite only the `active = ...` line of [style], keeping comments intact."""
    with open(CONFIG_PATH, encoding="utf-8", newline="") as f:
        text = f.read()
    new, n = re.subn(r'(?m)^(\[style\][^\[]*?^active\s*=\s*)"[^"]*"', rf'\g<1>"{key}"', text)
    if not n:
        new = text.rstrip() + f'\n\n[style]\nactive = "{key}"\n'
    with open(CONFIG_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(new)
