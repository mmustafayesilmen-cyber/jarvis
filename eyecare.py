"""Göz molası: bilgisayar başında geçen süreyi ölçer, her 2 saatte bir (ayarlanabilir) 2 dakikalık tam ekran göz molası zamanlayıcısı açtırır.
Süre klavye/fare kullanımından ölçülür (Windows GetLastInputInfo); hiçbir tuş ya da içerik kaydedilmez, yalnızca 'en son ne zaman dokunuldu' okunur.
5 dakikadan uzun ara (bilgisayardan kalkma, ekran kilidi, uyku) zaten dinlenme sayılır ve sayaç sıfırlanır. Video izlerken 5 dakikaya kadar dokunmamak
'başında' sayılır. Ayarlar config.json'da: eye_on, eye_every (dk), eye_len (dk). Zaman/boşta kalma kaynakları testlerde değiştirilebilir."""
import threading
import time

import settings

AWAY = 300              # bu kadar saniye dokunulmazsa "bilgisayardan kalktı" sayılır
SNOOZE = 600            # "ertele": 10 dakika
now = time.time
_lock = threading.Lock()
S = {"active": 0.0, "last": None, "away_since": None, "snooze_until": 0.0, "last_break": 0.0, "breaks_today": 0, "day": ""}


def idle_seconds() -> float:
    """Son klavye/fare girdisinden bu yana geçen saniye (Windows)."""
    import ctypes
    from ctypes import wintypes

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]
    li = LASTINPUTINFO()
    li.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):
        return 0.0
    return max(0.0, (ctypes.windll.kernel32.GetTickCount() - li.dwTime) / 1000.0)


def cfg() -> dict:
    d = settings.load()
    return {"on": bool(d.get("eye_on", True)), "every": max(15, min(480, int(d.get("eye_every", 120) or 120))),
            "len": max(1, min(15, int(d.get("eye_len", 2) or 2)))}


def tick(idle: float):
    """Periyodik çağrılır (ör. 15 sn). Mola zamanıysa 'due' döner, yoksa None."""
    t = now()
    c = cfg()
    with _lock:
        day = time.strftime("%Y-%m-%d", time.localtime(t))
        if S["day"] != day:
            S.update(day=day, breaks_today=0)
        last = S["last"]
        S["last"] = t
        if last is None:
            return None
        if t - last >= AWAY:                          # bilgisayar uykudaydı / Jarvis duraklamıştı: bu da ara sayılır
            S["active"] = 0.0
            return None
        dt = t - last
        if idle >= AWAY:
            if S["away_since"] is None:
                S["away_since"] = t - idle
            if t - S["away_since"] >= AWAY:           # gerçek bir ara verdi: gözler dinlendi, sayaç baştan
                S["active"] = 0.0
            return None
        S["away_since"] = None
        S["active"] += dt
        if not c["on"] or t < S["snooze_until"]:
            return None
        if S["active"] >= c["every"] * 60:
            return "due"
        return None


def started_break() -> None:
    with _lock:
        S.update(active=0.0, last_break=now(), snooze_until=0.0)
        S["breaks_today"] += 1


def snooze(sec: int = SNOOZE) -> None:
    with _lock:
        S["snooze_until"] = now() + sec


def status() -> dict:
    c = cfg()
    with _lock:
        left = max(0, c["every"] * 60 - S["active"])
        return {**c, "active_min": int(S["active"] // 60), "left_min": int(round(left / 60)), "breaks_today": S["breaks_today"],
                "snoozed": now() < S["snooze_until"]}


START_HOOK = None       # main.py: göz molası zamanlayıcısını açar ve söylenecek metni döner


def _dk(m: int) -> str:
    h, mm = divmod(int(m), 60)
    return ((f"{h} saat " if h else "") + (f"{mm} dakika" if mm or not h else "")).strip()


def _dir(m: int) -> str:
    """'2 saattir', '90 dakikadır' (son sözcüğe göre ek)."""
    s = _dk(m)
    return s + ("tir" if s.endswith("saat") else "dır")


def announce(c=None) -> str:
    c = c or cfg()
    return (f"Efendim, {_dir(c['every'])} bilgisayar başındasınız. {c['len']} dakikalık göz molası: ekrandan uzaklaşın, "
            "pencereden en uzak noktaya bakın ve gözlerinizi sık sık kırpın. Süre bitince haber vereceğim.")


def route(t: str):
    """Sesli komutlar: göz molası aç / kapat / durum / ertele / şimdi, 'göz molası her 90 dakikada', 'göz molası 3 dakika olsun'."""
    import re
    if re.fullmatch(r"(gözlerim|gözüm) (çok )?(yoruldu|yanıyor|ağrıyor|acıyor|kurudu)", t) and START_HOOK:
        return START_HOOK()
    if not re.search(r"\bgöz\w*\b", t) or not re.search(r"\b(mola\w*|dinlen\w*|hatırlat\w*|koru\w*)\b", t):
        return None
    if re.search(r"\b(ne zaman|kaç dakika kaldı|kalan|durum|ne kadardır|ne kadar süredir|ne kadar oldu)\b", t):
        s = status()
        if not s["on"]:
            return "Göz molası hatırlatıcısı kapalı efendim. Göz molasını aç derseniz açarım."
        return (f"{_dir(s['active_min'])} bilgisayar başındasınız, bir sonraki göz molasına yaklaşık {_dk(s['left_min'])} var. "
                f"Bugün {s['breaks_today']} göz molası verdiniz.")
    import scenes
    m = re.search(r"(\d{1,3}|(?:[a-zçğıöşü]+ ){0,2}[a-zçğıöşü]+)\s*(dakika|dk|saat)\w*", t)
    n = scenes.num_in(m.group(1)) if m else None
    if n and re.search(r"\bher\b|aralık|sıklık", t):                      # "göz molası her 90 dakikada", "her 1 saatte"
        mins = max(15, min(480, n * (60 if m.group(2).startswith("saat") else 1)))
        settings.set("eye_every", mins)
        settings.set("eye_on", True)
        return f"Tamam efendim, her {_dk(mins).strip()} bilgisayar başında kaldığınızda göz molası vereceğim."
    if n and re.search(r"süre|sürsün|uzunluk|olsun", t) and not m.group(2).startswith("saat"):   # "göz molası 3 dakika olsun"
        n = max(1, min(15, n))
        settings.set("eye_len", n)
        return f"Tamam efendim, göz molaları {n} dakika sürecek."
    if re.search(r"\b(kapat|kapa|durdur|iptal|istemiyorum|devre dışı)\w*", t):
        settings.set("eye_on", False)
        return "Göz molası hatırlatıcısını kapattım efendim. Tekrar istediğinizde göz molasını aç demeniz yeterli."
    if re.search(r"\b(ertele|sonra|bekle)\w*", t):
        snooze()
        return "Göz molasını on dakika erteledim efendim."
    if re.search(r"\b(şimdi|hemen|ver)\b", t) and START_HOOK:              # "şimdi göz molası ver"
        return START_HOOK()
    if re.search(r"\b(aç|başlat|etkinleştir|açık)\w*", t):
        settings.set("eye_on", True)
        c = cfg()
        return f"Göz molası hatırlatıcısı açık efendim: her {_dk(c['every']).strip()} bilgisayar başında kaldığınızda {c['len']} dakikalık bir mola zamanlayıcısı açacağım."
    return None
