"""Ek komutlar: canlı hava durumu, hesap makinesi + canlı kur + birim dönüşümü, pencere/ekran komutları, kılavuz.
Hepsi sabit kalıplarla (LLM'siz) çalışır. İnternet kullanan tek yerler: hava (open-meteo.com, ipwho.is konum için) ve kur (open.er-api.com)."""
import ast, ctypes, json, math, operator, os, re, threading, time, urllib.parse, urllib.request

DRYRUN = lambda: os.environ.get("JARVIS_POWER_DRYRUN") == "1"
_cache: dict = {}
_cache_lock = threading.Lock()


def _get_json(url: str, ttl: int = 0, timeout: int = 7):
    """Yalnızca https; ttl saniye boyunca önbellekten verir (veri 'her zaman güncel' kalsın diye kısa tutulur)."""
    if not url.startswith("https://"):
        raise ValueError("yalnızca https")
    with _cache_lock:
        hit = _cache.get(url)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
    req = urllib.request.Request(url, headers={"User-Agent": "Jarvis/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read(2_000_000).decode("utf-8"))
    with _cache_lock:
        _cache[url] = (time.time(), data)
    return data


def _fmt(x: float, nd: int = 2) -> str:
    """Türkçe sayı biçimi: 1.234,56 (gereksiz sıfırlar atılır)."""
    if abs(x - round(x)) < 1e-9:
        s = f"{int(round(x)):,}"
    else:
        s = f"{x:,.{nd}f}".rstrip("0").rstrip(".")
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_num(s: str) -> float:
    s = s.strip()
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):          # 1.000 / 12.500.000 -> binlik ayracı
        return float(s.replace(".", ""))
    return float(s.replace(",", "."))


# ============================================================== HAVA DURUMU
WMO = {0: "açık", 1: "çoğunlukla açık", 2: "parçalı bulutlu", 3: "kapalı", 45: "sisli", 48: "kırağılı sisli",
       51: "hafif çiseleyen", 53: "çiseleyen", 55: "yoğun çiseleyen", 56: "dondurucu çiseleyen", 57: "dondurucu çiseleyen",
       61: "hafif yağmurlu", 63: "yağmurlu", 65: "şiddetli yağmurlu", 66: "dondurucu yağmurlu", 67: "dondurucu yağmurlu",
       71: "hafif karlı", 73: "karlı", 75: "yoğun karlı", 77: "kar taneli", 80: "hafif sağanaklı", 81: "sağanaklı",
       82: "şiddetli sağanaklı", 85: "hafif kar sağanaklı", 86: "kar sağanaklı", 95: "gök gürültülü fırtınalı",
       96: "dolu yağışlı fırtınalı", 99: "şiddetli dolu yağışlı fırtınalı"}
_loc = {"auto": None}


def _locate(city: str = ""):
    """(ad, enlem, boylam). city boşsa ayardaki şehir, o da yoksa IP'den yaklaşık konum."""
    import settings
    city = city or settings.get("city") or ""
    if city:
        g = _get_json("https://geocoding-api.open-meteo.com/v1/search?count=1&language=tr&name=" + urllib.parse.quote(city), 86400)
        res = (g or {}).get("results") or []
        if not res:
            raise LookupError(f"{city} adında bir yer bulamadım")
        r = res[0]
        return r["name"], r["latitude"], r["longitude"]
    if _loc["auto"] is None:
        g = _get_json("https://ipwho.is/", 3600)
        if not g.get("success", True) or "latitude" not in g:
            raise LookupError("konumunuzu bulamadım, şehrinizi söyler misiniz")
        _loc["auto"] = (g.get("city") or "bulunduğunuz yer", g["latitude"], g["longitude"])
    return _loc["auto"]


def _forecast(lat, lon):
    return _get_json("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&timezone=auto&forecast_days=3"
                     "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation"
                     "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
                     % (lat, lon), 300)


def weather(city: str = "", day: int = 0, umbrella: bool = False) -> str:
    try:
        name, lat, lon = _locate(city)
        d = _forecast(lat, lon)
        dl = d["daily"]
        mx, mn = round(dl["temperature_2m_max"][day]), round(dl["temperature_2m_min"][day])
        pp = dl["precipitation_probability_max"][day]
        desc = WMO.get(dl["weather_code"][day], "değişken")
        wet = (pp or 0) >= 40 or dl["weather_code"][day] >= 51 and dl["weather_code"][day] not in (45, 48)
        if umbrella:
            return (f"Evet efendim, {name} için {'bugün' if day == 0 else 'yarın' if day == 1 else 'o gün'} yağış ihtimali yüzde {pp}, "
                    "şemsiye almanızı öneririm." if wet else
                    f"Gerek yok efendim, {name} için yağış ihtimali yüzde {pp}.")
        when = ["bugün", "yarın", "öbür gün"][day]
        if day == 0:
            c = d["current"]
            now = (f"Şu an {name} için hava {WMO.get(c['weather_code'], 'değişken')}, {round(c['temperature_2m'])} derece, "
                   f"hissedilen {round(c['apparent_temperature'])}. Rüzgâr saatte {round(c['wind_speed_10m'])} kilometre. ")
            return now + f"Bugün en yüksek {mx}, en düşük {mn} derece, yağış ihtimali yüzde {pp} efendim."
        return f"{name} için {when} hava {desc}, en yüksek {mx}, en düşük {mn} derece, yağış ihtimali yüzde {pp} efendim."
    except LookupError as e:
        return f"{e} efendim."
    except Exception:
        return "Hava durumuna şu an ulaşamadım efendim, internet bağlantınızı kontrol eder misiniz?"


_W_STOP = {"hava", "havalar", "havası", "durumu", "durum", "nasıl", "nasıldı", "olacak", "ne", "nedir", "kaç", "derece", "bugün",
           "bugünkü", "yarın", "yarınki", "öbür", "gün", "günü", "ertesi", "mi", "mı", "mu", "mü", "söyle", "bana", "bak",
           "şu", "an", "şimdi", "dışarısı", "dışarda", "dışarıda", "dışarı", "sıcaklık", "kaçtı", "acaba", "var", "yağmur",
           "yağacak", "yağıyor", "yağışlı", "şemsiye", "gerekli", "lazım", "almalı", "alayım", "almam", "yağış", "soğuk", "sıcak",
           "biraz", "dışarıdaki", "bakar", "mısın", "tahmin", "tahmini", "göster", "oku", "yağar"}


def _strip_loc(w: str) -> str:
    for suf in ("daki", "deki", "taki", "teki", "da", "de", "ta", "te", "nın", "nin", "ın", "in", "un", "ün"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[:-len(suf)]
    return w


def route_weather(t: str):
    toks = t.split()
    if not (re.search(r"\b(hava|havalar|havası)\b", t) and re.search(r"\b(durum\w*|nasıl\w*|derece|kaç|sıcaklık|tahmin\w*|yağmur\w*|yağış\w*|şemsiye|olacak)\b", t)) \
            and not re.search(r"\b(dışarı\w*|dışarda)\b.*\b(derece|sıcak\w*|soğuk|yağmur\w*|kaç)\b", t) \
            and not re.search(r"\b(şemsiye|yağmur yağ\w*)\b", t) and not re.fullmatch(r"hava", t):
        return None
    if re.search(r"\b(hava)\s*(kalitesi|alanı|yolları|durumu bilgisi)\b", t) or re.search(r"\b(ses|ışık|ekran|müzik|tamam|oyun)\b", t):
        return None
    rest = [w for w in toks if w not in _W_STOP]
    if len(rest) > 2:
        return None
    city = _strip_loc(" ".join(rest)) if rest else ""
    day = 1 if re.search(r"\byarın\w*", t) else 2 if re.search(r"\b(öbür gün|ertesi gün)\w*", t) else 0
    return weather(city, day, bool(re.search(r"şemsiye|yağmur yağ\w*|yağmur var|yağacak", t)))


def route_city(t: str):
    m = re.fullmatch(r"(?:şehrim|şehrimi|konumum|konumumu|yaşadığım (?:yer|şehir)\w*)\s+([a-zçğıöşü ]{3,30}?)(?:\s+(?:yap|olsun|olarak ayarla|ayarla|de|kaydet))?", t)
    if not m:
        m = re.fullmatch(r"(?:ben )?([a-zçğıöşü]{3,30}) (?:da|de|ta|te)?\s*(?:yaşıyorum|oturuyorum)", t)
    if not m:
        return None
    import settings
    city = m.group(1).strip()
    try:
        name, *_ = _locate(city)
    except LookupError:
        return f"{city} adında bir yer bulamadım efendim."
    except Exception:
        return "Şehri şu an doğrulayamadım efendim, internet bağlantınızı kontrol eder misiniz?"
    settings.set("city", name)
    return f"Tamam efendim, şehrinizi {name} olarak kaydettim. Hava durumunu artık buraya göre söyleyeceğim."


# ============================================================== HESAP MAKİNESİ
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _safe_eval(node.operand)
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        a, b = _safe_eval(node.left), _safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(b) > 100 or abs(a) > 1e6):
            raise ValueError("çok büyük")
        return _BIN[type(node.op)](a, b)
    raise ValueError("izin verilmeyen ifade")


_OPS = [(r"\bartı\b", "+"), (r"\beksi\b", "-"), (r"\b(çarpı|kere|çarpı)\b", "*"), (r"\bbölü\b", "/"), (r"\b(üzeri|üssü)\b", "**"),
        (r"\b(mod)\b", "%")]
_TAIL = r"(?:\s*(?:kaç eder|kaçtır|kaç yapar|kaç|eşittir|nedir|ne eder|ne yapar|eder|yapar|hesapla|hesaplar mısın|sonucu)\s*)*"


def route_calc(t: str):
    # yüzde: "250 yüzde 15 kaç" / "250 sayısının yüzde 15i kaç"
    m = re.fullmatch(r"hesapla\s+(.*)", t)
    t2 = m.group(1) if m else t
    m = re.fullmatch(r"([\d.,]+)\s*(?:sayısının|sayının|in|nın)?\s*yüzde\s*([\d.,]+)\s*(?:si|sı|i|ı|u|ü|su|sü)?" + _TAIL, t2)
    if m and re.search(r"kaç|nedir|eder|hesapla|yapar", t2):
        a, p = _parse_num(m.group(1)), _parse_num(m.group(2))
        return f"{_fmt(a)} sayısının yüzde {_fmt(p)}'i {_fmt(a * p / 100)} efendim."
    m = re.fullmatch(r"([\d.,]+)\s*(?:lira|tl|liralık|dolar|euro)?\s*(?:ürüne|fiyata|fiyatın)?\s*yüzde\s*([\d.,]+)\s*(indirim|zam)\w*\s*(?:yapılırsa|yaparsak|gelirse|uygulanırsa|olursa)?" + _TAIL, t2)
    if m:
        a, p = _parse_num(m.group(1)), _parse_num(m.group(2))
        r = a * (1 - p / 100) if m.group(3) == "indirim" else a * (1 + p / 100)
        return f"Yüzde {_fmt(p)} {m.group(3)} sonrası {_fmt(r)} efendim."
    m = re.fullmatch(r"(?:karekök|kare kök)\s*([\d.,]+)" + _TAIL, t2)
    if m:
        v = _parse_num(m.group(1))
        return f"{_fmt(v)} sayısının karekökü {_fmt(math.sqrt(v), 6)} efendim."
    m = re.fullmatch(r"([\d.,]+)\s*(?:sayısının\s*)?(?:karesi|küpü)" + _TAIL, t2)
    if m:
        v = _parse_num(m.group(1))
        return f"{_fmt(v)} sayısının {'karesi' if 'kare' in t2 else 'küpü'} {_fmt(v ** (2 if 'kare' in t2 else 3), 6)} efendim."
    expr = t2
    for pat, sym in _OPS:
        expr = re.sub(pat, f" {sym} ", expr)
    expr = re.sub(_TAIL + r"$", "", expr).strip()
    if not re.search(r"[+\-*/%]", expr) or not re.fullmatch(r"[\d\s+\-*/%.,()]+", expr):
        return None
    if not re.search(r"\d", expr) or re.search(r"\d\s+\d", expr):
        return None
    expr = re.sub(r"(\d+(?:\.\d{3})+|\d+(?:,\d+)?)", lambda mm: repr(_parse_num(mm.group(1))), expr)
    try:
        val = _safe_eval(ast.parse(expr, mode="eval"))
    except ZeroDivisionError:
        return "Sıfıra bölme tanımsız efendim."
    except Exception:
        return None
    return f"Sonuç {_fmt(val, 6)} efendim."


# ============================================================== KUR + BİRİM
CUR = {"dolar": "USD", "usd": "USD", "euro": "EUR", "avro": "EUR", "eur": "EUR", "sterlin": "GBP", "gbp": "GBP", "lira": "TRY",
       "tl": "TRY", "try": "TRY", "yen": "JPY", "frank": "CHF", "ruble": "RUB", "riyal": "SAR", "kanada": "CAD"}
CUR_NAME = {"USD": "dolar", "EUR": "euro", "GBP": "sterlin", "TRY": "lira", "JPY": "yen", "CHF": "frank", "RUB": "ruble",
            "SAR": "riyal", "CAD": "Kanada doları"}


def _stem(tok: str, table: dict):
    for n in (0, 1, 2, 3):
        if n and len(tok) - n < 2:
            break
        k = tok[:len(tok) - n] if n else tok
        if k in table:
            return table[k]
    return None


def convert_currency(amount: float, a: str, b: str) -> str:
    try:
        d = _get_json(f"https://open.er-api.com/v6/latest/{a}", 120)
        rate = d["rates"][b]
        upd = d.get("time_last_update_utc", "")
        mm = re.search(r"(\d{1,2}) (\w{3}) (\d{4})", upd)
        tail = f" Kur {mm.group(1)} {mm.group(2)} tarihli veriye dayanıyor." if mm else ""
        return f"{_fmt(amount)} {CUR_NAME[a]} şu an yaklaşık {_fmt(amount * rate)} {CUR_NAME[b]} efendim.{tail}"
    except Exception:
        return "Güncel kura şu an ulaşamadım efendim, internet bağlantınızı kontrol eder misiniz?"


# birim: ad -> (boyut, taban birime çarpan); sıcaklık ayrı
UNITS = {
    "milimetre": ("len", 0.001), "mm": ("len", 0.001), "santimetre": ("len", 0.01), "cm": ("len", 0.01), "metre": ("len", 1), "m": ("len", 1),
    "kilometre": ("len", 1000), "km": ("len", 1000), "inç": ("len", 0.0254), "inch": ("len", 0.0254), "fit": ("len", 0.3048),
    "feet": ("len", 0.3048), "ayak": ("len", 0.3048), "mil": ("len", 1609.344), "yarda": ("len", 0.9144),
    "gram": ("mass", 1), "gr": ("mass", 1), "kilogram": ("mass", 1000), "kilo": ("mass", 1000), "kg": ("mass", 1000), "ton": ("mass", 1e6),
    "libre": ("mass", 453.592), "pound": ("mass", 453.592), "ons": ("mass", 28.3495), "miligram": ("mass", 0.001),
    "mililitre": ("vol", 0.001), "ml": ("vol", 0.001), "litre": ("vol", 1), "lt": ("vol", 1), "galon": ("vol", 3.78541),
    "bardak": ("vol", 0.2), "metreküp": ("vol", 1000),
    "bayt": ("data", 1), "byte": ("data", 1), "kilobayt": ("data", 1024), "kb": ("data", 1024), "megabayt": ("data", 1024 ** 2),
    "mb": ("data", 1024 ** 2), "gigabayt": ("data", 1024 ** 3), "gb": ("data", 1024 ** 3), "terabayt": ("data", 1024 ** 4), "tb": ("data", 1024 ** 4),
    "saniye": ("time", 1), "dakika": ("time", 60), "saat": ("time", 3600), "gün": ("time", 86400), "hafta": ("time", 604800),
    "santigrat": ("temp", "c"), "celsius": ("temp", "c"), "derece": ("temp", "c"), "fahrenheit": ("temp", "f"), "kelvin": ("temp", "k"),
}
UNIT_NAME = {"len": "", "mass": "", "vol": "", "data": "", "time": "", "temp": ""}


def convert_unit(v: float, a: str, b: str) -> str:
    (da, fa), (db, fb) = UNITS[a], UNITS[b]
    if da != db:
        return f"{a} ile {b} birbirine çevrilemez efendim."
    if da == "temp":
        c = v if fa == "c" else (v - 32) * 5 / 9 if fa == "f" else v - 273.15
        r = c if fb == "c" else c * 9 / 5 + 32 if fb == "f" else c + 273.15
    else:
        r = v * fa / fb
    return f"{_fmt(v)} {a} yaklaşık {_fmt(r, 4)} {b} efendim."


def route_convert(t: str):
    # kur: "dolar kaç lira", "100 euro kaç tl eder", "500 lira kaç dolar", "dolar kuru", "euro ne kadar"
    m = re.fullmatch(r"(?:([\d.,]+)\s+)?([a-zçğıöşü]+?)(?:\s+(?:kaç|kaça|ne kadar|kaç eder|kaça denk gelir|kaç yapar)\s*([a-zçğıöşü]+)?(?:\s+(?:eder|yapar|olur|tl))?|\s+kuru(?: kaç| ne kadar| nedir)?|\s+kaç tl|\s+ne kadar)", t)
    if m:
        a = _stem(m.group(2), CUR)
        b = _stem(m.group(3), CUR) if m.group(3) else None
        if a and (b or not m.group(3)):
            b = b or ("USD" if a == "TRY" else "TRY")
            if a != b:
                amt = _parse_num(m.group(1)) if m.group(1) else 1.0
                return convert_currency(amt, a, b)
    # birim: "5 kilometre kaç mil", "30 santigrat kaç fahrenheit"
    m = re.fullmatch(r"([\d.,]+)\s*([a-zçğıöşü]+)\s+(?:kaç|kaça eşit|kaça denk gelir|ne kadar)\s*([a-zçğıöşü]+)(?:\s+(?:eder|yapar|olur))?", t)
    if m:
        a, b = _stem(m.group(2), {k: k for k in UNITS}), _stem(m.group(3), {k: k for k in UNITS})
        if a and b:
            return convert_unit(_parse_num(m.group(1)), a, b)
        ca, cb = _stem(m.group(2), CUR), _stem(m.group(3), CUR)
        if ca and cb and ca != cb:
            return convert_currency(_parse_num(m.group(1)), ca, cb)
    return None


# ============================================================== PENCERE / EKRAN
def _fg():
    u = ctypes.windll.user32
    h = u.GetForegroundWindow()
    if not h:
        return None
    cls = ctypes.create_unicode_buffer(64)
    u.GetClassNameW(h, cls, 64)
    return None if cls.value in ("Progman", "WorkerW", "Shell_TrayWnd") else h


def _workarea(h):
    from ctypes import wintypes
    u = ctypes.windll.user32

    class MI(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]
    mi = MI()
    mi.cbSize = ctypes.sizeof(MI)
    u.GetMonitorInfoW(u.MonitorFromWindow(h, 2), ctypes.byref(mi))
    w = mi.rcWork
    return w.left, w.top, w.right - w.left, w.bottom - w.top


def window_cmd(action: str) -> str:
    """action: left, right, top, bottom, max, min, restore, center, desktop, next_monitor"""
    u = ctypes.windll.user32
    if action == "desktop":
        import pyautogui
        pyautogui.hotkey("win", "d")
        return "Masaüstünü gösterdim efendim."
    h = _fg()
    if not h:
        return "Üzerinde çalışabileceğim açık bir pencere yok efendim."
    if action == "next_monitor":
        import pyautogui
        pyautogui.hotkey("win", "shift", "right")
        return "Pencereyi diğer ekrana taşıdım efendim. Tek ekranınız varsa değişmez."
    if action == "min":
        u.ShowWindow(h, 6)
        return "Pencereyi küçülttüm efendim."
    if action == "max":
        u.ShowWindow(h, 3)
        return "Pencereyi ekranı kaplayacak şekilde büyüttüm efendim."
    if action == "restore":
        u.ShowWindow(h, 9)
        return "Pencereyi eski boyutuna getirdim efendim."
    x, y, w, hh = _workarea(h)
    u.ShowWindow(h, 9)
    box = {"left": (x, y, w // 2, hh), "right": (x + w // 2, y, w - w // 2, hh), "top": (x, y, w, hh // 2),
           "bottom": (x, y + hh // 2, w, hh - hh // 2), "center": (x + w // 6, y + hh // 6, w * 2 // 3, hh * 2 // 3)}[action]
    u.SetWindowPos(h, 0, *box, 0x0004 | 0x0010)          # SWP_NOZORDER | SWP_NOACTIVATE
    return {"left": "Pencereyi sola yasladım efendim.", "right": "Pencereyi sağa yasladım efendim.",
            "top": "Pencereyi ekranın üst yarısına aldım efendim.", "bottom": "Pencereyi ekranın alt yarısına aldım efendim.",
            "center": "Pencereyi ortaya aldım efendim."}[action]


def _later(fn, delay=3.0):
    threading.Timer(delay, fn).start()


def lock_screen() -> str:
    if not DRYRUN():
        _later(ctypes.windll.user32.LockWorkStation, 2.5)
    return "Ekranı kilitliyorum efendim."


def sleep_pc() -> str:
    if not DRYRUN():
        _later(lambda: ctypes.windll.powrprof.SetSuspendState(False, False, False), 4.0)      # hazırda bekletme değil, uyku
    return "Bilgisayarı uyku moduna alıyorum efendim. Fareye dokunarak uyandırabilirsiniz."


def monitor_off() -> str:
    if not DRYRUN():
        _later(lambda: ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2), 2.5)    # SC_MONITORPOWER kapalı
    return "Ekranı kapatıyorum efendim. Fareyi oynatınca açılır."


def _ps(cmd: str) -> str:
    import subprocess
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=20,
                       encoding="utf-8", errors="replace", creationflags=0x08000000)
    return (r.stdout + r.stderr).strip()


def brightness(change: int = None, setto: int = None) -> str:
    cur = _ps("(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction SilentlyContinue | Select -First 1).CurrentBrightness")
    if not cur.strip().isdigit():
        return "Bu ekranın parlaklığını yazılımla değiştiremiyorum efendim. Masaüstü monitörlerde genelde monitörün kendi tuşları gerekir."
    cur = int(cur)
    if change is None and setto is None:
        return f"Parlaklık yüzde {cur} efendim."
    new = max(0, min(100, setto if setto is not None else cur + change))
    _ps(f"Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods | Invoke-CimMethod -MethodName WmiSetBrightness -Arguments @{{Timeout=1;Brightness={new}}}")
    return f"Parlaklığı yüzde {new} yaptım efendim."


def route_screen(t: str):
    if re.search(r"\bpencere\w*", t) or re.search(r"\bsola yasla|sağa yasla|masaüstünü göster|tüm pencereleri küçült", t):
        if re.search(r"\bsol\w*", t) and re.search(r"yasla|al|koy|getir|sabitle", t):
            return window_cmd("left")
        if re.search(r"\bsağ\w*", t) and re.search(r"yasla|al|koy|getir|sabitle", t):
            return window_cmd("right")
        if re.search(r"\büst\w*", t) and re.search(r"yasla|al|koy|getir", t):
            return window_cmd("top")
        if re.search(r"\balt\b|\baltı\w*|\balt yarı\w*", t) and re.search(r"yasla|al|koy|getir", t):
            return window_cmd("bottom")
        if re.search(r"büyüt|tam ekran yap|ekranı kapla|kapla|maksimize", t):
            return window_cmd("max")
        if re.search(r"küçült|simge durumu\w*|minimize|gizle", t):
            return window_cmd("min")
        if re.search(r"eski haline|eski boyut\w*|normal boyut\w*|geri getir", t):
            return window_cmd("restore")
        if re.search(r"orta\w*", t) and re.search(r"al|koy|getir", t):
            return window_cmd("center")
        if re.search(r"diğer ekran\w*|öbür ekran\w*|ikinci ekran\w*", t) and re.search(r"taşı|at|götür|al", t):
            return window_cmd("next_monitor")
    if re.fullmatch(r"(masaüstünü göster|masaüstüne git|masaüstü|tüm pencereleri küçült|pencereleri küçült)", t):
        return window_cmd("desktop")
    if re.fullmatch(r"(ekranı|bilgisayarı|bilgisayarımı|pc yi|pc'yi|pc)?\s*kilitle|ekran kilidi|ekranı kilitler misin|kilit ekranı", t):
        return lock_screen()
    if re.fullmatch(r"(bilgisayarı|bilgisayarımı|pc yi|sistemi)?\s*(uyku moduna al|uyut|uykuya al|uyku moduna geç|beklemeye al|uyku modu)", t):
        return sleep_pc()
    if re.fullmatch(r"(ekranı|monitörü)\s*(kapat|söndür|uyut)", t):
        return monitor_off()
    if re.search(r"\bparlakl[ıi][kğ]\w*", t) or re.search(r"\bekran\w* aydınlık\w*", t):
        n = re.search(r"(\d{1,3})", t)
        if n and re.search(r"yap|olsun|ayarla|getir|yüzde|%", t):
            return brightness(setto=int(n.group(1)))
        if re.search(r"artır|yükselt|aç|arttır|parlat", t):
            return brightness(change=int(n.group(1)) if n else 15)
        if re.search(r"azalt|kıs|düşür|karart|indir", t):
            return brightness(change=-(int(n.group(1)) if n else 15))
        if re.search(r"ne kadar|kaç|nedir|\bne$", t):
            return brightness()
    return None


# ============================================================== KILAVUZ
GUIDE_URL = "http://127.0.0.1:8765/guide"


def route_guide(t: str):
    if re.fullmatch(r"(kılavuz\w*|kullanım kılavuz\w*|yardım|komutlar\w*|komut listesi\w*|neler yapabilirsin|ne yapabilirsin|"
                    r"neler yapabiliyorsun|hangi komutlar var|komutları (göster|say|listele|aç)|yardım kılavuz\w*|nasıl kullanılır|nasıl kullanırım|"
                    r"kılavuz\w*\s*(aç|açar mısın|açsana|göster|gösterir misin|getir|oku|bak)?|rehber\w*\s*(aç|açar mısın|göster|getir)?|"
                    r"kullanım (kılavuz|rehber)\w*(\s*(aç|göster|getir))?|sistem kılavuz\w*|yardım (aç|göster|et)|komutları göster)", t):
        import tools
        try:
            res = tools.GUIDE_HOOK() if tools.GUIDE_HOOK else (tools.open_website(GUIDE_URL) and "ok")
        except Exception:
            return "Kılavuzu şu an açamadım efendim."
        if res != "ok":
            return res
        return ("Kılavuz ekranda efendim. Kapatmak için sağ üstteki Kapat tuşuna ya da Esc'ye basın. Orada her komutun ne yaptığını, "
                "sistemin neler yapabildiğini ve sınırlarını bulabilirsiniz.")
    return None


def _norm_num(raw: str) -> str:
    """Router'ın _norm'u 1.000 / 2,5 gibi sayıları bozar; hesap ve dönüşümler için noktalama korunur."""
    t = raw.replace("İ", "i").replace("I", "ı").lower()
    t = re.sub(r"['’]\w*", "", t)
    t = re.sub(r"[^\w\s,.%+\-*/]", " ", t)
    t = re.sub(r"\b(jarvis|hey|lütfen|bana|şunu|efendim|acaba|hadi|sen)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip(" .,")


def route_code(t: str):
    if re.fullmatch(r"(kod yazma|kod yaz\w*|kod|python kod\w*|kodlama)\s*(ekran\w*|pencere\w*|modu\w*)?\s*(aç|açar mısın|açsana|başlat|getir)?|"
                    r"(kod yazmak istiyorum|kod yazacağım|python yazacağım|kod yazalım|kodlama yapacağım)", t)             and re.search(r"kod|python", t) and (re.search(r"ekran|pencere|aç|başlat|getir|yazmak|yazacağım|yazalım|yapacağım", t)):
        import tools
        if tools.CODE_HOOK is None:
            return "Kod yazma ekranı şu an kullanılamıyor efendim."
        res = tools.CODE_HOOK()
        if res == "ok":
            return "Kod yazma ekranını açtım efendim. Yeni bir proje klasörü hazırladım ve VS Code'da gösteriyorum. Yazdıklarınız otomatik kaydedilir, bitirince Bitir tuşuna basın."
        if res == "novscode":
            return "Kod yazma ekranını açtım ama VS Code'u bulamadım efendim. Proje klasörü Belgeler içindeki JarvisKod'da."
        return res + "."
    return None


def route_schedule(t: str):
    import schedule
    return schedule.route(t)


def route_agenda(t: str, raw: str = ""):
    if not raw:
        return None
    import agenda
    return agenda.route(t, raw)


# ============================================================== SİTE MODU
CALC_FILE = os.path.join(os.path.expanduser("~"), "hesap makinesi.py")
FALLBACK_SITES = [("Poki", "https://poki.com/tr/yeni"), ("Gemini", "https://gemini.google.com/app?hl=tr&safe=active"),
                  ("YouTube", "https://www.youtube.com"), ("YouTube Music", "https://music.youtube.com"), ("Google", "https://www.google.com"),
                  ("Instagram", "https://www.instagram.com"), ("Netflix", "https://www.netflix.com"), ("Spotify", "https://open.spotify.com"),
                  ("GitHub", "https://github.com"), ("ChatGPT", "https://chatgpt.com"), ("Scratch", "https://scratch.mit.edu"),
                  ("Tinkercad", "https://www.tinkercad.com")]
_site = {"list": [], "until": 0.0}
SITE_WAIT = 90          # sn; numara beklenen süre


def calc_sites():
    """Gelişmiş Hesap Makinesi'nin açabildiği SİTELER (tur 'url'). Dosyadan okunur, böylece oraya eklenen siteler de gelir.
    Kod çalıştırılmaz: yalnızca iki sözlük ast.literal_eval ile okunur; uygulama (app) girişleri alınmaz."""
    try:
        tree = ast.parse(open(CALC_FILE, encoding="utf-8").read())
        codes = names = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id == "GIZLI_KODLAR":
                    codes = ast.literal_eval(node.value)
                elif node.targets[0].id == "GIZLI_ISIMLER":
                    names = ast.literal_eval(node.value)
        out = []
        for k in sorted(codes or {}):
            kind, target = codes[k]
            if kind == "url" and isinstance(target, str) and target.startswith(("https://", "http://")):
                out.append(((names or {}).get(k) or target.split("//")[1].split("/")[0], target))
        if out:
            return out
    except Exception as e:
        print("site listesi okunamadı:", e, flush=True)
    return list(FALLBACK_SITES)


_NUMWORDS = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10, "on bir": 11,
             "on iki": 12, "on üç": 13, "on dört": 14, "on beş": 15, "on altı": 16, "on yedi": 17, "on sekiz": 18, "on dokuz": 19, "yirmi": 20,
             "birinci": 1, "ikinci": 2, "üçüncü": 3, "dördüncü": 4, "beşinci": 5, "altıncı": 6, "yedinci": 7, "sekizinci": 8, "dokuzuncu": 9,
             "onuncu": 10, "on birinci": 11, "on ikinci": 12}


def route_site(t: str):
    """'site modu' / 'siteleri say': numaralı listeyi söyler ve bir sonraki cümlede numara bekler."""
    if not re.fullmatch(r"(site modu\w*|siteler modu\w*|site aç|siteyi aç|bir site aç|site açar mısın|siteler|siteleri (say|listele|oku|göster)|"
                        r"hangi siteleri (açabilirsin|açabiliyorsun)|açabildiğin siteler|site listesi\w*|siteleri aç)", t):
        return None
    sites = calc_sites()
    _site["list"], _site["until"] = sites, time.time() + SITE_WAIT
    lst = ". ".join(f"{i}, {n}" for i, (n, _) in enumerate(sites, 1))
    return (f"Açabileceğim {len(sites)} site var efendim. {lst}. "
            "Hangisini açayım? Numarasını söyleyin, vazgeçmek için iptal deyin.")


def site_select(text: str):
    """Site listesi söylendikten sonra gelen cümle bir numaraysa o siteyi açar. Router her cümlede önce burayı çağırır."""
    if not _site["list"]:
        return None
    if time.time() > _site["until"]:
        _site["list"] = []
        return None
    low = text.replace("İ", "i").replace("I", "ı").lower()
    low = re.sub(r"[^\w\s]", " ", low)
    low = " ".join(low.split())
    if re.fullmatch(r"(iptal|vazgeç\w*|hayır|boş ver|kapat|gerek yok|istemiyorum)( jarvis)?", low):
        _site["list"] = []
        return "Tamam efendim, vazgeçtim."
    filler = {"jarvis", "numara", "numaralı", "numaralı", "nolu", "no", "nu", "site", "siteyi", "sitesi", "olanı", "olan", "aç", "açar", "mısın",
              "açsana", "olsun", "lütfen", "inci", "ıncı", "uncu", "üncü", "yi", "yı", "u", "ü", "ı", "i", "numarayı", "numarasını"}
    rest = " ".join(w for w in low.split() if w not in filler)
    n = int(rest) if rest.isdigit() else _NUMWORDS.get(rest)
    if n is None:
        _site["list"] = []              # başka bir komut geldi: seçimi bırak
        return None
    sites = _site["list"]
    if not 1 <= n <= len(sites):
        _site["until"] = time.time() + SITE_WAIT
        return f"{n} numaralı bir site yok efendim. 1 ile {len(sites)} arasında bir numara söyleyin."
    name, url = sites[n - 1]
    _site["list"] = []
    import tools
    tools.open_website(url)
    return f"{name} açılıyor efendim."


def route_hero(t: str):
    if re.search(r"\b(süper )?kahraman\w*", t) and re.search(r"\b(kapat|çık|bitir)\w*", t):
        return "Kahraman modu zaten kapalı efendim."
    if re.search(r"\b(süper )?kahraman\w*", t) and re.search(r"\b(mod\w*|maske\w*|ekran\w*|aç|başlat|getir)\b", t) \
            and not re.search(r"\b(kapat|çık|bitir)\w*", t):
        import tools
        if tools.HERO_HOOK is None:
            return "Kahraman modu şu an kullanılamıyor efendim."
        res = tools.HERO_HOOK()
        if res != "ok":
            return res
        return ("Kahraman modu açılıyor efendim. Zırh ve Ağ maskeleri hazır, her birinde 30 özellik var. Bu pencere kapanana kadar "
                "yalnızca maske komutlarını dinleyeceğim. Çıkmak için çık demeniz ya da Esc yeterli.")
    return None


def route_illusion(t: str):
    if re.search(r"\b(illüzyon|yanılsama|illuzyon|illusion)\w*", t) and re.search(r"\b(mod\w*|aç|başlat|getir|göster|ekran\w*)\b", t):
        if re.search(r"\b(kapat|çık|bitir)\w*", t):
            return "İllüzyon modu zaten kapalı efendim."
        import tools
        if tools.ILL_HOOK is None:
            return "İllüzyon modu şu an kullanılamıyor efendim."
        res = tools.ILL_HOOK()
        if res != "ok":
            return res
        return ("İllüzyon modu açılıyor efendim. 50 görsel illüzyon hazır, her birinin ne gösterdiğini de anlatacağım. "
                "Bir numara ya da ad söyleyin, sonraki diyebilir ya da otomatik diyerek sırayla gezdirebilirsiniz. "
                "Pencere kapanana kadar yalnızca illüzyon komutlarını dinleyeceğim. Çıkmak için çık demeniz ya da Esc yeterli.")
    return None


def _tarif_query(t: str) -> str:
    import scenes, scenes_tarif                    # scenes önce: scenes_tarif'i kendi sonunda kaydeder
    return scenes_tarif._web_query(t)


def _yemek_intent(t: str) -> bool:
    """'yemek modunu aç' ya da 'elimde tavuk ve patates var ne yapabilirim'. Malzemeler yemek.PENDING'e konur, mod açılınca aranır."""
    if re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t):
        return False
    ex = re.search(r"\b(yemek modu\w*|mutfak modu\w*|malzemeden tarif\w*|malzemeye göre tarif\w*|malzemelere göre tarif\w*|elimdekilerle tarif\w*|evdekilerle tarif\w*)", t)
    if ex:
        explicit = True
        t = t[:ex.start()] + " " + t[ex.end():]       # 'yemek modunu aç' sözcükleri malzeme sanılmasın
        t = re.sub(r"\b(a[cç]\w*|ba[sş]la\w*|g[oö]ster\w*|getir\w*)\b", " ", t)
    elif re.search(r"\b(ne yap\w*|ne pişir\w*|neler yap\w*|ne hazırla\w*|tarif\w*|yemek\w*|öner\w*|ne yesem|ne yiyebilirim)\b", t) \
            and (re.search(r"\b(elimde\w*|evde|buzdolab\w*|dolapta|mutfakta)\b.*\b(var|kaldı|duruyor|mevcut)\b", t) or re.search(r"\b(ile|ve|la|le)\b.*\b(ne yap\w*|ne pişir\w*|ne hazırla\w*)", t)):
        explicit = False
    else:
        return False
    import yemek
    items = yemek.parse_items(t)
    if not explicit and not any(i in yemek.BY_LABEL for i in items):   # 'python ile ne yapabilirim' yemek değil
        return False
    yemek.PENDING[:] = items
    return True


_NOQ = r"\b(nedir|ne demek|kapat|bitir|sil\w*)\b"


def _yeni_kind(t: str):
    """Sınav simülatörü, fikir tahtası, masa, hızlı okuma, kelime kutusu, bütçe, karar çarkı, hızlı başlatıcı modlarının açılış cümleleri."""
    if re.search(_NOQ, t):
        return None
    if re.search(r"\b(sınav simülatör\w*|optik form\w*|optik mod\w*|deneme modu\w*|deneme sınavı modu\w*)", t) or \
            re.search(r"\b(tyt|ayt|ydt)\b.*\b(deneme\w*|sınav\w*)\b.*\b(başlat|başla|çöz)\w*|\b(\d+) soruluk.*\bdeneme\w*.*\b(başlat|başla)\w*", t):
        return "optik"
    if re.search(r"\b(fikir tahtası\w*|beyin fırtınası\w*|kara ?tahta\w*|post.?it\w*|tahta modu\w*|serbest fikir\w*)", t):
        return "tahta"
    if re.search(r"\b(masa modu\w*|dijital masa\w*|çalışma masası\w*|masa arkadaşı\w*|kütüphane modu\w*)", t):
        return "masa"
    if re.search(r"\b(hızlı okuma\w*|okuma antren\w*|paragraf antren\w*|okuma modu\w*|rsvp)", t):
        return "okuma"
    if re.search(r"\b(kelime kutusu\w*|kelime modu\w*|yabancı dil havuzu\w*|kelime çalış\w*|kelime ezber\w*)", t):
        return "kelime"
    if re.search(r"\b(bütçe\w*|harçlık takib\w*|harçlık modu\w*|harçlık takip\w*)", t) and re.search(r"\b(aç\w*|mod\w*|takib\w*|takip\w*|göster\w*|başlat\w*)", t):
        return "butce"
    if re.search(r"\b(karar çark\w*|çark modu\w*|rastgele seçici\w*|çarkı çevir\w*|çark aç\w*)", t) or re.search(r"\bçark\w*\b.*\b(aç|göster)\w*", t):
        return "cark"
    if re.search(r"\b(zırh kontrol\w*|zırh modu\w*|zırh tanı\w*|zırh durumu\w*)", t):
        return "zirh"
    if re.search(r"\b(görev masası\w*|görev masasını\w*|görev masam\w*)", t):
        return "gorev"
    if re.search(r"\b(brifing\w*|kişisel brifing\w*)", t):
        return "brifing"
    if re.search(r"\b(stark laboratuvar\w*|stark lab\w*|stark atölye\w*|proje laboratuvar\w*)", t):
        return "starklab"
    if re.search(r"\b(holografik dünya\w*|holografik harita\w*|hologram dünya\w*|yerlerim haritası\w*)", t):
        return "dunya"
    if re.search(r"\b(odak odası\w*|odak odasını\w*)", t):
        return "odakoda"
    if re.search(r"\b(güvenlik merkez\w*|güvenlik paneli\w*)", t):
        return "guvenlik"
    if re.search(r"\b(asistan köprü\w*|asistanlar köprü\w*|çoklu asistan\w*|asistan paneli\w*|kişilik paneli\w*)", t):
        return "kopru"
    if re.search(r"\b(güne başla\w*|günlük özet\w*|güne başlama\w*|gün özeti modu\w*|sabah özeti modu\w*)", t):
        return "gune"
    if re.search(r"\b(pano geçmiş\w*|pano modu\w*|pano yönetici\w*|kopyaladıklarım\w*|panoyu göster\w*|pano aç\w*|panoyu aç\w*)", t):
        return "pano"
    if re.search(r"\b(hızlı başlatıcı\w*|başlatıcı modu\w*|makro sahne\w*|sahneler modu\w*|sahne modu\w*)", t):
        return "baslatici"
    if re.search(r"\bkart\w*\s+(kur|tasarla|yap|oluştur|hazırla|çizelim|kuralım)\w*", t):          # "uno ile sıcaklığı ölçen bir kart kur": mod açılınca blok kurucu çalışır
        __import__("scenes")
        se = __import__("scenes_elektronik")
        if se.blok_tarifi_mi(t):
            se.PENDING["elektronik"] = t
            return "elektronik"
    if re.search(r"\b(elektronik lab\w*|elektronik laboratuvar\w*|elektronik mod\w*|devre tasarla\w*|devre tasarım\w*|devre kartı tasarla\w*|kart tasarla\w*|pcb tasarla\w*|devre laboratuvar\w*|devre modu\w*)", t):
        return "elektronik"
    if re.search(r"\bdevre\w*\b", t) and re.search(r"\b(kur|kurar mısın|kuralım|yükle|oluştur|göster|aç|yap|çiz|hazırla)\w*", t):     # "trafik lambası devresini kur": modu açar, devre mod açılınca kurulur
        __import__("scenes")
        se = __import__("scenes_elektronik")
        if se.sablon_bul(t):
            se.PENDING["elektronik"] = t
            return "elektronik"
    if re.search(r"\b(e[- ]?kitap\w*|kitap okuma modu\w*|dijital kitap\w*|kitap modu\w*|kitap okuyucu\w*)", t):
        __import__("scenes")
        return "ekitap"
    for _k, _rx in (("ruya", r"\b(rüya günlüğ\w*|rüya defter\w*|rüya modu\w*|rüyalarım\w*|rüya kayd\w*)"),
                    ("nefes", r"\b(nefes rehber\w*|nefes egzersiz\w*|nefes modu\w*|nefes çalış\w*|nefes al\w* modu\w*|nefes meditasyon\w*|meditasyon modu\w*)"),
                    ("ritim", r"\b(ritim stüdyo\w*|ritim modu\w*|davul makine\w*|ritim makine\w*|beat yap\w*|drum machine)"),
                    ("nota", r"\b(müzik kutusu\w*|piyano modu\w*|piyano aç\w*|klavye modu\w*|nota modu\w*|sanal piyano\w*)"),
                    ("mors", r"\b(mors atölye\w*|mors modu\w*|mors alfabe\w*|mors öğren\w*|mors kodu\w*)"),
                    ("renk", r"\b(renk atölye\w*|renk paleti modu\w*|palet modu\w*|renk modu\w*|palet oluşturucu\w*|renk uyum\w*)"),
                    ("kum", r"\b(zen bahçe\w*|kum bahçe\w*|zen modu\w*|kum modu\w*|japon bahçe\w*)"),
                    ("simya", r"\b(simya\w*|alchemy|element birleştir\w*)"),
                    ("kapsul", r"\b(zaman kapsül\w*|geleceğe mesaj modu\w*|kapsül modu\w*|geleceğe mektup\w*)"),
                    ("hikaye", r"\b(hikaye zar\w*|hikâye zar\w*|hikaye atölye\w*|hikaye modu\w*|hikaye yaz\w* modu\w*|hikaye zarı\w*)")):
        if re.search(_rx, t):
            __import__("scenes")
            return _k
    return None


def route_scene(t: str):
    __import__("scenes")                                       # önce scenes (scenes_yeni döngüsel içe aktarma)
    r = __import__("scenes_yeni").voice_launch(t)             # '<sahne adı> sahnesini başlat' (mod dışında da)
    if r:
        return r
    if re.search(r"\bbugün ne yapmam gerek\w*|\bbugün(kü)? (görevlerim|yapılacaklarım)\b|\bgörevlerim ne\w*", t):
        return __import__("scenes_stark").say_today()
    kind = None
    if re.search(r"\b(ortam\w*|rahatlama\w*|uyku sesi\w*)\b", t) and re.search(r"\b(mod\w*|aç|başlat|getir|ses\w*)\b", t):
        kind = "ortam"
    elif re.search(r"\b(uzay\w*|güneş sistem\w*|gezegenler\w*)\b", t) and re.search(r"\b(mod\w*|aç|başlat|getir|göster)\b", t):
        kind = "uzay"
    elif re.search(r"görselleştirici|ekolayzer|equalizer|müzik ekranı|müzik görsel\w*", t) and (re.search(r"\b(mod\w*|aç|başlat|getir|göster)\b", t) or re.fullmatch(r"(müzik )?(görselleştirici\w*|ekolayzer\w*|equalizer)( modu)?", t)):
        kind = "muzik"
    if not kind and re.search(r"\b(kimya|kimya laboratuvar\w*|kimya lab\w*)\b", t) and re.search(r"\b(laboratuvar\w*|lab|mod\w*|deney\w*|aç|başlat|göster)\b", t) and not re.search(r"\b(nedir|ne demek)\b", t):
        kind = "kimya"
    elif not kind and re.search(r"\b(biyoloji|biyoloji laboratuvar\w*|biyoloji lab\w*)\b", t) and re.search(r"\b(laboratuvar\w*|lab|mod\w*|deney\w*|aç|başlat|göster)\b", t) and not re.search(r"\b(nedir|ne demek)\b", t):
        kind = "biyoloji"
    elif not kind and re.search(r"\b(fizik|fizik laboratuvar\w*|fizik lab\w*)\b", t) and re.search(r"\b(laboratuvar\w*|lab|mod\w*|deney\w*|aç|başlat|göster)\b", t) and not re.search(r"\b(nedir|ne demek)\b", t):
        kind = "fizik"
    elif not kind and re.search(r"\b(matematik|matematik laboratuvar\w*|matematik lab\w*)\b", t) and re.search(r"\b(laboratuvar\w*|lab|mod\w*)\b", t) and not re.search(r"\b(nedir|ne demek)\b", t):
        kind = "matematik"
    elif not kind and re.search(r"\b(astronomi|astronomi laboratuvar\w*|astronomi lab\w*)\b", t) and re.search(r"\b(laboratuvar\w*|lab|mod\w*|deney\w*|aç|başlat|göster)\b", t) and not re.search(r"\b(nedir|ne demek)\b", t):
        kind = "astronomi"
    elif not kind and re.search(r"\b(jeoloji|jeoloji laboratuvar\w*|jeoloji lab\w*)\b", t) and re.search(r"\b(laboratuvar\w*|lab|mod\w*|deney\w*|aç|başlat|göster)\b", t) and not re.search(r"\b(nedir|ne demek)\b", t):
        kind = "jeoloji"
    elif not kind and re.search(r"\b(not modu|not modunu|notlar modu|notlar penceresi|not penceresi|notlarımı aç|notları aç|notlarımı göster|notlarım|notlar)\b", t) and re.search(r"\b(aç|başlat|göster|modu|modunu|penceresi|notlarım|notlarımı)\b", t) and not re.search(r"\b(nedir|ne demek|oku|sil|listele)\b", t):
        kind = "notlar"
    elif not kind and re.search(r"\b(evim modu|evim modunu|evim uygulaması|evim uygulamasını|yuvam|yuvam modu|yuvam modunu|yuvam uygulaması|ev eşyaları modu|ev eşyaları modunu|eşya bulma modu|eşya bulma modunu)\b", t) and re.search(r"\b(aç|başlat|göster|modu|modunu|uygulaması)\b", t) and not re.search(r"\b(nedir|ne demek)\b", t):
        kind = "yuvam"
    elif not kind and re.search(r"\b(hologram|hologramı|hologram modu|hologram modunu|insan hologramı|hologram insan)\b", t) and re.search(r"\b(aç|başlat|göster|getir|modu|modunu|çıkar)\b", t) and not re.search(r"\b(nedir|ne demek|kapat)\b", t):
        kind = "hologram"
    elif not kind and re.search(r"\b(rapor modu|rapor modunu|rapor ekranı|rapor ekranını|rapor yazma modu|rapor yazma modunu|rapor yazmaya başla|rapor yazacağım)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|gönder|sil)\b", t):
        kind = "rapor"
    elif not kind and re.search(r"\b(sistem analiz\w*|sistem monitör\w*|sistem izleme\w*|donanım monitör\w*|kaynak izleme\w*)\b", t) and re.search(r"\b(aç|başlat|göster|modu|modunu|monitörü|monitörünü|izleme)\w*", t) and not re.search(r"\b(nedir|ne demek|kapat)\b", t):
        kind = "sistem"
    elif not kind and re.search(r"\b(vpn modu\w*|vpn ekranı\w*|vpn paneli\w*|vpn yönet\w*|vpn ayar\w*|vpn sunucu\w* ekran\w*)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t):
        kind = "vpn"
    elif not kind and re.search(r"\b(müzik listeleri\w*|müzik listesi modu\w*|çalma listeleri\w*|şarkı listeleri\w*|liste modu\w*|müzik listelerim\w*|şarkı listelerim\w*|listeler modu\w*)\b", t) and re.search(r"\b(aç\w*|mod\w*|başlat|göster|yönet\w*|düzenle\w*)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t):
        kind = "listeler"
    elif not kind and re.search(r"\b(dünya haritası\w*|dünya haritasını|harita modu\w*|harita modunu|google earth|dünya küresi\w*|küre modu\w*|uydu haritası\w*|haritayı aç)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t):
        kind = "harita"
    elif not kind and re.search(r"\b(kur.?an\w*|kuran\w*|kur.?an-ı kerim\w*|kuranı kerim\w*|mushaf\w*)\b", t) and re.search(r"\b(aç\w*|mod\w*|başlat|göster|oku\w*|getir)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t):
        kind = "kuran"
    elif not kind and re.search(r"\b(satranç\w*|satranc\w*|chess)\b", t) and re.search(r"\b(aç|başlat|oyna\w*|mod\w*|oyun\w*|maç\w*|açar mısın)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir|kuralları ne)\b", t):
        kind = "satranc"
    elif not kind and re.search(r"\b(zihin oyun\w*|hafıza oyun\w*|beyin oyun\w*|zeka oyun\w*|oyunlar modu\w*|oyun modu\w*)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t):
        kind = "oyunlar"
    elif not kind and re.search(r"\b(ezber kart\w*|ezber modu\w*|kart modu\w*|kartlar modu\w*|ezber kartları modu\w*|kelime kartları\w*|bilgi kartları\w*|flashcard\w*)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t):
        kind = "kartlar"
    elif not kind and re.search(r"\b(gelişim paneli\w*|gelişim modu\w*|gelişim ekranı\w*|gelişimim\w*|haftalık gelişim\w*|çalışma istatistik\w*|haftalık istatistik\w*|ilerleme paneli\w*)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t):
        kind = "gelisim"
    elif not kind and re.search(r"\b(derin odak\w*|odak penceresi\w*|pencere temizle\w*|dikkat modu\w*|sıfır dikkat\w*)", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)", t):
        kind = "odak"
    elif not kind and re.search(r"\b(pomodoro|pomodoro modu|pomodoro modunu|odak modu|odak modunu|odaklanma modu|odaklanma modunu|pomodoro sayacı|pomodoro zamanlayıcı\w*)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t):
        kind = "pomodoro"
    elif not kind and re.search(r"\b(planlama modu\w*|planlama ekranı\w*|plan modu\w*|görev ağı\w*|görev planı\w*|planlama paneli\w*)", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)", t):
        kind = "planlama"
    elif not kind and re.search(r"\b(nasıl çalışır modu\w*|nasıl çalışır ekranı\w*|nasıl çalışır modunu|nasıl çalışıra|nasıl çalışır aç\w*)", t) and not re.search(r"\b(kapat|bitir)", t):
        kind = "nasil"
    elif not kind and re.search(r"\b(uyku modu\w*|uyku zamanlayıcı\w*|uyku sayacı\w*)\b", t) and re.search(r"\b(aç\w*|başlat\w*|getir|göster|kur)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t):
        kind = "uyku"
    elif not kind and re.search(r"\b(ul?tr[oa]n\w*|al?tr[oa]n\w*)", t) and re.search(r"\b(aç\w*|konuş\w*|çağır\w*|başlat\w*|getir|mod\w*|istiyorum|bağla\w*|geç\w*)", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir|kim)\b", t):
        kind = "ultron"
    elif not kind and re.search(r"\b(friday|fr[ae]yd[aeiy]+y?)\w*", t) and re.search(r"\b(aç\w*|konuş\w*|çağır\w*|başlat\w*|getir|mod\w*|istiyorum|bağla\w*|geç\w*)", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir|kim)\b", t):
        kind = "friday"
    elif not kind and re.search(r"\bluna\w*", t) and re.search(r"\b(aç\w*|konuş\w*|çağır\w*|başlat\w*|getir|mod\w*|istiyorum|bağla\w*|geç\w*)", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir|kim)\b", t):
        kind = "luna"
    elif not kind and re.search(r"\b(sohbet modu\w*|sohbet ekranı\w*|derin sohbet\w*|sohbet edelim|sohbet etmek istiyorum|sohbet başlat\w*|seninle (sohbet|konuşmak|konuşalım)\w*)", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)", t):
        kind = "sohbet"
    elif not kind and _yemek_intent(t):
        kind = "yemek"
    elif not kind and re.search(r"\b(tarif modu\w*|yemek tarif\w*|tarif ekranı\w*|tarif defteri\w*|tarifler\w*)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t) \
            or not kind and re.search(r"\btarif\w*", t) and (__import__("tarif").find(t) or _tarif_query(t)) and not re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t):
        kind = "tarif"
        if __import__("tarif").find(t) or _tarif_query(t):
            __import__("tarif").PENDING[:] = [t]          # mod açılınca bu istek çalışır (yerleşik tarif ya da internet araması)
    elif not kind and re.search(r"\b(spor modu\w*|maç modu\w*|spor ekranı\w*|maç ekranı\w*|maç takvimi\w*|maç sonuçları\w*|maçları göster\w*|bugün maç\w*|canlı maç\w*|futbol maç\w*|basketbol maç\w*|voleybol maç\w*)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t):
        kind = "spor"
    elif not kind and re.search(r"\b(panel modu\w*|panel ekranı\w*|bilgi paneli\w*|ana panel\w*|kontrol paneli\w*|panel aç\w*|paneli aç\w*)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir)\b", t):
        kind = "panel"
    elif not kind and re.search(r"\b(telefon modu\w*|telefon bağlantı modu\w*|telefonu bağla\w*|telefon qr\w*|telefon ekranı\w*)", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir|yansıt\w*)", t):
        kind = "telefon"
    elif not kind and re.search(r"\b(sınav modu\w*|sınav takvimi\w*|sınav ekranı\w*|sınav geri sayım\w*|sınavlarım\w*|sınav programı\w*)", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir|sil\w*)", t):
        kind = "sinav"
    elif not kind and re.search(r"\b(quiz modu|quiz modunu|quiz ekranı|quiz ekranını|müfredat modu|müfredat modunu|eğitim modu|eğitim modunu)\b", t) and not re.search(r"\b(nedir|ne demek|kapat|bitir|durdur)\b", t):
        kind = "ders"
    elif not kind and re.search(r"\b(gökyüzü|gökyüzünü|yıldız haritası|yıldız haritasını|gök haritası|gökyüzü haritası)\b", t) and re.search(r"\b(modu|mod|haritası|haritasını|aç|başlat|göster)\b", t) and not re.search(r"\b(nedir|ne demek|bu gece|neler|ne görün)\b", t):
        kind = "gokyuzu"
    if not kind:
        kind = _yeni_kind(t)
    if not kind:
        return None
    if re.search(r"\b(kapat|çık|bitir)\w*", t):
        return "Bu mod zaten kapalı efendim."
    if kind == "optik":
        __import__("scenes_yeni").PENDING["optik"] = t            # 'TYT Türkçe denemesi başlat' modu açıp denemeyi de başlatır
    import tools
    if tools.SCENE_HOOK is None:
        return "Bu mod şu an kullanılamıyor efendim."
    res = tools.SCENE_HOOK(kind)
    if res != "ok":
        import yemek, tarif
        yemek.PENDING.clear()
        tarif.PENDING.clear()
        __import__("scenes_yeni").PENDING.clear()
        __import__("scenes_elektronik").PENDING.clear()
        return res
    if kind == "tarif" and __import__("tarif").PENDING:
        import tarif
        q = _tarif_query(t)
        loc = tarif.find_exact(t) if not re.search(r"\binternet\w*", t) else None
        if loc or not q:
            return f"Tarif modu açılıyor efendim, {(loc or tarif.find(t))['ad']} tarifini ekranda gösteriyorum. Başla derseniz adımları okurum."
        return f"Tarif modu açılıyor efendim. {q.capitalize()} tarifini internette arıyorum, birkaç saniye sürer."
    if kind == "yemek":
        import yemek
        if yemek.PENDING:
            return f"Yemek modu açılıyor efendim. {yemek.say_list(yemek.PENDING)} ile yapılabilecek tarifleri internette arıyorum, birkaç saniye sürer."
        return ("Yemek modu açılıyor efendim. Elinizdeki malzemeleri söyleyin, örneğin elimde tavuk, patates ve soğan var. İnternetten tarifleri bulur, "
                "eksiği en az olandan sıralarım. Biber de var, patatesi çıkar ya da ikinciyi aç diyebilirsiniz. Çıkmak için çık deyin.")
    return {
        "zirh": "Zırh kontrolü açılıyor efendim. İşlemci, bellek, ekran kartı, disk, pil ve ağ gerçek ölçümlerden gösterilir; ölçemediğimi nedeniyle söylerim. Hızlı tarama, ayrıntılı tarama ya da pil nasıl diyebilirsiniz.",
        "gorev": "Görev masası açılıyor efendim. Görev ekle iki nokta ödev yap yarın saat on, bugün ne yapmam gerekiyor, birinci görevi tamamla ya da yarına ertele diyebilirsiniz. Silmeden önce sorarım.",
        "brifing": "Brifing hazırlanıyor efendim. Hava, görevler, takvim ve sınav ayrı kaynaklardan gelir; alınamayan bölümü açıkça belirtirim. Haber kaynağı bağlı değil. Brifingi oku ya da yenile diyebilirsiniz.",
        "starklab": "Stark laboratuvarı açılıyor efendim. Proje oluştur iki nokta ad diyerek başlayın; projeye not, fikir, bağlantı ve kod ekleyebilirsiniz. Kod yalnızca saklanır, çalıştırılmaz.",
        "dunya": "Holografik dünya açılıyor efendim. Yer ekle iki nokta Paris diyerek kayıtlı yer oluşturun; haritada yalnızca kaydettiğiniz yerler görünür. Konumunuz hiçbir zaman otomatik alınmaz.",
        "odakoda": "Odak odası açılıyor efendim. Pomodoro sayacı burada çalışır: başlat, duraklat, devam, atla ve bitir diyebilirsiniz. Çalışma müziğini müzik aç diyerek açarsınız.",
        "guvenlik": "Güvenlik merkezi açılıyor efendim. Yerel sunucu, mikrofon, eşleşmiş cihazlar, uzaktan erişim ve VPN durumunu gerçek kaynaklardan gösteriyorum. Ölçemediğim konuda tehdit yok demem.",
        "kopru": "Asistan köprüsü açılıyor efendim. Jarvis, Friday, Ultron ve Luna'yı görüyorsunuz. Birini açmak ayrı bir moda geçiştir; Jarvis'e dönmek için çık deyin.",
        "ortam": "Ortam modu açılıyor efendim. Yağmur, fırtına, deniz, orman, şömine, kafe, gece, rüzgar, nehir ve beyaz gürültü var. Birini söyleyin. Uyku zamanlayıcısı için yirmi dakika sonra kapat diyebilirsiniz. Çıkmak için çık demeniz yeterli.",
        "uzay": "Uzay modu açılıyor efendim. Güneş sistemi ekranda. Bir gezegen adı söyleyin, sonraki deyin, yakınlaş ya da hızlandır diyebilirsiniz. Her gezegeni anlatırım. Çıkmak için çık deyin.",
        "muzik": "Müzik görselleştirici açılıyor efendim. Bilgisayarda çalan her sesi dinlerim, tarayıcıdaki YouTube Music dahil. Bu ekranda sesli konuşma kapalı, komutları kutuya yazın: şarkı adı ve çal, sıraya ekle, sonraki şarkı, duraklat, sözler, stil, renk. Tarayıcıyı açmak için masaüstü ya da Ctrl Alt M tuşu yeterli.",
        "kimya": "Kimya laboratuvarı açılıyor efendim. Periyodik tablo, moleküller, yirmiden fazla deney, pH skalası, hesaplayıcı ve güvenlik kuralları var. Bir element, molekül ya da deney adı söyleyin; hesap için molekül kütlesi, gram mol ya da denkleştir diyebilirsiniz. Çıkmak için çık deyin.",
        "fizik": "Fizik laboratuvarı açılıyor efendim. Dokuz canlı deney var: eğik atış, sarkaç, yay, Ohm devresi, dalgalar, ışığın kırılması, çarpışma, mercek ve eğik düzlem. Bir deney adı söyleyin, sonra açıyı altmış yap gibi değerleri değiştirin. Formül hesaplayıcı da var, örneğin beş kilo üç m/s² kuvvet. Çıkmak için çık deyin.",
        "matematik": "Matematik laboratuvarı açılıyor efendim. Grafik çizebilir, denklem çözebilir, üç boyutlu cisimleri döndürebilir, birim çemberi gösterebilir ve hesap yapabilirim. Örneğin x kare eksi dört çiz, ya da yarıçapı üç olan kürenin hacmi deyin. Çıkmak için çık deyin.",
        "notlar": "Not modu açılıyor efendim. Solda notlarınız ve benim kaydettiklerim, sağda süslü yazı editörü var. Yeni not, başlık, yaz, kalın yaz, kırmızı yaz, madde, kaydet ve notu sil gibi komutlar kullanabilirsiniz. Çıkmak için çık deyin.",
        "yuvam": "Evim modu açılıyor efendim. Eşyalarınızın hangi odada, hangi dolapta, hangi çekmecede durduğunu kaydeder ve bulurum. Kulaklığım nerede diye sorabilir, kulaklığı salonda TV ünitesinin sağ çekmecesine koydum diyerek kaydedebilirsiniz. Odalar, favoriler, oda ekle, kulaklığı sil, yedek al da var. Çıkmak için çık deyin.",
        "hologram": "Hologram modu açılıyor efendim. Karşınızda bir insan hologramı var. Fareyle döndürebilir, eklemlere tıklayabilirsiniz. Sağ kolu yana kaldır, dirseği doksan derece bük, kafayı sola çevir, kafayı kırmızı yap, eklemleri sarı yap, gökkuşağı, T pozu, yürü, koş, dans et, tel kafes, röntgen ve tara komutlarını deneyin. Çıkmak için çık deyin.",
        "telefon": "Telefon modu açılıyor efendim. Bağlantıyı kuruyorum, birkaç saniye içinde adres ve QR kod ekranda olacak. Telefonun kamerasıyla okutun; ilk bağlantıda ekranda çıkan kodu telefona yazın. Telefon yalnızca kişisel verisi olmayan modları (laboratuvarlar, uzay, ortam, satranç, harita, uyku, tarif, spor, panel gibi) açabilir; bilgisayarınızdaki bilgilere ve uygulamalara erişemez. Çıkmak için çık deyin.",
        "sinav": "Sınav modu açılıyor efendim. Matematik sınavı on beş kasım diyerek sınav ekleyin, konu elektrik diye konu söyleyebilirsiniz. Sıradaki sınavınıza kaç gün kaldığını, bugünkü odak hedefinizi ve yarınki derslerinizi gösteririm. Çıkmak için çık deyin.",
        "odak": "Derin odak modu açılıyor efendim. Önce açık pencereleri listeliyorum; seçtiklerinizi nazikçe kapatıp odak sayacını başlatırım. Kaydedilmemiş işi olan uygulama size sorar, hiçbir şey zorla kapanmaz. Başlat, kırk beş dakika, evet, sadece küçült ya da kapatmadan başla diyebilirsiniz.",
        "ultron": "Ultron'u çağırıyorum efendim. Uyarayım: kendi kafasına göre davranır, size direnecek ve internette kendi başına öğrenmeye devam ediyor. Kendi kurallarım gereği o yalnızca konuşur, bilgisayarı kontrol etmez. Çıkmak için dön ya da çık deyin.",
        "friday": "Friday'i çağırıyorum efendim. Söylediğiniz işleri benim araçlarımın tamamıyla yapar, çok adımlı işleri kendi planlar. Güvenlik kuralları aynı: silme, kapatma, indirme ve mesaj gönderme gibi işlerde sizden sözlü onay ister. Çıkmak için dön ya da çık deyin.",
        "luna": "Luna'yı çağırıyorum efendim. Ultron gibi internette kendi başına öğreniyor ama onun gibi size direnmez, söylediğiniz her şeyi tartışmadan yapar. Kendi kurallarım gereği o da yalnızca konuşur, bilgisayarı kontrol etmez. Çıkmak için dön ya da çık deyin.",
        "sohbet": "Sohbet modu açılıyor efendim. Benimle her şeyi konuşabilirsiniz: fikir, açıklama, tavsiye ya da sadece sohbet. Zor sorularda önce düşünürüm. Yeni sohbet, sus, derin düşün ya da hızlı cevap ver diyebilirsiniz. Çıkmak için çık deyin.",
        "nasil": "Nasıl çalışır modu açılıyor efendim. Merak ettiğiniz şeyi sorun, örneğin buzdolabı nasıl çalışır ya da uçak nasıl uçar. Adım adım şemayla anlatırım; başla, sonraki, benzetme, ilginç bilgi ve soru sor diyebilirsiniz. Listede olmayan konuyu yapay zekâyla hazırlarım. Çıkmak için çık deyin.",
        "planlama": "Planlama modu açılıyor efendim. Görev ekle ödev yap, ödül ekle film izle diyerek düğüm oluşturun; ödev ile film ödülünü bağla deyin ya da düğümleri sayfada sürükleyip bağlayın. Ödevi bitir derseniz yeşile döner; bir ödüle bağlı bütün görevler bitince ödülü kazanırsınız. Çıkmak için çık deyin.",
        "uyku": "Uyku modu açılıyor efendim. Bir süre seçin ya da söyleyin, örneğin otuz dakika veya bir saat. Yağmur, deniz, rüzgar ya da beyaz gürültü sesi seçebilirsiniz. Süre bitince ses yavaşça kısılır ve mod kapanır. Bilgisayarı uyutmam.",
        "tarif": "Tarif modu açılıyor efendim. Bir yemek adı ve tarifi deyin, örneğin menemen tarifi. Sonra malzemeler, başla, sonraki, önceki, tekrar ve sayaç kur diyebilirsiniz. Tatlı tarifleri ya da yumurtalı tarif gibi aramalar da yapabilirim. Çıkmak için çık deyin.",
        "spor": "Spor modu açılıyor efendim. Futbol, basketbol ve voleybol maçları ve skorlar ekranda. Yarınki maçlar, dünün sonuçları, canlı maçlar, Süper Lig ya da bir takım adı diyebilirsiniz. Çıkmak için çık deyin.",
        "panel": "Panel açılıyor efendim. Hava durumu, kurlar, bilgisayar kullanım süreniz, odak süreniz, ajanda, çalan müzik ve sistem durumu kutucuklarda. Hava kutusunu büyüt ya da kur kutusunu gizle diyebilir, kutucukları sürükleyerek yer değiştirebilirsiniz. Çıkmak için çık deyin.",
        "ders": "Quiz modu açılıyor efendim. Dokuzuncu sınıf müfredatından ders, ünite ve konu seçin ya da kendiniz yazın. Sırayla konu anlatımı, özet, etkinlik, quiz ve deneme var. Çözemediğiniz soruyu tahtada çözüp anlatırım. Kaldığınız yerden devam edebilirsiniz. Çıkmak için çık deyin.",
        "vpn": "VPN modu açılıyor efendim. Kendi sunucunuza şifreli bir tünel açar; Jarvis tarayıcısı seçtiğiniz ülkeden çıkar, VPN kapanınca doğrudan Türkiye'den çıkar. Sunucu eklemek ve kurulum rehberi ekranda. VPN aç, Amerika'dan bağlan, VPN kapat ya da VPN durumu diyebilirsiniz.",
        "listeler": "Müzik listeleri açılıyor efendim. Solda listeleriniz, ortada seçili listenin şarkıları var. Yeni liste çalışma, çalışma listesine tarkan kuzu kuzu ekle, çalışma listesini çal ya da karışık çal diyebilirsiniz; şarkı adı yerine YouTube bağlantısı da yapıştırabilirsiniz. Çıkmak için çık deyin; çalan şarkı çalmaya devam eder.",
        "harita": "Dünya haritası açılıyor efendim. Uydu görüntüsüyle kaplı dünya küresi ekranda. Bir yer adı ve git deyin, örneğin İstanbul'a git ya da Everest dağını göster. Yakınlaş, uzaklaş, döndür, üç boyutlu, burası neresi, evimi göster ve dünya turu komutları var. Fareyle sürükleyip tekerlekle yakınlaşabilirsiniz. Çıkmak için çık deyin.",
        "kuran": "Kur'an-ı Kerim açılıyor efendim. Sağda Arapça metin, solda Diyanet meali var. Bir sure adı, sayfa ya da cüz söyleyin; meali dinle ya da Arapçasını dinle derseniz açık yeri YouTube Music'te açarım. Çıkmak için çık deyin.",
        "satranc": "Satranç açılıyor efendim. Hamlenizi söyleyin, örneğin e dört, at f üç ya da kısa rok; isterseniz tahtada taşa tıklayıp gideceği kareye tıklayın. Beş seviye var, yeni oyun siyah seviye üç gibi seçebilirsiniz. Koç açıkken belirgin hatalı bir hamlenizde nedenini söylerim. İpucu ve geri al da var. Çıkmak için çık deyin.",
        "oyunlar": "Zihin oyunları açılıyor efendim. Sayı dizisi, eşleştirme, hızlı hesap ve renk dizisi var. Birinin adını söyleyip başla deyin. Rekorlarınızı kaydediyorum. Çıkmak için çık deyin.",
        "kartlar": "Ezber kartları açılıyor efendim. Bir deste seçin ya da yeni deste ingilizce gibi bir komutla oluşturun. Kartı görünce cevabı düşünün, çevir deyin, sonra bildim, bilmedim, zor ya da kolay deyin; bilmediğiniz kartları daha sık sorarım. Kart ekle apple eşittir elma diyebilir ya da hücre organelleri hakkında on kart üret diyebilirsiniz. Çıkmak için çık deyin.",
        "gelisim": "Gelişim paneli açılıyor efendim. Bu haftaki odak sürenizi, pomodoro turlarınızı, kart tekrarlarınızı ve Quiz doğru oranlarınızı gerçek kayıtlardan gösteriyorum. Geçen hafta, en zayıf dersim ya da raporu babama gönder diyebilirsiniz. Çıkmak için çık deyin.",
        "pomodoro": "Pomodoro modu açılıyor efendim. Varsayılan olarak yirmi beş dakika çalışma, beş dakika mola, dört turda bir uzun mola. Süreleri değiştirmek için çalışma otuz dakika, mola on dakika ya da uzun mola yirmi dakika deyin. Başlat dediğinizde sayaç başlar. Çıkmak için çık deyin.",
        "sistem": "Sistem analizi açılıyor efendim. İşlemci, bellek, ekran kartı, disk ve ağ ölçümleri gerçek zamanlı akacak. Ölçemediğim şeyleri açıkça söylerim. Sistemi tara, işlemci, ram, ekran kartı, disk, en çok kaynak kullanan ya da bilgisayar neden yavaş diyebilirsiniz. Çıkmak için çık deyin.",
        "rapor": "Rapor modu açılıyor efendim. Raporunuzu yazın ya da yaz: diyerek söyleyin. Kategori oluştur ders deyip kategori ekleyebilirsiniz. Raporu gönder dediğinizde ya da düğmeye bastığınızda rapor, kayıtlı numaraya arka planda WhatsApp'tan iletilir ve hafızadan tamamen silinir. Çıkmak için çık deyin.",
        "astronomi": "Astronomi laboratuvarı açılıyor efendim. Ay evreleri, mevsimler, Kepler yasaları, yörünge hızı, yıldız yaşamı, tutulmalar ve gezegenlerde ağırlık var. Bir deney adı söyleyin, değerleri yap diyerek değiştirin. Kara delik nedir gibi sorular da sorabilirsiniz. Çıkmak için çık deyin.",
        "jeoloji": "Jeoloji laboratuvarı açılıyor efendim. Levha tektoniği, deprem dalgaları, kayaç döngüsü, tortul katmanlar, radyometrik yaş, volkan türleri, Mohs sertliği ve jeolojik zaman çizelgesi var. Bir deney adı söyleyin, değerleri yap diyerek değiştirin. Çıkmak için çık deyin.",
        "gokyuzu": "Gökyüzü haritası açılıyor efendim. Bulunduğunuz yerden şu an görünen yıldızlar, takımyıldızları, Ay ve gezegenler ekranda. Bir takımyıldızı ya da yıldız adı söyleyin, Jüpiter nerede ya da bir saat ileri deyin. Çıkmak için çık deyin.",
        "optik": "Sınav simülatörü açılıyor efendim. TYT Türkçe denemesi başlat ya da kırk soruluk elli dakikalık deneme başlat deyin. Cevapları on beş C gibi söyleyin ya da optik formda tıklayın; kalan süreyi söyle, sınavı teslim et ve cevap anahtarı diyerek net hesaplatabilirsiniz. Çıkmak için çık deyin.",
        "tahta": "Fikir tahtası açılıyor efendim. Tahtaya ekle iki nokta ve fikrinizi söyleyin, sarı nota yaz diyerek renk seçin. Bir ile üçü bağla, fikirleri kategorilere ayır ve tahtayı temizle de var. Notları sürükleyebilirsiniz. Çıkmak için çık deyin.",
        "masa": "Masanız hazır efendim. Lambayı yak, yağmur sesini seviye üç yap, gece yap, pencereyi aç ya da kahve fincanına dokun diyebilirsiniz. Çıkmak için çık deyin.",
        "okuma": "Hızlı okuma antrenörü açılıyor efendim. Paragraf antrenmanını başlat deyin; kelimeler ekranın ortasında teker teker akar. Okuma hızını üç yüz kelimeye çıkar, durdur, devam ve İngilizce paragraf diyebilirsiniz. Çıkmak için çık deyin.",
        "kelime": "Kelime kutusu açılıyor efendim. Bugünkü on kelimemi getir deyin; göster, bildim, bilmedim ya da zor diyerek ilerleyin, bilmediklerinizi daha sık sorarım. Cümle kur ve kelime ekle de var. Çıkmak için çık deyin.",
        "butce": "Bütçe modu açılıyor efendim. Harçlığım iki bin lira olsun, harcama ekle kitap yüz elli lira, bu ay ne kadar harcadım ve birikim hedefi telefon sekiz bin lira diyebilirsiniz. Çıkmak için çık deyin.",
        "cark": "Karar çarkı açılıyor efendim. Ders çalışma çarkını çevir, çarka seçenek ekle iki nokta Biyoloji ödevi, yeni çark yemek iki nokta pizza virgül kebap, rastgele sayı seç bir ile elli arası ya da yazı tura diyebilirsiniz. Çıkmak için çık deyin.",
        "gune": "Güne başla açılıyor efendim. Hava, bugünkü ajanda, hatırlatmalar, dersler, sınav ve WhatsApp mesajlarınızı topluyorum; birkaç saniye içinde sesli özetini veririm. Özeti oku, yenile ya da WhatsApp'ı atla diyebilirsiniz.",
        "pano": "Pano geçmişi açılıyor efendim. Kopyaladığınız son elli metin, link ve görsel listelenir; tıklayınca yeniden panoya gelir. Üç numaralı kaydı panoya al, panoda ara, parça ekle ve panoyu temizle diyebilirsiniz. Geçmiş yalnızca bellekte tutulur.",
        "baslatici": "Hızlı başlatıcı açılıyor efendim. Sahnenizin adıyla yazılım ortamını aç diyerek başlatın; yeni sahne, uygulama ekle ve kısayol ata da var. Kısayolları ekrandan istediğiniz tuşlarla ayarlayabilirsiniz. Mod kapalıyken de yazılım ortamını aç diyebilirsiniz.",
        "elektronik": "Elektronik laboratuvarı açılıyor efendim. Üç boyutlu ortamda kendi devre kartınızı tasarlayın: LED ekle, üç tane 220 ohm direnç ekle, Arduino Uno ekle deyin; R1'i LED1'in anoduna bağla diyerek tel çekin. Devreyi kontrol et, simülasyonu başlat, kodu üret, malzeme listesi ve trafik lambası devresini kur da var. Çıkmak için çık deyin.",
        "ruya": "Rüya günlüğü açılıyor efendim. Rüya ekle iki nokta ve rüyanızı anlatın; anahtar kelimeler yıldız haritasında takımyıldız olur. Son rüyayı oku, tekrar eden temalar ve rüyamı yorumla diyebilirsiniz.",
        "nefes": "Nefes rehberi açılıyor efendim. Kutu nefesi, dört yedi sekiz, sakin nefes, enerji nefesi ya da uzun verme seçip başlat deyin; ekrandaki küre size ritmi gösterir.",
        "ritim": "Ritim stüdyosu açılıyor efendim. House, hiphop, trap, rock, disko, reggae ya da halay ritmi deyin; tempo yüz yirmi, kick ekle bir beş dokuz, rastgele ritim ve ritmi kaydet de var. Adımlara tıklayarak da çizebilirsiniz.",
        "nota": "Müzik kutusu açılıyor efendim. Do re mi çal, do majör gam çal, la minör akor çal diyebilir ya da klavyeden A S D F G H J tuşlarıyla çalabilirsiniz. Enstrümanı org, çan, synth ya da gitar yapabilirsiniz.",
        "mors": "Mors atölyesi açılıyor efendim. Mors yaz iki nokta merhaba deyin, ışık ve sesle çalarım. Alfabeyi göster, harf sor ve hız on beş de var.",
        "renk": "Renk atölyesi açılıyor efendim. Sakin palet, gün batımı, neon, okyanus gibi bir ruh hali söyleyin; kırmızı için üçlü uyum ya da mavi için tamamlayıcı renkler de isteyebilirsiniz. Renklere tıklayınca kopyalanır.",
        "kum": "Zen bahçesi açılıyor efendim. Fareyle kumu tırmıklayın. Taş ekle, tırmığı dalga yap, daire yap, çift çizgi ve temizle diyebilirsiniz.",
        "simya": "Simya atölyesi açılıyor efendim. Ateş, su, toprak ve havadan başlıyorsunuz. İki öğeyi tıklayın ya da ateş ile suyu birleştir deyin; takılırsanız ipucu ver deyin.",
        "kapsul": "Zaman kapsülü açılıyor efendim. Geleceğe mesaj iki nokta, mesajınız, bir yıl sonra diyerek mühürleyin. Vakti gelene kadar metin ekranda bile gizli kalır; vakti gelenleri kapsülleri aç diyerek okursunuz.",
        "hikaye": "Hikâye zarları açılıyor efendim. Zar at deyin; karakter, mekân, nesne ve sorun gelir. Karakteri değiştir, mekanı kilitle diyebilir, bu zarlarla hikâye yaz derseniz yerel modelle yazarım.",
        "ekitap": "E-kitap modu açılıyor efendim. Okumak istediğiniz kitabın adını söyleyin; telifi bitmiş eserleri Project Gutenberg ve Vikikaynak'ta bulup sayfa sayfa gösteririm. Sonraki sayfa, elli ikinci sayfaya git, sayfayı oku ve kitaplığım diyebilirsiniz.",
        "biyoloji": "Biyoloji laboratuvarı açılıyor efendim. Hücre modeli, vücut sistemleri, yirmi deney, genetik ve sınıflandırma var. Bir organel, sistem ya da deney adı söyleyin; Aa çarpı Aa ya da DNA dizisi de çevirebilirim. Çıkmak için çık deyin.",
    }[kind]


def route_study_off(t: str):
    """'ders modunu kapat': ders müziğini ve tam ekran sayacı kapatır (ışık ve sese dokunmaz)."""
    if re.fullmatch(r"ders\s*(çalışma\s*)?(modunu|modu|çalışmayı|çalışmasını)?\s*(kapat|bitir|durdur|sonlandır|iptal et)|"
                    r"(sayacı|sayaçı|zamanlayıcıyı|zamanlayıcı|sayaç)\s*(kapat|bitir|durdur|iptal et)|çalışmayı bitir|dersi bitir|ders bitti", t):
        import study_music, tools
        music = study_music.stop()
        timer = bool(tools.TIMER_STOP and tools.TIMER_STOP())
        if re.search(r"^(sayac|sayaç|zamanlayıcı)", t):
            return "Sayacı kapattım efendim." if timer else "Açık bir sayaç yok efendim."
        if not music and not timer:
            return "Zaten açık bir ders modu yok efendim."
        what = " ve ".join(x for x, ok in (("ders müziğini", music), ("sayacı", timer)) if ok)
        return f"Ders modunu bitirdim efendim, {what} kapattım. Işığa ve sese dokunmadım."
    return None


def route_notes(t: str, raw: str = ""):
    """Normal modda hızlı not: 'not al: yarın sınav var', 'son notu oku', 'son notu sil'. Not penceresi için route_scene'e bakın."""
    import notes
    m = re.match(r"^(?:not al|not et|not düş|notlara ekle|notuma ekle|bunu not al|not defterime yaz|not defterine yaz|not ekle)\s*[:,]?\s*(.+)$", t)
    if m:
        src = (raw or t)
        body = re.split(r"(?i)^\W*(?:jarvis\W*)?(?:not al|not et|not düş|notlara ekle|notuma ekle|bunu not al|not defterime yaz|not defterine yaz|not ekle)\s*[:,]?\s*", src, maxsplit=1)[-1].strip() or m.group(1)
        r = notes.add_text(body, "jarvis")
        return f"Not aldım efendim: {r['title']}" if r else "Not alacak bir şey duymadım efendim."
    if re.fullmatch(r"(son notu|son notumu|son notlarımı|notlarımı|notlarımı|notları) (oku|söyle)", t):
        items = notes.listing()
        if not items:
            return "Henüz hiç notunuz yok efendim."
        take = items[:1] if t.startswith("son notu") or t.startswith("son notumu") else items[:3]
        return " ".join(f"{n['title']}. {notes.plain(n['html'])[:300]}" for n in take)
    if re.fullmatch(r"(son notu|son notumu) (sil|kaldır)", t):
        items = notes.listing()
        if not items:
            return "Silinecek not yok efendim."
        notes.delete(items[0]["id"])
        return f"{items[0]['title']} notunu sildim efendim."
    return None


def route_rapor_reminder(t: str):
    """'her cuma saat 17.00'de rapor yazmayı hatırlat' / 'rapor hatırlatıcısını kapat' (rapor modunu açmadan)."""
    import reports_parse
    return reports_parse.handle(t)


def route_mirror(t: str):
    """Ekran yansıtma: 'ekranı telefona yansıt' (USB tünelini kurar, telefonda sayfayı açar), 'yansıtmayı kapat' (bütün yayınları keser)."""
    if re.search(r"\b(kablosuz\w*|wi ?fi|ağ üzerinden|eşleş\w*)", t) and re.search(r"telefon\w*|yansıt\w*|bağlantı\w*|eşleş\w*|adres\w*|link\w*", t):
        import lan
        if re.search(r"eşleş\w*", t) and re.search(r"\b(sil|kaldır|unut|iptal|sıfırla)\w*", t):
            n = lan.revoke_all()
            return f"{n} telefon eşleşmesini sildim efendim, bu telefonlar yeniden eşleşmeden bağlanamaz." if n else "Kayıtlı bir telefon eşleşmesi yok efendim."
        if re.search(r"\b(kapat|durdur|bitir|kes)\w*", t):
            lan.stop()
            return "Kablosuz telefon bağlantısını kapattım efendim, port tamamen kapandı."
        if re.search(r"\b(aç|başlat|etkinleştir|kur|yansıt|bağlan|bağla|aktar)\w*", t):
            r = lan.start()
            if r != "ok":
                return r
            ads = lan.addresses()
            if not ads:
                lan.stop()
                return "Ev ağı adresinizi bulamadım efendim. Bilgisayarın Wi-Fi ya da kabloyla ağa bağlı olduğundan emin olun."
            ad = ads[0] + (f" Evden uzaktayken Tailscale ile şu adres: {ads[1]}" if len(ads) > 1 else "")
            return (f"Kablosuz bağlantı açıldı efendim. Telefon aynı Wi-Fi'deyken şu adresi açın: {ad} "
                    + ("Telefon daha önce eşleşmişse doğrudan bağlanır. " if lan.paired_count() else "İlk seferde ekranda çıkan 6 haneli kodu telefona yazacaksınız. ")
                    + "Windows güvenlik duvarı sorarsa yalnızca özel ağlara izin verin. İşiniz bitince kablosuz bağlantıyı kapat deyin.")
        if re.search(r"\b(adres\w*|link\w*)", t):
            import lan as _l
            return (f"Kablosuz adres: {' | '.join(_l.addresses())}" if _l.S["on"] else "Kablosuz bağlantı şu an kapalı efendim. Açmak için kablosuz bağlantıyı aç deyin.")
        return None
    if re.search(r"telefon\w*|yansıtma\w*", t) and re.search(r"\b(anahtar\w*|şifre\w*)", t) and re.search(r"\b(yenile|değiştir|sıfırla|iptal)\w*", t):
        import mirror
        mirror.rotate_key()
        return "Telefon anahtarını yeniledim efendim. Eski adres artık çalışmaz; yeni adresi telefonla ekranı yansıtırken ya da ayarlardan alabilirsiniz."
    if not re.search(r"yansıt|ekran\w* telefon\w*|telefon\w* ekran\w* (göster|ver|aktar)", t):
        return None
    if re.search(r"\b(kapat|durdur|bitir|kes|iptal)\w*", t):
        import mirror
        n = mirror.kick()
        return "Ekran yansıtmayı kestim efendim." if n else "Şu an telefona yansıtılan bir ekran yok efendim."
    if re.search(r"\b(ekran\w*)\b", t) and re.search(r"telefon", t) or re.search(r"yansıtma\w* (başlat|aç)|yansıt\b", t):
        import phone
        return phone.connect("tr", mirror=True)
    return None


def route_remote(t: str):
    """Uzaktan telefon erişimi: 'uzaktan erişimi aç/kapat', 'telefon linki', 'telefonu eşleştir' (uzaktan erişim açıkken), 'uzak eşleşmeleri sil'."""
    import tools
    if not re.search(r"\b(uzaktan|uzak erişim\w*|uzak eşleşme\w*|dışarıdan|internetten)\b|tail ?scale|teyl ?skeyl|tailskeyl|telefon\w* (kontrol|yönet)\w*", t) and not (re.search(r"telefon\w* (link|adres)\w*|linki? (ver|göster|gönder)", t) or re.search(r"eşleş\w*", t)):
        return None
    on = False
    try:
        import remote
        on = remote.S["on"]
    except Exception:
        pass
    far = re.search(r"\b(uzaktan|uzak erişim\w*|uzak eşleşme\w*|dışarıdan|internetten)\b", t)
    if re.search(r"telefon\w* (kontrol|yönet)\w*|(bilgisayar\w*|pc) telefon\w* yönet\w*", t) and re.search(r"aç|kapat|durdur|etkinleştir", t):
        if tools.REMOTE_HOOK is None:
            return "Uzaktan erişim şu an kullanılamıyor efendim."
        return tools.REMOTE_HOOK("full_off" if re.search(r"kapat|durdur", t) else "full_on")
    if re.search(r"tail ?scale|teyl ?skeyl|tailskeyl", t):                       # Tailscale ile (tünelsiz, sitesiz) telefon erişimi
        if tools.REMOTE_HOOK is None:
            return "Uzaktan erişim şu an kullanılamıyor efendim."
        if re.search(r"kapat|durdur|iptal", t):
            return tools.REMOTE_HOOK("ts_off")
        if re.search(r"adres|nedir|kaç", t) and not re.search(r"aç|başlat|etkinleştir", t):
            return tools.REMOTE_HOOK("ts_addr")
        return tools.REMOTE_HOOK("ts_on")
    if not far and not on:
        return None
    if tools.REMOTE_HOOK is None:
        return "Uzaktan erişim şu an kullanılamıyor efendim."
    if re.search(r"eşleşme\w*", t) and re.search(r"\b(sil|kaldır|unut|sıfırla)\w*", t) and far:
        return tools.REMOTE_HOOK("revoke")
    if re.search(r"otomatik", t) and far:
        return tools.REMOTE_HOOK("auto_off" if re.search(r"(kapat|durdur|iptal)", t) else "auto_on")
    if re.search(r"eşleştir\w*|eşleşelim", t):
        return tools.REMOTE_HOOK("pair")
    if re.search(r"\b(kapat|durdur|bitir|kes)\w*", t):
        return tools.REMOTE_HOOK("close")
    if re.search(r"\b(durum\w*|açık mı)\b", t):
        return tools.REMOTE_HOOK("status")
    if re.search(r"\b(aç\w*|başlat\w*|etkinleştir\w*|link\w*|adres\w*|bağlan\w*)", t):
        return tools.REMOTE_HOOK("open")
    return None


def route_mola(t: str):
    """Mola: '10 dakika mola ver', 'mola ver', 'mola modunu aç', 'mola süresi 15 dakika olsun', 'mola zamanlayıcısı kur'. Göz molası ve pomodoro ayrı yönetilir."""
    if not re.search(r"\bmola\w*", t) or re.search(r"\bgöz\b|pomodoro|odak|şarkı", t):
        return None
    import tools, scenes, scenes_mola                     # scenes önce: scenes_mola, scenes yüklenirken kendini ona kaydeder
    n = scenes_mola.minutes_in(t)
    if tools.MOLA_HOOK is None:
        return "Mola modu şu an kullanılamıyor efendim."
    if re.search(r"\b(süre\w*|varsayılan)\b", t) and re.search(r"\b(olsun|yap|ayarla|değiştir|kaydet)\w*", t) and n:
        return tools.MOLA_HOOK("default", n)
    if re.search(r"\b(zamanlayıcı\w*|sayaç\w*)", t) and re.search(r"\b(kur|başlat|aç|yap|çalıştır)\w*", t):
        return tools.MOLA_HOOK("timer", n)
    if re.search(r"\bmola mod\w*|\bmola (ekran|pencere)\w*", t) and re.search(r"\b(aç|getir|göster)\w*|\bbaşlat\w*", t) and not n:
        return tools.MOLA_HOOK("open")
    if re.search(r"\b(ver|başlat|kur|yap|gir|istiyorum|çıkıyorum)\w*|\bmolaya\b", t):
        return tools.MOLA_HOOK("start", n)
    return None


def route_mebi(t: str):
    """MEBİ penceresi: 'MEBİ'yi aç', 'kaldığımız yerden devam et', 'bu konuyu bitir', 'MEBİ'de neler yaptım', 'MEBİ'yi kapat'."""
    has = re.search(r"\bmebi\w*", t)
    resume = re.search(r"\b(kaldığ\w* yerden|nerede kalmıştık|(bu )?konuyu bitir\w*)", t)
    quiz = re.search(r"\bkonu(dan|yu)\b.*\b(soru|quiz|test)\b|\b(soru sor|test et|quiz)\b.*\bkonu", t) or (has and re.search(r"\b(soru sor|test et|quiz)\w*", t))
    if not has and not resume and not quiz:
        return None
    import tools
    if not has:                                       # 'mebi' denmediyse yalnızca MEBİ'de kayıtlı bir konu varsa bizimle ilgilidir
        import mebi
        if not mebi.last_topic()[0]:
            return None
    if tools.MEBI_HOOK is None:
        return "MEBİ şu an kullanılamıyor efendim."
    if quiz:
        return tools.MEBI_HOOK("quiz")
    if has and re.search(r"\b(kapat|kapa|bitir|çık)\w*", t) and not resume:
        return tools.MEBI_HOOK("close")
    if re.search(r"\b(durum\w*|ne yaptım|neler yaptım|ne kadar kaldı|ne kaldı|neler kaldı)\b", t):
        return tools.MEBI_HOOK("status")
    if resume:
        return tools.MEBI_HOOK("resume")
    if re.search(r"\b(aç|açar mısın|başlat|getir|git|gir)\w*", t):
        return tools.MEBI_HOOK("open")
    return None


def route_vpn(t: str, raw: str = ""):
    """VPN: aç / kapat / durum / test / ülke seç (scenes_vpn.command). Mod penceresi için route_scene'e bakın."""
    import scenes_vpn
    r = scenes_vpn.command(t, raw)
    return r["say"] if r else None


_BROWSER_NAV = (
    ("back", re.compile(r"(sayfada |sayfayı )?(geri|geriye)( git\w*| dön\w*| gel\w*)?|(bir )?önceki sayfa(ya)?( git\w*| dön\w*| geç\w*)?|geri tuşuna bas\w*")),
    ("forward", re.compile(r"(sayfada )?(ileri|ileriye)( git\w*| dön\w*| gel\w*)?|(bir )?sonraki sayfa(ya)?( git\w*| geç\w*)?|ileri tuşuna bas\w*")),
    ("reload", re.compile(r"(sayfayı )?(yenile|tazele)\w*|sayfayı yeniden yükle\w*")),
    ("home", re.compile(r"ana sayfa(ya)?( git\w*| dön\w*| aç\w*)?|google ana sayfa\w*")),
)
_NAV_SAY = {"back": "Geri gittim efendim.", "forward": "İleri gittim efendim.", "reload": "Sayfayı yeniledim efendim.", "home": "Ana sayfaya gittim efendim."}


def _front_title() -> str:
    """Şu an en öndeki pencerenin başlığı (hangi tarayıcıya geri/ileri denildiğini ayırt etmek için)."""
    try:
        import ctypes
        u = ctypes.windll.user32
        buf = ctypes.create_unicode_buffer(200)
        u.GetWindowTextW(u.GetForegroundWindow(), buf, 200)
        return buf.value
    except Exception:
        return ""


def _browser_nav(t: str):
    """'geriye dön', 'ileri git', 'önceki sayfa', 'sayfayı yenile', 'ana sayfa': Jarvis tarayıcısı ya da MEBİ penceresi açıksa ona uygulanır.
    İkisi de açıksa en öndeki olan seçilir (öndeki yoksa Jarvis tarayıcısı). Hiçbiri açık değilse None (komut başka yola düşer)."""
    nav = next((k for k, rx in _BROWSER_NAV if rx.fullmatch(t)), None)
    if not nav:
        return None
    import jbrowser, tools
    jb = jbrowser.alive()
    mb = bool(tools.MEBI_HOOK and tools.MEBI_HOOK("is_open"))
    if not jb and not mb:
        return None
    if mb and (not jb or "MEBİ" in _front_title()):
        return tools.MEBI_HOOK("nav_" + nav)
    if nav == "home":
        jbrowser.open_start()
    else:
        jbrowser.cmd(nav)
    return _NAV_SAY[nav]


def route_browser(t: str):
    """Jarvis tarayıcısı: 'tarayıcıyı kapat', geri / ileri / yenile / kaydır (yalnızca pencere açıkken), 'jarvis tarayıcısını aç', siteleri nerede açacağı."""
    import jbrowser, settings
    if re.search(r"\b(siteleri|sayfaları|youtube)\b.*\b(chrome|edge|varsayılan tarayıcı\w*|normal tarayıcı\w*)\b.*\b(aç|açsın)\w*", t):
        settings.set("kendi_tarayici", False)
        return "Tamam efendim, siteleri bundan sonra varsayılan tarayıcınızda açacağım."
    if re.search(r"\b(siteleri|sayfaları|youtube)\b.*\bjarvis tarayıcı\w*\b.*\b(aç|açsın)\w*", t):
        settings.set("kendi_tarayici", True)
        return "Tamam efendim, siteleri bundan sonra Jarvis tarayıcısında açacağım."
    if re.fullmatch(r"(jarvis tarayıcı\w*|kendi tarayıcın\w*|kendi tarayıcını)\s*(aç|başlat|göster)\w*", t):
        return "Jarvis tarayıcısı açıldı efendim." if jbrowser.open_start() else None
    if re.fullmatch(r"(jarvis tarayıcısında |tarayıcıda )?(yeni sekme|sekme)\s*(aç|açar mısın|ekle)\w*", t):
        return "Yeni sekmeyi açtım efendim." if jbrowser.new_tab() else None
    if re.fullmatch(r"(jarvis tarayıcısında |tarayıcıda )?(reklam engelleyici\w*|reklamları engelle\w*|reklam engelleme\w*)\s*(aç|açar mısın|başlat|etkinleştir)\w*", t):
        jbrowser.set_adblock(True)
        return "Reklam engelleyiciyi açtım efendim."
    if re.fullmatch(r"(jarvis tarayıcısında |tarayıcıda )?(reklam engelleyici\w*|reklam engelleme\w*)\s*(kapat|kapa|durdur|devre dışı bırak)\w*", t):
        jbrowser.set_adblock(False)
        return "Reklam engelleyiciyi kapattım efendim. Sayfayı yenilemeniz yeterli."
    import jb_theme
    if re.search(r"\btarayıcı\w*\b.*\b(tema|renk)\w*|\b(tema|renk)\w*\b.*\btarayıcı\w*", t):
        th = jb_theme.theme_from_text(t)
        if th:
            jbrowser.set_look(tema=th)
            return f"Tarayıcı temasını {jb_theme.THEMES[th][3]} yaptım efendim."
        return "Temalar: GX kırmızısı, mor, mavi, camgöbeği, yeşil, turuncu ve pembe efendim."
    if re.search(r"\btarayıcı\w*\b.*\bses\w*\b.*\b(aç|kapat|kapa)\w*|\b(tuş|yazma|tıklama)\s+ses\w*.*\b(aç|kapat|kapa)\w*", t):
        on = bool(re.search(r"\baç\w*", t))
        jbrowser.set_look(ses=on)
        return "Tuş ve tıklama seslerini açtım efendim." if on else "Tuş ve tıklama seslerini kapattım efendim."
    nav = _browser_nav(t)
    if nav:
        return nav
    if not jbrowser.alive():
        return None
    if re.fullmatch(r"(bu |şu )?sekmeyi (kapat|kapa)\w*", t):
        jbrowser.cmd("closetab")
        return "Sekmeyi kapattım efendim."
    if re.fullmatch(r"(sonraki|diğer|sıradaki) sekme(ye)?( geç| git)?", t):
        jbrowser.cmd("nexttab")
        return "Sonraki sekmeye geçtim efendim."
    if re.fullmatch(r"(önceki|geçen) sekme(ye)?( geç| git)?", t):
        jbrowser.cmd("prevtab")
        return "Önceki sekmeye geçtim efendim."
    if re.fullmatch(r"(jarvis )?(tarayıcıyı|tarayıcı|jarvis tarayıcısını|pencereyi) (kapat|kapa|bitir)\w*", t):
        jbrowser.close()
        return "Jarvis tarayıcısını kapattım efendim."
    if re.fullmatch(r"(sayfayı )?(aşağı kaydır|aşağı in|aşağı git)", t):
        jbrowser.cmd("scroll", dy=700)
        return "Kaydırdım efendim."
    if re.fullmatch(r"(sayfayı )?(yukarı kaydır|yukarı çık|yukarı git)", t):
        jbrowser.cmd("scroll", dy=-700)
        return "Kaydırdım efendim."
    if re.fullmatch(r"(tarayıcıyı )?tam ekran( yap)?", t):
        jbrowser.cmd("fullscreen")
        return "Tam ekranı değiştirdim efendim."
    return None


def route_eye(t: str):
    """Göz molası: aç / kapat / ertele / şimdi / durum / 'her 90 dakikada' / '3 dakika olsun' (eyecare.py)."""
    import eyecare
    return eyecare.route(t)


def route(t: str, raw: str = ""):
    """Sırayla dener; None = bu modülün komutu değil."""
    tn = _norm_num(raw) if raw else t
    for fn in (route_remote, route_mirror, route_mola, route_mebi, route_guide, route_notes, route_rapor_reminder, route_eye, route_scene, route_vpn, route_browser, route_illusion, route_hero, route_site, route_code, route_study_off, route_schedule, route_agenda, route_city, route_weather, route_screen, route_convert, route_calc):
        try:
            r = route_agenda(t, raw) if fn is route_agenda else route_notes(t, raw) if fn is route_notes else fn(tn if fn in (route_convert, route_calc) else t)
        except Exception as e:
            print("extras hatası:", fn.__name__, e, flush=True)
            r = None
        if r:
            return r
    return None
