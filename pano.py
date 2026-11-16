"""Pano geçmişi: kopyaladığınız son 50 metin / link / görsel / dosya yolu YALNIZCA BELLEKTE (RAM) tutulur, diske yazılmaz; Jarvis kapanınca silinir.
Hazır metin parçaları (kalıcı) ayrıca scenes_gunluk içinde pano_parcalar.json'dadır. İzleme ayarla kapatılabilir (config.json: pano_izle).
Gizlilik: parola yöneticilerinin 'geçmişe ekleme' bayrağını koyduğu içerik hiç alınmaz; parola/anahtar gibi görünen metinler listede gizli (••••) gösterilir
ama tıklayınca yine panoya konabilir. Panoyu kendimiz kurunca (geri koyma) bu yeni kayıt sayılmaz."""
import base64
import io
import itertools
import re
import threading
import time

MAX = 50
MAX_IMG = 10
MAX_TEXT = 5000
MAX_PNG = 6 * 1024 * 1024
H: list = []                    # en yeni başta
_lock = threading.Lock()
_ids = itertools.count(1)
S = {"self_seq": 0, "last": 0, "run": False}
ON_CHANGE = None                # main.py: pano değişince sayfaya haber verir

_SECRET_WORDS = re.compile(r"password|parola|şifre|sifre|passwd|secret|api[_-]?key|token|bearer|sk-[a-z0-9]|ghp_|AKIA[0-9A-Z]{8}", re.I)


def _sensitive(t: str) -> bool:
    t = t.strip()
    if _SECRET_WORDS.search(t) and len(t) < 300:
        return True
    if re.fullmatch(r"\S{8,128}", t) and not re.match(r"https?://|www\.|[\w.-]+\.(com|org|net|tr|io)\b", t, re.I):
        classes = sum(bool(re.search(p, t)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^\w\s]"))
        return classes >= 3
    return False


def _user32():
    import ctypes
    return ctypes.windll.user32


def _read_clip():
    """('text'|'image'|'files', değer) ya da None (boş / parola yöneticisi bayrağı / okunamadı)."""
    import win32clipboard as w
    import win32con
    for _ in range(6):
        try:
            w.OpenClipboard()
            break
        except Exception:
            time.sleep(0.05)
    else:
        return None
    try:
        for name in ("ExcludeClipboardContentFromMonitorProcessing",):
            if w.IsClipboardFormatAvailable(w.RegisterClipboardFormat(name)):
                return None
        f2 = w.RegisterClipboardFormat("CanIncludeInClipboardHistory")
        if w.IsClipboardFormatAvailable(f2):
            try:
                v = w.GetClipboardData(f2)
                if v is not None and (v == 0 or (isinstance(v, (bytes, bytearray)) and v[:1] == b"\x00")):
                    return None
            except Exception:
                return None
        if w.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            return "text", w.GetClipboardData(win32con.CF_UNICODETEXT)
        if w.IsClipboardFormatAvailable(win32con.CF_HDROP):
            return "files", list(w.GetClipboardData(win32con.CF_HDROP))
        if w.IsClipboardFormatAvailable(win32con.CF_DIB):
            return "image", None
    except Exception:
        return None
    finally:
        try:
            w.CloseClipboard()
        except Exception:
            pass
    return None


def _grab_image():
    from PIL import Image, ImageGrab
    im = ImageGrab.grabclipboard()
    if not isinstance(im, Image.Image):
        return None
    buf = io.BytesIO()
    im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB").save(buf, "PNG")
    png = buf.getvalue()
    if len(png) > MAX_PNG:
        return None
    th = im.convert("RGB")
    th.thumbnail((260, 200))
    tb = io.BytesIO()
    th.save(tb, "JPEG", quality=70)
    return png, "data:image/jpeg;base64," + base64.b64encode(tb.getvalue()).decode(), im.size


def _add(entry: dict):
    with _lock:
        if H and H[0]["kind"] == entry["kind"] and H[0].get("text") == entry.get("text") and entry["kind"] != "image":
            return
        entry["id"] = next(_ids)
        entry["ts"] = time.time()
        H.insert(0, entry)
        free = [e for e in H if not e.get("pin")]
        while len(free) > MAX:
            H.remove(free.pop())
        imgs = [e for e in H if e["kind"] == "image" and not e.get("pin")]
        while len(imgs) > MAX_IMG:
            H.remove(imgs.pop())
    if ON_CHANGE:
        try:
            ON_CHANGE()
        except Exception:
            pass


def _loop():
    u = _user32()
    S["last"] = u.GetClipboardSequenceNumber()
    while S["run"]:
        time.sleep(0.7)
        try:
            seq = u.GetClipboardSequenceNumber()
            if seq == S["last"]:
                continue
            S["last"] = seq
            if seq == S["self_seq"]:
                continue
            r = _read_clip()
            if not r:
                continue
            kind, val = r
            if kind == "text":
                t = str(val)[:MAX_TEXT]
                if not t.strip():
                    continue
                link = bool(re.fullmatch(r"https?://\S+", t.strip()))
                _add({"kind": "link" if link else "text", "text": t, "secret": (not link) and _sensitive(t)})
            elif kind == "files":
                _add({"kind": "files", "text": "\n".join(val)[:MAX_TEXT], "secret": False})
            elif kind == "image":
                g = _grab_image()
                if g:
                    _add({"kind": "image", "text": f"Görsel {g[2][0]}×{g[2][1]}", "png": g[0], "thumb": g[1], "secret": False})
        except Exception as e:
            print("pano izleme hatası:", type(e).__name__, flush=True)


def start():
    import settings
    if settings.get("pano_izle") is False or S["run"]:
        return
    S["run"] = True
    threading.Thread(target=_loop, daemon=True).start()


def stop():
    S["run"] = False


def enabled() -> bool:
    return bool(S["run"])


def set_enabled(on: bool):
    import settings
    settings.set("pano_izle", bool(on))
    start() if on else stop()


def view(q: str = "") -> list:
    q = (q or "").lower().strip()
    out = []
    with _lock:
        items = list(H)
    for e in items:
        if q and (e["secret"] or q not in e.get("text", "").lower()):
            continue
        t = e.get("text", "")
        out.append({"id": e["id"], "kind": e["kind"], "text": "•" * 8 if e["secret"] else t[:300], "n": len(t), "secret": e["secret"], "pin": bool(e.get("pin")),
                    "ts": time.strftime("%H:%M", time.localtime(e["ts"])), "thumb": e.get("thumb")})
    return out


def get(i: int):
    with _lock:
        return next((e for e in H if e["id"] == i), None)


def nth(n: int):
    """Listede n. kayıt (1 = en yeni)."""
    with _lock:
        return H[n - 1] if 1 <= n <= len(H) else None


def delete(i: int) -> bool:
    with _lock:
        e = next((e for e in H if e["id"] == i), None)
        ok = e is not None
        if ok:
            H.remove(e)
            e.clear()
    return ok


def pin(i: int) -> bool:
    with _lock:
        e = next((e for e in H if e["id"] == i), None)
        if e:
            e["pin"] = not e.get("pin")
    return bool(e)


def clear(keep_pins: bool = True) -> int:
    with _lock:
        n = len(H)
        keep = [e for e in H if e.get("pin")] if keep_pins else []
        for e in H:
            if e not in keep:
                e.clear()
        H[:] = keep
    return n - len(keep)


def set_clip(text: str = None, png: bytes = None) -> bool:
    """Panoyu kurar (geri koyma); bu değişiklik geçmişe yeni kayıt olarak eklenmez."""
    import win32clipboard as w
    import win32con
    for _ in range(8):
        try:
            w.OpenClipboard()
            break
        except Exception:
            time.sleep(0.05)
    else:
        return False
    try:
        w.EmptyClipboard()
        if png:
            from PIL import Image
            b = io.BytesIO()
            Image.open(io.BytesIO(png)).convert("RGB").save(b, "BMP")
            w.SetClipboardData(win32con.CF_DIB, b.getvalue()[14:])
        else:
            w.SetClipboardData(win32con.CF_UNICODETEXT, text or "")
    except Exception:
        return False
    finally:
        w.CloseClipboard()
    S["self_seq"] = _user32().GetClipboardSequenceNumber()
    S["last"] = S["self_seq"]
    return True


def restore(i: int) -> bool:
    e = get(i)
    if not e:
        return False
    return set_clip(png=e["png"]) if e["kind"] == "image" else set_clip(text=e.get("text", ""))
