"""Uzaktan erişimi otomatik açık tutma (isteğe bağlı, varsayılan KAPALI): Jarvis açılınca tünel kurulur, adres değiştikçe linki kullanıcının KENDİ WhatsApp numarasına gönderir.
Açma/kapama yalnızca sesle ('uzaktan erişimi otomatik aç/kapat') ya da config.json: uzak_otomatik. Alıcı numara YALNIZCA config.json: uzak_wa_no'dan okunur (ses/sayfa/telefon değiştiremez);
yoksa link gönderilmez, yalnızca ekranda/bildirimde gösterilir. Gönderim whatsapp.send_report ile yapılır (alıcı başlıkta doğrulanır, doğrulanamazsa hiçbir şey yazılmaz).
Güvenlik: erişim açık kalsa da telefon eşleşmeden giremez; eşleştirme yalnızca hiç eşleşmiş telefon yokken ya da 'telefonu eşleştir' deyince açılır. Link flaşı: en çok günde 6 gönderim, en az 5 dk arayla."""
import re
import threading
import time

import remote
import settings

_state = {"thread": None, "sent_host": "", "sent_t": [], "stop": False}
HOOKS = {"say": None, "notify": None}


def enabled() -> bool:
    return bool(settings.get("uzak_otomatik"))


def number() -> str:
    return re.sub(r"\D", "", str(settings.get("uzak_wa_no") or ""))


def _wait_idle(max_s: int = 60) -> None:
    """Klavye/fareye dokunulmuyorsa hemen, kullanılıyorsa en çok max_s sn bekleyip gönderir (WhatsApp otomasyonu odağı birkaç saniye alır)."""
    try:
        import usage
        t0 = time.time()
        while usage.idle_seconds() < 10 and time.time() - t0 < max_s:
            time.sleep(2)
    except Exception:
        pass


def send_link(url: str) -> str:
    now = time.time()
    _state["sent_t"] = [t for t in _state["sent_t"] if now - t < 86400]
    if not number():
        return "no-number"
    if len(_state["sent_t"]) >= 6 or (_state["sent_t"] and now - _state["sent_t"][-1] < 300):
        return "rate-limit"
    _wait_idle()
    import whatsapp
    r = whatsapp.send_report(number(), "Jarvis uzaktan erişim linki: " + url, "")
    if r in ("sent", "unverified"):
        _state["sent_t"].append(now)
    return r


def _loop():
    while enabled() and not _state["stop"]:
        try:
            if not remote.S["on"]:
                r = remote.start(auto=True)
                if r == "ok":
                    if not remote.paired_count():
                        remote.arm_pair()
                else:
                    time.sleep(60)
                    continue
            host = remote.S["host"]
            if host and host != _state["sent_host"]:
                u = remote.login_url()                 # '#k=' tek kullanımlık anahtarı taşır: eşleşmiş telefon yeni adreste kod yazmadan girer
                if HOOKS["notify"]:
                    HOOKS["notify"](u)
                res = send_link(u)
                if res in ("sent", "unverified"):
                    _state["sent_host"] = host
                    if HOOKS["say"]:
                        HOOKS["say"]("Uzaktan erişim linkini WhatsApp'tan gönderdim efendim." if res == "sent" else "Linki gönderdim ama doğrulayamadım efendim, WhatsApp'a bakın.")
                elif res == "no-number":
                    _state["sent_host"] = host
                    if HOOKS["say"]:
                        HOOKS["say"]("Uzaktan erişim açık ama link göndermek için config dosyasına uzak_wa_no numarası yazılmamış efendim; adres ekranda.")
                elif res == "rate-limit":
                    pass
                else:
                    _state["sent_host"] = host
                    if HOOKS["say"]:
                        HOOKS["say"]("Linki WhatsApp'tan gönderemedim efendim, adres ekranda.")
        except Exception as e:
            print("uzak otomatik hatası:", type(e).__name__, flush=True)
        time.sleep(15)


def start_loop() -> None:
    with remote._lock:
        t = _state["thread"]
        if t and t.is_alive():
            return
        _state["stop"] = False
        _state["thread"] = threading.Thread(target=_loop, daemon=True)
        _state["thread"].start()


def set_enabled(on: bool) -> None:
    settings.set("uzak_otomatik", bool(on))
    if on:
        start_loop()
    else:
        _state["stop"] = True
        remote.stop()
        _state["sent_host"] = ""
