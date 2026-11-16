"""Kendi VPN'iniz: sizin kiraladığınız bir sunucuya (ör. ABD'de bir VPS) SSH tüneli (ssh -D) açar ve yerelde 127.0.0.1:PORT'ta bir SOCKS5 proxy sunar.
Jarvis tarayıcısı (jbrowser) bu proxy'yi kullanır: VPN açıkken siteler sizi sunucunun ülkesinden görür, kapatınca doğrudan (Türkiye'den) çıkar.
Neden böyle: sistem düzeyinde VPN sürücüsü ve yönetici izni gerektirmez, bilgisayarın ağ ayarlarına dokunmaz, yalnızca Jarvis tarayıcısını etkiler (MEBİ, WhatsApp vb. Türkiye'den kalır).
Güvenlik: şifre kullanılmaz (yalnızca anahtar; özel anahtar bu klasörden çıkmaz), sunucu parmak izi ilk bağlantıda kaydedilir ve değişirse bağlantı REDDEDİLİR,
proxy yalnızca 127.0.0.1'de dinler, host/kullanıcı adları komut satırına girmeden önce sıkı doğrulanır. Çıkış gerçekten sunucudan mı yapılıyor diye her bağlantıda IP ve ülke ölçülür.
Veri: vpn_sunucular.json (sunucu listesi, gizli bilgi yok) ve vpn_anahtar/ (özel/açık anahtar, known_hosts). İkisi de yalnızca bu bilgisayarda kalır."""
import json
import os
import re
import secrets
import shutil
import socket
import ssl
import struct
import subprocess
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "vpn_sunucular.json")
KEYDIR = os.path.join(HERE, "vpn_anahtar")
KEY = os.path.join(KEYDIR, "jarvis_vpn_ed25519")
KNOWN = os.path.join(KEYDIR, "known_hosts")
BASE_PORT = 18081
IP_HOST, IP_PATH = "ipwho.is", "/"
COUNTRIES = {"US": "ABD", "DE": "Almanya", "NL": "Hollanda", "GB": "İngiltere", "FR": "Fransa", "JP": "Japonya", "CA": "Kanada", "SG": "Singapur", "CH": "İsviçre",
             "SE": "İsveç", "FI": "Finlandiya", "PL": "Polonya", "IT": "İtalya", "ES": "İspanya", "AU": "Avustralya", "BR": "Brezilya", "IN": "Hindistan", "KR": "Güney Kore",
             "AE": "Birleşik Arap Emirlikleri", "TR": "Türkiye", "IE": "İrlanda", "NO": "Norveç", "AT": "Avusturya", "BE": "Belçika", "CZ": "Çekya", "RO": "Romanya", "HK": "Hong Kong"}
_lock = threading.RLock()
S = {"state": "off", "id": None, "port": None, "proc": None, "err": "", "info": None, "since": 0.0, "direct": None, "stderr": [], "stop": threading.Event(), "tries": 0, "manual_off": True, "kill": False}
ON_CHANGE = None            # main.py: durum değişince çağrılır (tarayıcı yönlendirmesi ve arayüz güncellemesi)


# ------------------------------------------------------------------ doğrulama
HOST_RE = re.compile(r"^(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*|\d{1,3}(?:\.\d{1,3}){3})$")
USER_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")


def clean_server(d: dict):
    """Sayfadan ya da komuttan gelen sunucu bilgisini doğrular. (sunucu, hata) döner. Host ve kullanıcı komut satırına gireceği için '-' ile başlayamaz."""
    name = " ".join(str(d.get("name") or "").split())[:30]
    host = str(d.get("host") or "").strip()
    user = str(d.get("user") or "root").strip().lower()
    cc = str(d.get("cc") or "").strip().upper()
    try:
        port = 22 if d.get("port") in (None, "") else int(d.get("port"))
    except (TypeError, ValueError):
        return None, "Bağlantı noktası sayı olmalı."
    if not HOST_RE.match(host) or len(host) > 253:
        return None, "Sunucu adresi geçersiz (IP adresi ya da alan adı yazın)."
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host) and any(int(x) > 255 for x in host.split(".")):
        return None, "IP adresi geçersiz."
    if host.startswith(("127.", "0.", "169.254.")) or host.lower() == "localhost":
        return None, "Yerel adres sunucu olamaz."
    if not USER_RE.match(user):
        return None, "Kullanıcı adı geçersiz (küçük harf, rakam, _ ve - kullanın; genelde root)."
    if not 1 <= port <= 65535:
        return None, "Bağlantı noktası 1-65535 arasında olmalı."
    if not re.fullmatch(r"[A-Z]{2}", cc):
        return None, "Ülke kodu iki harf olmalı (ör. US)."
    return {"id": str(d.get("id") or "s" + secrets.token_hex(3)), "name": name or COUNTRIES.get(cc, cc), "host": host, "port": port, "user": user, "cc": cc}, None


def load() -> dict:
    try:
        with open(CFG, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            raise ValueError
    except (OSError, ValueError):
        d = {}
    servers = []
    for x in d.get("servers", []) if isinstance(d.get("servers"), list) else []:
        s, err = clean_server(x) if isinstance(x, dict) else (None, "x")
        if s and re.fullmatch(r"s[0-9a-f]{6}", s["id"]):
            servers.append(s)
    return {"servers": servers[:20], "active": d.get("active") if any(s["id"] == d.get("active") for s in servers) else None, "auto": bool(d.get("auto"))}


def save(d: dict) -> None:
    tmp = CFG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CFG)


def add_server(d: dict):
    s, err = clean_server({**d, "id": None})
    if err:
        return None, err
    cfg = load()
    if len(cfg["servers"]) >= 20:
        return None, "En fazla 20 sunucu eklenebilir."
    if any(x["host"] == s["host"] and x["port"] == s["port"] and x["user"] == s["user"] for x in cfg["servers"]):
        return None, "Bu sunucu zaten ekli."
    cfg["servers"].append(s)
    cfg["active"] = cfg["active"] or s["id"]
    save(cfg)
    return s, None


def remove_server(sid: str) -> bool:
    cfg = load()
    n = len(cfg["servers"])
    cfg["servers"] = [s for s in cfg["servers"] if s["id"] != sid]
    if len(cfg["servers"]) == n:
        return False
    if S["id"] == sid and S["state"] != "off":
        disconnect()
    if cfg["active"] == sid:
        cfg["active"] = cfg["servers"][0]["id"] if cfg["servers"] else None
    save(cfg)
    return True


def set_active(sid: str) -> bool:
    cfg = load()
    if any(s["id"] == sid for s in cfg["servers"]):
        cfg["active"] = sid
        save(cfg)
        return True
    return False


def find_server(cfg: dict, text: str):
    """Ad, ülke adı ya da ülke koduyla sunucu bul ('amerika', 'abd', 'us', 'almanya')."""
    q = str(text or "").replace("İ", "i").replace("I", "ı").lower().strip()
    alias = {"amerika": "US", "abd": "US", "birleşik devletler": "US", "us": "US", "usa": "US", "almanya": "DE", "hollanda": "NL", "ingiltere": "GB", "ingiltere ": "GB", "ngiltere": "GB",
             "fransa": "FR", "japonya": "JP", "kanada": "CA", "singapur": "SG", "isviçre": "CH", "i̇sviçre": "CH"}
    cc = alias.get(q) or (q.upper() if re.fullmatch(r"[a-z]{2}", q) else None)
    if cc:
        hit = [s for s in cfg["servers"] if s["cc"] == cc]
        if hit:
            return hit[0]
    low = lambda s: s.replace("İ", "i").replace("I", "ı").lower()
    if len(q) < 3:                                     # 'ya' gibi kısa parçalar ad içinde rastgele eşleşmesin
        return None
    hit = [s for s in cfg["servers"] if q in low(s["name"]) or q == low(COUNTRIES.get(s["cc"], ""))]
    return hit[0] if hit else None


# ------------------------------------------------------------------ anahtar
def find_tool(name: str):
    p = shutil.which(name)
    if p:
        return p
    for base in (r"C:\Program Files\Git\usr\bin", os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\usr\bin"), r"C:\Windows\System32\OpenSSH"):
        c = os.path.join(base, name + ".exe")
        if os.path.exists(c):
            return c
    return None


def ensure_key() -> str:
    """Anahtar çifti yoksa üretir (şifresiz ed25519: tüneli sesle açabilmek için; dosya yalnızca bu Windows kullanıcısına açıktır). Açık anahtarı döner."""
    if not os.path.exists(KEY):
        kg = find_tool("ssh-keygen")
        if not kg:
            raise RuntimeError("ssh-keygen bulunamadı (Git for Windows ya da Windows OpenSSH istemcisi gerekli)")
        os.makedirs(KEYDIR, exist_ok=True)
        r = subprocess.run([kg, "-t", "ed25519", "-N", "", "-C", "jarvis-vpn", "-q", "-f", KEY], capture_output=True, text=True, creationflags=0x08000000, timeout=30)
        if r.returncode != 0 or not os.path.exists(KEY):
            raise RuntimeError("anahtar üretilemedi: " + (r.stderr or "")[:120])
        _lock_down(KEY)
    return public_key()


def _lock_down(path: str) -> None:
    """Özel anahtara yalnızca bu kullanıcı erişsin (OpenSSH aksi hâlde anahtarı kullanmayı reddeder)."""
    try:
        user = os.environ.get("USERNAME") or ""
        if user:
            subprocess.run(["icacls", path, "/inheritance:r", "/grant:r", f"{user}:F"], capture_output=True, creationflags=0x08000000, timeout=15)
    except Exception:
        pass


def public_key() -> str:
    try:
        with open(KEY + ".pub", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


# ------------------------------------------------------------------ SOCKS5 istemcisi (yalnızca doğrulama için; dış paket yok)
def socks_get(port: int, host: str, path: str = "/", timeout: float = 15.0):
    """SOCKS5 proxy üzerinden https://host/path adresini okur. (durum kodu, gövde) döner; hata olursa istisna fırlatır."""
    s = socket.create_connection(("127.0.0.1", int(port)), timeout=timeout)
    try:
        s.settimeout(timeout)
        s.sendall(b"\x05\x01\x00")
        if s.recv(2) != b"\x05\x00":
            raise OSError("SOCKS5 el sıkışması başarısız")
        h = host.encode("idna")
        s.sendall(b"\x05\x01\x00\x03" + bytes([len(h)]) + h + struct.pack(">H", 443))
        r = s.recv(10)
        if len(r) < 2 or r[1] != 0:
            raise ConnectionError(f"proxy bağlanamadı (kod {r[1] if len(r) > 1 else '?'})")
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(s, server_hostname=host) as t:
            t.sendall(f"GET {path} HTTP/1.0\r\nHost: {host}\r\nUser-Agent: Jarvis-vpn-test\r\nAccept: application/json\r\nConnection: close\r\n\r\n".encode())
            buf = b""
            while len(buf) < 200000:
                c = t.recv(65536)
                if not c:
                    break
                buf += c
        head, _, body = buf.partition(b"\r\n\r\n")
        return int(head.split(b" ", 2)[1]), body
    finally:
        try:
            s.close()
        except OSError:
            pass


def _parse_ip(body: bytes):
    """ipwho.is ({'ip','country','country_code',...}) ya da yedek api.country.is ({'ip','country':'US'}) yanıtını okur."""
    try:
        j = json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        return None
    if not isinstance(j, dict) or j.get("success") is False or "ip" not in j:
        return None
    cc = str(j.get("country_code") or (j.get("country") if re.fullmatch(r"[A-Za-z]{2}", str(j.get("country") or "")) else "") or "")[:2].upper()
    name = str(j.get("country") or "")[:60]
    if re.fullmatch(r"[A-Za-z]{2}", name):
        name = COUNTRIES.get(name.upper(), name.upper())
    return {"ip": str(j["ip"])[:45], "country": name, "cc": cc, "city": str(j.get("city") or "")[:60], "isp": str((j.get("connection") or {}).get("isp") or "")[:80]}


IP_SERVICES = [("ipwho.is", "/"), ("api.country.is", "/")]


def tunnel_ip(port: int):
    last = None
    for host, path in IP_SERVICES:
        t = time.time()
        try:
            code, body = socks_get(port, host, path)
        except ConnectionError:
            raise                                       # proxy hedefe bağlanamadı: sunucu çıkış yapamıyor, yedek servis denemenin anlamı yok
        except Exception as e:
            last = e
            print(f"VPN: IP servisi {host} yanıt vermedi ({type(e).__name__}), yedeğe geçiliyor", flush=True)
            continue
        info = _parse_ip(body) if code == 200 else None
        if info:
            info["ms"] = int((time.time() - t) * 1000)
            return info
    if last:
        raise last
    return None


def direct_ip():
    """Tünelsiz (doğrudan) çıkış: gerçek ülkeniz."""
    import urllib.request
    for host, path in IP_SERVICES:
        try:
            with urllib.request.urlopen(urllib.request.Request(f"https://{host}{path}", headers={"User-Agent": "Jarvis-vpn-test"}), timeout=10) as r:
                info = _parse_ip(r.read(200000))
        except Exception:
            continue
        if info:
            S["direct"] = info
            return info
    return None


# ------------------------------------------------------------------ tünel
def _free_port(start: int = BASE_PORT) -> int:
    for p in range(start, start + 50):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise OSError("boş yerel port bulunamadı")


def _explain(err: str, srv: dict) -> str:
    e = err.lower()
    if "remote host identification has changed" in e or "host key verification failed" in e:
        return ("GÜVENLİK UYARISI: sunucunun parmak izi değişmiş. Sunucuyu siz yeniden kurmadıysanız birisi araya girmeye çalışıyor olabilir; bağlanmadım. "
                "Yeniden kurduysanız sunucu kartındaki 'parmak izini sıfırla' ile onaylayabilirsiniz.")
    if "permission denied" in e:
        return "Sunucu anahtarımızı kabul etmedi. Açık anahtarı sunucuda ~/.ssh/authorized_keys dosyasına eklediniz mi? Kullanıcı adı doğru mu?"
    if "timed out" in e or "no route" in e or "network is unreachable" in e:
        return "Sunucuya ulaşılamadı (zaman aşımı). IP adresi doğru mu, sunucu açık mı, güvenlik duvarı bağlantı noktasına izin veriyor mu?"
    if "connection refused" in e:
        return "Sunucu bağlantıyı reddetti: SSH çalışmıyor ya da bağlantı noktası yanlış."
    if "could not resolve" in e or "name or service not known" in e:
        return "Sunucu adresi çözülemedi. Adresi kontrol edin."
    if "address already in use" in e or "cannot listen" in e or "could not request local forwarding" in e:
        return "Yerel proxy portu kullanımda. Birkaç saniye sonra yeniden deneyin."
    if "administratively prohibited" in e or "forwarding" in e and "disabled" in e:
        return "Sunucu SSH tüneline izin vermiyor (AllowTcpForwarding kapalı)."
    if "connection closed" in e or "connection reset" in e:
        return "Sunucu bağlantıyı kapattı."
    return "Bağlantı kurulamadı: " + (err.strip().splitlines()[-1][:140] if err.strip() else "bilinmeyen hata")


def _kill_proc(p) -> None:
    if not p:
        return
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, creationflags=0x08000000, timeout=10)
    except Exception:
        pass
    try:
        p.kill()
    except Exception:
        pass


def _notify():
    cb = ON_CHANGE
    if cb:
        try:
            cb(status())
        except Exception as e:
            print("VPN bildirim hatası:", type(e).__name__, flush=True)


def _start_ssh(srv: dict, port: int):
    ssh = find_tool("ssh")
    if not ssh:
        raise RuntimeError("ssh bulunamadı (Git for Windows ya da Windows OpenSSH istemcisi gerekli)")
    ensure_key()
    cmd = [ssh, "-N", "-T", "-F", "/dev/null" if "Git" in ssh else "NUL", "-D", f"127.0.0.1:{port}", "-i", KEY, "-p", str(srv["port"]),
           "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "PasswordAuthentication=no", "-o", "ExitOnForwardFailure=yes",
           "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3", "-o", "ConnectTimeout=15", "-o", "StrictHostKeyChecking=accept-new",
           "-o", f"UserKnownHostsFile={KNOWN}", "-o", "LogLevel=ERROR", "-o", "ForwardAgent=no", "-o", "ForwardX11=no", "--", f"{srv['user']}@{srv['host']}"]
    p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", creationflags=0x08000000)
    lines = []
    S["stderr"] = lines

    def rd():
        try:
            for ln in p.stderr:
                lines.append(ln.rstrip()[:300])
                del lines[:-30]
        except Exception:
            pass
    threading.Thread(target=rd, daemon=True).start()
    return p


def _wait_socks(p, port: int, timeout: float = 30.0) -> bool:
    """Yerel proxy gerçekten SOCKS5 konuşana kadar bekler; ssh ölürse hemen False."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if p.poll() is not None:
            return False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1) as s:
                s.sendall(b"\x05\x01\x00")
                if s.recv(2) == b"\x05\x00":
                    return True
        except OSError:
            pass
        time.sleep(0.4)
    return False


def connect(sid=None) -> dict:
    """Tüneli açar (bloklar, birkaç saniye sürer: arka planda çağırın). Sonuç status() sözlüğü."""
    with _lock:
        if S["state"] in ("connecting", "on", "reconnecting"):
            if sid and sid != S["id"]:
                disconnect()
            else:
                return status()
        cfg = load()
        sid = sid or cfg["active"]
        srv = next((s for s in cfg["servers"] if s["id"] == sid), None)
        if not srv:
            S.update(state="off", err="Henüz sunucu eklenmemiş. VPN modunda sunucu ekleyin.")
            _notify()
            return status()
        S.update(state="connecting", id=srv["id"], err="", info=None, port=_free_port(), tries=0, manual_off=False, kill=False)
        S["stop"] = threading.Event()
    _notify()
    stop = S["stop"]
    ok = _bring_up(srv, stop)
    if ok:
        threading.Thread(target=_watchdog, args=(stop,), daemon=True).start()
    return status()


def _bring_up(srv: dict, stop: threading.Event) -> bool:
    port = S["port"]
    try:
        p = _start_ssh(srv, port)
    except Exception as e:
        S.update(state="off", err=str(e)[:200])
        _notify()
        return False
    S["proc"] = p
    if stop.is_set():                                   # bağlanırken kullanıcı VPN'i kapattı
        _kill_proc(p)
        return False
    if not _wait_socks(p, port):
        if stop.is_set():
            return False
        time.sleep(0.4)
        err = "\n".join(S["stderr"])
        _kill_proc(p)
        S.update(state="off", proc=None, err=_explain(err, srv))
        print("VPN: bağlanamadı:", err[-160:].replace("\n", " "), flush=True)
        _notify()
        return False
    try:
        info = tunnel_ip(port)
    except Exception as e:
        err = "\n".join(S["stderr"]) + " " + str(e)
        _kill_proc(p)
        S.update(state="off", proc=None, err="Sunucu tünel isteğimi reddetti: SSH tünellemeye (AllowTcpForwarding) izin vermiyor ya da internete çıkamıyor. sshd_config'de AllowTcpForwarding yes olmalı." if isinstance(e, ConnectionError) else
                 f"Tünel açıldı ama sunucu internete çıkaramadı ({type(e).__name__}). Sunucunun internet erişimini kontrol edin.")
        _notify()
        return False
    if not info:
        _kill_proc(p)
        S.update(state="off", proc=None, err="Tünel açıldı ama çıkış IP'si ölçülemedi (IP servisine ulaşılamadı).")
        _notify()
        return False
    if stop.is_set():
        _kill_proc(p)
        return False
    warn = ""
    if info["cc"] and info["cc"] != srv["cc"]:
        warn = f"Dikkat: sunucu {COUNTRIES.get(srv['cc'], srv['cc'])} olarak kayıtlı ama çıkış {info['country']} görünüyor."
    S.update(state="on", info=info, since=time.time(), err=warn)
    print(f"VPN: bağlandı ({srv['name']}, çıkış {info['country']})", flush=True)           # IP adresi günlüğe yazılmaz
    _notify()
    return True


def _watchdog(stop: threading.Event):
    """Her 10 sn tüneli yoklar. Koparsa aynı portta (tarayıcı kaçak yapmasın) 5 kez artan beklemeyle yeniden dener."""
    while not stop.wait(10):
        with _lock:
            if S["state"] not in ("on", "reconnecting") or stop.is_set():
                return
            p, port, sid = S["proc"], S["port"], S["id"]
        healthy = bool(p) and p.poll() is None
        if healthy:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=3) as s:
                    s.sendall(b"\x05\x01\x00")
                    healthy = s.recv(2) == b"\x05\x00"
            except OSError:
                healthy = False
        if healthy:
            continue
        srv = next((s for s in load()["servers"] if s["id"] == sid), None)
        _kill_proc(p)
        for k in range(1, 6):
            if stop.is_set() or not srv:
                return
            S.update(state="reconnecting", err=f"Bağlantı koptu, yeniden deneniyor ({k}/5)…", tries=k)
            _notify()
            if stop.wait(3 * k):
                return
            if stop.is_set():
                return
            if _bring_up(srv, stop):
                break
        else:
            S.update(state="off", proc=None, kill=True, err="Bağlantı koptu ve yeniden kurulamadı. Tarayıcı güvenlik için internete çıkmaz (gerçek IP'niz sızmaz); VPN'i yeniden açın ya da 'VPN kapat' diyerek doğrudan bağlantıya dönün.")
            _notify()
            return


def disconnect() -> bool:
    """Tüneli kapatır. Tarayıcı doğrudan (Türkiye) bağlantıya döner."""
    with _lock:
        was = S["state"] != "off"
        S["stop"].set()
        _kill_proc(S["proc"])
        S.update(state="off", proc=None, info=None, err="", port=None, since=0.0, manual_off=True, kill=False)
    if was:
        print("VPN: kapatıldı", flush=True)
    _notify()
    return was


def forget_host(sid: str) -> bool:
    """Parmak izi değişmiş sunucuyu bilerek (kullanıcı onayıyla) yeniden onaylamak için kayıttan siler."""
    srv = next((s for s in load()["servers"] if s["id"] == sid), None)
    kg = find_tool("ssh-keygen")
    if not srv or not kg or not os.path.exists(KNOWN):
        return False
    target = srv["host"] if srv["port"] == 22 else f"[{srv['host']}]:{srv['port']}"
    r = subprocess.run([kg, "-R", target, "-f", KNOWN], capture_output=True, text=True, creationflags=0x08000000, timeout=15)
    return r.returncode == 0


def fingerprint(sid: str) -> str:
    """Sunucunun kayıtlı parmak izi (ilk bağlantıda kaydedilir); sunucu sağlayıcınızın panelindekiyle karşılaştırabilirsiniz. Yoksa ''."""
    srv = next((s for s in load()["servers"] if s["id"] == sid), None)
    kg = find_tool("ssh-keygen")
    if not srv or not kg or not os.path.exists(KNOWN):
        return ""
    target = srv["host"] if srv["port"] == 22 else f"[{srv['host']}]:{srv['port']}"
    r = subprocess.run([kg, "-l", "-F", target, "-f", KNOWN], capture_output=True, text=True, creationflags=0x08000000, timeout=15)
    for ln in (r.stdout or "").splitlines():                  # '[host]:port ED25519 SHA256:...'
        parts = ln.split()
        if ln and not ln.startswith("#") and len(parts) >= 3 and parts[2].startswith("SHA256:"):
            return f"{parts[2]} ({parts[1]})"
    return ""


def status() -> dict:
    cfg = load()
    srv = next((s for s in cfg["servers"] if s["id"] == (S["id"] if S["state"] != "off" else cfg["active"])), None)
    live = S["state"] in ("on", "reconnecting", "connecting") or S["kill"]
    return {"state": S["state"], "server": srv, "port": S["port"] if live else None, "info": S["info"], "since": S["since"], "err": S["err"],
            "direct": S["direct"], "tries": S["tries"], "manual": S["manual_off"], "kill": S["kill"]}


def view() -> dict:
    cfg = load()
    st = status()
    return {"status": st, "servers": [{**s, "fp": fingerprint(s["id"])} for s in cfg["servers"]], "active": cfg["active"], "auto": cfg["auto"], "pub": public_key(), "countries": COUNTRIES,
            "ssh": bool(find_tool("ssh")), "keygen": bool(find_tool("ssh-keygen"))}
