"""WhatsApp MASAÜSTÜ uygulaması için okuma (Windows bildirimleri) ve mesaj gönderme (onaylı).

Okuma: WhatsApp penceresindeki "Okunmamış" filtresine basılıp liste Windows'un yerleşik OCR'ı (Türkçe) ile okunur.
       Hiçbir sohbet açılmaz, bu yüzden mesajlar "okundu" olmaz; yalnızca her sohbetin son mesaj önizlemesi okunur.
       OCR başarısız olursa Windows bildirimlerinden yakalananlar yedek olarak kullanılır.
Gönderme: Kişi, uygulamadaki aramayla ada göre bulunur. Mesaj ASLA onaysız gönderilmez.
"""
import asyncio, ctypes, io, os, re, shutil, sqlite3, subprocess, tempfile, threading, time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.expandvars(r"%LocalAppData%\Microsoft\Windows\Notifications")

_msgs: list[dict] = []
_seen: set[int] = set()
_lock = threading.Lock()
_draft: dict | None = None


def _poll_once():
    tmp = tempfile.mkdtemp()
    try:
        for f in ("wpndatabase.db", "wpndatabase.db-wal", "wpndatabase.db-shm"):
            src = os.path.join(DB_DIR, f)
            if os.path.exists(src):
                shutil.copy(src, tmp)
        con = sqlite3.connect(os.path.join(tmp, "wpndatabase.db"))
        rows = con.execute(
            "select n.Id, n.Payload, n.ArrivalTime from Notification n join NotificationHandler h "
            "on n.HandlerId=h.RecordId where h.PrimaryId like '%WhatsApp%' and n.Type='toast'").fetchall()
        con.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for nid, payload, arrival in rows:
        if nid in _seen:
            continue
        _seen.add(nid)
        try:
            raw = payload.decode("utf-8", "ignore") if isinstance(payload, bytes) else str(payload)
            texts = [t.text or "" for t in ET.fromstring(raw[raw.index("<"):]).iter("text")]
        except Exception:
            continue
        if texts:
            with _lock:
                _msgs.append({"id": nid, "from": texts[0], "text": " ".join(texts[1:]), "read": False})


def start_watcher():
    def run():
        while True:
            try:
                _poll_once()
            except Exception:
                pass
            time.sleep(3)
    threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------- pencereyi OCR ile okuma
_TIME_RE = re.compile(r"^(\d{1,2}[:.]\d{2}|dün|bugün|pzt|sal|çar|per|cum|cmt|paz|pazartesi|salı|çarşamba|perşembe|cuma|cumartesi|pazar|"
                      r"\d{1,2}[./]\d{1,2}[./]\d{2,4})$", re.I)
_EMPTY_RE = re.compile(r"okunmamış|bulunamadı|sohbet yok|sohbetiniz yok", re.I)


async def _ocr_async(img):
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
    from winsdk.windows.globalization import Language
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    st = InMemoryRandomAccessStream()
    dw = DataWriter(st)
    dw.write_bytes(buf.getvalue())
    await dw.store_async()
    await dw.flush_async()
    st.seek(0)
    bmp = await (await BitmapDecoder.create_async(st)).get_software_bitmap_async()
    eng = OcrEngine.try_create_from_language(Language("tr")) or OcrEngine.try_create_from_user_profile_languages()
    return await eng.recognize_async(bmp)


def _ocr_lines(img) -> list:
    """[(x, y, genişlik, yükseklik, metin)] satır satır."""
    res = asyncio.run(_ocr_async(img))
    out = []
    for line in res.lines:
        ws = list(line.words)
        if not ws:
            continue
        r0, r1 = ws[0].bounding_rect, ws[-1].bounding_rect
        out.append((r0.x, r0.y, r1.x + r1.width - r0.x, max(x.bounding_rect.height for x in ws), line.text.strip()))
    return out


def _wa_window(open_if_needed=True):
    from pywinauto import Desktop
    for attempt in range(2):
        for win in Desktop(backend="uia").windows(class_name="WinUIDesktopWin32WindowClass"):
            if win.window_text() == "WhatsApp":
                return win
        if not open_if_needed or attempt:
            break
        subprocess.Popen(["explorer.exe", "whatsapp:"])
        for _ in range(30):
            time.sleep(1)
            for win in Desktop(backend="uia").windows(class_name="WinUIDesktopWin32WindowClass"):
                if win.window_text() == "WhatsApp":
                    time.sleep(3)
                    return win
    return None


class _Rect:
    def __init__(self, r):
        self.left, self.top, self.right, self.bottom = r.left, r.top, r.right, r.bottom

    def width(self):
        return self.right - self.left

    def height(self):
        return self.bottom - self.top


def _shot(win):
    """Pencerenin ekran görüntüsü. Konum doğrudan Windows'tan okunur (pywinauto küçültülmüş pencerede eski değeri tutuyor)."""
    import pyautogui
    from ctypes import wintypes
    rr = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(win.handle, ctypes.byref(rr))
    r = _Rect(rr)
    if r.width() < 100 or r.height() < 100 or r.left < -3000:
        raise RuntimeError("WhatsApp penceresi görüntülenemedi")
    return pyautogui.screenshot(region=(r.left, r.top, r.width(), r.height())), r


def _chips(lines):
    names = {"tümü": None, "okunmamış": None, "favoriler": None, "gruplar": None}
    for x, y, w, h, t in lines:
        k = t.lower()
        if k in names and names[k] is None:
            names[k] = (x, y, w, h)
    return names


def _active_chip(img, chips):
    """Seçili filtre düğmesinin arka planı diğerlerinden farklıdır (açık yeşil); onu bul."""
    import numpy as np
    cols = {}
    for k, v in chips.items():
        if v:
            x, y, w, h = v
            px = img.getpixel((max(0, int(x) - 8), int(y + h / 2)))[:3]
            cols[k] = np.array(px, dtype=float)
    if len(cols) < 3:
        return None
    for k, c in cols.items():
        others = [o for kk, o in cols.items() if kk != k]
        spread = max(float(np.linalg.norm(a - b)) for a in others for b in others)
        if spread < 25 and float(np.linalg.norm(c - np.mean(others, axis=0))) > 25:
            return k
    return None


def _chip_selected(img, chip) -> bool:
    """Filtre düğmesi seçiliyse arka planı yeşilimsidir (açık temada açık yeşil, koyu temada koyu yeşil)."""
    x, y, ww, h = chip
    hits = 0
    for dx, dy in ((-8, h / 2), (ww / 2, -6), (ww + 8, h / 2)):
        px = img.getpixel((min(img.width - 1, max(0, int(x + dx))), min(img.height - 1, max(0, int(y + dy)))))[:3]
        if px[1] > px[0] + 15 and px[1] > px[2] + 10:
            hits += 1
    return hits >= 2


def _parse_chat_rows(lines, img_w, top_y):
    """Sohbet listesi satırlarını (ad, sayı, önizleme) gruplarına ayır."""
    limit = img_w * 0.38
    col = sorted([l for l in lines if l[0] < limit and l[1] > top_y + 20], key=lambda l: l[1])
    groups, cur = [], []
    for l in col:
        if cur and l[1] - cur[-1][1] > 34:
            groups.append(cur)
            cur = []
        cur.append(l)
    if cur:
        groups.append(cur)
    chats = []
    for g in groups:
        count, texts = 0, []
        for x, y, w, h, t in g:
            if _TIME_RE.match(t):
                continue
            if t.isdigit() and x > img_w * 0.2:                 # sağdaki yeşil rozet: okunmamış sayısı
                count = int(t)
                continue
            texts.append(t)
        if not texts:
            continue
        name, preview = texts[0], " ".join(texts[1:]).strip()
        if len(name) > 45 and not preview:                       # ad ve önizleme tek satır okunmuş
            name, preview = "Bir sohbet", name
        chats.append({"name": name[:60], "count": count or 1, "preview": preview[:200]})
    if len(chats) == 1 and _EMPTY_RE.search(chats[0]["name"] + " " + chats[0]["preview"]):
        return []
    return chats


def _restore_and_wait(win, bring_to_front):
    """Pencereyi geri getir ve gerçekten ekranda çizilene kadar bekle (simge durumundan açılış 1-4 sn sürebiliyor)."""
    from ctypes import wintypes
    u = ctypes.windll.user32
    for _ in range(50):
        u.ShowWindow(win.handle, 9)
        bring_to_front(win.handle)
        r = wintypes.RECT()
        u.GetWindowRect(win.handle, ctypes.byref(r))
        if not u.IsIconic(win.handle) and r.left > -3000 and (r.right - r.left) > 400 and (r.bottom - r.top) > 300:
            break
        time.sleep(0.2)
    time.sleep(1.2)


def read_unread_chats() -> list:
    """Okunmamış sohbetler: [{'name','count','preview'}]. Hata olursa RuntimeError."""
    import pyautogui
    pyautogui.FAILSAFE = False
    from tools import bring_to_front
    win = _wa_window()
    if win is None:
        raise RuntimeError("WhatsApp uygulaması açılamadı")
    was_min = win.is_minimized()
    _restore_and_wait(win, bring_to_front)
    clicked = False
    try:
        img, r = _shot(win)
        lines = _ocr_lines(img)
        chips = _chips(lines)
        if not chips["okunmamış"] or not chips["tümü"]:
            raise RuntimeError("WhatsApp sohbet listesini göremedim (bir sohbet ya da başka bir ekran açık olabilir)")
        if not _chip_selected(img, chips["okunmamış"]):
            x, y, w, h = chips["okunmamış"]
            pyautogui.click(r.left + x + w / 2, r.top + y + h / 2)
            clicked = True
            time.sleep(1.4)
            img, r = _shot(win)
            if not _chip_selected(img, chips["okunmamış"]):
                raise RuntimeError("Okunmamış filtresi seçilemedi")
            lines = _ocr_lines(img)
        return _parse_chat_rows(lines, img.width, chips["okunmamış"][1])
    finally:
        try:
            if clicked:
                x, y, w, h = chips["tümü"]
                pyautogui.click(r.left + x + w / 2, r.top + y + h / 2)      # filtreyi eski haline getir
                time.sleep(0.6)
            if was_min:
                ctypes.windll.user32.ShowWindow(win.handle, 6)
        except Exception:
            pass


def _fmt_chat(c) -> str:
    who = c["name"] if c["count"] <= 1 else f"{c['name']} ({c['count']} mesaj)"
    return f"{who}: {c['preview']}" if c["preview"] else f"{who}: (metin okunamadı)"


def unread_messages() -> str:
    """Okunmamış WhatsApp sohbetlerini 'ad: önizleme' satırları olarak verir; hiç yoksa bunu açıkça söyler."""
    try:
        chats = read_unread_chats()
        if not chats:
            return "Okunmamış WhatsApp sohbeti yok."
        return "\n".join(_fmt_chat(c) for c in chats[:12])
    except Exception as e:
        print("WhatsApp OCR okuma hatası:", e, flush=True)
        try:
            _poll_once()
        except Exception:
            pass
        with _lock:
            new = [m for m in _msgs if not m["read"]]
            for m in new:
                m["read"] = True
        if new:
            return "\n".join(f"{m['from']}: {m['text']}" for m in new[-15:])
        return f"HATA: {e}"


def _window():
    from pywinauto import Desktop
    for w in Desktop(backend="uia").windows():
        if w.window_text() == "WhatsApp" and "WinUI" in (w.element_info.class_name or ""):
            return w
    return None


def _focus():
    w = _window()
    if w is None:
        subprocess.Popen(["explorer.exe", "whatsapp:"])
        for _ in range(30):
            time.sleep(0.5)
            w = _window()
            if w:
                break
        else:
            raise RuntimeError("WhatsApp uygulaması açılamadı")
        time.sleep(2)
    try:
        w.restore()
    except Exception:
        pass
    w.set_focus()
    time.sleep(0.6)


def _paste(text: str):
    import pyperclip, pyautogui
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")


def prepare_message(contact: str, message: str) -> str:
    """Uygulamadaki aramayla kişiyi bulur, sohbeti açar ve mesajı yazar (göndermez)."""
    global _draft
    import pyautogui
    _focus()
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.6)
    _paste(contact)
    time.sleep(1.5)
    pyautogui.press("down")
    pyautogui.press("enter")
    time.sleep(1.0)
    _paste(message)
    _draft = {"contact": contact, "message": message, "t": time.time()}
    return f"Taslak WhatsApp'ta hazır. Alıcı: {contact} (aramadaki ilk sonuç). Mesaj: {message}"


def send_confirmed() -> str:
    global _draft
    import pyautogui
    if not _draft or time.time() - _draft["t"] > 180:
        _draft = None
        return "Onaylanmış bir taslak yok ya da süresi doldu; önce mesajı yeniden hazırlamalıyım."
    _focus()
    pyautogui.press("enter")
    who, _draft = _draft["contact"], None
    return f"Mesaj {who} kişisine gönderildi."


# ---------------------------------------------------------------- rapor gönderme (rapor modu)
def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _header_ok(img, phone: str, name: str) -> bool:
    """Sohbet başlığında (pencerenin sağ-üst bölgesi) hedef numara ya da kayıtlı ad görünüyor mu? Görünmüyorsa yanlış sohbete yazmamak için gönderilmez."""
    w, h = img.size
    band = img.crop((int(w * 0.28), 0, w, min(h, 130)))
    text = " ".join(l[4] for l in _ocr_lines(band))
    d = _digits(text)
    tail = phone[-10:]
    if tail and tail in d:
        return True
    return bool(name) and name.lower() in text.lower()


def _foreground(win) -> bool:
    return ctypes.windll.user32.GetForegroundWindow() == win.handle


def _bring(win) -> bool:
    """WhatsApp'ı öne alır; gerçekten ön plandaysa True. Değilse hiçbir tuş basımı yapılmaz (başka uygulamaya yazmamak için)."""
    for _ in range(3):
        try:
            win.restore()
        except Exception:
            pass
        try:
            win.set_focus()
        except Exception:
            pass
        time.sleep(0.8)
        if _foreground(win):
            return True
    return False


def send_report(phone: str, text: str, name: str = "") -> str:
    """Raporu, numarası verilen kişiye WhatsApp masaüstü uygulamasından gönderir (elle dokunmaya gerek yok).
    Adımlar: uygulamayı öne al -> 'Yeni sohbet' aramasına numarayı yaz -> ilk sonucu aç -> başlıkta hedefi doğrula (doğrulanamazsa HİÇBİR ŞEY yazılmaz)
    -> yapıştır -> Enter -> gönderimi doğrula. (whatsapp://send bağlantısı bu sürümde sohbeti açmıyor, o yüzden arama kullanılır.)
    Dönüş: 'sent' (gönderildi ve doğrulandı) | 'unverified' (Enter basıldı ama doğrulanamadı) | 'failed:<neden>' (hiçbir şey gönderilmedi).
    JARVIS_WA_DRYRUN=1: WhatsApp'a hiç dokunmadan 'sent' döner (test için). Pano her durumda temizlenir."""
    if os.environ.get("JARVIS_WA_DRYRUN") == "1":
        return "sent"
    import pyautogui, pyperclip
    phone = _digits(phone)
    if not 10 <= len(phone) <= 15 or not text.strip():
        return "failed:geçersiz numara ya da boş rapor"
    try:
        win = _window()
        if win is None:
            os.startfile("whatsapp:")                           # explorer.exe ile açınca Dosyalar penceresi çıkıyordu
            for _ in range(40):
                time.sleep(0.5)
                win = _window()
                if win is not None:
                    break
            if win is None:
                return "failed:WhatsApp uygulaması açılamadı"
            time.sleep(3.0)
        if not _bring(win):
            return "failed:WhatsApp öne alınamadı"
        pyautogui.press("esc")
        time.sleep(0.3)
        pyautogui.press("esc")
        time.sleep(0.4)
        pyautogui.hotkey("ctrl", "n")                           # Yeni sohbet
        time.sleep(1.3)
        pyperclip.copy("+" + phone)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(2.5)
        if not _foreground(win):
            return "failed:WhatsApp ön planda değil"
        pyautogui.press("down")
        time.sleep(0.4)
        pyautogui.press("enter")
        time.sleep(2.0)
        img, r = _shot(win)
        if not _header_ok(img, phone, name):
            return "failed:alıcı sohbetinin açıldığı doğrulanamadı"
        pyautogui.click(int(r.left + r.width() * 0.62), int(r.bottom - 46))      # mesaj kutusuna odaklan
        time.sleep(0.4)
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.9)
        img2, _ = _shot(win)
        if not _foreground(win) or not _header_ok(img2, phone, name):     # yapıştırırken sohbet değişmediğinden emin ol
            return "failed:sohbet değişti, gönderilmedi"
        pyautogui.press("enter")
        time.sleep(2.0)
        probe = " ".join(text.split())[:14]
        img3, _ = _shot(win)
        body = " ".join(l[4] for l in _ocr_lines(img3))
        ok = probe.lower() in " ".join(body.split()).lower()
        return "sent" if ok else "unverified"
    except Exception as e:
        return f"failed:{type(e).__name__}"
    finally:
        try:
            pyperclip.copy("")                                  # rapor panoda kalmasın
        except Exception:
            pass
        try:
            w = _window()
            if w is not None:
                ctypes.windll.user32.ShowWindow(w.handle, 6)    # WhatsApp'ı küçült
        except Exception:
            pass
