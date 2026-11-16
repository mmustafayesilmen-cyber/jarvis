"""Elektronik Laboratuvarı (kind 'elektronik'): 3B ortamda devre kartı (PCB) tasarımı. Sayfa ui/scene_elektronik.html (three.js, modes.js) parçaları yerleştirir ve
tel çeker; bu modül parça bilgisini verir, Türkçe komutları anlar (ekle/sil/bağla/kontrol/simülasyon/kod/hesap...) ve kartları kaydeder.
Çözümleme motoru elektronik_analiz.py, katalog elektronik_data.py. Her işlev (text, state) -> {"say", "do"}; sayfaya giden işlemler do["op"] ile.
Sayfadan gelen '§' ile başlayan komutlar sesli değildir (say ''): §kart|<json> §ac|ad §silkart|ad §sablon|id §bilgi|parça."""
import datetime
import json
import math
import os
import random
import re
import threading

import scenes
import elektronik_analiz as an
import elektronik_bloklar as bl
from elektronik_data import PARTS, KATS, SABLONLAR, ALIAS, E12, fmt_ohm

try:
    from rapidfuzz import fuzz
except ImportError:                                # rapidfuzz yoksa difflib
    import difflib

    class fuzz:                                    # noqa: N801
        @staticmethod
        def ratio(a, b):
            return difflib.SequenceMatcher(None, a, b).ratio() * 100

HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(HERE, "elektronik_kartlar.json")
_lk = threading.Lock()
PENDING: dict = {}          # extras: mod açılırken söylenen şablon komutu ("trafik lambası devresini kur") mod açılınca kurulur
E = {"kart": None, "sab": None, "plan": [], "mcu": "uno", "mcu_acik": False, "ipucu": None, "ipucu_ad": "", "gen": 0}       # oturum durumu (RAM): açık kart, son kurulan şablon ve adımı
RENKLER = {"yesil": "yesil", "mavi": "mavi", "kirmizi": "kirmizi", "siyah": "siyah", "mor": "mor", "beyaz": "beyaz", "sari": "sari"}
LED_RENK = {"kirmizi": "kirmizi", "yesil": "yesil", "mavi": "mavi", "sari": "sari", "beyaz": "beyaz", "turuncu": "turuncu"}
_TR = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u", "µ": "u", "Ω": " ohm "})
_NUM = {"bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5, "alti": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10}


def fold(text: str) -> str:
    """Küçük harf, Türkçe harfler ASCII, ek ('R1'i) atılır; ASR hatalarına dayanıklı eşleştirme için."""
    t = str(text).replace("İ", "i").replace("I", "ı").lower().translate(_TR)
    t = re.sub(r"['’`]\w*", "", t)
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)
    t = re.sub(r"[^a-z0-9.+\s]", " ", t)
    t = re.sub(r"(?<![0-9])\.|\.(?![0-9])", " ", t)
    return " ".join(t.split())


# ============================================================ kayıt (atomik)
def _load():
    try:
        with open(FILE, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("kartlar"), dict):
            return d
    except (OSError, ValueError):
        pass
    return {"kartlar": {}, "son": ""}


def _save(d):
    with _lk:
        with open(FILE + ".tmp", "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(FILE + ".tmp", FILE)


def _clean(k):
    """Sayfadan gelen kartı doğrular (boyut sınırları, geçerli parça kimlikleri)."""
    if not isinstance(k, dict):
        return None
    try:
        w, h = int(k.get("w") or 40), int(k.get("h") or 28)
    except (TypeError, ValueError):
        w, h = 40, 28
    out = {"ad": str(k.get("ad") or "")[:40], "w": max(10, min(80, w)), "h": max(10, min(80, h)),
           "renk": k.get("renk") if k.get("renk") in RENKLER else "yesil", "parcalar": [], "teller": []}
    ip = k.get("ipucu")
    if isinstance(ip, dict) and isinstance(ip.get("esik"), (int, float)) and ip.get("olcu") in ("temp", "cm", "hum") and ip.get("yon") in (">", "<"):
        out["ipucu"] = {"esik": float(ip["esik"]), "olcu": ip["olcu"], "yon": ip["yon"]}          # blok kurucudan gelen eşik (kod üretimi)
    for p in (k.get("parcalar") or [])[:400]:
        if isinstance(p, dict) and p.get("p") in PARTS and p.get("i"):
            out["parcalar"].append(p)
    ids = {p["i"] for p in out["parcalar"]}
    for t in (k.get("teller") or [])[:1500]:
        try:
            if t["a"][0] in ids and t["b"][0] in ids:
                out["teller"].append(t)
        except (KeyError, TypeError, IndexError):
            continue
    return out


def _names():
    return sorted(_load()["kartlar"])


def _find_saved(name):
    d = _load()["kartlar"]
    f = fold(name)
    for k in d:
        if fold(k) == f:
            return k
    best = max(d, key=lambda k: fuzz.ratio(fold(k), f), default=None)
    return best if best and fuzz.ratio(fold(best), f) >= 78 else None


# ============================================================ parça adı çözümü
_ALIASF = sorted(((fold(a), pid) for pid, al in ALIAS.items() for a in al), key=lambda x: -len(x[0]))
_STOP = {"ve", "ile", "bir", "bu", "su", "o", "icin", "de", "da", "ki", "mi", "mu"}
_RENK_KW = {"kirmizi": "kirmizi", "yesil": "yesil", "mavi": "mavi", "sari": "sari", "beyaz": "beyaz", "turuncu": "turuncu"}
_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(kilo|mega|meg|k|m|u|n|p)?\s*(ohm|volt|v|amper|ah|a|farad|f|hz)?(?![a-z0-9])")


def extract(t):
    """Birimli değerleri çıkarır: {'ohm':[..], 'farad':[..], 'volt':[..], 'amp':[..], 'mah':[..], 'hz':[..]} ve değerler silinmiş metin."""
    out = {"ohm": [], "farad": [], "volt": [], "amp": [], "mah": [], "hz": []}
    t = re.sub(r"mikro ?farad\w*", "uf", t)
    t = re.sub(r"nano ?farad\w*", "nf", t)
    t = re.sub(r"piko ?farad\w*", "pf", t)
    t = re.sub(r"mili ?amper\w*", "ma", t)
    t = re.sub(r"kilo ?hertz\w*", "khz", t)
    spans = []
    for m in _UNIT.finditer(t):
        n = float(m.group(1))
        pre, unit = m.group(2), m.group(3)
        if not pre and not unit:
            continue
        mult = {"kilo": 1e3, "k": 1e3, "mega": 1e6, "meg": 1e6}.get(pre or "", None)
        if unit == "ohm" or (not unit and pre in ("kilo", "k", "mega", "meg")):
            out["ohm"].append(n * (mult or (1e6 if pre == "m" else 1)))
        elif unit in ("f", "farad") or (not unit and pre in ("u", "n", "p")):
            if pre in ("u", "n", "p", None, "m"):
                out["farad"].append(n * {"u": 1e-6, "n": 1e-9, "p": 1e-12, "m": 1e-3, None: 1.0}[pre])
            else:
                continue
        elif unit in ("v", "volt") and pre in (None, "m"):
            out["volt"].append(n * (1e-3 if pre == "m" else 1))
        elif unit == "ah":
            out["mah"].append(n * (1 if pre == "m" else 1000))
        elif unit in ("a", "amper") and pre in (None, "m"):
            out["amp"].append(n * (1e-3 if pre == "m" else 1))
        elif unit == "hz":
            out["hz"].append(n * {"k": 1e3, "kilo": 1e3}.get(pre or "", 1))
        else:
            continue
        spans.append((m.start(), m.end()))
    s = t
    for a, b in reversed(spans):
        s = s[:a] + " " + s[b:]
    return out, " ".join(s.split())


def find_parts(t, fuzzy=False):
    """Metindeki parça adları (konum sırasıyla): [(parça id, başlangıç, bitiş)]; uzun takma ad önce tüketilir."""
    used, found = [], []
    for al, pid in _ALIASF:
        for m in re.finditer(r"(?<![a-z0-9])" + re.escape(al) + r"[a-z]{0,6}(?![0-9a-z])" if len(al) > 3 else r"(?<![a-z0-9])" + re.escape(al) + r"(?:[a-z]{0,2})(?![0-9a-z])", t):
            if any(not (m.end() <= a or m.start() >= b) for a, b in used):
                continue
            used.append((m.start(), m.end()))
            found.append((pid, m.start(), m.end()))
    if not found and fuzzy:
        toks = t.split()
        pos, best = 0, None
        for n in (3, 2, 1):
            for k in range(len(toks) - n + 1):
                g = " ".join(toks[k:k + n])
                if len(g) < 5 or g in _STOP:
                    continue
                for al, pid in _ALIASF:
                    if len(al) >= 5 and fuzz.ratio(g, al) >= 86 and (best is None or fuzz.ratio(g, al) > best[0]):
                        best = (fuzz.ratio(g, al), pid)
        if best:
            found.append((best[1], 0, 0))
    return sorted(found, key=lambda x: x[1])


def _nearest(part, kind, value):
    """Parçanın değer listesinden (logaritmik) en yakın değer."""
    lst = part.get("degerler") or []
    conv = {"ohm": an.parse_ohm, "farad": an.parse_cap, "volt": an.num}[kind]
    c = [(abs(math.log(max(conv(x), 1e-15) / max(value, 1e-15))), x) for x in lst if conv(x)]
    return min(c)[1] if c else None


def _count_before(toks_before):
    """'3 tane', 'üç', '5 adet' gibi ifadeyi (renk sözcükleri atlanarak) okur."""
    tk = [x for x in toks_before if x not in _RENK_KW]
    if tk and tk[-1] in ("tane", "adet", "ad"):
        tk = tk[:-1]
        if tk and (tk[-1].isdigit() or tk[-1] in _NUM):
            return int(tk[-1]) if tk[-1].isdigit() else _NUM[tk[-1]]
        return None
    if tk and (tk[-1].isdigit() or tk[-1] in _NUM):
        n = int(tk[-1]) if tk[-1].isdigit() else _NUM[tk[-1]]
        return n if n <= 20 else None
    return None


def parse_add(t0):
    """'üç tane 220 ohm direnç ekle' -> [{p, n, deger?, renk?}]"""
    vals, t = extract(t0)
    parts = find_parts(t, fuzzy=True)
    out = []
    for pid, s, e in parts:
        pre = t[:s].split()
        d = {"p": pid, "n": 1}
        n = _count_before(pre)
        if n:
            d["n"] = max(1, min(n, 12))
        for w in pre[-3:]:
            if w in _RENK_KW:
                d["renk"] = _RENK_KW[w]
        part = PARTS[pid]
        if pid == "kondansator_seramik" and vals["farad"] and vals["farad"][0] > 1.2e-6:
            pid = d["p"] = "kondansator_elektrolitik"
            part = PARTS[pid]
        if part.get("degerler"):
            if vals["ohm"] and pid in ("direnc", "potansiyometre", "trimpot", "termistor"):
                d["deger"] = _nearest(part, "ohm", vals["ohm"].pop(0))
            elif vals["farad"] and pid.startswith("kondansator"):
                d["deger"] = _nearest(part, "farad", vals["farad"].pop(0))
            elif vals["volt"] and pid in ("zener", "dc_jak", "lm2596", "pil_aa"):
                d["deger"] = _nearest(part, "volt", vals["volt"].pop(0))
            if not d.get("deger"):
                d.pop("deger", None)
        if not part.get("renkler"):
            d.pop("renk", None)
        out.append(d)
    return out


# ============================================================ hesaplayıcılar
_RC = {"siyah": 0, "kahverengi": 1, "kahve": 1, "kirmizi": 2, "turuncu": 3, "sari": 4, "yesil": 5, "mavi": 6, "mor": 7, "gri": 8, "beyaz": 9}
_RC_AD = ["siyah", "kahverengi", "kırmızı", "turuncu", "sarı", "yeşil", "mavi", "mor", "gri", "beyaz"]
_TOL = {"altin": 5, "gumus": 10}


def _fmt(v, unit, digs=3):
    return f"{v:.{digs}g} {unit}"


def _eng(v, unit):
    for lim, pre in ((1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "µ"), (1e-9, "n"), (1e-12, "p")):
        if abs(v) >= lim * 0.9999:
            return f"{v / lim:.3g} {pre}{unit}"
    return f"{v:.3g} {unit}"


def _hesap(baslik, rows, say, aciklama=""):
    return {"say": say, "do": {"op": "hesap", "baslik": baslik, "satirlar": rows, "aciklama": aciklama}}


def calc(t, raw):
    vals, rest = extract(t)
    # --- LED ön direnci
    if re.search(r"\bled\b", t) and re.search(r"direnc", t):
        vs = vals["volt"][0] if vals["volt"] else 5.0
        col = next((LED_RENK[w] for w in t.split() if w in LED_RENK), "kirmizi")
        ma = (vals["amp"][0] * 1000) if vals["amp"] else 20.0
        vf = an.VF[col]
        if vs <= vf + 0.1:
            return {"say": f"{vs:g} volt, {col.replace('kirmizi', 'kırmızı')} LED'i yakmaya yetmez efendim; LED ileri gerilimi yaklaşık {vf:g} volt."}
        r = (vs - vf) / (ma / 1000)
        rs = an.e12_up(r)
        i = (vs - vf) / rs * 1000
        p = (i / 1000) ** 2 * rs * 1000
        return _hesap("LED ön direnci", [["Kaynak gerilimi", f"{vs:g} V"], ["LED rengi / Vf", f"{col} / {vf:g} V"], ["Hedef akım", f"{ma:g} mA"], ["Hesaplanan direnç", _eng(r, 'Ω')],
                                         ["Seçilen E12 değeri", fmt_ohm(rs)], ["Gerçek akım", f"{i:.1f} mA"], ["Direnç gücü", f"{p:.0f} mW (1/4 W yeterli)" if p < 200 else f"{p:.0f} mW (1/2 W kullan)"]],
                      f"{vs:g} volt ve {col.replace('kirmizi', 'kırmızı')} LED için {fmt_ohm(rs)} direnç kullanın efendim; akım yaklaşık {i:.0f} miliamper olur.", "R = (Vkaynak − Vf) / I; ileri akım aşılmasın diye bir sonraki standart (E12) değer seçilir.")
    # --- renk kodu
    if re.search(r"renk", t):
        cols = [w for w in t.split() if w in _RC or w in _TOL]
        if len(cols) >= 3 and not vals["ohm"]:
            d = [_RC[c] for c in cols if c in _RC]
            nd = 3 if len(cols) == 5 else 2
            if len(d) < nd + 1:
                return {"say": "Renkleri sırayla söyleyin efendim; en az üç renk gerekir."}
            mult = d[nd] if len(d) > nd else 0
            val = int("".join(str(x) for x in d[:nd])) * (10 ** mult)
            if len(cols) > len(d) or cols[nd] in _TOL:
                pass
            tol = next((_TOL[c] for c in cols if c in _TOL), 5)
            return _hesap("Renk kodundan değer", [["Renkler", " ".join(cols)], ["Değer", fmt_ohm(val)], ["Tolerans", f"%{tol}"]], f"Bu direnç {fmt_ohm(val)}, tolerans yüzde {tol} efendim.")
        if vals["ohm"]:
            v = vals["ohm"][0]
            if v < 1:
                return {"say": "Direnç değeri bir ohmdan küçük olamaz efendim."}
            e = int(math.floor(math.log10(v)))
            dig = round(v / 10 ** (e - 1))
            if dig >= 100:
                dig //= 10
                e += 1
            m = e - 1
            if m < 0:
                m = -1
            cl = [_RC_AD[dig // 10], _RC_AD[dig % 10], _RC_AD[m] if m >= 0 else "altın", "altın"]
            return _hesap(f"{fmt_ohm(v)} renk kodu", [["1. bant", cl[0]], ["2. bant", cl[1]], ["Çarpan", cl[2]], ["Tolerans", "altın (%5)"]], f"{fmt_ohm(v)} için renkler sırasıyla {cl[0]}, {cl[1]}, {cl[2]}, altın efendim.")
    # --- Ohm kanunu
    if re.search(r"ohm kanun|ohm kanunu", t) or (re.search(r"hesap", t) and sum(1 for k in ("volt", "amp", "ohm") if vals[k]) == 2):
        V = vals["volt"][0] if vals["volt"] else None
        I = vals["amp"][0] if vals["amp"] else None
        R = vals["ohm"][0] if vals["ohm"] else None
        if V is not None and R and I is None:
            I = V / R
        elif V is not None and I and R is None:
            R = V / I
        elif I is not None and R and V is None:
            V = I * R
        else:
            return {"say": "Ohm kanunu için iki değer söyleyin efendim; örneğin 9 volt 330 ohm akım hesapla."}
        P = V * I
        return _hesap("Ohm kanunu", [["Gerilim (V)", _eng(V, "V")], ["Akım (I)", _eng(I, "A")], ["Direnç (R)", _eng(R, "Ω")], ["Güç (P = V×I)", _eng(P, "W")]],
                      f"Gerilim {_eng(V, 'volt')}, akım {_eng(I, 'amper')}, direnç {_eng(R, 'ohm')} efendim.", "V = I × R   |   P = V × I")
    # --- gerilim bölücü
    if re.search(r"bolucu", t):
        if len(vals["ohm"]) >= 2:
            vin = vals["volt"][0] if vals["volt"] else 5.0
            r1, r2 = vals["ohm"][:2]
            vo = vin * r2 / (r1 + r2)
            return _hesap("Gerilim bölücü", [["Giriş", f"{vin:g} V"], ["R1 (üst)", fmt_ohm(r1)], ["R2 (alt)", fmt_ohm(r2)], ["Çıkış", f"{vo:.2f} V"], ["Bölücü akımı", _eng(vin / (r1 + r2), "A")]],
                          f"Çıkış gerilimi {vo:.2f} volt efendim.", "Vout = Vin × R2 / (R1 + R2); çıkışa bağlı yük bu değeri düşürür.")
        return {"say": "Gerilim bölücü için giriş gerilimini ve iki direnci söyleyin efendim; örneğin gerilim bölücü 5 volt 1k 2k."}
    # --- RC zaman sabiti
    if re.search(r"zaman sabit", t):
        if vals["ohm"] and vals["farad"]:
            tau = vals["ohm"][0] * vals["farad"][0]
            return _hesap("RC zaman sabiti", [["R", fmt_ohm(vals["ohm"][0])], ["C", _eng(vals["farad"][0], "F")], ["τ = R×C", _eng(tau, "s")], ["%63 dolum", _eng(tau, "s")], ["%99 dolum (5τ)", _eng(5 * tau, "s")]],
                          f"Zaman sabiti {_eng(tau, 'saniye')}; kondansatör yaklaşık {_eng(5 * tau, 'saniyede')} dolar efendim.", "τ = R × C")
        return {"say": "Direnç ve kondansatör değerini söyleyin efendim; örneğin 10k 100 mikrofarad zaman sabiti."}
    # --- 555 frekansı
    if re.search(r"\b555\b", t) and re.search(r"frekans|hesap", t):
        if len(vals["ohm"]) >= 2 and vals["farad"]:
            r1, r2 = vals["ohm"][:2]
            c = vals["farad"][0]
            f = 1.44 / ((r1 + 2 * r2) * c)
            du = (r1 + r2) / (r1 + 2 * r2) * 100
            return _hesap("555 astable", [["R1", fmt_ohm(r1)], ["R2", fmt_ohm(r2)], ["C", _eng(c, "F")], ["Frekans", _eng(f, "Hz")], ["Periyot", _eng(1 / f, "s")], ["Doluluk oranı", f"%{du:.0f}"]],
                          f"555 yaklaşık {_eng(f, 'hertz')} ile çalışır efendim, doluluk oranı yüzde {du:.0f}.", "f = 1,44 / ((R1 + 2·R2) · C)")
        return {"say": "555 için iki direnci ve kondansatörü söyleyin efendim; örneğin 555 frekans 1k 68k 10 mikrofarad."}
    # --- pil ömrü
    if re.search(r"pil omr|pil kac saat|pilim kac|ne kadar dayan", t) or (vals["mah"] and vals["amp"]):
        if vals["mah"] and vals["amp"]:
            h = vals["mah"][0] / (vals["amp"][0] * 1000)
            return _hesap("Pil ömrü", [["Kapasite", f"{vals['mah'][0]:g} mAh"], ["Akım", f"{vals['amp'][0] * 1000:g} mA"], ["İdeal süre", f"{h:.1f} saat"], ["Gerçekçi (%70)", f"{h * 0.7:.1f} saat ({h * 0.7 / 24:.1f} gün)"]],
                          f"Pil yaklaşık {h * 0.7:.0f} saat dayanır efendim (ideal {h:.0f} saat).", "süre = kapasite (mAh) / akım (mA); pil yaşı ve sıcaklık nedeniyle %70 ile çarpılır.")
        return {"say": "Pil kapasitesini ve akımı söyleyin efendim; örneğin 2000 mAh pil 50 mA akım."}
    # --- seri / paralel
    if re.search(r"seri|paralel", t) and len(vals["ohm"]) + len(re.findall(r"\d+(?:\.\d+)?", rest)) >= 2:
        nums = vals["ohm"] + [float(x) for x in re.findall(r"\d+(?:\.\d+)?", rest)]
        seri = re.search(r"seri", t) and not re.search(r"paralel", t)
        r = sum(nums) if seri else 1 / sum(1 / x for x in nums)
        return _hesap("Seri / paralel direnç", [["Dirençler", " , ".join(fmt_ohm(x) for x in nums)], ["Bağlantı", "seri" if seri else "paralel"], ["Eşdeğer", fmt_ohm(round(r, 2))]],
                      f"{'Seri' if seri else 'Paralel'} eşdeğer direnç {fmt_ohm(round(r, 2))} efendim.", "Seri: R = R1 + R2 …   Paralel: 1/R = 1/R1 + 1/R2 …")
    return None


# ============================================================ bağlama (etiket/pin çözümü)
_PINKW = [("anod", ["A"]), ("anot", ["A"]), ("katod", ["K"]), ("katot", ["K"]), ("toprak", ["GND", "-", "K", "GND2", "GND3"]), ("eksi", ["-", "GND", "K"]), ("negatif", ["-", "GND"]),
          ("arti", ["+", "VCC", "VDD", "5V", "VIN", "3V3"]), ("pozitif", ["+", "VCC"]), ("vcc", ["VCC", "+", "VDD", "VIN"]), ("besleme", ["VCC", "+", "VDD", "VIN"]), ("sinyal", ["SIG", "OUT", "DATA", "S", "AO", "DQ", "IN", "DIN"]),
          ("signal", ["SIG", "OUT", "DATA", "S", "AO"]), ("taban", ["B"]), ("base", ["B"]), ("kolektor", ["C"]), ("emiter", ["E"]), ("emitor", ["E"]), ("kapi", ["G"]), ("gate", ["G"]),
          ("drain", ["D"]), ("savak", ["D"]), ("kaynak", ["S"]), ("source", ["S"]), ("trig", ["TRIG"]), ("echo", ["ECHO"]), ("data", ["DATA", "DS", "DIO", "DIN"]), ("sda", ["SDA"]), ("scl", ["SCL"]),
          ("tx", ["TX"]), ("rx", ["RX"]), ("cikis", ["OUT", "AO", "DO", "SIG"]), ("giris", ["IN", "SIG"]), ("kayar", ["W"]), ("gnd", ["GND", "-", "K"])]
_PINWORDS = {"pin", "pini", "pinini", "bacak", "bacagi", "bacagini", "ucu", "ucunu", "ucuna"}
_RAIL = {"5v": ["5V", "VBUS", "VOUT"], "3v3": ["3V3", "3V3b", "VOUT"], "vin": ["VIN"], "gnd": ["GND", "GND2", "GND3", "-"], "toprak": ["GND", "GND2", "GND3", "-"]}


def _label_map(kart):
    return {fold(p.get("etiket") or ""): p for p in kart.get("parcalar", []) if p.get("etiket")}


def _resolve_label(tok, lm):
    if tok in lm:
        return lm[tok]
    best = None
    for k, p in lm.items():
        if tok.startswith(k) and re.fullmatch(r"[a-z]{1,4}", tok[len(k):]) and (best is None or len(k) > len(best[0])):
            best = (k, p)
    return best[1] if best else None


def _used_pins(kart):
    used = set()
    for t in kart.get("teller", []):
        try:
            used.add(tuple(t["a"]))
            used.add(tuple(t["b"]))
        except (KeyError, TypeError):
            pass
    return used


def bagla(t, raw, kart):
    lm = _label_map(kart)
    insts = {p["i"]: p for p in kart.get("parcalar", [])}
    toks = t.split()
    ents = []
    for n, tok in enumerate(toks):
        nxt = toks[n + 1] if n + 1 < len(toks) else ""
        p = _resolve_label(tok, lm)
        if p:
            ents.append({"p": p, "pin": None, "kw": None})
            continue
        if tok in ("gnd", "toprak") and nxt not in _PINWORDS:
            ents.append({"rail": "gnd"})
            continue
        if tok in ("5v", "3v3", "vin"):
            ents.append({"rail": tok})
            continue
        if tok.isdigit() and ents and ents[-1].get("p") is not None and ents[-1]["kw"] is None and tok in [pn["ad"] for pn in PARTS[ents[-1]["p"]["p"]]["pinler"]]:
            ents[-1]["kw"] = [tok]                      # "R2 2. ucunu ..." gibi numaralı bacak
            continue
        kw = next((c for k, c in _PINKW if tok.startswith(k)), None)
        if kw and ents and ents[-1].get("p") is not None and ents[-1]["kw"] is None:
            ents[-1]["kw"] = kw
            continue
        m = re.fullmatch(r"(d\d{1,2}|a\d{1,2}|g\d{1,2}|gp\d{1,2}|p[bcd]\d)", tok)
        if m:
            ents.append({"mcupin": tok.upper()})
            continue
        part = find_parts(tok)
        if part and part[0][0] and tok not in ("ve", "ile"):
            cands = [q for q in kart.get("parcalar", []) if q["p"] == part[0][0]]
            if len(cands) == 1 and cands[0].get("etiket"):
                ents.append({"p": cands[0], "pin": None, "kw": None})
    if len(ents) < 2:
        return None
    a, b = ents[0], ents[1]
    used = _used_pins(kart)

    def res(e, other):
        if "rail" in e:
            names = _RAIL[e["rail"]]
            pri = [q for q in kart["parcalar"] if PARTS[q["p"]]["kat"] in ("kart", "guc")] + kart["parcalar"]
            for q in pri:
                for pn in PARTS[q["p"]]["pinler"]:
                    if pn["ad"] in names and (e["rail"] != "gnd" or pn["tip"] == "gnd") and q.get("etiket"):
                        return [q["etiket"], pn["ad"]]
            return None
        if "mcupin" in e:
            for q in kart["parcalar"]:
                for pn in PARTS[q["p"]]["pinler"]:
                    if pn["ad"].upper() == e["mcupin"] and q.get("etiket") and PARTS[q["p"]]["kat"] == "kart":
                        return [q["etiket"], pn["ad"]]
            return None
        q = e["p"]
        pins = [pn["ad"] for pn in PARTS[q["p"]]["pinler"]]
        if e["kw"]:
            for c in e["kw"]:
                if c in pins:
                    return [q["etiket"], c]
        free = [pn for pn in pins if (q["i"], pn) not in used]
        if other is not None and e is b and free:
            return [q["etiket"], free[0]]
        return [q["etiket"], (free or pins)[0]]
    ra = res(a, b)
    if ra and "p" in a:
        used.add((a["p"]["i"], ra[1]))
    rb = res(b, a)
    if not ra or not rb:
        return None
    return ra, rb


# ============================================================ ana işleyici
_HELP = ("Elektronik laboratuvarında parça ekleyin: kırmızı LED ekle, üç tane 220 ohm direnç ekle, Arduino Uno ekle. "
         "R1'i LED1'in anoduna bağla, LED1 katodu GND'ye diyerek bağlayın. Devreyi kontrol et, simülasyonu başlat, kodu üret, malzeme listesi ve devreyi anlat var. "
         "Trafik lambası devresini kur gibi hazır devreleri yükleyebilir, sıradaki adım ne diye sorabilirsiniz. Hesaplamak için 9 volt mavi led için direnç hesapla deyin. "
         "İstediğiniz özelliği söyleyip kart kur diyebilirsiniz: sıcaklığı ölçüp ekranda gösteren, 30 derecede fanı açan bir kart kur. Plana LED bloğu ekle, planı kur, planı temizle de var.")
_VIEWS = [("xray", r"rontgen|x ray|xray|saydam|baglantilari goster|izleri goster"), ("patlat", r"patlat|parcala|patlatilmis"), ("ust", r"ustten|ust gorunum|kus bakisi"), ("alt", r"alttan|alt gorunum|lehim tarafi|arka yuz"),
          ("3b", r"\b3b\b|uc boyutlu|3 boyutlu|perspektif|normal gorunum"), ("don", r"dondur|donsun|otomatik don")]


def _kart(st):
    k = st.get("kart") or E.get("kart")
    return k if isinstance(k, dict) else {"ad": "", "w": 40, "h": 28, "renk": "yesil", "parcalar": [], "teller": []}


def _do(say, do=None):
    r = {"say": say}
    if do is not None:
        do = dict(do)
        do.setdefault("msg", say)
        r["do"] = do
    return r


def _sab_bul(t):
    best = None
    for s in SABLONLAR:
        for a in [s["ad"]] + s.get("ad_alt", []):
            fa = fold(a)
            if re.search(r"(?<![a-z0-9])" + re.escape(fa), t) and (best is None or len(fa) > best[0]):
                best = (len(fa), s)
    return best[1] if best else None


def sablon_bul(t):
    return _sab_bul(fold(t))


def _yukle_sablon(s, st):
    k = an.sablon_kart(s)
    E["kart"] = st["kart"] = k
    E["sab"] = {"id": s["id"], "n": 0}
    return _do(f"{s['ad']} devresini kurdum efendim. {s['acik']} Adım adım anlatmamı isterseniz sıradaki adım ne diye sorun.", {"op": "kart", "kart": k})


def _devre(st):
    return an.Devre(_kart(st))


def elektronik(text, st):
    raw = str(text).strip()
    if raw.startswith("§"):
        return _ozel(raw, st)
    t = fold(raw)
    if not t:
        return None
    kart = _kart(st)

    def has(*p):
        return any(re.search(x, t) for x in p)
    if has(r"\byardim\b|\bkomutlar\b|neler yapabilirsin|ne yapabilirim"):
        return {"say": _HELP}
    r = _blok_komut(raw, t, st)
    if r is not None:
        return r
    ekle_v = has(r"\b(ekle|ekleyin|ekler misin|koy|koyun|yerlestir|ilave|getir)\w*")
    sil_v = has(r"\b(sil|silin|kaldir|cikar|at)\b|\bsilsene\b")
    # ---- hesaplayıcılar (ekle/sil içermeyenler)
    if not ekle_v and not sil_v and has(r"hesap|renk kod|ohm kanun|bolucu|zaman sabit|pil omr|pil kac|\bmah\b|seri direnc|paralel direnc|seri paralel|seri bagl.*direnc|555 frekans|\bkac ohm|hangi direnc"):
        r = calc(t, raw)
        if r:
            return r
        if has(r"direnc.*hesap|hesap.*direnc|hangi direnc"):
            return {"say": "Hangi LED ve kaç volt olduğunu söyleyin efendim; örneğin 9 volt mavi led için direnç hesapla."}
    # ---- kontrol / simülasyon / kod / bom / anlat
    if has(r"simulasyon\w*.*(durdur|bitir|kapat|kes)|simule\w*.*(durdur|bitir)|simulasyonu dur|simulasyon dur"):
        return _do("Simülasyonu durdurdum efendim.", {"op": "simdur"})
    if has(r"simulasyon|simule|devreyi calistir|calistir$|enerji ver|devreyi test"):
        if not has(r"kod"):
            return _sim(st)
    if has(r"\bkontrol\b|denetle|hata var mi|hatali mi|sorun var mi|devre dogru mu|devre calisir mi|dogru mu"):
        return _kontrol(st)
    if has(r"\bkod\w*\s+(kaydet|sakla|dosya)|kaydet.*\bkod\b"):
        return _kod(st, kaydet=True)
    if has(r"\bkod\b|\bkodu\b|kodunu|arduino kodu|program yaz|sketch|taslak"):
        return _kod(st, kaydet=False)
    if has(r"malzeme|\bbom\b|parca listesi|alisveris listesi|neler lazim|hangi parcalar lazim"):
        return _bom(st)
    if has(r"devreyi anlat|devre ne yap|devreyi acikla|bu devre ne|devreyi ozetle|devre hakkinda"):
        m = _devre(st).anlat()
        return _do(m, {"op": "anlat", "metin": m})
    # ---- kartlar
    if has(r"kartlari listele|kartlarim|kayitli kart|hangi kartlar|kartlari goster"):
        n = _names()
        return _do(("Kayıtlı kartlarınız: " + ", ".join(n) + ".") if n else "Henüz kayıtlı kartınız yok efendim.", {"op": "kartlar", "kartlar": n})
    if has(r"yeni (kart|devre|proje)|bos kart"):
        k = {"ad": "", "w": 40, "h": 28, "renk": "yesil", "parcalar": [], "teller": []}
        E["kart"] = st["kart"] = k
        E["sab"] = None
        return _do("Yeni boş kart hazır efendim.", {"op": "kart", "kart": k})
    if has(r"kart\w*\s+(temizle|bosalt|sifirla)|hepsini (sil|kaldir)|tumunu (sil|kaldir)|her seyi (sil|kaldir)|temizle$"):
        k = dict(kart, parcalar=[], teller=[])
        E["kart"] = st["kart"] = k
        return _do("Kartı temizledim efendim.", {"op": "sil", "hedef": "hepsi"})
    if has(r"kart\w*\s+kaydet|devreyi kaydet|\bkaydet$|projeyi kaydet"):
        return _kaydet(st)
    m = re.search(r"(.+?)\s+kart\w*\s+(ac|yukle|getir|cagir)\b", t) or re.search(r"\bkart\w*\s+(.+?)\s+(ac|yukle|getir)\b", t)
    if m and not has(r"yeni"):
        name = _find_saved(re.sub(r"\b(kayitli|kaydettigim|benim)\b", "", m.group(1)).strip())
        if not name:
            return {"say": "Böyle bir kayıtlı kart bulamadım efendim. Kartları listele diyebilirsiniz."}
        return _ozel("§ac|" + name, st)
    m = re.search(r"(.+?)\s+kart\w*\s+(sil|kaldir)\b", t)
    if m:
        name = _find_saved(m.group(1))
        if not name:
            return {"say": "Böyle bir kayıtlı kart bulamadım efendim."}
        return _ozel("§silkart|" + name, st)
    m = re.search(r"kart\w*\s+ad\w*\s+(.+?)\s*(?:yap|olsun|koy|degistir|diye)\b", t)
    if m:
        ad = re.sub(r"^(adi|adini)\s+", "", m.group(1)).strip()
        rm = re.search(r"kart\w*\s+ad\w*\s+(.+?)\s*(?:yap|olsun|koy|degistir|diye)\b", raw, re.I)
        ad = (rm.group(1).strip() if rm else ad).strip(" '\"")[:40]
        if ad:
            k = dict(kart, ad=ad)
            E["kart"] = st["kart"] = k
            return _do(f"Kartın adı {ad} oldu efendim.", {"op": "ad", "ad": ad})
    m = re.search(r"kart\w*\s+(?:boyut|olcu)\w*.*?(\d+)\D+(\d+)", t) or re.search(r"(\d+)\s*(?:e|a|ye|ya|x|çarpı|carpi|ile)?\s*(\d+)\s*(?:yap|olsun|boyut)", t)
    if m and has(r"kart|boyut"):
        w, h = max(10, min(80, int(m.group(1)))), max(10, min(80, int(m.group(2))))
        k = dict(kart, w=w, h=h)
        E["kart"] = st["kart"] = k
        return _do(f"Kart boyutu {w} çarpı {h} oldu efendim (birim 2,54 milimetre).", {"op": "boyut", "w": w, "h": h})
    m = re.search(r"\b(yesil|mavi|kirmizi|siyah|mor|beyaz|sari)\b", t)
    if m and has(r"kart\w*") and has(r"\b(yap|olsun|boya|renk\w*|degistir)\b") and not ekle_v:
        c = RENKLER[m.group(1)]
        k = dict(kart, renk=c)
        E["kart"] = st["kart"] = k
        return _do(f"Kart rengi {m.group(1).replace('kirmizi', 'kırmızı').replace('yesil', 'yeşil').replace('sari', 'sarı')} oldu efendim.", {"op": "renk", "renk": c})
    # ---- görünüm
    for v, pat in _VIEWS:
        if has(pat) and has(r"goster|gorunum|bak|ac|yap|dondur|donsun|patlat|rontgen|x ray|xray|uc boyutlu|perspektif|saydam|\b3b\b|ustten|alttan|parcala|normal|don\b"):
            say = {"ust": "Kartı üstten gösteriyorum efendim.", "3b": "Üç boyutlu görünüme döndüm efendim.", "alt": "Kartın alt yüzü, lehim tarafı.", "patlat": "Parçaları patlatılmış görünümde ayırdım efendim.",
                   "xray": "Röntgen görünümü: bağlantı izleri görünür efendim.", "don": "Kartı döndürüyorum efendim."}[v]
            return _do(say, {"op": "gorunum", "v": v})
    # ---- şablonlar / adım adım
    if has(r"sablon\w*|hazir devre\w*|ornek devre\w*|ornekler"):
        if has(r"liste|goster|neler|hangi|var mi|\bsablonlar\b|hazir devreler|ornek devreler") and not _sab_bul(t):
            rows = [[s["ad"], s["acik"]] for s in SABLONLAR]
            return _hesap("Hazır devreler", rows, "Hazır devreler: " + ", ".join(s["ad"] for s in SABLONLAR) + ". Adını söyleyip devresini kur deyin efendim.", "Örnek: 'trafik lambası devresini kur'")
    s = _sab_bul(t)
    if s and not has(r"\b(sil|kaldir)\b"):
        return _yukle_sablon(s, st)
    if has(r"siradaki adim|sonraki adim|adim adim|ilk adim|bir sonraki adim|onceki adim|adimi tekrar|adim ne"):
        return _adim(t)
    if has(r"gunun parca|rastgele parca|surpriz parca|bir parca sec"):
        pid = random.Random(datetime.date.today().toordinal()).choice(sorted(PARTS))
        p = PARTS[pid]
        return _do(f"Günün parçası: {p['ad']}. {p['kisa']}", {"op": "bilgi", "p": pid})
    if has(r"parca oner|oner\w*|tavsiye|ne kullanmaliyim|hangi (parca|sensor)\w* kullan"):
        return _oner(t)
    # ---- bağlama
    if has(r"\bbagla\w*|birlestir\w*|lehimle|\bbaglar misin|\bbaglayin") or (not ekle_v and not sil_v and len(re.findall(r"\b[a-z]{1,4}\d{1,2}\b", t)) >= 1 and has(r"anot|katot|gnd|toprak|5v|3v3|vcc")):
        r = bagla(t, raw, kart)
        if not r:
            return {"say": "Bağlantıyı anlayamadım efendim. Parça etiketiyle söyleyin; örneğin R1'i LED1'in anoduna bağla, LED1 katodu GND'ye ya da buton D2'ye bağla."}
        a, b = r
        return _do(f"{a[0]} {a[1]} ucunu {b[0]} {b[1]} ucuna bağladım efendim.", {"op": "bagla", "a": a, "b": b, "tip": "kablo"})
    # ---- silme
    if sil_v and has(r"kart\w*|devre\w*") and not find_parts(t) and not any(_resolve_label(w, _label_map(kart)) for w in t.split()) and not has(r"secil"):
        return {"say": "Kartı boşaltmak için kartı temizle deyin efendim; kayıtlı bir kartı silmek için adını söyleyip kartını sil deyin."}
    if sil_v:
        if has(r"secil\w*|sectigim|secili"):
            return _do("Seçili parçayı sildim efendim.", {"op": "sil", "hedef": "secili"})
        lm = _label_map(kart)
        for tok in t.split():
            p = _resolve_label(tok, lm)
            if p:
                return _do(f"{p['etiket']} silindi efendim.", {"op": "sil", "hedef": p["etiket"]})
        pr = find_parts(t, fuzzy=True)
        if pr:
            return _do(f"{PARTS[pr[0][0]]['ad']} parçalarını sildim efendim.", {"op": "sil", "hedef": pr[0][0]})
        return {"say": "Hangi parçayı sileceğimi anlayamadım efendim. Etiketiyle söyleyin; örneğin R1'i sil ya da seçileni sil."}
    # ---- bilgi
    pr = find_parts(t, fuzzy=False)
    if pr and (has(r"nedir|ne ise yarar|ne yapar|bacak|pin\w* neler|pinleri|ayak|bilgi|hakkinda|nasil calisir|ne demek|nasil kullan|ozellik|anlat|tanit|nedr") and not ekle_v):
        pid = pr[0][0]
        p = PARTS[pid]
        pins = ", ".join(f"{x['ad']} ({x['acik']})" if x["acik"] else x["ad"] for x in p["pinler"][:8])
        if has(r"bacak|pin|ayak"):
            return _do(f"{p['ad']} bacakları: {pins}. {p['dikkat']}", {"op": "bilgi", "p": pid})
        return _do(f"{p['ad']}: {p['kisa']} {p['bilgi'].split('. ')[0].rstrip('.')}. Dikkat: {p['dikkat']}", {"op": "bilgi", "p": pid})
    # ---- ekleme
    items = parse_add(t)
    if items and (ekle_v or len(t.split()) <= 5):
        it = items[0]
        extra = " ".join(x for x in (it.get("renk", "").replace("kirmizi", "kırmızı").replace("yesil", "yeşil").replace("sari", "sarı"), it.get("deger", "")) if x)
        say = (f"{it['n']} adet " if it["n"] > 1 else "") + (extra + " " if extra else "") + PARTS[it["p"]]["ad"] + " eklendi efendim."
        if len(items) > 1:
            say += " Diğer parçaları da tek tek söyleyin."
        return _do(say, {"op": "ekle", **it})
    if items:
        return {"say": f"{PARTS[items[0]['p']]['ad']} parçasını eklememi ister misiniz efendim? Ekle diyerek söyleyin."}
    return {"say": "Anlayamadım efendim. LED ekle, R1'i LED1'in anoduna bağla, devreyi kontrol et ya da trafik lambası devresini kur diyebilirsiniz."}


# ============================================================ alt komutlar
def _ozel(raw, st, soyle=False):
    cmd, _, arg = raw[1:].partition("|")
    if cmd == "kart":
        try:
            k = _clean(json.loads(arg))
        except (ValueError, TypeError):
            return {"say": ""}
        if k is None:
            return {"say": ""}
        E["kart"] = st["kart"] = k
        if k["ad"] and k["parcalar"]:
            d = _load()
            if d["kartlar"].get(k["ad"]) != k:
                d["kartlar"][k["ad"]] = k
                d["son"] = k["ad"]
                try:
                    _save(d)
                except OSError as e:
                    print("elektronik kayıt hatası:", type(e).__name__, flush=True)
        return {"say": ""}
    if cmd == "ac":
        d = _load()["kartlar"]
        name = arg.strip() if arg.strip() in d else _find_saved(arg)
        if not name:
            return {"say": "Böyle bir kart yok efendim."}
        k = d[name]
        E["kart"] = st["kart"] = k
        E["sab"] = None
        return _do(f"{name} kartı açıldı efendim.", {"op": "kart", "kart": k})
    if cmd == "silkart":
        d = _load()
        name = arg.strip() if arg.strip() in d["kartlar"] else _find_saved(arg)
        if not name:
            return {"say": "Böyle bir kart yok efendim."}
        d["kartlar"].pop(name, None)
        if d.get("son") == name:
            d["son"] = ""
        _save(d)
        return _do(f"{name} kartı silindi efendim.", {"op": "kartlar", "kartlar": sorted(d["kartlar"])})
    if cmd == "sablon":
        s = next((x for x in SABLONLAR if x["id"] == arg.strip()), None)
        return _yukle_sablon(s, st) if s else {"say": ""}
    if cmd == "bilgi":
        pid = arg.strip()
        return {"say": "", "do": {"op": "bilgi", "p": pid}} if pid in PARTS else {"say": ""}
    if cmd == "blok":
        bid, _, js = arg.partition("|")
        try:
            prm = json.loads(js) if js.strip() else {}
        except ValueError:
            prm = {}
        r = _blok_ekle(bid.strip(), prm if isinstance(prm, dict) else {})
        r["say"] = ""
        return r
    if cmd == "blokcikar":
        try:
            n = int(arg.strip())
        except ValueError:
            return {"say": ""}
        if 0 <= n < len(E["plan"]):
            b = bl.BLOKLAR[E["plan"].pop(n)["id"]]
            return {"say": "", "do": _plan_op(False, [], f"{b['ad']} bloğu plandan çıkarıldı.")}
        return {"say": ""}
    if cmd == "plantemizle":
        _plan_sifirla()
        return {"say": "", "do": _plan_op(False, [], "Plan temizlendi.")}
    if cmd == "mcu":
        mid = arg.strip()
        if mid not in bl.MCULAR:
            return {"say": ""}
        E["mcu"], E["mcu_acik"] = mid, True
        return {"say": "", "do": _plan_op(False, [], f"Kart: {bl.MCULAR[mid]['ad']}")}
    if cmd == "kur":
        if not E["plan"]:
            return {"say": "Plan boş efendim. Önce blok ekleyin ya da kart kur diyerek ne istediğinizi söyleyin." if soyle else "", "do": _plan_op(False, ["Plan boş: önce blok ekleyin."], "Plan boş.")}
        try:
            k, notlar = _kur_uygula(st)
        except bl.BlokHata as e:
            return {"say": str(e) if soyle else "", "do": _plan_op(False, [str(e)], str(e))}
        say = _soylenen(k, notlar, [])
        metin = _anlat_metni(notlar)
        threading.Timer(0.35, lambda: _bildir({"op": "anlat", "metin": metin})).start()          # kart işleminden SONRA, bir kez
        return {"say": say if soyle else "", "do": {"op": "kart", "kart": k, "msg": say}}
    return {"say": ""}


def _kaydet(st):
    k = _kart(st)
    if not k["parcalar"]:
        return {"say": "Kart boş efendim, kaydedecek bir şey yok."}
    d = _load()
    if not k.get("ad"):
        n = 1
        while f"Kart {n}" in d["kartlar"]:
            n += 1
        k = dict(k, ad=f"Kart {n}")
        E["kart"] = st["kart"] = k
    d["kartlar"][k["ad"]] = k
    d["son"] = k["ad"]
    _save(d)
    return _do(f"{k['ad']} kartını kaydettim efendim.", {"op": "ad", "ad": k["ad"]})


def _kontrol(st):
    A = _devre(st)
    sor, puan = A.kontrol()
    h = sum(1 for s in sor if s["sev"] == "hata")
    u = sum(1 for s in sor if s["sev"] == "uyari")
    if h or u:
        ilk = next(s for s in sor if s["sev"] == "hata") if h else next(s for s in sor if s["sev"] == "uyari")
        say = f"Devre kontrolü: puan {puan}, {h} hata, {u} uyarı. En önemlisi: {ilk['msg'][:170]}"
    else:
        say = f"Devre kontrolü tamam efendim, puan {puan}. " + (sor[0]["msg"] if sor and sor[0]["sev"] == "bilgi" and len(sor) == 1 else "Büyük bir sorun görmedim.")
    return _do(say, {"op": "kontrol", "sorunlar": sor, "puan": puan})


def _sim(st):
    A = _devre(st)
    r = A.sim()
    if r["yanik"]:
        say = f"Dikkat efendim, {len(r['yanik'])} parça zarar görüyor. {r['not'][0] if r['not'] else ''}"
    else:
        say = f"Simülasyon başladı efendim: {len(r['acik'])} parça sürekli çalışıyor, {len(r['yanip'])} parça kontrollü yanıp sönüyor."
        if not (r["acik"] or r["yanip"]):
            say = "Simülasyon başladı ama çalışan bir parça yok efendim. Önce devreyi kontrol edelim."
    return _do(say, {"op": "sim", **r})


def _ad_dosya(ad):
    return re.sub(r"[^a-z0-9_]+", "_", fold(ad or "kart")).strip("_") or "kart"


def _kod(st, kaydet):
    k = _kart(st)
    if not k.get("ipucu") and E.get("ipucu") and E.get("ipucu_ad") == k.get("ad"):          # sayfa kartı geri yollarken eşiği düşürdüyse RAM'deki ipucu kullanılır
        k = dict(k, ipucu=E["ipucu"])
    kod, neden = an.kod_uret(k)
    if kod is None:
        return {"say": neden}
    ad = _ad_dosya(k.get("ad"))
    do = {"op": "kod", "kod": kod, "baslik": f"{k.get('ad') or 'Kart'} — Arduino taslağı", "dosya": f"{ad}.ino"}
    say = "Arduino taslağını hazırladım efendim, ekranda. Kaydetmek için kodu kaydet deyin."
    if kaydet:
        d = os.path.join(HERE, "workspace", "elektronik", ad)
        try:
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, ad + ".ino")
            with open(p + ".tmp", "w", encoding="utf-8") as f:
                f.write(kod)
            os.replace(p + ".tmp", p)
            do["dosya"] = os.path.relpath(p, HERE).replace("\\", "/")
            say = f"Kodu kaydettim efendim: {do['dosya']}. Arduino IDE ile açabilirsiniz."
        except OSError as e:
            say = f"Kodu kaydedemedim efendim ({type(e).__name__})."
    return _do(say, do)


def _bom(st):
    A = _devre(st)
    rows = A.bom()
    if not rows:
        return {"say": "Kart boş efendim, malzeme listesi yok."}
    toplam = sum(r["adet"] for r in rows)
    return _do(f"Malzeme listesi hazır efendim: {len(rows)} çeşit, toplam {toplam} parça.", {"op": "bom", "satirlar": rows})


def _adim(t):
    s = E.get("sab")
    sab = next((x for x in SABLONLAR if s and x["id"] == s["id"]), None)
    if not sab:
        return {"say": "Önce bir hazır devre kurun efendim; örneğin trafik lambası devresini kur."}
    adim = sab["adim"]
    if re.search(r"onceki", t):
        s["n"] = max(0, s["n"] - 2)
    elif re.search(r"tekrar", t):
        s["n"] = max(0, s["n"] - 1)
    elif re.search(r"\bilk\b", t):
        s["n"] = 0
    n = s["n"]
    if n >= len(adim):
        s["n"] = 0
        return _do("Tüm adımlar bitti efendim. Devreyi kontrol et ve simülasyonu başlat diyerek deneyebilirsiniz.", {"op": "hesap", "baslik": sab["ad"] + ": adımlar", "satirlar": [[str(i + 1), x] for i, x in enumerate(adim)], "aciklama": "Tüm adımlar tamamlandı."})
    s["n"] = n + 1
    return _do(f"Adım {n + 1} / {len(adim)}: {adim[n]}", {"op": "hesap", "baslik": f"{sab['ad']}: adım {n + 1}/{len(adim)}", "satirlar": [[str(i + 1), x + ("  ◀" if i == n else "")] for i, x in enumerate(adim)], "aciklama": adim[n]})


_SIN = {"mesafe": ["hcsr04", "ir_engel"], "uzaklik": ["hcsr04"], "sicaklik": ["lm35", "dht11", "ds18b20", "termistor"], "isi": ["lm35", "ds18b20"], "nem": ["dht11", "toprak_nem"], "isik": ["ldr", "led"],
        "hareket": ["pir", "mpu6050"], "ses": ["mikrofon", "buzzer"], "gaz": ["mq2"], "duman": ["mq2"], "motor": ["dc_motor", "servo", "step_motor", "l298n"], "ekran": ["lcd1602", "oled", "tm1637"],
        "kablosuz": ["hc05", "esp32", "nrf24"], "wifi": ["esp32", "nodemcu"], "bluetooth": ["hc05"], "kumanda": ["ir_alici", "joystick"], "pil": ["pil_9v", "lipo", "tp4056"], "saat": ["rtc"],
        "kart": ["rfid"], "basinc": ["bmp280"], "egim": ["mpu6050"], "ivme": ["mpu6050"], "buyuk": ["role", "mosfet_n"], "yuk": ["role", "mosfet_n", "transistor_npn"]}


def _oner(t):
    cand = []
    for w in t.split():
        for k, v in _SIN.items():
            if w.startswith(k):
                cand += v
    if not cand:
        q = [w for w in t.split() if len(w) >= 4 and w not in ("oner", "parca", "oneri")]
        sc = []
        for pid, p in PARTS.items():
            txt = fold(p["ad"] + " " + p["kisa"] + " " + p["bilgi"])
            n = sum(1 for w in q if w in txt)
            if n:
                sc.append((n, pid))
        cand = [pid for _, pid in sorted(sc, reverse=True)[:3]]
    cand = list(dict.fromkeys(cand))[:3]
    if not cand:
        return {"say": "Ne yapmak istediğinizi biraz daha anlatır mısınız efendim? Örneğin mesafe ölçmek için hangi parça diye sorabilirsiniz."}
    return _do("Önerim: " + "; ".join(f"{PARTS[c]['ad']} ({PARTS[c]['kisa']})" for c in cand), {"op": "bilgi", "p": cand[0]})


# ============================================================ blok tabanlı kart kurucu
# Plan (E["plan"]) yalnızca RAM'dedir; mod her açılışta boş başlar. Tarif/konuşma diske yazılmaz (yalnızca kurulan kart, adıyla kayıt dosyasına).
# Ollama ile seçim ayrı iş parçacığında yapılır; sonuç NOTIFY ile sayfaya gider (main'de bağlanır).
NOTIFY = None            # (kind, do) -> sayfaya işlem gönderir
SAY = None               # (metin, kind) -> sesli söyler (PC penceresi açıkken)
LLM = True               # False: yalnızca kural tabanlı seçim (testler)
_KUR_RX = r"\bkart\w*\s+(kur|tasarla|yap|olustur|hazirla|cizelim|kuralim)\w*"


def _bildir(do, say=None):
    if NOTIFY:
        try:
            NOTIFY("elektronik", do)
        except Exception as e:                      # noqa: BLE001
            print("elektronik bildirim hatası:", type(e).__name__, flush=True)
    if say and SAY:
        try:
            SAY(say, "elektronik")
        except Exception:                           # noqa: BLE001
            pass


def _plan_op(calisiyor=False, notlar=None, msg=None):
    d = {"op": "plan", "mcu": E["mcu"], "plan": bl.plan_satirlari(E["plan"]), "notlar": list(notlar or []), "calisiyor": bool(calisiyor)}
    if msg:
        d["msg"] = msg
    return d


def _plan_sifirla():
    E["gen"] += 1
    E.update(plan=[], mcu="uno", mcu_acik=False, ipucu=None)


def _plan_ozeti():
    return "; ".join(s["ozet"] for s in bl.plan_satirlari(E["plan"])) or "boş"


def _kur_uygula(st):
    """Plandan kartı kurar (mevcut kartın üzerine yazar; sayfa geri al tutar). (kart, notlar) döner; BlokHata yükseltir."""
    r = bl.kur(E["plan"], E["mcu"], ipucu=E.get("ipucu"), esnek=not E["mcu_acik"])
    k = r["kart"]
    E["kart"] = k
    if isinstance(st, dict):
        st["kart"] = k
    E["sab"] = None
    E["mcu"] = r["mcu"]
    E["ipucu_ad"] = k["ad"]
    return k, r["notlar"]


def _anlat_metni(notlar):
    return "Plan: " + _plan_ozeti() + "\n" + "\n".join(dict.fromkeys(notlar))


def _soylenen(k, notlar, sec_notlari):
    n_uy = sum(1 for n in notlar if n.startswith(("HATA", "Uyarı (kontrol)")))
    say = f"Kartı kurdum efendim: {len(k['parcalar'])} parça, {bl.MCULAR[E['mcu']]['ad']}."
    yok = [n for n in sec_notlari if "bloğum yok" in n or "üretemem" in n]
    if yok:
        say += " " + yok[0]
    if n_uy:
        say += f" Kontrolde {n_uy} uyarı çıktı, ayrıntılar ekranda."
    return say


def _tarif_isle(tarif, st, gen, bekle=0.0):
    """Ayrı iş parçacığı: tarif -> blok seçimi (LLM ya da kural) -> plan -> kart. Eskimiş (gen değişmiş) sonuç atılır."""
    import time
    try:
        if bekle:
            time.sleep(bekle)
            _bildir({"op": "plan", "mcu": E["mcu"], "plan": [], "notlar": [], "calisiyor": True, "msg": "Düşünüyorum efendim…"})
        r = bl.sec(tarif, llm=LLM)
        if gen != E["gen"]:
            return
        if not r["bloklar"]:
            soru = r["soru"] or "Bu isteği bloklarla karşılayamadım efendim."
            _bildir(_plan_op(False, r["notlar"] + [soru], soru), soru)
            return
        E["plan"] = r["bloklar"]
        E["mcu"], E["mcu_acik"], E["ipucu"] = r["mcu"], bool(r.get("mcu_acik")), r["ipucu"]
        try:
            k, notlar = _kur_uygula(st)
        except bl.BlokHata as e:
            _bildir(_plan_op(False, r["notlar"] + [str(e)], str(e)), "Kartı kuramadım efendim. " + str(e))
            return
        if gen != E["gen"]:
            return
        notlar = r["notlar"] + notlar
        say = _soylenen(k, notlar, r["notlar"])
        _bildir(_plan_op(False, [], f"Plan hazır: {_plan_ozeti()}"))
        _bildir({"op": "kart", "kart": k, "msg": say})
        _bildir({"op": "anlat", "metin": _anlat_metni(notlar)}, say)
    except Exception as e:                          # noqa: BLE001
        print("elektronik blok kurucu hatası:", type(e).__name__, e, flush=True)
        _bildir(_plan_op(False, ["Kurucu hata verdi, tekrar deneyin."], "Kurucu hata verdi efendim."))


def _tarif_baslat(tarif, st):
    E["gen"] += 1
    g = E["gen"]
    threading.Thread(target=_tarif_isle, args=(tarif, st, g), daemon=True).start()
    return _do("Düşünüyorum efendim…", _plan_op(True, [], "Düşünüyorum efendim…"))


def tarif_mi(t):
    """Folded metin bir blok kurucu isteği mi? ('kart kur: ...', '... yapan bir kart tasarla')"""
    m = re.search(_KUR_RX, t)
    if not m:
        return False
    kalan = (t[:m.start()] + " " + t[m.end():]).split()
    return len(kalan) >= 3 or bool(re.match(r"kart\w*\s+kur\b", t) and len(kalan) >= 1)


def _plan_ses(raw, t, st):
    if re.search(r"\bplan\w*\s+(temizle|sifirla|bosalt)\w*|plani (sil|temizle)", t):
        _plan_sifirla()
        return _do("Planı temizledim efendim.", _plan_op(False, [], "Plan temizlendi."))
    if re.search(r"\bplan\w*\s+(kur|olustur|uygula)\w*|plani (kur|karta)", t):
        return _ozel("§kur", st, soyle=True)
    if re.search(r"plani (goster|oku)|plan(da)? ne var|plan nedir", t):
        return _do("Plan: " + _plan_ozeti() + ".", _plan_op(False))
    m = re.search(r"\bplana?\b(.*)\b(ekle|ilave|koy)\w*", t)
    if m:
        it = bl.blok_bul(m.group(1) + " " + raw)
        if not it:
            return {"say": "Hangi bloğu ekleyeceğimi anlayamadım efendim. Örneğin plana LED bloğu ekle deyin."}
        return _blok_ekle(it["id"], it["param"])
    return None


def _blok_ekle(bid, param):
    b = bl.BLOKLAR.get(bid)
    if not b:
        return {"say": ""}
    if len(E["plan"]) >= 24:
        return _do("Plan dolu efendim (en çok 24 blok).", _plan_op(False))
    E["plan"].append({"id": bid, "param": bl.param_dogrula(b, param)})
    return _do(f"{b['ad']} bloğu plana eklendi efendim.", _plan_op(False))


def _blok_komut(raw, t, st):
    """Blok kurucu sesli/yazılı komutları: 'kart kur: <tarif>', '... yapan bir kart tasarla', 'plana LED bloğu ekle', 'planı kur', 'planı temizle'."""
    r = _plan_ses(raw, t, st)
    if r is not None:
        return r
    if not re.search(_KUR_RX, t):
        return None
    if tarif_mi(t):
        ham = re.sub(r"^\s*kart\w*\s+kur\w*\s*[:,]?\s*", "", raw.strip(), flags=re.I)
        return _tarif_baslat(ham or raw, st)
    if re.match(r"(bir )?kart\w*\s+(kur|tasarla|olustur|hazirla)\w*$", t):
        return {"say": "Nasıl bir kart kurayım efendim? Ne yapmasını istediğinizi söyleyin; örneğin: uno ile sıcaklığı ölçüp ekranda gösteren, 30 derecede fanı açan bir kart kur."}
    return None


def blok_tarifi_mi(metin):
    """extras için: açılış cümlesi bir blok tarifi mi (şablon adı yoksa ya da 'kart' diyorsa)."""
    return tarif_mi(fold(metin))


def tarif_ham(metin):
    return re.sub(r"^\s*kart\w*\s+kur\w*\s*[:,]?\s*", "", str(metin).strip(), flags=re.I)


# ============================================================ başlangıç verisi
_PUB = None


def _public():
    global _PUB
    if _PUB is None:
        keep = ("ad", "kat", "ref", "kisa", "bilgi", "pinler", "ozellik", "kullanim", "dikkat", "degerler", "varsayilan", "renkler", "satir", "m")
        _PUB = {pid: {k: p[k] for k in keep if k in p} for pid, p in PARTS.items()}
    return _PUB


def init_payload():
    pend = PENDING.pop("elektronik", None)
    _plan_sifirla()
    if pend:
        s = sablon_bul(pend)
        if s and not re.search(r"\bkart", fold(pend)):
            E["kart"] = an.sablon_kart(s)
            E["sab"] = {"id": s["id"], "n": 0}
        elif blok_tarifi_mi(pend):                        # "... yapan bir kart kur": mod açılınca blok kurucu çalışır
            threading.Thread(target=_tarif_isle, args=(tarif_ham(pend), {}, E["gen"], 1.2), daemon=True).start()
    d = _load()
    kart = E["kart"] or d["kartlar"].get(d.get("son") or "")
    return {"parts": _public(), "kats": [list(k) for k in KATS], "kart": kart, "kartlar": sorted(d["kartlar"]),
            "sablonlar": [{"id": s["id"], "ad": s["ad"], "acik": s["acik"]} for s in SABLONLAR],
            "bloklar": bl.katalog(), "plan": [], "mcular": bl.MCU_ADLAR}
