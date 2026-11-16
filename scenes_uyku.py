"""Uyku modu: süreyi siz seçersiniz ('30 dakika', 'bir saat'), karanlık ekranda yavaşça kararan sayaç ve isteğe bağlı uyku sesi.
Süre bitince ses yavaşça kısılır ve mod kendiliğinden kapanır; geri sayımı ve sesi sayfa yürütür (sunucu yalnızca seçili süreyi ve sesi saklar).
Bilgisayarı uyutmaz/kapatmaz; yalnızca bu modu kapatır."""
import re
import time

import scenes
import settings
from scenes_mola import minutes_in

LIMITS = (1, 600)
SOUNDS = [("yağmur", "rain", r"yağmur|yağış"), ("deniz", "sea", r"deniz|dalga"), ("rüzgar", "wind", r"rüzgar|rüzgâr"),
          ("beyaz gürültü", "white", r"beyaz|gürültü"), ("sessiz", "none", r"sessiz|ses yok|sesi kapat|sessizlik")]
PRESETS = [10, 15, 20, 30, 45, 60, 90]
S = {"on": False, "len": 0, "end": 0.0, "sound": "rain", "paused": False, "left": 0.0}


def clamp(m) -> int:
    try:
        m = int(round(float(m)))
    except (TypeError, ValueError):
        m = 30
    return max(LIMITS[0], min(LIMITS[1], m))


def default_len() -> int:
    return clamp(settings.get("uyku_len") or 30)


def snapshot() -> dict:
    left = (S["left"] if S["paused"] else max(0.0, S["end"] - time.time())) if S["on"] else 0.0
    return {"on": S["on"], "len": S["len"], "left": round(left, 1), "paused": S["paused"], "sound": S["sound"], "default": default_len(),
            "presets": PRESETS, "sounds": [{"key": k, "name": n} for n, k, _ in SOUNDS]}


def init_payload():
    S.update(on=False, len=0, end=0.0, paused=False)
    return snapshot()


def view():
    return snapshot()


def _say_time(m: int) -> str:
    h, mm = divmod(m, 60)
    return (f"{h} saat " if h else "") + (f"{mm} dakika" if mm or not h else "")


def uyku(text: str, st: dict):
    t = scenes.norm(text)
    if not t:
        return None
    n = minutes_in(t)
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Bir süre söyleyin, örneğin otuz dakika ya da bir saat. Yağmur, deniz, rüzgar, beyaz gürültü ya da sessiz diyerek ses seçebilirsiniz. "
                       "Beş dakika ekle, duraklat, devam, ne kadar kaldı, varsayılan süre kırk beş dakika olsun ve bitir de diyebilirsiniz."}
    for name, key, pat in SOUNDS:
        if re.search(pat, t) and not re.search(r"\b(ekle|uzat)\w*", t):
            S["sound"] = key
            return {"do": {"snap": snapshot()}, "say": f"Uyku sesi {name} efendim." if key != "none" else "Ses kapalı efendim, sessiz uyuyacaksınız."}
    if re.search(r"\b(varsayılan|süre\w*)\b", t) and re.search(r"\b(olsun|yap|ayarla|değiştir|kaydet)\w*", t) and n:
        m = clamp(n)
        settings.set("uyku_len", m)
        return {"do": {"snap": snapshot()}, "say": f"Varsayılan uyku süresi {_say_time(m)} oldu efendim."}
    if re.search(r"\b(ekle|uzat|daha)\w*", t) and n:
        if not S["on"]:
            return {"say": "Önce uyku sayacını başlatmanız gerekiyor efendim."}
        if S["paused"]:
            S["left"] += clamp(n) * 60
        else:
            S["end"] += clamp(n) * 60
        S["len"] += clamp(n)
        return {"do": {"snap": snapshot()}, "say": f"{clamp(n)} dakika ekledim efendim."}
    if re.search(r"\b(duraklat|durdur|beklet)\w*|^dur$", t):
        if not S["on"] or S["paused"]:
            return {"say": "Duraklatılacak çalışan bir sayaç yok efendim."}
        S.update(paused=True, left=max(0.0, S["end"] - time.time()))
        return {"do": {"snap": snapshot()}, "say": "Sayaç duraklatıldı efendim."}
    if re.search(r"\b(devam|sürdür)\w*", t):
        if not S["paused"]:
            return {"say": "Duraklatılmış bir sayaç yok efendim."}
        S.update(paused=False, end=time.time() + S["left"])
        return {"do": {"snap": snapshot()}, "say": "Sayaç devam ediyor efendim."}
    if re.search(r"\b(kalan|ne kadar|kaç dakika)\b", t) and not n:
        left = int(snapshot()["left"] // 60)
        return {"say": f"Uykuya {left} dakika var efendim." if S["on"] else "Sayaç çalışmıyor efendim."}
    if re.search(r"\b(bitir|iptal|vazgeç)\w*", t):
        S.update(on=False, len=0, end=0.0, paused=False)
        return {"do": {"snap": snapshot()}, "say": "Uyku sayacını iptal ettim efendim."}
    if re.search(r"\b(başlat|başla|kur|ayarla|uyu\w*|yat\w*|olsun)\w*", t) or n:
        m = clamp(n) if n else default_len()
        S.update(on=True, len=m, end=time.time() + m * 60, paused=False)
        return {"do": {"snap": snapshot(), "start": True}, "say": f"{_say_time(m)} sonra uyku modu kapanacak efendim. İyi geceler."}
    return {"say": "Anlayamadım efendim. Otuz dakika, bir saat, yağmur sesi ya da bitir diyebilirsiniz."}
