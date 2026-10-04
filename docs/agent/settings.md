# Settings

## Location

`%LOCALAPPDATA%\TextFixer\` (`config.DATA_DIR`), outside the repo and outside the
installed app folder so updates and reinstalls never touch it:

| File | Content |
| --- | --- |
| `config.toml` | All settings incl. API key (written by `config.save`, `tomli_w`) |
| `textfixer.log` | Log: timings and lengths only, never message text |
| `app\` | Installed exe (replaced by updates) |
| `update\` | Updater work files: `apply.ps1`, `apply.log`, `started.ok` |

`config.ensure_config()` creates the file with defaults, or migrates the pre-0.2
`config.toml` from the repo root (copy → normalize → delete the old one).

## Schema

`config.Config` is the single schema; `load()` maps TOML sections to fields with
defaults for anything missing, `save()` writes the same structure:

```toml
[api]        base_url, api_key, models[], proxy, reasoning_effort, timeout_s, max_chars
[hotkeys]    fix, fix_and_send, layout
[auto_enter] enabled, apps[]
[timing]     select_delay_ms, copy_timeout_ms, enter_copy_timeout_ms, paste_settle_ms, clipboard_restore_ms
[updates]    check
[style]      active
[styles.<id>] name, rewrite, strip_final_period, prompt
```

`TEXTFIXER_API_KEY` env var overrides `api.api_key` on load.

## Built-in vs custom styles

- `[styles.<id>] builtin = true` (nothing else stored) = an unedited built-in style.
  `load()` renders it from `config._DEFAULT_STYLES[ui.language]`; `localize_builtin()`
  re-renders after a language change (`App.apply_config`).
- Any edit in the settings window (`_store_style`) flips `builtin` to False; from then
  on name/prompt/flags are stored verbatim and never translated.
- "Reset to default" replaces a style with `builtin_style(key, language)`.
- Migration: pre-0.5 configs stored full text; a style equal to a built-in in *any*
  language (`_matches_builtin`) is converted to `builtin = true` on load.

## Settings window

`settings_ui.SettingsWindow` edits a deep copy of the config and calls back into
`App.apply_config(cfg)` on save, which validates hotkeys, persists, rebuilds the
`Corrector` and refreshes the menu — no restart needed. While the window is open,
`App._on_key` ignores hotkeys so they can be recorded.

## Adding a setting

1. Field with default in `Config`.
2. Read it in `load()` and write it in `save()` (same section names).
3. Widget in `settings_ui.py` (`_build_*` tab) and pass it in `_collect()`.
4. Use `self.cfg.<field>` at runtime (the object is replaced on save — don't cache values).
5. Mention it in `README.md` if user-facing.
