"""Ezber kartları: desteler, kartlar ve aralıklı tekrar (SM-2'nin sadeleştirilmiş hâli). Veri yalnızca bu bilgisayarda kartlar.json'da durur.
Bilinen kart seyrek, bilinmeyen sık gelir: Bilmedim -> 1 dk sonra yine, Zor -> kısa aralık, İyi -> aralık * kolaylık, Kolay -> daha uzun aralık.
Yapay zekâ ile üretim yerel modelle (Ollama, brain ile aynı model ve num_ctx) yapılır; üretilen kartlar 'YZ' diye işaretlenir.
Zaman kaynağı now() testlerde değiştirilebilir."""
import json
import os
import re
import secrets
import threading
import time

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kartlar.json")
MAX_DECKS, MAX_CARDS, MAX_TXT, NEW_PER_DAY = 60, 5000, 300, 30
now = time.time
_lock = threading.RLock()
S = {"deck": None, "card": None, "flipped": False}       # oturum durumu (bellekte)
GEN = {"busy": False, "msg": ""}


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.localtime(now()))


def _txt(v, n=MAX_TXT) -> str:
    return " ".join("".join(ch for ch in str(v or "") if ch.isprintable() or ch == "\n").split())[:n]


def _load() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            raise ValueError
    except (OSError, ValueError):
        d = {}
    d.setdefault("decks", [])
    d.setdefault("cards", [])
    d.setdefault("log", {})
    return d


def _save(d: dict) -> None:
    for k in sorted(d["log"])[:-400]:
        d["log"].pop(k, None)
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PATH)


# ------------------------------------------------------------------ desteler
def find_deck(d: dict, name_or_id: str):
    q = str(name_or_id or "").strip().lower()
    if not q:
        return None
    return (next((x for x in d["decks"] if x["id"] == q), None) or next((x for x in d["decks"] if x["name"].lower() == q), None)
            or next((x for x in d["decks"] if q in x["name"].lower()), None))


def add_deck(name: str) -> dict:
    name = _txt(name, 40)
    if not name:
        return {}
    with _lock:
        d = _load()
        ex = find_deck(d, name)
        if ex and ex["name"].lower() == name.lower():
            return ex
        if len(d["decks"]) >= MAX_DECKS:
            return {}
        dk = {"id": "d" + secrets.token_hex(4), "name": name, "created": int(now())}
        d["decks"].append(dk)
        _save(d)
        S.update(deck=dk["id"], card=None, flipped=False)
        return dk


def delete_deck(deck_id: str) -> int:
    with _lock:
        d = _load()
        dk = find_deck(d, deck_id)
        if not dk:
            return -1
        n = sum(1 for c in d["cards"] if c["deck"] == dk["id"])
        d["cards"] = [c for c in d["cards"] if c["deck"] != dk["id"]]
        d["decks"] = [x for x in d["decks"] if x["id"] != dk["id"]]
        _save(d)
        if S["deck"] == dk["id"]:
            S.update(deck=None, card=None, flipped=False)
        return n


def select_deck(name_or_id) -> dict:
    with _lock:
        d = _load()
        dk = find_deck(d, name_or_id) if name_or_id else None
        S.update(deck=dk["id"] if dk else None, card=None, flipped=False)
        return dk or {}


# ------------------------------------------------------------------ kartlar
def add_card(deck_id: str, front: str, back: str, ai: bool = False) -> dict:
    front, back = _txt(front), _txt(back)
    if not front or not back:
        return {}
    with _lock:
        d = _load()
        dk = find_deck(d, deck_id)
        if not dk or len(d["cards"]) >= MAX_CARDS:
            return {}
        if any(c["deck"] == dk["id"] and c["front"].lower() == front.lower() for c in d["cards"]):
            return {"dup": True}
        c = {"id": "c" + secrets.token_hex(5), "deck": dk["id"], "front": front, "back": back, "ai": bool(ai),
             "ease": 2.5, "ivl": 0.0, "reps": 0, "lapses": 0, "due": 0, "seen": False, "created": int(now())}
        d["cards"].append(c)
        _save(d)
        return c


def delete_card(card_id: str) -> bool:
    with _lock:
        d = _load()
        n = len(d["cards"])
        d["cards"] = [c for c in d["cards"] if c["id"] != card_id]
        if len(d["cards"]) == n:
            return False
        _save(d)
        if S["card"] == card_id:
            S.update(card=None, flipped=False)
        return True


def edit_card(card_id: str, front: str, back: str) -> bool:
    front, back = _txt(front), _txt(back)
    if not front or not back:
        return False
    with _lock:
        d = _load()
        c = next((x for x in d["cards"] if x["id"] == card_id), None)
        if not c:
            return False
        c.update(front=front, back=back, ai=False)
        _save(d)
        return True


# ------------------------------------------------------------------ aralıklı tekrar
def _fmt(sec: float) -> str:
    if sec < 3600:
        return f"{max(1, round(sec / 60))} dk"
    if sec < 86400:
        return f"{round(sec / 3600)} sa"
    days = sec / 86400
    if days < 30:
        return f"{round(days)} gün"
    if days < 365:
        return f"{round(days / 30)} ay"
    return f"{days / 365:.1f} yıl".replace(".", ",")


def _schedule(c: dict, g: int):
    """(yeni_aralık_gün, sonraki_süre_saniye, yeni_kolaylık). g: 0 bilmedim, 1 zor, 2 iyi, 3 kolay."""
    ease, ivl = c["ease"], c["ivl"]
    if g == 0:
        return 0.0, 60, max(1.3, ease - 0.2)
    if c["reps"] == 0 or ivl < 1:                    # yeni ya da yeniden öğrenilen kart
        return {1: (0.0, 600, ease - 0.15), 2: (1.0, 86400, ease), 3: (4.0, 4 * 86400, ease + 0.15)}[g]
    if g == 1:
        n = max(1.0, ivl * 1.2)
        return n, n * 86400, max(1.3, ease - 0.15)
    if g == 2:
        n = max(ivl + 1, ivl * ease)
        return n, n * 86400, ease
    n = max(ivl + 2, ivl * ease * 1.3)
    return n, n * 86400, ease + 0.15


def previews(c: dict) -> dict:
    return {g: _fmt(_schedule(c, g)[1]) for g in range(4)} if c else {}


def _new_today(d: dict) -> int:
    return int((d["log"].get(_today()) or {}).get("new", 0))


def _queue(d: dict, deck_id):
    """Sıradaki kart: önce zamanı gelmiş tekrarlar (en eski önce), sonra günlük sınır içinde yeni kartlar (eklenme sırasıyla)."""
    t = now()
    pool = [c for c in d["cards"] if deck_id in (None, c["deck"])]
    due = sorted((c for c in pool if c["seen"] and c["due"] <= t), key=lambda c: c["due"])
    new = [c for c in pool if not c["seen"]] if _new_today(d) < NEW_PER_DAY else []
    return due, new


def current() -> dict:
    """Gösterilecek kart (yoksa {}). Oturumda seçili kart hâlâ uygunsa o kalır."""
    with _lock:
        d = _load()
        cur = next((c for c in d["cards"] if c["id"] == S["card"]), None)
        if cur and S["deck"] in (None, cur["deck"]) and (not cur["seen"] or cur["due"] <= now() + 1200):
            return cur
        due, new = _queue(d, S["deck"])
        # başka kart kalmadıysa 20 dk içinde dönecek öğrenme kartları (bilmedim / zor) öne alınır
        soon = sorted((c for c in d["cards"] if S["deck"] in (None, c["deck"]) and c["seen"] and 0 < c["due"] - now() <= 1200), key=lambda c: c["due"])
        nxt = (due or new or soon or [None])[0]
        S.update(card=nxt["id"] if nxt else None, flipped=False)
        return nxt or {}


def flip(on=None) -> bool:
    if not current():
        return False
    S["flipped"] = (not S["flipped"]) if on is None else bool(on)
    return True


def grade(g: int) -> dict:
    """Geçerli kartı değerlendirir; {'card', 'next'} ya da {}."""
    g = max(0, min(3, int(g)))
    with _lock:
        d = _load()
        c = next((x for x in d["cards"] if x["id"] == S["card"]), None)
        if not c:
            return {}
        ivl, sec, ease = _schedule(c, g)
        was_new = not c["seen"]
        c.update(ivl=round(ivl, 3), ease=round(max(1.3, min(3.2, ease)), 3), due=int(now() + sec), seen=True,
                 reps=0 if g == 0 else c["reps"] + 1, lapses=c["lapses"] + (1 if g == 0 and not was_new else 0))
        lg = d["log"].setdefault(_today(), {"rev": 0, "ok": 0, "new": 0})
        lg["rev"] += 1
        lg["ok"] += 1 if g >= 2 else 0
        lg["new"] += 1 if was_new else 0
        _save(d)
        S.update(card=None, flipped=False)
        return {"card": c, "next": _fmt(sec)}


# ------------------------------------------------------------------ görünüm
def deck_stats(d: dict, deck_id):
    t = now()
    pool = [c for c in d["cards"] if deck_id in (None, c["deck"])]
    return {"total": len(pool), "due": sum(1 for c in pool if c["seen"] and c["due"] <= t), "new": sum(1 for c in pool if not c["seen"]),
            "learned": sum(1 for c in pool if c["seen"] and c["ivl"] >= 21)}


def view() -> dict:
    c = current()
    with _lock:
        d = _load()
        decks = [{"id": x["id"], "name": x["name"], **deck_stats(d, x["id"])} for x in d["decks"]]
        dk = find_deck(d, S["deck"]) if S["deck"] else None
        lg = d["log"].get(_today()) or {}
        card = None
        if c:
            card = {"id": c["id"], "front": c["front"], "back": c["back"], "ai": c.get("ai", False), "new": not c["seen"], "reps": c["reps"],
                    "deck": next((x["name"] for x in d["decks"] if x["id"] == c["deck"]), "")}
        cards = [{"id": x["id"], "front": x["front"], "back": x["back"], "ai": x.get("ai", False),
                  "state": "yeni" if not x["seen"] else ("öğrenildi" if x["ivl"] >= 21 else "tekrarda"), "due": _fmt(max(0, x["due"] - now())) if x["seen"] and x["due"] > now() else "şimdi"}
                 for x in d["cards"] if S["deck"] and x["deck"] == S["deck"]][-300:]
        return {"decks": decks, "deck": dk["id"] if dk else None, "deckName": dk["name"] if dk else "Tüm desteler", "all": deck_stats(d, None),
                "here": deck_stats(d, S["deck"]), "card": card, "flipped": S["flipped"], "previews": previews(c) if c else {},
                "today": {"rev": lg.get("rev", 0), "ok": lg.get("ok", 0), "new": lg.get("new", 0), "newLimit": NEW_PER_DAY},
                "cards": cards, "gen": dict(GEN)}


def log_days() -> dict:
    with _lock:
        return dict(_load()["log"])


# ------------------------------------------------------------------ yapay zekâ ile kart üretimi
_PROMPT = """Bir 9. sınıf öğrencisi için ezber kartları hazırla.
Konu ya da kaynak:
---
{src}
---
Tam olarak {n} kart üret. Her kartın önü kısa bir soru, terim ya da kelime; arkası kısa ve DOĞRU cevap olsun (en fazla 25 kelime).
Kaynak bir metinse yalnızca metindeki bilgilere dayan, uydurma. Yabancı dil kelimesi istendiyse ön yüz kelime, arka yüz Türkçe anlamı olsun.
Yanıtın YALNIZCA şu JSON olsun, başka hiçbir şey yazma:
{{"kartlar": [{{"on": "...", "arka": "..."}}]}}"""


def _llm(prompt: str):
    """Yerel model (brain ile aynı model ve num_ctx; ders modu ile aynı GPU kilidi)."""
    import ollama
    try:
        from brain import MODEL, CTX
    except Exception:
        MODEL, CTX = "qwen3:8b", 4096
    try:
        import ders_ai
        lock = ders_ai._llm_lock
    except Exception:
        lock = threading.Lock()
    with lock:
        r = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}], think=False, keep_alive="10m",
                        options={"temperature": 0.3, "num_ctx": CTX, "num_predict": 1800})
    return (r.message.content or "").strip()


def parse_cards(text: str) -> list:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return []
    s = m.group(0)
    for cand in (s, re.sub(r",\s*([}\]])", r"\1", s)):
        try:
            data = json.loads(cand)
            break
        except ValueError:
            data = None
    out = []
    for k in (data or {}).get("kartlar", []) if isinstance(data, dict) else []:
        if isinstance(k, dict):
            f, b = _txt(k.get("on")), _txt(k.get("arka"))
            if f and b and f.lower() != b.lower():
                out.append((f, b))
    return out


def generate(deck_id: str, source: str, n: int = 10, llm=None) -> dict:
    """Kaynaktan n kart üretip desteye ekler. {'added', 'dup', 'msg'} döner. Uzun sürer: arka planda çağrılmalı."""
    n = max(3, min(25, int(n)))
    source = _txt(source, 3500)
    if not source:
        return {"added": 0, "dup": 0, "msg": "Kart üretmek için bir konu ya da metin gerekiyor efendim."}
    if GEN["busy"]:
        return {"added": 0, "dup": 0, "msg": "Zaten kart üretiyorum efendim, biraz bekleyin."}
    GEN.update(busy=True, msg=f"{n} kart üretiliyor…")
    try:
        try:
            pairs = parse_cards((llm or _llm)(_PROMPT.format(src=source, n=n)))
        except Exception as e:
            print("KARTLAR: model hatası:", type(e).__name__, flush=True)
            pairs = []
        added = dup = 0
        for f, b in pairs[:n]:
            r = add_card(deck_id, f, b, ai=True)
            if r.get("dup"):
                dup += 1
            elif r:
                added += 1
        msg = (f"{added} kart ekledim efendim" + (f", {dup} tanesi zaten vardı" if dup else "") + ". Yapay zekâ kartları YZ diye işaretli, yanlış olanı silebilirsiniz."
               if added else "Üretilen kartların hepsi bu destede zaten vardı efendim." if dup else "Kart üretemedim efendim, konuyu biraz daha açık yazmayı deneyin.")
        return {"added": added, "dup": dup, "msg": msg}
    finally:
        GEN.update(busy=False, msg="")
