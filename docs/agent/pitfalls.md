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
  in Python string literals use `\\` for Windows paths. In this environment even a
  quoted bash heredoc (`<<'EOF'`) turned `\n` inside Python source into real newlines
  and broke `config.py`: put patch scripts in a file (Write tool) and run that file.
- **Line endings**: rewriting config with `Path.write_text` converted LF→CRLF on
  Windows. Use `newline=""` or binary writes when preserving files matters.
- **Restarting during development**: kill only TextFixer processes
  (`Get-Process TextFixer`, or `pythonw` whose command line contains `textfixer`), never
  all `pythonw` processes.
- **Venv `pythonw.exe` is a launcher**: it spawns the base interpreter, so there are two
  processes and Task Manager shows "Python". That's why the app ships as an exe.
- **Spawning PowerShell from the windowed exe**: with `DETACHED_PROCESS` PowerShell
  silently never starts (it needs a console). Use `CREATE_NO_WINDOW |
  CREATE_NEW_PROCESS_GROUP` (+ `CREATE_BREAKAWAY_FROM_JOB` with fallback). v0.3.0 from
  GitHub shipped with this bug: updating *from* that build quits the app without
  swapping — reinstall with `install.cmd` if someone is stuck on it.
- **Testing detached children from the agent shell**: the agent's command runner kills
  child processes when the command ends, so "it didn't run" may be the harness. Test
  survival by writing a marker file from the child and checking it after the parent exits.
- **`shutil.rmtree` right after killing the exe** can leave the folder "delete pending";
  `tools/build.py` retries before copying.
- **Groq 403s** are usually network/region (VPN off), not the model — see `llm.md`.
