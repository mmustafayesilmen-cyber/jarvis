"""Telefon modu: açılınca uzaktan erişim (remote.py) kendiliğinden başlar; ekranda adres, QR kod, eşleştirme kodu ve kalan süre görünür.
Mod kapanınca (çık / pencere kapanışı) tünel ve sunucu da kapanır. Komutlar: 'yeni link' (tüneli yeniler), 'eşleştir', 'eşleşmeleri sil', 'durum'."""
import re
import time

import scenes

S = {"starting": False, "err": "", "code": ""}


def _matrix(url: str):
    try:
        import qrcode
        q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
        q.add_data(url)
        q.make(fit=True)
        return ["".join("1" if c else "0" for c in row) for row in q.get_matrix()]
    except Exception as e:
        print("QR hatası:", type(e).__name__, flush=True)
        return None


def view() -> dict:
    import remote
    u = remote.login_url()                       # QR/adres tek kullanımlık giriş anahtarını taşır: okutan telefon kod yazmadan eşleşir
    return {"on": remote.S["on"], "starting": S["starting"], "err": S["err"], "url": u, "qr": _matrix(u) if u else None,
            "ts": remote.ts_url(), "paired": remote.paired_count(), "left": int(max(0, remote.S["until"] - time.time())) if remote.S["on"] else 0,
            "pairing": time.time() < remote._pair["until"], "code": S["code"] if time.time() < remote._pair["until"] else "",
            "modes": [remote.NAMES[k] for k in remote.WHITELIST]}


def init_payload() -> dict:
    S.update(err="", code="")
    return view()


def telefon(text: str, st: dict):
    import remote
    t = scenes.norm(text)
    if not t:
        return None
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Yeni link, eşleştir, eşleşmeleri sil, durum ve çık diyebilirsiniz. Telefon yalnızca uyku, tarif, spor ve panel modlarını açabilir."}
    if re.search(r"\b(sil|kaldır|unut|sıfırla)\w*", t) and re.search(r"eşleşme\w*", t):
        n = remote.revoke_all()
        return {"do": {"data": view()}, "say": f"{n} telefon eşleşmesini sildim efendim." if n else "Kayıtlı bir telefon eşleşmesi yok efendim."}
    if re.search(r"eşleştir\w*|eşleşelim|yeni telefon", t):
        if not remote.S["on"]:
            return {"say": "Bağlantı henüz kurulmadı efendim."}
        remote.arm_pair()
        return {"do": {"data": view()}, "say": "Eşleştirme üç dakika açık efendim. Telefonda KOD İSTE'ye basın, kodu ekranda göstereceğim."}
    if re.search(r"\b(yeni link|yeniden başlat|linki yenile|yenile|tekrar bağlan)\w*", t):
        return {"later": _restart, "do": {"data": {**view(), "starting": True}}, "say": "Bağlantıyı yeniliyorum efendim."}
    if re.search(r"\b(durum\w*|ne kadar kaldı|açık mı)\b", t):
        v = view()
        return {"say": (f"Bağlantı açık efendim, {v['left'] // 60} dakika sonra kapanacak. {v['paired']} telefon eşleşmiş." if v["on"] else "Bağlantı şu an kapalı efendim.")}
    return {"do": {"data": view()}, "say": ""}


def _restart():
    import remote
    remote.stop()
    S["starting"] = True
    r = remote.start()
    S["starting"] = False
    S["err"] = "" if r == "ok" else r
    if r == "ok" and not remote.paired_count():
        remote.arm_pair()
    return {"do": {"data": view()}, "say": "Yeni bağlantı hazır efendim." if r == "ok" else r}
