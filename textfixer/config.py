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
    # Built-in and unedited: text comes from _DEFAULT_STYLES in the UI language.
    builtin: bool = False


_DEFAULT_STYLES = {
    "en": {
        "my": Style("my", "My style", (
            "Fix only spelling, grammar, commas and capitalization.\n"
            "Keep my wording, slang, tone and word order. Do not rephrase, shorten or extend.\n"
            "Start every sentence with a capital letter.\n"
            "Do not put a period after the last sentence.\n"
            "If everything is already correct, return the text unchanged."
        ), strip_final_period=True),
        "business": Style("business", "Business", (
            "Rewrite the message in a polite, clear business style for work chats with colleagues or clients.\n"
            "Complete sentences, correct punctuation, no slang, filler words or profanity.\n"
            "Keep the meaning and all facts. Do not add greetings, signatures or details that are not in the original.\n"
            "Keep it about as long as the original."
        ), rewrite=True),
    },
    "ru": {
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
    },
}


def default_styles(language: str = "en") -> dict[str, Style]:
    """Fresh copies of the built-in styles, in the UI language if available."""
    return {k: replace(s, builtin=True) for k, s in _DEFAULT_STYLES.get(language, _DEFAULT_STYLES["en"]).items()}


def builtin_style(key: str, language: str) -> Style | None:
    return default_styles(language).get(key)


def localize_builtin(styles: dict[str, Style], language: str) -> dict[str, Style]:
    """Re-render unedited built-in styles in `language`; edited styles stay as they are."""
    return {k: (builtin_style(k, language) or s) if s.builtin else s for k, s in styles.items()}


def _matches_builtin(style: Style) -> bool:
    """True if the style equals a built-in one in any language (pre-0.5 configs stored full text)."""
    for lang in _DEFAULT_STYLES:
        b = builtin_style(style.key, lang)
        if b and (b.name, b.prompt, b.rewrite, b.strip_final_period) == (
                style.name, style.prompt, style.rewrite, style.strip_final_period):
            return True
    return False


@dataclass
class Config:
    language: str = "en"  # UI language, see textfixer/locales
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
    check_updates: bool = True
    styles: dict[str, Style] = field(default_factory=default_styles)
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
    language = raw.get("ui", {}).get("language", d.language)
    styles = {}
    for key, s in raw.get("styles", {}).items():
        st = Style(key, s.get("name", key), s.get("prompt", "").strip(),
                   bool(s.get("rewrite", False)), bool(s.get("strip_final_period", False)),
                   builtin=bool(s.get("builtin", False)))
        if st.builtin or _matches_builtin(st):
            st = builtin_style(key, language) or replace(st, builtin=False)
        styles[key] = st
    styles = styles or default_styles(language)
    return Config(
        language=language,
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
        check_updates=bool(raw.get("updates", {}).get("check", d.check_updates)),
    )


def save(cfg: Config) -> None:
    data = {
        "ui": {"language": cfg.language},
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
        "updates": {"check": cfg.check_updates},
        "style": {"active": cfg.active_style},
        "styles": {
            k: {"builtin": True} if s.builtin else
            {"name": s.name, "rewrite": s.rewrite, "strip_final_period": s.strip_final_period, "prompt": s.prompt}
            for k, s in cfg.styles.items()
        },
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        tomli_w.dump(data, f, multiline_strings=True)
    os.replace(tmp, CONFIG_PATH)


def http_proxy_kwargs(proxy: str) -> dict:
    """httpx.Client kwargs for the proxy setting: "" = system/env, "direct" = none, else a URL."""
    proxy = proxy.strip()
    return {"trust_env": not proxy, "proxy": proxy if proxy and proxy != "direct" else None}
