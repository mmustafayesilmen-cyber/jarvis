"""İki günlük-iş modu: 'Güne başla' (hava, bugünün ajandası/hatırlatmaları/dersleri, yaklaşan sınav, kurlar ve WhatsApp okunmamışları tek ekranda + sesli özet)
ve 'Pano geçmişi' (pano.py: son 50 kopya, hazır metin parçaları). Komutlar yalnızca işlenirken bellekte durur (scenes.handle / cmdbuf).
Güne başla veri toplar ama hiçbir şey yazmaz/göndermez; WhatsApp özeti yalnızca ekrandaki sohbet listesinden okunur (whatsapp.read_unread_chats) ve
config.json: gune_whatsapp ile kapatılabilir. Sonuçlar yalnızca RAM'dedir."""
import concurrent.futures as cf
import datetime
import re
import threading
import time

import scenes
from scenes import norm
from scenes_yeni import _load, _save, _raw_after_colon

NOTIFY = None      # main.py: (kind, do) -> sayfaya gönderir (mod açıksa)
SAY = None         # main.py: (metin, kind) -> modda hâlâ açıksa seslendirir
GUN = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
AYLAR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# ================================================================== GÜNE BAŞLA
G = {"data": {}, "summary": "", "busy": False, "gen": 0, "at": 0.0}


def _greet() -> str:
    h = datetime.datetime.now().hour
    return "Günaydın" if 5 <= h < 12 else "İyi günler" if h < 18 else "İyi akşamlar" if h < 23 else "İyi geceler"


def _hava():
    import extras
    name, lat, lon = extras._locate("")
    d = extras._forecast(lat, lon)
    c, dl = d["current"], d["daily"]
    pp = dl["precipitation_probability_max"][0] or 0
    code = dl["weather_code"][0]
    return {"city": name, "temp": round(c["temperature_2m"]), "feels": round(c["apparent_temperature"]), "d": extras.WMO.get(c["weather_code"], "değişken"),
            "hi": round(dl["temperature_2m_max"][0]), "lo": round(dl["temperature_2m_min"][0]), "pp": pp, "wind": round(c["wind_speed_10m"]),
            "umbrella": pp >= 40 or (code >= 51 and code not in (45, 48)),
            "days": [{"gun": i, "hi": round(dl["temperature_2m_max"][i]), "lo": round(dl["temperature_2m_min"][i]), "d": extras.WMO.get(dl["weather_code"][i], ""),
                      "pp": dl["precipitation_probability_max"][i] or 0} for i in range(min(3, len(dl["time"])))]}


def _bugun():
    import agenda
    import reminders
    import schedule
    now = datetime.datetime.now()
    eod = now.replace(hour=23, minute=59, second=59)
    ev = [{"t": i["title"], "w": agenda.fmt_when(datetime.datetime.fromtimestamp(i["when"]), i.get("timed", True), now)} for i in agenda.upcoming(start=now, end=eod)]
    rem = [{"t": r["message"], "w": datetime.datetime.fromtimestamp(r["due"]).strftime("%H:%M")} for r in reminders.pending()
           if r.get("kind", "reminder") == "reminder" and now.timestamp() <= r["due"] <= eod.timestamp()]
    wd = now.weekday()
    les = schedule.day_lessons(wd)
    lessons = None
    if les:
        lessons = [{"n": i + 1, "ad": schedule.DERS[k][0], "saat": schedule.SAATLER[i][0]} for i, k in les]
    return {"ev": ev, "rem": rem, "lessons": lessons, "weekend": les is None}


def _sinav():
    import sinav
    return [{"ders": e["ders"], "kalan": e["kalan"], "konu": e.get("konu", "")} for e in sinav.upcoming()[:3]]


def _kur():
    import panel
    return panel._kur()


def _wa():
    import settings
    if settings.get("gune_whatsapp") is False:
        return {"off": True, "chats": []}
    import whatsapp
    chats = whatsapp.read_unread_chats()
    return {"off": False, "chats": [{"name": c["name"], "count": c["count"], "preview": c.get("preview", "")} for c in chats[:12]]}


def _summary(d: dict) -> str:
    now = datetime.datetime.now()
    out = [f"{_greet()} efendim. Bugün {now.day} {AYLAR[now.month]} {GUN[now.weekday()]}."]
    h = d.get("hava")
    if h:
        out.append(f"{h['city']} için hava {h['d']}, {h['temp']} derece; en yüksek {h['hi']}, en düşük {h['lo']}." + (" Şemsiye almanızı öneririm." if h["umbrella"] else ""))
    b = d.get("bugun")
    if b:
        if b["ev"]:
            out.append(f"Ajandanızda bugün {len(b['ev'])} kayıt var: " + "; ".join(f"{e['w']} {e['t']}" for e in b["ev"][:4]) + ".")
        else:
            out.append("Bugün için ajanda kaydınız yok.")
        if b["rem"]:
            out.append(f"{len(b['rem'])} hatırlatmanız var: " + "; ".join(f"saat {r['w']} {r['t']}" for r in b["rem"][:3]) + ".")
        if b["weekend"]:
            out.append("Bugün ders yok.")
        elif b["lessons"]:
            out.append(f"Bugün {len(b['lessons'])} dersiniz var; ilki {b['lessons'][0]['ad']}, saat {b['lessons'][0]['saat']}.")
    s = d.get("sinav")
    if s:
        e = s[0]
        out.append(f"En yakın sınavınız {e['ders']}, " + ("bugün." if e["kalan"] == 0 else "yarın." if e["kalan"] == 1 else f"{e['kalan']} gün sonra."))
    w = d.get("wa")
    if w is not None and not w.get("off"):
        ch = w["chats"]
        if ch:
            tot = sum(c["count"] for c in ch)
            out.append(f"WhatsApp'ta {len(ch)} sohbette {tot} okunmamış mesaj var: " + ", ".join(c["name"] for c in ch[:4]) + ".")
        elif "error" in w:
            out.append("WhatsApp mesajlarını okuyamadım.")
        else:
            out.append("Okunmamış WhatsApp mesajınız yok.")
    return " ".join(out)


def _collect(gen: int, speak: bool = True):
    jobs = {"hava": _hava, "bugun": _bugun, "sinav": _sinav, "kur": _kur, "wa": _wa}
    G.update(busy=True, data={}, summary="")
    ex = cf.ThreadPoolExecutor(max_workers=5)
    futs = {ex.submit(f): k for k, f in jobs.items()}
    try:
        for fu in cf.as_completed(futs, timeout=50):
            k = futs[fu]
            try:
                v = fu.result()
            except Exception as e:
                print("güne başla:", k, type(e).__name__, flush=True)
                v = {"off": False, "chats": [], "error": True} if k == "wa" else None
            if G["gen"] != gen:
                return
            G["data"][k] = v
            if NOTIFY:
                NOTIFY("gune", {"part": {k: v}})
    except cf.TimeoutError:
        print("güne başla: zaman aşımı", flush=True)
    finally:
        ex.shutdown(wait=False)
    if G["gen"] != gen:
        return
    G.update(summary=_summary(G["data"]), busy=False, at=time.time())
    if NOTIFY:
        NOTIFY("gune", {"summary": G["summary"], "done": True})
    if speak and SAY:
        SAY(G["summary"], "gune")


def _start(speak: bool = True):
    G["gen"] += 1
    threading.Thread(target=_collect, args=(G["gen"], speak), daemon=True).start()


def gune_init():
    if not G["busy"] and time.time() - G["at"] > 300:        # sayfa yeniden bağlanınca baştan toplanmaz; 5 dakikadan eskiyse yenilenir
        G.update(data={}, summary="")
        _start()
    import settings
    return {"snap": {"data": G["data"], "summary": G["summary"], "busy": G["busy"], "wa_on": settings.get("gune_whatsapp") is not False,
                     "greet": _greet(), "date": f"{datetime.date.today().day} {AYLAR[datetime.date.today().month]} {GUN[datetime.date.today().weekday()]}"}}


def gune(text, st):
    t = norm(text)
    import settings
    if re.search(r"\b(yardım|komutlar)\b", t):
        return {"say": "Özeti oku, yenile, WhatsApp'ı atla ya da WhatsApp'ı dahil et diyebilirsiniz."}
    if re.search(r"\bwhatsapp\w*", t) and re.search(r"\b(atla|kapat|çıkar|dahil etme|okuma)\w*", t):
        settings.set("gune_whatsapp", False)
        return {"do": {"wa_on": False}, "say": "WhatsApp özeti kapatıldı efendim."}
    if re.search(r"\bwhatsapp\w*", t) and re.search(r"\b(aç|dahil|ekle|oku)\w*", t):
        settings.set("gune_whatsapp", True)
        _start(speak=False)
        return {"do": {"wa_on": True, "reset": True}, "say": "WhatsApp özeti açıldı, yeniliyorum efendim."}
    if re.search(r"\b(yenile|tekrar topla|güncelle)\w*", t):
        _start(speak=False)
        return {"do": {"reset": True}, "say": "Bilgileri yeniliyorum efendim."}
    if re.search(r"\b(oku|söyle|özet\w*|tekrar|anlat)\w*", t):
        if G["summary"]:
            return {"say": G["summary"]}
        return {"say": "Bilgileri henüz topluyorum efendim, birkaç saniye."}
    return {"say": "Özeti oku ya da yenile diyebilirsiniz efendim."}


# ================================================================== PANO GEÇMİŞİ
PA_FILE = "pano_parcalar.json"


def _parts():
    d = _load(PA_FILE, {})
    d.setdefault("items", [])
    d.setdefault("next", 1)
    return d


_Q = [""]


def pano_snap(q=None):
    import pano
    if q is None:
        q = _Q[0]
    _Q[0] = q
    d = _parts()
    return {"hist": pano.view(q), "parts": [{"id": p["id"], "name": p["name"], "text": p["text"][:300], "n": len(p["text"])} for p in d["items"]],
            "on": pano.enabled(), "q": q}


def pano_init():
    return {"snap": pano_snap()}


def pano_mode(text, st):
    import pano
    raw = text.strip()
    t = norm(text)
    d = _parts()

    def res(say, q=None):
        return {"do": {"snap": pano_snap(q)}, "say": say}
    if raw.startswith("§"):
        c = raw[1:].split("|")
        try:
            if c[0] == "kopyala":
                return res("Panoya konuldu efendim." if pano.restore(int(c[1])) else "Kayıt bulunamadı efendim.")
            if c[0] == "sil":
                pano.delete(int(c[1]))
                return res("")
            if c[0] == "sabit":
                pano.pin(int(c[1]))
                return res("")
            if c[0] == "ara":
                return res("", c[1] if len(c) > 1 else "")
            if c[0] == "parcakopyala":
                p = next(x for x in d["items"] if x["id"] == int(c[1]))
                return res("Parça panoya konuldu efendim." if pano.set_clip(text=p["text"]) else "Panoya yazamadım efendim.")
            if c[0] == "parcasil":
                d["items"] = [x for x in d["items"] if x["id"] != int(c[1])]
                _save(PA_FILE, d)
                return res("")
            if c[0] == "parcaekle":
                name, body = c[1].strip(), "|".join(c[2:]).strip()
                if body:
                    d["items"].append({"id": d["next"], "name": (name or f"Parça {d['next']}")[:40], "text": body[:5000]})
                    d["next"] += 1
                    _save(PA_FILE, d)
                    return res("Parça kaydedildi efendim.")
        except (ValueError, StopIteration, IndexError):
            pass
        return {"say": ""}
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Son kopyaladığımı söyle, üç numaralı kaydı panoya al, panoda ara kelime, panoyu temizle, parça ekle iki nokta ad eşittir metin, "
                       "üç numaralı parçayı kopyala, pano izlemeyi kapat ya da aç diyebilirsiniz. Geçmiş yalnızca bellekte tutulur."}
    if re.search(r"\bpano\w*\s*(izle\w*|takip\w*)", t) and re.search(r"\b(kapat|durdur|kapa)\w*", t):
        pano.set_enabled(False)
        return res("Pano izleme kapatıldı efendim. Geçmişteki kayıtlar yerinde duruyor.")
    if re.search(r"\bpano\w*\s*(izle\w*|takip\w*)", t) and re.search(r"\b(aç|başlat|etkinleştir)\w*", t):
        pano.set_enabled(True)
        return res("Pano izleme açıldı efendim.")
    if re.search(r"\b(panoyu|geçmişi|kayıtları|hepsini)\b.*\b(temizle|sil|boşalt)\w*|\btemizle\b", t) and not re.search(r"parça", t):
        n = pano.clear()
        return res(f"{n} kaydı sildim efendim. Sabitlenenler yerinde." if n else "Silinecek kayıt yok efendim.")
    if re.search(r"\bparça\w*", t) and re.search(r"\b(ekle|kaydet)\w*", t):
        body = _raw_after_colon(raw)
        if not body:
            return {"say": "Parçayı iki nokta üst üste sonrası söyleyin efendim. Örneğin parça ekle iki nokta adres eşittir İstanbul Kadıköy."}
        name, text_ = [x.strip() for x in body.split("=", 1)] if "=" in body else ("", body.strip())
        d["items"].append({"id": d["next"], "name": (name or f"Parça {d['next']}")[:40], "text": text_[:5000]})
        d["next"] += 1
        _save(PA_FILE, d)
        return res("Hazır parçayı kaydettim efendim.")
    if re.search(r"\bparça\w*", t) and re.search(r"\b(sil|kaldır)\w*", t):
        m = re.search(r"(\d+)", t)
        if m:
            d["items"] = [x for x in d["items"] if x["id"] != int(m.group(1))]
            _save(PA_FILE, d)
            return res("Parçayı sildim efendim.")
    if re.search(r"\bparça\w*", t) and re.search(r"\b(kopyala|panoya|al|getir)\w*", t):
        m = re.search(r"(\d+)", t)
        p = next((x for x in d["items"] if m and x["id"] == int(m.group(1))), None) or next((x for x in d["items"] if norm(x["name"]) in t), None)
        if p:
            return res("Parça panoya konuldu efendim." if pano.set_clip(text=p["text"]) else "Panoya yazamadım efendim.")
        return {"say": "Hangi parça efendim? Numarasını ya da adını söyleyin."}
    m = re.search(r"panoda\s+ara\w*\s+(.+)$|panoda\s+(.+?)\s*(?:ara\w*)?$|(.+?)\s+panoda ara\w*|ara\w*\s*[:：]\s*(.+)$", t)
    if m and re.search(r"\bara\w*", t):
        q = next(g for g in m.groups() if g).strip()
        r = pano.view(q)
        return res(f"{len(r)} kayıt buldum efendim." if r else "Eşleşen kayıt yok efendim.", q)
    m = re.search(r"(\d+)\s*(?:numaralı|\.)?\s*(?:kayıt\w*|kopya\w*)?", t)
    if m and re.search(r"\b(panoya|kopyala|al|getir|geri)\w*", t):
        e = pano.nth(int(m.group(1)))
        if e:
            return res("Panoya konuldu efendim." if pano.restore(e["id"]) else "Panoya yazamadım efendim.")
        return {"say": "Bu numarada kayıt yok efendim."}
    if re.search(r"\b(son|en son)\b.*\b(kopyala\w*|pano\w*)\b|\bpanoda ne var\b", t):
        e = pano.nth(1)
        if not e:
            return {"say": "Geçmiş boş efendim."}
        return {"say": "Son kopyaladığınız: " + ("gizli içerik, söylemiyorum." if e["secret"] else e["text"][:200])}
    return {"say": "Anlayamadım efendim. Son kopyaladığımı söyle ya da üç numaralı kaydı panoya al diyebilirsiniz."}
