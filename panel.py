"""Panel modu verisi: her kutucuk ayrı toplanır, biri çökerse yalnızca o kutucuk 'veri yok' gösterir. İnternet: hava (open-meteo) ve kur (open.er-api.com)."""
import concurrent.futures as cf

import extras

TILES = ["hava", "kur", "sure", "pomodoro", "sinav", "ajanda", "muzik", "sistem"]
NAMES = {"hava": r"hava", "kur": r"kur|döviz|dolar|euro", "sure": r"süre|kullanım|ekran süresi|bilgisayar", "pomodoro": r"pomodoro|odak",
         "sinav": r"sınav|sinav", "ajanda": r"ajanda|takvim|program", "muzik": r"müzik|şarkı|çalan", "sistem": r"sistem|işlemci|ram|pil"}


def _hava():
    name, lat, lon = extras._locate("")
    d = extras._forecast(lat, lon)
    c, dl = d["current"], d["daily"]
    days = [{"gun": i, "hi": round(dl["temperature_2m_max"][i]), "lo": round(dl["temperature_2m_min"][i]), "d": extras.WMO.get(dl["weather_code"][i], ""),
             "pp": dl["precipitation_probability_max"][i]} for i in range(min(3, len(dl["time"])))]
    return {"city": name, "temp": round(c["temperature_2m"]), "feels": round(c["apparent_temperature"]), "d": extras.WMO.get(c["weather_code"], "değişken"),
            "wind": round(c["wind_speed_10m"]), "days": days}


def _kur():
    d = extras._get_json("https://open.er-api.com/v6/latest/USD", 300)["rates"]
    try_ = d["TRY"]
    return [{"k": "USD", "v": round(try_, 2)}, {"k": "EUR", "v": round(try_ / d["EUR"], 2)}, {"k": "GBP", "v": round(try_ / d["GBP"], 2)},
            {"k": "CHF", "v": round(try_ / d["CHF"], 2)}]


def _sure():
    import usage
    return {**usage.today(), "week": usage.week()}


def _pomodoro():
    import pomodoro
    s = pomodoro.snapshot()
    return {"min": s["work_min_today"], "done": s["done_today"], "phase": s["name"]}


def _ajanda():
    import agenda
    import datetime
    out = []
    for i in agenda.upcoming(7)[:5]:
        out.append({"t": i["title"], "w": agenda.fmt_when(datetime.datetime.fromtimestamp(i["when"]), i.get("timed", True))})
    return out


def _sinav():
    import sinav
    ex = sinav.upcoming()[:3]
    return [{"ders": e["ders"], "kalan": e["kalan"], "konu": e.get("konu", "")} for e in ex]


def _muzik():
    import nowplaying
    c = nowplaying.current()
    return {"title": c.get("title"), "artist": c.get("artist"), "playing": c.get("playing")} if c and c.get("title") else None


def _sistem():
    import psutil
    b = psutil.sensors_battery()
    return {"cpu": round(psutil.cpu_percent(interval=0.3)), "ram": round(psutil.virtual_memory().percent), "bat": round(b.percent) if b else None,
            "plug": bool(b.power_plugged) if b else None}


_FN = {"hava": _hava, "kur": _kur, "sure": _sure, "pomodoro": _pomodoro, "sinav": _sinav, "ajanda": _ajanda, "muzik": _muzik, "sistem": _sistem}


def _safe(k):
    try:
        return _FN[k]()
    except Exception as e:
        print(f"panel {k} hatası:", type(e).__name__, flush=True)
        return None


def view() -> dict:
    with cf.ThreadPoolExecutor(len(_FN)) as ex:
        fut = {k: ex.submit(_safe, k) for k in _FN}
        data = {k: f.result(timeout=25) for k, f in fut.items()}
    return {"tiles": TILES, "data": data}


def init_payload() -> dict:
    return {"tiles": TILES, "data": {}, "loading": True}
