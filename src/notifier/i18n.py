import locale as _locale

from .locales import en as _en
from .locales import ja as _ja

_LOCALES = {"en": _en.STRINGS, "ja": _ja.STRINGS}
DEFAULT_LANG = "en"
SUPPORTED = ("en", "ja")

_state = {"lang": DEFAULT_LANG}


def _detect_system_lang() -> str:
    try:
        lang = (_locale.getlocale()[0] or "")
    except Exception:
        lang = ""
    lang_l = lang.lower()
    if lang_l.startswith("ja") or "japanese" in lang_l:
        return "ja"
    return "en"


def set_language(lang: str) -> None:
    if not lang or lang == "auto":
        lang = _detect_system_lang()
    if lang not in _LOCALES:
        lang = DEFAULT_LANG
    _state["lang"] = lang


def current_language() -> str:
    return _state["lang"]


def t(key: str, **kwargs) -> str:
    data = _LOCALES.get(_state["lang"], _LOCALES[DEFAULT_LANG])
    val = data.get(key)
    if val is None:
        val = _LOCALES[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return val.format(**kwargs)
        except Exception:
            return val
    return val
