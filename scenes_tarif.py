"""Tarif modu komutları: 'menemen tarifi', 'malzemeler', 'başla', 'sonraki', 'önceki', 'tekrar', 'adım üç', 'sayaç kur', 'tatlı tarifleri', 'yumurtalı tarif'.
Jarvis adımları sesli okur; elleriniz meşgulken yalnızca 'sonraki' demeniz yeterli."""
import re

import scenes
import tarif as T

_STOP = {"tarif", "tarifi", "tarifini", "tarifler", "tarifleri", "göster", "aç", "bul", "var", "mı", "mi", "neler", "ne", "yapalım", "yapacağım", "nasıl", "yapılır", "öner"}


_TM = r"\b(t?h?erm[oa] ?mi[kx]s?\w*|tm ?[567])\b"
_TM_OFF = r"\b(ocakta|normal tarif\w*|ocak sürüm\w*|makinesiz|thermomixsiz|termomikssiz)\b|\b(kapat|olmadan|istemiyorum)\w*"


_WEB_STOP = r"\b(tarif\w*|internet\w*|ara|arar|arasana|bul|bulur|getir|göster|aç|nasıl|yapılır|yapılışı|yapımı|yapacağım|yapabilirim|yaparım|ver|oku|söyle|bana|ben|lütfen|istiyorum|olan|mı|mi)\b"


def _web_query(t: str) -> str:
    """'fırında patatesli tavuk tarifi' -> 'fırında patatesli tavuk'. Tarif/nasıl yapılır istenmiyorsa ya da kategori adıysa ('tatlı tarifi') boş."""
    if not re.search(r"\btarif\w*|nasıl yapılır|yapılışı|yapımı|internet\w*", t) or re.search(r"\btarifler\w*|\b(elimde|evde)\b", t):
        return ""
    q = " ".join(re.sub(_WEB_STOP, " ", t).split())
    if len(q) < 3 or (len(q.split()) == 1 and any(q[:5] == c.split()[0][:5] for c in T.CATS)):
        return ""
    return q


def _step_say(r, i):
    a = r["adim"][i]
    t, dk = a[0], a[1]
    tm = T.tm_text(a[2]) if len(a) > 2 else ""
    tail = f" Bu adım yaklaşık {dk} dakika sürüyor, sayaç kurmamı ister misiniz?" if dk >= 3 else ""
    return f"Adım {i + 1} / {len(r['adim'])}: {t}" + (f" Thermomix: {tm}." if tm else "") + tail


def _tm_cmd(t: str, cur):
    """'Thermomix tarifleri' / 'Thermomix ile yap' / 'ocakta yap'. Cümlede ayrıca bir tarif adı varsa None (tarif açılırken ayar uygulanır)."""
    off = bool(re.search(_TM_OFF, t))
    rest = re.sub(_TM, " ", t)
    if T.find(rest):
        T.S["tm"] = not off
        return None
    if cur and not cur.get("tmonly"):
        if not T.BY_ID[cur["id"]].get("tmv"):
            return {"say": f"{cur['ad']} için Thermomix sürümü yok efendim; ocakta yapılır."}
        T.S.update(tm=not off, step=-1, kisi=0)
        return {"do": {"step": -1}, "say": f"{cur['ad']} {'ocak' if off else 'Thermomix'} sürümüne geçtim efendim. Malzemeler değişti; başla derseniz adımları okurum."}
    T.S["tm"] = not off
    if off:
        return {"do": {"list": True}, "say": "Thermomix kapalı, tarifler ocak sürümüyle açılacak efendim."}
    ids = [r["id"] for r in T.R if T.has_tm(r)]
    T.S.update(id=None, step=-1)
    return {"do": {"filter": ids}, "say": f"{len(ids)} Thermomix tarifi var efendim. Örneğin " + ", ".join(T.BY_ID[i]["ad"] for i in ids[-4:]) + ". Hangisini açayım?"}


def _tarif(text: str, st: dict):
    t = scenes.norm(text)
    if not t:
        return None
    cur = T.cur()
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Bir yemek adı ve tarifi deyin, örneğin menemen tarifi. Malzemeler, başla, sonraki, önceki, tekrar, adım üç ve sayaç kur diyebilirsiniz. Tatlı tarifleri ya da yumurtalı tarif gibi aramalar da yapabilirim. "
                       "Thermomix tarifleri derseniz Thermomix ayarlı tarifleri gösteririm; bir tarifte Thermomix ile ya da ocakta yap diyerek sürümünü değiştirebilirsiniz."}
    if re.search(_TM, t) or re.search(r"\b(ocakta|makinesiz|thermomixsiz|termomikssiz|normal tarif\w*|ocak sürüm\w*)\b", t):
        r = _tm_cmd(t, cur)
        if r is not None:
            return r
        t = re.sub(_TM, " ", t)
    if re.search(r"\b(alışveriş|market)\b.*\b(listem|listemi|listesi|listeyi)\b|\b(listemi|listeyi)\b.*\b(oku|göster)\b", t) and not re.search(r"\b(ekle|at)\b", t):
        if re.search(r"\b(temizle|sil|boşalt|sıfırla)\w*", t):
            T.shopping_save([])
            return {"say": "Alışveriş listesini temizledim efendim."}
        items = T.shopping()
        return {"do": {"show": "shop"}, "say": ("Alışveriş listeniz: " + ", ".join(items[:15]) + ".") if items else "Alışveriş listeniz boş efendim."}
    if re.search(r"\b(alışveriş|market)\b.*\b(temizle|sil|boşalt)\w*|\blisteyi (temizle|sil|boşalt)", t):
        T.shopping_save([])
        return {"say": "Alışveriş listesini temizledim efendim."}
    if cur and re.search(r"\b(püf\w*|ipucu\w*|ip ucu|tüyo\w*|kalori\w*|saklama|nasıl saklan\w*)\b", t):
        from tarif_extra import INFO
        i = INFO.get(cur.get("id"))
        if not i:
            return {"say": "Bu tarif için ek bilgi yok efendim."}
        return {"do": {"show": "tip"}, "say": f"{cur['ad']}, kişi başı yaklaşık {i[0]} kalori. {i[1]} {i[2]}"}
    if cur and re.search(r"\b(alışveriş|market)\w*.*\b(ekle|at|yaz)\w*|\b(eksik|malzemeleri) (listeye|listesine) ekle", t):
        n = T.shopping_add(cur)
        return {"say": f"{cur['ad']} malzemelerinden {n} kalemi alışveriş listesine ekledim efendim."}
    m = re.search(r"\b(\w+)\s*kişilik\b", t)
    if cur and m and (scenes.num_in(m.group(1)) or 0) >= 1:
        T.S["kisi"] = min(scenes.num_in(m.group(1)), 30)
        return {"say": f"{cur['ad']} için malzemeleri {T.S['kisi']} kişiye göre ayarladım efendim."}
    m2 = re.search(r"\b(?:ama |ve )?(\w+) (?:kişi|kişiyiz|kişiye)\b", t)
    if cur and m2 and (scenes.num_in(m2.group(1)) or 0) >= 1 and re.search(r"\b(yap|olsun|ayarla|için|kişiyiz)\b", t):
        T.S["kisi"] = min(scenes.num_in(m2.group(1)), 30)
        return {"say": f"Malzemeleri {T.S['kisi']} kişiye göre ayarladım efendim."}
    if re.search(r"\b(elimde|evde|var)\b", t) and re.search(r"\b(ne yapsam|ne pişir\w*|tarif|yapılır|öner\w*)\b", t):
        hits = T.by_ingredient(" ".join(w for w in t.split() if w not in _STOP and w not in ("elimde", "evde", "var", "ne", "yapsam", "pişirsem", "yapılır", "ve", "ile")))
        if hits:
            return {"do": {"filter": [x["id"] for x in hits[:12]]}, "say": "Bunlardan yapabilirsiniz: " + ", ".join(x["ad"] for x in hits[:5]) + "."}
        return {"say": "Bu malzemelerle eşleşen tarif bulamadım efendim."}
    if cur:
        if re.search(r"\b(malzeme\w*|neler lazım|ne lazım)\b", t):
            return {"do": {"show": "mal"}, "say": f"{cur['ad']} için malzemeler: " + ", ".join(cur["mal"]) + "."}
        if re.search(r"\b(sayaç|zamanlayıcı|süre)\b.*\b(kur|başlat|ayarla)\w*|\b(kur|başlat)\w*\b.*\b(sayaç|zamanlayıcı)", t) or re.fullmatch(r"(evet|olur|kur|sayaç kur)", t):
            i = max(0, T.S["step"])
            d = cur["adim"][i][1]
            if not d:
                return {"say": "Bu adımda süre gerektiren bir şey yok efendim."}
            return {"do": {"timer": d, "label": f"{cur['ad']} · adım {i + 1}"}, "say": f"{d} dakikalık sayaç başladı efendim."}
        m = re.search(r"\badım\s+(\w+)", t)
        if m and (scenes.num_in(m.group(1)) or 0) >= 1:
            i = min(scenes.num_in(m.group(1)), len(cur["adim"])) - 1
            T.S["step"] = i
            return {"do": {"step": i}, "say": _step_say(cur, i)}
        if re.search(r"\b(başla|başlayalım|başlat)\b", t) and T.S["step"] < 0:
            T.S["step"] = 0
            return {"do": {"step": 0}, "say": "Başlıyoruz efendim. " + _step_say(cur, 0)}
        if re.search(r"\b(sonraki|devam|ileri|bitti|tamam|yaptım|oldu)\b", t):
            i = T.S["step"] + 1
            if i >= len(cur["adim"]):
                return {"do": {"step": len(cur["adim"]) - 1, "done": True}, "say": f"{cur['ad']} hazır efendim, afiyet olsun!"}
            T.S["step"] = i
            return {"do": {"step": i}, "say": _step_say(cur, i)}
        if re.search(r"\b(önceki|geri|bir önceki)\b", t):
            i = max(0, T.S["step"] - 1)
            T.S["step"] = i
            return {"do": {"step": i}, "say": _step_say(cur, i)}
        if re.search(r"\b(tekrar|tekrarla|yeniden|ne demiştin)\b", t):
            i = max(0, T.S["step"])
            return {"say": _step_say(cur, i)}
        if re.search(r"\b(liste|tarifler|menü|başka tarif|geri dön|ana sayfa)\b", t) and not T.find(t):
            T.S.update(id=None, step=-1)
            return {"do": {"list": True}, "say": "Tarif listesine döndük efendim."}
    if re.search(r"\btarifler\w*", t):                 # çoğul: kategori listesi (ad eşleşmesinden önce)
        for c in T.CATS:
            if c.split()[0][:5] in t:
                names = [x["ad"] for x in T.R if x["kat"] == c]
                return {"do": {"cat": c}, "say": f"{c.capitalize()} tarifleri: " + ", ".join(names[:8]) + "."}
    web = _web_query(t)
    r = None if web and (re.search(r"\binternet\w*", t) or not T.find_exact(t)) else T.find_exact(t) or (None if web else T.find(t))
    if web and not r:
        T.web_search(web)
        T.S.update(id=None, step=-1)
        return {"do": {"busy": f"“{web}” internette aranıyor…"}, "say": f"{web.capitalize()} tarifini internette arıyorum efendim, birkaç saniye sürer."}
    if r:
        T.S.update(id=r["id"], step=-1, kisi=0)
        r = T.cur()
        tm = " Thermomix ayarlarıyla." if T.tm_on(r) else (" Thermomix sürümü de var, Thermomix ile derseniz geçerim." if r.get("tmv") else "")
        return {"do": {"open": r["id"]}, "say": f"{r['ad']}, yaklaşık {r['dk']} dakika, {r['kisi']} kişilik.{tm} Malzemeleri ekranda gösteriyorum; başla derseniz adımları okurum."}
    for c in T.CATS:
        if c.split()[0][:5] in t and re.search(r"\btarif\w*|neler|var", t):
            names = [x["ad"] for x in T.R if x["kat"] == c]
            return {"do": {"cat": c}, "say": f"{c.capitalize()} tarifleri: " + ", ".join(names) + "."}
    if re.search(r"\btarif\w*|ne yapsam|ne pişir\w*|yemek öner\w*", t):
        hits = T.by_ingredient(" ".join(w for w in t.split() if w not in _STOP))
        if hits and len(hits) < len(T.R):
            return {"do": {"filter": [x["id"] for x in hits]}, "say": "Şunları önerebilirim: " + ", ".join(x["ad"] for x in hits[:6]) + "."}
    return {"say": "Anlayamadım efendim. Bir yemek adı ve tarifi deyin, örneğin menemen tarifi; ya da tatlı tarifleri."}


def init_payload():
    v = T.init_payload()
    if T.PENDING:                                  # mod normal Jarvis'ten 'X tarifi' ile açıldı (söyleyeceği extras.route_scene'de söylendi)
        text = T.PENDING.pop()
        T.PENDING.clear()
        r = _tarif(text, {})
        v = T.view()
        if r and r.get("do", {}).get("busy"):
            v["busy"] = r["do"]["busy"]
    return v


def tarif(text: str, st: dict):
    r = _tarif(text, st)
    if r is not None:
        r = {**r, "do": {**(r.get("do") or {}), "data": T.view()}}
    return r
