"""Dünya haritası modu komutları: '<yer>'e git', 'burası neresi', yakınlaş / uzaklaş, döndür, 3B / düz, kuzey, dünyayı göster, etiketler,
evimi göster, dünya turu, burayı kaydet, kayıtlı yerlerim. Yer arama ağ isteği olduğu için 'later' ile arka planda yapılır."""
import re

import harita as H
import scenes

VERBS = r"(?:git|gidelim|gider misin|götür|uç|uçalım|uçur|göster|gösterir misin|aç|bul|nerede|neresi|haritada göster|zoom yap|yakınlaş)"


def _place_of(raw: str):
    """'İstanbul'a git' -> 'İstanbul', 'Everest dağını göster' -> 'Everest dağı', 'Paris nerede' -> 'Paris'."""
    t = " ".join(str(raw).split())
    t = re.sub(r"^(?:jarvis\W+)?", "", t, flags=re.I)
    t = re.sub(r"\s+" + VERBS + r"\s*[.!?]*$", "", t, flags=re.I)
    t = re.sub(r"['’](?:[a-zA-ZçğıöşüÇĞİÖŞÜ]+)\b", "", t)          # İstanbul'a, Paris'e, Kapadokya'ya
    t = re.sub(r"\b(dağını|dağına)$", "dağı", t, flags=re.I)
    t = re.sub(r"\b(gölünü|gölüne)$", "gölü", t, flags=re.I)
    return t.strip(" ,.")


def _fly_to(raw: str, place: str):
    def job():
        try:
            g = H.geocode(place)
            if not g and len(place) > 4:                              # 'istanbula' gibi eki bitişik yazılmış adlar
                for cut in (3, 2, 1):
                    g = H.geocode(place[:-cut])
                    if g:
                        break
        except Exception as e:
            return {"say": f"Yer aramasına ulaşamadım efendim, internet bağlantısını kontrol edin. ({type(e).__name__})"}
        if not g:
            return {"say": f"{place} adında bir yer bulamadım efendim."}
        name = g["short"]
        return {"do": {"fly": {"lat": g["lat"], "lon": g["lon"], "bbox": g["bbox"], "name": g["name"], "short": name, "type": g["type"]}},
                "say": f"{name} efendim."}
    return job


def harita(text: str, st: dict):
    t = scenes.norm(text)
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Bir yer adı ve git deyin, örneğin İstanbul'a git ya da Everest dağını göster. Yakınlaş, uzaklaş, döndür, üç boyutlu, tepeden bak, "
                       "kuzeyi yukarı al, dünyayı göster, burası neresi, evimi göster, dünya turu, burayı kaydet ve etiketleri kapat komutları da var."}
    if re.search(r"\b(neler yapabilirsin)\b", t) is None and re.search(r"\b(git|göster|götür|uç|hakkında|bilgi|anlat|nedir|nerede)\b", t):
        for tn, lat, lon, zoom, pitch, bearing, info in H.TOUR:        # bilinen ünlü yerler: ağ gerekmez, hemen uçar ve bilgiyi okur
            key = scenes.norm(tn)
            if key and re.search(r"(?:^|\s)" + re.escape(key.split()[0]) + r"\w*", t) and (len(key.split()) == 1 or all(w in t for w in key.split()[:2])):
                return {"do": {"fly": {"lat": lat, "lon": lon, "zoom": zoom, "short": tn, "name": tn}}, "say": f"{tn}. {info}"}
    if re.search(r"\b(burası neresi|neredeyiz|bu ne(resi)?|bu şehir ne|bu ülke ne|şu an nere\w*)\b", t):
        return {"do": {"ask_center": True}, "say": ""}
    if re.search(r"\b(dünya turu|tur başlat|turu başlat|gezdir|tur yap|dünyayı gez\w*)\b", t):
        return {"do": {"tour": True}, "say": "Dünya turu başlıyor efendim. Durdurmak için turu durdur deyin."}
    if re.search(r"\b(turu durdur|turu bitir|turu kapat|dur|durdur)\b", t):
        return {"do": {"stop": True}, "say": ""}
    if re.search(r"\b(evimi|evim|memleketim\w*|şehrimi|evime|eve)\b", t) and re.search(r"\b(göster|git|dön|götür|aç)\w*|^evim$", t):
        def job():
            try:
                name, lat, lon = H.home()
            except Exception as e:
                return {"say": f"Ev konumunuzu bulamadım efendim. ({e})"}
            return {"do": {"fly": {"lat": lat, "lon": lon, "zoom": 12.5, "short": name, "name": name}}, "say": f"{name} efendim."}
        return {"say": "", "later": job}
    if re.search(r"\b(dünyayı göster|dünyaya dön|uzaya çık|tüm dünya|küreyi göster|uzaklaş tamamen)\b", t):
        return {"do": {"globe": True}, "say": ""}
    if re.search(r"\b(etiket\w*|yer adları|isimler\w*|sınırlar\w*)\b", t):
        on = not re.search(r"kapat|gizle|kaldır|istemiyorum", t)
        s = H.state(); s["labels"] = on; H.save_state(s)
        return {"do": {"labels": on}, "say": "Yer adları ve sınırlar açık efendim." if on else "Yer adlarını ve sınırları gizledim efendim."}
    if re.search(r"\b(üç boyut\w*|3 ?b|3d|eğ|eğik|dağları göster|yandan bak)\b", t):
        s = H.state(); s["terrain"] = True; H.save_state(s)
        return {"do": {"terrain": True, "pitch": 65}, "say": "Üç boyutlu görünüm efendim."}
    if re.search(r"\b(tepeden bak|düz bak|yukarıdan bak|iki boyut\w*|2 ?b|2d|düzleştir)\b", t):
        return {"do": {"pitch": 0}, "say": ""}
    if re.search(r"\b(kuzey\w*)\b", t):
        return {"do": {"north": True}, "say": ""}
    if re.search(r"\b(dönmeyi durdur|döndürmeyi durdur|sabit tut)\b", t):
        return {"do": {"spin": False}, "say": ""}
    if re.search(r"\b(döndür|dönsün|çevir)\w*", t):
        return {"do": {"spin": True}, "say": ""}
    m = re.search(r"\b(yakınlaş|yaklaş|büyüt)\w*", t)
    if m:
        return {"do": {"zoom": 2 if re.search(r"\bçok\b", t) else 1}, "say": ""}
    if re.search(r"\b(uzaklaş|küçült|geri çekil)\w*", t):
        return {"do": {"zoom": -2 if re.search(r"\bçok\b", t) else -1}, "say": ""}
    if re.search(r"\b(burayı kaydet|kaydet|işaretle|favori\w*e ekle)\b", t):
        return {"do": {"save_here": True}, "say": ""}
    if re.search(r"\b(kayıtlı yerler\w*|kaydettiğim yerler|favorilerim|işaretli yerler)\b", t):
        s = H.state()
        if not s["saved"]:
            return {"say": "Henüz kayıtlı yeriniz yok efendim. Burayı kaydet diyerek ekleyebilirsiniz."}
        return {"do": {"saved": True}, "say": "Kayıtlı yerleriniz: " + ", ".join(x["name"] for x in s["saved"][-8:]) + "."}
    place = _place_of(text)
    if place and len(place) >= 2:
        return {"say": "", "later": _fly_to(text, place)}
    return {"say": "Anlayamadım efendim. Bir yer adı ve git deyin, ya da yardım deyin."}


def ws(d: dict, st: dict):
    t = str(d.get("type", ""))[7:]
    if t == "search":
        q = " ".join(str(d.get("q", "")).split())[:120]
        return {"later": _fly_to(q, _place_of(q) or q)} if q else {}
    if t == "where":                                       # sayfa: harita merkezi -> yer adı
        try:
            lat, lon, z = float(d["lat"]), float(d["lon"]), float(d.get("zoom", 8))
        except (KeyError, TypeError, ValueError):
            return {}

        def job():
            try:
                name = H.reverse(lat, lon, 5 if z < 5 else 8 if z < 9 else 12 if z < 13 else 16)
            except Exception as e:
                return {"say": f"Yer adına ulaşamadım efendim. ({type(e).__name__})"}
            return {"do": {"here": name or ""}, "say": f"Burası {name}." if name else "Burası açık deniz ya da adsız bir bölge efendim."}
        return {"later": job}
    if t == "cam":                                         # son kamera konumu (sessiz)
        c = d.get("cam") or {}
        try:
            cam = {k: round(float(c[k]), 5) for k in ("lng", "lat", "zoom", "pitch", "bearing")}
        except (KeyError, TypeError, ValueError):
            return {"quiet": True}
        s = H.state(); s["cam"] = cam; H.save_state(s)
        return {"quiet": True}
    if t == "save":
        try:
            item = {"name": str(d.get("name") or "Kayıtlı yer")[:80], "lat": float(d["lat"]), "lon": float(d["lon"]), "zoom": float(d.get("zoom", 12))}
        except (KeyError, TypeError, ValueError):
            return {}
        s = H.state(); s["saved"] = [x for x in s["saved"] if x["name"] != item["name"]][-39:] + [item]; H.save_state(s)
        return {"say": f"{item['name']} kaydedildi efendim.", "speak": True}
    if t == "unsave":
        s = H.state(); s["saved"] = [x for x in s["saved"] if x["name"] != str(d.get("name"))]; H.save_state(s)
        return {}
    if t in ("labels", "terrain"):
        s = H.state(); s[t] = bool(d.get("on")); H.save_state(s)
        return {"quiet": True}
    if t == "say":                                         # tur sırasında yer bilgisini Jarvis söyler
        txt = str(d.get("text", ""))[:300]
        return {"say": txt, "speak": True} if txt else {}
    return {}


def init_payload():
    return H.view()
