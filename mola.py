"""Mola modu çekirdeği: tek bir geri sayım. Varsayılan süre ayarlanabilir (config.json: mola_len, dakika). Durum yalnızca bellekte tutulur.
Süre bitince sesli haber, hatırlatıcı sistemi (reminders.json, kind='mola') üzerinden gelir; böylece mod penceresi küçültülmüş ya da kapanmış olsa da bildirilir.
Duraklatma, süre ekleme ve bitirme hatırlatmayı iptal edip yeniden kurar. Zaman kaynağı now() testlerde değiştirilebilir."""
import threading
import time

import reminders
import settings

LIMITS = (1, 180)
PRESETS = [5, 10, 15, 20, 30]
now = time.time
_lock = threading.RLock()
S = {"on": False, "len": 0, "end": 0.0, "left": 0.0, "paused": False, "due": None}


def clamp(m) -> int:
    try:
        m = int(round(float(m)))
    except (TypeError, ValueError):
        m = 10
    return max(LIMITS[0], min(LIMITS[1], m))


def default_len() -> int:
    return clamp(settings.get("mola_len") or 10)


def set_default(m) -> int:
    m = clamp(m)
    settings.set("mola_len", m)
    return m


def _disarm() -> None:
    if S["due"] is not None:
        reminders.cancel_due(S["due"])
        S["due"] = None


def _arm() -> None:
    S["due"] = reminders.add_at(max(1.0, S["end"] - now()), "mola", "mola")


def start(minutes=None) -> int:
    """Molayı başlatır (çalışan varsa yenisiyle değiştirir). Dakika verilmezse varsayılan süre kullanılır."""
    m = clamp(minutes) if minutes else default_len()
    with _lock:
        _disarm()
        S.update(on=True, len=m, paused=False, end=now() + m * 60, left=m * 60.0)
        _arm()
    return m


def remaining() -> float:
    with _lock:
        if not S["on"]:
            return 0.0
        return S["left"] if S["paused"] else max(0.0, S["end"] - now())


def pause() -> bool:
    with _lock:
        if not S["on"] or S["paused"] or remaining() <= 0:
            return False
        S["left"] = remaining()
        S["paused"] = True
        _disarm()
        return True


def resume() -> bool:
    with _lock:
        if not S["on"] or not S["paused"]:
            return False
        S.update(paused=False, end=now() + S["left"])
        _arm()
        return True


def add(minutes) -> int:
    """Çalışan molaya dakika ekler (bitmişse yeniden başlatır). Yeni kalan süreyi dakika olarak döner; mola yoksa 0."""
    m = clamp(minutes)
    with _lock:
        if not S["on"]:
            return 0
        _disarm()
        if S["paused"]:
            S["left"] += m * 60
        else:
            S["end"] = max(S["end"], now()) + m * 60
            _arm()
        S["len"] += m
        return int(round(remaining() / 60))


def end() -> None:
    with _lock:
        _disarm()
        S.update(on=False, len=0, end=0.0, left=0.0, paused=False)


def snapshot() -> dict:
    """Sayfanın çizdiği durum. 'left' saniye cinsindendir; sayfa kendi saatine göre sayar (sunucu saati gönderilmez)."""
    with _lock:
        left = remaining()
        return {"on": S["on"], "len": S["len"], "left": round(left, 1), "paused": S["paused"], "finished": S["on"] and not S["paused"] and left <= 0,
                "default": default_len(), "presets": PRESETS, "limits": list(LIMITS)}
