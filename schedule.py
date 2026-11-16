"""Ders programı (örnek). Bugünün/yarının derslerini, sıradaki dersi söyler."""
import datetime, re

GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
SAATLER = [("08:20", "09:00"), ("09:10", "09:50"), ("10:00", "10:40"), ("10:50", "11:30"),
           ("11:40", "12:20"), ("13:10", "13:50"), ("14:00", "14:40"), ("14:50", "15:30")]
ORD = ["birinci", "ikinci", "üçüncü", "dördüncü", "beşinci", "altıncı", "yedinci", "sekizinci"]

# kod -> (ders adı, öğretmen)   (örnek program; kendi dersinize göre düzenleyin)
DERS = {"MAT": ("Matematik", "Matematik öğretmeni"), "FİZ": ("Fizik", "Fizik öğretmeni"), "KİM": ("Kimya", "Kimya öğretmeni"),
        "BIO": ("Biyoloji", "Biyoloji öğretmeni"), "TDIE": ("Türk Dili ve Edebiyatı", "Edebiyat öğretmeni"),
        "İNG": ("Yabancı Dil", "İngilizce öğretmeni"), "TAR": ("Tarih", "Tarih öğretmeni"), "COĞ": ("Coğrafya", "Coğrafya öğretmeni")}
PROGRAM = [  # Pazartesi..Cuma, 8 ders
    ["MAT", "MAT", "FİZ", "FİZ", "TDIE", "TDIE", "İNG", "İNG"],
    ["KİM", "KİM", "MAT", "MAT", "TAR", "TAR", "COĞ", "COĞ"],
    ["BIO", "BIO", "TDIE", "TDIE", "FİZ", "FİZ", "İNG", "İNG"],
    ["MAT", "MAT", "KİM", "KİM", "TAR", "TAR", "COĞ", "COĞ"],
    ["TDIE", "TDIE", "BIO", "BIO", "MAT", "MAT", "FİZ", "FİZ"],
]
ALIAS = {"matematik": "MAT", "mat": "MAT", "fizik": "FİZ", "kimya": "KİM", "biyoloji": "BIO", "coğrafya": "COĞ", "tarih": "TAR",
         "edebiyat": "TDIE", "türkçe": "TDIE", "türk dili": "TDIE", "ingilizce": "İNG", "yabancı dil": "İNG"}


def cap(x: str) -> str:
    """Türkçe baş harf büyütme (i -> İ)."""
    return ("İ" if x[:1] == "i" else x[:1].upper()) + x[1:] if x else x


def _ordl(idx):
    return [ORD[i] for i in idx]


def _join(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " ve " + items[-1]


def day_lessons(wd: int):
    """[(ders no 0-7, kod)] ya da hafta sonu için None."""
    return list(enumerate(PROGRAM[wd])) if 0 <= wd <= 4 else None


def say_day(wd: int, label: str) -> str:
    les = day_lessons(wd)
    if les is None:
        nxt = PROGRAM[0]
        return f"{_head(wd, label)}, ders yok efendim, hafta sonu. Pazartesi derslerinizi söyleyeyim. " + _say_groups(0)
    return f"{_head(wd, label)}. {len(les)} dersiniz var. " + _say_groups(wd)


def _head(wd: int, label: str) -> str:
    return f"{cap(label)} {GUNLER[wd]}" if label in ("bugün", "yarın", "öbür gün") else f"{GUNLER[wd]} günü"


def _say_groups(wd: int) -> str:
    groups = []
    for i, code in enumerate(PROGRAM[wd]):
        if groups and groups[-1][0] == code:
            groups[-1][1].append(i)
        else:
            groups.append([code, [i]])
    parts = []
    for code, idx in groups:
        name = DERS[code][0]
        parts.append(f"{_join(_ordl(idx))} ders {name}, saat {SAATLER[idx[0]][0]}")
    return ". ".join(cap(p) for p in parts) + f". Okul {SAATLER[-1][1]}'de bitiyor efendim."


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def now_status(now=None) -> str:
    now = now or datetime.datetime.now()
    wd = now.weekday()
    if wd > 4:
        return "Bugün hafta sonu, ders yok efendim."
    cur = now.hour * 60 + now.minute
    for i, (a, b) in enumerate(SAATLER):
        if _mins(a) <= cur < _mins(b):
            code = PROGRAM[wd][i]
            nxt = f" Sonraki ders {DERS[PROGRAM[wd][i + 1]][0]}." if i + 1 < 8 and PROGRAM[wd][i + 1] != code else ""
            return f"Şu an {ORD[i]} dersteyiz: {DERS[code][0]}, öğretmeniniz {DERS[code][1]}. Ders {b}'de bitiyor.{nxt}"
        if cur < _mins(a):
            code = PROGRAM[wd][i]
            if i == 0:
                return f"Ders henüz başlamadı efendim. İlk dersiniz {DERS[code][0]}, saat {a}'da."
            return f"Şu an teneffüstesiniz efendim. Sıradaki ders {DERS[code][0]}, saat {a}'da."
    return "Bugünkü dersleriniz bitti efendim."


def next_lesson(now=None) -> str:
    now = now or datetime.datetime.now()
    wd, cur = now.weekday(), now.hour * 60 + now.minute
    if wd <= 4:
        for i, (a, b) in enumerate(SAATLER):
            if cur < _mins(a):
                return f"Sıradaki ders {DERS[PROGRAM[wd][i]][0]}, saat {a}'da efendim."
    nd = (wd + 1) % 7
    d = 1
    while nd > 4:
        nd, d = (nd + 1) % 7, d + 1
    return f"Bugünkü dersler bitti. Sıradaki ders {GUNLER[nd]} günü {DERS[PROGRAM[nd][0]][0]}, saat {SAATLER[0][0]}'da efendim."


def when_subject(code: str, now=None) -> str:
    now = now or datetime.datetime.now()
    name = DERS[code][0]
    days = [(d, [i for i, c in enumerate(PROGRAM[d]) if c == code]) for d in range(5)]
    days = [(d, ix) for d, ix in days if ix]
    if not days:
        return f"{name} dersiniz programda yok efendim."
    txt = ", ".join(f"{GUNLER[d]} {_join(_ordl(ix))} ders, saat {SAATLER[ix[0]][0]}" for d, ix in days)
    total = sum(len(ix) for _, ix in days)
    return f"{name} haftada {total} saat efendim: {txt}."


def teacher(code: str) -> str:
    return f"{DERS[code][0]} öğretmeniniz {DERS[code][1]} efendim."


def find_subject(t: str):
    for k in sorted(ALIAS, key=len, reverse=True):
        if re.search(rf"\b{k}\w*", t):
            return ALIAS[k]
    return None


_DAYS = {"pazartesi": 0, "salı": 1, "çarşamba": 2, "perşembe": 3, "cuma": 4, "cumartesi": 5, "pazar": 6}


def route(t: str, now=None):
    now = now or datetime.datetime.now()
    if re.search(r"\b(mod\w*|çalışma|çalış\w*|müzik\w*|müziği|saati|çal\w*|zamanı)\b", t) and not re.search(r"hangi|program", t):
        return None
    if not re.search(r"\bders\w*|\bprogram\w*|öğretmen\w*|\bhoca\w*|okul|teneffüs|\bsıradaki\b", t) \
            and not (find_subject(t) and re.search(r"ne zaman|hangi gün\w*|kaçta|kaç saat", t)):
        return None
    if re.search(r"hangi derste|şu an hangi ders|şimdi hangi ders|şu an ders|şimdi ders|derste miyiz|ders var mı şu", t):
        return now_status(now)
    if re.search(r"sıradaki ders|bir sonraki ders|sonraki ders|sıradaki", t) and not re.search(r"şarkı|müzik", t):
        return next_lesson(now)
    if re.search(r"okul (kaçta|ne zaman) (biter|bitiyor|çıkıyoruz)|dersler (kaçta|ne zaman) (biter|bitiyor)|son ders (kaçta|ne zaman|saat)", t):
        return f"Okul her gün {SAATLER[-1][1]}'de bitiyor efendim."
    if re.search(r"okul (kaçta|ne zaman) (başlar|başlıyor)|ilk ders (kaçta|ne zaman|saat)|dersler (kaçta|ne zaman) (başlar|başlıyor)", t):
        return f"Okul {SAATLER[0][0]}'de başlıyor efendim."
    sub = find_subject(t)
    if sub and re.search(r"öğretmen\w*|hoca\w*", t):
        return teacher(sub)
    if sub and re.search(r"ne zaman|hangi gün\w*|kaçta|kaç saat|kaç gün|var mı", t):
        return when_subject(sub, now)
    wd, label = None, None
    if re.search(r"\byarın\w*", t):
        wd, label = (now.weekday() + 1) % 7, "yarın"
    elif re.search(r"\b(öbür gün|ertesi gün)\w*", t):
        wd, label = (now.weekday() + 2) % 7, "öbür gün"
    else:
        for name, i in sorted(_DAYS.items(), key=lambda kv: -len(kv[0])):
            if re.search(rf"\b{name}\w*", t):
                wd, label = i, name
                break
    if wd is None:
        wd, label = now.weekday(), "bugün"
    if re.search(r"kaç (dersim|ders)\w*|ders sayı\w*", t):
        les = day_lessons(wd)
        return (f"{_head(wd, label)} ders yok efendim." if les is None else f"{_head(wd, label)} {len(les)} dersiniz var efendim.")
    if re.search(r"hangi (ders|derslerim|dersler)\w*|ders\w* (ne|neler|ne var)|derslerim|dersim|ders program\w*|program\w*|ders var", t):
        return say_day(wd, label)
    return None
