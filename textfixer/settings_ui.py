"""Settings window (tkinter). Runs in its own thread; talks to the app via callbacks."""

import queue
import re
import threading
import tkinter as tk
from dataclasses import replace
from tkinter import messagebox, ttk
from typing import Callable

from . import config as config_mod
from . import i18n
from . import winapi as w
from .config import Config, Style
from .i18n import t

# Tk keysym -> our hotkey key name
_KEYSYMS = {"space": "space", "Return": "enter", "Pause": "pause", "Tab": "tab", "Insert": "insert",
            "Delete": "delete", "Home": "home", "End": "end", "Prior": "pageup", "Next": "pagedown",
            "Scroll_Lock": "scrolllock"}
_MODIFIER_KEYSYMS = {"Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R", "Win_L", "Win_R",
                     "Meta_L", "Meta_R", "Caps_Lock"}


class SettingsWindow:
    def __init__(self, cfg: Config, on_save: Callable[[Config], str | None],
                 on_test: Callable[[Config], str], on_close: Callable[[], None],
                 initial_tab: str | None = None):
        self.cfg = replace(cfg, styles={k: replace(s) for k, s in cfg.styles.items()})
        self.on_save = on_save
        self.on_test = on_test
        self.on_close = on_close
        self.initial_tab = initial_tab
        self.raise_request = threading.Event()
        self._results: queue.Queue = queue.Queue()

    # ------------------------------------------------------------ helpers

    def _row(self, parent, r: int, label: str, widget, hint: str = "") -> None:
        ttk.Label(parent, text=label).grid(row=r, column=0, sticky="nw", padx=(0, 10), pady=4)
        widget.grid(row=r, column=1, sticky="ew", pady=4)
        if hint:
            ttk.Label(parent, text=hint, foreground="#666", wraplength=420, justify="left").grid(
                row=r + 1, column=1, sticky="w", pady=(0, 6))

    def _tab(self, title: str) -> ttk.Frame:
        f = ttk.Frame(self.nb, padding=14)
        f.columnconfigure(1, weight=1)
        self.nb.add(f, text=title)
        return f

    @staticmethod
    def _text(parent, height: int, value: str) -> tk.Text:
        box = tk.Text(parent, height=height, width=50, wrap="word", font=("Segoe UI", 10), undo=True)
        box.insert("1.0", value)
        return box

    # --------------------------------------------------------------- tabs

    def _build_api(self) -> None:
        f = self._tab(t("settings.tab.api"))
        c = self.cfg
        self.v_key = tk.StringVar(value=c.api_key)
        key_box = ttk.Frame(f)
        key_box.columnconfigure(0, weight=1)
        self.e_key = ttk.Entry(key_box, textvariable=self.v_key, show="•")
        self.e_key.grid(row=0, column=0, sticky="ew")
        self.v_show = tk.BooleanVar()
        ttk.Checkbutton(key_box, text=t("settings.show"), variable=self.v_show,
                        command=lambda: self.e_key.config(show="" if self.v_show.get() else "•")).grid(
            row=0, column=1, padx=(8, 0))
        self._row(f, 0, t("settings.api_key"), key_box)

        self.v_url = tk.StringVar(value=c.base_url)
        self._row(f, 2, t("settings.base_url"), ttk.Entry(f, textvariable=self.v_url), t("settings.base_url.hint"))

        self.t_models = self._text(f, 4, "\n".join(c.models))
        self._row(f, 4, t("settings.models"), self.t_models, t("settings.models.hint"))

        proxy_system, proxy_direct = t("settings.proxy.system"), t("settings.proxy.direct")
        proxy_value = proxy_system if not c.proxy else proxy_direct if c.proxy == "direct" else c.proxy
        self.v_proxy = tk.StringVar(value=proxy_value)
        self._row(f, 6, t("settings.proxy"), ttk.Combobox(f, textvariable=self.v_proxy,
                  values=[proxy_system, proxy_direct, "http://127.0.0.1:10809"]), t("settings.proxy.hint"))

        self.v_effort = tk.StringVar(value=c.reasoning_effort or "—")
        self._row(f, 8, t("settings.effort"), ttk.Combobox(f, textvariable=self.v_effort, state="readonly",
                  values=["low", "medium", "high", "—"], width=10), t("settings.effort.hint"))

        nums = ttk.Frame(f)
        self.v_timeout = tk.StringVar(value=f"{c.timeout_s:g}")
        self.v_maxchars = tk.StringVar(value=str(c.max_chars))
        ttk.Label(nums, text=t("settings.timeout")).pack(side="left")
        ttk.Spinbox(nums, from_=2, to=60, textvariable=self.v_timeout, width=6).pack(side="left", padx=(6, 18))
        ttk.Label(nums, text=t("settings.max_chars")).pack(side="left")
        ttk.Spinbox(nums, from_=100, to=20000, increment=500, textvariable=self.v_maxchars,
                    width=8).pack(side="left", padx=6)
        self._row(f, 10, t("settings.limits"), nums)

        self.v_updates = tk.BooleanVar(value=c.check_updates)
        ttk.Checkbutton(f, text=t("settings.check_updates"), variable=self.v_updates).grid(
            row=11, column=1, sticky="w", pady=(8, 0))

        test = ttk.Frame(f)
        test.grid(row=12, column=1, sticky="ew", pady=(14, 0))
        self.b_test = ttk.Button(test, text=t("settings.test"), command=self._test)
        self.b_test.pack(side="left")
        self.v_test = tk.StringVar()
        ttk.Label(test, textvariable=self.v_test, wraplength=300, justify="left").pack(side="left", padx=10)

    def _build_hotkeys(self) -> None:
        f = self._tab(t("settings.tab.hotkeys"))
        c = self.cfg
        self.v_hk = {}
        rows = [("fix", c.hotkey_fix), ("fix_and_send", c.hotkey_fix_and_send), ("layout", c.hotkey_layout)]
        for i, (key, value) in enumerate(rows):
            v = tk.StringVar(value=value)
            self.v_hk[key] = v
            box = ttk.Frame(f)
            box.columnconfigure(0, weight=1)
            e = ttk.Entry(box, textvariable=v)
            e.grid(row=0, column=0, sticky="ew")
            ttk.Button(box, text=t("settings.hk.record"), command=lambda v=v, e=e: self._record(v, e)).grid(
                row=0, column=1, padx=(8, 0))
            self._row(f, i * 2, t(f"settings.hk.{key}"), box, t(f"settings.hk.{key}.hint"))
        ttk.Label(f, foreground="#666", wraplength=520, justify="left", text=t("settings.hk.help")).grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _build_enter(self) -> None:
        f = self._tab(t("settings.tab.enter"))
        self.v_auto = tk.BooleanVar(value=self.cfg.auto_enter)
        ttk.Checkbutton(f, text=t("settings.enter.enabled"), variable=self.v_auto).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        self.t_apps = self._text(f, 6, "\n".join(self.cfg.auto_enter_apps))
        self._row(f, 1, t("settings.enter.apps"), self.t_apps, t("settings.enter.apps.hint"))

    def _build_styles(self) -> None:
        f = self._tab(t("settings.tab.styles"))
        f.columnconfigure(1, weight=1)
        f.rowconfigure(0, weight=1)
        left = ttk.Frame(f)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        self.lb_styles = tk.Listbox(left, height=10, width=18, exportselection=False, font=("Segoe UI", 10))
        self.lb_styles.pack(fill="y", expand=True)
        self.lb_styles.bind("<<ListboxSelect>>", lambda e: self._select_style())
        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text=t("settings.style.add"), command=self._add_style).pack(side="left", expand=True, fill="x")
        ttk.Button(btns, text=t("settings.style.delete"), command=self._del_style).pack(side="left", expand=True, fill="x", padx=(4, 0))
        self.b_reset = ttk.Button(left, text=t("settings.style.reset"), command=self._reset_style)
        self.b_reset.pack(fill="x", pady=(4, 0))

        right = ttk.Frame(f)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(1, weight=1)
        right.rowconfigure(4, weight=1)
        self.v_sname = tk.StringVar()
        self._row(right, 0, t("settings.style.name"), ttk.Entry(right, textvariable=self.v_sname))
        self.v_rewrite = tk.BooleanVar()
        self.v_strip = tk.BooleanVar()
        ttk.Checkbutton(right, text=t("settings.style.rewrite"), variable=self.v_rewrite).grid(
            row=1, column=1, sticky="w")
        ttk.Checkbutton(right, text=t("settings.style.strip"), variable=self.v_strip).grid(
            row=2, column=1, sticky="w", pady=(0, 6))
        ttk.Label(right, text=t("settings.style.prompt")).grid(row=3, column=0, sticky="nw", padx=(0, 10))
        self.t_prompt = self._text(right, 10, "")
        self.t_prompt.grid(row=3, column=1, rowspan=2, sticky="nsew")
        ttk.Label(right, foreground="#666", wraplength=420, justify="left", text=t("settings.style.hint")).grid(row=5, column=1, sticky="w", pady=(6, 0))
        self.v_sorigin = tk.StringVar()
        ttk.Label(right, textvariable=self.v_sorigin, wraplength=420, justify="left").grid(
            row=6, column=1, sticky="w", pady=(4, 0))

        self._style_keys: list[str] = []
        self._cur_style: str | None = None
        self._refresh_styles(self.cfg.active_style)

    def _build_timing(self) -> None:
        f = self._tab(t("settings.tab.timing"))
        c = self.cfg
        self.v_timing = {}
        self.timing_labels = {}
        rows = [("select_delay_ms", "select_delay", True), ("copy_timeout_ms", "copy_timeout", True),
                ("enter_copy_timeout_ms", "enter_copy_timeout", True), ("paste_settle_ms", "paste_settle", False),
                ("clipboard_restore_ms", "clipboard_restore", False)]
        for i, (key, name, has_hint) in enumerate(rows):
            value = getattr(c, key)
            label = t(f"settings.timing.{name}")
            hint = t(f"settings.timing.{name}.hint") if has_hint else ""
            self.timing_labels[key] = label
            v = tk.StringVar(value=str(value))
            self.v_timing[key] = v
            box = ttk.Frame(f)
            ttk.Spinbox(box, from_=0, to=5000, increment=10, textvariable=v, width=8).pack(side="left")
            ttk.Label(box, text=t("settings.ms")).pack(side="left", padx=6)
            self._row(f, i * 2, label, box, hint)

    # ------------------------------------------------------------- styles

    def _refresh_styles(self, select: str | None) -> None:
        self._style_keys = list(self.cfg.styles)
        self.lb_styles.delete(0, "end")
        for k in self._style_keys:
            mark = "  ✓" if k == self.cfg.active_style else ""
            self.lb_styles.insert("end", self.cfg.styles[k].name + mark)
        if select in self._style_keys:
            i = self._style_keys.index(select)
            self.lb_styles.selection_set(i)
            self._cur_style = None
            self._select_style()

    def _store_style(self) -> None:
        if self._cur_style and self._cur_style in self.cfg.styles:
            s = self.cfg.styles[self._cur_style]
            new = (self.v_sname.get().strip() or s.key, self.v_rewrite.get(), self.v_strip.get(),
                   self.t_prompt.get("1.0", "end").strip())
            if new != (s.name, s.rewrite, s.strip_final_period, s.prompt):
                s.name, s.rewrite, s.strip_final_period, s.prompt = new
                s.builtin = False  # edited: from now on it's the user's own text

    def _select_style(self) -> None:
        sel = self.lb_styles.curselection()
        if not sel:
            return
        self._store_style()
        key = self._style_keys[sel[0]]
        self._cur_style = key
        s = self.cfg.styles[key]
        self.v_sname.set(s.name)
        self.v_rewrite.set(s.rewrite)
        self.v_strip.set(s.strip_final_period)
        self.t_prompt.delete("1.0", "end")
        self.t_prompt.insert("1.0", s.prompt)
        self.v_sorigin.set(t("settings.style.builtin") if s.builtin else t("settings.style.custom"))
        can_reset = not s.builtin and config_mod.builtin_style(key, self.cfg.language) is not None
        self.b_reset.state(["!disabled" if can_reset else "disabled"])

    def _reset_style(self) -> None:
        key = self._cur_style
        builtin = key and config_mod.builtin_style(key, self.cfg.language)
        if builtin:
            self.cfg.styles[key] = builtin
            self._cur_style = None
            self._refresh_styles(key)

    def _build_help(self) -> None:
        f = self._tab(t("settings.tab.help"))
        f.rowconfigure(0, weight=1)
        text = t("settings.help.text", fix=self.cfg.hotkey_fix or "—",
                 send=self.cfg.hotkey_fix_and_send or "—", layout=self.cfg.hotkey_layout or "—")
        box = tk.Text(f, wrap="word", font=("Segoe UI", 10), relief="flat", padx=6, pady=4,
                      background=self.root.cget("background"))
        box.tag_configure("h", font=("Segoe UI Semibold", 11), spacing1=6, spacing3=2)
        paragraphs = text.split("\n\n")
        for i, para in enumerate(paragraphs):
            head, _, body = para.partition("\n")
            if body:
                box.insert("end", head + "\n", "h")
                box.insert("end", body)
            else:
                box.insert("end", head)
            if i < len(paragraphs) - 1:
                box.insert("end", "\n\n")
        box.config(state="disabled")
        f.columnconfigure(0, weight=1)
        f.columnconfigure(1, weight=0)
        scroll = ttk.Scrollbar(f, orient="vertical", command=box.yview)
        box.config(yscrollcommand=scroll.set)
        box.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.help_tab = f

    def _add_style(self) -> None:
        self._store_style()
        n = 1
        while f"style{n}" in self.cfg.styles:
            n += 1
        key = f"style{n}"
        self.cfg.styles[key] = Style(key, t("settings.style.new_name", n=n), t("settings.style.new_prompt"))
        self._cur_style = None
        self._refresh_styles(key)

    def _del_style(self) -> None:
        if len(self.cfg.styles) <= 1 or not self._cur_style:
            messagebox.showinfo("TextFixer", t("settings.style.keep_one"), parent=self.root)
            return
        del self.cfg.styles[self._cur_style]
        if self.cfg.active_style not in self.cfg.styles:
            self.cfg.active_style = next(iter(self.cfg.styles))
        self._cur_style = None
        self._refresh_styles(next(iter(self.cfg.styles)))

    # ------------------------------------------------------------ hotkeys

    def _record(self, var: tk.StringVar, entry: ttk.Entry) -> None:
        old = var.get()
        var.set(t("settings.hk.press"))
        entry.focus_set()

        def on_key(e):
            if e.keysym in _MODIFIER_KEYSYMS:
                return "break"
            if e.keysym == "Escape":
                var.set(old)
            elif e.keysym == "BackSpace":
                var.set("")
            else:
                ks = e.keysym
                key = _KEYSYMS.get(ks) or (ks.lower() if re.fullmatch(r"[A-Za-z0-9]|F\d{1,2}", ks) else None)
                if key is None and e.char and e.char.isalnum():
                    key = e.char.lower()
                if key is None:
                    return "break"  # unsupported key, keep waiting
                mods = []
                if e.state & 0x4:
                    mods.append("ctrl")
                if e.state & 0x1:
                    mods.append("shift")
                if e.state & 0x20000:
                    mods.append("alt")
                var.set("+".join(mods + [key]))
            entry.unbind("<KeyPress>")
            return "break"

        entry.bind("<KeyPress>", on_key)

    # -------------------------------------------------------- collect/save

    def _collect(self) -> Config:
        """Read the form into a Config. Raises ValueError with a readable message."""
        self._store_style()
        lines = lambda box: [x.strip() for x in box.get("1.0", "end").splitlines() if x.strip()]
        proxy = self.v_proxy.get().strip()
        proxy = ("" if proxy in ("", t("settings.proxy.system"))
                 else "direct" if proxy == t("settings.proxy.direct") else proxy)
        models = lines(self.t_models)
        if not models:
            raise ValueError(t("settings.err.no_models"))
        for name, v in self.v_hk.items():
            if v.get().strip():
                try:
                    w.Hotkey(v.get())
                except ValueError as e:
                    raise ValueError(str(e))
        specs = [v.get().strip().lower() for v in self.v_hk.values() if v.get().strip()]
        if len(specs) != len(set(specs)):
            raise ValueError(t("settings.err.duplicate_hotkey"))

        def num(v, name, cast=int):
            try:
                return cast(v.get())
            except ValueError:
                raise ValueError(t("settings.err.not_number", field=name))

        return replace(
            self.cfg,
            api_key=self.v_key.get().strip(),
            base_url=self.v_url.get().strip().rstrip("/"),
            models=models,
            proxy=proxy,
            reasoning_effort="" if self.v_effort.get() == "—" else self.v_effort.get(),
            timeout_s=num(self.v_timeout, t("settings.timeout"), float),
            max_chars=num(self.v_maxchars, t("settings.max_chars")),
            hotkey_fix=self.v_hk["fix"].get().strip(),
            hotkey_fix_and_send=self.v_hk["fix_and_send"].get().strip(),
            hotkey_layout=self.v_hk["layout"].get().strip(),
            auto_enter=self.v_auto.get(),
            check_updates=self.v_updates.get(),
            auto_enter_apps=[a.lower() for a in lines(self.t_apps)],
            language=self._language_code(),
            **{k: num(v, self.timing_labels[k]) for k, v in self.v_timing.items()},
        )

    def _language_code(self) -> str:
        names = {name: code for code, name in i18n.languages().items()}
        return names.get(self.v_lang.get(), self.cfg.language)

    def _save(self) -> None:
        try:
            cfg = self._collect()
        except ValueError as e:
            messagebox.showerror("TextFixer", str(e), parent=self.root)
            return
        err = self.on_save(cfg)
        if err:
            messagebox.showerror("TextFixer", err, parent=self.root)
            return
        self._close()

    def _test(self) -> None:
        try:
            cfg = self._collect()
        except ValueError as e:
            self.v_test.set(str(e))
            return
        self.b_test.state(["disabled"])
        self.v_test.set(t("settings.testing"))
        threading.Thread(target=lambda: self._results.put(self.on_test(cfg)), daemon=True).start()

    def _poll(self) -> None:
        try:
            while True:
                self.v_test.set(self._results.get_nowait())
                self.b_test.state(["!disabled"])
        except queue.Empty:
            pass
        if self.raise_request.is_set():
            self.raise_request.clear()
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        self.root.after(150, self._poll)

    def _close(self) -> None:
        self.root.destroy()

    # ---------------------------------------------------------------- run

    def run(self) -> None:
        try:
            self.root = tk.Tk()
            self.root.title(t("settings.title"))
            self.root.minsize(640, 520)
            try:
                ttk.Style(self.root).theme_use("vista")
            except tk.TclError:
                pass
            outer = ttk.Frame(self.root, padding=10)
            outer.pack(fill="both", expand=True)
            self.nb = ttk.Notebook(outer)
            self.nb.pack(fill="both", expand=True)
            self._build_api()
            self._build_hotkeys()
            self._build_enter()
            self._build_styles()
            self._build_timing()
            self._build_help()
            if self.initial_tab == "help":
                self.nb.select(self.help_tab)
            bar = ttk.Frame(outer)
            bar.pack(fill="x", pady=(10, 0))
            ttk.Label(bar, text=t("settings.language")).pack(side="left")
            self.v_lang = tk.StringVar(value=i18n.languages().get(self.cfg.language, "English"))
            ttk.Combobox(bar, textvariable=self.v_lang, state="readonly", width=14,
                         values=list(i18n.languages().values())).pack(side="left", padx=(8, 0))
            ttk.Button(bar, text=t("settings.cancel"), command=self._close).pack(side="right")
            ttk.Button(bar, text=t("settings.save"), command=self._save).pack(side="right", padx=(0, 8))
            self.root.protocol("WM_DELETE_WINDOW", self._close)
            self.root.after(150, self._poll)
            self.root.lift()
            self.root.focus_force()
            self.root.mainloop()
        finally:
            self.on_close()
