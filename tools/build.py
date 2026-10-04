"""Build TextFixer.exe with PyInstaller and install it to %LOCALAPPDATA%\TextFixer\app.

Usage: .venv\Scripts\python tools\build.py [--no-install]
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from textfixer import __version__, config  # noqa: E402
from textfixer.app import ICON_IDLE  # noqa: E402

BUILD = ROOT / "build"
APP_DIR = config.DATA_DIR / "app"

VERSION_INFO = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=({v}, 0), prodvers=({v}, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('FileDescription', 'TextFixer'),
    StringStruct('ProductName', 'TextFixer'),
    StringStruct('FileVersion', '{s}'),
    StringStruct('ProductVersion', '{s}'),
    StringStruct('OriginalFilename', 'TextFixer.exe')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)
"""


def build() -> Path:
    BUILD.mkdir(exist_ok=True)
    ico = BUILD / "textfixer.ico"
    ICON_IDLE.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64)])
    parts = [int(p) for p in __version__.split(".")] + [0] * 3
    ver = BUILD / "version_info.txt"
    ver.write_text(VERSION_INFO.format(v=", ".join(map(str, parts[:3])), s=__version__), encoding="utf-8")
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
        "--name", "TextFixer", "--icon", str(ico), "--version-file", str(ver),
        "--hidden-import", "pystray._win32",
        "--distpath", str(BUILD / "dist"), "--workpath", str(BUILD / "work"), "--specpath", str(BUILD),
        str(ROOT / "textfixer.pyw"),
    ], check=True)
    return BUILD / "dist" / "TextFixer"


def stop_running() -> None:
    """Stop the installed exe and a dev instance started from source."""
    subprocess.run(["taskkill", "/f", "/im", "TextFixer.exe"], capture_output=True)
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | "
                    "Where-Object CommandLine -like '*textfixer*' | "
                    "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"],
                   capture_output=True)
    time.sleep(1)


def install(dist: Path) -> Path:
    config.ensure_config()  # migrate the old repo config.toml before the first exe start
    stop_running()
    if APP_DIR.exists():
        shutil.rmtree(APP_DIR)
    shutil.copytree(dist, APP_DIR)
    exe = APP_DIR / "TextFixer.exe"
    subprocess.Popen([str(exe)], cwd=APP_DIR, creationflags=subprocess.DETACHED_PROCESS)
    return exe


if __name__ == "__main__":
    dist = build()
    if "--no-install" in sys.argv:
        print(f"Built: {dist}")
    else:
        print(f"Installed and started: {install(dist)}")
