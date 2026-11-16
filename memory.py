"""Kalıcı hafıza (memory.json, yalnızca bu bilgisayarda). Jarvis'e 'bunu hatırla' denen bilgiler."""
import json, os, threading, datetime

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")
MAX = 60
_lock = threading.Lock()


def _load() -> list:
    try:
        with open(PATH, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save(items):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(items[-MAX:], f, ensure_ascii=False, indent=2)


def remember(fact: str) -> str:
    fact = " ".join(fact.split())[:300]
    if not fact:
        return "Hatırlanacak bir şey yok."
    with _lock:
        items = _load()
        if any(i["fact"].lower() == fact.lower() for i in items):
            return "Bunu zaten biliyorum."
        items.append({"fact": fact, "date": datetime.date.today().isoformat()})
        _save(items)
    return f"Hatırlayacağım: {fact}"


def forget(keyword: str) -> str:
    k = keyword.lower().strip()
    with _lock:
        items = _load()
        keep = [i for i in items if k not in i["fact"].lower()]
        _save(keep)
    n = len(items) - len(keep)
    return f"{n} bilgiyi unuttum." if n else "Bununla ilgili bir şey hatırlamıyorum."


def remove_at(index: int) -> bool:
    """Sıra numarasıyla tek bir hatırayı siler."""
    with _lock:
        items = _load()
        if not 0 <= index < len(items):
            return False
        del items[index]
        _save(items)
    return True


def facts() -> list:
    return [i["fact"] for i in _load()]


def as_prompt() -> str:
    f = facts()
    if not f:
        return ""
    return ("\n\nKULLANICI HAKKINDA HATIRLADIKLARIN (kullanıcının sana söyledikleri, doğru kabul et):\n"
            + "\n".join(f"- {x}" for x in f))
