"""Russian UI strings for the de-itzmx patch installer GUI."""

from __future__ import annotations

DEFAULT = "ru"

_STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "window_title": "Патч itzmx для Clip Studio Paint",
        "choose_csp_version": "Версия CSP",
        "csp_detected": "Установлена: {version}",
        "csp_version_unknown": "Версия {version} не поддерживается этим установщиком",
        "payload_missing": "Пакет для {version} пока недоступен",
        "status_checking": "Проверка…",
        "status_patched": "Патч установлен · версия {version}",
        "status_not_patched": "Патч не установлен",
        "detail_patched": "Запускайте Clip Studio Paint как обычно — без пароля и заставки itzmx.",
        "detail_not_patched": "После установки CSP откроется без пароля и заставки itzmx.",
        "status_partial": "Установка неполная — нет: {missing}",
        "status_broken_proxy": "Патч удалён не полностью. Нажмите «Удалить патч» ещё раз.",
        "status_no_csp": "Clip Studio Paint не найден",
        "detail_no_csp": "Ожидается папка CELSYS с CLIP STUDIO PAINT.",
        "install_path": "{path}",
        "btn_patch": "Установить",
        "btn_unpatch": "Удалить",
        "btn_close": "Закрыть",
        "working_patch": "Установка…",
        "working_unpatch": "Удаление…",
        "done_title": "Готово",
        "done_patch": "Патч установлен. Запустите Clip Studio Paint.",
        "done_unpatch": "Патч удалён. CSP снова покажет пароль и заставку itzmx.",
        "failed_title": "Ошибка",
        "err_csp_running": "Закройте Clip Studio Paint (включая трей) и попробуйте снова.",
        "err_admin_denied": "Нужны права администратора. Подтвердите запрос UAC.",
        "err_csp_not_found": "Clip Studio Paint не найден.",
        "err_payload_missing": "Пакет патча для версии {version} не найден в этом установщике.",
        "err_version_mismatch": (
            "Выбрана {selected}, а установлена {installed}. "
            "Выберите версию из списка, совпадающую с установленной."
        ),
        "err_deploy_incomplete": "Не все файлы удалось скопировать: {detail}",
        "err_generic": "Что-то пошло не так. Закройте CSP и попробуйте снова.",
        "warn_version_unsupported": "Версия CSP ({installed}) не поддерживается.",
    },
}


def t(key: str, **kwargs: str) -> str:
    text = _STRINGS[DEFAULT].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def localize_error(message: str, *, version: str | None = None) -> str:
    text = message.strip()
    low = text.lower()

    if text.startswith("payload_missing:"):
        ver = text.split(":", 1)[-1] or version or "?"
        return t("err_payload_missing", version=ver)
    if text.startswith("deploy_incomplete:"):
        detail = text.split(":", 1)[-1]
        return t("err_deploy_incomplete", detail=detail)
    if "csp is running" in low or "закройте clip studio" in low:
        return t("err_csp_running")
    if "administrator" in low or "uac" in low:
        return t("err_admin_denied")
    if "not found" in low:
        return t("err_csp_not_found")
    return t("err_generic")
