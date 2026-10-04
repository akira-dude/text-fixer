# Pitfalls (each one happened)

- **pystray callback arity**: `MenuItem(action=…)` accepts callables with 0, 1 or 2
  positional params only. `lambda icon, item, k=key: …` has 3 → `ValueError` when the
  menu is built → app dies at start with no console. Use a closure factory
  (`App._style_item`). Always build the menu in a test before restarting the app.
- **Discord (Electron) applies `Ctrl+A` asynchronously**: an immediate `Ctrl+C` copies
  nothing. Hence `select_delay_ms` and the `Ctrl+C` retry. Same delay before `Ctrl+V`.
- **`fix_and_send` must not send unchecked text**: if the grab fails, don't press Enter.
  Plain `enter` jobs must always end with an Enter (never swallow the user's key).
- **Backslashes in shell heredocs / `printf`**: `\a`, `\b` became control characters in
  `install.cmd` and `README.md` once. Write files with the editor tool, not `printf`;
  in Python string literals use `\\` for Windows paths.
- **Line endings**: rewriting config with `Path.write_text` converted LF→CRLF on
  Windows. Use `newline=""` or binary writes when preserving files matters.
- **Restarting during development**: kill only TextFixer processes
  (`Get-Process TextFixer`, or `pythonw` whose command line contains `textfixer`), never
  all `pythonw` processes.
- **Venv `pythonw.exe` is a launcher**: it spawns the base interpreter, so there are two
  processes and Task Manager shows "Python". That's why the app ships as an exe.
- **Groq 403s** are usually network/region (VPN off), not the model — see `llm.md`.
