"""English UI strings (reference locale: every key must exist here)."""

STRINGS = {
    # --- tray menu
    "menu.hotkeys": "Fix: {fix} · and send: {send} · layout: {layout}",
    "menu.model": "Model: {model}",
    "menu.style": "Style: {style}",
    "menu.auto_enter": "Fix layout on Enter",
    "menu.autostart": "Start with Windows",
    "menu.settings": "Settings…",
    "menu.data_folder": "Open data folder",
    "menu.update_to": "Update to {version}",
    "menu.updating": "Updating…",
    "menu.check_updates": "Check for updates (version {version})",
    "menu.quit": "Quit",
    "tray.title": "TextFixer — {style}",

    # --- notifications
    "notify.error": "Error: {error}",
    "notify.too_long": "Text is longer than {max} characters — only the layout was fixed",
    "notify.model_switched": "Model: {model}",
    "notify.window_changed": "The window changed — the fixed text is in the clipboard",
    "notify.update_available": "Version {version} is available — tray menu → “Update”",
    "notify.up_to_date": "You have the latest version {version}",
    "notify.update_check_failed": "Update check: {error}",
    "notify.update_only_installed": "Updates work only in the installed version (install.cmd)",
    "notify.downloading": "Downloading version {version}…",
    "notify.update_failed": "Update failed: {error}",
    "notify.updated": "Updated to version {version}",
    "notify.update_rolled_back": "The update did not start — the previous version is running. Details in update\\apply.log",
    "notify.ask_api_key": "Enter an API key in the settings",

    # --- connection test
    "test.sample": "hello how are you doing today",
    "test.ok": "✓ {model}, {ms} ms: “{text}”",
    "test.fail": "✗ {error}",

    # --- LLM errors
    "llm.proxy_down": "Proxy is unreachable — is the VPN off?",
    "llm.timeout": "timeout {seconds} s",
    "llm.network": "Network: {error} — check internet/VPN",
    "llm.bad_key": "Invalid API key",
    "llm.region_block": "The provider blocks the request at network level ({message}) — check your VPN",
    "llm.no_key": "No API key set — open Settings",
    "llm.all_failed": "All models are unavailable. {errors}",
    "llm.weird_answer": "The model returned something odd, text left as is",

    # --- updater errors
    "upd.github_down": "GitHub is unreachable: {error}",
    "upd.no_archive": "Release {version} has no archive",
    "upd.no_checksum": "No checksum — update not installed",
    "upd.download_failed": "Download failed: {error}",
    "upd.bad_checksum": "Checksum mismatch — the archive is damaged",
    "upd.bad_path": "Suspicious path in the archive",
    "upd.no_exe": "The archive has no TextFixer.exe",

    # --- hotkey parsing
    "hotkey.unknown_key": "Unknown key '{key}' in '{spec}'",
    "hotkey.no_main_key": "'{spec}' has no main key",

    # --- settings window
    "settings.title": "TextFixer — settings",
    "settings.save": "Save",
    "settings.cancel": "Cancel",
    "settings.tab.api": "Connection",
    "settings.tab.hotkeys": "Hotkeys",
    "settings.tab.enter": "Enter",
    "settings.tab.styles": "Styles",
    "settings.tab.timing": "Timings",

    "settings.language": "Language",
    "settings.api_key": "API key",
    "settings.show": "show",
    "settings.base_url": "API URL",
    "settings.base_url.hint": "Any OpenAI-compatible API. Groq: https://api.groq.com/openai/v1",
    "settings.models": "Models",
    "settings.models.hint": "One per line, in priority order. If a model is unavailable (disabled, rate-limited, down), "
                            "the next one is used; a failed model is skipped for 10 minutes.",
    "settings.proxy": "Proxy",
    "settings.proxy.system": "System (same as the browser)",
    "settings.proxy.direct": "No proxy",
    "settings.proxy.hint": "You can type your own URL. An explicit VPN client address is more reliable than the system one.",
    "settings.effort": "gpt-oss reasoning",
    "settings.effort.hint": "low is the fastest. Not used for other models.",
    "settings.limits": "Limits",
    "settings.timeout": "timeout, s",
    "settings.max_chars": "max characters",
    "settings.check_updates": "Check for updates automatically (GitHub)",
    "settings.test": "Test connection",
    "settings.testing": "Testing…",

    "settings.hk.fix": "Fix",
    "settings.hk.fix.hint": "layout + AI, style from the tray",
    "settings.hk.fix_and_send": "Fix and send",
    "settings.hk.fix_and_send.hint": "the same, then Enter",
    "settings.hk.layout": "Layout only",
    "settings.hk.layout.hint": "no AI, instant",
    "settings.hk.record": "Record",
    "settings.hk.press": "press a combination…",
    "settings.hk.help": "“Record” — press the combination (Esc cancels, Backspace clears). "
                        "You can also type it: modifiers ctrl, shift, alt, win; keys a-z, 0-9, f1-f24, "
                        "space, enter, pause, insert, home, end…",

    "settings.enter.enabled": "Fix the layout on Enter before sending",
    "settings.enter.apps": "Apps",
    "settings.enter.apps.hint": "Exe names, one per line (as in Task Manager → Details). "
                                "Shift+Enter (new line) is not affected.",

    "settings.style.add": "Add",
    "settings.style.delete": "Delete",
    "settings.style.name": "Name",
    "settings.style.rewrite": "Rewrite the text (allow changing the length)",
    "settings.style.strip": "Remove the period at the end of the message",
    "settings.style.prompt": "Instruction",
    "settings.style.hint": "Fixed rules are always added: never translate, never answer the message, "
                           "keep links, @mentions, emojis and line breaks.",
    "settings.style.new_name": "New style {n}",
    "settings.style.new_prompt": "Fix spelling and punctuation.",
    "settings.style.keep_one": "At least one style must remain.",

    "settings.timing.select_delay": "Pause after Ctrl+A",
    "settings.timing.select_delay.hint": "Discord applies the selection with a delay. If the first press does nothing, increase it.",
    "settings.timing.copy_timeout": "Copy wait",
    "settings.timing.copy_timeout.hint": "for hotkeys",
    "settings.timing.enter_copy_timeout": "Copy wait on Enter",
    "settings.timing.enter_copy_timeout.hint": "on an empty field Enter is delayed by this much",
    "settings.timing.paste_settle": "Pause before Enter after paste",
    "settings.timing.clipboard_restore": "Restore clipboard after",
    "settings.ms": "ms",

    "settings.err.no_models": "Specify at least one model",
    "settings.err.duplicate_hotkey": "The same combination is assigned twice",
    "settings.err.not_number": "“{field}” must be a number",
}
