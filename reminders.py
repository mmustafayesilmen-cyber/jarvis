"""Hatırlatıcılar ve zamanlayıcılar (reminders.json). Jarvis kapanıp açılsa da kaybolmaz."""
import json, os, threading, time, datetime

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reminders.json")
_lock = threading.Lock()


def _load() -> list:
    try:
        with open(PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save(items):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _when(seconds: float) -> str:
    t = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
    return t.strftime("%H:%M")


def add(seconds: float, message: str, kind: str = "reminder") -> str:
    seconds = max(1, float(seconds))
    with _lock:
        items = _load()
        items.append({"due": time.time() + seconds, "message": message.strip()[:200], "kind": kind})
        _save(items)
    return _when(seconds)


def add_at(seconds: float, message: str, kind: str = "reminder") -> float:
    """Hatırlatma ekler ve vade zamanını (epoch saniye) döndürür."""
    seconds = max(1, float(seconds))
    due = time.time() + seconds
    with _lock:
        items = _load()
        items.append({"due": due, "message": message.strip()[:200], "kind": kind})
        _save(items)
    return due


def cancel_due(due: float) -> int:
    """Belirli vadeli hatırlatmayı iptal et (sayaç erken kapatılınca)."""
    with _lock:
        items = _load()
        keep = [i for i in items if abs(i["due"] - float(due)) > 0.5]
        _save(keep)
    return len(items) - len(keep)


def pending() -> list:
    return sorted(_load(), key=lambda i: i["due"])


def cancel_all() -> int:
    with _lock:
        n = len(_load())
        _save([])
    return n


def pop_due() -> list:
    now = time.time()
    with _lock:
        items = _load()
        due = [i for i in items if i["due"] <= now]
        if due:
            _save([i for i in items if i["due"] > now])
    return due


def lik(phrase: str) -> str:
    """'5 dakika' -> '5 dakikalık', 'yarım saat' -> 'yarım saatlik' (ünlü uyumu; 'saat' istisnadır)."""
    p = phrase.strip()
    if p.endswith("saat"):
        return p + "lik"
    vowels = [c for c in p.lower() if c in "aıoueiöü"]
    last = vowels[-1] if vowels else "e"
    return p + {"a": "lık", "ı": "lık", "o": "luk", "u": "luk", "e": "lik", "i": "lik", "ö": "lük", "ü": "lük"}[last]
