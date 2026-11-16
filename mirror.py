"""Telefona ekran yansıtma (yalnızca USB tüneli üzerinden; bkz. phone.py). Bilgisayarın birincil ekranını JPEG kareleri olarak telefondaki /mirror sayfasına yollar.
Güvenlik: yayın ucu (/mws) da /ws gibi yalnızca 127.0.0.1'i dinler, her açılışta değişen gizli anahtarı ve doğru Origin'i ister; telefon `adb reverse` tüneliyle
bağlanır, ağa hiçbir port açılmaz. Yayın yalnızca bir telefon bağlıyken yapılır; bağlanınca ve kopunca bildirim gider, `kick()` bütün yayınları keser.
Gecikme: aynı anda en çok 1 kare yoldadır; telefon 'aldım' (ack) deyince o an yeni kare yakalanır (kuyruk birikmez); değişmeyen kare gönderilmez; telefona gidiş-dönüş süresi
uzarsa kalite ve boyut kendiliğinden düşer. Fare imleci karede yoktur, ayrıca yollanır (telefon üstüne çizer). Tıklama/tuş telefondan bilgisayara GİTMEZ: yalnızca izleme."""
import asyncio
import ctypes
import io
import json
import os
import secrets
import struct
import time
import zlib

from PIL import Image, ImageGrab

MODES = {"hizli": (45, 1280), "dengeli": (62, 1600), "net": (78, 4096)}      # (en yüksek JPEG kalitesi, en geniş kare genişliği)
MAX_CLIENTS = 2
MIN_INTERVAL = 0.025            # en çok ~40 kare/sn
IDLE_KEEPALIVE = 1.0            # ekran hiç değişmese de en geç bu kadar sürede bir kare
state = {"n": 0, "gen": 0, "lan_gen": 0, "on_change": None}
KEY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phone_key.txt")
_key = {"v": ""}


def key() -> str:
    """Telefon anahtarı: Jarvis'in her açılışta değişen anahtarına EK olarak kabul edilen, dosyada duran sabit anahtar (telefondaki adresi yer imi yapabilmeniz için).
    Yalnızca USB tüneliyle ulaşılabilen adreste ve doğru Origin ile işe yarar. rotate_key() onu yeniler; eski adres hemen geçersiz olur."""
    if not _key["v"]:
        try:
            with open(KEY_PATH, encoding="utf-8") as f:
                _key["v"] = f.read().strip()
        except OSError:
            pass
        if len(_key["v"]) < 24:
            return rotate_key()
    return _key["v"]


def rotate_key() -> str:
    _key["v"] = secrets.token_urlsafe(24)
    try:
        with open(KEY_PATH, "w", encoding="utf-8") as f:
            f.write(_key["v"])
    except OSError:
        pass
    return _key["v"]


def key_ok(candidate, launch_token: str) -> bool:
    """Gelen anahtar ya bu açılışın anahtarıdır ya da sabit telefon anahtarı (sabit zamanlı karşılaştırma)."""
    c = str(candidate or "").encode("utf-8", "ignore")
    return secrets.compare_digest(c, launch_token.encode()) or secrets.compare_digest(c, key().encode())


def kick() -> int:
    """Bütün açık yayınları keser (sesli 'yansıtmayı kapat'). Kesilen yayın sayısını döner."""
    n = state["n"]
    state["gen"] += 1
    return n


def kick_lan() -> None:
    """Yalnızca kablosuz (Wi-Fi) bağlı telefonların yayınını keser; USB'dekilere dokunmaz."""
    state["lan_gen"] += 1


def _cursor():
    class P(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    p = P()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


_gdi = {}


def _gdi_setup():
    """GDI işlevlerinin 64-bit tutamaç türlerini bir kez tanıtır (tanıtılmazsa tutamaçlar 32-bit'e kırpılıp taşar)."""
    if _gdi:
        return
    from ctypes import wintypes
    u, g = ctypes.windll.user32, ctypes.windll.gdi32
    u.GetDC.restype, u.GetDC.argtypes = wintypes.HDC, [wintypes.HWND]
    u.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    g.CreateCompatibleDC.restype, g.CreateCompatibleDC.argtypes = wintypes.HDC, [wintypes.HDC]
    g.CreateDIBSection.restype = wintypes.HBITMAP
    g.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD]
    g.SelectObject.restype, g.SelectObject.argtypes = wintypes.HGDIOBJ, [wintypes.HDC, wintypes.HGDIOBJ]
    g.SetStretchBltMode.argtypes = [wintypes.HDC, ctypes.c_int]
    g.SetBrushOrgEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
    g.StretchBlt.argtypes = [wintypes.HDC] + [ctypes.c_int] * 4 + [wintypes.HDC] + [ctypes.c_int] * 4 + [wintypes.DWORD]
    g.DeleteObject.argtypes, g.DeleteDC.argtypes = [wintypes.HGDIOBJ], [wintypes.HDC]

    class BMIH(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD), ("x", wintypes.LONG), ("y", wintypes.LONG), ("c1", wintypes.DWORD), ("c2", wintypes.DWORD)]
    _gdi["BMIH"] = BMIH


def _stretch(dw: int, dh: int, smooth: bool):
    """Birincil ekranı GDI ile doğrudan dw x dh olarak kopyalar (tam boyutlu kare yakalayıp sonra küçültmekten ~2 kat hızlı). (ham BGRX baytlar, genişlik, yükseklik)."""
    _gdi_setup()
    u, g = ctypes.windll.user32, ctypes.windll.gdi32
    sw, sh = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    hdc = u.GetDC(None)
    mdc = g.CreateCompatibleDC(hdc)
    hbm = None
    try:
        bmi = _gdi["BMIH"](ctypes.sizeof(_gdi["BMIH"]), dw, -dh, 1, 32, 0, 0, 0, 0, 0, 0)
        bits = ctypes.c_void_p()
        hbm = g.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        if not hbm or not bits.value:
            raise OSError("ekran kopyası oluşturulamadı")
        old = g.SelectObject(mdc, hbm)
        g.SetStretchBltMode(mdc, 4 if smooth else 3)                    # 4 = HALFTONE (yumuşak), 3 = COLORONCOLOR (hızlı)
        if smooth:
            g.SetBrushOrgEx(mdc, 0, 0, None)
        if not g.StretchBlt(mdc, 0, 0, dw, dh, hdc, 0, 0, sw, sh, 0x00CC0020 | 0x40000000):     # SRCCOPY | CAPTUREBLT (yarı saydam pencereler de gelir)
            raise OSError("ekran kopyalanamadı")
        raw = ctypes.string_at(bits, dw * dh * 4)
        g.SelectObject(mdc, old)
        return raw, dw, dh
    finally:
        if hbm:
            g.DeleteObject(hbm)
        g.DeleteDC(mdc)
        u.ReleaseDC(None, hdc)


def grab_encode(width: int, quality: int, prev_sig):
    """(jpeg | None, imza, imleç_x, imleç_y): birincil ekranı yakalar, genişliği 'width'e indirir, JPEG'e çevirir. Önceki kareyle aynıysa jpeg None döner."""
    u = ctypes.windll.user32
    sw, sh = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    if width >= sw:
        img = ImageGrab.grab()
        sig = zlib.adler32(img.tobytes())
    else:
        dw = max(320, int(width))
        raw, dw, dh = _stretch(dw, max(1, round(sh * dw / sw)), smooth=dw <= 800)
        sig = zlib.adler32(raw)
        img = None
    cx, cy = _cursor()
    cx, cy = max(0.0, min(1.0, cx / max(1, sw))), max(0.0, min(1.0, cy / max(1, sh)))
    if sig == prev_sig:
        return None, sig, cx, cy
    if img is None:
        img = Image.frombuffer("RGB", (dw, dh), raw, "raw", "BGRX", 0, 1)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, subsampling=2)
    return buf.getvalue(), sig, cx, cy


async def serve(sock, lan: bool = False) -> None:
    """Kabul edilmiş WebSocket'e yayın yapar. İstemci mesajları: {"a": kare_no} (alındı), {"mode": "hizli|dengeli|net"}, {"p": 1|0} (duraklat/sürdür)."""
    if state["n"] >= MAX_CLIENTS:
        await sock.close(code=1013)
        return
    loop = asyncio.get_running_loop()
    gen, lgen = state["gen"], state["lan_gen"]
    state["n"] += 1
    if state["on_change"]:
        state["on_change"](state["n"])
    q_max, w_max = MODES["hizli"]
    q, w = q_max - 8, w_max - 160
    acked = asyncio.Event()
    acked.set()
    sent_at = {}
    flags = {"pause": False, "rtt": 0.0}

    async def reader():
        nonlocal q_max, w_max, q, w
        try:
            await _read()
        finally:
            acked.set()                                      # ana döngü beklemede takılı kalmasın: bağlantı kopunca hemen uyanıp çıksın

    async def _read():
        nonlocal q_max, w_max, q, w
        while True:
            d = json.loads(await sock.receive_text())
            if "a" in d:
                t0 = sent_at.pop(d["a"], None)
                if t0 is not None:
                    flags["rtt"] = time.time() - t0
                    # gidiş-dönüş uzadıysa küçült, rahatsa yavaşça büyüt
                    if flags["rtt"] > 0.14:
                        q, w = max(30, q - 6), max(640, w - 120)
                    elif flags["rtt"] < 0.06:
                        q, w = min(q_max, q + 2), min(w_max, w + 40)
                acked.set()
            elif d.get("mode") in MODES:
                q_max, w_max = MODES[d["mode"]]
                q, w = min(q, q_max), min(w, w_max)
            elif "p" in d:
                flags["pause"] = bool(d["p"])
                acked.set()

    rd = asyncio.create_task(reader())
    rd.add_done_callback(lambda t: t.cancelled() or t.exception())      # bağlantı kopunca reader hatası günlüğü kirletmesin
    sig, last_send, fid, last_cur = None, 0.0, 0, (-1.0, -1.0)
    try:
        while not rd.done() and state["gen"] == gen and (not lan or state["lan_gen"] == lgen):
            if flags["pause"]:
                await asyncio.sleep(0.2)
                continue
            try:
                await asyncio.wait_for(acked.wait(), 0.25)       # telefon hazır olmadan yeni kare yakalanmaz: gecikme birikmez
            except asyncio.TimeoutError:
                continue
            t0 = time.time()
            try:
                jpeg, sig_new, cx, cy = await loop.run_in_executor(None, grab_encode, w, q, sig)
            except OSError as e:                                  # ekran kilitli/kapalı ya da yakalama reddedildi: bağlantıyı koparıp yeniden bağlanma döngüsüne girme
                if time.time() - flags.get("err_t", 0) > 20:
                    flags["err_t"] = time.time()
                    print("YANSITMA: ekran yakalanamadı:", e, flush=True)
                    await sock.send_text(json.dumps({"e": "Bilgisayar ekranı şu an yakalanamıyor (kilitli ya da kapalı olabilir)."}))
                await asyncio.sleep(1.0)
                continue
            if jpeg is None and time.time() - last_send < IDLE_KEEPALIVE:
                if abs(cx - last_cur[0]) + abs(cy - last_cur[1]) > 0.002:      # ekran aynı ama imleç oynadı: yalnızca imleç
                    last_cur = (cx, cy)
                    await sock.send_text(json.dumps({"c": [round(cx, 4), round(cy, 4)]}))
                await asyncio.sleep(max(0.0, MIN_INTERVAL - (time.time() - t0)))
                continue
            if jpeg is None:                                                     # canlı tutma karesi: aynı görüntüyü yeniden yakalayıp yollamak yerine imleç bilgisi
                last_send = time.time()
                last_cur = (cx, cy)
                await sock.send_text(json.dumps({"c": [round(cx, 4), round(cy, 4)], "k": 1}))
                continue
            sig, fid = sig_new, (fid + 1) & 0xFFFFFFFF
            last_cur = (cx, cy)
            acked.clear()
            sent_at[fid] = time.time()
            if len(sent_at) > 8:
                sent_at.pop(next(iter(sent_at)))
            await sock.send_bytes(struct.pack("<IHH", fid, int(cx * 65535), int(cy * 65535)) + jpeg)
            last_send = time.time()
            await asyncio.sleep(max(0.0, MIN_INTERVAL - (time.time() - t0)))
    finally:
        rd.cancel()
        state["n"] = max(0, state["n"] - 1)
        if state["on_change"]:
            state["on_change"](state["n"])
        try:
            await sock.close()
        except Exception:
            pass
