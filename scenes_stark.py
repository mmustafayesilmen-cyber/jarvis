"""Sekiz Stark modu: Zırh Kontrolü (zirh), Görev Masası (gorev), S.H.I.E.L.D. Brifingi (brifing), Stark Laboratuvarı (starklab),
Holografik Dünya (dunya), Güvenlik Merkezi (guvenlik), Çoklu Asistan Köprüsü (kopru). Odak Odası (odakoda) pomodoro.py'yi olduğu gibi kullanır
(ikinci sayaç yoktur; komutlar scenes_pomodoro'ya gider, bkz. scenes.py/main.py).

İlkeler: her ekran yalnızca gerçek ölçüm/kayıtlardan beslenir; ölçülemeyen değer "ölçülemedi" + nedeniyle gösterilir, örnek veri yoktur.
Yeni dış servis YOKTUR: hava = extras._forecast (Open-Meteo, zaten kullanılıyor), yer arama = harita.geocode (Nominatim, zaten kullanılıyor).
Komutlar yalnızca işlenirken bellekte durur (scenes.handle / cmdbuf). Anahtar, parola, cihaz anahtarı, özel IP hiçbir yerde gösterilmez/yazılmaz."""
import concurrent.futures as cf
import datetime
import re
import threading
import time
import urllib.parse

import psutil

import scenes
from scenes import norm
from scenes_yeni import _load, _save

NOTIFY = None        # main.py: (kind, do) -> mod açıksa sayfaya gönderir
SAY = None           # main.py: (metin, kind) -> modda hâlâ açıksa seslendirir
HOOK = None          # main.py: () -> {"clients": int, "mic_muted": bool|None, "scene": str|None, "persona": str|None}

GUN = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
AY = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _p(x, d=0):
    return f"{x:.{d}f}".replace(".", ",")


def _push(kind, do):
    if NOTIFY:
        try:
            NOTIFY(kind, do)
        except Exception as e:
            print("stark bildirim hatası:", type(e).__name__, flush=True)


def _yes(t):
    return bool(re.fullmatch(r"(evet|tamam|onaylıyorum|onayla|sil|olur|devam|kesinlikle)( \w+)?", t))


def _no(t):
    return bool(re.fullmatch(r"(hayır|vazgeç|iptal|olmaz|yapma|dur)( \w+)?", t))


def _raw_low(raw: str) -> str:
    """agenda.route ile aynı normalleştirme (saat için noktalama korunur)."""
    low = raw.replace("İ", "i").replace("I", "ı").lower()
    low = re.sub(r"['’]", "", low)
    low = re.sub(r"[^\w\s:.,]", " ", low)
    return " ".join(low.split())


# ================================================================== 1) ZIRH KONTROLÜ
def _battery() -> dict:
    try:
        b = psutil.sensors_battery()
    except Exception:
        b = None
    if b is None:
        return {"present": False, "why": "Bu bilgisayarda pil algılanmadı (masaüstü olabilir)."}
    left = b.secsleft if isinstance(b.secsleft, int) and b.secsleft > 0 else None
    return {"present": True, "percent": round(b.percent), "plugged": bool(b.power_plugged), "left_min": None if left is None else left // 60}


def _link() -> dict:
    """Yalnızca arayüz durumu (internete bağlanıp sınamaz: gizlilik). 'Bağlantı var' ≠ 'internet erişimi sınandı'."""
    try:
        ups = [n for n, s in psutil.net_if_stats().items() if s.isup and "loopback" not in n.lower() and not n.lower().startswith("lo")]
    except Exception:
        return {"known": False, "why": "Ağ arayüzleri okunamadı."}
    return {"known": True, "up": bool(ups), "nics": len(ups)}


def readiness(s: dict, bat: dict, lk: dict) -> dict:
    """Genel hazırlık durumu ve HANGİ ölçümlerden türediği. Ölçülemeyenler durumu iyi göstermez, 'ölçülemedi' olarak listelenir."""
    import sysmon
    used, unm, warn = [], [], list(s.get("alerts") or [])
    used += [f"İşlemci yükü %{_p(s['cpu']['total'])}", f"RAM %{_p(s['ram']['percent'])}", f"C diski %{_p(s['disk']['percent'])} dolu"]
    g = s.get("gpu")
    if g:
        used.append("Ekran kartı yükü/ısısı/VRAM")
    else:
        unm.append("Ekran kartı (nvidia-smi bulunamadı ya da yanıt vermedi)")
    unm.append("İşlemci sıcaklığı (Windows bu sensörü yönetici izni olmadan vermiyor)")
    unm.append("Disk sıcaklığı (yönetici izni gerekir)")
    if bat.get("present"):
        used.append(f"Pil %{bat['percent']}" + (" (şarjda)" if bat["plugged"] else ""))
        if not bat["plugged"] and bat["percent"] <= 20:
            warn.append(f"Pil yüzde {bat['percent']} ve şarjda değil")
    else:
        unm.append("Pil (cihazda pil yok)")
    if lk.get("known"):
        used.append("Ağ arayüzü " + ("bağlı" if lk["up"] else "kapalı"))
        if not lk["up"]:
            warn.append("Etkin bir ağ bağlantısı görünmüyor")
    else:
        unm.append("Ağ durumu")
    level = "dikkat" if warn else "hazir"
    text = "Zırh hazır: ölçülebilen değerlerde eşik aşımı yok." if not warn else "Dikkat gerektiren durum var."
    return {"level": level, "text": text, "warn": warn, "used": used, "unmeasured": unm}


def zirh_tick() -> dict:
    """main.py zirh döngüsü: sysmon ölçümü + pil + ağ + hazırlık (saniyede bir)."""
    import sysmon
    snap = sysmon.SAMPLER.snapshot()
    bat, lk = _battery(), _link()
    return {"snap": snap, "bat": bat, "link": lk, "ready": readiness(snap, bat, lk), "static": sysmon._STATIC or {}, "t": time.time()}


def _last_snap():
    import sysmon
    s = sysmon.SAMPLER
    return s.hist[-1] if s.running and s.hist else None


def zirh_init() -> dict:
    return {"static": __import__("sysmon")._STATIC or {}}


def _deep_job(gen):
    time.sleep(10)
    import sysmon
    h = list(sysmon.SAMPLER.hist)[-10:]
    if not h or ZS.get("gen") != gen:
        return
    cpu = [x["cpu"]["total"] for x in h]
    ram = [x["ram"]["percent"] for x in h]
    top = h[-1]["top_cpu"][:3]
    msg = (f"Ayrıntılı tarama bitti: {len(h)} ölçümde işlemci ortalama %{_p(sum(cpu) / len(cpu))}, en yüksek %{_p(max(cpu))}; RAM ortalama %{_p(sum(ram) / len(ram))}. "
           + ("En çok işlemci kullananlar: " + ", ".join(f"{n} %{_p(v)}" for n, v in top) + ". " if top else "")
           + ("Dikkat: " + "; ".join(h[-1]["alerts"]) + "." if h[-1]["alerts"] else "Eşik aşımı yok."))
    ZS["deep"] = False
    _push("zirh", {"deep": {"done": True, "text": msg}, "msg": "Ayrıntılı tarama tamamlandı."})
    if SAY:
        SAY(msg, "zirh")


ZS = {"gen": 0, "deep": False}


def zirh(text: str, st: dict):
    t = norm(text)
    if re.search(r"\b(sistemi|bilgisayarı|bilgisayarımı|pc'yi)\b.*\b(kapat|yeniden başlat|uyut|kilitle)\w*", t):
        return {"say": "Güç komutları bu modda çalışmaz efendim. Önce çık deyip normal Jarvis'e dönün."}
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Hızlı tarama, ayrıntılı tarama, genel durum, pil, disk, ağ, ekran kartı ve çık diyebilirsiniz."}
    s = _last_snap()
    if s is None:
        return {"say": "Ölçüm henüz başlamadı efendim, bir saniye bekleyin."}
    bat, lk = _battery(), _link()
    r = readiness(s, bat, lk)
    if re.search(r"\bayrıntılı\b.*\btara\w*|\bderin tara\w*", t):
        if ZS["deep"]:
            return {"say": "Ayrıntılı tarama zaten sürüyor efendim."}
        ZS.update(deep=True, gen=ZS["gen"] + 1)
        threading.Thread(target=_deep_job, args=(ZS["gen"],), daemon=True).start()
        return {"do": {"deep": {"run": True}}, "say": "Ayrıntılı tarama başladı efendim: on saniye boyunca ölçümleri topluyorum. Ek yük bindirmiyorum, yalnızca zaten yapılan ölçümleri birleştiriyorum."}
    if re.search(r"\btara\w*|\bhızlı\b|\bgenel durum\b|\bzırh\b|\bdurum\w*", t):
        import scenes_sistem
        msg = scenes_sistem.scan_summary(s) if not r["warn"] else "Dikkat: " + "; ".join(r["warn"]) + "."
        return {"do": {"quick": True}, "say": r["text"] + " " + msg}
    if re.search(r"\bpil\w*|\bşarj\w*", t):
        if not bat["present"]:
            return {"say": bat["why"]}
        return {"say": f"Pil yüzde {bat['percent']}, " + ("şarjda." if bat["plugged"] else "şarjda değil.")}
    if re.search(r"\bdisk\w*", t):
        import scenes_sistem
        return {"say": scenes_sistem.say_disk(s)}
    if re.search(r"\bağ\b|\binternet\b|\bbağlantı\w*", t):
        import scenes_sistem
        return {"say": scenes_sistem.say_net(s)}
    if re.search(r"\bekran kartı\b|\bgpu\b", t):
        import scenes_sistem
        return {"say": scenes_sistem.say_gpu(s)}
    return {"say": r["text"]}


# ================================================================== 2) GÖREV MASASI
GF = "gorev_masasi.json"
GL = threading.RLock()


def _gd():
    d = _load(GF, {})
    d.setdefault("items", [])
    d.setdefault("next", 1)
    return d


def _fmt_due(i) -> str:
    if not i.get("due"):
        return "tarihsiz"
    import agenda
    return agenda.fmt_when(datetime.datetime.fromtimestamp(i["due"]), i.get("timed", True))


def _arm(i):
    """Saatli görev için hatırlatma kurar (reminders.json: ikinci bir saklama yok, yalnızca mevcut mekanizma). Vade tarihi göreve işlenir."""
    import reminders
    if i.get("rem"):
        reminders.cancel_due(i["rem"])
        i["rem"] = None
    if i.get("due") and i.get("timed") and not i.get("done") and i["due"] > time.time() + 5:
        i["rem"] = reminders.add_at(i["due"] - time.time(), i["title"], "reminder")


def _disarm(i):
    if i.get("rem"):
        import reminders
        reminders.cancel_due(i["rem"])
        i["rem"] = None


def gorev_view() -> dict:
    import agenda
    import reminders
    with GL:
        d = _gd()
    now = datetime.datetime.now()
    eod = now.replace(hour=23, minute=59, second=59).timestamp()
    op = [i for i in d["items"] if not i.get("done")]
    key = lambda i: (i.get("due") or 9e12, -i.get("prio", 2))
    today = sorted([i for i in op if i.get("due") and i["due"] <= eod], key=key)
    later = sorted([i for i in op if not (i.get("due") and i["due"] <= eod)], key=key)
    done = sorted([i for i in d["items"] if i.get("done")], key=lambda i: -(i.get("done_at") or 0))[:25]

    def row(i):
        return {"id": i["id"], "title": i["title"], "when": _fmt_due(i), "prio": i.get("prio", 2), "note": i.get("note", ""), "repeat": i.get("repeat", ""),
                "late": bool(i.get("due") and i["due"] < time.time() and not i.get("done") and i.get("timed", True)), "remind": bool(i.get("rem")), "done": bool(i.get("done"))}
    mine = {i.get("rem") for i in d["items"] if i.get("rem")}
    cal = [{"t": e["title"], "w": agenda.fmt_when(datetime.datetime.fromtimestamp(e["when"]), e.get("timed", True), now)} for e in agenda.upcoming(7)]
    rem = [{"t": r["message"], "w": agenda.fmt_when(datetime.datetime.fromtimestamp(r["due"]), True, now)} for r in reminders.pending()
           if r.get("kind", "reminder") == "reminder" and r["due"] <= time.time() + 7 * 86400 and not any(abs(r["due"] - m) < 1 for m in mine if m)]
    # takvim kayıtlarının otomatik "yarım saat sonra" hatırlatmaları listede ikinci kez görünmesin
    rem = [r for r in rem if not any(r["t"].startswith(c["t"]) for c in cal)]
    return {"today": [row(i) for i in today], "later": [row(i) for i in later], "done": [row(i) for i in done], "cal": cal, "rem": rem,
            "date": f"{now.day} {AY[now.month]} {GUN[now.weekday()]}"}


def say_today() -> str:
    v = gorev_view()
    if not v["today"] and not v["cal"][:1]:
        return "Bugün için açık göreviniz yok efendim."
    out = []
    if v["today"]:
        out.append(f"Bugün {len(v['today'])} göreviniz var: " + "; ".join((f"{r['when']} " if 'tarihsiz' not in r['when'] else '') + r["title"] for r in v["today"][:5]) + ".")
    td = [c for c in v["cal"] if c["w"].startswith("bugün")]
    if td:
        out.append("Takvimde: " + "; ".join(f"{c['w']} {c['t']}" for c in td[:3]) + ".")
    return " ".join(out) or "Bugün için açık göreviniz yok efendim."


def _find(d, t, num=None):
    if num is not None:
        return next((i for i in d["items"] if i["id"] == num), None)
    m = re.search(r"(?<![:\d])(\d{1,4})(?!\d|:)", t)
    if m:
        return next((i for i in d["items"] if i["id"] == int(m.group(1))), None)
    hit = [i for i in d["items"] if not i.get("done") and norm(i["title"]) and norm(i["title"]) in t]
    if not hit:
        words = [w for w in t.split() if len(w) > 3]
        hit = [i for i in d["items"] if not i.get("done") and any(w in norm(i["title"]) for w in words)]
    return hit[0] if len(hit) == 1 else (hit if hit else None)


def _clean_title(low: str) -> str:
    s = re.sub(r"^\W*(görev masasına |görev masası |görevlerime |göreve |yeni )?(görev|hatırlatıcı|hatırlatma|iş|yapılacak)\s*(ekle\w*|oluştur\w*|kaydet\w*|yaz\w*)?\s*[:,]?\s*", "", low)
    s = re.sub(r"\b(ekle\w*|kaydet\w*|hatırlat\w*|görev\w*|olarak|diye)\b", " ", s)
    s = re.sub(r"\b(her gün|her hafta|günlük|haftalık|öncelikli|yüksek öncelik\w*|düşük öncelik\w*|acil)\b", " ", s)
    return " ".join(s.split()).strip(" ,.:")


def _add(raw: str, st: dict):
    import agenda
    low = _raw_low(raw)
    rep = "daily" if re.search(r"\bher gün\b|\bgünlük\b", low) else "weekly" if re.search(r"\bher hafta\b|\bhaftalık\b", low) else ""
    prio = 3 if re.search(r"\b(acil|yüksek öncelik\w*|öncelikli|önemli)\b", low) else 1 if re.search(r"\bdüşük öncelik\w*", low) else 2
    note = ""
    if "not:" in low:
        low, note = [x.strip() for x in low.split("not:", 1)]
    p = agenda.parse_when(low)
    due, timed, rest = None, False, low
    if p:
        when, rest, timed = p
        if when <= datetime.datetime.now() and timed:
            return {"say": "Bu zaman geçmişte kaldı efendim, ileri bir zaman söyler misiniz?"}
        due = when.timestamp() if timed else when.replace(hour=23, minute=59, second=0).timestamp()
    elif re.search(r"\bsaat\s+\d|\b\d{1,2}[:.]\d{2}\b|\b(sabah|akşam|öğle\w*|gece)\b", low):
        return {"say": "Hangi gün için efendim? Bugün, yarın ya da bir gün adı söyleyerek yeniden ekler misiniz?"}
    elif re.search(r"\b(haftaya|ay sonu|ayın sonunda|gelecek|önümüzdeki|bir ara|birkaç)\b", low):
        return {"say": "Zamanı tam anlayamadım efendim. Bugün, yarın, bir gün adı ya da tarih ve saat söyler misiniz?"}
    title = _clean_title(rest)
    if not title:
        return {"say": "Görevin ne olduğunu anlayamadım efendim. Örneğin: görev ekle: ödev yap yarın saat 10."}
    with GL:
        d = _gd()
        if any(not i.get("done") and i["title"].lower() == title.lower() and i.get("due") == due for i in d["items"]):
            return {"say": "Bu görev zaten listede efendim."}
        i = {"id": d["next"], "title": title[:120], "due": due, "timed": bool(timed), "prio": prio, "note": note[:300], "repeat": rep, "done": False, "rem": None, "created": time.time()}
        d["next"] += 1
        _arm(i)
        d["items"].append(i)
        _save(GF, d)
    when = f" {_fmt_due(i)} için" if due else ""
    extra = " Hatırlatıcı da kuruldu." if i["rem"] else ("" if not due or timed else " Saat söylemediğiniz için gün sonuna ayarladım, hatırlatıcı kurmadım.")
    return {"do": {"data": gorev_view()}, "say": f"Tamam efendim,{when} {title} görev masasına eklendi.{extra}"}


def _next_due(i):
    step = 86400 if i["repeat"] == "daily" else 7 * 86400
    n = i["due"] + step
    while n < time.time():
        n += step
    return n


def gorev(text: str, st: dict):
    t = norm(text)
    raw = str(text).strip()
    res = lambda say="": {"do": {"data": gorev_view()}, "say": say}
    if st.get("confirm"):
        c = st.pop("confirm")
        if _yes(t):
            with GL:
                d = _gd()
                it = _find(d, "", c)
                if it:
                    _disarm(it)
                    d["items"] = [x for x in d["items"] if x["id"] != c]
                    _save(GF, d)
            return res("Görevi sildim efendim.")
        return res("Vazgeçtim efendim, görev duruyor.")
    if raw.startswith("§"):                                # sayfa düğmeleri: §tamam|id  §ertele|id  §sil|id  §ekle|başlık|tarih|öncelik|not  §duzenle|id|başlık|not|öncelik
        c = raw[1:].split("|")
        try:
            with GL:
                d = _gd()
                it = _find(d, "", int(c[1])) if len(c) > 1 and c[1].isdigit() else None
                if c[0] == "tamam" and it:
                    return _complete(d, it)
                if c[0] == "geri" and it:
                    it["done"] = False
                    it.pop("done_at", None)
                    _arm(it)
                    _save(GF, d)
                    return res("Görevi yeniden açtım efendim.")
                if c[0] == "ertele" and it:
                    return _postpone(d, it, c[2] if len(c) > 2 else "yarın")
                if c[0] == "sil" and it:
                    st["confirm"] = it["id"]
                    return {"say": f"{it['title']} görevini silmemi onaylıyor musunuz? Bu geri alınamaz. Evet ya da hayır deyin."}
                if c[0] == "silonay" and it:                  # sayfadaki satır içi onaydan gelir
                    _disarm(it)
                    d["items"] = [x for x in d["items"] if x["id"] != it["id"]]
                    _save(GF, d)
                    return res("Görevi sildim efendim.")
                if c[0] == "duzenle" and it:
                    it["title"] = (c[2] or it["title"])[:120]
                    it["note"] = (c[3] if len(c) > 3 else it.get("note", ""))[:300]
                    if len(c) > 4 and c[4] in ("1", "2", "3"):
                        it["prio"] = int(c[4])
                    _save(GF, d)
                    return res("Görevi güncelledim efendim.")
        except (ValueError, IndexError):
            pass
        if c[0] == "ekle" and len(c) > 1 and c[1].strip():
            r = _add(f"{c[1]} {c[2] if len(c) > 2 else ''} {'acil' if len(c) > 3 and c[3] == '3' else ''}", st)
            return r
        return res("")
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Görev ekle iki nokta ödev yap yarın saat on, bugün ne yapmam gerekiyor, ikinci görevi tamamla, ertele, yarına ertele, sil, "
                       "öncelik yüksek, ve çık diyebilirsiniz. Silmeden önce size soracağım."}
    if re.search(r"\bbugün ne\b|\bneler var\b|\bgörevlerim\b|\bne yapmam\b|\bne yapacağım\b|\bgörevleri (oku|say|söyle|listele)", t):
        return res(say_today())
    if re.search(r"\b(ekle|oluştur|kaydet)\w*", t) and re.search(r"\b(görev|hatırlatıcı|hatırlatma|iş|yapılacak)\w*", t):
        return _add(raw, st)
    it = None
    if re.search(r"\b(tamamla|tamamlandı|bitti|bitirdim|yaptım|halloldu|işaretle)\w*", t) or re.search(r"\b(ertele|erteleyelim|ileri at)\w*", t) or re.search(r"\b(sil|kaldır|iptal et)\w*", t) \
            or re.search(r"\b(öncelik|düzenle|değiştir|not)\w*", t):
        with GL:
            d = _gd()
            it = _find(d, t)
            if isinstance(it, list):
                return res("Birden fazla görev eşleşti efendim, numarasını söyler misiniz? " + "; ".join(f"{x['id']} numara {x['title']}" for x in it[:4]))
            if it is None:
                return res("Hangi görev efendim? Numarasını ya da adını söyler misiniz?")
            if re.search(r"\b(sil|kaldır|iptal et)\w*", t):
                st["confirm"] = it["id"]
                return {"say": f"{it['title']} görevini silmemi onaylıyor musunuz? Bu geri alınamaz. Evet ya da hayır deyin."}
            if re.search(r"\b(ertele|erteleyelim|ileri at)\w*", t):
                return _postpone(d, it, t)
            if re.search(r"\b(tamamla|tamamlandı|bitti|bitirdim|yaptım|halloldu|işaretle)\w*", t):
                return _complete(d, it)
            m = re.search(r"\böncelik\w*.*\b(yüksek|acil|normal|orta|düşük)", t)
            if m:
                it["prio"] = 3 if m.group(1) in ("yüksek", "acil") else 1 if m.group(1) == "düşük" else 2
                _save(GF, d)
                return res("Önceliği güncelledim efendim.")
            if ":" in raw and re.search(r"\bnot\b", t):
                it["note"] = raw.split(":", 1)[1].strip()[:300]
                _save(GF, d)
                return res("Notu kaydettim efendim.")
            if ":" in raw and re.search(r"\b(düzenle|değiştir)\w*", t):
                it["title"] = raw.split(":", 1)[1].strip()[:120]
                _save(GF, d)
                return res("Görevi güncelledim efendim.")
    return res("Anlayamadım efendim. Görev ekle, bugün ne yapmam gerekiyor, birinci görevi tamamla ya da yarına ertele diyebilirsiniz.")


def _complete(d, it):
    if it.get("repeat") and it.get("due"):
        it["due"] = _next_due(it)
        _arm(it)
        _save(GF, d)
        return {"do": {"data": gorev_view()}, "say": f"{it['title']} tamamlandı efendim; tekrarlandığı için bir sonraki sefere {_fmt_due(it)} olarak kuruldu."}
    it["done"], it["done_at"] = True, time.time()
    _disarm(it)
    _save(GF, d)
    return {"do": {"data": gorev_view()}, "say": f"{it['title']} tamamlandı olarak işaretlendi efendim."}


def _postpone(d, it, spec):
    spec = norm(spec)
    base = datetime.datetime.fromtimestamp(it["due"]) if it.get("due") else datetime.datetime.now()
    m = re.search(r"(\d+)\s*(saat|dakika|dk|gün)", spec)
    if m:
        n = int(m.group(1))
        delta = datetime.timedelta(hours=n) if m.group(2) == "saat" else datetime.timedelta(minutes=n) if m.group(2) in ("dakika", "dk") else datetime.timedelta(days=n)
        new = max(base, datetime.datetime.now()) + delta
    elif re.search(r"\bhaftaya\b", spec):
        new = base + datetime.timedelta(days=7)
    else:
        new = base + datetime.timedelta(days=1) if it.get("due") else datetime.datetime.now().replace(hour=23, minute=59) + datetime.timedelta(days=1)
    it["due"] = new.timestamp()
    if not it.get("timed"):
        it["due"] = new.replace(hour=23, minute=59, second=0).timestamp()
    _arm(it)
    _save(GF, d)
    return {"do": {"data": gorev_view()}, "say": f"{it['title']} görevini {_fmt_due(it)} tarihine erteledim efendim."}


# ================================================================== 3) S.H.I.E.L.D. BRİFİNGİ
BR = {"data": {}, "summary": "", "busy": False, "gen": 0, "at": 0.0}
SRC = {"hava": "Open-Meteo (extras._forecast)", "bugun": "Görev Masası + takvim (agenda.json, reminders.json)", "sinav": "Sınav modu (sinav.json)", "kur": "Panel kur kaynağı (panel._kur)"}


def _b_hava():
    import scenes_gunluk
    return scenes_gunluk._hava()


def _b_gorev():
    v = gorev_view()
    return {"today": v["today"][:6], "cal": [c for c in v["cal"] if c["w"].startswith("bugün")][:5], "late": [r for r in v["today"] if r["late"]][:3],
            "next": v["later"][:3]}


def _b_sinav():
    import scenes_gunluk
    return scenes_gunluk._sinav()


def _b_kur():
    import scenes_gunluk
    return scenes_gunluk._kur()


def _brief_text(d: dict) -> str:
    now = datetime.datetime.now()
    out = [f"{now.day} {AY[now.month]} {GUN[now.weekday()]}."]
    g = d.get("gorev")
    if isinstance(g, dict) and g.get("ok"):
        v = g["v"]
        if v["late"]:
            out.append(f"Önce: {len(v['late'])} görevinizin zamanı geçmiş, ilki {v['late'][0]['title']}.")
        if v["today"]:
            out.append(f"Bugün {len(v['today'])} göreviniz var, ilki {v['today'][0]['title']}.")
        else:
            out.append("Bugün açık göreviniz yok.")
        if v["cal"]:
            out.append("Takvimde " + "; ".join(f"{c['w']} {c['t']}" for c in v["cal"][:3]) + ".")
    h = d.get("hava")
    if isinstance(h, dict) and h.get("ok"):
        h = h["v"]
        out.append(f"{h['city']}'da hava {h['d']}, {h['temp']} derece, en yüksek {h['hi']}." + (" Şemsiye alın." if h["umbrella"] else ""))
    s = d.get("sinav")
    if isinstance(s, dict) and s.get("ok") and s["v"]:
        e = s["v"][0]
        out.append(f"En yakın sınav {e['ders']}, " + ("bugün." if e["kalan"] == 0 else "yarın." if e["kalan"] == 1 else f"{e['kalan']} gün sonra."))
    miss = [k for k in ("hava", "gorev") if not (isinstance(d.get(k), dict) and d[k].get("ok"))]
    if miss:
        out.append("Şu bölümler alınamadı: " + ", ".join({"hava": "hava durumu", "gorev": "görevler"}[k] for k in miss) + ".")
    out.append("Haber kaynağı bağlı değil.")
    return " ".join(out)


def _b_collect(gen: int, speak: bool = False):
    jobs = {"hava": _b_hava, "gorev": _b_gorev, "sinav": _b_sinav, "kur": _b_kur}
    BR.update(busy=True, data={}, summary="")
    ex = cf.ThreadPoolExecutor(max_workers=4)
    futs = {ex.submit(f): k for k, f in jobs.items()}
    try:
        for fu in cf.as_completed(futs, timeout=40):
            k = futs[fu]
            try:
                v = {"ok": True, "v": fu.result(), "at": time.time()}
            except Exception as e:
                print("brifing:", k, type(e).__name__, flush=True)
                v = {"ok": False, "err": "Kaynağa ulaşılamadı (internet bağlantısı ya da servis yanıtı)." if k in ("hava", "kur") else "Okunamadı.", "at": time.time()}
            if BR["gen"] != gen:
                return
            BR["data"][k] = v
            _push("brifing", {"part": {k: v}})
    except cf.TimeoutError:
        for k in jobs:
            if k not in BR["data"]:
                BR["data"][k] = {"ok": False, "err": "Zaman aşımı.", "at": time.time()}
                _push("brifing", {"part": {k: BR["data"][k]}})
    finally:
        ex.shutdown(wait=False)
    if BR["gen"] != gen:
        return
    BR.update(summary=_brief_text(BR["data"]), busy=False, at=time.time())
    _push("brifing", {"summary": BR["summary"], "done": True})
    if speak and SAY:
        SAY(BR["summary"], "brifing")


def brifing_init() -> dict:
    import settings
    if not BR["data"] or time.time() - BR["at"] > 1800:
        BR["gen"] += 1
        threading.Thread(target=_b_collect, args=(BR["gen"],), daemon=True).start()
    return {"data": BR["data"], "summary": BR["summary"], "busy": BR["busy"], "src": SRC, "auto": bool(settings.get("brifing_oto")), "now": time.time()}


def brifing(text: str, st: dict):
    t = norm(text)
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Brifingi oku, yenile, görevlerim ve hava nasıl diyebilirsiniz. Haber kaynağı bağlı değil. Hiçbir şey arka planda kendiliğinden sorgulanmaz."}
    if re.search(r"\b(otomatik yenile\w*)\b.*\b(aç|etkinleştir)\w*", t):
        __import__("settings").set("brifing_oto", True)
        return {"do": {"auto": True}, "say": "Otomatik yenileme açıldı efendim: sayfa açıkken yarım saatte bir yenilenir."}
    if re.search(r"\b(otomatik yenile\w*)\b.*\b(kapat|durdur)\w*", t):
        __import__("settings").set("brifing_oto", False)
        return {"do": {"auto": False}, "say": "Otomatik yenileme kapandı efendim."}
    if re.search(r"\b(yenile|güncelle|tekrar al|baştan)\w*", t):
        BR["gen"] += 1
        threading.Thread(target=_b_collect, args=(BR["gen"], False), daemon=True).start()
        return {"do": {"reset": True}, "say": "Yeniliyorum efendim."}
    if re.search(r"\b(oku|söyle|dinle|özet)\w*|\bbrifing\w*", t):
        if BR["busy"] or not BR["summary"]:
            return {"say": "Brifing hâlâ hazırlanıyor efendim, birkaç saniye sonra tekrar isteyin."}
        return {"say": BR["summary"]}
    return {"say": "Anlayamadım efendim. Brifingi oku ya da yenile diyebilirsiniz."}


# ================================================================== 4) STARK LABORATUVARI
LF = "stark_lab.json"
LL = threading.RLock()
TIPLER = {"not": "Not", "fikir": "Fikir", "baglanti": "Bağlantı", "kod": "Kod"}
DILLER = ("python", "javascript", "typescript", "c", "cpp", "csharp", "java", "html", "css", "sql", "bash", "powershell", "json", "diğer")


def _ld():
    d = _load(LF, {})
    d.setdefault("projects", [])
    d.setdefault("next", 1)
    d.setdefault("nexti", 1)
    return d


def lab_view(st=None, q: str = "") -> dict:
    with LL:
        d = _ld()
    ps = sorted(d["projects"], key=lambda p: (not p.get("pinned"), -(p.get("updated") or 0)))
    cur = None
    oid = (st or {}).get("open")
    if oid:
        cur = next((p for p in d["projects"] if p["id"] == oid), None)
    ql = q.lower().strip()
    hits = []
    if ql:
        for p in d["projects"]:
            for it in p["items"]:
                if ql in (it["title"] + " " + it.get("body", "") + " " + " ".join(it.get("tags", []))).lower():
                    hits.append({"pid": p["id"], "pname": p["name"], **it})
    lst = [{"id": p["id"], "name": p["name"], "desc": p.get("desc", ""), "tags": p.get("tags", []), "pinned": bool(p.get("pinned")), "updated": p.get("updated"), "n": len(p["items"])}
           for p in ps if not ql or ql in (p["name"] + " " + p.get("desc", "") + " " + " ".join(p.get("tags", []))).lower()]
    return {"projects": lst, "open": cur, "q": q, "hits": hits[:40], "types": TIPLER, "langs": DILLER}


def _touch(p):
    p["updated"] = time.time()


def lab(text: str, st: dict):
    raw = str(text).strip()
    t = norm(text)
    res = lambda say="", q="": {"do": {"data": lab_view(st, q)}, "say": say}
    if st.get("confirm"):
        c = st.pop("confirm")
        if _yes(t):
            with LL:
                d = _ld()
                if c[0] == "p":
                    d["projects"] = [p for p in d["projects"] if p["id"] != c[1]]
                    if st.get("open") == c[1]:
                        st.pop("open", None)
                else:
                    p = next((p for p in d["projects"] if p["id"] == c[1]), None)
                    if p:
                        p["items"] = [i for i in p["items"] if i["id"] != c[2]]
                        _touch(p)
                _save(LF, d)
            return res("Sildim efendim.")
        return res("Vazgeçtim efendim.")
    if raw.startswith("§"):                       # §p|ad|açıklama  §o|id  §e|tip|başlık|dil|gövde  §pin|id  §sp|id  §si|iid  §tag|etiketler  §q|sorgu  §cp|id|ad|açıklama
        c = raw[1:].split("|")
        with LL:
            d = _ld()
            try:
                if c[0] == "p" and c[1].strip():
                    p = {"id": d["next"], "name": c[1].strip()[:80], "desc": (c[2] if len(c) > 2 else "")[:300], "tags": [], "pinned": False, "created": time.time(), "updated": time.time(), "items": []}
                    d["next"] += 1
                    d["projects"].append(p)
                    st["open"] = p["id"]
                    _save(LF, d)
                    return res("Proje oluşturuldu.")
                if c[0] == "o":
                    st["open"] = int(c[1]) if c[1] else None
                    return res("")
                if c[0] == "q":
                    return res("", c[1] if len(c) > 1 else "")
                p = next((p for p in d["projects"] if p["id"] == st.get("open")), None)
                if c[0] == "e" and p:
                    tip = c[1] if c[1] in TIPLER else "not"
                    body = "|".join(c[4:]).strip() if len(c) > 4 else ""
                    title = c[2].strip()[:100]
                    if tip == "baglanti":
                        u = (body or title).strip()
                        if not re.match(r"https?://", u, re.I):
                            return res("Bağlantı http:// ya da https:// ile başlamalı, eklenmedi.")
                        body = u
                    if not (title or body):
                        return res("Boş öğe eklenmedi.")
                    p["items"].append({"id": d["nexti"], "type": tip, "title": title or body[:40], "body": body[:20000], "lang": c[3] if len(c) > 3 and c[3] in DILLER else "", "tags": [], "at": time.time()})
                    d["nexti"] += 1
                    _touch(p)
                    _save(LF, d)
                    return res("Eklendi.")
                if c[0] == "pin":
                    q_ = next((x for x in d["projects"] if x["id"] == int(c[1])), None)
                    if q_:
                        q_["pinned"] = not q_.get("pinned")
                        _save(LF, d)
                    return res("")
                if c[0] == "tag" and p:
                    p["tags"] = [x.strip()[:24] for x in c[1].split(",") if x.strip()][:8]
                    _touch(p)
                    _save(LF, d)
                    return res("Etiketler güncellendi.")
                if c[0] == "cp" and p:
                    p["name"], p["desc"] = c[2].strip()[:80] or p["name"], (c[3] if len(c) > 3 else "")[:300]
                    _touch(p)
                    _save(LF, d)
                    return res("Proje güncellendi.")
                if c[0] == "sp":
                    st["confirm"] = ("p", int(c[1]))
                    return {"say": "Projeyi ve içindeki tüm öğeleri silmemi onaylıyor musunuz? Bu geri alınamaz. Evet ya da hayır deyin."}
                if c[0] == "si" and p:
                    st["confirm"] = ("i", p["id"], int(c[1]))
                    return {"say": "Bu öğeyi silmemi onaylıyor musunuz? Evet ya da hayır deyin."}
                if c[0] == "spo":                              # sayfadaki satır içi onaydan gelir
                    d["projects"] = [x for x in d["projects"] if x["id"] != int(c[1])]
                    if st.get("open") == int(c[1]):
                        st.pop("open", None)
                    _save(LF, d)
                    return res("Proje silindi.")
                if c[0] == "sio" and p:
                    p["items"] = [x for x in p["items"] if x["id"] != int(c[1])]
                    _touch(p)
                    _save(LF, d)
                    return res("Öğe silindi.")
            except (ValueError, IndexError):
                pass
        return res("")
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Proje oluştur iki nokta ad, projeyi aç ad, not ekle, fikir ekle, bağlantı ekle, kod ekle python iki nokta kod, proje ara kelime ve projeleri say diyebilirsiniz. Kod yalnızca saklanır, bu ekran kod çalıştırmaz."}
    if re.search(r"\bproje\w*", t) and re.search(r"\b(oluştur|ekle|başlat|yeni)\w*", t) and ":" in raw:
        return lab("§p|" + raw.split(":", 1)[1].strip(), st)
    if re.search(r"\bprojeleri (say|listele|oku)", t):
        n = len(lab_view(st)["projects"])
        return res(f"{n} projeniz var efendim." if n else "Henüz proje yok efendim.")
    m = re.search(r"\bprojeyi (aç|göster)\w*\s+(.+)$", t)
    if m:
        d = _ld()
        p = next((p for p in d["projects"] if m.group(2).strip() in norm(p["name"])), None)
        if p:
            st["open"] = p["id"]
            return res(f"{p['name']} açıldı efendim.")
        return res("Bu adla bir proje bulamadım efendim.")
    m = re.search(r"\b(proje|öğe)\w* ara\w*\s+(.+)$|\bara\w*[: ]+(.+)$", t)
    if m:
        q = (m.group(2) or m.group(3)).strip()
        v = lab_view(st, q)
        return res(f"{len(v['projects'])} proje, {len(v['hits'])} öğe buldum efendim.", q)
    m = re.match(r"\s*(not|fikir|bağlantı|link|kod)\s*(ekle|kaydet)\w*\s*(python|javascript|js|typescript|c|cpp|csharp|java|html|css|sql|bash|powershell|json)?\s*[:：]\s*(.+)$", raw, re.I | re.S)
    if m:
        if not st.get("open"):
            return {"say": "Önce bir proje açın efendim."}
        tip = {"not": "not", "fikir": "fikir", "bağlantı": "baglanti", "link": "baglanti", "kod": "kod"}[m.group(1).lower()]
        lang = {"js": "javascript"}.get((m.group(3) or "").lower(), (m.group(3) or "").lower())
        body = m.group(4).strip()
        return lab(f"§e|{tip}|{body[:40].splitlines()[0] if body else ''}|{lang}|{body}", st)
    return {"say": "Anlayamadım efendim. Proje oluştur iki nokta ad ya da not ekle iki nokta metin diyebilirsiniz."}


def lab_init() -> dict:
    return lab_view({})


# ================================================================== 5) HOLOGRAFİK DÜNYA
DF = "dunya_yerler.json"
DL = threading.RLock()
DW = {}                    # yer id -> {"v": hava, "at": zaman} (yalnızca RAM)


def _dd():
    d = _load(DF, {})
    d.setdefault("places", [])
    d.setdefault("next", 1)
    return d


def dunya_view(sel=None) -> dict:
    with DL:
        d = _dd()
    return {"places": d["places"], "sel": sel, "weather": {str(k): v for k, v in DW.items()}}


def _w_job(pid, lat, lon):
    try:
        import extras
        j = extras._forecast(lat, lon)
        c, dl = j["current"], j["daily"]
        v = {"temp": round(c["temperature_2m"]), "d": extras.WMO.get(c["weather_code"], "değişken"), "wind": round(c["wind_speed_10m"]),
             "days": [{"hi": round(dl["temperature_2m_max"][i]), "lo": round(dl["temperature_2m_min"][i]), "d": extras.WMO.get(dl["weather_code"][i], ""),
                       "pp": dl["precipitation_probability_max"][i] or 0, "date": dl["time"][i]} for i in range(min(3, len(dl["time"])))], "src": "Open-Meteo"}
        DW[pid] = {"ok": True, "v": v, "at": time.time()}
    except Exception as e:
        print("dünya hava:", type(e).__name__, flush=True)
        DW[pid] = {"ok": False, "err": "Hava verisi alınamadı (internet bağlantısı ya da servis).", "at": time.time()}
    _push("dunya", {"weather": {str(pid): DW[pid]}})


def _geo_job(q):
    import harita
    try:
        g = harita.geocode(q)
        if not g and len(q) > 4:
            for cut in (3, 2, 1):
                g = harita.geocode(q[:-cut])
                if g:
                    break
    except Exception as e:
        _push("dunya", {"err": "Yer araması başarısız: internet bağlantısı ya da arama servisi kullanılamıyor.", "msg": "Yer aranamadı."})
        return
    if not g:
        _push("dunya", {"err": f"“{q}” için sonuç bulunamadı.", "msg": "Yer bulunamadı."})
        return
    with DL:
        d = _dd()
        if any(abs(p["lat"] - g["lat"]) < 0.01 and abs(p["lon"] - g["lon"]) < 0.01 for p in d["places"]):
            _push("dunya", {"err": "Bu yer zaten kayıtlı.", "msg": "Bu yer zaten kayıtlı."})
            return
        p = {"id": d["next"], "name": g["short"][:60], "full": g["name"][:160], "lat": round(g["lat"], 5), "lon": round(g["lon"], 5), "note": "", "plan": "", "at": time.time()}
        d["next"] += 1
        d["places"].append(p)
        _save(DF, d)
    _push("dunya", {"data": dunya_view(p["id"]), "msg": f"{p['name']} kaydedildi."})
    _w_job(p["id"], p["lat"], p["lon"])


def dunya(text: str, st: dict):
    raw = str(text).strip()
    t = norm(text)
    res = lambda say="", sel=None: {"do": {"data": dunya_view(sel)}, "say": say}
    if st.get("confirm"):
        c = st.pop("confirm")
        if _yes(t):
            with DL:
                d = _dd()
                d["places"] = [p for p in d["places"] if p["id"] != c]
                _save(DF, d)
            DW.pop(c, None)
            return res("Yeri kaldırdım efendim.")
        return res("Vazgeçtim efendim.")
    if raw.startswith("§"):                                 # §y|ad|lat|lon  §yd|id|ad|not|plan  §ys|id  §sec|id
        c = raw[1:].split("|")
        try:
            if c[0] == "y":
                lat, lon = float(c[2]), float(c[3])
                if not (-90 <= lat <= 90 and -180 <= lon <= 180) or not c[1].strip():
                    return res("Ad ve geçerli koordinat gerekli.")
                with DL:
                    d = _dd()
                    p = {"id": d["next"], "name": c[1].strip()[:60], "full": "", "lat": round(lat, 5), "lon": round(lon, 5), "note": "", "plan": "", "at": time.time()}
                    d["next"] += 1
                    d["places"].append(p)
                    _save(DF, d)
                threading.Thread(target=_w_job, args=(p["id"], p["lat"], p["lon"]), daemon=True).start()
                return res("Yer kaydedildi.", p["id"])
            if c[0] == "yd":
                with DL:
                    d = _dd()
                    p = next(p for p in d["places"] if p["id"] == int(c[1]))
                    p["name"], p["note"] = c[2].strip()[:60] or p["name"], c[3].strip()[:400]
                    plan = c[4].strip() if len(c) > 4 else ""
                    if plan and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", plan):
                        return res("Plan tarihi gün-ay-yıl biçiminde seçilmeli.", p["id"])
                    p["plan"] = plan
                    _save(DF, d)
                return res("Güncellendi.", p["id"])
            if c[0] == "ys":
                st["confirm"] = int(c[1])
                return {"say": "Bu yeri kayıtlı yerlerden kaldırmamı onaylıyor musunuz? Evet ya da hayır deyin."}
            if c[0] == "yso":                                # sayfadaki satır içi onaydan gelir
                with DL:
                    d = _dd()
                    d["places"] = [p for p in d["places"] if p["id"] != int(c[1])]
                    _save(DF, d)
                DW.pop(int(c[1]), None)
                return res("Yer kaldırıldı.")
            if c[0] == "sec":
                pid = int(c[1])
                p = next((p for p in _dd()["places"] if p["id"] == pid), None)
                if p and (pid not in DW or time.time() - DW[pid]["at"] > 1800):
                    threading.Thread(target=_w_job, args=(pid, p["lat"], p["lon"]), daemon=True).start()
                return res("", pid)
        except (ValueError, IndexError, StopIteration):
            return res("İşlem uygulanamadı: geçersiz değer.")
        return res("")
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Yer ekle iki nokta Paris, kayıtlı yerlerim, Paris'i göster, Paris hava nasıl ve çık diyebilirsiniz. Konumunuz hiçbir zaman otomatik alınmaz."}
    if re.search(r"\byer\w*", t) and re.search(r"\b(ekle|kaydet)\w*", t) and ":" in raw:
        q = raw.split(":", 1)[1].strip()
        if not q:
            return {"say": "Yer adını iki nokta sonrası söyler misiniz efendim?"}
        threading.Thread(target=_geo_job, args=(q,), daemon=True).start()
        return {"do": {"busy": True}, "say": f"{q} aranıyor efendim."}
    if re.search(r"\b(kayıtlı yer\w*|yerlerim|yerleri say|yerleri oku)\b", t):
        ps = _dd()["places"]
        return res(("Kayıtlı yerleriniz: " + ", ".join(p["name"] for p in ps[:10]) + ".") if ps else "Henüz kayıtlı yeriniz yok efendim.")
    ps = _dd()["places"]
    p = next((p for p in ps if norm(p["name"]) and norm(p["name"]) in t), None)
    if p:
        if p["id"] not in DW or time.time() - DW[p["id"]]["at"] > 1800:
            threading.Thread(target=_w_job, args=(p["id"], p["lat"], p["lon"]), daemon=True).start()
        extra = f" Plan tarihi {p['plan']}." if p.get("plan") else ""
        w = DW.get(p["id"])
        if re.search(r"\bhava\w*", t) and w and w.get("ok"):
            return res(f"{p['name']} için hava {w['v']['d']}, {w['v']['temp']} derece.{extra}", p["id"])
        return res(f"{p['name']} seçildi efendim.{extra}", p["id"])
    return {"say": "Anlayamadım efendim. Yer ekle iki nokta yer adı ya da kayıtlı yerlerim diyebilirsiniz."}


def dunya_init() -> dict:
    return dunya_view()


# ================================================================== 6) GÜVENLİK MERKEZİ
EV = []            # yalnızca bu oturumda, mod açıkken GÖZLENEN durum değişiklikleri (RAM)
LAST = {}


def _hms(ts=None):
    return datetime.datetime.fromtimestamp(ts or time.time()).strftime("%H:%M:%S")


def guvenlik_view() -> dict:
    import settings
    now = time.time()
    h = HOOK() if HOOK else {}
    cards = []
    cards.append({"id": "sunucu", "name": "Yerel sunucu", "state": "ok", "text": "127.0.0.1:8765 dinliyor (yalnızca bu bilgisayar); her açılışta değişen jeton ve kaynak denetimi gerekir.",
                  "src": "main.py (WebSocket/uvicorn)", "at": now, "extra": f"Bağlı arayüz: {h.get('clients', '?')}"})
    mm = h.get("mic_muted")
    cards.append({"id": "mikrofon", "name": "Mikrofon", "state": "unk" if mm is None else "warn" if mm else "ok",
                  "text": "Durum okunamadı." if mm is None else ("Sessize alınmış; Jarvis seni duymuyor." if mm else "Açık; Jarvis uyandırma sözcüğünü dinliyor."), "src": "voice.muted", "at": now})
    try:
        import remote
        import lan
        rp, lp = remote.paired_count(), lan.paired_count()
        cards.append({"id": "cihaz", "name": "Eşleşmiş cihazlar", "state": "ok" if (rp + lp) == 0 else "info",
                      "text": f"İnternet/Tailscale telefon eşleşmesi: {rp}; Wi-Fi telefon eşleşmesi: {lp}. Cihaz anahtarları gösterilmez.", "src": "remote.py, lan.py", "at": now})
        nets = []
        if remote.S["on"]:
            nets.append(f"internet (Cloudflare tüneli; eşleşmiş cihaz gerekir, {int(max(0, remote.S['until'] - now) // 60)} dk sonra kapanır)" if not remote.S.get("auto") else "internet (Cloudflare tüneli, otomatik mod)")
        if remote.TS["on"]:
            nets.append("Tailscale ağındaki cihazlarınız (8768)")
        if lan.S["on"]:
            nets.append("aynı yerel ağ (yalnızca özel IP aralıkları, 8766)")
        full = bool(settings.get("uzak_tam_kontrol")) and remote.TS["on"]
        cards.append({"id": "uzak", "name": "Uzaktan erişim", "state": "warn" if nets else "ok",
                      "text": ("AÇIK. Erişilebildiği ağlar: " + "; ".join(nets) + ".") if nets else "Kapalı; Jarvis şu an hiçbir ağa açık değil.",
                      "extra": ("Telefondan tam kontrol AÇIK (yalnızca Tailscale)." if full else "Telefondan tam kontrol kapalı."), "src": "remote.S, remote.TS, lan.S, ayar uzak_tam_kontrol", "at": now})
    except Exception as e:
        cards.append({"id": "uzak", "name": "Uzaktan erişim", "state": "unk", "text": "Bu konuda ölçüm yok: durum okunamadı.", "src": "remote.py", "at": now})
    try:
        import vpn
        s = vpn.status()
        txt = {"on": "Bağlı.", "off": "Kapalı.", "connecting": "Bağlanıyor.", "reconnecting": "Yeniden bağlanıyor."}.get(s["state"], str(s["state"]))
        cards.append({"id": "vpn", "name": "VPN (Jarvis tarayıcısı)", "state": "ok" if s["state"] == "on" else "info", "text": txt + (" Ölüm anahtarı açık." if s.get("kill") else ""),
                      "src": "vpn.status()", "at": now})
    except Exception:
        cards.append({"id": "vpn", "name": "VPN", "state": "unk", "text": "Bu konuda ölçüm yok.", "src": "vpn.py", "at": now})
    cur = {c["id"]: c["text"] for c in cards}
    if LAST:
        for k, v in cur.items():
            if LAST.get(k) is not None and LAST[k] != v and k in ("mikrofon", "cihaz", "uzak", "vpn"):
                EV.append({"t": _hms(), "text": f"{next(c['name'] for c in cards if c['id'] == k)}: {v}"})
    LAST.clear()
    LAST.update(cur)
    del EV[:-30]
    return {"cards": cards, "events": list(reversed(EV)), "since": _hms(LAST_START[0]), "none": "Jarvis kalıcı bir güvenlik olay günlüğü tutmuyor; yalnızca bu pencere açıkken gözlenen değişiklikler listelenir. Saldırı tespiti yapılmaz.", "t": now}


LAST_START = [time.time()]


def guvenlik_init() -> dict:
    LAST_START[0] = time.time()
    LAST.clear()
    EV.clear()
    return guvenlik_view()


def guvenlik(text: str, st: dict):
    t = norm(text)
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Durum, uzaktan erişim açık mı, eşleşmiş cihazlar, mikrofon, VPN ve çık diyebilirsiniz. Bu mod ayar değiştirmez, tarama yapmaz."}
    v = guvenlik_view()
    by = {c["id"]: c for c in v["cards"]}
    if re.search(r"\buzak\w*|\berişim\w*", t):
        return {"do": {"data": v}, "say": by["uzak"]["text"] + " " + by["uzak"].get("extra", "")}
    if re.search(r"\bcihaz\w*|\beşleş\w*", t):
        return {"do": {"data": v}, "say": by["cihaz"]["text"]}
    if re.search(r"\bmikrofon\w*", t):
        return {"do": {"data": v}, "say": by["mikrofon"]["text"]}
    if re.search(r"\bvpn\b", t):
        return {"do": {"data": v}, "say": by["vpn"]["text"]}
    pc = [c["name"] for c in v["cards"] if c["state"] == "warn"]
    return {"do": {"data": v}, "say": ("Dikkat edilecekler: " + ", ".join(pc) + ". " if pc else "") + "Bu konuda yalnızca Jarvis'in bildiği durumları gösterebilirim; tehdit taraması yapmıyorum."}


# ================================================================== 7) ÇOKLU ASİSTAN KÖPRÜSÜ
def kopru_view() -> dict:
    import settings
    import voice
    h = HOOK() if HOOK else {}
    active = h.get("persona") or "jarvis"
    tts = settings.get("tts")
    tune, pv = voice.PERSONA_TUNE, voice.PERSONA_VOICE
    cards = []
    spec = {
        "jarvis": ("Jarvis", "Ana asistan: sesle komut yönlendirme, sahne modları, ev/PC kontrolü, yerel LLM yedeği.", ["Hazır komut yönlendirici (router)", "Araç kullanan LLM (tools.TOOLS)", "Tüm sahne modları", "Hafıza (memory.json)"],
                 f"Ana ses ({'Edge TTS' if tts == 'edge' else 'Piper'}), Jarvis FX {'açık' if settings.get('jarvis_fx') else 'kapalı'}"),
        "friday": ("Friday", "Araç kullanan, kısa ve pratik yardımcı. Kendi geçmişi ve öğrendikleri var.", ["Jarvis'in araçlarını kullanır (güvenlik katmanı aynı)", "Tehlikeli işlemde sözlü onay", "İşlem günlüğü (yalnızca RAM)", "Arka planda pratik konu öğrenme"], None),
        "ultron": ("Ultron", "Direnen, kendi kendine öğrenen sohbet kişiliği. PC'yi kontrol etmez.", ["Serbest sohbet (araç yok)", "Arka planda genel konu araştırma", "Geçmiş yalnızca RAM'de"], None),
        "luna": ("Luna", "Sakin, yumuşak sohbet kişiliği. PC'yi kontrol etmez.", ["Serbest sohbet (araç yok)", "Arka planda genel konu araştırma", "Geçmiş yalnızca RAM'de"], None),
    }
    for k, (nm, desc, caps, sv) in spec.items():
        if sv is None:
            tn = tune.get(k, {}).get("tr")
            vv = pv.get(k, {}).get("tr")
            sv = ("Ses: " + (vv or "Jarvis'in sesi") + (f", hız {tn[0]}, perde {tn[1]}" if tn else ""))
        learn = None
        if k != "jarvis":
            learn = bool(settings.get(f"{k}_ogren"))
        state = "active" if k == active else "ready"
        cards.append({"id": k, "name": nm, "desc": desc, "caps": caps, "voice": sv, "state": state, "learn": learn, "separate": k != "jarvis"})
    return {"cards": cards, "active": active, "scene": h.get("scene"), "t": time.time(),
            "note": "Asistanlar ayrı kişiliklerdir; ortak hafıza yoktur, her biri kendi geçmişini ve notlarını tutar."}


def kopru_init() -> dict:
    return kopru_view()


def kopru(text: str, st: dict):
    t = norm(text)
    if re.search(r"\b(yardım|komutlar)\b", t):
        return {"say": "Friday'i aç, Ultron'u aç, Luna'yı aç diyebilirsiniz. Bunlar ayrı bir moda geçiştir; bu pencere kapanır. Jarvis'e dönmek için çık deyin."}
    for k in ("friday", "ultron", "luna"):
        if k in t and re.search(r"\b(aç|çağır|başlat|geç|konuş)\w*", t):
            return {"do": {"open": k}, "say": ""}
    return {"do": {"data": kopru_view()}, "say": "Hangi asistan efendim? Friday, Ultron ya da Luna."}
