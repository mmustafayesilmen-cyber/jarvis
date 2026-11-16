"""Takvim/randevu (agenda.json): tarihli hatırlatmalar. "Pazartesi 9'da dişçi randevum var", "yarın akşam 8'de maç ekle".
Zamanı gelince hatırlatıcı sistemi (reminders.json) üzerinden sesli haber verir; 30 dakikadan uzaksa ayrıca 30 dk önceden de haber verir."""
import datetime, json, os, re, threading

import reminders

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agenda.json")
_lock = threading.Lock()
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
_AY = {a.lower(): i + 1 for i, a in enumerate(AYLAR)}
_GUN = {g.lower(): i for i, g in enumerate(GUNLER)}


def _load() -> list:
    try:
        with open(PATH, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _save(items):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------------ ayrıştırma
def parse_when(text: str, now=None):
    """Cümleden (datetime, kalan_metin, saat_belirtildi_mi) çıkarır; tarih bulunamazsa None."""
    now = now or datetime.datetime.now()
    s = " " + text + " "
    date, hit = None, False

    def cut(m):
        nonlocal s
        s = s[:m.start()] + " " + s[m.end():]

    m = re.search(r"\b(\d{1,3}) gün sonra\b", s)
    if m:
        date, hit = (now + datetime.timedelta(days=int(m.group(1)))).date(), True
        cut(m)
    if not hit:
        m = re.search(r"\b(\d{1,2})\s+(" + "|".join(_AY) + r")\w*(?:\s+(\d{4}))?", s)
        if m:
            day, mon = int(m.group(1)), _AY[m.group(2)]
            year = int(m.group(3)) if m.group(3) else now.year
            try:
                date = datetime.date(year, mon, day)
                if not m.group(3) and date < now.date():
                    date = datetime.date(year + 1, mon, day)
                hit = True
                cut(m)
            except ValueError:
                return None
    if not hit:
        m = re.search(r"\b(öbür gün|ertesi gün)\w*", s)
        if m:
            date, hit = (now + datetime.timedelta(days=2)).date(), True
            cut(m)
    if not hit:
        m = re.search(r"\b(bugün|yarın)\w*", s)
        if m:
            date, hit = (now + datetime.timedelta(days=1 if m.group(1) == "yarın" else 0)).date(), True
            cut(m)
    if not hit:
        m = re.search(r"\b(haftaya\s+)?(" + "|".join(_GUN) + r")\w*(\s+günü)?", s)
        if m:
            wd = _GUN[m.group(2)]
            delta = (wd - now.weekday()) % 7
            if m.group(1):
                delta += 7 if delta < 7 and not (delta == 0) else 0
                if delta == 0:
                    delta = 7
            date, hit = (now + datetime.timedelta(days=delta)).date(), True
            cut(m)
            pending_same_day = delta == 0 and not m.group(1)
        else:
            pending_same_day = False
    else:
        pending_same_day = False
    if not hit:
        return None
    # saat
    hour = minute = None
    period = re.search(r"\b(sabah|öğleden sonra|öğlen|akşam|gece|öğle)\b", s)
    m = re.search(r"(?:saat\s+)?\b(\d{1,2})\s*[:. ]\s*(\d{2})\b", s) or re.search(r"saat\s+(\d{1,2})\b(?:\s+(buçuk))?", s) \
        or re.search(r"\b(\d{1,2})\s*(buçuk)\b", s)
    if m:
        hour = int(m.group(1))
        if len(m.groups()) >= 2 and m.group(2) and m.group(2).isdigit():
            minute = int(m.group(2))
        elif len(m.groups()) >= 2 and m.group(2) == "buçuk":
            minute = 30
        else:
            minute = 0
        cut(m)
    else:
        m = re.search(r"\b(\d{1,2})\s*(?:da|de|ta|te)\b", s)       # "9'da" (kesme işareti silinmiş olabilir)
        if m and 0 <= int(m.group(1)) <= 24:
            hour, minute = int(m.group(1)), 0
            cut(m)
    if hour is None and period:
        hour, minute = {"sabah": 9, "öğle": 12, "öğlen": 12, "öğleden sonra": 15, "akşam": 19, "gece": 22}[period.group(1)], 0
    if period:
        s = s.replace(period.group(0), " ", 1)
        if hour is not None and period.group(1) in ("akşam", "öğleden sonra", "gece") and hour < 12:
            hour += 12
        if period.group(1) == "gece" and hour == 12:
            hour = 0
    elif hour is not None and 1 <= hour <= 6:         # "saat 3" demek büyük olasılıkla öğleden sonra
        hour += 12
    timed = hour is not None
    if not timed:
        hour, minute = 9, 0
    if hour > 23 or minute > 59:
        return None
    when = datetime.datetime.combine(date, datetime.time(hour, minute))
    if when <= now and pending_same_day:
        when += datetime.timedelta(days=7)
    return when, " ".join(s.split()), timed


def _title(rest: str) -> str:
    rest = re.sub(r"\b(bana|benim|takvime|takvimime|takvimimize|ekle\w*|kaydet\w*|hatırlat\w*|unutturma|var|olacak|not al|not|diye|lütfen|saat|için|söyle)\b", " ", rest)
    rest = re.sub(r"\s+", " ", rest).strip(" ,.")
    return re.sub(r"^(da|de|ta|te)\s+", "", rest)       # "3 te dişçi" -> "dişçi"


# ------------------------------------------------------------------ komutlar
def fmt_when(when, timed=True, now=None) -> str:
    now = now or datetime.datetime.now()
    d = when.date()
    delta = (d - now.date()).days
    if delta == 0:
        day = "bugün"
    elif delta == 1:
        day = "yarın"
    elif 1 < delta < 7:
        day = GUNLER[d.weekday()]
    else:
        day = f"{d.day} {AYLAR[d.month - 1]} {GUNLER[d.weekday()]}"
    return f"{day} saat {when:%H:%M}" if timed else day


def add_event(raw: str, now=None):
    """Cümleyi ayrıştırır, kaydeder. None = takvim komutu değil / tarih yok."""
    now = now or datetime.datetime.now()
    p = parse_when(raw, now)
    if not p:
        return None
    when, rest, timed = p
    title = _title(rest)
    if not title:
        return "Neyi kaydedeceğimi anlayamadım efendim. Örneğin: pazartesi saat 9'da dişçi randevum var."
    if when <= now:
        return "Bu zaman geçmişte kaldı efendim, ileri bir tarih söyler misiniz?"
    secs = (when - now).total_seconds()
    dues = [reminders.add_at(secs, title, "reminder")]
    if secs > 31 * 60:
        dues.append(reminders.add_at(secs - 30 * 60, f"{title}, yarım saat sonra", "reminder"))
    with _lock:
        items = _load()
        if any(abs(i["when"] - when.timestamp()) < 60 and i["title"] == title for i in items):
            for d in dues:
                reminders.cancel_due(d)
            return "Bu kayıt takvimde zaten var efendim."
        items.append({"when": when.timestamp(), "title": title, "timed": timed, "dues": dues})
        _save(items)
    tail = "" if timed else " Saat söylemediğiniz için sabah 9 olarak kaydettim."
    return f"Tamam efendim, {fmt_when(when, now=now)} için {title} takvime eklendi, zamanı gelince hatırlatacağım.{tail}"


def upcoming(days: int = 7, start=None, end=None, now=None):
    now = now or datetime.datetime.now()
    with _lock:
        items = [i for i in _load() if i["when"] > now.timestamp() - 60]
        _save(items)                      # geçmişleri temizle
    lo = start or now
    hi = end or now + datetime.timedelta(days=days)
    return sorted([i for i in items if lo.timestamp() <= i["when"] < hi.timestamp()], key=lambda i: i["when"])


def say_list(items, empty: str, now=None) -> str:
    now = now or datetime.datetime.now()
    if not items:
        return empty
    parts = [f"{fmt_when(datetime.datetime.fromtimestamp(i['when']), i.get('timed', True), now)} {i['title']}" for i in items[:8]]
    return f"{len(items)} kaydınız var efendim: " + "; ".join(parts) + "."


def delete_event(keyword: str) -> str:
    k = keyword.strip().lower()
    if not k:
        return "Hangi kaydı sileceğimi anlayamadım efendim."
    with _lock:
        items = _load()
        hit = [i for i in items if k in i["title"].lower()]
        if not hit:
            return "Bununla ilgili bir takvim kaydı bulamadım efendim."
        if len(hit) > 1:
            return f"{len(hit)} kayıt eşleşti efendim, biraz daha belirgin söyler misiniz?"
        for d in hit[0].get("dues", []):
            reminders.cancel_due(d)
        _save([i for i in items if i is not hit[0] and i != hit[0]])
    return f"{hit[0]['title']} kaydını sildim efendim."


def route(t: str, raw: str, now=None):
    """t = router normu, raw = noktalaması korunmuş metin (saat için)."""
    now = now or datetime.datetime.now()
    low = raw.replace("İ", "i").replace("I", "ı").lower()
    low = re.sub(r"['’]", "", low)
    low = re.sub(r"[^\w\s:.,]", " ", low)
    low = " ".join(low.split())
    # sil
    m = re.fullmatch(r"(.+?)\s*(?:randevusunu|randevumu|kaydını|kaydını|etkinliğini|planını)?\s*(?:sil|iptal et|kaldır|takvimden sil)", low)
    if m and re.search(r"randevu|takvim|kayd|etkinlik|plan", low):
        return delete_event(re.sub(r"\b(takvimden|takvimdeki|takvimimdeki|randevusunu|randevumu|kaydını|etkinliğini|planını)\b", " ", m.group(1)).strip())
    # listele
    if re.search(r"\btakvim\w*|\brandevu\w*|\bne var\b|\bneler var\b|\bplan\w*", low) and not re.search(r"\b(ekle|kaydet|var|hatırlat)\b.*\b(ekle|kaydet|hatırlat)\b", low):
        if re.search(r"takvim\w*|randevu\w*|ne var|neler var|planım", low) and re.search(r"\b(ne|neler|hangi|oku|söyle|göster|var mı|listele|nedir)\b|takvimim$|takvimimi", low):
            if re.search(r"ders", low):
                return None
            if re.search(r"\bbugün\b", low):
                s = datetime.datetime.combine(now.date(), datetime.time.min)
                return say_list(upcoming(start=now, end=s + datetime.timedelta(days=1), now=now), "Bugün için takvimde bir şey yok efendim.", now)
            if re.search(r"\byarın\b", low):
                s = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time.min)
                return say_list(upcoming(start=s, end=s + datetime.timedelta(days=1), now=now), "Yarın için takvimde bir şey yok efendim.", now)
            if re.search(r"\bay\b|aylık|bu ay", low):
                return say_list(upcoming(30, now=now), "Önümüzdeki 30 günde takvimde bir şey yok efendim.", now)
            return say_list(upcoming(7, now=now), "Önümüzdeki bir hafta için takvimde bir şey yok efendim.", now)
    # ekle: tarih + (var|ekle|kaydet|hatırlat|randevu|takvim); sorular (hangi dersler var, hava nasıl...) kayıt değildir
    if re.search(r"\b(hangi|nasıl|nedir|kaç|kim|ne zaman|dersler\w*|derslerim|ders programı|hava\w*|mı|mi|mu|mü)\b", low):
        return None
    if re.search(r"\b(ekle\w*|kaydet\w*|hatırlat\w*|randevu\w*|takvim\w*|var|planım|toplantı\w*|sınav\w*|yazılı)\b", low):
        return add_event(low, now)
    return None
