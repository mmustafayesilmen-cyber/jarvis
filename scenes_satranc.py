"""Satranç modu komutları. Hamleler: 'e4', 'e2 e4', 'at f3', 'fil c4 alır', 'kısa rok', 'Af3', 'Nf3'. Diğer: yeni oyun (beyaz/siyah, seviye),
seviye 1-5, geri al, ipucu, koç aç/kapat, teslim, tahtayı çevir, kim önde, son hamle. Jarvis'in hamlesi arka planda hesaplanır ('later')."""
import re

import chess_engine as C
import satranc as S
import scenes

LV = {"yeni başlayan": 1, "acemi": 1, "kolay": 2, "orta": 3, "zor": 4, "usta": 5}


def _engine_later(before=None, m=None):
    return lambda: S.engine_reply(before, m)


def _new(t: str) -> dict:
    color = "b" if re.search(r"\bsiyah\w*", t) else "w" if re.search(r"\bbeyaz\w*", t) else None
    lv = _level_in(t)
    S.new_game(color, lv)
    v = S.view()
    say = f"Yeni oyun efendim. Siz {'beyazsınız, ilk hamle sizde' if v['color'] == 'w' else 'siyahsınız, ilk hamleyi ben yapıyorum'}. Seviye: {v['levelName']}."
    out = {"do": {"new": True}, "say": say}
    if S.engine_first():
        out["later"] = _engine_later()
    return out


def _level_in(t: str):
    m = re.search(r"\b(seviye|zorluk|level)\w*\s*(\d|bir|iki|üç|dört|beş)\b", t)
    if m:
        return scenes.num_in(m.group(2))
    for k, v in LV.items():
        if re.search(r"\b" + k + r"\b", t):
            return v
    return None


def satranc(text: str, st: dict):
    t = scenes.norm(text)
    v = S.view()
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar|nasıl oynan\w*)\b", t):
        return {"say": "Hamlenizi söyleyin: e dört, at f üç, fil c dört, kısa rok gibi. Ya da tahtada taşa tıklayıp gideceği kareye tıklayın. "
                       "Yeni oyun siyah, seviye üç, geri al, ipucu, koç kapat, teslim ol ve tahtayı çevir komutları da var."}
    if re.search(r"\b(yeni oyun|yeni maç|baştan başla|oyunu yeniden|tekrar oynayalım|yeniden başla)\b", t):
        return _new(t)
    if re.search(r"\b(seviye|zorluk|level)\w*\b", t) or re.fullmatch(r"(yeni başlayan|acemi|kolay|orta|zor|usta)( seviye\w*| ol| olsun| yap)?", t):
        lv = _level_in(t)
        if not lv:
            return {"say": f"Şu anki seviye {v['levelName']}. Bir ile beş arasında bir seviye söyleyin efendim."}
        S.set_level(lv)
        return {"do": {"level": lv}, "say": f"Seviye {S.LEVEL_NAMES[lv]} oldu efendim" + (", yeni hamlelerimde geçerli." if v["san"] else ".")}
    if re.search(r"\b(geri al|hamleyi geri|son hamleyi geri|geri alayım|undo)\b", t):
        if not S.undo():
            return {"say": "Geri alınacak hamle yok ya da şu an düşünüyorum efendim."}
        out = {"do": {"undo": True}, "say": "Geri aldım efendim, sıra sizde."}
        if S.engine_first():
            out.update(say="Geri aldım efendim.", later=_engine_later())
        return out
    if re.search(r"\b(ipucu|ne oynamalıyım|ne oynayayım|en iyi hamle|yardım et|öner)\w*", t):
        return {"say": "Bakıyorum efendim.", "later": lambda: (lambda h: f"İpucu: {h}." if h else "Şu an ipucu veremiyorum efendim, sıra sizde olmalı.")(S.hint())}
    if re.search(r"\bkoç\w*\b", t):
        on = not re.search(r"kapat|kapa|istemiyorum|sus|durdur", t)
        S.set_coach(on)
        return {"do": {"coach": on}, "say": "Koç açık efendim, belirgin hatalı bir hamle yaparsanız nedenini söylerim." if on else "Koç kapalı efendim, hamlelerinize yorum yapmayacağım."}
    if re.search(r"\b(teslim|pes ediyorum|pes ettim|terk)\w*", t):
        r = S.resign()
        return {"do": {"over": True}, "say": r or "Şu an teslim olunacak bir oyun yok efendim."}
    if re.search(r"\b(tahtayı|tahta)\s*(çevir|döndür)\w*", t):
        return {"do": {"flip": True}, "say": ""}
    if re.search(r"\b(kim önde|durum|puan|skor|malzeme)\b", t):
        mat = v["material"] * (1 if v["color"] == "w" else -1)
        if abs(mat) < 100:
            s = "Malzeme eşit efendim."
        elif mat > 0:
            s = f"Siz yaklaşık {abs(mat) // 100} piyon değerinde öndesiniz efendim."
        else:
            s = f"Ben yaklaşık {abs(mat) // 100} piyon değerinde öndeyim efendim."
        st_ = v["stats"].get(str(v["level"]), {})
        if st_:
            s += f" Bu seviyede {st_.get('kazanç', 0)} galibiyet, {st_.get('kayıp', 0)} yenilgi, {st_.get('beraberlik', 0)} beraberliğiniz var."
        return {"say": s}
    if re.search(r"\b(son hamle|ne oynadın|hangi hamle|ne yaptın)\b", t):
        return {"say": f"Son hamle {v['san'][-1]}." if v["san"] else "Henüz hamle yapılmadı efendim."}
    if v["thinking"]:
        return {"say": "Düşünüyorum efendim, birazdan hamlemi yapacağım."}
    if v["result"]:
        return {"say": "Oyun bitti efendim. Yeni oyun ya da geri al diyebilirsiniz."}
    m, why = S.parse(text)
    if not m:
        return {"say": why}
    r = S.player_move(m)
    if not r["ok"]:
        return {"say": r["say"]}
    out = {"do": {"moved": r["san"]}, "say": r["say"]}
    if r.get("engine"):
        out["later"] = _engine_later(r["before"], r["move"])
    return out


def ws(d: dict, st: dict):
    t = str(d.get("type", ""))[8:]
    if t == "move":
        try:
            m = (C.sq(str(d.get("from"))[:2]), C.sq(str(d.get("to"))[:2]), str(d.get("promo") or "")[:1].upper() or None)
        except (ValueError, IndexError):
            return {}
        if m[2] and m[2] not in "QRBN":
            return {}
        legal = S.G["board"].legal()
        if m not in legal and (m[0], m[1], "Q") in legal:      # terfi seçilmediyse vezir
            m = (m[0], m[1], "Q")
        r = S.player_move(m)
        if not r["ok"]:
            return {"say": r["say"], "speak": True}
        out = {"do": {"moved": r["san"]}, "say": r["say"], "speak": bool(r["say"])}
        if r.get("engine"):
            out["later"] = _engine_later(r["before"], r["move"])
        return out
    if t == "new":
        color = d.get("color") if d.get("color") in ("w", "b") else None
        lv = int(d.get("level")) if str(d.get("level", "")).isdigit() else None
        S.new_game(color, lv)
        out = {"do": {"new": True}}
        if S.engine_first():
            out["later"] = _engine_later()
        return out
    if t == "resume":                                       # pencere açıldı, yarım oyunda sıra Jarvis'teyse devam
        return {"later": _engine_later()} if S.engine_first() else {}
    if t == "level":
        if str(d.get("level", "")).isdigit():
            S.set_level(int(d["level"]))
        return {}
    if t == "undo":
        if not S.undo():
            return {}
        out = {"do": {"undo": True}}
        if S.engine_first():
            out["later"] = _engine_later()
        return out
    if t == "hint":
        return {"later": lambda: (lambda h: f"İpucu: {h}." if h else "Şu an ipucu veremiyorum efendim.")(S.hint())}
    if t == "coach":
        S.set_coach(bool(d.get("on")))
        return {}
    if t == "resign":
        return {"say": S.resign(), "speak": True}
    return {}


def init_payload():
    if not S.G["loaded"]:
        S.load()
    return S.view()
