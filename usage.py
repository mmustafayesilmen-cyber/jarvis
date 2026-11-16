"""Bilgisayar kullanım süresi: Jarvis çalışırken, son 2 dakikada klavye/fare kullanıldıysa o dilim 'aktif' sayılır (usage.json, yalnızca yerel).
Hangi uygulamanın öne çıktığı da süre olarak tutulur (yalnızca işlem adı, pencere başlığı/içerik okunmaz). Jarvis kapalıyken geçen süre ölçülemez."""
import ctypes
import datetime
import json
import os
import threading
import time
from ctypes import wintypes

import psutil

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usage.json")
STEP, IDLE_MAX, KEEP = 30, 120, 35
_lock = threading.Lock()
_db = {}
_started = False


class _LII(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def idle_seconds() -> float:
    li = _LII()
    li.cbSize = ctypes.sizeof(_LII)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):
        return 0.0
    return max(0.0, (ctypes.windll.kernel32.GetTickCount() - li.dwTime) / 1000.0)


def _fg_app() -> str:
    try:
        h = ctypes.windll.user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        n = psutil.Process(pid.value).name()
        return n[:-4] if n.lower().endswith(".exe") else n
    except Exception:
        return ""


def _load():
    global _db
    try:
        with open(FILE, encoding="utf-8") as f:
            _db = json.load(f)
    except (OSError, ValueError):
        _db = {}


def _save():
    cut = (datetime.date.today() - datetime.timedelta(days=KEEP)).isoformat()
    for k in [k for k in _db if k < cut]:
        del _db[k]
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(_db, f, ensure_ascii=False)
    except OSError:
        pass


def _loop():
    n = 0
    while True:
        time.sleep(STEP)
        try:
            if idle_seconds() < IDLE_MAX:
                d = _db.setdefault(datetime.date.today().isoformat(), {"sec": 0, "apps": {}})
                with _lock:
                    d["sec"] += STEP
                    app = _fg_app()
                    if app:
                        d["apps"][app] = d["apps"].get(app, 0) + STEP
                n += 1
                if n % 10 == 0:
                    with _lock:
                        _save()
        except Exception as e:
            print("kullanım süresi hatası:", type(e).__name__, flush=True)


def start():
    global _started
    if _started:
        return
    _started = True
    _load()
    threading.Thread(target=_loop, daemon=True).start()


def stop_save():
    with _lock:
        _save()


def today() -> dict:
    d = _db.get(datetime.date.today().isoformat()) or {"sec": 0, "apps": {}}
    apps = sorted(d["apps"].items(), key=lambda kv: -kv[1])[:4]
    return {"sec": int(d["sec"]), "apps": [{"name": k, "sec": int(v)} for k, v in apps]}


def week() -> list:
    out = []
    for i in range(6, -1, -1):
        day = datetime.date.today() - datetime.timedelta(days=i)
        out.append({"gun": ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"][day.weekday()], "sec": int((_db.get(day.isoformat()) or {}).get("sec", 0))})
    return out
