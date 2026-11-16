"""Satranç modu oyun yönetimi: Jarvis'e karşı oyun, Türkçe sesli/yazılı hamle anlama, koç uyarıları, ipucu, geri alma, istatistik.
Oyun ve istatistik yalnızca bu bilgisayarda satranc.json'da durur. Motor chess_engine.py (dış paket yok)."""
import json
import os
import re
import threading

import chess_engine as C

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "satranc.json")
LEVEL_NAMES = {1: "Yeni başlayan", 2: "Kolay", 3: "Orta", 4: "Zor", 5: "Usta"}
_lock = threading.RLock()
G = {"board": C.Board(), "moves": [], "san": [], "color": "w", "level": 2, "coach": True, "result": None, "thinking": False,
     "comment": "", "hint": None, "last": None, "loaded": False}


# ------------------------------------------------------------------ kayıt
def _load() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save() -> None:
    d = _load()
    d.update(game={"moves": [C.name(a) + C.name(b) + (p or "") for a, b, p in G["moves"]], "color": G["color"], "level": G["level"],
                   "coach": G["coach"], "result": G["result"]})
    d.setdefault("stats", {})
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PATH)


def _record(outcome: str) -> None:
    """outcome: 'kazanç' | 'kayıp' | 'beraberlik' — seviyeye göre sayılır."""
    d = _load()
    st = d.setdefault("stats", {}).setdefault(str(G["level"]), {"kazanç": 0, "kayıp": 0, "beraberlik": 0})
    st[outcome] = st.get(outcome, 0) + 1
    import time
    day = time.strftime("%Y-%m-%d")
    lg = d.setdefault("log", {}).setdefault(day, {"games": 0})
    lg["games"] += 1
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def load() -> None:
    """Pencere açılınca yarım kalan oyun yüklenir."""
    with _lock:
        g = _load().get("game") or {}
        G.update(board=C.Board(), moves=[], san=[], color=g.get("color", "w") if g.get("color") in ("w", "b") else "w",
                 level=int(g.get("level", 2)) if str(g.get("level", 2)).isdigit() and 1 <= int(g.get("level", 2)) <= 5 else 2,
                 coach=bool(g.get("coach", True)), result=None, thinking=False, comment="", hint=None, last=None, loaded=True)
        for u in g.get("moves", [])[:600]:
            m = _from_uci(u)
            if not m:
                break
            _apply(m)
        G["result"] = g.get("result") if G["moves"] else None


def _from_uci(u: str):
    if not re.fullmatch(r"[a-h][1-8][a-h][1-8][QRBN]?", str(u)):
        return None
    m = (C.sq(u[:2]), C.sq(u[2:4]), u[4] if len(u) > 4 else None)
    return m if m in G["board"].legal() else None


def _apply(m) -> str:
    b = G["board"]
    s = b.san(m)
    G["san"].append(s)
    G["moves"].append(m)
    b.push(m)
    G["last"] = m
    return s


# ------------------------------------------------------------------ görünüm
def stats() -> dict:
    return _load().get("stats", {})


def view() -> dict:
    with _lock:
        b = G["board"]
        legal = b.legal() if not G["result"] else []
        lm = {}
        for a, t, p in legal:
            lm.setdefault(C.name(a), [])
            if C.name(t) not in lm[C.name(a)]:
                lm[C.name(a)].append(C.name(t))
        caps = {"w": [], "b": []}                        # alınan taşlar (başlangıca göre eksikler)
        full = {"P": 8, "N": 2, "B": 2, "R": 2, "Q": 1}
        for t, n in full.items():
            for side, ch in (("w", t), ("b", t.lower())):
                miss = max(0, n - b.sq.count(ch))
                caps[side] += [ch] * miss
        mat = sum(C.VAL[p.upper()] * (1 if p.isupper() else -1) for p in b.sq if p not in ".Kk")
        return {"fen": b.fen(), "sq": b.sq, "turn": "w" if b.white else "b", "color": G["color"], "level": G["level"], "levelName": LEVEL_NAMES[G["level"]],
                "legal": lm if (("w" if b.white else "b") == G["color"] and not G["thinking"]) else {},
                "last": [C.name(G["last"][0]), C.name(G["last"][1])] if G["last"] else None,
                "check": C.name(b.king(b.white)) if b.in_check() else None, "san": G["san"], "opening": __import__("satranc_open").name_for(G["san"]), "result": G["result"], "thinking": G["thinking"],
                "comment": G["comment"], "hint": G["hint"], "coach": G["coach"], "captured": caps, "material": mat, "stats": stats(),
                "levels": LEVEL_NAMES}


# ------------------------------------------------------------------ oyun akışı
def new_game(color: str = None, level: int = None) -> None:
    with _lock:
        G.update(board=C.Board(), moves=[], san=[], result=None, thinking=False, comment="", hint=None, last=None)
        if color in ("w", "b"):
            G["color"] = color
        if level and 1 <= int(level) <= 5:
            G["level"] = int(level)
        _save()


def set_level(level: int) -> None:
    with _lock:
        G["level"] = max(1, min(5, int(level)))
        _save()


def set_coach(on: bool) -> None:
    with _lock:
        G["coach"] = bool(on)
        _save()


def _finish_check():
    r = G["board"].result()
    if r and not G["result"]:
        G["result"] = r[0] + " · " + r[1]
        mine = "1-0" if G["color"] == "w" else "0-1"
        _record("beraberlik" if r[0] == "1/2-1/2" else "kazanç" if r[0] == mine else "kayıp")
        return r
    return None


def end_text(r) -> str:
    res, why = r
    if res == "1/2-1/2":
        return f"Oyun berabere bitti efendim, {why}."
    mine = "1-0" if G["color"] == "w" else "0-1"
    return "Mat! Tebrikler efendim, kazandınız." if res == mine else "Mat. Bu oyunu ben kazandım efendim. Yeni oyun ister misiniz?"


def player_move(m) -> dict:
    """Oyuncunun hamlesi (yasallık burada denetlenir). {'ok', 'san', 'say', 'engine'(bool)}"""
    with _lock:
        b = G["board"]
        if G["result"]:
            return {"ok": False, "say": "Oyun bitti efendim. Yeni oyun diyebilirsiniz."}
        if ("w" if b.white else "b") != G["color"] or G["thinking"]:
            return {"ok": False, "say": "Şu an sıra bende efendim, biraz bekleyin."}
        if m not in b.legal():
            return {"ok": False, "say": "Bu hamle kurallara uygun değil efendim."}
        before = b.copy()
        s = _apply(m)
        G["hint"] = None
        G["comment"] = ""
        r = _finish_check()
        _save()
        if r:
            return {"ok": True, "san": s, "say": end_text(r), "engine": False}
        G["thinking"] = True
        return {"ok": True, "san": s, "say": "", "engine": True, "before": before, "move": m}


def coach_note(before: C.Board, m) -> str:
    """Oyuncunun hamlesi en iyi hamleden belirgin kötüyse kısa açıklama (yalnızca koç açıkken)."""
    if not G["coach"]:
        return ""
    best, best_sc = C.analyse(before, 3, 2.0)
    if not best or best == m:
        return ""
    nb = before.copy()
    nb.push(m)
    reply, reply_sc = C.analyse(nb, 3, 2.0)
    my_sc = -reply_sc                                 # oyuncu açısından
    loss = best_sc - my_sc
    if loss < 150 or best_sc > 90000 and my_sc > 90000:
        return ""
    poss = {"Q": "veziriniz", "R": "kaleniz", "B": "filiniz", "N": "atınız", "P": "piyonunuz", "K": "şahınız"}
    if reply_sc > 90000:
        what = "Bu hamle rakibinize mat fırsatı veriyor."
    elif reply and nb.sq[reply[1]] != ".":
        what = f"Bu hamleden sonra {poss[nb.sq[reply[1]].upper()]} {C.name(reply[1])} karesinde alınabiliyor."
    else:
        what = "Bu hamle konumunuzu zayıflatıyor."
    return f"Koç: {what} Daha iyisi {before.san(best)} olabilirdi."


def engine_reply(before=None, m=None) -> str:
    """Arka planda çağrılır: koç notu + Jarvis'in hamlesi. Söylenecek metni döner."""
    note = ""
    try:
        if before is not None and m is not None:
            note = coach_note(before, m)
        with _lock:
            b = G["board"].copy()
            lv = G["level"]
        mv, sc = C.best_move(b, lv)
        with _lock:
            G["thinking"] = False
            if not mv or G["result"]:
                return note
            desc = G["board"].describe(mv)
            _apply(mv)
            G["comment"] = note
            r = _finish_check()
            _save()
        out = (note + " " if note else "") + desc.capitalize() + "."
        if r:
            out += " " + end_text(r)
        return out
    finally:
        G["thinking"] = False


def engine_first() -> bool:
    """Oyuncu siyahsa ve sıra beyazdaysa Jarvis başlar."""
    with _lock:
        if G["result"] or ("w" if G["board"].white else "b") == G["color"] or G["thinking"]:
            return False
        G["thinking"] = True
        return True


def undo() -> bool:
    """Son hamle çiftini (oyuncu + Jarvis) geri alır."""
    with _lock:
        if G["thinking"] or not G["moves"]:
            return False
        n = len(G["moves"])
        k = 2 if ("w" if G["board"].white else "b") == G["color"] else 1     # sıra oyuncudaysa Jarvis'in cevabı + oyuncunun hamlesi geri
        keep = [C.name(a) + C.name(b) + (p or "") for a, b, p in G["moves"][:max(0, n - k)]]
        G.update(board=C.Board(), moves=[], san=[], result=None, comment="", hint=None, last=None)
        for u in keep:
            _apply(_from_uci(u))
        _save()
        return True


def hint() -> str:
    with _lock:
        b = G["board"].copy()
        if G["result"] or ("w" if b.white else "b") != G["color"]:
            return ""
    m, _ = C.analyse(b, 3, 3.0)
    if not m:
        return ""
    G["hint"] = [C.name(m[0]), C.name(m[1])]
    return b.describe(m)


def resign() -> str:
    with _lock:
        if G["result"] or not G["moves"]:
            return ""
        G["result"] = ("0-1" if G["color"] == "w" else "1-0") + " · terk"
        _record("kayıp")
        _save()
        return "Teslim oldunuz efendim. İyi oyundu, yeni oyun diyebilirsiniz."


# ------------------------------------------------------------------ Türkçe hamle anlama
_LET = {"a": "a", "be": "b", "bi": "b", "b": "b", "ce": "c", "se": "c", "c": "c", "de": "d", "d": "d", "e": "e", "ef": "f", "f": "f", "ge": "g", "g": "g", "ha": "h", "h": "h"}
_NUM = {"bir": "1", "iki": "2", "üç": "3", "dört": "4", "beş": "5", "altı": "6", "yedi": "7", "sekiz": "8"}
_PIECE = [("N", r"\b(at|atı|atla|atımı|atım|knight)\b"), ("B", r"\b(fil|fili|filimi|filim|filler|bishop)\b"), ("R", r"\b(kale|kaleyi|kalemi|kalem|rook)\b"),
          ("Q", r"\b(vezir|veziri|vezirimi|vezirim|queen)\b"), ("K", r"\b(şah|şahı|şahımı|şahım|king)\b"), ("P", r"\b(piyon|piyonu|piyonla|piyonumu|pawn)\b")]


def _squares(t: str) -> list:
    t = re.sub(r"\b(" + "|".join(_NUM) + r")\b", lambda m: _NUM[m.group(1)], t)
    t = re.sub(r"\b(be|bi|ce|se|de|ef|ge|ha)\s*([1-8])", lambda m: _LET[m.group(1)] + m.group(2), t)
    t = re.sub(r"\b([a-h])\s+([1-8])\b", r"\1\2", t)
    return re.findall(r"(?<![a-zçğıöşü])([a-h][1-8])(?![0-9])", t)


def parse(text: str):
    """Metinden yasal hamle: (hamle, None) ya da (None, açıklama)."""
    b = G["board"]
    legal = b.legal()
    raw = str(text).strip()
    t = raw.replace("İ", "i").replace("I", "ı").lower()
    t = re.sub(r"['’]\w*", " ", t)
    if re.search(r"\b(kısa rok|küçük rok|rok kısa|o-o)\b", t) and not re.search(r"o-o-o", t):
        m = next((x for x in legal if b.sq[x[0]].upper() == "K" and x[1] - x[0] == 2), None)
        return (m, None) if m else (None, "Şu an kısa rok yapılamaz efendim.")
    if re.search(r"\b(uzun rok|büyük rok|rok uzun)\b|o-o-o", t):
        m = next((x for x in legal if b.sq[x[0]].upper() == "K" and x[0] - x[1] == 2), None)
        return (m, None) if m else (None, "Şu an uzun rok yapılamaz efendim.")
    # cebirsel gösterim: Nf3, Af3, Vxd5, exd5, e8=Q, Ke2 (K = Kale, Ş = şah)
    m = re.fullmatch(r"\s*([NBRQKAFVŞnbrqkafvş]?)([a-h]?[1-8]?)x?([a-h][1-8])(?:=?([QRBNVAFKqrbnvafk]))?[+#!?]*\s*", raw.replace("İ", "i"))
    promo_map = {"q": "Q", "v": "Q", "r": "R", "k": "R", "b": "B", "f": "B", "n": "N", "a": "N"}
    if m and (m.group(1) or len(raw.strip()) <= 7):
        pl = m.group(1)
        types = {"": ["P"], "n": ["N"], "a": ["N"], "b": ["B"], "f": ["B"], "r": ["R"], "q": ["Q"], "v": ["Q"], "ş": ["K"], "k": ["R", "K"]}[pl.lower()]
        if pl == "B":
            types = ["B"]
        to = C.sq(m.group(3))
        dis = m.group(2)
        promo = promo_map.get((m.group(4) or "").lower())
        for tp in types:
            c = [x for x in legal if x[1] == to and b.sq[x[0]].upper() == tp and (not dis or dis in C.name(x[0])) and (x[2] == (promo or ("Q" if x[2] else None)))]
            if len(c) == 1:
                return c[0], None
            if len(c) > 1:
                return None, f"Bu kareye giden birden fazla taşınız var efendim, hangisi olduğunu söyleyin; örneğin {C.name(c[0][0])} {m.group(3)}."
    sqs = _squares(t)
    ptype = next((p for p, pat in _PIECE if re.search(pat, t)), None)
    promo = None
    pm = re.search(r"(vezir|kale|fil|at)\w*\s*(olsun|çıkar|terfi|yap)|terfi\w*\s*(vezir|kale|fil|at)", t)
    if pm:
        promo = {"vezir": "Q", "kale": "R", "fil": "B", "at": "N"}[pm.group(1) or pm.group(3)]
    if not sqs:
        return None, "Hamleyi anlayamadım efendim. Örneğin e4, at f3, e2 e4 ya da kısa rok deyin."
    if len(sqs) >= 2:
        a, to = C.sq(sqs[0]), C.sq(sqs[1])
        c = [x for x in legal if x[0] == a and x[1] == to]
    else:
        to = C.sq(sqs[0])
        c = [x for x in legal if x[1] == to]
        if ptype:
            c = [x for x in c if b.sq[x[0]].upper() == ptype]
        elif len({b.sq[x[0]].upper() for x in c}) > 1 and any(b.sq[x[0]].upper() == "P" for x in c):
            c = [x for x in c if b.sq[x[0]].upper() == "P"]          # "e4" tek başına: piyon
    if any(x[2] for x in c):
        c = [x for x in c if x[2] == (promo or "Q")]
    if len(c) == 1:
        return c[0], None
    if not c:
        what = (C.TR[ptype].lower() + " ile ") if ptype else ""
        return None, f"{what}{sqs[-1]} karesine yasal bir hamle yok efendim."
    names = ", ".join(sorted({f"{C.TR[b.sq[x[0]].upper()].lower()} {C.name(x[0])}" for x in c}))
    return None, f"Oraya birden fazla taş gidebiliyor efendim: {names}. Hangisi olduğunu söyleyin, örneğin {C.name(c[0][0])} {C.name(c[0][1])}."
