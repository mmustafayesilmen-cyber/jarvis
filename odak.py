"""Derin odak modu çekirdeği: tek bir geri sayım + başlarken açık pencereleri nazikçe kapatma/küçültme.
Kapatma ZORLA değil, her pencereye normal 'kapat' iletisi (WM_CLOSE) gönderilir: kaydedilmemiş işi olan uygulamalar kendi 'kaydet?' penceresini gösterir, hiçbir şey kaybolmaz.
Hangi pencerelerin kapanacağı kullanıcıya listelenir ve onay ister; Jarvis'in kendi pencereleri ve Claude uygulaması listeye hiç girmez. Süre bitince sesli haber hatırlatıcı sistemindendir (kind='odak').
Test için JARVIS_POWER_DRYRUN=1: hiçbir pencereye dokunulmaz. Süre config.json: odak_len (1-240 dk)."""
import ctypes
import os
import threading
import time
from ctypes import wintypes

import psutil

import reminders
import settings

LIMITS = (1, 240)
PRESETS = [25, 45, 60, 90, 120]
now = time.time
_lock = threading.RLock()
S = {"on": False, "len": 0, "end": 0.0, "left": 0.0, "paused": False, "due": None, "closed": 0}
KEEP = {"pythonw.exe", "python.exe", "claude.exe", "dwm.exe", "searchhost.exe", "startmenuexperiencehost.exe", "shellexperiencehost.exe", "textinputhost.exe"}
SHELL_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "NotifyIconOverflowWindow"}
WM_CLOSE = 0x0010
user32 = ctypes.windll.user32
dwm = ctypes.windll.dwmapi


def clamp(m) -> int:
    try:
        m = int(round(float(m)))
    except (TypeError, ValueError):
        m = 45
    return max(LIMITS[0], min(LIMITS[1], m))


def default_len() -> int:
    return clamp(settings.get("odak_len") or 45)


def set_default(m) -> int:
    m = clamp(m)
    settings.set("odak_len", m)
    return m


def windows() -> list:
    """Kapatılabilir açık pencereler: [{'hwnd', 'title', 'app', 'min'}]. Jarvis, Claude ve kabuk pencereleri hariç."""
    out = []
    me = os.getpid()
    WNDENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        cloaked = wintypes.DWORD()
        dwm.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked))          # 14 = DWMWA_CLOAKED (sanal masaüstü/arka plan UWP)
        if cloaked.value:
            return True
        if user32.GetWindowLongW(hwnd, -20) & 0x80:                                                  # WS_EX_TOOLWINDOW
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n <= 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        title = buf.value.strip()
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, cls, 64)
        if not title or cls.value in SHELL_CLASSES or title.upper().startswith("JARVIS"):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == me:
            return True
        try:
            app = psutil.Process(pid.value).name()
        except Exception:
            return True
        if app.lower() in KEEP:
            return True
        out.append({"hwnd": int(hwnd), "title": title[:90], "app": app[:-4] if app.lower().endswith(".exe") else app, "min": bool(user32.IsIconic(hwnd))})
        return True
    user32.EnumWindows(WNDENUM(cb), 0)
    return out


def act(hwnds: list, mode: str) -> int:
    """mode 'close' (nazik kapat) ya da 'min' (küçült). Yalnızca şu an windows() listesinde olan pencerelere dokunur (eski/yanlış kimlikler yok sayılır)."""
    ok = {w["hwnd"] for w in windows()}
    n = 0
    for h in hwnds:
        try:
            h = int(h)
        except (TypeError, ValueError):
            continue
        if h not in ok:
            continue
        if os.environ.get("JARVIS_POWER_DRYRUN") == "1":
            n += 1
            continue
        if mode == "close":
            user32.PostMessageW(h, WM_CLOSE, 0, 0)
        else:
            user32.ShowWindow(h, 6)                                  # SW_MINIMIZE
        n += 1
    S["closed"] += n if mode == "close" else 0
    return n


def _disarm() -> None:
    if S["due"] is not None:
        reminders.cancel_due(S["due"])
        S["due"] = None


def _arm() -> None:
    S["due"] = reminders.add_at(max(1.0, S["end"] - now()), "odak", "odak")


def start(minutes=None) -> int:
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
        S["left"], S["paused"] = remaining(), True
        _disarm()
        return True


def resume() -> bool:
    with _lock:
        if not S["on"] or not S["paused"]:
            return False
        S.update(paused=False, end=now() + S["left"])
        _arm()
        return True


def end() -> None:
    with _lock:
        _disarm()
        S.update(on=False, len=0, end=0.0, left=0.0, paused=False)


def snapshot(with_windows: bool = False) -> dict:
    with _lock:
        left = remaining()
        d = {"on": S["on"], "len": S["len"], "left": round(left, 1), "paused": S["paused"], "finished": S["on"] and not S["paused"] and left <= 0,
             "default": default_len(), "presets": PRESETS, "limits": list(LIMITS), "closed": S["closed"]}
    if with_windows:
        d["windows"] = [{k: v for k, v in w.items()} for w in windows()]
    return d
