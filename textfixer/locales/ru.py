"""Русские строки интерфейса (ключи — как в en.py)."""

STRINGS = {
    # --- tray menu
    "menu.hotkeys": "Исправить: {fix} · с отправкой: {send} · раскладка: {layout}",
    "menu.model": "Модель: {model}",
    "menu.style": "Стиль: {style}",
    "menu.auto_enter": "Исправлять раскладку по Enter",
    "menu.autostart": "Запускать вместе с Windows",
    "menu.settings": "Настройки…",
    "menu.data_folder": "Открыть папку с данными",
    "menu.update_to": "Обновить до {version}",
    "menu.updating": "Обновление…",
    "menu.check_updates": "Проверить обновления (версия {version})",
    "menu.quit": "Выход",
    "tray.title": "TextFixer — {style}",

    # --- notifications
    "notify.error": "Ошибка: {error}",
    "notify.too_long": "Текст длиннее {max} символов — исправлена только раскладка",
    "notify.model_switched": "Модель: {model}",
    "notify.window_changed": "Окно сменилось — исправленный текст лежит в буфере обмена",
    "notify.update_available": "Доступна версия {version} — меню трея → «Обновить»",
    "notify.up_to_date": "Установлена последняя версия {version}",
    "notify.update_check_failed": "Проверка обновлений: {error}",
    "notify.update_only_installed": "Обновление работает только в установленной версии (install.cmd)",
    "notify.downloading": "Скачиваю версию {version}…",
    "notify.update_failed": "Обновление не удалось: {error}",
    "notify.updated": "Обновлено до версии {version}",
    "notify.update_rolled_back": "Обновление не установилось — работает прежняя версия. Подробности в update\\apply.log",
    "notify.ask_api_key": "Впиши API-ключ в настройках",

    # --- connection test
    "test.sample": "привет как дела",
    "test.ok": "✓ {model}, {ms} мс: «{text}»",
    "test.fail": "✗ {error}",

    # --- LLM errors
    "llm.proxy_down": "Прокси недоступен — VPN выключен?",
    "llm.timeout": "таймаут {seconds} с",
    "llm.network": "Сеть: {error} — проверь интернет/VPN",
    "llm.bad_key": "Неверный API-ключ",
    "llm.region_block": "Провайдер блокирует запрос по сети ({message}) — проверь VPN",
    "llm.no_key": "Не задан API-ключ — открой настройки",
    "llm.all_failed": "Все модели недоступны. {errors}",
    "llm.weird_answer": "Модель вернула что-то странное, текст не тронут",

    # --- updater errors
    "upd.github_down": "GitHub недоступен: {error}",
    "upd.no_archive": "В релизе {version} нет архива",
    "upd.no_checksum": "Нет контрольной суммы — обновление не установлено",
    "upd.download_failed": "Не удалось скачать: {error}",
    "upd.bad_checksum": "Контрольная сумма не совпала — архив повреждён",
    "upd.bad_path": "Подозрительный путь в архиве",
    "upd.no_exe": "В архиве нет TextFixer.exe",

    # --- hotkey parsing
    "hotkey.unknown_key": "Неизвестная клавиша '{key}' в '{spec}'",
    "hotkey.no_main_key": "В '{spec}' нет основной клавиши",

    # --- settings window
    "settings.title": "TextFixer — настройки",
    "settings.save": "Сохранить",
    "settings.cancel": "Отмена",
    "settings.tab.api": "Подключение",
    "settings.tab.hotkeys": "Горячие клавиши",
    "settings.tab.enter": "Enter",
    "settings.tab.styles": "Стили",
    "settings.tab.timing": "Тайминги",

    "settings.language": "Язык",
    "settings.api_key": "API-ключ",
    "settings.show": "показать",
    "settings.base_url": "Адрес API",
    "settings.base_url.hint": "Любой OpenAI-совместимый API. Groq: https://api.groq.com/openai/v1",
    "settings.models": "Модели",
    "settings.models.hint": "По одной в строке, по порядку. Если модель недоступна (выключена, лимит, упала), "
                            "берётся следующая; упавшая пропускается 10 минут.",
    "settings.proxy": "Прокси",
    "settings.proxy.system": "Системный (как в браузере)",
    "settings.proxy.direct": "Без прокси",
    "settings.proxy.hint": "Можно вписать свой адрес. Явный адрес VPN-клиента надёжнее системного.",
    "settings.effort": "Рассуждения gpt-oss",
    "settings.effort.hint": "low — быстрее всего. Для других моделей не используется.",
    "settings.limits": "Ограничения",
    "settings.timeout": "таймаут, с",
    "settings.max_chars": "макс. символов",
    "settings.check_updates": "Проверять обновления автоматически (GitHub)",
    "settings.test": "Проверить подключение",
    "settings.testing": "Проверяю…",

    "settings.hk.fix": "Исправить",
    "settings.hk.fix.hint": "раскладка + ИИ, стилем из трея",
    "settings.hk.fix_and_send": "Исправить и отправить",
    "settings.hk.fix_and_send.hint": "то же и сразу Enter",
    "settings.hk.layout": "Только раскладка",
    "settings.hk.layout.hint": "без ИИ, мгновенно",
    "settings.hk.record": "Записать",
    "settings.hk.press": "нажми сочетание…",
    "settings.hk.help": "«Записать» — нажми нужное сочетание (Esc — отмена, Backspace — без клавиши). "
                        "Можно вписать вручную: модификаторы ctrl, shift, alt, win; клавиши a-z, 0-9, f1-f24, "
                        "space, enter, pause, insert, home, end…",

    "settings.enter.enabled": "Исправлять раскладку по Enter перед отправкой",
    "settings.enter.apps": "Приложения",
    "settings.enter.apps.hint": "Имена exe по одному в строке (как в диспетчере задач → Подробности). "
                                "Shift+Enter (перенос строки) не трогается.",

    "settings.style.add": "Добавить",
    "settings.style.delete": "Удалить",
    "settings.style.name": "Название",
    "settings.style.rewrite": "Переписывать текст (разрешить менять длину)",
    "settings.style.strip": "Убирать точку в конце сообщения",
    "settings.style.prompt": "Инструкция",
    "settings.style.hint": "Общие правила добавляются всегда: не переводить, не отвечать на сообщение, "
                           "сохранять ссылки, @упоминания, эмодзи и переносы строк.",
    "settings.style.new_name": "Новый стиль {n}",
    "settings.style.new_prompt": "Исправь орфографию и пунктуацию.",
    "settings.style.keep_one": "Должен остаться хотя бы один стиль.",

    "settings.timing.select_delay": "Пауза после Ctrl+A",
    "settings.timing.select_delay.hint": "Discord применяет выделение не сразу. Если первое нажатие не срабатывает — увеличь.",
    "settings.timing.copy_timeout": "Ожидание копирования",
    "settings.timing.copy_timeout.hint": "для горячих клавиш",
    "settings.timing.enter_copy_timeout": "Ожидание копирования при Enter",
    "settings.timing.enter_copy_timeout.hint": "на пустом поле Enter задерживается на это время",
    "settings.timing.paste_settle": "Пауза перед Enter после вставки",
    "settings.timing.clipboard_restore": "Возврат буфера обмена через",
    "settings.ms": "мс",

    "settings.err.no_models": "Укажи хотя бы одну модель",
    "settings.err.duplicate_hotkey": "Одно сочетание назначено дважды",
    "settings.err.not_number": "«{field}» — должно быть число",
}
