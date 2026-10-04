# TextFixer — notes for AI agents

Windows tray app (Python 3.14) that fixes text in any focused input field by hotkey:
wrong keyboard layout (EN↔RU) is fixed locally, spelling/capitalization/style via an
OpenAI-compatible LLM API (Groq by default). Personal project of the repo owner; not
related to the Unipay repos in the parent `F:\GIT` workspace.

Read next: [`docs/agent/INDEX.md`](docs/agent/INDEX.md).

## Ground rules

- **Language**: chat with the user in Russian. UI strings and notifications are Russian.
  README, code, comments, agent docs (`AGENTS.md`, `docs/agent/**`) and commit
  messages are English.
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`…), English.
  This repo has no release branches: work directly on `main`, push to `origin main`.
  No AI attribution lines in commits.
- **Secrets**: the user's API key lives only in `%LOCALAPPDATA%\TextFixer\config.toml`.
  Never print it, never copy it into the repo, never read that file unless needed
  (prefer `textfixer.config.load()` and print only `bool(cfg.api_key)`).
- **Public repo**: anything committed is public. Keep personal data out.
- **Releases are user-visible**: pushing a `v*` tag publishes an update that the
  installed app offers to the user. Only tag when the user asks for a release.

## Quick commands

```bash
.venv\Scripts\python -m tests.test_layout   # layout detection tests (must stay green)
.venv\Scripts\python -m textfixer           # run from source (stop the installed exe first: single instance)
install.cmd                                 # build TextFixer.exe and install it locally
```

## Verify before claiming done

- Import + menu build: `python -X utf8 -c "from textfixer.app import App; a=App(); print([str(i.text) for i in a.icon.menu.items]); a.corrector.close()"`.
  pystray validates callback arity when the menu is built — a bad lambda crashes the app at start.
- After restarting the app, check the process is still alive a few seconds later
  (`Get-Process TextFixer`), not just that the log says `started`.
- The app runs without a console (`--windowed`); fatal errors go to
  `%LOCALAPPDATA%\TextFixer\textfixer.log` only.
