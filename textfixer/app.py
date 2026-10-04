import ctypes
import logging
import os
import queue
import sys
import threading
import time
import winreg
from dataclasses import replace

import pystray
from PIL import Image, ImageDraw, ImageFont

from . import __version__, i18n, updater
from . import config as config_mod
from . import winapi as w
from .layout import fix_layout
from .i18n import t
from .llm import Corrector, LlmError
from .settings_ui import SettingsWindow

log = logging.getLogger("textfixer")

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "TextFixer"
UPDATE_CHECK_INTERVAL_S = 6 * 3600


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
        i18n.set_language(self.cfg.language)
        self.corrector = Corrector(self.cfg)
        self.hotkeys: dict[str, w.Hotkey] = {}
        self._apply_hotkeys(self.cfg)
        self.settings: SettingsWindow | None = None
        self.update: updater.Release | None = None
        self._updating = False
        self._check_now = threading.Event()
        self.hook = w.KeyboardHook(self._on_key)
        self.icon = pystray.Icon("textfixer", ICON_IDLE, t("tray.title", style=self.cfg.style.name), self._menu())

    # ------------------------------------------------------------ config

    def _apply_hotkeys(self, cfg: config_mod.Config) -> None:
        hk = {}
        for name, spec in (("fix", cfg.hotkey_fix), ("fix_and_send", cfg.hotkey_fix_and_send),
                           ("layout", cfg.hotkey_layout)):
            if spec:
                hk[name] = w.Hotkey(spec)
        self.hotkeys = hk

    def apply_config(self, cfg: config_mod.Config) -> str | None:
        """Apply and persist settings from the settings window. Returns an error message."""
        # Built-in styles follow the (possibly new) UI language.
        cfg = replace(cfg, styles=config_mod.localize_builtin(cfg.styles, cfg.language))
        try:
            self._apply_hotkeys(cfg)
            config_mod.save(cfg)
        except (ValueError, OSError) as e:
            self._apply_hotkeys(self.cfg)
            return str(e)
        self.cfg = cfg
        i18n.set_language(cfg.language)
        old, self.corrector = self.corrector, Corrector(cfg)
        old.close()
        self.icon.title = t("tray.title", style=cfg.style.name)
        self.icon.update_menu()
        log.info("settings saved, models=%s", ", ".join(cfg.models))
        return None

    def test_connection(self, cfg: config_mod.Config) -> str:
        corrector = Corrector(cfg)
        try:
            out, dt = corrector.correct(t("test.sample"), cfg.style)
            return t("test.ok", model=corrector.last_model, ms=f"{dt * 1000:.0f}", text=out)
        except LlmError as e:
            return t("test.fail", error=e)
        finally:
            corrector.close()

    def open_settings(self, tab: str | None = None) -> None:
        if self.settings:
            self.settings.raise_request.set()
            return

        def closed():
            self.settings = None

        self.settings = SettingsWindow(self.cfg, self.apply_config, self.test_connection, closed, tab)
        threading.Thread(target=self.settings.run, name="settings", daemon=True).start()

    # -------------------------------------------------------------- hook

    def _on_key(self, vk: int, mods: frozenset) -> bool:
        """Runs inside the keyboard hook: must be fast, no I/O besides WinAPI."""
        # While the settings window is open, let hotkeys through so they can be recorded.
        for name, hk in self.hotkeys.items() if not self.settings else ():
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
                self.notify(t("notify.error", error=e))
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
                self.notify(t("notify.too_long", max=cfg.max_chars))
            else:
                self.icon.icon = ICON_BUSY
                try:
                    prev_model = self.corrector.last_model
                    fixed, dt = self.corrector.correct(fixed, cfg.style)
                    llm_ms = dt * 1000
                    if self.corrector.last_model != prev_model and prev_model:
                        self.notify(t("notify.model_switched", model=self.corrector.last_model))
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
            self.notify(t("notify.window_changed"))
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
            config_mod.save(self.cfg)
        except OSError:
            log.exception("save style failed")
        self.icon.title = t("tray.title", style=self.cfg.style.name)

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
        try:
            config_mod.save(self.cfg)
        except OSError:
            log.exception("save failed")

    @staticmethod
    def _autostart_cmd() -> str:
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}" --autostart'
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        script = config_mod.ROOT / "textfixer.pyw"
        return f'"{pythonw}" "{script}" --autostart'

    def _sync_autostart(self) -> None:
        """Point an existing autostart entry at this exe (e.g. after reinstalling elsewhere)."""
        if not getattr(sys, "frozen", False) or not self._autostart_enabled():
            return
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as k:
                if winreg.QueryValueEx(k, RUN_NAME)[0] != self._autostart_cmd():
                    winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, self._autostart_cmd())
                    log.info("autostart entry updated")
        except OSError:
            log.exception("autostart sync failed")

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

    # ----------------------------------------------------------- updates

    def _update_loop(self) -> None:
        notified = ""
        self._check_now.wait(20)  # don't slow down startup
        while True:
            if self.cfg.check_updates or self._check_now.is_set():
                manual = self._check_now.is_set()
                try:
                    self.update = updater.check(self.cfg.proxy)
                    self.icon.update_menu()
                    if self.update and (self.update.version != notified or manual):
                        notified = self.update.version
                        self.notify(t("notify.update_available", version=self.update.version))
                    elif manual:
                        self.notify(t("notify.up_to_date", version=__version__))
                except updater.UpdateError as e:
                    log.warning("update check: %s", e)
                    if manual:
                        self.notify(t("notify.update_check_failed", error=e))
            self._check_now.clear()
            self._check_now.wait(UPDATE_CHECK_INTERVAL_S)

    def _update_action(self) -> None:
        if not self.update:
            self._check_now.set()
            return
        if not updater.is_installed():
            self.notify(t("notify.update_only_installed"))
            return
        if self._updating:
            return
        self._updating = True
        threading.Thread(target=self._do_update, args=(self.update,), name="update", daemon=True).start()

    def _do_update(self, rel: updater.Release) -> None:
        try:
            self.notify(t("notify.downloading", version=rel.version))
            self.icon.icon = ICON_BUSY
            updater.download(rel, self.cfg.proxy)
            log.info("update: %s downloaded, applying", rel.version)
            updater.launch_apply()
            self.quit()
        except Exception as e:
            log.exception("update failed")
            self.icon.icon = ICON_ERROR
            self.notify(t("notify.update_failed", error=e))
            self._updating = False

    def _update_label(self, item) -> str:
        if self._updating:
            return t("menu.updating")
        if self.update:
            return t("menu.update_to", version=self.update.version)
        return t("menu.check_updates", version=__version__)

    def _menu(self) -> pystray.Menu:
        def hk_label(item):
            return t("menu.hotkeys", fix=self.cfg.hotkey_fix, send=self.cfg.hotkey_fix_and_send,
                     layout=self.cfg.hotkey_layout)

        return pystray.Menu(
            pystray.MenuItem(hk_label, None, enabled=False),
            pystray.MenuItem(lambda item: t("menu.model", model=self.corrector.last_model or self.cfg.models[0]),
                             None, enabled=False),
            pystray.MenuItem(lambda item: t("menu.style", style=self.cfg.style.name), pystray.Menu(self._style_items)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: t("menu.auto_enter"), self._toggle_auto_enter,
                             checked=lambda item: self.cfg.auto_enter),
            pystray.MenuItem(lambda item: t("menu.autostart"), self._toggle_autostart,
                             checked=self._autostart_enabled),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: t("menu.settings"), lambda: self.open_settings(), default=True),
            pystray.MenuItem(lambda item: t("menu.data_folder"), lambda: os.startfile(config_mod.DATA_DIR)),
            pystray.MenuItem(self._update_label, lambda: self._update_action()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: t("menu.quit"), self.quit),
        )

    def quit(self) -> None:
        self.hook.stop()
        self.jobs.put((None, 0))
        self.corrector.close()
        self.icon.stop()

    def run(self) -> None:
        threading.Thread(target=self._worker, name="worker", daemon=True).start()
        self.hook.start()
        self._sync_autostart()
        threading.Thread(target=self._update_loop, name="updates", daemon=True).start()
        if "--updated" in sys.argv:
            # Give the tray a moment; if we crash before this, the apply script rolls back.
            threading.Timer(3, updater.mark_started).start()
            threading.Timer(3.5, self.notify, args=(t("notify.updated", version=__version__),)).start()
        elif "--update-failed" in sys.argv:
            threading.Timer(1.5, self.notify, args=(t("notify.update_rolled_back"),)).start()
        log.info("started %s%s, %s, models=%s", __version__, " (autostart)" if "--autostart" in sys.argv else "",
                 sys.executable, ", ".join(self.cfg.models))
        self.icon.run()


def main() -> None:
    config_mod.DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # crisp settings window on HiDPI
    except (AttributeError, OSError):
        pass
    logging.basicConfig(
        filename=config_mod.LOG_PATH, level=logging.INFO, encoding="utf-8",
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if not w.single_instance("Local\\TextFixerSingleInstance"):
        return
    try:
        config_mod.ensure_config()
        app = App()
        if not app.cfg.api_key:
            threading.Timer(1.0, app.open_settings, args=("help",)).start()
            threading.Timer(1.5, app.notify, args=(t("notify.ask_api_key"),)).start()
        app.run()
    except Exception:
        log.exception("fatal error")  # pythonw has no console, the log is the only trace
        raise
