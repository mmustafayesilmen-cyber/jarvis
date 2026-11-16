"""Zihin oyunları modu: skorlar ve rekorlar (oyunlar.json, yalnızca bu bilgisayarda). Oyunların kendisi ui/scene_oyunlar.html'de çalışır.
Oyunlar: dizi (sayı dizisi hatırlama), eslestir (kart eşleştirme), hesap (60 sn hızlı hesap), simon (renk dizisi)."""
import json
import os
import threading
import time

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oyunlar.json")
GAMES = {"dizi": "Sayı dizisi", "eslestir": "Eşleştirme", "hesap": "Hızlı hesap", "simon": "Renk dizisi", "element": "Element avı"}
UNIT = {"dizi": "rakam", "eslestir": "puan", "hesap": "doğru", "simon": "adım", "element": "doğru"}
_lock = threading.Lock()


def _load() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            raise ValueError
    except (OSError, ValueError):
        d = {}
    d.setdefault("best", {})
    d.setdefault("log", {})
    d.setdefault("recent", {})
    return d


def _save(d: dict) -> None:
    for k in sorted(d["log"])[:-400]:
        d["log"].pop(k, None)
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PATH)


def add_score(game: str, score) -> dict:
    """Biten oyunun skoru. {'record': bool, 'best': int, 'prev': int} — geçersizse {}."""
    if game not in GAMES:
        return {}
    try:
        score = max(0, min(100000, int(score)))
    except (TypeError, ValueError):
        return {}
    with _lock:
        d = _load()
        prev = int(d["best"].get(game, 0))
        rec = score > prev
        if rec:
            d["best"][game] = score
        day = time.strftime("%Y-%m-%d")
        lg = d["log"].setdefault(day, {"plays": 0})
        lg["plays"] += 1
        lg[game] = lg.get(game, 0) + 1
        r = d["recent"].setdefault(game, [])
        r.append(score)
        d["recent"][game] = r[-20:]
        _save(d)
    return {"record": rec and prev > 0, "first": prev == 0, "best": max(prev, score), "prev": prev}


def view() -> dict:
    d = _load()
    day = time.strftime("%Y-%m-%d")
    return {"games": [{"id": g, "name": n, "unit": UNIT[g], "best": int(d["best"].get(g, 0)), "recent": d["recent"].get(g, [])[-10:]} for g, n in GAMES.items()],
            "today": (d["log"].get(day) or {}).get("plays", 0)}


def log_days() -> dict:
    return dict(_load()["log"])
