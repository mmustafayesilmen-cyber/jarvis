"""Derin odak modu komutları: 'başlat', '45 dakika', 'evet' (listelenen pencereleri kapat ve başla), 'sadece küçült', 'kapatmadan başla', 'listeyi yenile', 'duraklat', 'devam', 'ne kadar kaldı',
'odak süresi 60 dakika olsun', 'bitir'. Pencereler zorla değil nazikçe kapatılır; liste her zaman önce gösterilir ve onay ister."""
import re

import odak as O
import scenes
from scenes_mola import minutes_in


def _res(say: str, listing: bool = False, **extra):
    return {"do": {"snap": O.snapshot(listing), "msg": say, **extra}, "say": say}


def odak(text: str, st: dict):
    t = scenes.norm(text)
    if not t:
        return None
    n = minutes_in(t)
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Önce açık pencereleri listelerim. Evet derseniz kapatıp başlarım, sadece küçült derseniz küçültürüm, kapatmadan başla derseniz dokunmam. Kırk beş dakika gibi bir süre de söyleyebilirsiniz."}
    if re.search(r"\b(süre\w*|varsayılan)\b", t) and re.search(r"\b(olsun|yap|ayarla|değiştir|kaydet)\w*", t) and n:
        return _res(f"Varsayılan odak süresi {O.set_default(n)} dakika oldu efendim.")
    if re.search(r"\b(bitir|iptal|vazgeç|çalışmayı bitir)\w*", t):
        O.end()
        return _res("Odak modunu bitirdim efendim.", True)
    if re.search(r"\b(duraklat|durdur|beklet)\w*", t):
        return _res("Odak duraklatıldı efendim." if O.pause() else "Duraklatılacak bir odak yok efendim.")
    if re.search(r"\b(devam|sürdür)\w*", t) and O.S["on"]:
        return _res("Odak devam ediyor efendim." if O.resume() else "Duraklatılmış bir odak yok efendim.")
    if re.search(r"\b(kalan|ne kadar|kaç dakika)\b", t) and not n:
        s = int(O.remaining())
        return {"say": f"Odağınızın bitmesine {s // 60} dakika var efendim." if O.S["on"] else "Odak çalışmıyor efendim."}
    if re.search(r"\b(listeyi yenile|yenile|pencereleri (göster|listele)|hangi pencereler)\w*", t):
        ws = O.windows()
        return _res(f"{len(ws)} açık pencere var efendim." if ws else "Kapatılacak açık pencere yok efendim.", True)
    if n:
        st["odak_n"] = n
    n = n or st.get("odak_n")
    wl = {w["hwnd"] for w in O.windows()}
    sel = [h for h in st.get("odak_sel", []) if h in wl] if st.get("odak_sel") else sorted(wl)
    if re.search(r"\b(sadece küçült|yalnızca küçült|küçült)\w*", t):
        k = O.act(sel, "min")
        m = O.start(n)
        return _res(f"{k} pencereyi küçülttüm, {m} dakikalık odak başladı efendim. Bol şans.", True)
    if re.search(r"\b(kapatmadan|dokunma|olduğu gibi|listesiz)\b", t):
        m = O.start(n)
        return _res(f"Pencerelere dokunmadan {m} dakikalık odak başladı efendim.", True)
    if re.fullmatch(r"(evet|onaylıyorum|tamam|kapat|kapat ve başla|evet kapat|olur)", t) or re.search(r"\b(kapat ve başla|kapatıp başla|hepsini kapat)\b", t):
        k = O.act(sel, "close")
        m = O.start(n)
        return _res(f"{k} pencereye kapat iletisi gönderdim; kaydedilmemiş işi olanlar size soracak. {m} dakikalık odak başladı efendim.", True)
    if re.search(r"\b(başlat|başla|kur|ver)\w*", t) or n:
        ws = O.windows()
        return _res((f"{len(ws)} açık pencere var efendim. Hepsini kapatıp başlamamı onaylıyor musunuz? Evet, sadece küçült ya da kapatmadan başla diyebilirsiniz."
                     if ws else "Kapatılacak pencere yok efendim."), True, pending=(n or O.default_len()))
    return {"say": "Anlayamadım efendim. Başlat, evet, sadece küçült, kapatmadan başla ya da bitir diyebilirsiniz."}


def init_payload():
    return O.snapshot(True)
