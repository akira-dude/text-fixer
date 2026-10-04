"""Settings window (tkinter). Runs in its own thread; talks to the app via callbacks."""

import queue
import re
import threading
import tkinter as tk
from dataclasses import replace
from tkinter import messagebox, ttk
from typing import Callable

from . import winapi as w
from .config import Config, Style

PROXY_SYSTEM = "Системный (как в браузере)"
PROXY_DIRECT = "Без прокси"

# Tk keysym -> our hotkey key name
_KEYSYMS = {"space": "space", "Return": "enter", "Pause": "pause", "Tab": "tab", "Insert": "insert",
            "Delete": "delete", "Home": "home", "End": "end", "Prior": "pageup", "Next": "pagedown",
            "Scroll_Lock": "scrolllock"}
_MODIFIER_KEYSYMS = {"Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R", "Win_L", "Win_R",
                     "Meta_L", "Meta_R", "Caps_Lock"}


class SettingsWindow:
    def __init__(self, cfg: Config, on_save: Callable[[Config], str | None],
                 on_test: Callable[[Config], str], on_close: Callable[[], None]):
        self.cfg = replace(cfg, styles={k: replace(s) for k, s in cfg.styles.items()})
        self.on_save = on_save
        self.on_test = on_test
        self.on_close = on_close
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
        t = tk.Text(parent, height=height, width=50, wrap="word", font=("Segoe UI", 10), undo=True)
        t.insert("1.0", value)
        return t

    # --------------------------------------------------------------- tabs

    def _build_api(self) -> None:
        f = self._tab("Подключение")
        c = self.cfg
        self.v_key = tk.StringVar(value=c.api_key)
        key_box = ttk.Frame(f)
        key_box.columnconfigure(0, weight=1)
        self.e_key = ttk.Entry(key_box, textvariable=self.v_key, show="•")
        self.e_key.grid(row=0, column=0, sticky="ew")
        self.v_show = tk.BooleanVar()
        ttk.Checkbutton(key_box, text="показать", variable=self.v_show,
                        command=lambda: self.e_key.config(show="" if self.v_show.get() else "•")).grid(
            row=0, column=1, padx=(8, 0))
        self._row(f, 0, "API-ключ", key_box)

        self.v_url = tk.StringVar(value=c.base_url)
        self._row(f, 2, "Адрес API", ttk.Entry(f, textvariable=self.v_url),
                  "Любой OpenAI-совместимый API. Groq: https://api.groq.com/openai/v1")

        self.t_models = self._text(f, 4, "\n".join(c.models))
        self._row(f, 4, "Модели", self.t_models,
                  "По одной в строке, по порядку. Если модель недоступна (выключена, лимит, упала), "
                  "берётся следующая; упавшая пропускается 10 минут.")

        proxy_value = PROXY_SYSTEM if not c.proxy else PROXY_DIRECT if c.proxy == "direct" else c.proxy
        self.v_proxy = tk.StringVar(value=proxy_value)
        self._row(f, 6, "Прокси", ttk.Combobox(f, textvariable=self.v_proxy,
                                                values=[PROXY_SYSTEM, PROXY_DIRECT, "http://127.0.0.1:10809"]),
                  "Можно вписать свой адрес. Явный адрес VPN-клиента надёжнее системного.")

        self.v_effort = tk.StringVar(value=c.reasoning_effort or "—")
        self._row(f, 8, "Рассуждения gpt-oss", ttk.Combobox(f, textvariable=self.v_effort, state="readonly",
                                                            values=["low", "medium", "high", "—"], width=10),
                  "low — быстрее всего. Для других моделей не используется.")

        nums = ttk.Frame(f)
        self.v_timeout = tk.StringVar(value=f"{c.timeout_s:g}")
        self.v_maxchars = tk.StringVar(value=str(c.max_chars))
        ttk.Label(nums, text="таймаут, с").pack(side="left")
        ttk.Spinbox(nums, from_=2, to=60, textvariable=self.v_timeout, width=6).pack(side="left", padx=(6, 18))
        ttk.Label(nums, text="макс. символов").pack(side="left")
        ttk.Spinbox(nums, from_=100, to=20000, increment=500, textvariable=self.v_maxchars,
                    width=8).pack(side="left", padx=6)
        self._row(f, 10, "Ограничения", nums)

        test = ttk.Frame(f)
        test.grid(row=11, column=1, sticky="ew", pady=(14, 0))
        self.b_test = ttk.Button(test, text="Проверить подключение", command=self._test)
        self.b_test.pack(side="left")
        self.v_test = tk.StringVar()
        ttk.Label(test, textvariable=self.v_test, wraplength=300, justify="left").pack(side="left", padx=10)

    def _build_hotkeys(self) -> None:
        f = self._tab("Горячие клавиши")
        c = self.cfg
        self.v_hk = {}
        rows = [("fix", "Исправить", c.hotkey_fix, "раскладка + ИИ, стилем из трея"),
                ("fix_and_send", "Исправить и отправить", c.hotkey_fix_and_send, "то же и сразу Enter"),
                ("layout", "Только раскладка", c.hotkey_layout, "без ИИ, мгновенно")]
        for i, (key, label, value, hint) in enumerate(rows):
            v = tk.StringVar(value=value)
            self.v_hk[key] = v
            box = ttk.Frame(f)
            box.columnconfigure(0, weight=1)
            e = ttk.Entry(box, textvariable=v)
            e.grid(row=0, column=0, sticky="ew")
            ttk.Button(box, text="Записать", command=lambda v=v, e=e: self._record(v, e)).grid(
                row=0, column=1, padx=(8, 0))
            self._row(f, i * 2, label, box, hint)
        ttk.Label(f, foreground="#666", wraplength=520, justify="left", text=(
            "«Записать» — нажми нужное сочетание (Esc — отмена, Backspace — без клавиши). "
            "Можно вписать вручную: модификаторы ctrl, shift, alt, win; клавиши a-z, 0-9, f1-f24, "
            "space, enter, pause, insert, home, end…")).grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _build_enter(self) -> None:
        f = self._tab("Enter")
        self.v_auto = tk.BooleanVar(value=self.cfg.auto_enter)
        ttk.Checkbutton(f, text="Исправлять раскладку по Enter перед отправкой", variable=self.v_auto).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        self.t_apps = self._text(f, 6, "\n".join(self.cfg.auto_enter_apps))
        self._row(f, 1, "Приложения", self.t_apps,
                  "Имена exe по одному в строке (как в диспетчере задач → Подробности). "
                  "Shift+Enter (перенос строки) не трогается.")

    def _build_styles(self) -> None:
        f = self._tab("Стили")
        f.columnconfigure(1, weight=1)
        f.rowconfigure(0, weight=1)
        left = ttk.Frame(f)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        self.lb_styles = tk.Listbox(left, height=10, width=18, exportselection=False, font=("Segoe UI", 10))
        self.lb_styles.pack(fill="y", expand=True)
        self.lb_styles.bind("<<ListboxSelect>>", lambda e: self._select_style())
        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="Добавить", command=self._add_style).pack(side="left", expand=True, fill="x")
        ttk.Button(btns, text="Удалить", command=self._del_style).pack(side="left", expand=True, fill="x", padx=(4, 0))

        right = ttk.Frame(f)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(1, weight=1)
        right.rowconfigure(4, weight=1)
        self.v_sname = tk.StringVar()
        self._row(right, 0, "Название", ttk.Entry(right, textvariable=self.v_sname))
        self.v_rewrite = tk.BooleanVar()
        self.v_strip = tk.BooleanVar()
        ttk.Checkbutton(right, text="Переписывать текст (разрешить менять длину)", variable=self.v_rewrite).grid(
            row=1, column=1, sticky="w")
        ttk.Checkbutton(right, text="Убирать точку в конце сообщения", variable=self.v_strip).grid(
            row=2, column=1, sticky="w", pady=(0, 6))
        ttk.Label(right, text="Инструкция").grid(row=3, column=0, sticky="nw", padx=(0, 10))
        self.t_prompt = self._text(right, 10, "")
        self.t_prompt.grid(row=3, column=1, rowspan=2, sticky="nsew")
        ttk.Label(right, foreground="#666", wraplength=420, justify="left", text=(
            "Общие правила добавляются всегда: не переводить, не отвечать на сообщение, "
            "сохранять ссылки, @упоминания, эмодзи и переносы строк.")).grid(row=5, column=1, sticky="w", pady=(6, 0))

        self._style_keys: list[str] = []
        self._cur_style: str | None = None
        self._refresh_styles(self.cfg.active_style)

    def _build_timing(self) -> None:
        f = self._tab("Тайминги")
        c = self.cfg
        self.v_timing = {}
        rows = [("select_delay_ms", "Пауза после Ctrl+A", c.select_delay_ms,
                 "Discord применяет выделение не сразу. Если первое нажатие не срабатывает — увеличь."),
                ("copy_timeout_ms", "Ожидание копирования", c.copy_timeout_ms, "для горячих клавиш"),
                ("enter_copy_timeout_ms", "Ожидание копирования при Enter", c.enter_copy_timeout_ms,
                 "на пустом поле Enter задерживается на это время"),
                ("paste_settle_ms", "Пауза перед Enter после вставки", c.paste_settle_ms, ""),
                ("clipboard_restore_ms", "Возврат буфера обмена через", c.clipboard_restore_ms, "")]
        for i, (key, label, value, hint) in enumerate(rows):
            v = tk.StringVar(value=str(value))
            self.v_timing[key] = v
            box = ttk.Frame(f)
            ttk.Spinbox(box, from_=0, to=5000, increment=10, textvariable=v, width=8).pack(side="left")
            ttk.Label(box, text="мс").pack(side="left", padx=6)
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
            s.name = self.v_sname.get().strip() or s.key
            s.rewrite = self.v_rewrite.get()
            s.strip_final_period = self.v_strip.get()
            s.prompt = self.t_prompt.get("1.0", "end").strip()

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

    def _add_style(self) -> None:
        self._store_style()
        n = 1
        while f"style{n}" in self.cfg.styles:
            n += 1
        key = f"style{n}"
        self.cfg.styles[key] = Style(key, f"Новый стиль {n}", "Исправь орфографию и пунктуацию.")
        self._cur_style = None
        self._refresh_styles(key)

    def _del_style(self) -> None:
        if len(self.cfg.styles) <= 1 or not self._cur_style:
            messagebox.showinfo("TextFixer", "Должен остаться хотя бы один стиль.", parent=self.root)
            return
        del self.cfg.styles[self._cur_style]
        if self.cfg.active_style not in self.cfg.styles:
            self.cfg.active_style = next(iter(self.cfg.styles))
        self._cur_style = None
        self._refresh_styles(next(iter(self.cfg.styles)))

    # ------------------------------------------------------------ hotkeys

    def _record(self, var: tk.StringVar, entry: ttk.Entry) -> None:
        old = var.get()
        var.set("нажми сочетание…")
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
        lines = lambda t: [x.strip() for x in t.get("1.0", "end").splitlines() if x.strip()]
        proxy = self.v_proxy.get().strip()
        proxy = "" if proxy in ("", PROXY_SYSTEM) else "direct" if proxy == PROXY_DIRECT else proxy
        models = lines(self.t_models)
        if not models:
            raise ValueError("Укажи хотя бы одну модель")
        for name, v in self.v_hk.items():
            if v.get().strip():
                try:
                    w.Hotkey(v.get())
                except ValueError as e:
                    raise ValueError(str(e))
        specs = [v.get().strip().lower() for v in self.v_hk.values() if v.get().strip()]
        if len(specs) != len(set(specs)):
            raise ValueError("Одно сочетание назначено дважды")

        def num(v, name, cast=int):
            try:
                return cast(v.get())
            except ValueError:
                raise ValueError(f"«{name}» — должно быть число")

        return replace(
            self.cfg,
            api_key=self.v_key.get().strip(),
            base_url=self.v_url.get().strip().rstrip("/"),
            models=models,
            proxy=proxy,
            reasoning_effort="" if self.v_effort.get() == "—" else self.v_effort.get(),
            timeout_s=num(self.v_timeout, "таймаут", float),
            max_chars=num(self.v_maxchars, "макс. символов"),
            hotkey_fix=self.v_hk["fix"].get().strip(),
            hotkey_fix_and_send=self.v_hk["fix_and_send"].get().strip(),
            hotkey_layout=self.v_hk["layout"].get().strip(),
            auto_enter=self.v_auto.get(),
            auto_enter_apps=[a.lower() for a in lines(self.t_apps)],
            **{k: num(v, k) for k, v in self.v_timing.items()},
        )

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
        self.v_test.set("Проверяю…")
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
            self.root.title("TextFixer — настройки")
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
            bar = ttk.Frame(outer)
            bar.pack(fill="x", pady=(10, 0))
            ttk.Button(bar, text="Отмена", command=self._close).pack(side="right")
            ttk.Button(bar, text="Сохранить", command=self._save).pack(side="right", padx=(0, 8))
            self.root.protocol("WM_DELETE_WINDOW", self._close)
            self.root.after(150, self._poll)
            self.root.lift()
            self.root.focus_force()
            self.root.mainloop()
        finally:
            self.on_close()
