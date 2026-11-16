"""Mod ve laboratuvar komutlarının anlık kaydı: komut yalnızca bellekte (RAM) tutulur, işlem bitince metni de silinip kayıt tamamen kaldırılır.
Hiçbir şey diske yazılmaz. Not penceresi 'bekleyen komut' sayısını canlı gösterebilsin diye vardır."""
import itertools
import threading
import time

_lock = threading.Lock()
_items: dict = {}
_ids = itertools.count(1)


def add(kind: str, text: str) -> int:
    i = next(_ids)
    with _lock:
        _items[i] = {"kind": kind, "text": str(text)[:300], "t": time.time()}
    return i


def done(i: int) -> None:
    """İşlem bitti: metni üzerine yazıp kaydı siler."""
    with _lock:
        it = _items.pop(i, None)
        if it:
            it["text"] = ""
            it.clear()


def clear() -> None:
    with _lock:
        for it in _items.values():
            it.clear()
        _items.clear()


def snapshot() -> list:
    with _lock:
        return [{"id": i, "kind": v["kind"], "text": v["text"], "age": round(time.time() - v["t"], 1)} for i, v in _items.items()]
