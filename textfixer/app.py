import logging
import os
import queue
import sys
import threading
import time
import winreg

import pystray
from PIL import Image, ImageDraw, ImageFont

from . import config as config_mod
from . import winapi as w
from .layout import fix_layout
from .llm import Corrector, LlmError

log = logging.getLogger("textfixer")

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "TextFixer"


def _icon(color: str) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2, 2, 62, 62), radius=14, fill=color)
    try:
        font = ImageFont.truetype("segoeuib.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    d.text((32, 33), "Aa", fill="white", font=font, anchor="mm")
    return img


ICON_IDLE = _icon("#3b82f6")
ICON_BUSY = _icon("#f59e0b")
ICON_ERROR = _icon("#ef4444")


class App:
    def __init__(self) -> None:
        self.jobs: queue.Queue = queue.Queue()
        self.cfg = config_mod.load()
        self.corrector = Corrector(self.cfg)
        self.hotkeys: dict[str, w.Hotkey] = {}
        self._apply_hotkeys()
        self.hook = w.KeyboardHook(self._on_key)
        self.icon = pystray.Icon("textfixer", ICON_IDLE, f"TextFixer — {self.cfg.style.name}", self._menu())

    # ------------------------------------------------------------ config

    def _apply_hotkeys(self) -> None:
        hk = {}
        for name, spec in (("fix", self.cfg.hotkey_fix), ("fix_and_send", self.cfg.hotkey_fix_and_send),
                           ("layout", self.cfg.hotkey_layout)):
            if spec:
                hk[name] = w.Hotkey(spec)
        self.hotkeys = hk

    def reload(self) -> None:
        try:
            cfg = config_mod.load()
            self.cfg = cfg
            self._apply_hotkeys()
            old, self.corrector = self.corrector, Corrector(cfg)
            old.close()
            self.icon.update_menu()
            self.notify("Настройки перечитаны")
        except Exception as e:
            log.exception("reload failed")
            self.notify(f"Ошибка в config.toml: {e}")

    # -------------------------------------------------------------- hook

    def _on_key(self, vk: int, mods: frozenset) -> bool:
        """Runs inside the keyboard hook: must be fast, no I/O besides WinAPI."""
        for name, hk in self.hotkeys.items():
            if hk.vk == vk and hk.mods == mods:
                self.jobs.put((name, w.foreground_window()))
                return True
        if (vk == w.VK_RETURN and not mods and self.cfg.auto_enter
                and w.foreground_process() in self.cfg.auto_enter_apps):
            self.jobs.put(("enter", w.foreground_window()))
            return True
        return False

    # ------------------------------------------------------------ worker

    def _worker(self) -> None:
        while True:
            job, hwnd = self.jobs.get()
            if job is None:
                return
            try:
                self._run_job(job, hwnd)
            except Exception as e:
                log.exception("job %s failed", job)
                self.notify(f"Ошибка: {e}")
                if job == "enter":
                    w.tap(w.VK_RETURN)  # never swallow the user's Enter
            finally:
                self.icon.icon = ICON_IDLE

    def _grab(self, timeout_ms: int) -> tuple[str | None, str | None]:
        """Select all + copy. Returns (text in field, previous clipboard text)."""
        saved = w.get_clipboard_text()
        seq = w.clipboard_seq()
        w.tap(ord("A"), ctrl=True)
        # Electron apps (Discord) apply the selection asynchronously; an
        # immediate Ctrl+C would copy nothing.
        time.sleep(self.cfg.select_delay_ms / 1000)
        w.tap(ord("C"), ctrl=True)
        start = time.perf_counter()
        retried = False
        while (elapsed := time.perf_counter() - start) < timeout_ms / 1000:
            if w.clipboard_seq() != seq:
                time.sleep(0.01)  # let the app finish writing all formats
                return w.get_clipboard_text(), saved
            if not retried and elapsed > timeout_ms / 2000:
                w.tap(ord("C"), ctrl=True)
                retried = True
            time.sleep(0.003)
        return None, saved

    def _paste(self, text: str) -> None:
        w.set_clipboard_text(text)
        w.tap(ord("A"), ctrl=True)
        time.sleep(self.cfg.select_delay_ms / 1000)
        w.tap(ord("V"), ctrl=True)

    def _restore_later(self, saved: str | None) -> None:
        if saved is None:
            return
        delay = self.cfg.clipboard_restore_ms / 1000
        threading.Timer(delay, w.set_clipboard_text, args=(saved,)).start()

    def _run_job(self, job: str, hwnd: int) -> None:
        t0 = time.perf_counter()
        cfg = self.cfg
        if job != "enter":
            w.release_modifiers()
        text, saved = self._grab(cfg.enter_copy_timeout_ms if job == "enter" else cfg.copy_timeout_ms)

        if text is None or not text.strip() or (job == "enter" and len(text) > cfg.max_chars):
            # Plain Enter must still work; fix_and_send never sends unchecked text.
            if job == "enter":
                w.tap(w.VK_RETURN)
            self._restore_later(saved)
            log.info("%s: nothing to fix (%.0f ms)", job, (time.perf_counter() - t0) * 1000)
            return

        fixed = fix_layout(text)
        llm_ms = 0.0
        if job in ("fix", "fix_and_send"):
            if len(fixed) > cfg.max_chars:
                self.notify(f"Текст длиннее {cfg.max_chars} символов — исправлена только раскладка")
            else:
                self.icon.icon = ICON_BUSY
                try:
                    prev_model = self.corrector.last_model
                    fixed, dt = self.corrector.correct(fixed, cfg.style)
                    llm_ms = dt * 1000
                    if self.corrector.last_model != prev_model and prev_model:
                        self.notify(f"Модель: {self.corrector.last_model}")
                        self.icon.update_menu()
                except LlmError as e:
                    log.warning("llm: %s", e)
                    self.icon.icon = ICON_ERROR
                    self.notify(str(e))
                    if job == "fix_and_send":
                        # Don't send a message the user wanted fixed first.
                        if fixed != text:
                            self._paste(fixed)
                        self._restore_later(saved)
                        return

        if w.foreground_window() != hwnd:
            # The user switched windows while we waited for the model.
            w.set_clipboard_text(fixed)
            self.notify("Окно сменилось — исправленный текст лежит в буфере обмена")
            return

        if fixed != text:
            self._paste(fixed)
        if job in ("enter", "fix_and_send"):
            if fixed != text:
                time.sleep(cfg.paste_settle_ms / 1000)
            w.tap(w.VK_RETURN)
        self._restore_later(saved)
        log.info("%s: %d chars, changed=%s, llm %.0f ms (%s), total %.0f ms", job, len(text),
                 fixed != text, llm_ms, self.corrector.last_model if llm_ms else "-",
                 (time.perf_counter() - t0) * 1000)

    # -------------------------------------------------------------- tray

    def notify(self, msg: str) -> None:
        try:
            self.icon.notify(msg, "TextFixer")
        except Exception:
            pass

    def _set_style(self, key: str) -> None:
        self.cfg.active_style = key
        try:
            config_mod.save_active_style(key)
        except OSError:
            log.exception("save style failed")
        self.icon.title = f"TextFixer — {self.cfg.style.name}"

    def _style_item(self, key: str, name: str) -> pystray.MenuItem:
        # pystray inspects the arity of callbacks, so no default-arg lambdas here.
        def action(icon, item):
            self._set_style(key)

        def checked(item):
            return self.cfg.active_style == key

        return pystray.MenuItem(name, action, checked=checked, radio=True)

    def _style_items(self):
        return [self._style_item(key, st.name) for key, st in self.cfg.styles.items()]

    def _toggle_auto_enter(self, icon, item) -> None:
        self.cfg.auto_enter = not self.cfg.auto_enter

    @staticmethod
    def _autostart_cmd() -> str:
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        script = config_mod.ROOT / "textfixer.pyw"
        return f'"{pythonw}" "{script}"'

    def _autostart_enabled(self, item=None) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
                winreg.QueryValueEx(k, RUN_NAME)
                return True
        except OSError:
            return False

    def _toggle_autostart(self, icon, item) -> None:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if self._autostart_enabled():
                winreg.DeleteValue(k, RUN_NAME)
            else:
                winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, self._autostart_cmd())

    def _menu(self) -> pystray.Menu:
        def hk_label(item):
            return (f"Исправить: {self.cfg.hotkey_fix} · с отправкой: {self.cfg.hotkey_fix_and_send}"
                    f" · раскладка: {self.cfg.hotkey_layout}")

        return pystray.Menu(
            pystray.MenuItem(hk_label, None, enabled=False),
            pystray.MenuItem(lambda item: f"Модель: {self.corrector.last_model or self.cfg.models[0]}",
                             None, enabled=False),
            pystray.MenuItem(lambda item: f"Стиль: {self.cfg.style.name}", pystray.Menu(self._style_items)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Исправлять раскладку по Enter", self._toggle_auto_enter,
                             checked=lambda item: self.cfg.auto_enter),
            pystray.MenuItem("Запускать вместе с Windows", self._toggle_autostart,
                             checked=self._autostart_enabled),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Открыть настройки", lambda: os.startfile(config_mod.CONFIG_PATH)),
            pystray.MenuItem("Перечитать настройки", lambda: self.reload()),
            pystray.MenuItem("Открыть лог", lambda: os.startfile(config_mod.LOG_PATH)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", self.quit),
        )

    def quit(self) -> None:
        self.hook.stop()
        self.jobs.put((None, 0))
        self.corrector.close()
        self.icon.stop()

    def run(self) -> None:
        threading.Thread(target=self._worker, name="worker", daemon=True).start()
        self.hook.start()
        log.info("started, models=%s", ", ".join(self.cfg.models))
        self.icon.run()


def main() -> None:
    logging.basicConfig(
        filename=config_mod.LOG_PATH, level=logging.INFO, encoding="utf-8",
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if not w.single_instance("Local\\TextFixerSingleInstance"):
        return
    try:
        created = config_mod.ensure_config()
        app = App()
        if created or not app.cfg.api_key:
            os.startfile(config_mod.CONFIG_PATH)
            threading.Timer(1.5, app.notify, args=("Впиши api_key в config.toml и нажми «Перечитать настройки»",)).start()
        app.run()
    except Exception:
        log.exception("fatal error")  # pythonw has no console, the log is the only trace
        raise
