"""Telefondan bilgisayarda fare ve klavye kullanma (yalnızca Tailscale 'tam kontrol' yolu; remote._pc çağırır). Kullanıcının tercihi: telefon bilgisayarı tam yönetebilsin.
Koordinatlar 0-1 arası normalleştirilmiş birincil ekran konumudur (ekran yayınıyla aynı: mirror.grab_encode). Win32 SendInput/mouse_event ile gerçek girdi gönderilir.
Test için JARVIS_POWER_DRYRUN=1: hiçbir girdi gönderilmez (yalnızca doğrulama). Hız sınırı ve boyut sınırları aşağıdadır."""
import ctypes
import os
import time
from ctypes import wintypes

u32 = ctypes.windll.user32
MAX_TEXT = 500
_last = {"t": 0.0, "n": 0}

VK = {"enter": 0x0D, "return": 0x0D, "backspace": 0x08, "tab": 0x09, "esc": 0x1B, "escape": 0x1B, "delete": 0x2E, "del": 0x2E, "space": 0x20, "home": 0x24, "end": 0x23,
      "pageup": 0x21, "pagedown": 0x22, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28, "insert": 0x2D, "ctrl": 0x11, "control": 0x11, "alt": 0x12, "shift": 0x10,
      "win": 0x5B, "windows": 0x5B, "capslock": 0x14, "printscreen": 0x2C, "menu": 0x5D,
      "volumeup": 0xAF, "volumedown": 0xAE, "mute": 0xAD, "playpause": 0xB3, "next": 0xB0, "prev": 0xB1}
for i in range(1, 13):
    VK[f"f{i}"] = 0x6F + i
EXTENDED = {0x2E, 0x24, 0x23, 0x21, 0x22, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x5B, 0x5D}


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 32)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


def _dry() -> bool:
    return os.environ.get("JARVIS_POWER_DRYRUN") == "1"


def _rate() -> bool:
    """Saniyede en çok ~80 girdi; aşılırsa True (atla)."""
    now = time.time()
    if now - _last["t"] > 1.0:
        _last.update(t=now, n=0)
    _last["n"] += 1
    return _last["n"] > 80


def _screen():
    return u32.GetSystemMetrics(0), u32.GetSystemMetrics(1)


def _pt(nx, ny):
    sw, sh = _screen()
    return int(max(0.0, min(1.0, float(nx))) * (sw - 1)), int(max(0.0, min(1.0, float(ny))) * (sh - 1))


def _mouse(flags: int, data: int = 0):
    u32.mouse_event(flags, 0, 0, data & 0xFFFFFFFF, 0)


LEFT, RIGHT, MIDDLE = (0x2, 0x4), (0x8, 0x10), (0x20, 0x40)


def mouse(d: dict) -> str:
    """act: move | click | dclick | rclick | mclick | down | up | rdown | rup | scroll. Dönüş: açıklama ('ok' ya da hata)."""
    if _rate():
        return "hız sınırı"
    act = str(d.get("act") or "")
    try:
        if act == "scroll":
            dy = max(-30.0, min(30.0, float(d.get("dy") or 0)))
            if _dry():
                return "ok"
            _mouse(0x800, int(-dy * 120))                   # WHEEL: pozitif = yukarı; parmak yukarı kaydırınca sayfa aşağı gitsin diye işaret çevrilir
            return "ok"
        x, y = _pt(d.get("x"), d.get("y"))
    except (TypeError, ValueError):
        return "geçersiz"
    if act not in ("move", "click", "dclick", "rclick", "mclick", "down", "up", "rdown", "rup"):
        return "bilinmeyen"
    if _dry():
        return "ok"
    u32.SetCursorPos(x, y)
    if act == "click":
        _mouse(LEFT[0]); _mouse(LEFT[1])
    elif act == "dclick":
        for _ in range(2):
            _mouse(LEFT[0]); _mouse(LEFT[1]); time.sleep(0.04)
    elif act == "rclick":
        _mouse(RIGHT[0]); _mouse(RIGHT[1])
    elif act == "mclick":
        _mouse(MIDDLE[0]); _mouse(MIDDLE[1])
    elif act == "down":
        _mouse(LEFT[0])
    elif act == "up":
        _mouse(LEFT[1])
    elif act == "rdown":
        _mouse(RIGHT[0])
    elif act == "rup":
        _mouse(RIGHT[1])
    return "ok"


def _key_event(vk: int, up: bool):
    flags = (0x2 if up else 0) | (0x1 if vk in EXTENDED else 0)
    u32.keybd_event(vk, u32.MapVirtualKeyW(vk, 0), flags, 0)


def keys(d: dict) -> str:
    """keys: ['ctrl','c'] gibi: sırayla basılır, ters sırayla bırakılır. Tek harf/rakam ya da yukarıdaki adlar."""
    if _rate():
        return "hız sınırı"
    ks = d.get("keys")
    if not isinstance(ks, list) or not 1 <= len(ks) <= 5:
        return "geçersiz"
    codes = []
    for k in ks:
        k = str(k).lower().strip()
        if k in VK:
            codes.append(VK[k])
        elif len(k) == 1:
            r = u32.VkKeyScanW(ord(k))
            if r == -1:
                return "tuş yok"
            codes.append(r & 0xFF)
        else:
            return "tuş yok"
    if _dry():
        return "ok"
    for c in codes:
        _key_event(c, False)
    for c in reversed(codes):
        _key_event(c, True)
    return "ok"


def typing(d: dict) -> str:
    """text: Unicode olarak yazılır (Türkçe karakterler dahil). Tek seferde en çok 500 karakter."""
    text = str(d.get("text") or "")[:MAX_TEXT]
    if not text:
        return "boş"
    if _dry():
        return "ok"
    for ch in text:
        if ch == "\n":
            keys({"keys": ["enter"]})
            continue
        for up in (False, True):
            inp = INPUT(1, _U(ki=KEYBDINPUT(0, ord(ch), 0x4 | (0x2 if up else 0), 0, 0)))
            u32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        time.sleep(0.004)
    return "ok"


def handle(d: dict) -> str:
    t = d.get("type")
    if t == "mouse":
        return mouse(d)
    if t == "keys":
        return keys(d)
    if t == "type":
        return typing(d)
    return "bilinmeyen"


_shell_busy = {"on": False}


def shell(cmd: str) -> dict:
    """PowerShell komutu çalıştırır (en çok 60 sn, çıktı 20 KB ile sınırlı, tek seferde bir komut). {'out', 'code'} döner. Test: JARVIS_POWER_DRYRUN=1 çalıştırmaz."""
    import subprocess
    if _shell_busy["on"]:
        return {"out": "Önceki komut hâlâ çalışıyor.", "code": -1}
    if _dry():
        return {"out": "(test kipi: çalıştırılmadı)", "code": 0}
    _shell_busy["on"] = True
    try:
        p = subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + cmd],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, cwd=os.path.expanduser("~"), creationflags=0x08000000)
        try:
            out, _ = p.communicate(timeout=60)
            code = p.returncode
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, creationflags=0x08000000)
            out, _ = p.communicate()
            code = -2
        txt = out.decode("utf-8", "replace")
        if code == -2:
            txt += "\n(60 saniyede bitmedi, durduruldu)"
        return {"out": txt[:20000], "code": code}
    except Exception as e:
        return {"out": f"Çalıştırılamadı: {type(e).__name__}", "code": -1}
    finally:
        _shell_busy["on"] = False
