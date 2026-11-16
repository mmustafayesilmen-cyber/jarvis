"""Spor/maç modu verisi: futbol, basketbol ve voleybol maçları. Ana kaynak ESPN'in herkese açık skor tablosu (Süper Lig, Şampiyonlar Ligi, büyük ligler, NBA, üniversite voleybolu; canlı skor ve dakika),
ek kaynak TheSportsDB (test anahtarı "123"; Euroleague, Türk basketbolu, Sultanlar Ligi gibi ESPN'de olmayanlar için, kapsamı sınırlı). İnternet gerekir; sonuçlar 2 dakika önbellekte durur.
ESPN resmî bir API sözleşmesi değildir (belgesiz uç); değişirse o lig atlanır, diğer kaynak çalışmaya devam eder. Favori takımlar config.json: spor_fav."""
import concurrent.futures as cf
import datetime
import re

import extras
import settings

SPORTS = {"futbol": "Soccer", "basketbol": "Basketball", "voleybol": "Volleyball"}
KEY = "123"
PRIO = ("turk", "türk", "champions", "europa", "euroleague", "eurocup", "nba", "premier", "la liga", "serie a", "bundesliga", "ligue 1", "world cup", "nations league", "cev", "fiba")
S = {"sport": "futbol", "day": 0, "league": "", "team": "", "onlyfav": False}
ESPN = {"futbol": [("soccer/tur.1", "Süper Lig"), ("soccer/uefa.champions", "Şampiyonlar Ligi"), ("soccer/uefa.europa", "Avrupa Ligi"), ("soccer/uefa.europa.conf", "Konferans Ligi"),
                   ("soccer/eng.1", "Premier Lig"), ("soccer/esp.1", "La Liga"), ("soccer/ita.1", "Serie A"), ("soccer/ger.1", "Bundesliga"), ("soccer/fra.1", "Ligue 1"),
                   ("soccer/tur.2", "TFF 1. Lig"), ("soccer/fifa.world", "Dünya Kupası"), ("soccer/uefa.nations", "UEFA Uluslar Ligi"),
                   ("soccer/ned.1", "Hollanda Eredivisie"), ("soccer/por.1", "Portekiz Ligi"), ("soccer/bel.1", "Belçika Ligi"), ("soccer/sco.1", "İskoçya Premiership"),
                   ("soccer/eng.2", "İngiltere Championship"), ("soccer/ger.2", "Almanya 2. Bundesliga"), ("soccer/eng.fa", "FA Cup"), ("soccer/esp.copa_del_rey", "İspanya Kral Kupası"),
                   ("soccer/ita.coppa_italia", "İtalya Kupası"), ("soccer/uefa.champions_qual", "Şampiyonlar Ligi Eleme"), ("soccer/conmebol.libertadores", "Copa Libertadores"),
                   ("soccer/usa.1", "ABD MLS"), ("soccer/bra.1", "Brezilya Serie A"), ("soccer/arg.1", "Arjantin Ligi"), ("soccer/mex.1", "Meksika Liga MX"),
                   ("soccer/ksa.1", "Suudi Pro Lig"), ("soccer/fifa.friendly", "Hazırlık Maçları")],
        "basketbol": [("basketball/nba", "NBA"), ("basketball/wnba", "WNBA"), ("basketball/mens-college-basketball", "NCAA Basketbol"), ("basketball/womens-college-basketball", "NCAA Kadınlar Basketbol")],
        "voleybol": [("volleyball/womens-college-volleyball", "NCAA Kadınlar Voleybol"), ("volleyball/mens-college-volleyball", "NCAA Erkekler Voleybol")]}


def _lc(x: str) -> str:
    """Türkçe büyük İ/I'yı doğru küçültür (İtalya -> italya), süzgeç eşleşmesi için."""
    return str(x).replace("İ", "i").replace("I", "ı").lower()


def favs() -> list:
    v = settings.get("spor_fav")
    return [str(x) for x in v] if isinstance(v, list) else []


def set_favs(lst: list) -> list:
    lst = [x for x in dict.fromkeys(str(x).strip() for x in lst) if x][:12]
    settings.set("spor_fav", lst)
    return lst


def _is_fav(m: dict) -> bool:
    t = (m["ev"] + " " + m["dep"]).lower()
    return any(f.lower() in t for f in favs())


def _espn_one(path: str, name: str, day: int) -> list:
    d = (datetime.date.today() + datetime.timedelta(days=day)).strftime("%Y%m%d")
    data = extras._get_json(f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={d}", 120, 10)
    out = []
    for e in (data or {}).get("events") or []:
        try:
            comp = e["competitions"][0]
            home = next(c for c in comp["competitors"] if c.get("homeAway") == "home")
            away = next(c for c in comp["competitors"] if c.get("homeAway") == "away")
            st = e["status"]["type"]
            state = st.get("state")
            start = _local(e["date"].replace("Z", ""))
            durum = "canlı" if state == "in" else "bitti" if state == "post" else "yaklaşan"
            if st.get("name") in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_SUSPENDED"):
                durum = "ertelendi"
            has = state in ("in", "post")
            out.append({"lig": name, "ev": home["team"].get("displayName", "?"), "dep": away["team"].get("displayName", "?"),
                        "es": home.get("score") if has else None, "ds": away.get("score") if has else None,
                        "saat": start.strftime("%H:%M") if start else "", "durum": durum, "ts": start.timestamp() if start else 0,
                        "dk": (st.get("shortDetail") or "") if state == "in" else ""})
        except (KeyError, StopIteration, TypeError):
            continue
    return out


def _espn(sport: str, day: int) -> list:
    out = []
    with cf.ThreadPoolExecutor(6) as ex:
        futs = [ex.submit(_espn_one, p, n, day) for p, n in ESPN.get(sport, [])]
        for f in futs:
            try:
                out += f.result(timeout=20)
            except Exception:
                pass
    return out


def _key(m: dict) -> frozenset:
    n = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())[:5]
    return frozenset((n(m["ev"]), n(m["dep"])))


def _local(ts: str):
    try:
        d = datetime.datetime.fromisoformat(ts).replace(tzinfo=datetime.timezone.utc).astimezone()
        return d
    except Exception:
        return None


def _status(e: dict, start) -> str:
    st = (e.get("strStatus") or "").lower()
    has = e.get("intHomeScore") not in (None, "") or e.get("intAwayScore") not in (None, "")
    if st in ("match finished", "ft", "aet", "pen", "finished", "after over time", "after penalties") or "finish" in st:
        return "bitti"
    if st in ("postponed", "cancelled", "canceled", "abandoned", "suspended"):
        return "ertelendi"
    if has and start and start <= datetime.datetime.now(start.tzinfo) and st not in ("not started", "ns", ""):
        return "canlı"
    if has and start and start < datetime.datetime.now(start.tzinfo) - datetime.timedelta(hours=4):
        return "bitti"
    return "yaklaşan" if not has else "canlı"


def _tsdb(sport: str, day: int) -> list:
    d = (datetime.date.today() + datetime.timedelta(days=day)).isoformat()
    data = extras._get_json(f"https://www.thesportsdb.com/api/v1/json/{KEY}/eventsday.php?d={d}&s={SPORTS[sport]}", 120, 10)
    out = []
    for e in (data or {}).get("events") or []:
        start = _local(e.get("strTimestamp") or "")
        out.append({"lig": e.get("strLeague") or "Diğer", "ev": e.get("strHomeTeam") or "?", "dep": e.get("strAwayTeam") or "?",
                    "es": e.get("intHomeScore"), "ds": e.get("intAwayScore"), "saat": start.strftime("%H:%M") if start else (e.get("strTime") or "")[:5],
                    "durum": _status(e, start) if start else "yaklaşan", "ts": start.timestamp() if start else 0})
    return out


def matches(sport: str = "", day: int = 0) -> list:
    sport = sport or S["sport"]
    out = _espn(sport, day)
    seen = {_key(m) for m in out}
    try:
        for m in _tsdb(sport, day):
            if _key(m) not in seen:
                out.append(m)
    except Exception:
        pass                                      # ek kaynak kapalıysa ESPN sonuçları yeter
    for m in out:
        m["fav"] = _is_fav(m)
    out.sort(key=lambda m: (not m["fav"], not any(p in m["lig"].lower() for p in PRIO), m["lig"], m["ts"]))
    return out


def view() -> dict:
    try:
        ms = matches(S["sport"], S["day"])
        err = ""
    except Exception:
        ms, err = [], "Maç verisine şu an ulaşılamadı. İnternet bağlantınızı kontrol edin."
    q = _lc(S["league"] or S["team"])
    if q:
        ms = [m for m in ms if q in _lc(m["lig"]) or q in _lc(m["ev"]) or q in _lc(m["dep"])]
    if S["onlyfav"]:
        ms = [m for m in ms if m.get("fav")]
    leagues = {}
    for m in ms:
        leagues.setdefault(m["lig"], []).append(m)
    return {"sport": S["sport"], "day": S["day"], "q": q, "onlyfav": S["onlyfav"], "favs": favs(), "err": err, "n": len(ms), "canli": sum(1 for m in ms if m["durum"] == "canlı"),
            "leagues": [{"name": k, "matches": v} for k, v in leagues.items()]}


def init_payload() -> dict:
    S.update(sport="futbol", day=0, league="", team="", onlyfav=False)
    return {"sport": "futbol", "day": 0, "q": "", "err": "", "n": 0, "canli": 0, "leagues": [], "loading": True}   # ağ isteği açılışı bekletmesin: sayfa 'yenile' ister


def say_summary(v: dict) -> str:
    if v["err"]:
        return v["err"]
    day = ["bugün", "yarın", "dün"][{0: 0, 1: 1, -1: 2}.get(v["day"], 0)] if v["day"] in (0, 1, -1) else "o gün"
    if not v["n"]:
        return f"{day.capitalize()} için {v['sport']} maçı bulamadım efendim."
    first = [m for lg in v["leagues"] for m in lg["matches"]][:4]
    parts = []
    for m in first:
        if m["es"] not in (None, "") and m["ds"] not in (None, ""):
            parts.append(f"{m['ev']} {m['es']} {m['ds']} {m['dep']}" + (", canlı" if m["durum"] == "canlı" else ""))
        else:
            parts.append(f"{m['ev']} {m['dep']} saat {m['saat']}")
    return f"{day.capitalize()} {v['n']} {v['sport']} maçı var efendim" + (f", {v['canli']} tanesi canlı" if v["canli"] else "") + ". " + "; ".join(parts) + "."
