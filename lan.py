"""Telefonla DOĞRUDAN Wi-Fi bağlantısı (kablosuz, aracı sunucu yok): ekran yansıtma ve komut için ayrı, küçük bir sunucu.
Güvenlik tasarımı:
- Jarvis'in asıl sunucusu (arayüz, tüm uçlar) hâlâ yalnızca 127.0.0.1'i dinler; ağa açılan YALNIZCA bu dosyadaki küçük sunucudur ve yalnızca üç şey sunar:
  telefon sayfası, eşleştirme ve (eşleşmiş telefon için) ekran yayını + birkaç komut (yazı komutu, mikrofon aç/kapa, kılavuz).
- Varsayılan KAPALI: sesle açılınca dinlemeye başlar, kapatılınca port tamamen kapanır; Jarvis her başladığında yeniden kapalıdır.
- Yalnızca özel ağ adreslerinden (192.168.x.x, 10.x.x.x, 172.16-31.x.x) bağlantı kabul edilir; internet adresleri her zaman reddedilir.
- Eşleştirme: telefon kod ister, kod YALNIZCA bilgisayar ekranında/bildiriminde görünür, telefona yazılır (2 dk geçerli, 5 hatalı denemede kod iptal ve 60 sn kilit).
  Doğru kodla telefona rastgele bir cihaz anahtarı verilir; bilgisayarda yalnızca özeti (SHA-256) saklanır. Sonraki bağlantılar bu anahtarı ister.
- Her istek aynı kaynaktan (Origin = sayfanın kendi adresi) gelmelidir; başka bir sitedeki betik bağlanamaz.
- Trafik düz HTTP/WS'dir (şifreli değil): güvenilir bir ev ağı varsayılır; halka açık Wi-Fi'de açmayın."""
import asyncio
import hashlib
import ipaddress
import json
import os
import secrets
import socket
import threading
import time

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

import mirror

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8766
DEV_PATH = os.path.join(HERE, "lan_devices.json")
MAX_DEVICES = 2
CODE_TTL, MAX_TRIES, LOCK_S, START_GAP = 120, 5, 60, 10
FORWARD_TYPES = {"state", "user", "jarvis", "tool", "mic", "mirror"}      # telefona yalnızca bunlar iletilir
HOOKS = {"text": None, "mic_toggle": None, "open_guide": None, "pair_code": None}
S = {"on": False, "server": None}
_lock = threading.RLock()
_pend = {"id": "", "code": "", "exp": 0.0, "tries": 0}
_rate = {"last": 0.0, "lock_until": 0.0}
_socks = {}                      # kontrol WebSocket'leri -> kendi olay döngüleri (ana arayüzden gelen mesajları iletmek için)


# ------------------------------------------------------------------ cihazlar
def _load() -> list:
    try:
        with open(DEV_PATH, encoding="utf-8") as f:
            d = json.load(f)
        return [x for x in d.get("devices", []) if isinstance(x, dict) and isinstance(x.get("h"), str)]
    except (OSError, ValueError, AttributeError):
        return []


def _save(devs: list) -> None:
    tmp = DEV_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"devices": devs}, f)
    os.replace(tmp, DEV_PATH)


def _h(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8", "ignore")).hexdigest()


def device_ok(token) -> bool:
    if not token:
        return False
    h = _h(str(token))
    ok = False
    for d in _load():
        ok = secrets.compare_digest(d["h"], h) or ok          # hepsi karşılaştırılır (zamanlama farkı vermesin)
    return ok


def revoke_all() -> int:
    n = len(_load())
    _save([])
    mirror.kick_lan()
    return n


def paired_count() -> int:
    return len(_load())


# ------------------------------------------------------------------ eşleştirme
def start_pair():
    """Yeni eşleştirme kodu üretir ve bilgisayarda gösterir. Çok sık istenirse ya da kilitliyse None."""
    now = time.time()
    with _lock:
        if now < _rate["lock_until"] or now - _rate["last"] < START_GAP:
            return None
        _rate["last"] = now
        _pend.update(id=secrets.token_urlsafe(8), code=f"{secrets.randbelow(10 ** 6):06d}", exp=now + CODE_TTL, tries=0)
        out = {"id": _pend["id"], "code": _pend["code"]}
    if HOOKS["pair_code"]:
        HOOKS["pair_code"](out["code"])
    return {"id": out["id"]}


def confirm_pair(pid: str, code: str):
    """(durum, jeton|kalan_hak): 'ok' doğru; 'bad' yanlış kod; 'lock' çok fazla yanlış; 'none' geçerli istek yok/süresi doldu."""
    now = time.time()
    with _lock:
        if now < _rate["lock_until"]:
            return "lock", 0
        if not _pend["id"] or now > _pend["exp"] or not secrets.compare_digest(str(pid).encode(), _pend["id"].encode()):
            return "none", 0
        if not secrets.compare_digest(str(code).strip().encode(), _pend["code"].encode()):
            _pend["tries"] += 1
            left = MAX_TRIES - _pend["tries"]
            if left <= 0:
                _pend.update(id="", code="", exp=0.0)
                _rate["lock_until"] = now + LOCK_S
                return "lock", 0
            return "bad", left
        _pend.update(id="", code="", exp=0.0)
        token = secrets.token_urlsafe(32)
        devs = _load()[-(MAX_DEVICES - 1):] + [{"h": _h(token), "t": int(now)}]      # en eski eşleşme düşer
        _save(devs)
        return "ok", token


# ------------------------------------------------------------------ ağ
def lan_ip() -> str:
    """Bilgisayarın ev ağındaki adresi (paket göndermeden, varsayılan yoldan okunur)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return ""
    finally:
        s.close()


def address() -> str:
    ip = lan_ip()
    return f"http://{ip}:{PORT}/" if ip else ""


def addresses() -> list:
    """Telefonda açılabilecek adresler: ev Wi-Fi'si ve (kuruluysa) Tailscale."""
    out = [a for a in (address(),) if a]
    ts = tailscale_ip()
    if ts:
        out.append(f"http://{ts}:{PORT}/")
    return out


_HOME_NETS = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16", "127.0.0.0/8", "fc00::/7", "fe80::/10", "::1/128")]


_TS_NET = ipaddress.ip_network("100.64.0.0/10")           # Tailscale'in kullandığı aralık
_ts_cache = {"t": 0.0, "ip": ""}


def tailscale_ip() -> str:
    """Bu bilgisayardaki Tailscale arayüzünün adresi (kurulu değilse ''). 30 sn önbelleklenir."""
    now = time.time()
    if now - _ts_cache["t"] < 30:
        return _ts_cache["ip"]
    ip = ""
    try:
        import psutil
        for name, addrs in psutil.net_if_addrs().items():
            if "tailscale" in name.lower():
                for a in addrs:
                    if a.family == socket.AF_INET and ipaddress.ip_address(a.address) in _TS_NET:
                        ip = a.address
    except Exception:
        ip = ""
    _ts_cache.update(t=now, ip=ip)
    return ip


def private_client(host: str, server_ip: str = "") -> bool:
    """Yalnızca ev/ofis ağı adresleri (RFC 1918, bağlantı-yerel, geri döngü). Belgeleme/ayrılmış aralıklar ve internet adresleri reddedilir.
    Tailscale aralığındaki (100.64.0.0/10) istemci YALNIZCA bağlantı bu bilgisayarın kendi Tailscale adresine geldiyse kabul edilir (server_ip):
    aynı aralığı kullanan başka bir ağdaki (ör. operatör/yurt ağı) kişiler bu yoldan giremez."""
    try:
        ip = ipaddress.ip_address(str(host).split("%")[0])
    except ValueError:
        return False
    if getattr(ip, "ipv4_mapped", None):
        ip = ip.ipv4_mapped
    if any(ip in n for n in _HOME_NETS):
        return True
    if ip in _TS_NET:
        ts = tailscale_ip()
        return bool(ts) and str(server_ip).replace("::ffff:", "") == ts
    return False


def same_origin(headers) -> bool:
    origin, host = headers.get("origin"), headers.get("host")
    return bool(origin and host and origin == f"http://{host}")


# ------------------------------------------------------------------ sunucu
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class Guard:
    """Her isteğin ilk kapısı: sunucu kapalıysa ya da istemci özel ağda değilse hiçbir şey sunmaz."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            host = (scope.get("client") or ("", 0))[0]
            local = (scope.get("server") or ("", 0))[0]
            if not S["on"] or not private_client(host, local):
                if scope["type"] == "http":
                    await send({"type": "http.response.start", "status": 403, "headers": [(b"content-type", b"text/plain")]})
                    await send({"type": "http.response.body", "body": b"yasak"})
                else:
                    await receive()
                    await send({"type": "websocket.close", "code": 1008})
                return
        await self.inner(scope, receive, send)


app.add_middleware(Guard)


@app.get("/")
async def page():
    with open(os.path.join(HERE, "ui", "mirror.html"), encoding="utf-8") as f:
        html = f.read().replace('<meta charset="utf-8">', '<meta charset="utf-8"><meta name="jv-lan" content="1">', 1)
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@app.post("/pair/start")
async def pair_start(req: Request):
    if not same_origin(req.headers):
        return JSONResponse({"ok": False, "msg": "yasak"}, status_code=403)
    r = start_pair()
    if r is None:
        return JSONResponse({"ok": False, "msg": "Biraz bekleyip tekrar deneyin."}, status_code=429)
    return {"ok": True, "id": r["id"]}


@app.post("/pair/confirm")
async def pair_confirm(req: Request):
    if not same_origin(req.headers):
        return JSONResponse({"ok": False, "msg": "yasak"}, status_code=403)
    try:
        d = await req.json()
        pid, code = str(d.get("id", ""))[:40], str(d.get("code", ""))[:12]
    except (ValueError, AttributeError):
        return JSONResponse({"ok": False, "msg": "geçersiz istek"}, status_code=400)
    st, val = confirm_pair(pid, code)
    if st == "ok":
        return {"ok": True, "token": val}
    msg = {"bad": f"Kod yanlış. Kalan hak: {val}", "lock": "Çok fazla yanlış deneme. Bir dakika bekleyin.", "none": "Kodun süresi doldu, yeniden kod isteyin."}[st]
    return JSONResponse({"ok": False, "msg": msg}, status_code=429 if st == "lock" else 400)


async def _auth(sock: WebSocket) -> bool:
    if not same_origin(sock.headers) or not device_ok(sock.query_params.get("d")):
        await sock.close(code=1008)
        return False
    await sock.accept()
    return True


@app.websocket("/mws")
async def stream(sock: WebSocket):
    if not await _auth(sock):
        return
    try:
        await mirror.serve(sock, lan=True)
    except (WebSocketDisconnect, RuntimeError):
        pass
    except Exception as e:
        print("KABLOSUZ yayın hatası:", type(e).__name__, e, flush=True)


@app.websocket("/ws")
async def control(sock: WebSocket):
    if not await _auth(sock):
        return
    _socks[sock] = asyncio.get_running_loop()
    try:
        while S["on"]:
            try:
                raw = await asyncio.wait_for(sock.receive_text(), 5.0)
            except asyncio.TimeoutError:
                if not device_ok(sock.query_params.get("d")):          # eşleşme silindiyse bağlantı kesilir
                    break
                continue
            if len(raw) > 4000:
                continue
            d = json.loads(raw)
            t = d.get("type")
            if t == "text" and isinstance(d.get("text"), str) and d["text"].strip() and HOOKS["text"]:
                HOOKS["text"](d["text"].strip()[:1000])
            elif t == "mic_toggle" and HOOKS["mic_toggle"]:
                HOOKS["mic_toggle"]()
            elif t == "open_guide" and HOOKS["open_guide"]:
                HOOKS["open_guide"]()
    except (WebSocketDisconnect, RuntimeError, ValueError):
        pass
    finally:
        _socks.pop(sock, None)
        try:
            await sock.close()
        except Exception:
            pass


def broadcast(msg: dict) -> None:
    """main.emit'ten: Jarvis'in durum/konuşma mesajlarını eşleşmiş telefona iletir (yalnızca izinli türler)."""
    if not _socks or msg.get("type") not in FORWARD_TYPES:
        return
    s = json.dumps(msg)
    for sock, lp in list(_socks.items()):
        try:
            asyncio.run_coroutine_threadsafe(sock.send_text(s), lp)
        except Exception:
            pass


# ------------------------------------------------------------------ aç / kapat
def start() -> str:
    """Kablosuz sunucuyu başlatır. 'ok' ya da hata açıklaması."""
    with _lock:
        if S["on"]:
            return "ok"
        srv = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="warning"))
        S.update(on=True, server=srv)
        threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(40):
        if srv.started:
            return "ok"
        time.sleep(0.1)
    stop()
    return "Kablosuz sunucu başlatılamadı (8766 numaralı port kullanımda olabilir)."


def stop() -> None:
    with _lock:
        srv, S["server"] = S["server"], None
        S["on"] = False
    mirror.kick_lan()
    if srv is not None:
        srv.should_exit = True
    with _lock:
        _pend.update(id="", code="", exp=0.0)
