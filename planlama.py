"""Planlama modu verisi: görev ve ödül düğümleri, aralarındaki bağlar. Planlama.json'da (yalnızca yerel, gitignored) durur.
Bir ödüle bağlı (başka ödüle uğramadan görevler üzerinden ulaşılan) tüm görevler bitince ödül kazanılır."""
import json
import os
import random
import threading
import time

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "planlama.json")
_lock = threading.RLock()
MAX_NODES = 80


def _load() -> dict:
    try:
        with open(FILE, encoding="utf-8") as f:
            d = json.load(f)
        nodes = [n for n in d.get("nodes", []) if isinstance(n, dict) and n.get("id") and n.get("t") in ("g", "o") and n.get("text")]
        ids = {n["id"] for n in nodes}
        links = [list(l) for l in d.get("links", []) if isinstance(l, list) and len(l) == 2 and l[0] in ids and l[1] in ids and l[0] != l[1]]
        return {"nodes": nodes, "links": links}
    except (OSError, ValueError, AttributeError):
        return {"nodes": [], "links": []}


def _save(d: dict) -> None:
    with open(FILE + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(FILE + ".tmp", FILE)


def _adj(d: dict) -> dict:
    a = {n["id"]: set() for n in d["nodes"]}
    for x, y in d["links"]:
        a[x].add(y)
        a[y].add(x)
    return a


def _tasks_of(d: dict, rid: str) -> list:
    """Ödülden başlayıp yalnızca görev düğümleri üzerinden ulaşılan görev kimlikleri."""
    adj, by = _adj(d), {n["id"]: n for n in d["nodes"]}
    seen, stack = set(), [rid]
    while stack:
        for nb in adj[stack.pop()]:
            if nb not in seen and by[nb]["t"] == "g":
                seen.add(nb)
                stack.append(nb)
    return list(seen)


def _refresh(d: dict) -> list:
    """Ödül durumlarını yeniden hesaplar; yeni kazanılan ödüllerin düğümlerini döner."""
    by = {n["id"]: n for n in d["nodes"]}
    won = []
    for n in d["nodes"]:
        if n["t"] != "o":
            continue
        ts = _tasks_of(d, n["id"])
        ok = bool(ts) and all(by[i].get("done") for i in ts)
        if ok and not n.get("got"):
            won.append(n)
        n["got"] = ok
    return won


def snapshot() -> dict:
    with _lock:
        d = _load()
        by = {n["id"]: n for n in d["nodes"]}
        nodes = []
        for n in d["nodes"]:
            e = dict(n)
            if n["t"] == "o":
                ts = _tasks_of(d, n["id"])
                e["prog"] = [sum(1 for i in ts if by[i].get("done")), len(ts)]
            nodes.append(e)
        g = [n for n in d["nodes"] if n["t"] == "g"]
        o = [n for n in d["nodes"] if n["t"] == "o"]
        return {"nodes": nodes, "links": d["links"],
                "stat": {"g": len(g), "gd": sum(1 for n in g if n.get("done")), "o": len(o), "od": sum(1 for n in o if n.get("got"))}}


def _free_spot(nodes: list):
    best, bd = (0.5, 0.5), -1
    for _ in range(40):
        p = (random.uniform(.08, .92), random.uniform(.1, .9))
        dist = min([((p[0] - n["x"]) * 1.6) ** 2 + (p[1] - n["y"]) ** 2 for n in nodes] or [9])
        if dist > bd:
            best, bd = p, dist
    return best


def add(t: str, text: str, to: list = ()) -> dict:
    text = " ".join(text.split())[:60]
    with _lock:
        d = _load()
        if len(d["nodes"]) >= MAX_NODES:
            return {}
        x, y = _free_spot(d["nodes"])
        n = {"id": f"{t}{int(time.time() * 1000) % 10**9:x}{random.randrange(16**2):02x}", "t": t, "text": text, "done": False, "got": False, "x": round(x, 3), "y": round(y, 3)}
        d["nodes"].append(n)
        for i in to:
            if i in {m["id"] for m in d["nodes"]} and i != n["id"]:
                d["links"].append([n["id"], i])
        _refresh(d)
        _save(d)
    return n


def find(q: str, t: str = ""):
    """Düğümü adına göre bulur (tam eşleşme, sonra içerme); bulunamazsa None."""
    q = " ".join(q.lower().split())
    if not q:
        return None
    with _lock:
        ns = [n for n in _load()["nodes"] if not t or n["t"] == t]
    for test in (lambda s: s == q, lambda s: q in s, lambda s: s in q):
        hit = [n for n in ns if test(" ".join(n["text"].lower().split()))]
        if hit:
            return hit[0]
    for k in (1, 2, 3):                                   # "ödevi" / "filmi" gibi hâl ekleri
        if len(q) - k >= 3:
            hit = [n for n in ns if q[:len(q) - k] in " ".join(n["text"].lower().split())]
            if hit:
                return hit[0]
    return None


def _mutate(fn):
    with _lock:
        d = _load()
        res = fn(d)
        won = _refresh(d)
        _save(d)
    return res, won


def move(i: str, x: float, y: float):
    def f(d):
        for n in d["nodes"]:
            if n["id"] == i:
                n["x"], n["y"] = round(max(.02, min(.98, x)), 3), round(max(.04, min(.96, y)), 3)
    return _mutate(f)


def toggle(i: str, value=None):
    def f(d):
        for n in d["nodes"]:
            if n["id"] == i and n["t"] == "g":
                n["done"] = (not n.get("done")) if value is None else bool(value)
                return n
    return _mutate(f)


def link(a: str, b: str):
    def f(d):
        ids = {n["id"] for n in d["nodes"]}
        if a == b or a not in ids or b not in ids:
            return False
        if [a, b] in d["links"] or [b, a] in d["links"]:
            return False
        d["links"].append([a, b])
        return True
    return _mutate(f)


def unlink(a: str, b: str):
    def f(d):
        n = len(d["links"])
        d["links"] = [l for l in d["links"] if set(l) != {a, b}]
        return n - len(d["links"])
    return _mutate(f)


def remove(i: str):
    def f(d):
        n = len(d["nodes"])
        d["nodes"] = [x for x in d["nodes"] if x["id"] != i]
        d["links"] = [l for l in d["links"] if i not in l]
        return n - len(d["nodes"])
    return _mutate(f)


def clear_done():
    def f(d):
        gone = {n["id"] for n in d["nodes"] if (n["t"] == "g" and n.get("done"))}
        d["nodes"] = [n for n in d["nodes"] if n["id"] not in gone]
        d["links"] = [l for l in d["links"] if not (set(l) & gone)]
        return len(gone)
    return _mutate(f)


def rename(i: str, text: str):
    text = " ".join(text.split())[:60]

    def f(d):
        for n in d["nodes"]:
            if n["id"] == i and text:
                n["text"] = text
    return _mutate(f)
