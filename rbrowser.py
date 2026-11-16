"""Telefon için AYRI tarayıcı: bilgisayarda görünmeyen (headless) bir Edge, her açılışta boş ve geçici bir profille çalışır; telefon yalnızca görüntüsünü alır, dokunuş/yazı gönderir.
Jarvis tarayıcısının (jbrowser) penceresine, oturumlarına ve çerezlerine DOKUNMAZ; bilgisayardaki hiçbir şey görünmez. VPN açıksa jbrowser ile aynı yerel proxy kullanılır.
Güvenlik:
- Yalnızca http/https; yerel/özel/bağlantı-yerel adresler (127.x, 10.x, 192.168.x, localhost, *.local...) hem gezinmede hem her alt istekte (yönlendirme, resim, betik) engellenir:
  telefon bu yolla Jarvis arayüzüne, ev ağındaki cihazlara ya da dosyalara (file://) ulaşamaz.
- Profil geçici klasördedir; kapanınca silinir (çerez, geçmiş, indirilenler kalmaz). Eklenti/senkron/izin istemi kapalı.
- Tek örnek; 10 dakika işlem yapılmazsa ya da uzaktan erişim kapanınca süreç sonlandırılır."""
import base64
import ipaddress
import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.request
from urllib.parse import urlsplit

from websockets.sync.client import connect

EDGES = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
W, H, DSF = 412, 760, 1.25
UA = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
IDLE_S = 600
S = {"proc": None, "ws": None, "tmp": "", "proxy": False, "last": 0.0, "shared": False, "vw": W, "vh": H}
_lock = threading.RLock()
_wlock = threading.Lock()
_next = {"id": 0}
_wait = {}
_hostcache = {}


def _private_ip(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return True
    if getattr(a, "ipv4_mapped", None):
        a = a.ipv4_mapped
    return not a.is_global


def blocked(url: str) -> bool:
    """True = bu adres tarayıcıya verilmez (yerel/özel ağ ya da http/https dışı)."""
    try:
        u = urlsplit(url)
    except ValueError:
        return True
    if u.scheme in ("data", "blob", "about", "chrome-extension"):
        return u.scheme == "about" and url != "about:blank"          # sayfanın kendi data/blob içerikleri serbest
    if u.scheme not in ("http", "https", "ws", "wss") or not u.hostname:
        return True
    host = u.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".lan", ".home", ".corp")):
        return True
    try:
        ipaddress.ip_address(host.strip("[]"))
        return _private_ip(host.strip("[]"))
    except ValueError:
        pass
    if S["proxy"]:                                            # adlar proxy tarafında çözülür; yerel ağa oradan yol yok
        return False
    hit = _hostcache.get(host)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    try:
        bad = any(_private_ip(i[4][0]) for i in socket.getaddrinfo(host, None))
    except OSError:
        bad = False
    if len(_hostcache) > 500:
        _hostcache.clear()
    _hostcache[host] = (time.time(), bad)
    return bad


def _send(msg: dict) -> None:
    with _wlock:
        S["ws"].send(json.dumps(msg))


def _call(method: str, params=None, timeout: float = 15.0):
    with _lock:
        _next["id"] += 1
        i = _next["id"]
    ev = threading.Event()
    _wait[i] = [ev, None]
    _send({"id": i, "method": method, "params": params or {}})
    if not ev.wait(timeout):
        _wait.pop(i, None)
        raise TimeoutError(method)
    res = _wait.pop(i)[1]
    if "error" in res:
        raise RuntimeError(res["error"].get("message", "cdp"))
    return res.get("result", {})


def _reader(ws) -> None:
    try:
        for raw in ws:
            m = json.loads(raw)
            if "id" in m:
                w = _wait.get(m["id"])
                if w:
                    w[1] = m
                    w[0].set()
            elif m.get("method") == "Fetch.requestPaused":
                p = m["params"]
                try:
                    if blocked(p["request"]["url"]):
                        _send({"id": 0, "method": "Fetch.failRequest", "params": {"requestId": p["requestId"], "errorReason": "BlockedByClient"}})
                    else:
                        _send({"id": 0, "method": "Fetch.continueRequest", "params": {"requestId": p["requestId"]}})
                except Exception:
                    pass
    except Exception:
        pass
    if S["ws"] is ws:
        S["ws"] = None
    for w in list(_wait.values()):
        w[1] = {"error": {"message": "kapandı"}}
        w[0].set()


def alive() -> bool:
    p = S["proc"]
    return bool(S["ws"] and (p is None or p.poll() is None))


def start(proxy: str = "") -> str:
    """Tarayıcıyı başlatır ('ok' ya da hata). proxy: '127.0.0.1:port' (socks5)."""
    with _lock:
        if alive():
            S["last"] = time.time()
            return "ok"
        stop()
        exe = next((e for e in EDGES if os.path.exists(e)), "")
        if not exe:
            return "Microsoft Edge bulunamadı efendim."
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        tmp = tempfile.mkdtemp(prefix="jarvis_rb_")
        args = [exe, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={tmp}", "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                "--disable-sync", "--disable-background-networking", "--deny-permission-prompts", "--mute-audio", "--hide-scrollbars", "--disable-features=Translate",
                f"--window-size={W},{H}", "about:blank"]
        if proxy:
            args += [f"--proxy-server=socks5://{proxy}", "--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1"]
        S.update(proc=subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000), tmp=tmp, proxy=bool(proxy))
        ws_url = ""
        for _ in range(75):
            try:
                tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2).read())
                ws_url = next((t["webSocketDebuggerUrl"] for t in tabs if t.get("type") == "page"), "")
                if ws_url:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if not ws_url:
            stop()
            return "Tarayıcı başlatılamadı efendim."
        S["ws"] = connect(ws_url, max_size=30_000_000, open_timeout=10)
        threading.Thread(target=_reader, args=(S["ws"],), daemon=True).start()
        try:
            _call("Page.enable")
            _call("Fetch.enable", {"patterns": [{"urlPattern": "*"}]})
            _call("Emulation.setDeviceMetricsOverride", {"width": W, "height": H, "deviceScaleFactor": DSF, "mobile": True})
            _call("Emulation.setUserAgentOverride", {"userAgent": UA})
        except Exception as e:
            stop()
            return f"Tarayıcı hazırlanamadı ({type(e).__name__})."
        S["last"] = time.time()
        return "ok"


def attach(port: int) -> str:
    """Jarvis tarayıcısının (jbrowser, WebView2) yalnızca 127.0.0.1'deki hata ayıklama portuna bağlanır; yeni tarayıcı AÇMAZ, profile dokunmaz."""
    with _lock:
        stop()
        ws_url = ""
        for _ in range(100):
            try:
                tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{int(port)}/json/list", timeout=2).read())
                ws_url = next((t["webSocketDebuggerUrl"] for t in tabs if t.get("type") == "page"), "")
                if ws_url:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if not ws_url:
            return "Jarvis tarayıcısına bağlanılamadı efendim."
        S.update(shared=True, proxy=False)
        S["ws"] = connect(ws_url, max_size=30_000_000, open_timeout=10)
        threading.Thread(target=_reader, args=(S["ws"],), daemon=True).start()
        try:
            _call("Page.enable")
        except Exception as e:
            stop()
            return f"Bağlantı hazırlanamadı ({type(e).__name__})."
        S["last"] = time.time()
        return "ok"


def viewport(w: float, h: float) -> None:
    """Telefonun ekran boyutu: paylaşılan tarayıcıda sayfa bu boyutta çizilir (telefon tam ekranı doldurur). Pencere boyutu değişmez, yalnızca çizim alanı; ayrılınca eski hâline döner."""
    if not S["shared"]:
        return
    w, h = max(280, min(1600, int(w))), max(300, min(2400, int(h)))
    _touch()
    _call("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": False})
    S["vw"], S["vh"] = float(w), float(h)


def _vp() -> tuple:
    """Sayfanın görünür alanı (CSS pikseli); paylaşılan tarayıcıda pencere boyutu değişebilir."""
    if not S["shared"]:
        return W, H
    try:
        m = _call("Page.getLayoutMetrics", timeout=5)
        v = m.get("cssVisualViewport") or m.get("visualViewport") or {}
        w, h = float(v.get("clientWidth") or 0), float(v.get("clientHeight") or 0)
        if w > 50 and h > 50:
            S["vw"], S["vh"] = w, h
    except Exception:
        pass
    return S["vw"], S["vh"]


def stop() -> None:
    if S["shared"] and S["ws"]:
        try:
            _call("Emulation.clearDeviceMetricsOverride", timeout=3)           # paylaşılan tarayıcı eski çizim boyutuna döner
        except Exception:
            pass
    with _lock:
        p, ws, tmp = S["proc"], S["ws"], S["tmp"]
        S.update(proc=None, ws=None, tmp="", shared=False, vw=W, vh=H)
    try:
        if ws:
            ws.close()
    except Exception:
        pass
    if p is not None:
        try:
            p.terminate()
            p.wait(5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)


def idle_check() -> None:
    if alive() and time.time() - S["last"] > IDLE_S:
        stop()


def _touch():
    S["last"] = time.time()


def navigate(text: str) -> str:
    """Adres ya da arama sözcüğü; engelliyse açıklama döner, tamamsa 'ok'."""
    t = text.strip()[:2000]
    if not t:
        return "Adres boş."
    if "://" not in t:
        t = ("https://" + t) if ("." in t and " " not in t) else "https://www.google.com/search?q=" + urllib.request.quote(t)
    if blocked(t):
        return "Bu adres güvenlik nedeniyle engellendi (yerel ağ ya da desteklenmeyen tür)."
    _touch()
    _call("Page.navigate", {"url": t})
    return "ok"


def frame(quality: int = 55) -> bytes:
    _touch()
    vw, vh = _vp()
    prm = {"format": "jpeg", "quality": quality}
    if S["shared"]:
        prm["clip"] = {"x": 0, "y": 0, "width": vw, "height": vh, "scale": max(0.5, min(2.0, 900.0 / vw))}
    r = _call("Page.captureScreenshot", prm, 20)
    return base64.b64decode(r["data"])


def info() -> dict:
    try:
        r = _call("Runtime.evaluate", {"expression": "JSON.stringify([location.href, document.title])", "returnByValue": True}, 5)
        u, t = json.loads(r["result"]["value"])
    except Exception:
        u, t = "", ""
    vw, vh = _vp()
    return {"url": u[:300], "title": t[:120], "vw": vw, "vh": vh}


_EDIT_JS = """(()=>{let a=document.activeElement;while(a&&a.shadowRoot&&a.shadowRoot.activeElement)a=a.shadowRoot.activeElement;
if(!a)return false;const t=(a.tagName||'').toUpperCase();
return !!(a.isContentEditable||t==='TEXTAREA'||(t==='INPUT'&&!/^(button|checkbox|radio|submit|range|color|file|image|reset|hidden)$/i.test(a.type||'text')))})()"""


def tap(nx: float, ny: float) -> bool:
    """Dokunur; ardından odaktaki öğe yazılabilir bir kutuysa True döner (telefon klavyeyi açar)."""
    _touch()
    vw, vh = _vp()
    x, y = max(0.0, min(1.0, float(nx))) * vw, max(0.0, min(1.0, float(ny))) * vh
    for typ in ("mouseMoved", "mousePressed", "mouseReleased"):
        _call("Input.dispatchMouseEvent", {"type": typ, "x": x, "y": y, "button": "left", "clickCount": 1})
    try:
        r = _call("Runtime.evaluate", {"expression": _EDIT_JS, "returnByValue": True}, timeout=3)
        return bool(((r or {}).get("result") or {}).get("value"))
    except Exception:
        return False


def scroll(dy: float, dx: float = 0.0) -> None:
    _touch()
    vw, vh = _vp()
    _call("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": vw / 2, "y": vh / 2, "deltaX": max(-3000.0, min(3000.0, float(dx))), "deltaY": max(-3000.0, min(3000.0, float(dy)))})


def text(s: str) -> None:
    _touch()
    _call("Input.insertText", {"text": str(s)[:500]})


_KEYS = {"Enter": (13, "\r"), "Backspace": (8, ""), "Tab": (9, ""), "Escape": (27, ""), "ArrowDown": (40, ""), "ArrowUp": (38, "")}


def key(name: str) -> None:
    if name not in _KEYS:
        return
    _touch()
    vk, txt = _KEYS[name]
    base = {"key": name, "code": name, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk}
    _call("Input.dispatchKeyEvent", {"type": "keyDown", **base, **({"text": txt} if txt else {})})
    _call("Input.dispatchKeyEvent", {"type": "keyUp", **base})


def history(step: int) -> None:
    _touch()
    h = _call("Page.getNavigationHistory")
    i = h["currentIndex"] + step
    if 0 <= i < len(h["entries"]):
        _call("Page.navigateToHistoryEntry", {"entryId": h["entries"][i]["id"]})


def reload() -> None:
    _touch()
    _call("Page.reload")
