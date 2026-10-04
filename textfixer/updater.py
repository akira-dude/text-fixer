"""Self-update from GitHub Releases.

Flow: check() finds a newer release -> download() verifies the zip and unpacks it
to %LOCALAPPDATA%\\TextFixer\\app.new -> launch_apply() starts a PowerShell script
and the app quits -> the script swaps app.new into app, starts the new exe with
--updated and waits for it to call mark_started(); if it doesn't, the old version
is restored. config.toml lives one level above app\\, so settings are untouched.
"""

import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from . import __version__
from .config import DATA_DIR, http_proxy_kwargs
from .i18n import t

log = logging.getLogger("textfixer")

REPO = "akira-dude/text-fixer"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

APP_DIR = DATA_DIR / "app"
NEW_DIR = DATA_DIR / "app.new"
UPDATE_DIR = DATA_DIR / "update"
STARTED_OK = UPDATE_DIR / "started.ok"

# Runs detached after the app exits. Keep it self-contained: the app folder is
# renamed underneath it.
APPLY_SCRIPT = r"""
param([int]$AppPid, [string]$Data)
$ErrorActionPreference = 'Stop'
$app = Join-Path $Data 'app'
$new = Join-Path $Data 'app.new'
$old = Join-Path $Data 'app.old'
$ok  = Join-Path $Data 'update\started.ok'
$log = Join-Path $Data 'update\apply.log'
function Log($m) { Add-Content -Path $log -Value ("{0:s} {1}" -f (Get-Date), $m) -Encoding utf8 }
function Start-App($dir, $arg) { Start-Process -FilePath (Join-Path $dir 'TextFixer.exe') -ArgumentList $arg -WorkingDirectory $Data }

Log "apply: waiting for pid $AppPid"
Wait-Process -Id $AppPid -Timeout 15 -ErrorAction SilentlyContinue
Get-Process TextFixer -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300
if (Test-Path $old) { Remove-Item $old -Recurse -Force }
Remove-Item $ok -Force -ErrorAction SilentlyContinue

$moved = $false
for ($i = 0; $i -lt 20 -and -not $moved; $i++) {
    try { Rename-Item -Path $app -NewName 'app.old'; $moved = $true } catch { Start-Sleep -Milliseconds 500 }
}
if (-not $moved) { Log 'apply: app folder is locked, keeping the old version'; Start-App $app '--update-failed'; exit 1 }
Rename-Item -Path $new -NewName 'app'
Start-App $app '--updated'

for ($i = 0; $i -lt 40 -and -not (Test-Path $ok); $i++) { Start-Sleep -Milliseconds 500 }
if (Test-Path $ok) {
    Remove-Item $old -Recurse -Force -ErrorAction SilentlyContinue
    Log 'apply: updated'
    exit 0
}

Log 'apply: new version did not start, rolling back'
Get-Process TextFixer -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
$failed = Join-Path $Data 'app.failed'
if (Test-Path $failed) { Remove-Item $failed -Recurse -Force }
Rename-Item -Path $app -NewName 'app.failed'
Rename-Item -Path $old -NewName 'app'
Start-App $app '--update-failed'
exit 1
"""


class UpdateError(Exception):
    pass


@dataclass
class Release:
    version: str
    notes: str
    page: str
    zip_url: str
    zip_name: str
    sha256: str | None
    sha256_url: str | None


def parse_version(s: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", s)[:3])


def is_installed() -> bool:
    """Only the exe installed in %LOCALAPPDATA%\\TextFixer\\app can update itself."""
    return getattr(sys, "frozen", False) and Path(sys.executable).parent.resolve() == APP_DIR.resolve()


def _client(proxy: str) -> httpx.Client:
    return httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": f"TextFixer/{__version__}"},
                        **http_proxy_kwargs(proxy))


def check(proxy: str) -> Release | None:
    """Newest release if it is newer than the running version."""
    with _client(proxy) as c:
        try:
            r = c.get(LATEST_URL, headers={"Accept": "application/vnd.github+json"})
        except httpx.HTTPError as e:
            raise UpdateError(t("upd.github_down", error=e.__class__.__name__)) from e
    if r.status_code == 404:
        return None  # no releases yet
    if r.status_code != 200:
        raise UpdateError(f"GitHub {r.status_code}")
    data = r.json()
    version = data["tag_name"].lstrip("v")
    if parse_version(version) <= parse_version(__version__):
        return None
    assets = {a["name"]: a for a in data.get("assets", [])}
    zips = [a for name, a in assets.items() if name.startswith("TextFixer") and name.endswith(".zip")]
    if not zips:
        raise UpdateError(t("upd.no_archive", version=version))
    z = zips[0]
    digest = z.get("digest") or ""
    sha_asset = assets.get(z["name"] + ".sha256")
    return Release(
        version=version,
        notes=(data.get("body") or "").strip(),
        page=data.get("html_url", ""),
        zip_url=z["browser_download_url"],
        zip_name=z["name"],
        sha256=digest.split(":", 1)[1].lower() if digest.startswith("sha256:") else None,
        sha256_url=sha_asset["browser_download_url"] if sha_asset else None,
    )


def download(rel: Release, proxy: str) -> Path:
    """Download, verify and unpack the release into app.new. Returns that folder."""
    UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = UPDATE_DIR / rel.zip_name
    h = hashlib.sha256()
    with _client(proxy) as c:
        expected = rel.sha256
        if not expected and rel.sha256_url:
            expected = c.get(rel.sha256_url).text.split()[0].lower()
        if not expected:
            raise UpdateError(t("upd.no_checksum"))
        try:
            with c.stream("GET", rel.zip_url) as r, open(zip_path, "wb") as f:
                r.raise_for_status()
                for chunk in r.iter_bytes(1 << 16):
                    f.write(chunk)
                    h.update(chunk)
        except httpx.HTTPError as e:
            raise UpdateError(t("upd.download_failed", error=e.__class__.__name__)) from e
    if h.hexdigest() != expected:
        zip_path.unlink(missing_ok=True)
        raise UpdateError(t("upd.bad_checksum"))

    if NEW_DIR.exists():
        shutil.rmtree(NEW_DIR)
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.startswith(("/", "\\")) or ".." in Path(name).parts:
                raise UpdateError(t("upd.bad_path"))
        zf.extractall(NEW_DIR)
    zip_path.unlink(missing_ok=True)
    if not (NEW_DIR / "TextFixer.exe").exists():
        shutil.rmtree(NEW_DIR, ignore_errors=True)
        raise UpdateError(t("upd.no_exe"))
    return NEW_DIR


def launch_apply() -> None:
    """Start the swap script; the caller must exit right after."""
    UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    script = UPDATE_DIR / "apply.ps1"
    script.write_text(APPLY_SCRIPT, encoding="utf-8-sig")
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
           "-File", str(script), "-AppPid", str(os.getpid()), "-Data", str(DATA_DIR)]
    # Not DETACHED_PROCESS: PowerShell silently fails to start without a console.
    flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        # Leave our job object (if any) so the script survives this process exiting.
        subprocess.Popen(cmd, cwd=DATA_DIR, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB)
    except OSError:
        subprocess.Popen(cmd, cwd=DATA_DIR, creationflags=flags)
    log.info("update: apply script started")


def mark_started() -> None:
    """Called by a freshly updated version once it is up: confirms the update."""
    try:
        UPDATE_DIR.mkdir(parents=True, exist_ok=True)
        STARTED_OK.write_text(__version__, encoding="utf-8")
    except OSError:
        log.exception("update: cannot write started marker")
