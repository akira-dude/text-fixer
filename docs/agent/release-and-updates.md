# Build, release and self-update

## Local build / install

`install.cmd` → creates `.venv` if needed, installs `requirements.txt` +
`requirements-build.txt`, runs `tools/build.py`:

1. Generates `build/textfixer.ico` from `app.ICON_IDLE` and a PyInstaller version
   resource (`FileDescription` = "TextFixer" → that's what Task Manager shows).
2. PyInstaller **onedir**, `--windowed`, hidden import `pystray._win32`.
3. Migrates the old repo config (`config.ensure_config()`), stops the running exe and
   any `pythonw … textfixer` dev instance, replaces `%LOCALAPPDATA%\TextFixer\app`,
   starts the new exe.

`tools/build.py --no-install` only builds (used by CI). `build/` is git-ignored.

## Publishing a release (only when the user asks)

1. Bump `textfixer/__init__.py` `__version__` (semver: fix → patch, feature → minor).
2. Commit (`chore: release vX.Y.Z` or include it in the feature commit), push `main`.
3. `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. `.github/workflows/release.yml` (windows-latest, Python 3.14) checks tag == version,
   runs layout tests, builds, zips `build/dist/TextFixer/*` as
   `TextFixer-vX.Y.Z.zip` (files at zip root) + `.zip.sha256`, release notes = commit
   subjects since the previous tag.
5. Watch it: `gh run watch` / `gh release view vX.Y.Z`.

Never delete or re-tag a published release: installed apps may be mid-download.
If a release is broken, ship a new patch version.

## Self-update (`updater.py`)

- `check()` → `GET api.github.com/repos/akira-dude/text-fixer/releases/latest`
  (unauthenticated, repo is public; respects `api.proxy`). Newer = semver compare of
  tag vs `__version__`.
- App checks 20 s after start and every 6 h if `updates.check`; the tray item shows
  "Обновить до X" when available, otherwise "Проверить обновления".
- `download()` streams the zip to `update\`, verifies SHA-256 (asset `digest` from the
  API, fallback `.sha256` asset), rejects path traversal, unpacks to `app.new\`,
  requires `TextFixer.exe`.
- `launch_apply()` writes `update\apply.ps1` and starts it detached; the app quits.
  The script waits for the old PID, renames `app` → `app.old`, `app.new` → `app`,
  starts the exe with `--updated`, then waits up to 20 s for `update\started.ok`
  (written by `updater.mark_started()` ~3 s after the new version is up).
  No marker → kill, `app` → `app.failed`, `app.old` → `app`, start with `--update-failed`.
  Script log: `update\apply.log`.
- Only an exe running from `%LOCALAPPDATA%\TextFixer\app` updates itself
  (`is_installed()`); a source run just reports that.

Why folder swap instead of per-file patching: Windows locks the running exe/DLLs, and
almost every code change rewrites `TextFixer.exe` anyway (the Python code is packed
into it); GitHub Releases serve archives, not file trees. A full ~20 MB zip keeps it
simple and gives atomic rollback.

Settings survive because they live in `%LOCALAPPDATA%\TextFixer\config.toml`, one level
above `app\`. If a new version changes the config schema, keep `load()` backward
compatible (missing keys → defaults, renamed keys → read the old name too).

## Testing the updater locally

Install a build with a lower `__version__` (temporarily edit, `install.cmd`, revert),
then trigger the tray item or call `updater.check/download/launch_apply` from a script
while the installed exe runs; verify `apply.log`, the new version in the log line
`started X.Y.Z`, and that `config.toml` is unchanged.
