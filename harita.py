"""Dünya haritası modu: yer arama (OpenStreetMap Nominatim), 'burası neresi' (ters arama), ev konumu, kayıtlı yerler, dünya turu.
Haritanın kendisi ui/scene_harita.html'de MapLibre GL ile çizilir; uydu görüntüsü Esri, yükseklik AWS açık verisi (kullanıcı onayı 2026-10-11).
Nominatim kullanım kuralları: tanıtıcı User-Agent, saniyede en fazla 1 istek, sonuçlar önbelleğe alınır. Aranan yer adı dışında hiçbir bilgi gönderilmez."""
import json
import os
import threading
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "harita_durum.json")
UA = "Jarvis-kisisel-asistan/1.0 (yerel masaustu uygulamasi)"
_lock = threading.Lock()
_last = [0.0]
_cache = {}

# dünya turu: (ad, enlem, boylam, yakınlık, eğim, yön, kısa bilgi)
TOUR = [("Kapadokya", 38.6431, 34.8289, 13.2, 65, 30, "Peri bacaları ve vadileri; milyonlarca yıl süren volkanik kül ve erozyonun eseri."),
        ("İstanbul Boğazı", 41.0850, 29.0550, 12.4, 60, -20, "Asya ile Avrupa'yı ayıran, Karadeniz'i Marmara'ya bağlayan boğaz."),
        ("Everest Dağı", 27.9881, 86.9250, 12.2, 72, 160, "Dünyanın en yüksek dağı, 8848 metre."),
        ("Büyük Kanyon", 36.1069, -112.1129, 12.0, 70, 40, "Colorado Nehri'nin milyonlarca yılda oyduğu, yer yer 1800 metre derinliğinde kanyon."),
        ("Mısır Piramitleri", 29.9792, 31.1342, 15.5, 60, 20, "Gize piramitleri; Keops Piramidi yaklaşık 4500 yıllık."),
        ("Amazon Nehri", -3.1190, -60.0217, 9.5, 50, 0, "Debisi en büyük nehir; çevresindeki yağmur ormanı dünyanın en büyüğü."),
        ("Niagara Şelalesi", 43.0799, -79.0747, 14.8, 60, -30, "ABD ile Kanada sınırındaki dev şelaleler."),
        ("Matterhorn", 45.9763, 7.6586, 12.6, 72, 250, "Alplerin piramit biçimli zirvesi, 4478 metre."),
        ("Büyük Set Resifi", -18.2871, 147.6992, 8.5, 45, 0, "Uzaydan görülebilen en büyük mercan resifi sistemi."),
        ("Mardin", 37.3129, 40.7350, 14.2, 60, 0, "Mezopotamya ovasına bakan taş şehir.")]


def _get(url: str):
    with _lock:                                           # Nominatim: saniyede en fazla 1 istek
        wait = 1.05 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "tr,en"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def geocode(query: str):
    """Yer adı -> {'name','lat','lon','bbox','type'} ya da None."""
    q = " ".join(str(query).split())[:120]
    if not q:
        return None
    if q.lower() in _cache:
        return _cache[q.lower()]
    res = _get("https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=" + urllib.parse.quote(q))
    out = None
    if res:
        r = res[0]
        bb = [float(x) for x in r.get("boundingbox", [])] if r.get("boundingbox") else None   # [güney, kuzey, batı, doğu]
        out = {"name": r.get("display_name", q), "short": r.get("name") or q, "lat": float(r["lat"]), "lon": float(r["lon"]),
               "bbox": [bb[2], bb[0], bb[3], bb[1]] if bb else None, "type": r.get("addresstype") or r.get("type", "")}
    _cache[q.lower()] = out
    return out


def reverse(lat: float, lon: float, zoom: int = 10):
    """Koordinat -> okunur yer adı ya da None (denizde olabilir)."""
    z = max(3, min(18, int(zoom)))
    r = _get(f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom={z}&lat={float(lat):.5f}&lon={float(lon):.5f}")
    if not r or r.get("error"):
        return None
    a = r.get("address", {})
    parts = [a.get(k) for k in ("village", "town", "city_district", "city", "county", "province", "state", "country") if a.get(k)]
    seen, uniq = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return ", ".join(uniq[-3:]) or r.get("display_name")


def home():
    """(ad, enlem, boylam): Jarvis'in hava durumunda kullandığı şehir (config.json 'city')."""
    import extras
    return extras._locate("")


# ------------------------------------------------------------------ kullanıcı durumu
def state() -> dict:
    try:
        with open(STATE, encoding="utf-8") as f:
            s = json.load(f)
        if not isinstance(s, dict):
            raise ValueError
    except (OSError, ValueError):
        s = {}
    s.setdefault("labels", True)
    s.setdefault("terrain", True)
    s.setdefault("saved", [])
    s.setdefault("cam", None)            # son kamera: {lng, lat, zoom, pitch, bearing}
    return s


def save_state(s: dict) -> None:
    keep = {k: s[k] for k in ("labels", "terrain", "saved", "cam") if k in s}
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(keep, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE)


def view() -> dict:
    s = state()
    return {"labels": s["labels"], "terrain": s["terrain"], "saved": s["saved"][-40:], "cam": s["cam"],
            "tour": [{"name": t[0], "lat": t[1], "lon": t[2], "zoom": t[3], "pitch": t[4], "bearing": t[5], "info": t[6]} for t in TOUR]}


from harita_more import TOUR_X
TOUR.extend(TOUR_X)
