# TextFixer

A Windows tray app that fixes the text you are typing — in any app (Discord, Telegram, a browser, Claude…) — with one hotkey.

- **Wrong keyboard layout** (`ghbdtn` → `привет`, `руддщ` → `hello`): fixed locally, instantly, offline.
- **Spelling, capitalization, punctuation, tone**: via a fast remote LLM (Groq by default; any OpenAI-compatible API works).
- **Enter in Discord / Telegram**: if the message was typed in the wrong layout, it is fixed first and then sent.

The UI is in Russian.

## Install

**From a release.** Download `TextFixer-vX.Y.Z.zip` from [Releases](https://github.com/akira-dude/text-fixer/releases), extract it to `%LOCALAPPDATA%\TextFixer\app` and run `TextFixer.exe`. Self-update only works from that folder.

**From source.** Run `install.cmd`. It creates `.venv`, builds `TextFixer.exe` with PyInstaller, installs it to `%LOCALAPPDATA%\TextFixer\app` and starts it. Run it again after code changes to rebuild and reinstall; settings are kept. To run without building: `.venv\Scripts\python -m textfixer`.

On first start the settings window opens: paste an API key (e.g. from [console.groq.com](https://console.groq.com)) and press «Проверить подключение» (test connection).

Start with Windows: a checkbox in the tray menu.

## Settings

Tray menu → «Настройки…» (or click the tray icon): API key, models, proxy, hotkeys, apps for the Enter fix, styles, timings. Changes apply immediately.

Data lives outside the repo and the app folder, in `%LOCALAPPDATA%\TextFixer`: `config.toml` (settings, including the API key) and `textfixer.log`. The log contains only timings and text lengths, never the text itself.

**Models.** A list in priority order. If a model fails (disabled, rate-limited, down), the next one is used and the failed one is skipped for 10 minutes. A network-level block (for example the provider rejecting your region) is reported as such — switching models would not help, check your VPN/proxy.

**Proxy.** System proxy (default), no proxy, or an explicit URL such as `http://127.0.0.1:10809`.

## Hotkeys (configurable)

| Keys | Action |
| --- | --- |
| `Ctrl+Shift+Space` | fix layout + LLM correction |
| `Ctrl+Shift+Enter` | same, then send (Enter) |
| `Pause` | layout only, no LLM |
| `Enter` in listed apps | fix the layout if needed, then send |

## Styles

Pick the correction style in the tray («Стиль» submenu). Built in:

- **Мой стиль** (my style) — spelling, commas and capitals only; wording and slang stay, no period at the end.
- **Деловой** (business) — rewrites the message in a polite business tone.

Edit styles or add your own in Settings → «Стили». Fixed rules (never translate, never answer the message, keep links/mentions/emojis) are always added; see `textfixer/llm.py`.

Tray icon: blue — idle, yellow — waiting for the model, red — error (details in the notification and the log).

## Updates

The app checks GitHub Releases on start and every 6 hours (can be disabled in Settings). When a new version is out, you get a notification and a «Обновить до X» (update to X) tray item: the zip is downloaded and its SHA-256 verified, the app folder is swapped and the app restarts. Settings are untouched. If the new version fails to start, the previous one is restored automatically.

Publishing a version: bump `__version__` in `textfixer/__init__.py`, commit, push a `vX.Y.Z` tag — GitHub Actions builds the exe and publishes the release.

## How it works

`Ctrl+A` → `Ctrl+C` → fix → `Ctrl+A` → `Ctrl+V`, then the previous clipboard text is restored. The pasted text is kept out of the `Win+V` clipboard history. Keys are intercepted with a low-level keyboard hook (ctypes, no extra libraries).

## Limitations

- Apps running as administrator don't accept input from a normal process — TextFixer does nothing there.
- Only clipboard **text** is restored; an image in the clipboard is lost after a fix.
- Without a focused field, `Ctrl+A` may select the whole page; text longer than `max_chars` is not sent to the LLM.
- Don't type or switch windows while waiting for the model (if the window changes, the result is left in the clipboard).

## Development

```
.venv\Scripts\python -m tests.test_layout
```

Notes for AI agents: [`AGENTS.md`](AGENTS.md) and [`docs/agent/`](docs/agent/INDEX.md).
