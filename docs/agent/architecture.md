# Architecture

## Files

| Path | Role |
| --- | --- |
| `textfixer.pyw` | Entry point (PyInstaller target, also runnable with `pythonw`) |
| `textfixer/__main__.py` | `python -m textfixer` |
| `textfixer/__init__.py` | `__version__` — single source of truth for the version |
| `textfixer/app.py` | `App`: tray icon/menu, keyboard-hook handler, job worker, autostart, updates UI |
| `textfixer/winapi.py` | ctypes: low-level keyboard hook, `SendInput`, clipboard, foreground process, mutex |
| `textfixer/layout.py` + `lang_data.py` | Local EN↔RU wrong-layout fix |
| `textfixer/llm.py` | `Corrector`: chat-completions call, prompt, model fallback |
| `textfixer/config.py` | `Config`/`Style` dataclasses, load/save TOML, migration, proxy helper |
| `textfixer/settings_ui.py` | tkinter settings window |
| `textfixer/updater.py` | GitHub Releases check/download, swap script |
| `tools/build.py` | PyInstaller build + local install |
| `.github/workflows/release.yml` | Tag → build → GitHub Release |
| `tests/test_layout.py` | Layout detection cases (plain script, no pytest) |

## Threads

- **Main thread**: `pystray.Icon.run()` (Win32 message loop for the tray).
- **`kbhook`**: owns `WH_KEYBOARD_LL` hook + its message loop. The callback
  (`App._on_key`) must return fast (Windows drops slow LL hooks): it only matches
  hotkeys, checks the foreground exe for Enter, and enqueues a job.
- **`worker`**: processes jobs sequentially (`fix`, `fix_and_send`, `layout`, `enter`).
- **`settings`**: a fresh `tk.Tk()` per opened settings window; all Tk calls stay in it.
  Cross-thread signals use `queue`/`Event` polled with `root.after`.
- **`updates`**: periodic GitHub check; **`llm-warm`**: pings `/models` every 2 min to
  keep the TLS connection warm.

## A fix, step by step

1. Hook sees a hotkey (or plain Enter in an `auto_enter.apps` exe), swallows the key
   (and its key-up), enqueues `(job, hwnd)`.
2. Worker releases still-held modifiers (`release_modifiers`, with a dummy key before
   Alt/Win release so menus/Start don't open).
3. Grab: save clipboard text → `Ctrl+A` → wait `select_delay_ms` → `Ctrl+C` → wait for
   `GetClipboardSequenceNumber` to change (retry `Ctrl+C` once at half timeout).
4. `fix_layout()`; for `fix`/`fix_and_send` also `Corrector.correct()` with the active style.
5. If the foreground window changed meanwhile → leave result in clipboard, notify, stop.
6. Paste: set clipboard (excluded from Win+V history) → `Ctrl+A` → wait → `Ctrl+V`;
   for send jobs wait `paste_settle_ms` and tap Enter.
7. Restore the previous clipboard text after `clipboard_restore_ms` (timer thread).

Our own injected keys carry `LLKHF_INJECTED`, so the hook ignores them — no recursion.

## Why it is built this way

- **Clipboard + synthetic keys** instead of UI Automation: works in every app
  (Electron/Discord, Qt/Telegram, browsers) with one code path.
- **Own ctypes hook** instead of `keyboard`/`pynput`: reliable suppression and the
  injected-flag check; no extra dependency.
- **Local layout fix**: instant and offline, so Enter interception adds ~150 ms at most.
- **LLM only on explicit hotkeys**: Enter never waits for the network.
- **PyInstaller onedir exe** in `%LOCALAPPDATA%\TextFixer\app`: Task Manager shows
  "TextFixer" (not "Python"), autostart is a plain exe path, fast start (no onefile unpack).
- **Single instance**: named mutex `Local\TextFixerSingleInstance`; a second start exits silently.

## Known limitations

- Elevated (admin) windows don't receive our input (UIPI) and the hook doesn't see
  their keys — nothing is lost, the app just does nothing there.
- Only clipboard **text** is restored; images in the clipboard are lost after a fix.
- `Ctrl+A` without a focused field may select the whole page; `max_chars` caps damage.
