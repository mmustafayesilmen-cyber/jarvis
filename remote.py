"""Uzaktan (internet) telefon erişimi: YALNIZCA birkaç mod, bilgisayara erişim YOK.
Telefon; ekran yayını, serbest komut, mikrofon, ışık/ses/güç komutu, dosya ya da uygulama kontrolü alamaz. Tek yapabildiği WHITELIST'teki modların sayfalarını
açıp o modların kendi komutlarını çalıştırmaktır (NAMES sözlüğü: laboratuvarlar, uzay, ortam, satranç, harita, uyku, tarif, spor, panel vb.); mod işleyicileri bilgisayarda pencere açmadan, sesli konuşmadan, burada çalışır.
Tasarım:
- Sunucu YALNIZCA 127.0.0.1:8767'yi dinler; internete açan, bin/cloudflared.exe ile kurulan Cloudflare 'quick tunnel'dır (hesap gerekmez, link her açılışta değişir).
- Yalnızca sesle açılır ('uzaktan erişimi aç'), TTL (varsayılan 2 saat) dolunca ya da 'uzaktan erişimi kapat' denince tünel ve sunucu tamamen kapanır; kalıcı değildir.
- Kapı (Guard): istek geri döngüden (tünel) gelmeli VE Host başlığı tünel adresi olmalı; yerel tarayıcıdaki başka siteler 127.0.0.1:8767'ye ulaşsa da Host uyuşmadığı için reddedilir.
- Eşleştirme yalnızca sesle 'telefonu eşleştir' denince 3 dakikalık pencere açıkken yapılır; 8 haneli kod YALNIZCA bilgisayarda gösterilir, pencerede en çok 5 deneme.
  Cihaz anahtarının yalnızca SHA-256 özeti remote_devices.json'dadır (gitignored, en çok 3 cihaz).
- Anahtar dönüşü: telefon cihaz anahtarını yalnızca /session'a gönderir ve 90 saniyelik oturum anahtarı alır; sayfa 45 sn'de bir yeniler. Her WebSocket mesajı güncel oturum anahtarını taşır,
  süresi dolan oturum anında reddedilir. Link ya da oturum anahtarı sızsa bile en çok bir dakika işe yarar."""
import asyncio
import hashlib
import ipaddress
import json
import os
import re
import secrets
import subprocess
import threading
import time

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, FileResponse

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(HERE, "ui")
PORT = int(os.environ.get("JARVIS_REMOTE_PORT") or 8767)          # testlerde başka bir port verilebilir (çalışan Jarvis'in bağlantısına dokunmamak için)
EXE = os.path.join(HERE, "bin", "cloudflared.exe")
DEV_PATH = os.path.join(HERE, "remote_devices.json")
# Yalnızca kişisel veri taşımayan ve bilgisayarda yan etki yapmayan modlar. Hariç: notlar, evim, rapor, gelişim, kartlar, ders (MEBİ), müzik listeleri, müzik görselleştirici,
# sistem, VPN, mola/pomodoro (PC'de sesli bildirim), telefon, illüzyon/kahraman ve Jarvis tarayıcısı (PC'deki bir pencere; uzaktan sürülemez).
NAMES = {"uyku": "Uyku", "tarif": "Tarif", "spor": "Spor / Maç", "panel": "Panel", "ortam": "Ortam", "uzay": "Uzay", "gokyuzu": "Gökyüzü", "hologram": "Hologram",
         "kimya": "Kimya lab", "biyoloji": "Biyoloji lab", "fizik": "Fizik lab", "matematik": "Matematik lab", "astronomi": "Astronomi lab", "jeoloji": "Jeoloji lab",
         "satranc": "Satranç", "oyunlar": "Zihin oyunları", "kuran": "Kur'an-ı Kerim", "harita": "Dünya haritası"}
NAMES.update({"sinav": "Sınav", "notlar": "Notlar", "yuvam": "Evim", "rapor": "Rapor", "kartlar": "Ezber kartları", "gelisim": "Gelişim", "ders": "Quiz (MEBİ)",
              "pomodoro": "Pomodoro", "mola": "Mola", "sistem": "Sistem", "muzik": "Müzik görselleştirici", "listeler": "Müzik listeleri"})
WHITELIST = tuple(NAMES)
# Tailscale + tam kontrol açıkken (kullanıcının tercihi) ek olarak açılan modlar: bilgisayarın pencerelerini kapatan odak ve VPN
FULL_KINDS = ("odak", "vpn", "sohbet", "ultron", "friday", "luna")   # sohbet/kişilikler memory.json okur, Friday araç kullanır: yalnızca Tailscale + tam kontrol açıkken
NAMES_FULL = {"odak": "Derin odak", "vpn": "VPN", "sohbet": "Sohbet", "ultron": "Ultron", "friday": "Friday", "luna": "Luna"}


def kind_ok(kind, headers) -> bool:
    return kind in WHITELIST or (kind in FULL_KINDS and full_enabled(headers))
# Bilgisayarın ana sürecindeki (main.py) durumlu işlevlerle çalışan modlar: komutlar ve düğmeler main.remote_ws ile işlenir, sonuçlar main.emit -> forward ile telefona gelir.
# Hariç (bilerek): derin odak (bilgisayarın pencerelerini kapatır), VPN, telefon modu, illüzyon/kahraman ve Jarvis tarayıcısı penceresi.
HEAVY = ("odak", "vpn", "sohbet", "ultron", "friday", "luna", "notlar", "yuvam", "rapor", "kartlar", "gelisim", "ders", "pomodoro", "mola", "sistem", "muzik", "listeler", "sinav")
BIG_KINDS = ("yuvam", "notlar", "rapor", "ders")                                                       # fotoğraf/gövde taşıyabilen mesajlar (3 MB'a kadar)
MAIN = {"attach": None, "detach": None, "ws": None}
_subs = {}                                                                                              # mod -> {(WebSocket, event loop)}
_grace = {}                                                                                             # mod -> son telefon ayrıldıktan sonra döngülerin yaşayacağı son an
GRACE_S = 60
_slock = threading.Lock()


def attached(kind: str) -> bool:
    """Bu modu gösteren uzaktan telefon var mı (ya da yeni ayrıldı ve bekleme süresi dolmadı)? main'deki mod döngüleri buna bakar."""
    with _slock:
        return bool(_subs.get(kind)) or time.time() < _grace.get(kind, 0.0)


def forward(msg: dict) -> None:
    """main.emit'ten: modu gösteren uzaktaki telefonlara mod mesajı gönderir (yalnızca o modun aboneleri)."""
    with _slock:
        subs = list(_subs.get(msg.get("kind"), ()))
    if not subs:
        return
    data = json.dumps(msg)
    for sock, lp in subs:
        try:
            asyncio.run_coroutine_threadsafe(sock.send_text(data), lp)
        except Exception:
            pass


def _sub(kind: str, sock, lp) -> None:
    with _slock:
        _subs.setdefault(kind, set()).add((sock, lp))
        _grace.pop(kind, None)


def _unsub(kind: str, sock, lp) -> None:
    with _slock:
        _subs.get(kind, set()).discard((sock, lp))
        if _subs.get(kind):
            return
        _grace[kind] = time.time() + GRACE_S

    def fin():
        if not attached(kind) and MAIN["detach"]:
            try:
                MAIN["detach"](kind)
            except Exception as e:
                print("UZAKTAN ayrılma hatası:", type(e).__name__, flush=True)
    t = threading.Timer(GRACE_S + 2, fin)
    t.daemon = True
    t.start()
PAGE_OF = {"kimya": "scene_lab.html", "biyoloji": "scene_lab.html", "fizik": "scene_sci.html", "matematik": "scene_sci.html", "astronomi": "scene_sci.html", "jeoloji": "scene_sci.html"}
SCI = ("fizik", "matematik", "astronomi", "jeoloji", "gokyuzu")
VIEW_MODS = {"satranc": "satranc", "oyunlar": "oyunlar", "kuran": "kuran", "harita": "harita"}          # sonuçla birlikte güncel görünüm de gider (main._scene_view ile aynı)
NEW_PAGES = ("uyku", "tarif", "spor", "panel")                                                         # modes.js kabuğunu kullananlar
MAX_DEVICES, SESSION_TTL, PAIR_WINDOW, PAIR_TRIES, TTL_S = 3, 90, 180, 5, 2 * 3600
HOOKS = {"pair_code": None, "link": None, "closed": None}
S = {"on": False, "host": "", "server": None, "proc": None, "until": 0.0, "auto": False}
PORT_TS = int(os.environ.get("JARVIS_TS_PORT") or 8768)
TS = {"on": False, "ip": "", "server": None}               # Tailscale dinleyicisi: yalnızca bilgisayarın Tailscale adresinde (100.64.0.0/10), tünel/site gerekmez


def up() -> bool:
    """Herhangi bir uzaktan erişim yolu (Cloudflare tüneli ya da Tailscale) açık mı?"""
    return S["on"] or TS["on"]


def _ts_client(ip: str) -> bool:
    """Yalnızca Tailscale ağındaki (100.64.0.0/10) istemciler. Test için JARVIS_TS_TEST=1 ve adres 127.0.0.1 iken geri döngü de kabul edilir."""
    try:
        a = ipaddress.ip_address(str(ip).split("%")[0])
    except ValueError:
        return False
    if getattr(a, "ipv4_mapped", None):
        a = a.ipv4_mapped
    if os.environ.get("JARVIS_TS_TEST") == "1" and TS["ip"] == "127.0.0.1":
        return a.is_loopback
    return a in ipaddress.ip_network("100.64.0.0/10")
_lock = threading.RLock()
_sess = {}                                       # oturum anahtarı özeti -> bitiş zamanı
_pair = {"until": 0.0, "id": "", "code": "", "tries": 0}
_bad = {"n": 0, "lock": 0.0, "t0": 0.0}
_keys = {}                                       # tek kullanımlık giriş anahtarlarının özeti -> bitiş zamanı (link '#k=' parçasında gider)
KEY_TTL = 86400
MAX_KEYS = 6


def _h(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8", "ignore")).hexdigest()


def _devs() -> list:
    try:
        with open(DEV_PATH, encoding="utf-8") as f:
            return [x for x in json.load(f).get("devices", []) if isinstance(x, dict) and isinstance(x.get("h"), str)]
    except (OSError, ValueError, AttributeError):
        return []


def _save(devs) -> None:
    with open(DEV_PATH + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"devices": devs}, f)
    os.replace(DEV_PATH + ".tmp", DEV_PATH)


def paired_count() -> int:
    return len(_devs())


def revoke_all() -> int:
    n = len(_devs())
    _save([])
    _sess.clear()
    return n


def _dev_ok(tok) -> bool:
    if not tok or not isinstance(tok, str) or len(tok) > 200:
        return False
    h, ok = _h(tok), False
    for d in _devs():
        ok = secrets.compare_digest(d["h"], h) or ok
    return ok


def _locked() -> bool:
    return time.time() < _bad["lock"]


def _fail() -> None:
    now = time.time()
    if now - _bad["t0"] > 300:
        _bad.update(n=0, t0=now)
    _bad["n"] += 1
    if _bad["n"] >= 10:
        _bad.update(lock=now + 300, n=0)


def login_url() -> str:
    """Telefona gönderilecek adres: '#k=<tek kullanımlık anahtar>' içerir. Anahtar adresin # sonrası parçasındadır (sunucuya, WhatsApp önizlemesine ya da günlüğe gitmez),
    telefon bunu ilk açılışta /login ile bir cihaz anahtarına çevirir ve kullanılmış olur; böylece adres her açılışta değişse de eşleşmiş telefon yeniden kod yazmaz.
    24 saat geçerli, tek kullanımlık; aynı adres için kullanılana kadar aynı anahtar verilir."""
    if not (S["on"] and S["host"]):
        return ""
    now = time.time()
    for k in [k for k, v in _keys.items() if v < now]:
        _keys.pop(k, None)
    lk = S.get("lkey")
    if not lk or lk["host"] != S["host"] or _h(lk["raw"]) not in _keys:
        if len(_keys) >= MAX_KEYS:
            _keys.pop(min(_keys, key=_keys.get), None)
        raw = secrets.token_urlsafe(24)
        _keys[_h(raw)] = now + KEY_TTL
        S["lkey"] = {"host": S["host"], "raw": raw}
        lk = S["lkey"]
    return f"https://{S['host']}/#k={lk['raw']}"


def _use_key(raw) -> bool:
    if not raw or not isinstance(raw, str) or len(raw) > 80:
        return False
    exp = _keys.pop(_h(raw), 0.0)
    return exp > time.time()


def new_session() -> str:
    tok = secrets.token_urlsafe(24)
    now = time.time()
    for k in [k for k, v in _sess.items() if v < now]:
        _sess.pop(k, None)
    _sess[_h(tok)] = now + SESSION_TTL
    return tok


def session_ok(tok) -> bool:
    if not tok or not isinstance(tok, str) or len(tok) > 100:
        return False
    return _sess.get(_h(tok), 0) > time.time()


# ------------------------------------------------------------------ eşleştirme
def arm_pair() -> str:
    """Sesle 'telefonu eşleştir': 3 dakikalık pencere açar. Kod telefon isteyince üretilir ve yalnızca bilgisayarda gösterilir."""
    _pair.update(until=time.time() + PAIR_WINDOW, id="", code="", tries=0)
    return "ok"


def _start_pair(force: bool = False):
    now = time.time()
    if (now > _pair["until"] and not force) or _locked():
        return None
    if force:
        _pair["until"] = now + PAIR_WINDOW                 # Tailscale'te ilk eşleşme: kod doğrulanabilsin diye pencere açılır
    _pair.update(id=secrets.token_urlsafe(8), code=f"{secrets.randbelow(10 ** 8):08d}", tries=0)
    if HOOKS["pair_code"]:
        HOOKS["pair_code"](_pair["code"])
    return _pair["id"]


def _confirm(pid: str, code: str):
    now = time.time()
    if now > _pair["until"] or not _pair["id"] or not secrets.compare_digest(pid.encode(), _pair["id"].encode()):
        return "none", None
    if not secrets.compare_digest(code.strip().encode(), _pair["code"].encode()):
        _pair["tries"] += 1
        if _pair["tries"] >= PAIR_TRIES:
            _pair.update(until=0.0, id="", code="")
            return "lock", None
        return "bad", PAIR_TRIES - _pair["tries"]
    _pair.update(until=0.0, id="", code="")
    tok = secrets.token_urlsafe(32)
    _save(_devs()[-(MAX_DEVICES - 1):] + [{"h": _h(tok), "t": int(now)}])
    return "ok", tok


# ------------------------------------------------------------------ sunucu
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class Guard:
    """Hiçbir şey sunmaz, şu ikisi dışında: (1) tünel: istek geri döngüden gelir VE Host tünel adresidir; (2) Tailscale: istek Tailscale ağından, bilgisayarın kendi Tailscale adresine
    ve Host=<o adres>:<port> ile gelir. Aksi hâlde (başka site, başka ağ, yanlış Host) 403."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            client = (scope.get("client") or ("", 0))[0]
            local = scope.get("server") or ("", 0)
            hdr = {k.decode("latin1").lower(): v.decode("latin1") for k, v in scope.get("headers", [])}
            h = hdr.get("host", "").lower()
            ok = bool(S["on"] and S["host"] and client in ("127.0.0.1", "::1") and h == S["host"] and local[1] == PORT)
            ok = ok or bool(TS["on"] and local[1] == PORT_TS and str(local[0]).replace("::ffff:", "") == TS["ip"] and h == f"{TS['ip']}:{PORT_TS}" and _ts_client(client))
            if not ok:
                if scope["type"] == "http":
                    await send({"type": "http.response.start", "status": 403, "headers": [(b"content-type", b"text/plain")]})
                    await send({"type": "http.response.body", "body": b"yasak"})
                else:
                    await receive()
                    await send({"type": "websocket.close", "code": 1008})
                return
        await self.inner(scope, receive, send)


app.add_middleware(Guard)


def _via_ts(headers) -> bool:
    return bool(TS["on"] and headers.get("host", "").lower() == f"{TS['ip']}:{PORT_TS}")


FULL = {"text": None, "mic_toggle": None, "open_guide": None, "open": None}              # main.py doldurur: bilgisayardaki Jarvis'e yazılı komut, mikrofon, kılavuz
PC_TYPES = {"state", "user", "jarvis", "tool", "mic", "mirror"}              # telefondaki 'Bilgisayar' sayfasına iletilen Jarvis mesajları
_pcsubs = set()


def full_enabled(headers) -> bool:
    """Tam kontrol (ekran + serbest komut) YALNIZCA Tailscale dinleyicisinde ve 'telefon kontrolü' açıkken. Herkese açık tünelden asla."""
    import settings
    return bool(_via_ts(headers) and settings.get("uzak_tam_kontrol"))


def forward_pc(msg: dict) -> None:
    """main.emit'ten: bağlı 'Bilgisayar' sayfalarına Jarvis durumu/konuşması iletilir."""
    if msg.get("type") not in PC_TYPES or not _pcsubs:
        return
    data = json.dumps(msg)
    for sock, lp in list(_pcsubs):
        try:
            asyncio.run_coroutine_threadsafe(sock.send_text(data), lp)
        except Exception:
            pass


def kick_pc() -> None:
    """Tam kontrol kapatıldı: bağlı sayfalara haber verip bağlantıları keser."""
    for sock, lp in list(_pcsubs):
        try:
            asyncio.run_coroutine_threadsafe(sock.send_text(json.dumps({"type": "off"})), lp)
            asyncio.run_coroutine_threadsafe(sock.close(code=1008), lp)
        except Exception:
            pass
    _pcsubs.clear()


def _same_origin(headers) -> bool:
    o, h = headers.get("origin", ""), headers.get("host", "").lower()
    if S["host"] and h == S["host"]:
        return o == "https://" + h
    return bool(_via_ts(headers) and o == "http://" + h)


SHIM = r"""<script>(()=>{const N=window.WebSocket,H=location.host,kind=location.pathname.split("/").pop();
const ls=k=>{try{return localStorage.getItem(k)||""}catch(e){return ""}};
async function renew(){try{const r=await fetch("/session",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({d:ls("jv_rdev")})});const d=await r.json();if(d.ok){try{localStorage.setItem("jv_s",d.s)}catch(e){}return true}}catch(e){}return false}
function W(url,p){const u=String(url);if(!/127\.0\.0\.1:8765\/ws/.test(u))return p===undefined?new N(url):new N(url,p);
 const w=new N((location.protocol==="https:"?"wss://":"ws://")+H+"/ws?k="+encodeURIComponent(kind)),s0=w.send.bind(w);
 w.send=d=>{try{const o=JSON.parse(d);if(o.type==="scene_close"){location.href="/";return}if(o.type==="mode_peek")return;o.s=ls("jv_s");d=JSON.stringify(o)}catch(e){}return s0(d)};
 w.addEventListener("message",e=>{try{const m=JSON.parse(e.data);if(m.type==="auth"&&!m.ok)renew().then(ok=>{if(!ok)location.href="/"})}catch(_){}});return w}
W.prototype=N.prototype;["CONNECTING","OPEN","CLOSING","CLOSED"].forEach((k,i)=>{W[k]=i});window.WebSocket=W;renew();setInterval(renew,45000)})()</script>"""
CSP_CONNECT = re.compile(r"connect-src 'self'( ws://127\.0\.0\.1:8765)?")


VIEWPORT = '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="color-scheme" content="dark">'
try:
    with open(os.path.join(UI, "remote_mobile.css"), encoding="utf-8") as _f:
        MOBILE_CSS = "<style>" + _f.read() + "</style>"
except OSError:
    MOBILE_CSS = ""


def mobile_head(html: str) -> str:
    """Telefon için ek başlık: eski sayfalarda viewport yoktu, telefon 980 px'lik masaüstü düzeni çiziyordu (dar-ekran kuralları hiç devreye girmiyordu)."""
    return ("" if 'name="viewport"' in html else VIEWPORT) + MOBILE_CSS


def _page(name: str, kind: str = "", req: Request = None) -> HTMLResponse:
    with open(os.path.join(UI, name), encoding="utf-8") as f:
        html = f.read()
    mark = '<meta charset="utf-8"><meta name="jv-remote" content="1">' + mobile_head(html) + ("" if "/kit/modes.js" in html else SHIM)
    html = html.replace('<meta charset="utf-8">', mark, 1)
    wsb = ("ws://" + f"{TS['ip']}:{PORT_TS}") if (req is not None and _via_ts(req.headers)) else "wss://" + S["host"]
    html = CSP_CONNECT.sub("connect-src 'self' " + wsb, html, count=1)
    return HTMLResponse(html, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"})


@app.get("/")
async def home(req: Request):
    return _page("remote.html", "", req)


@app.get("/scene/{kind}")
async def mode_page(kind: str, req: Request):
    if not kind_ok(kind, req.headers):
        return PlainTextResponse("yok", status_code=404)
    return _page(PAGE_OF.get(kind, f"scene_{kind}.html"), kind, req)


@app.get("/pc")
async def pc_page(req: Request):
    if not full_enabled(req.headers):
        return PlainTextResponse("kapalı", status_code=403)
    return _page("remote_pc.html", "", req)


@app.get("/browser")
async def browser_page(req: Request):
    return _page("remote_browser.html", "", req)


@app.get("/kit/{name}")
async def kit(name: str):
    if name not in ("modes.css", "modes.js", "scene_kit.css", "scene_kit.js"):
        return PlainTextResponse("yok", status_code=404)
    return FileResponse(os.path.join(UI, name), headers={"Cache-Control": "no-store"})


@app.get("/kit-help/{kind}")
async def kit_help(kind: str, req: Request):
    if not kind_ok(kind, req.headers):
        return JSONResponse({"title": "", "groups": []})
    import scene_kit
    return JSONResponse(scene_kit.help_for(kind))


@app.get("/vendor/maplibre/{name}")
async def maplibre(name: str):
    if name not in ("maplibre-gl-csp.js", "maplibre-gl-csp-worker.js", "maplibre-gl.css"):
        return PlainTextResponse("yok", status_code=404)
    return FileResponse(os.path.join(UI, "vendor", "maplibre", name), headers={"Cache-Control": "max-age=86400"})


@app.get("/fonts/{name}")
async def font(name: str):
    if name != "AmiriQuran.ttf":
        return PlainTextResponse("yok", status_code=404)
    return FileResponse(os.path.join(UI, "fonts", name), media_type="font/ttf", headers={"Cache-Control": "max-age=86400"})


@app.get("/info")
async def info(req: Request):
    return {"modes": [{"kind": k, "name": NAMES[k]} for k in WHITELIST] + [{"kind": k, "name": NAMES_FULL[k]} for k in FULL_KINDS if full_enabled(req.headers)] + [{"kind": "browser", "name": "Tarayıcı", "href": "/browser"}], "paired": paired_count() > 0, "pairing": time.time() < _pair["until"], "full": full_enabled(req.headers)}


@app.post("/pair/start")
async def pair_start(req: Request):
    if not _same_origin(req.headers):
        return JSONResponse({"ok": False, "msg": "yasak"}, status_code=403)
    pid = _start_pair(force=bool(_via_ts(req.headers)))          # Tailscale'te pencere beklemeden: ağa yalnızca kullanıcının kendi cihazları girer; kod yine yalnızca bilgisayarda gösterilir, 5 deneme
    if not pid:
        return JSONResponse({"ok": False, "msg": "Eşleştirme kapalı. Bilgisayara 'telefonu eşleştir' deyin."}, status_code=403)
    return {"ok": True, "id": pid}


@app.post("/pair/confirm")
async def pair_confirm(req: Request):
    if not _same_origin(req.headers):
        return JSONResponse({"ok": False, "msg": "yasak"}, status_code=403)
    try:
        d = await req.json()
        st, val = _confirm(str(d.get("id", ""))[:40], str(d.get("code", ""))[:12])
    except (ValueError, AttributeError):
        return JSONResponse({"ok": False, "msg": "geçersiz istek"}, status_code=400)
    if st == "ok":
        return {"ok": True, "token": val}
    msg = {"bad": f"Kod yanlış. Kalan hak: {val}", "lock": "Çok fazla yanlış deneme. Eşleştirme kapandı.", "none": "Kodun süresi doldu, yeniden 'telefonu eşleştir' deyin."}[st]
    return JSONResponse({"ok": False, "msg": msg}, status_code=400)


@app.post("/login")
async def login(req: Request):
    """Adresteki tek kullanımlık anahtarı bu telefonun kalıcı cihaz anahtarına çevirir (anahtar kullanılmış sayılır)."""
    if not _same_origin(req.headers):
        return JSONResponse({"ok": False}, status_code=403)
    if _locked():
        return JSONResponse({"ok": False, "msg": "Çok fazla hatalı deneme."}, status_code=429)
    try:
        d = await req.json()
    except ValueError:
        return JSONResponse({"ok": False}, status_code=400)
    if not _use_key(d.get("k")):
        _fail()
        return JSONResponse({"ok": False, "msg": "Bu giriş linkinin süresi dolmuş ya da daha önce kullanılmış."}, status_code=401)
    tok = secrets.token_urlsafe(32)
    _save(_devs()[-(MAX_DEVICES - 1):] + [{"h": _h(tok), "t": int(time.time())}])
    return {"ok": True, "token": tok}


NOTES: list = []                                          # telefona gidecek bildirimler (son 50): {"i": no, "t": başlık, "x": metin}
_note = {"id": 0}


def push_note(title: str, text: str) -> None:
    """Hatırlatma/zamanlayıcı/mola gibi olayları, Tailscale'e bağlı eşleşmiş telefondaki Jarvis uygulamasına bildirim olarak iletir."""
    _note["id"] += 1
    NOTES.append({"i": _note["id"], "t": str(title)[:60], "x": str(text)[:300]})
    del NOTES[:-50]


@app.get("/notify")
async def notify(req: Request, since: int = -1):
    """Uzun bekleyen istek: yeni bildirim gelince ya da 25 sn dolunca döner. Oturum anahtarı X-S başlığında; yalnızca Tailscale adresinde."""
    if not _via_ts(req.headers) or not session_ok(req.headers.get("x-s")):
        return JSONResponse({"ok": False}, status_code=401)
    if since < 0:
        return {"ok": True, "last": _note["id"], "n": []}
    end = time.time() + 25
    while time.time() < end and _note["id"] <= since:
        await asyncio.sleep(0.5)
    return {"ok": True, "last": _note["id"], "n": [n for n in NOTES if n["i"] > since]}


@app.post("/session")
async def session(req: Request):
    if not _same_origin(req.headers):
        return JSONResponse({"ok": False}, status_code=403)
    if _locked():
        return JSONResponse({"ok": False, "msg": "Çok fazla hatalı deneme."}, status_code=429)
    try:
        d = await req.json()
    except ValueError:
        return JSONResponse({"ok": False}, status_code=400)
    if not _dev_ok(d.get("d")):
        _fail()
        return JSONResponse({"ok": False, "msg": "Bu telefonun eşleşmesi geçersiz."}, status_code=401)
    return {"ok": True, "s": new_session(), "ttl": SESSION_TTL}


def _clean_panel(do: dict) -> dict:
    """Panelde bilgisayara ait ayrıntılar (çalan müzik, sistem, uygulama adları) telefona gönderilmez."""
    return do                                              # kullanıcı kişisel modlara izin verdi: panelde müzik, sistem, sınav ve ajanda kutucukları da gösterilir
    data = (do or {}).get("data")
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        dd = dict(data["data"])
        dd["muzik"] = None
        dd["sistem"] = None
        dd["sinav"] = None
        dd["ajanda"] = []                                  # sınav ve ajanda kişisel kayıttır: telefona gitmez
        if isinstance(dd.get("sure"), dict):
            dd["sure"] = {**dd["sure"], "apps": []}
        do = {**do, "data": {**data, "data": dd, "tiles": [t for t in data.get("tiles", []) if t not in ("muzik", "sistem", "sinav", "ajanda")]}}
    return do


async def _heavy(sock: WebSocket, kind: str):
    """Durumlu modlar (notlar, evim, rapor, kartlar, gelişim, quiz, pomodoro, mola, sistem, müzik, listeler, sınav): iş main.remote_ws'te yapılır, sonuçlar emit ile bu sokete akar."""
    import scenes
    await sock.accept()
    loop = asyncio.get_running_loop()
    st = {}
    limit = 3_000_000 if kind in BIG_KINDS else 6000
    registered = False
    try:
        while up():
            raw = await asyncio.wait_for(sock.receive_text(), 120.0)
            if len(raw) > limit:
                continue
            d = json.loads(raw)
            if not session_ok(d.get("s")):
                await sock.send_text(json.dumps({"type": "auth", "ok": False}))
                break
            t = str(d.get("type") or "")
            if t == "scene_ready":
                if not registered:
                    _sub(kind, sock, loop)
                    registered = True
                    if MAIN["attach"]:
                        await asyncio.to_thread(MAIN["attach"], kind)
                data = await asyncio.to_thread(scenes.INITS[kind])
                await sock.send_text(json.dumps({"type": "scene_init", "kind": kind, "data": data}))
            elif registered and MAIN["ws"]:
                await asyncio.to_thread(MAIN["ws"], kind, d, st)
    except (WebSocketDisconnect, RuntimeError, ValueError, asyncio.TimeoutError):
        pass
    except Exception as e:
        print("UZAKTAN mod hatası:", kind, type(e).__name__, flush=True)
    finally:
        if registered:
            _unsub(kind, sock, loop)
        try:
            await sock.close()
        except Exception:
            pass


def _view_of(kind: str):
    import importlib
    return importlib.import_module(VIEW_MODS[kind]).view if kind in VIEW_MODS else None


def _ws_mod(kind: str):
    import importlib
    return importlib.import_module("scenes_" + kind) if kind in VIEW_MODS else None


def _shape(kind: str, r: dict) -> dict:
    """Mod sonucunu telefona uygun hâle getirir: PC'de yan etki yaratacak her şey (müzik, tarayıcı açma, konuşma) atılır; görünüm eklenir."""
    do = dict(r.get("do") or {})
    do.pop("music", None)
    if kind == "panel":
        do = _clean_panel(do)
    v = _view_of(kind)
    if v is not None:
        do["data"] = v()
    return {**do, "msg": r.get("say", "")}


_BLOCK = {"harita": re.compile(r"\b(evim|evimi|evime|evimde)\b")}                                      # kişisel konum bilgisi (ev) uzaktan açılmaz


async def _browser(sock: WebSocket):
    """Telefon tarayıcısı: varsayılan olarak AYRI, geçici profilli headless Edge (rbrowser.start; bilgisayardaki hesaplara/oturumlara bağlı değil). ?m=shared: bunun yerine
    JARVİS TARAYICISININ KENDİSİ (jbrowser; oturumları ve VPN çıkışıyla; 127.0.0.1'de hata ayıklama portu). Her mesaj güncel oturum anahtarını taşır."""
    import rbrowser
    await sock.accept()
    shared = sock.query_params.get("m") == "shared"     # varsayılan AYRI: bilgisayardaki oturumlar (Google vb.) telefona sızmaz
    q, last, nfr = [55], [b""], [0]
    try:
        proxy = ""
        if shared:
            import jbrowser
            port = await asyncio.to_thread(jbrowser.phone_open)
            r = await asyncio.to_thread(rbrowser.attach, port)
            proxy = jbrowser.S.get("proxy") or ""
        else:
            r = await asyncio.to_thread(rbrowser.start, "")
        await sock.send_text(json.dumps({"type": "ready", "ok": r == "ok", "msg": "" if r == "ok" else r, "vpn": bool(proxy), "shared": shared}))
        if r != "ok":
            return
        while up():
            d = json.loads(await asyncio.wait_for(sock.receive_text(), 300.0))
            if not session_ok(d.get("s")):
                await sock.send_text(json.dumps({"type": "auth", "ok": False}))
                break
            t = str(d.get("type") or "")
            try:
                if t == "frame":
                    t0 = time.time()
                    jpg = await asyncio.to_thread(rbrowser.frame, q[0])
                    q[0] = 40 if time.time() - t0 > 0.7 else 55                      # yavaşlayınca kare küçülür
                    h = hashlib.md5(jpg).digest()
                    same = h == last[0]
                    last[0] = h
                    if not same:
                        await sock.send_bytes(jpg)                                    # aynı kare tekrar gönderilmez
                    nfr[0] += 1
                    meta = await asyncio.to_thread(rbrowser.info) if (not same or nfr[0] % 6 == 0) else {}      # adres/başlık sorgusu her karede gerekmez: gecikmeyi azaltır
                    await sock.send_text(json.dumps({"type": "info", "same": same, **meta}))
                elif t == "nav":
                    res = await asyncio.to_thread(rbrowser.navigate, str(d.get("url") or ""))
                    if res != "ok":
                        await sock.send_text(json.dumps({"type": "msg", "text": res}))
                elif t == "size":
                    await asyncio.to_thread(rbrowser.viewport, float(d.get("w")), float(d.get("h")))
                elif t == "tap":
                    ed = await asyncio.to_thread(rbrowser.tap, float(d.get("x")), float(d.get("y")))
                    await sock.send_text(json.dumps({"type": "focus", "edit": bool(ed)}))
                elif t == "scroll":
                    await asyncio.to_thread(rbrowser.scroll, float(d.get("dy") or 0), float(d.get("dx") or 0))
                elif t == "text":
                    await asyncio.to_thread(rbrowser.text, str(d.get("text") or ""))
                elif t == "key":
                    await asyncio.to_thread(rbrowser.key, str(d.get("key") or ""))
                elif t == "back":
                    await asyncio.to_thread(rbrowser.history, -1)
                elif t == "forward":
                    await asyncio.to_thread(rbrowser.history, 1)
                elif t == "reload":
                    await asyncio.to_thread(rbrowser.reload)
                elif t == "close":
                    await asyncio.to_thread(rbrowser.stop)
                    break
            except (TypeError, ValueError):
                continue
            except TimeoutError:
                await sock.send_text(json.dumps({"type": "msg", "text": "Sayfa yanıt vermedi."}))
    except (WebSocketDisconnect, RuntimeError, ValueError, asyncio.TimeoutError):
        pass
    except Exception as e:
        print("UZAKTAN tarayıcı hata:", type(e).__name__, flush=True)
    finally:
        await asyncio.to_thread(_browser_release)
        try:
            await sock.close()
        except Exception:
            pass


async def _pc(sock: WebSocket):
    """Bilgisayarı yönetme (yalnızca Tailscale): yazılı komut bilgisayardaki Jarvis'e sesli komut gibi gider, mikrofon aç/kapat, kılavuz. Her mesaj güncel oturum anahtarını taşır ve her seferinde 'telefon kontrolü' ayarı yeniden denetlenir."""
    await sock.accept()
    loop = asyncio.get_running_loop()
    reg, last = False, 0.0
    try:
        while up():
            d = json.loads(await asyncio.wait_for(sock.receive_text(), 90.0))
            if not session_ok(d.get("s")):
                await sock.send_text(json.dumps({"type": "auth", "ok": False}))
                break
            if not full_enabled(sock.headers):
                await sock.send_text(json.dumps({"type": "off"}))
                break
            if not reg:
                _pcsubs.add((sock, loop))
                reg = True
            t = d.get("type")
            if t == "text" and isinstance(d.get("text"), str) and d["text"].strip() and FULL["text"]:
                if time.time() - last < 0.4:
                    continue
                last = time.time()
                FULL["text"](d["text"].strip()[:1000])
            elif t == "mic_toggle" and FULL["mic_toggle"]:
                FULL["mic_toggle"]()
            elif t == "open_guide" and FULL["open_guide"]:
                FULL["open_guide"]()
            elif t == "open" and isinstance(d.get("kind"), str) and FULL["open"]:
                r = await asyncio.to_thread(FULL["open"], d["kind"][:20])                         # modu BİLGİSAYARDA açar/kapatır (ekranı telefondan görürsünüz)
                await sock.send_text(json.dumps({"type": "open_res", "kind": d["kind"][:20], "res": str(r)[:200]}))
            elif t == "shell" and isinstance(d.get("cmd"), str) and d["cmd"].strip():
                import remote_input
                res = await asyncio.to_thread(remote_input.shell, d["cmd"].strip()[:4000])        # PowerShell komutu: tam kontrol kullanıcının tercihi (yalnızca Tailscale)
                await sock.send_text(json.dumps({"type": "shell_out", "id": d.get("id"), **res}))
            elif t in ("mouse", "keys", "type"):
                import remote_input
                await asyncio.to_thread(remote_input.handle, d)               # gerçek fare/klavye girdisi (yalnızca Tailscale + tam kontrol açık)
    except (WebSocketDisconnect, RuntimeError, ValueError, asyncio.TimeoutError):
        pass
    except Exception as e:
        print("UZAKTAN bilgisayar hatası:", type(e).__name__, flush=True)
    finally:
        _pcsubs.discard((sock, loop))
        try:
            await sock.close()
        except Exception:
            pass


async def _pcscreen(sock: WebSocket):
    """Bilgisayar ekranı yayını (mirror.py): bağlanırken oturum doğrulanır, bağlantı en çok 30 dakika sürer (sonra sayfa taze oturumla yeniden bağlanır)."""
    import mirror
    await sock.accept()
    try:
        d = json.loads(await asyncio.wait_for(sock.receive_text(), 10.0))
        if not session_ok(d.get("s")):
            await sock.send_text(json.dumps({"type": "auth", "ok": False}))
            return
        await asyncio.wait_for(mirror.serve(sock), 1800.0)
    except (WebSocketDisconnect, RuntimeError, ValueError, asyncio.TimeoutError):
        pass
    except Exception as e:
        print("UZAKTAN ekran hatası:", type(e).__name__, str(e)[:120], flush=True)
    finally:
        try:
            await sock.close()
        except Exception:
            pass


async def _audio(sock: WebSocket):
    """Telefon tarayıcısının sesi (audio_tap.py): bilgisayarın hoparlör karışımı PCM olarak akar. İstemci en az 20 saniyede bir {s} gönderip oturumu doğrular, aksi hâlde kesilir."""
    import audio_tap
    await sock.accept()
    loop = asyncio.get_running_loop()
    q = asyncio.Queue()

    def cb(pcm: bytes):
        loop.call_soon_threadsafe(lambda: (q.qsize() > 25 and q.get_nowait(), q.put_nowait(pcm)))
    try:
        d = json.loads(await asyncio.wait_for(sock.receive_text(), 10.0))
        if not session_ok(d.get("s")):
            await sock.send_text(json.dumps({"type": "auth", "ok": False}))
            return
        if not audio_tap.subscribe(cb):
            await sock.send_text(json.dumps({"type": "msg", "text": "Ses aktarma kullanılamıyor."}))
            return
        await sock.send_text(json.dumps({"type": "ready", "rate": audio_tap.OUT_RATE}))
        last_ok = time.time()

        async def reader():
            nonlocal last_ok
            while True:
                m = json.loads(await sock.receive_text())
                if session_ok(m.get("s")):
                    last_ok = time.time()
        rd = asyncio.create_task(reader())
        try:
            while up() and not rd.done() and time.time() - last_ok < 120:
                try:
                    await sock.send_bytes(await asyncio.wait_for(q.get(), 1.0))
                except asyncio.TimeoutError:
                    continue
        finally:
            rd.cancel()
    except (WebSocketDisconnect, RuntimeError, ValueError, asyncio.TimeoutError):
        pass
    except Exception as e:
        print("UZAKTAN ses hata:", type(e).__name__, flush=True)
    finally:
        try:
            audio_tap.unsubscribe(cb)
        except Exception:
            pass
        try:
            await sock.close()
        except Exception:
            pass


def _browser_release() -> None:
    """Telefon ayrıldı / kapandı: bağlantı kesilir; telefon için açılan Jarvis tarayıcısı kapanır, kullanıcının açtığı hata ayıklama portu olmadan yeniden açılır."""
    try:
        import rbrowser
        rbrowser.stop()
    except Exception:
        pass
    try:
        import jbrowser
        jbrowser.phone_release()
    except Exception:
        pass
    try:
        import audio_tap
        audio_tap.stop_all()
    except Exception:
        pass


_chat_last = {"t": 0.0}


async def _chat(sock: WebSocket):
    """Telefondan sohbet + güvenli yazılı komutlar (remote_chat.py). Her mesaj güncel oturum anahtarını taşır; yanıt parça parça akar."""
    import remote_chat
    await sock.accept()
    hist = []
    loop = asyncio.get_running_loop()
    try:
        while up():
            d = json.loads(await asyncio.wait_for(sock.receive_text(), 300.0))
            if not session_ok(d.get("s")):
                await sock.send_text(json.dumps({"type": "auth", "ok": False}))
                break
            text = str(d.get("text") or "").strip()[:500]
            if d.get("type") != "chat" or not text:
                continue
            if time.time() - _chat_last["t"] < 1.0:
                await sock.send_text(json.dumps({"type": "chat_done", "text": "Biraz yavaş efendim."}))
                continue
            _chat_last["t"] = time.time()
            if full_enabled(sock.headers) and FULL["text"]:
                # Tailscale + tam kontrol: sohbet kutusundaki her şey bilgisayardaki Jarvis'e sesli komut gibi gider; cevaplar 'jarvis' mesajlarıyla bu sohbete akar.
                if (sock, loop) not in _pcsubs:
                    _pcsubs.add((sock, loop))
                FULL["text"](text)
                await sock.send_text(json.dumps({"type": "chat_done", "text": "", "cmd": True}))
                continue
            reply, kind = await asyncio.to_thread(remote_chat.safe_command, text, {**NAMES, "browser": "Tarayıcı"})
            if reply:
                await sock.send_text(json.dumps({"type": "chat_done", "text": reply, "open": ("/browser" if kind == "browser" else "/scene/" + kind) if kind else ""}))
                continue
            q = asyncio.Queue()

            def work():
                try:
                    for piece in remote_chat.stream(hist, text):
                        loop.call_soon_threadsafe(q.put_nowait, piece)
                except Exception as e:
                    print("UZAKTAN sohbet hatası:", type(e).__name__, flush=True)
                    loop.call_soon_threadsafe(q.put_nowait, None)
                    return
                loop.call_soon_threadsafe(q.put_nowait, "")
            threading.Thread(target=work, daemon=True).start()
            while True:
                piece = await asyncio.wait_for(q.get(), 90.0)
                if piece is None:
                    await sock.send_text(json.dumps({"type": "chat_done", "text": "Şu an yanıt veremiyorum efendim, yerel yapay zekâ hazır olmayabilir."}))
                    break
                if piece == "":
                    await sock.send_text(json.dumps({"type": "chat_done", "text": ""}))
                    break
                await sock.send_text(json.dumps({"type": "chat_delta", "text": piece}))
    except (WebSocketDisconnect, RuntimeError, ValueError, asyncio.TimeoutError):
        pass
    except Exception as e:
        print("UZAKTAN sohbet hata:", type(e).__name__, flush=True)
    finally:
        _pcsubs.discard((sock, loop))
        try:
            await sock.close()
        except Exception:
            pass


@app.websocket("/ws")
async def ws(sock: WebSocket):
    if not _same_origin(sock.headers):
        await sock.close(code=1008)
        return
    kind = sock.query_params.get("k")
    if kind in ("pc", "pcscreen"):
        if not full_enabled(sock.headers):
            await sock.close(code=1008)
            return
        await (_pc if kind == "pc" else _pcscreen)(sock)
        return
    if kind == "chat":
        await _chat(sock)
        return
    if kind == "browser":
        await _browser(sock)
        return
    if kind == "audio":
        await _audio(sock)
        return
    if not kind_ok(kind, sock.headers):
        await sock.close(code=1008)
        return
    if kind in HEAVY:
        await _heavy(sock, kind)
        return
    await sock.accept()
    st = {}
    import scenes

    async def push(do: dict):
        await sock.send_text(json.dumps({"type": "scene_do", "kind": kind, "do": do}))

    async def run_later(f):
        try:
            res = await asyncio.to_thread(f)
        except Exception as e:
            print("UZAKTAN arka plan hatası:", type(e).__name__, flush=True)
            return
        do = {}
        if isinstance(res, dict):
            do, res = res.get("do") or {}, res.get("say", "")
        try:
            await push(_shape(kind, {"do": do, "say": res if isinstance(res, str) else ""}) | {"done": True})
        except Exception:
            pass

    async def deliver(r):
        if not r or r.get("exit"):
            return
        await push(_shape(kind, r))
        if callable(r.get("later")):
            asyncio.create_task(run_later(r["later"]))

    try:
        while up():
            raw = await asyncio.wait_for(sock.receive_text(), 120.0)
            if len(raw) > 4000:
                continue
            d = json.loads(raw)
            if not session_ok(d.get("s")):
                await sock.send_text(json.dumps({"type": "auth", "ok": False}))
                break
            t = str(d.get("type") or "")
            if t == "scene_ready":
                data = await asyncio.to_thread(scenes.INITS[kind])
                await sock.send_text(json.dumps({"type": "scene_init", "kind": kind, "data": _clean_panel({"data": data})["data"] if kind == "panel" else data}))
            elif t == "text" and isinstance(d.get("text"), str) and d["text"].strip():
                text = d["text"].strip()[:300]
                if kind in _BLOCK and _BLOCK[kind].search(text.lower()):
                    await push({"msg": "Bu komut uzaktan erişimde kapalı."})
                    continue
                await deliver(await asyncio.to_thread(scenes.handle, kind, text, st))
            elif t == "scene_state" and isinstance(d.get("state"), dict) and len(json.dumps(d["state"])) < 1500:
                st.update(d["state"])
            elif t == "sci_param" and kind in SCI:
                import scenes_sci
                res = await asyncio.to_thread(scenes_sci.sci_param, kind, d)
                if res:
                    await push(res)
            elif kind in VIEW_MODS and t.startswith(kind + "_"):
                mod = _ws_mod(kind)
                r = await asyncio.to_thread(mod.ws, d, st) or {}
                if not r.get("quiet"):
                    await deliver(r)
    except (WebSocketDisconnect, RuntimeError, ValueError, asyncio.TimeoutError):
        pass
    except Exception as e:
        print("UZAKTAN hata:", type(e).__name__, flush=True)
    finally:
        try:
            await sock.close()
        except Exception:
            pass


# ------------------------------------------------------------------ tünel + aç / kapat
_URL = re.compile(r"https://([a-z0-9-]+\.trycloudflare\.com)")


def _tunnel() -> str:
    p = subprocess.Popen([EXE, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{PORT}"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace", creationflags=0x08000000)
    S["proc"] = p
    found = {"h": ""}

    def pump():
        for line in p.stdout:
            m = _URL.search(line)
            if m and not found["h"]:
                found["h"] = m.group(1).lower()
    threading.Thread(target=pump, daemon=True).start()
    for _ in range(150):
        if found["h"]:
            return found["h"]
        if p.poll() is not None:
            break
        time.sleep(0.2)
    return ""


def start(auto: bool = False) -> str:
    """Sunucuyu ve tüneli açar. 'ok' ya da hata açıklaması; adres S['host'] içindedir. auto=True (remote_auto): 2 saatlik süre sınırı yok."""
    with _lock:
        if S["on"]:
            return "ok"
        if not os.path.exists(EXE):
            return "Tünel programı bulunamadı efendim (bin klasöründe cloudflared.exe olmalı)."
        srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning", proxy_headers=False))   # X-Forwarded-For yok sayılır: istemci hep geri döngü (tünel) görünür
        S.update(server=srv, host="", until=time.time() + TTL_S, auto=bool(auto))
        threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(40):
        if srv.started:
            break
        time.sleep(0.1)
    else:
        stop()
        return "Uzaktan erişim sunucusu başlatılamadı (8767 numaralı port kullanımda olabilir)."
    host = _tunnel()
    if not host:
        stop()
        return "Tünel kurulamadı efendim, internet bağlantınızı kontrol edin."
    S.update(on=True, host=host)
    threading.Thread(target=_watch, args=(srv,), daemon=True).start()
    return "ok"


def _watch(srv) -> None:
    while S["on"] and S["server"] is srv:
        time.sleep(5)
        try:
            import rbrowser
            if rbrowser.alive() and time.time() - rbrowser.S["last"] > rbrowser.IDLE_S:
                _browser_release()
        except Exception:
            pass
        if (time.time() > S["until"] and not S["auto"]) or (S["proc"] and S["proc"].poll() is not None):
            stop()
            if HOOKS["closed"]:
                HOOKS["closed"]()
            return


def ts_url() -> str:
    return f"http://{TS['ip']}:{PORT_TS}/" if TS["on"] else ""


def ts_start() -> str:
    """Sunucuyu YALNIZCA bilgisayarın Tailscale adresinde (100.x.y.z) dinletir; tünel ve herkese açık adres kullanılmaz. 'ok' ya da hata açıklaması."""
    with _lock:
        if TS["on"]:
            return "ok"
        import lan
        ip = os.environ.get("JARVIS_TS_IP") or lan.tailscale_ip()
        if not ip:
            return "Bu bilgisayarda Tailscale adresi bulunamadı efendim. Tailscale kurulu ve açık olmalı."
        srv = uvicorn.Server(uvicorn.Config(app, host=ip, port=PORT_TS, log_level="warning", proxy_headers=False))
        TS.update(on=True, ip=ip, server=srv)
        threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(40):
        if srv.started:
            return "ok"
        time.sleep(0.1)
    ts_stop()
    return f"Tailscale dinleyicisi başlatılamadı ({PORT_TS} numaralı port kullanımda olabilir)."


def ts_stop() -> None:
    with _lock:
        srv = TS["server"]
        TS.update(on=False, ip="", server=None)
    if srv is not None:
        srv.should_exit = True


def stop() -> None:
    with _lock:
        srv, proc = S["server"], S["proc"]
        S.update(on=False, host="", server=None, proc=None, auto=False, lkey=None)
        _sess.clear()
        _keys.clear()
        _pair.update(until=0.0, id="", code="")
    try:
        _browser_release()                                 # uzaktan erişim kapanınca telefon bağlantısı kesilir; telefon için açılan tarayıcı kapanır
    except Exception:
        pass
    if proc is not None:
        try:
            proc.terminate()
        except OSError:
            pass
    if srv is not None:
        srv.should_exit = True


def url() -> str:
    return f"https://{S['host']}/" if S["on"] and S["host"] else ""
