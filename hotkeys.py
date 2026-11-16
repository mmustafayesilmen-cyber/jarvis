"""Ayarlanabilir genel kısayollar. 'Masaüstüne geç' kısayolu (config.json: kisayol_peek, varsayılan ctrl+alt+m) ve Hızlı Başlatıcı sahnelerinin kısayolları
(system_presets.json) buradan kaydedilir. Yalnızca RegisterHotKey kullanılır: tuş kaydı/dinleme yoktur; kısayol yalnızca basılınca çalışır.
En az bir değiştirici (Ctrl / Alt / Win) şarttır, böylece tek bir harf kısayolu yazarken tetiklenmez."""
import ctypes
import threading
import time
from ctypes import wintypes

MODS = {"alt": 1, "ctrl": 2, "control": 2, "kontrol": 2, "shift": 4, "üst karakter": 4, "win": 8, "windows": 8}
NAMED = {"space": 0x20, "boşluk": 0x20, "enter": 0x0D, "tab": 0x09, "esc": 0x1B, "home": 0x24, "end": 0x23, "insert": 0x2D, "delete": 0x2E,
         "pageup": 0x21, "pagedown": 0x22, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28}
PEEK_ID = 0x4A41
SCENE_ID = 0x4B00
RELOAD = threading.Event()
STATUS: dict = {}        # kısayol -> kaydedilebildi mi


def parse(s: str):
    """'ctrl+alt+1' -> (değiştirici, sanal tuş) ya da None (geçersiz / değiştirici yok)."""
    s = (s or "").lower().replace("+", " ").replace("-", " ").strip()
    if not s:
        return None
    mods, key = 0, None
    for tok in s.split():
        if tok in MODS:
            mods |= MODS[tok]
        elif key is None:
            key = tok
        else:
            return None
    if key is None or not (mods & (1 | 2 | 8)):
        return None
    if key in NAMED:
        vk = NAMED[key]
    elif len(key) == 1 and key.isascii() and key.isalnum():
        vk = ord(key.upper())
    elif key[0] == "f" and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        vk = 0x70 + int(key[1:]) - 1
    else:
        return None
    return mods, vk


def canon(s: str) -> str:
    """Kullanıcının yazdığı kısayolu 'ctrl+alt+m' biçimine getirir; geçersizse ''."""
    p = parse(s)
    if not p:
        return ""
    mods, vk = p
    names = [n for n, b in (("ctrl", 2), ("alt", 1), ("shift", 4), ("win", 8)) if mods & b]
    inv = {v: k for k, v in NAMED.items() if k.isascii() and k not in ("boşluk",)}
    key = inv.get(vk) or (f"f{vk - 0x70 + 1}" if 0x70 <= vk <= 0x87 else chr(vk).lower())
    return "+".join(names + [key])


def entries(peek_fn):
    import settings
    out = []
    pk = settings.get("kisayol_peek")
    pk = "ctrl+alt+m" if pk is None else pk
    if pk:
        out.append((PEEK_ID, pk, peek_fn))
    try:
        import scenes  # önce scenes: scenes_yeni, scenes içinden yüklenir (döngüsel içe aktarma)
        import scenes_yeni
        for i, (combo, name) in enumerate(scenes_yeni.hotkey_scenes()):
            out.append((SCENE_ID + i, combo, lambda n=name: scenes_yeni.launcher_run(n)))
    except Exception as e:
        print("kısayol sahneleri okunamadı:", type(e).__name__, flush=True)
    return out


def run(peek_fn):
    """Kısayol iş parçacığı: RELOAD kurulunca kayıtlar yeniden okunur (ayar değişince)."""
    u = ctypes.windll.user32
    reg: dict = {}

    def sync():
        for hid in list(reg):
            u.UnregisterHotKey(None, hid)
        reg.clear()
        STATUS.clear()
        for hid, combo, fn in entries(peek_fn):
            p = parse(combo)
            if not p:
                continue
            ok = bool(u.RegisterHotKey(None, hid, p[0] | 0x4000, p[1]))      # 0x4000 = NOREPEAT
            STATUS[combo] = ok
            if ok:
                reg[hid] = fn
            else:
                print(f"kısayol {combo} kaydedilemedi (başka uygulama kullanıyor olabilir)", flush=True)
    sync()
    msg = wintypes.MSG()
    while True:
        if RELOAD.is_set():
            RELOAD.clear()
            sync()
        if u.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            if msg.message == 0x0312:                       # WM_HOTKEY
                fn = reg.get(int(msg.wParam))
                if fn:
                    def go(f=fn):
                        try:
                            f()
                        except Exception as e:
                            print("kısayol hatası:", type(e).__name__, e, flush=True)
                    threading.Thread(target=go, daemon=True).start()
        else:
            time.sleep(0.05)
