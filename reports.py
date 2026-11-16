"""Rapor modu: yazılan raporlar yalnızca bu bilgisayarda (raporlar.json) taslak olarak durur. 'Gönder' denince rapor, sabit tanımlı tek alıcıya
WhatsApp masaüstü uygulamasından iletilir ve iletildikten sonra rapor diskten ve bellekten tamamen silinir (dosyanın eski içeriği üzerine yazılır).
Alıcı numarası yalnızca config.json'daki report_phone alanından okunur; sayfa, ses ya da başka hiçbir yol bunu değiştiremez."""
import datetime
import json
import os
import re
import secrets
import tempfile
import threading

import settings

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raporlar.json")
DEFAULT_PHONE = ""                         # config.json: report_phone (örn. 905xxxxxxxxx); boşsa rapor gönderilmez
MAX_REPORTS, MAX_CATS, MAX_BODY, MAX_TITLE, MAX_TPL = 100, 30, 12000, 120, 20
DEFAULT_TEMPLATES = [
    {"name": "Ders raporu", "title": "Ders raporu", "body": "Sınıf / konu:\nİşlenenler:\nÖdev:\nÖğrenci durumu:\nNotlar:", "cat": "Ders"},
    {"name": "Günlük rapor", "title": "Günlük rapor", "body": "Yapılanlar:\nYapılacaklar:\nNotlar:", "cat": ""},
    {"name": "Haftalık rapor", "title": "Haftalık rapor", "body": "Bu hafta yapılanlar:\nSorunlar:\nGelecek hafta planı:", "cat": ""},
]
_lock = threading.RLock()
_sending: set = set()
SEND_HOOK = None                          # main.py: raporu arka planda gönderen işlev (sesli komut için)

DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def phone() -> str:
    p = re.sub(r"\D", "", str(settings.get("report_phone") or DEFAULT_PHONE))
    return p if 10 <= len(p) <= 15 else DEFAULT_PHONE


def phone_label() -> str:
    p = phone()
    return ("(numara ayarlı değil)" if not p else f"+{p[:2]} {p[2:5]} {p[5:8]} {p[8:10]} {p[10:]}" if len(p) == 12 else f"+{p}")


def contact_name() -> str:
    return str(settings.get("report_contact") or "")[:40]


def _s(v, n) -> str:
    return " ".join(str(v if v is not None else "").replace("\x00", " ").split())[:n]


def _text(v, n) -> str:
    return "\n".join(l.rstrip() for l in str(v if v is not None else "").replace("\x00", " ").replace("\r", "").split("\n")).strip("\n")[:n]


def _date(v) -> str:
    v = str(v or "")
    try:
        datetime.date.fromisoformat(v)
        return v
    except ValueError:
        return ""


def _now() -> datetime.datetime:
    return datetime.datetime.now()


def _load() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    cats, seen = [], set()
    for c in (d.get("categories") if isinstance(d, dict) and isinstance(d.get("categories"), list) else [])[:MAX_CATS]:
        c = _s(c, 30)
        if c and c.lower() not in seen:
            seen.add(c.lower())
            cats.append(c)
    reps = []
    for r in (d.get("reports") if isinstance(d, dict) and isinstance(d.get("reports"), list) else [])[:MAX_REPORTS]:
        if not isinstance(r, dict) or not re.fullmatch(r"r[0-9a-f]{8}", str(r.get("id", ""))):
            continue
        cat = _s(r.get("cat"), 30)
        reps.append({"id": r["id"], "title": _s(r.get("title"), MAX_TITLE), "body": _text(r.get("body"), MAX_BODY), "cat": cat if cat.lower() in seen else "",
                     "date": _date(r.get("date")) or _now().date().isoformat(), "time": _s(r.get("time"), 5) if re.fullmatch(r"\d\d:\d\d", str(r.get("time", ""))) else "",
                     "mod": str(r.get("mod", ""))[:19], "status": _s(r.get("status"), 80)})
    raw_t = d.get("templates") if isinstance(d, dict) and isinstance(d.get("templates"), list) else None
    tpls = [dict(t) for t in DEFAULT_TEMPLATES] if raw_t is None else [
        {"name": _s(t.get("name"), 30), "title": _s(t.get("title"), MAX_TITLE), "body": _text(t.get("body"), 4000), "cat": _s(t.get("cat"), 30)}
        for t in raw_t[:MAX_TPL] if isinstance(t, dict) and _s(t.get("name"), 30)]
    rm = d.get("reminder") if isinstance(d, dict) and isinstance(d.get("reminder"), dict) else {}
    days = sorted({int(x) for x in rm.get("days", []) if isinstance(x, int) and 0 <= x <= 6}) if isinstance(rm.get("days", []), list) else []
    tm = str(rm.get("time", ""))
    reminder = {"days": days, "time": tm, "last": _date(rm.get("last"))} if days and re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", tm) else {}
    return {"categories": cats, "reports": reps, "templates": tpls, "reminder": reminder}


def _wipe_file() -> None:
    """Eski dosyanın içeriğinin üzerine sıfır yazar (disk üzerinde silinen rapor metni kalmasın)."""
    try:
        n = os.path.getsize(PATH)
        with open(PATH, "r+b") as f:
            f.write(b"\x00" * n)
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        pass


def _save(d: dict, wipe: bool = False) -> None:
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(PATH), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        if wipe:
            _wipe_file()
        os.replace(tmp, PATH)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def view() -> dict:
    with _lock:
        d = _load()
    return {"categories": d["categories"], "reports": sorted(d["reports"], key=lambda r: r["mod"], reverse=True), "templates": d["templates"],
            "reminder": reminder_label(d["reminder"]), "to": phone_label(), "today": _now().date().isoformat()}


def init_payload():
    return view()


# ------------------------------------------------------------------ kategoriler
def add_category(name: str) -> str:
    name = _s(name, 30)
    if not name:
        return ""
    with _lock:
        d = _load()
        ex = next((c for c in d["categories"] if c.lower() == name.lower()), None)
        if ex:
            return ex
        if len(d["categories"]) >= MAX_CATS:
            return ""
        d["categories"].append(name)
        _save(d)
    return name


def find_category(name: str) -> str:
    n = _s(name, 30).lower()
    with _lock:
        for c in _load()["categories"]:
            if c.lower() == n:
                return c
    return ""


def delete_category(name: str) -> bool:
    n = _s(name, 30).lower()
    with _lock:
        d = _load()
        keep = [c for c in d["categories"] if c.lower() != n]
        if len(keep) == len(d["categories"]):
            return False
        d["categories"] = keep
        for r in d["reports"]:
            if r["cat"].lower() == n:
                r["cat"] = ""
        _save(d)
    return True


# ------------------------------------------------------------------ raporlar
def save(rid: str, title: str, body: str, cat: str = "", date: str = "") -> dict:
    """Taslağı oluşturur ya da günceller. Döner: {'id', ...}"""
    title, body = _s(title, MAX_TITLE), _text(body, MAX_BODY)
    with _lock:
        d = _load()
        cur = next((r for r in d["reports"] if r["id"] == rid), None) if re.fullmatch(r"r[0-9a-f]{8}", str(rid or "")) else None
        if cur is None:
            if len(d["reports"]) >= MAX_REPORTS:
                return {}
            now = _now()
            cur = {"id": "r" + secrets.token_hex(4), "date": now.date().isoformat(), "time": now.strftime("%H:%M"), "status": ""}
            d["reports"].append(cur)
        c = _s(cat, 30)
        cur.update(title=title, body=body, cat=c if c.lower() in {x.lower() for x in d["categories"]} else "", mod=_now().isoformat(timespec="seconds"), status="")
        dt = _date(date)
        if dt:
            if dt != cur["date"]:
                cur["time"] = ""                  # tarih elle değiştirildi: oluşturma saati artık geçerli değil
            cur["date"] = dt
        _save(d)
    return {"id": cur["id"]}


def get(rid: str):
    with _lock:
        return next((dict(r) for r in _load()["reports"] if r["id"] == rid), None)


def delete(rid: str) -> bool:
    with _lock:
        d = _load()
        keep = [r for r in d["reports"] if r["id"] != rid]
        if len(keep) == len(d["reports"]):
            return False
        d["reports"] = keep
        _save(d, wipe=True)
    return True


def set_status(rid: str, status: str) -> None:
    with _lock:
        d = _load()
        r = next((x for x in d["reports"] if x["id"] == rid), None)
        if r:
            r["status"] = _s(status, 80)
            _save(d)


# ------------------------------------------------------------------ mesaj biçimi
def format_message(r: dict) -> str:
    """Kategori en başta, sonra rapor tarihi, sonra başlık ve metin."""
    try:
        dt = datetime.date.fromisoformat(r["date"])
        date = f"{dt.day} {MONTHS[dt.month - 1]} {dt.year} {DAYS[dt.weekday()]}" + (f", {r['time']}" if r.get("time") else "")
    except (ValueError, KeyError):
        date = r.get("date", "")
    lines = []
    if r.get("cat"):
        lines.append(f"Kategori: {r['cat']}")
    lines.append(f"Rapor tarihi: {date}")
    lines.append("")
    if r.get("title"):
        lines.append(f"*{r['title']}*")
        lines.append("")
    lines.append(r.get("body", ""))
    return "\n".join(lines).strip()


# ------------------------------------------------------------------ gönderme
def send(rid: str):
    """Raporu gönderir; yalnızca 'sent' ise raporu tamamen siler. Dönüş: (durum, mesaj). Aynı rapor aynı anda iki kez gönderilmez."""
    r = get(rid)
    if not r:
        return "failed", "Rapor bulunamadı."
    if not (r["body"].strip() or r["title"].strip()):
        return "failed", "Rapor boş, göndermedim."
    with _lock:
        if rid in _sending:
            return "failed", "Bu rapor zaten gönderiliyor."
        _sending.add(rid)
    try:
        import whatsapp
        if not phone():
            return "failed", "Rapor numarası ayarlı değil; config.json içine report_phone ekleyin."
        text = format_message(r)
        res = whatsapp.send_report(phone(), text, contact_name())
        text = ""
        if res == "sent":
            delete(rid)
            return "sent", "Rapor iletildi ve hafızadan tamamen silindi."
        if res == "unverified":
            set_status(rid, "gönderilmiş olabilir, WhatsApp'ta kontrol edin")
            return "unverified", "Enter'a bastım ama iletildiğini doğrulayamadım. Rapor silinmedi, lütfen WhatsApp'ta kontrol edin."
        why = res.split(":", 1)[1] if ":" in res else res
        set_status(rid, "gönderilemedi: " + why[:50])
        return "failed", f"Rapor gönderilemedi ({why}). Hiçbir mesaj gitmedi, rapor taslak olarak duruyor."
    finally:
        with _lock:
            _sending.discard(rid)


# ------------------------------------------------------------------ şablonlar
def add_template(name: str, title: str, body: str, cat: str = "") -> str:
    """Verilen içerikten şablon kaydeder (aynı adlı varsa günceller). Döner: kaydedilen ad ('' = olmadı)."""
    name = _s(name, 30)
    if not name:
        return ""
    with _lock:
        d = _load()
        t = {"name": name, "title": _s(title, MAX_TITLE), "body": _text(body, 4000), "cat": _s(cat, 30)}
        i = next((i for i, x in enumerate(d["templates"]) if x["name"].lower() == name.lower()), None)
        if i is None:
            if len(d["templates"]) >= MAX_TPL:
                return ""
            d["templates"].append(t)
        else:
            d["templates"][i] = t
        _save(d)
    return name


def find_template(name: str):
    n = _s(name, 30).lower()
    if not n:
        return None
    with _lock:
        ts = _load()["templates"]
    return next((t for t in ts if t["name"].lower() == n), None) or next((t for t in ts if n in t["name"].lower() or t["name"].lower() in n), None)


def delete_template(name: str) -> bool:
    n = _s(name, 30).lower()
    with _lock:
        d = _load()
        keep = [t for t in d["templates"] if t["name"].lower() != n]
        if len(keep) == len(d["templates"]):
            return False
        d["templates"] = keep
        _save(d)
    return True


# ------------------------------------------------------------------ hatırlatıcı (haftalık rapor yazma vakti)
def reminder_label(rm: dict = None) -> str:
    rm = _load()["reminder"] if rm is None else rm
    if not rm:
        return ""
    days = rm["days"]
    who = "her gün" if len(days) == 7 else "hafta içi her gün" if days == [0, 1, 2, 3, 4] else ", ".join(DAYS[i] for i in days)
    return f"{who} {rm['time']}"


def set_reminder(days, time_hhmm: str) -> str:
    days = sorted({int(x) for x in days if isinstance(x, int) and 0 <= x <= 6})
    if not days or not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(time_hhmm)):
        return ""
    with _lock:
        d = _load()
        d["reminder"] = {"days": days, "time": time_hhmm, "last": ""}
        _save(d)
    return reminder_label(d["reminder"])


def clear_reminder() -> bool:
    with _lock:
        d = _load()
        had = bool(d["reminder"])
        d["reminder"] = {}
        _save(d)
    return had


def due_now(now=None) -> bool:
    """Hatırlatma saati geldiyse (aynı gün bir kez; Jarvis o sırada kapalıysa en fazla 3 saat geç) True döner ve bugünü işaretler."""
    now = now or _now()
    with _lock:
        d = _load()
        rm = d["reminder"]
        if not rm or now.weekday() not in rm["days"] or rm.get("last") == now.date().isoformat():
            return False
        h, m = map(int, rm["time"].split(":"))
        due = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if not (due <= now <= due + datetime.timedelta(hours=3)):
            return False
        rm["last"] = now.date().isoformat()
        _save(d)
    return True
