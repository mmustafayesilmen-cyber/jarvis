"""Android telefonu USB kablosuyla Jarvis'e bağlar.

Güvenlik: `adb reverse` telefonun 127.0.0.1:8765 adresini YALNIZCA USB kablosu üzerinden bilgisayardaki Jarvis'e
yönlendirir. Wi-Fi'ye / ağa hiçbir port açılmaz; sunucu hâlâ yalnızca 127.0.0.1'i dinler. Arayüz adresi her açılışta
değişen gizli anahtarı içerir ve telefona doğrudan adb üzerinden verilir.
"""
import os, shutil, subprocess

PORT = 8765
URL = ""          # main.py tarafından ayarlanır: http://127.0.0.1:8765/?t=<anahtar>
MIRROR_URL = ""   # ... /mirror?t=<anahtar>: bilgisayar ekranını yansıtan ve Jarvis'i yöneten telefon sayfası


def _adb() -> str | None:
    for p in (shutil.which("adb"),
              os.path.expandvars(r"%LocalAppData%\Android\Sdk\platform-tools\adb.exe"),
              os.path.expandvars(r"%ProgramFiles%\Android\platform-tools\adb.exe")):
        if p and os.path.exists(p):
            return p
    return None


def _run(*args, timeout=20) -> subprocess.CompletedProcess:
    return subprocess.run([_adb(), *args], capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace", creationflags=0x08000000)


def connect(lang: str = "tr", mirror: bool = False) -> str:
    """Telefonu USB tüneliyle bağlar ve Jarvis sayfasını telefonda açar. mirror=True: ekran yansıtma sayfası açılır."""
    tr = lang != "en"
    if not _adb():
        return ("Telefon bağlantısı için adb bulunamadı efendim." if tr else "I couldn't find adb, sir.")
    devices = [l.split()[0] for l in _run("devices").stdout.splitlines()[1:] if l.strip().endswith("device")]
    if not devices:
        return ("Bağlı bir Android telefon göremiyorum efendim. Kabloyu takın, telefonda USB hata ayıklamayı açın "
                "ve çıkan izni onaylayın." if tr else
                "I can't see a connected Android phone, sir. Plug in the cable and enable USB debugging.")
    serial = devices[0]
    r = _run("-s", serial, "reverse", f"tcp:{PORT}", f"tcp:{PORT}")
    if r.returncode != 0:
        return (f"Telefona bağlanamadım efendim: {r.stderr.strip()[:80]}" if tr else "I couldn't connect to the phone, sir.")
    # adb shell komutu telefonda kabukta çalışır: '&' karakteri bozmasın diye adres tek tırnak içinde
    _run("-s", serial, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", f"'{(MIRROR_URL if mirror and MIRROR_URL else URL)}&remote=1'")
    if mirror:
        return ("Ekranı telefona yansıtıyorum efendim. Telefonda Jarvis ekran sayfası açıldı; kablo takılı olduğu sürece görürsünüz."
                if tr else "I'm mirroring the screen to your phone, sir.")
    return ("Telefon kabloyla bağlandı efendim, Jarvis ekranı telefonda açıldı." if tr else
            "Your phone is connected by cable, sir. Jarvis is now open on it.")


def _device():
    """(seri_no, durum): bağlı ve izinli telefon varsa seri no; yoksa (None, açıklama)."""
    if not _adb():
        return None, "adb bulunamadı"
    rows = [l.split() for l in _run("devices").stdout.splitlines()[1:] if l.strip()]
    ok = [r[0] for r in rows if len(r) > 1 and r[1] == "device"]
    if ok:
        return ok[0], ""
    if any(len(r) > 1 and r[1] == "unauthorized" for r in rows):
        return None, "izin"
    return None, "yok"


def wake(on: bool = True) -> str:
    """'Telefonumu aç': kablolu telefonun ekranını yakar ve kilit ekranını kaldırır. PIN/desen/parmak izi AŞILMAZ:
    güvenli bir kilit varsa yalnızca kilit ekranı görünür, açmak sizin işiniz. on=False ekranı söndürür."""
    serial, why = _device()
    if not serial:
        if why == "izin":
            return "Telefon bağlı ama izin vermemiş efendim. Telefonun ekranında çıkan USB hata ayıklama iznini onaylayın."
        if why == "adb bulunamadı":
            return "Telefona ulaşmak için gereken adb aracını bulamadım efendim."
        return ("Telefonu göremiyorum efendim. Kabloyla bilgisayara takın, telefonda USB hata ayıklamanın açık olduğundan emin olun, "
                "sonra tekrar söyleyin.")
    if not on:
        _run("-s", serial, "shell", "input", "keyevent", "KEYCODE_SLEEP")
        return "Telefonun ekranını kapattım efendim."
    _run("-s", serial, "shell", "input", "keyevent", "KEYCODE_WAKEUP")
    _run("-s", serial, "shell", "wm", "dismiss-keyguard")          # güvenli kilidi atlamaz; kilit yoksa kilit ekranını kaldırır
    locked = "mShowingLockscreen=true" in _run("-s", serial, "shell", "dumpsys", "window").stdout.replace(" ", "") or              "isStatusBarKeyguard=true" in _run("-s", serial, "shell", "dumpsys", "window").stdout
    return ("Telefonun ekranını açtım efendim. Kilit ekranında kaldı, kilidi sizin açmanız gerekiyor." if locked
            else "Telefonu açtım efendim, ekranı yanıyor.")


def disconnect() -> str:
    if _adb():
        _run("reverse", "--remove-all")
    return "Telefon bağlantısı kesildi efendim."
