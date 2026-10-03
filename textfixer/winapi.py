"""Thin ctypes wrappers: low-level keyboard hook, SendInput, clipboard, foreground app."""

import ctypes
import os
import threading
import time
from ctypes import wintypes as wt
from typing import Callable

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
ULONG_PTR = ctypes.c_size_t

WH_KEYBOARD_LL = 13
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105
WM_QUIT = 0x12
LLKHF_INJECTED = 0x10

VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN = 0x10, 0x11, 0x12, 0x5B, 0x5C
VK_RETURN = 0x0D
MODIFIER_VKS = {0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5}

VK_NAMES = {
    "space": 0x20, "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B,
    "backspace": 0x08, "pause": 0x13, "break": 0x13, "insert": 0x2D, "ins": 0x2D,
    "delete": 0x2E, "del": 0x2E, "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "scrolllock": 0x91, "capslock": 0x14, "`": 0xC0, "/": 0xBF, "\\": 0xDC, ";": 0xBA,
    "'": 0xDE, ",": 0xBC, ".": 0xBE, "[": 0xDB, "]": 0xDD, "-": 0xBD, "=": 0xBB,
    **{f"f{i}": 0x6F + i for i in range(1, 25)},
}
MOD_NAMES = {"ctrl": "ctrl", "control": "ctrl", "shift": "shift", "alt": "alt", "win": "win"}


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("u", _INPUTUNION)]


HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype = wt.HHOOK
user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [wt.HHOOK]
user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.GetForegroundWindow.restype = wt.HWND
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.OpenClipboard.argtypes = [wt.HWND]
user32.GetClipboardData.argtypes = [wt.UINT]
user32.GetClipboardData.restype = wt.HANDLE
user32.SetClipboardData.argtypes = [wt.UINT, wt.HANDLE]
user32.SetClipboardData.restype = wt.HANDLE
user32.RegisterClipboardFormatW.argtypes = [wt.LPCWSTR]
user32.GetClipboardSequenceNumber.restype = wt.DWORD
kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
kernel32.GetModuleHandleW.restype = wt.HMODULE
kernel32.GlobalAlloc.argtypes = [wt.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wt.HGLOBAL
kernel32.GlobalLock.argtypes = [wt.HGLOBAL]
kernel32.GlobalLock.restype = wt.LPVOID
kernel32.GlobalUnlock.argtypes = [wt.HGLOBAL]
kernel32.GlobalSize.argtypes = [wt.HGLOBAL]
kernel32.GlobalSize.restype = ctypes.c_size_t
kernel32.GlobalFree.argtypes = [wt.HGLOBAL]
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.CreateMutexW.argtypes = [wt.LPVOID, wt.BOOL, wt.LPCWSTR]
kernel32.CreateMutexW.restype = wt.HANDLE


# ---------------------------------------------------------------- hotkeys

class Hotkey:
    def __init__(self, spec: str):
        self.spec = spec
        mods, vk = set(), None
        for part in spec.lower().replace(" ", "").split("+"):
            if part in MOD_NAMES:
                mods.add(MOD_NAMES[part])
            elif part in VK_NAMES:
                vk = VK_NAMES[part]
            elif len(part) == 1 and part.isalnum():
                vk = ord(part.upper())
            else:
                raise ValueError(f"Неизвестная клавиша '{part}' в '{spec}'")
        if vk is None:
            raise ValueError(f"В '{spec}' нет основной клавиши")
        self.mods = frozenset(mods)
        self.vk = vk


def _down(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def current_mods() -> frozenset:
    mods = set()
    if _down(VK_CONTROL):
        mods.add("ctrl")
    if _down(VK_SHIFT):
        mods.add("shift")
    if _down(VK_MENU):
        mods.add("alt")
    if _down(VK_LWIN) or _down(VK_RWIN):
        mods.add("win")
    return frozenset(mods)


# ------------------------------------------------------------------- hook

class KeyboardHook:
    """Global low-level hook. `handler(vk, mods)` returns True to swallow a key press."""

    def __init__(self, handler: Callable[[int, frozenset], bool]):
        self.handler = handler
        self._swallowed_up: set[int] = set()
        self._proc = HOOKPROC(self._callback)  # keep a reference against GC
        self._thread_id = 0
        self._ready = threading.Event()

    def _callback(self, code: int, wparam: int, lparam: int) -> int:
        try:
            if code == 0:
                kb = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if not kb.flags & LLKHF_INJECTED and kb.vkCode not in MODIFIER_VKS:
                    if wparam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        if self.handler(kb.vkCode, current_mods()):
                            self._swallowed_up.add(kb.vkCode)
                            return 1
                    elif wparam in (WM_KEYUP, WM_SYSKEYUP) and kb.vkCode in self._swallowed_up:
                        self._swallowed_up.discard(kb.vkCode)
                        return 1
        except Exception:  # never break the user's keyboard
            pass
        return user32.CallNextHookEx(None, code, wparam, lparam)

    def _run(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()
        hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0)
        self._ready.set()
        if not hook:
            return
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            pass
        user32.UnhookWindowsHookEx(hook)

    def start(self) -> None:
        threading.Thread(target=self._run, name="kbhook", daemon=True).start()
        self._ready.wait(2)

    def stop(self) -> None:
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)


# -------------------------------------------------------------- SendInput

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x2


def _key_input(vk: int, up: bool) -> INPUT:
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.u.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP if up else 0, time=0, dwExtraInfo=0)
    return inp


def send_keys(events: list[tuple[int, bool]]) -> None:
    arr = (INPUT * len(events))(*(_key_input(vk, up) for vk, up in events))
    user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))


def tap(vk: int, ctrl: bool = False) -> None:
    ev = [(VK_CONTROL, False)] if ctrl else []
    ev += [(vk, False), (vk, True)]
    if ctrl:
        ev.append((VK_CONTROL, True))
    send_keys(ev)


def release_modifiers() -> None:
    """Logically release modifiers the user still holds after pressing a hotkey."""
    held = [vk for vk in (0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, VK_LWIN, VK_RWIN) if _down(vk)]
    if not held:
        return
    ev: list[tuple[int, bool]] = []
    if any(vk in (0xA4, 0xA5, VK_LWIN, VK_RWIN) for vk in held):
        # A lone Alt/Win release would open the menu bar / Start menu.
        ev += [(0xE8, False), (0xE8, True)]
    ev += [(vk, True) for vk in held]
    send_keys(ev)


# -------------------------------------------------------------- clipboard

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x2
_EXCLUDE_FMT = user32.RegisterClipboardFormatW("ExcludeClipboardContentFromMonitorProcessing")


def _open_clipboard() -> bool:
    for _ in range(50):
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.005)
    return False


def clipboard_seq() -> int:
    return user32.GetClipboardSequenceNumber()


def get_clipboard_text() -> str | None:
    if not _open_clipboard():
        return None
    try:
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return None
        p = kernel32.GlobalLock(h)
        if not p:
            return None
        try:
            raw = ctypes.string_at(p, kernel32.GlobalSize(h))
        finally:
            kernel32.GlobalUnlock(h)
        text = raw.decode("utf-16-le", errors="replace")
        return text.split("\0", 1)[0]
    finally:
        user32.CloseClipboard()


def _global_bytes(data: bytes) -> int:
    h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    p = kernel32.GlobalLock(h)
    ctypes.memmove(p, data, len(data))
    kernel32.GlobalUnlock(h)
    return h


def set_clipboard_text(text: str) -> bool:
    """Put text on the clipboard, hidden from Win+V clipboard history."""
    if not _open_clipboard():
        return False
    try:
        user32.EmptyClipboard()
        h = _global_bytes((text + "\0").encode("utf-16-le"))
        if not user32.SetClipboardData(CF_UNICODETEXT, h):
            kernel32.GlobalFree(h)
            return False
        hx = _global_bytes(b"\0\0\0\0")
        if not user32.SetClipboardData(_EXCLUDE_FMT, hx):
            kernel32.GlobalFree(hx)
        return True
    finally:
        user32.CloseClipboard()


# ------------------------------------------------------------ foreground

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_proc_cache: dict[int, str] = {}


def foreground_window() -> int:
    return user32.GetForegroundWindow() or 0


def foreground_process() -> str:
    """Lowercase exe name of the foreground window, e.g. 'discord.exe'."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value in _proc_cache:
        return _proc_cache[pid.value]
    name = ""
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if h:
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wt.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                name = os.path.basename(buf.value).lower()
        finally:
            kernel32.CloseHandle(h)
    if len(_proc_cache) > 256:
        _proc_cache.clear()
    _proc_cache[pid.value] = name
    return name


def single_instance(name: str) -> bool:
    ctypes.set_last_error(0)
    kernel32.CreateMutexW(None, False, name)
    return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS
