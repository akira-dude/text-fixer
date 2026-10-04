"""Settings: stored in %LOCALAPPDATA%\\TextFixer\\config.toml, edited from the settings window."""

import os
import shutil
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path

import tomli_w

ROOT = Path(__file__).resolve().parent.parent  # source checkout (or bundle dir when frozen)
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "TextFixer"
CONFIG_PATH = DATA_DIR / "config.toml"
LOG_PATH = DATA_DIR / "textfixer.log"
LEGACY_CONFIG = ROOT / "config.toml"  # pre-GUI location inside the repo


@dataclass
class Style:
    key: str
    name: str
    prompt: str
    rewrite: bool = False
    strip_final_period: bool = False


DEFAULT_STYLES = {
    "my": Style("my", "Мой стиль", (
        "Исправь только орфографию, грамматику, запятые и заглавные буквы.\n"
        "Сохрани мои формулировки, сленг, тон и порядок слов. Не перефразируй, не сокращай и не дополняй.\n"
        "Каждое предложение начинай с заглавной буквы.\n"
        "В конце последнего предложения точку не ставь.\n"
        "Если всё уже правильно, верни текст без изменений."
    ), strip_final_period=True),
    "business": Style("business", "Деловой", (
        "Перепиши сообщение в вежливом, ясном деловом стиле — для рабочей переписки с коллегами или клиентами.\n"
        "Полные предложения, правильная пунктуация, без сленга, слов-паразитов и мата.\n"
        "Сохрани смысл и все факты. Не добавляй приветствий, подписей и деталей, которых нет в исходнике.\n"
        "Длина — примерно как у исходного сообщения."
    ), rewrite=True),
}


@dataclass
class Config:
    base_url: str = "https://api.groq.com/openai/v1"
    api_key: str = ""
    models: list[str] = field(default_factory=lambda: [
        "openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"])
    proxy: str = ""  # "" = system, "direct" = none, or a URL
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
    styles: dict[str, Style] = field(default_factory=lambda: {k: replace(s) for k, s in DEFAULT_STYLES.items()})
    active_style: str = "my"

    @property
    def style(self) -> Style:
        return self.styles.get(self.active_style) or next(iter(self.styles.values()))


def ensure_config() -> bool:
    """Create the config (migrating the old repo one). Returns True if it was just created."""
    if CONFIG_PATH.exists():
        return False
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LEGACY_CONFIG.exists():
        shutil.copyfile(LEGACY_CONFIG, CONFIG_PATH)
        save(load())  # normalize to the current format
        LEGACY_CONFIG.unlink()
        return False
    save(Config())
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
    } or d.styles
    return Config(
        styles=styles,
        active_style=raw.get("style", {}).get("active", next(iter(styles))),
        base_url=api.get("base_url", d.base_url).rstrip("/"),
        api_key=os.environ.get("TEXTFIXER_API_KEY") or api.get("api_key", ""),
        # "models" is a fallback chain; a single "model" is still accepted.
        models=list(api.get("models") or [api.get("model", d.models[0])]),
        proxy=api.get("proxy", d.proxy),
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


def save(cfg: Config) -> None:
    data = {
        "api": {
            "base_url": cfg.base_url, "api_key": cfg.api_key, "models": cfg.models, "proxy": cfg.proxy,
            "reasoning_effort": cfg.reasoning_effort, "timeout_s": cfg.timeout_s, "max_chars": cfg.max_chars,
        },
        "hotkeys": {"fix": cfg.hotkey_fix, "fix_and_send": cfg.hotkey_fix_and_send, "layout": cfg.hotkey_layout},
        "auto_enter": {"enabled": cfg.auto_enter, "apps": cfg.auto_enter_apps},
        "timing": {
            "select_delay_ms": cfg.select_delay_ms, "copy_timeout_ms": cfg.copy_timeout_ms,
            "enter_copy_timeout_ms": cfg.enter_copy_timeout_ms, "paste_settle_ms": cfg.paste_settle_ms,
            "clipboard_restore_ms": cfg.clipboard_restore_ms,
        },
        "style": {"active": cfg.active_style},
        "styles": {
            k: {"name": s.name, "rewrite": s.rewrite, "strip_final_period": s.strip_final_period, "prompt": s.prompt}
            for k, s in cfg.styles.items()
        },
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        tomli_w.dump(data, f, multiline_strings=True)
    os.replace(tmp, CONFIG_PATH)
