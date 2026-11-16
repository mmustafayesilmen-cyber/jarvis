"""Sınav takvimi ve günlük çalışma önerisi. Sınavlar sinav.json'da (yalnızca yerel, gitignored). Ders programı schedule.py'den okunur (değiştirilmez);
öneri, en yakın sınavın kalan gününe ve bugünkü pomodoro odak süresine göre hesaplanır; uydurma yok, yalnızca kayıtlı veriler."""
import datetime
import json
import os
import threading

import schedule

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sinav.json")
_lock = threading.Lock()


def _load() -> list:
    try:
        with open(FILE, encoding="utf-8") as f:
            d = json.load(f)
        return [x for x in d if isinstance(x, dict) and x.get("ders") and x.get("tarih")] if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _save(items: list) -> None:
    with open(FILE + ".tmp", "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    os.replace(FILE + ".tmp", FILE)


def add(ders: str, tarih: datetime.date, konu: str = "") -> dict:
    ders = ders.strip()[:40]
    with _lock:
        items = [x for x in _load() if not (x["ders"].lower() == ders.lower() and x["tarih"] == tarih.isoformat())]
        e = {"id": f"{int(datetime.datetime.now().timestamp() * 1000)}", "ders": ders, "tarih": tarih.isoformat(), "konu": konu.strip()[:80]}
        items.append(e)
        items.sort(key=lambda x: x["tarih"])
        _save(items[:60])
    return e


def remove(ders: str) -> int:
    ders = ders.lower().strip()
    with _lock:
        items = _load()
        keep = [x for x in items if ders not in x["ders"].lower()]
        _save(keep)
    return len(items) - len(keep)


def days_left(e: dict, today=None) -> int:
    today = today or datetime.date.today()
    return (datetime.date.fromisoformat(e["tarih"]) - today).days


def upcoming(today=None) -> list:
    today = today or datetime.date.today()
    out = []
    for e in _load():
        try:
            n = days_left(e, today)
        except ValueError:
            continue
        if n >= 0:
            out.append({**e, "kalan": n})
    return sorted(out, key=lambda x: x["kalan"])


def target_minutes(n: int) -> int:
    return 30 if n > 14 else 45 if n > 7 else 90 if n > 2 else 120


def advice(today=None):
    """(metin, hedef_dk, yapılan_dk) en yakın sınav için; sınav yoksa None."""
    ex = upcoming(today)
    if not ex:
        return None
    e = ex[0]
    n = e["kalan"]
    try:
        import pomodoro
        done = pomodoro.snapshot()["work_min_today"]
    except Exception:
        done = 0
    tgt = target_minutes(n)
    when = "bugün" if n == 0 else "yarın" if n == 1 else f"{n} gün sonra"
    topic = f" Konu: {e['konu']}." if e.get("konu") else ""
    left = max(0, tgt - done)
    txt = f"{e['ders']} sınavı {when}.{topic} Bugünkü hedef {tgt} dakika odak; " + (f"{done} dakika yaptınız, {left} dakika kaldı." if left else f"{done} dakika yaptınız, hedef tamam.")
    return txt, tgt, done


def week() -> list:
    """Haftalık ders programı (schedule.py'den, salt okunur): [{'gun', 'dersler': [ad...]}]."""
    out = []
    for wd in range(5):
        les = schedule.day_lessons(wd) or []
        out.append({"gun": schedule.GUNLER[wd], "bugun": wd == datetime.date.today().weekday(), "dersler": [schedule.DERS[k][0] for _, k in les]})
    return out


def view() -> dict:
    a = advice()
    wd = datetime.date.today().weekday()
    tmr = (wd + 1) % 7
    tl = schedule.day_lessons(tmr)
    return {"sinavlar": upcoming(), "advice": a[0] if a else "", "hedef": a[1] if a else 0, "yapilan": a[2] if a else 0,
            "hafta": week(), "yarin": [schedule.DERS[k][0] for _, k in tl] if tl else [], "yarin_gun": schedule.GUNLER[tmr]}


def init_payload() -> dict:
    return view()
