"""Jarvis tarayıcısını (jbrowser_proc.py, ayrı süreç) yöneten ana-süreç tarafı. 'YouTube aç', 'site aç', 'google'da ara' komutları açıldığında bu pencere kullanılır.
VPN açıkken pencere o ülkenin sunucusundan çıkar (proxy 127.0.0.1:port), VPN kapanınca ya da değişince pencere yeni ayarla yeniden açılır ve aynı sayfaya döner.
Güvenlik: yalnızca http/https adresleri gönderilir; proxy yalnızca 127.0.0.1'e verilir; komutlar süreçle stdin üzerinden (satır başına JSON) konuşulur."""
import json
import os
import re
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROC = os.path.join(HERE, "jbrowser_proc.py")
TITLE = "JARVIS TARAYICI"
_lock = threading.RLock()
S = {"p": None, "proxy": "", "badge": "", "badge_ok": False, "url": "", "last_open": 0.0, "cdp": 0, "phone": False}
FOCUS = None            # main.py: pencere başlığına odak veren işlev (focus_window)
CC_NAMES = {"US": "ABD", "DE": "Almanya", "NL": "Hollanda", "GB": "İngiltere", "FR": "Fransa", "JP": "Japonya", "CA": "Kanada", "SG": "Singapur", "TR": "Türkiye"}


def safe_url(u: str) -> bool:
    return bool(re.match(r"^https?://[^\s]+$", str(u))) and len(str(u)) < 2000


def alive() -> bool:
    p = S["p"]
    return bool(p and p.poll() is None)


def media():
    """Jarvis tarayıcısında şu an çalan medya ({'title','artist','pos','dur'}) ya da None. Konum, son bildirimden bu yana geçen süreyle ilerletilir."""
    m = S.get("media")
    if not m or not alive() or time.time() - m["ts"] > 2.5:
        return None
    return dict(m, pos=min(m["dur"] or 1e9, m["pos"] + (time.time() - m["ts"])))


def _py() -> str:
    return sys.executable.replace("pythonw", "python")


def _reader(p):
    try:
        for line in p.stdout:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("ev") == "loaded" and safe_url(e.get("url", "")):
                S["url"] = e["url"]
            elif e.get("ev") == "media":
                S["media"] = {"title": str(e.get("title") or ""), "artist": str(e.get("artist") or ""), "pos": float(e.get("pos") or 0),
                              "dur": float(e.get("dur") or 0), "ts": time.time()}
            elif e.get("ev") == "adblock":
                S["blocked"] = int(e.get("n") or 0)
            elif e.get("ev") == "error":
                print("TARAYICI hata:", str(e.get("msg"))[:80], flush=True)
    except Exception:
        pass


def _spawn(url: str, cdp: int = 0, bg: bool = False):
    import settings
    cmd = [_py(), PROC, "--url", url if safe_url(url) else "about:blank", "--proxy", S["proxy"], "--badge", S["badge"], "--badge-ok", "1" if S["badge_ok"] else "0",
           "--gpu", {True: "1", False: "0"}.get(settings.get("tarayici_gpu"), "2"),      # ayar yoksa "2": GPU açık ama GPU birleştirme kapalı (siyah ekranı önler)
           "--adblock", "0" if settings.get("reklam_engel") is False else "1"]            # varsayılan açık
    if cdp:
        cmd += ["--cdp", str(int(cdp)), "--bg", "1" if bg else "0"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1,
                         creationflags=0x08000000, cwd=HERE)
    S["p"], S["cdp"] = p, int(cdp or 0)
    threading.Thread(target=_reader, args=(p,), daemon=True).start()
    print(f"TARAYICI: açıldı ({'proxy ' + S['proxy'] if S['proxy'] else 'doğrudan'})", flush=True)


def _send(o: dict) -> bool:
    p = S["p"]
    if not alive():
        return False
    try:
        p.stdin.write(json.dumps(o, ensure_ascii=False) + "\n")
        p.stdin.flush()
        return True
    except (OSError, ValueError):
        return False


def open_url(url: str) -> bool:
    """Adresi Jarvis tarayıcısında açar (pencere yoksa açar). Geçersiz adres False döner."""
    if not safe_url(url):
        return False
    with _lock:
        S["url"] = url
        if alive() and _send({"cmd": "goto", "url": url}):
            pass
        else:
            _spawn(url)
        S["last_open"] = time.time()
    if FOCUS:
        threading.Thread(target=lambda: (time.sleep(1.5), FOCUS(TITLE)), daemon=True).start()
    return True


def open_start() -> bool:
    """Tarayıcıyı başlangıç sayfasıyla açar (jb_theme.start_html: saat, arama, hızlı erişim kutuları). Pencere açıksa yeni sekmede gösterir."""
    with _lock:
        if alive() and _send({"cmd": "newtab", "url": ""}):
            pass
        else:
            _spawn("about:blank")              # 'about:blank' ile açılış = başlangıç sayfası (jbrowser_proc)
        S["url"] = ""
        S["last_open"] = time.time()
    if FOCUS:
        threading.Thread(target=lambda: (time.sleep(1.5), FOCUS(TITLE)), daemon=True).start()
    return True


def new_tab(url: str = "https://www.google.com/") -> bool:
    """Yeni sekme (aynı süreçte yeni pencere) açar; tarayıcı kapalıysa onu açar."""
    if not safe_url(url):
        return False
    with _lock:
        if alive() and _send({"cmd": "newtab", "url": url}):
            S["url"] = url
        else:
            _spawn(url)
            S["url"] = url
    return True


def set_route(proxy_port=None, badge: str = "", ok: bool = False):
    """VPN durumu değişti: proxy (None = doğrudan) ve rozet metni. Pencere açıksa yeni ayarla yeniden açılır, aynı sayfaya döner."""
    proxy = f"127.0.0.1:{int(proxy_port)}" if proxy_port else ""
    with _lock:
        changed = proxy != S["proxy"]
        S["proxy"], S["badge"], S["badge_ok"] = proxy, badge, ok
        if not alive():
            return
        if changed:
            url = S["url"]
            _send({"cmd": "close"})
            try:
                S["p"].wait(timeout=4)
            except Exception:
                try:
                    S["p"].kill()
                except Exception:
                    pass
            _spawn(url if safe_url(url) else "about:blank", cdp=S["cdp"])
            if FOCUS:
                threading.Thread(target=lambda: (time.sleep(1.5), FOCUS(TITLE)), daemon=True).start()
        else:
            _send({"cmd": "badge", "text": badge, "ok": ok})


def set_adblock(on: bool) -> bool:
    """Reklam engelleyiciyi açar/kapatır (kalıcı ayar; pencere açıksa anında uygulanır, sayfa yenilenince etkisi görülür)."""
    import settings
    settings.set("reklam_engel", bool(on))
    return _send({"cmd": "adblock", "on": bool(on)})


def set_look(tema=None, ses=None) -> bool:
    """Tarayıcı görünümü: tema adı (jb_theme.THEMES) ve/veya tıklama-yazma sesleri. Kalıcıdır; pencere açıksa anında uygulanır."""
    import settings
    if tema is not None:
        settings.set("tarayici_tema", tema)
    if ses is not None:
        settings.set("tarayici_ses", bool(ses))
    return _send({"cmd": "look"})


def cmd(name: str, **kw) -> bool:
    if name not in ("back", "forward", "reload", "fullscreen", "scroll", "close", "newtab", "closetab", "nexttab", "prevtab"):
        return False
    ok = _send({"cmd": name, **kw})
    if name == "close":
        close()
    return ok


def close():
    with _lock:
        if alive():
            _send({"cmd": "close"})
            try:
                S["p"].wait(timeout=4)
            except Exception:
                try:
                    S["p"].kill()
                except Exception:
                    pass
        S["p"], S["cdp"], S["phone"] = None, 0, False


def phone_open() -> int:
    """Telefondan uzaktan erişim: Jarvis tarayıcısını yalnızca 127.0.0.1'de hata ayıklama portuyla açar ve portu döner. Tarayıcı kapalıysa arka planda (küçültülmüş) açılır;
    açıksa aynı sayfaya dönerek bu portla yeniden başlar. Telefon bırakılınca phone_release() portu kapatır."""
    import socket
    with _lock:
        if alive() and S["cdp"]:
            return S["cdp"]
        was = alive()
        url = S["url"] if safe_url(S["url"]) else "about:blank"
        if was:
            _send({"cmd": "close"})
            try:
                S["p"].wait(timeout=4)
            except Exception:
                try:
                    S["p"].kill()
                except Exception:
                    pass
        sk = socket.socket()
        sk.bind(("127.0.0.1", 0))
        port = sk.getsockname()[1]
        sk.close()
        _spawn(url, cdp=port, bg=not was)
        S["phone"] = not was
        return port


def phone_release() -> None:
    """Telefon ayrıldı: telefon için açılan tarayıcı kapanır; kullanıcının açık tuttuğu tarayıcı aynı sayfaya dönerek hata ayıklama portu olmadan yeniden açılır."""
    with _lock:
        if not S["cdp"]:
            return
        mine, url = S["phone"], S["url"]
        close()
        if not mine:
            _spawn(url if safe_url(url) else "about:blank")


def status() -> dict:
    return {"open": alive(), "proxy": S["proxy"], "url": S["url"]}
