"""Mola modu komut işleyicisi: 'başlat', '10 dakika', '5 dakika ekle', 'duraklat', 'devam', 'ne kadar kaldı', 'mola süresi 15 dakika olsun', 'bitir'.
Yalnızca mola durumunu (mola.py) değiştirir; güç/ışık/ses komutu yok. Çıktı: {'do': sayfaya giden durum, 'say': konuşulacak metin} ya da {'exit': True, 'say': ...}."""
import re

import mola as ml
import scenes
from scenes_pomodoro import _DUR, _W


def minutes_in(t: str):
    """'10 dakika', 'on beş dakika', 'yarım saat', '2 saat' cümlelerinden dakika çıkarır; yoksa None."""
    if re.search(r"yarım saat", t):
        return 30
    m = _DUR.search(t)
    if m:
        return scenes.num_in(m.group(1))
    m = re.search(r"(\d{1,2}|" + _W + r")\s*saat", t)
    if m:
        n = scenes.num_in(m.group(1))
        return n * 60 if n else None
    return None


def _res(say: str, **extra):
    return {"do": {"snap": ml.snapshot(), "msg": say, **extra}, "say": say}


def _left_text() -> str:
    s = int(ml.remaining())
    if not ml.S["on"]:
        return "Şu an çalışan bir mola yok efendim."
    if s <= 0:
        return "Molanız bitti efendim, çalışmaya dönebilirsiniz."
    m, sec = divmod(s, 60)
    return f"Molanın bitmesine {m} dakika {sec} saniye kaldı efendim." if m else f"Molanın bitmesine {sec} saniye kaldı efendim."


def mola(text: str, st: dict):
    t = scenes.norm(text)
    if not t:
        return None
    n = minutes_in(t)
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Başlat, on dakika, beş dakika ekle, duraklat, devam, ne kadar kaldı, mola süresi on beş dakika olsun, bitir ve çık diyebilirsiniz."}
    if re.search(r"\b(varsayılan|süre\w*)\b", t) and re.search(r"\b(olsun|yap|ayarla|değiştir|kaydet)\w*", t) and n:
        m = ml.set_default(n)
        return _res(f"Varsayılan mola süresi {m} dakika oldu efendim.")
    if re.search(r"\b(ekle|uzat|daha)\w*", t) and n:
        left = ml.add(n)
        return _res(f"{n} dakika ekledim, molanın bitmesine {left} dakika var efendim." if left else "Önce molayı başlatmanız gerekiyor efendim.")
    if re.search(r"\b(duraklat|durdur|beklet)\w*|^dur$", t):
        return _res("Mola duraklatıldı efendim." if ml.pause() else "Duraklatılacak çalışan bir mola yok efendim.")
    if re.search(r"\b(devam|sürdür)\w*", t):
        return _res("Mola devam ediyor efendim." if ml.resume() else "Duraklatılmış bir mola yok efendim.")
    if re.search(r"\b(kalan|ne kadar|kaç dakika|kaç saniye)\b", t) and not n:
        return _res(_left_text())
    if re.search(r"\b(bitir|çalışmaya dön|çalışmaya geç|yeter)\w*", t):
        return {"exit": True, "say": "Mola bitti efendim, çalışmaya dönelim."}
    if re.search(r"\b(başlat|başla|ver|kur|yap|olsun)\w*", t) or n:
        m = ml.start(n)
        return _res(f"{m} dakikalık mola başladı efendim. Dinlenin, bitince haber veririm.")
    return {"say": "Anlayamadım efendim. Başlat, on dakika, beş dakika ekle, duraklat ya da bitir diyebilirsiniz."}

