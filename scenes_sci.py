"""Fizik ve matematik laboratuvarı modlarının komut işleyicileri. Çıktı: {'do': sayfaya giden komut, 'say': konuşulacak metin}.
Hesaplar güvenli çözümleyiciyle (safemath) yapılır; eval/exec yoktur."""
import math
import re

import numpy as np

import sci_data as D
import sci_data2 as D2
from safemath import MathErr, _numwords, evaluate, f_of, parse, speech_to_expr


def _norm(text: str) -> str:
    t = text.replace("İ", "i").replace("I", "ı").lower()
    t = re.sub(r"['’]\w*", "", t)
    t = re.sub(r"[^\w\sçğıöşü%.,²³^/*+=()\-]", " ", t)
    t = re.sub(r"\b(jarvis|hey|lütfen|bana|şunu|efendim|hadi|şimdi|bize)\b", " ", t)
    return " ".join(t.split())


def fmt(x: float, say: bool = True) -> str:
    """Okunaklı sayı: 4 anlamlı basamak; konuşmada virgül (nokta 'nokta' diye okunmasın)."""
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "tanımsız"
    if abs(x - round(x)) < 1e-9 and abs(x) < 1e12:
        s = str(int(round(x)))
    else:
        s = f"{x:.4g}"
        if "e" in s:
            v = float(s)
            s = str(int(v)) if 1 <= abs(v) < 1e15 else f"{x:.3e}"
    return s.replace(".", ",") if say else s


def _num(t: str):
    m = re.search(r"(-?\d+(?:[.,]\d+)?)", t)
    return float(m.group(1).replace(",", ".")) if m else None


# ============================================================== FİZİK
FZ = {e["key"]: e for e in D.FIZ_EXPS + D2.AST_EXPS + D2.GEO_EXPS}
CAT = {"fizik": (D.FIZ_EXPS, D.FIZ_CONCEPTS), "astronomi": (D2.AST_EXPS, D2.AST_CONCEPTS), "jeoloji": (D2.GEO_EXPS, D2.GEO_CONCEPTS)}
# parametre sözcükleri: (deney, parametre) -> desen; deney '*' tüm deneylerde
PARAM_PAT = {   # açık (ordinal / tam ad içeren) desenler önce denenir
    ("atis", "v"): r"(?:başlangıç )?hız\w*|sürat\w*", ("atis", "a"): r"açı\w*", ("atis", "g"): r"yerçekimi\w*|çekim\w*", ("atis", "h"): r"yüksekli\w*|kule\w*",
    ("sarkac", "L"): r"ip(?: uzunl\w*)?|uzunl\w*|boy\w*", ("sarkac", "t0"): r"(?:başlangıç )?açı\w*", ("sarkac", "g"): r"yerçekimi\w*|çekim\w*",
    ("yay", "m"): r"kütle\w*", ("yay", "k"): r"yay sabiti\w*|sabit\w*|sertlik\w*", ("yay", "A"): r"genlik\w*",
    ("ohm", "V"): r"gerilim\w*|pil\w*|volt\w*", ("ohm", "R1"): r"(?:birinci|ilk|1\.?) direnç\w*|direnç 1|r1", ("ohm", "R2"): r"(?:ikinci|2\.?) direnç\w*|direnç 2|r2",
    ("dalga", "f2"): r"(?:ikinci|2\.?) (?:dalga\w* )?frekans\w*|f2", ("dalga", "A2"): r"(?:ikinci|2\.?) (?:dalga\w* )?genlik\w*|a2",
    ("dalga", "f1"): r"(?:birinci|ilk|1\.?) (?:dalga\w* )?frekans\w*|f1", ("dalga", "A1"): r"(?:birinci|ilk|1\.?) (?:dalga\w* )?genlik\w*|a1",
    ("kirilma", "n1"): r"(?:üst|birinci|1\.?) ortam\w*(?: (?:kırıcılık|indis)\w*)?|n1", ("kirilma", "n2"): r"(?:alt|ikinci|2\.?) ortam\w*(?: (?:kırıcılık|indis)\w*)?|n2",
    ("kirilma", "a"): r"(?:gelme )?açı\w*",
    ("carpisma", "m1"): r"(?:birinci|1\.?) (?:cisim\w* )?kütle\w*|kütle 1|m1", ("carpisma", "m2"): r"(?:ikinci|2\.?) (?:cisim\w* )?kütle\w*|kütle 2|m2",
    ("carpisma", "v1"): r"(?:birinci|1\.?) (?:cisim\w* )?hız\w*|hız 1|v1", ("carpisma", "v2"): r"(?:ikinci|2\.?) (?:cisim\w* )?hız\w*|hız 2|v2",
    ("carpisma", "e"): r"esneklik\w*|e katsayı\w*",
    ("mercek", "f"): r"odak(?: uzaklığ\w*)?", ("mercek", "d"): r"(?:cisim )?uzaklığ\w*|mesafe\w*",
    ("duzlem", "a"): r"açı\w*|eğim\w*", ("duzlem", "mu"): r"sürtünme\w*|μ", ("duzlem", "m"): r"kütle\w*",
    ("ayevre", "gun"): r"yaş\w*|gün\w*", ("mevsim", "gun"): r"yılın günü|gün\w*|tarih\w*", ("mevsim", "egim"): r"eğikli\w*|eğim\w*|eksen\w*",
    ("kepler", "e"): r"dışmerkezli\w*|elips\w*|e\b", ("kepler", "a"): r"yarı büyük eksen\w*|büyük eksen\w*|uzaklık\w*|a\b",
    ("yorunge", "v"): r"hız\w*|sürat\w*", ("hr", "m"): r"kütle\w*", ("tutulma", "beta"): r"sapma\w*|beta\w*|eğikli\w*", ("tutulma", "tur"): r"tür\w*",
    ("agirlik", "k"): r"kütle\w*|kilo\w*|kg",
    ("levha", "tur"): r"tür\w*|sınır\w*", ("levha", "hiz"): r"hız\w*|sürat\w*", ("deprem", "M"): r"büyüklü\w*|magnitüd\w*|şiddet\w*", ("deprem", "km"): r"uzaklık\w*|mesafe\w*",
    ("kayac", "adim"): r"adım\w*|aşama\w*", ("katman", "mm"): r"birikme\w*|birikim\w*|hız\w*", ("katman", "m"): r"kalınlı\w*",
    ("radyo", "kalan"): r"kalan\w*|yüzde\w*", ("radyo", "yom"): r"yarı ömür\w*", ("volkan", "si"): r"silika\w*", ("mohs", "s"): r"sertlik\w*|mohs",
    ("zaman", "my"): r"milyon yıl\w*|milyon\w*|my\b",
}
from lab_more_sim import PARAM_PAT_X  # noqa: E402
PARAM_PAT.update(PARAM_PAT_X)
PARAM_GEN = {   # ordinal söylenmediyse geçerli genel sözcükler
    ("dalga", "f1"): r"frekans\w*", ("dalga", "A1"): r"genlik\w*", ("kirilma", "n2"): r"kırıcılık\w*|indis\w*",
    ("ohm", "R1"): r"direnç\w*", ("carpisma", "m1"): r"kütle\w*", ("carpisma", "v1"): r"hız\w*",
}
GRAV = [("ay", 1.62, r"\bay(?:da)?\b"), ("mars", 3.71, r"mars\w*"), ("jüpiter", 24.8, r"jüpiter\w*"), ("dünya", 9.81, r"dünya\w*"), ("venüs", 8.87, r"venüs\w*"), ("merkür", 3.7, r"merkür\w*")]


def fz_defaults(key):
    return {p[0]: p[5] for p in FZ[key]["params"]}


def lab_init(kind):
    exps, concepts = CAT[kind]
    out = {"exps": [{"key": e["key"], "name": e["name"], "aim": e["aim"], "params": [list(p) for p in e["params"]], "formulas": e["formulas"], "why": e["why"]} for e in exps],
           "concepts": [{"title": t, "text": x} for t, _, x in concepts]}
    if kind == "jeoloji":
        out["mohs"] = [list(m) for m in D2.MOHS]
        out["time"] = [list(z) for z in D2.GEO_TIME]
    if kind == "astronomi":
        out["bodies"] = [list(b) for b in D2.BODY_G]
    return out


def fz_init():
    return lab_init("fizik")


def fz_results(key, p):
    """(satırlar, sözlü özet) — sayfadaki JS ile aynı formüller."""
    g = p.get("g", 9.81)
    if key == "atis":
        v, a, h = p["v"], math.radians(p["a"]), p["h"]
        vx, vy = v * math.cos(a), v * math.sin(a)
        t = (vy + math.sqrt(vy * vy + 2 * g * h)) / g
        rng, hmax = vx * t, h + vy * vy / (2 * g)
        return ([f"Uçuş süresi: {fmt(t, False)} s", f"Menzil: {fmt(rng, False)} m", f"En büyük yükseklik: {fmt(hmax, False)} m", f"Yatay hız: {fmt(vx, False)} m/s"],
                f"Cisim yaklaşık {fmt(t)} saniye havada kalır, {fmt(rng)} metre uzağa düşer ve en fazla {fmt(hmax)} metre yükselir.")
    if key == "sarkac":
        T = 2 * math.pi * math.sqrt(p["L"] / g)
        return ([f"Periyot: {fmt(T, False)} s", f"Frekans: {fmt(1 / T, False)} Hz"], f"Sarkacın periyodu yaklaşık {fmt(T)} saniye, frekansı {fmt(1 / T)} hertz.")
    if key == "yay":
        w = math.sqrt(p["k"] / p["m"])
        T = 2 * math.pi / w
        return ([f"Periyot: {fmt(T, False)} s", f"Açısal frekans: {fmt(w, False)} rad/s", f"En büyük hız: {fmt(p['A'] * w, False)} m/s", f"Toplam enerji: {fmt(0.5 * p['k'] * p['A'] ** 2, False)} J"],
                f"Periyot yaklaşık {fmt(T)} saniye, en büyük hız {fmt(p['A'] * w)} metre bölü saniye, toplam enerji {fmt(0.5 * p['k'] * p['A'] ** 2)} joule.")
    if key == "ohm":
        V, R1, R2 = p["V"], p["R1"], p["R2"]
        par = p.get("p", 0) >= 0.5
        Req = R1 * R2 / (R1 + R2) if par else R1 + R2
        I = V / Req
        if par:
            lines = [f"Eşdeğer direnç: {fmt(Req, False)} Ω (paralel)", f"Toplam akım: {fmt(I, False)} A", f"R1 akımı: {fmt(V / R1, False)} A, R2 akımı: {fmt(V / R2, False)} A", f"Güç: {fmt(V * I, False)} W"]
        else:
            lines = [f"Eşdeğer direnç: {fmt(Req, False)} Ω (seri)", f"Akım: {fmt(I, False)} A", f"R1 gerilimi: {fmt(I * R1, False)} V, R2 gerilimi: {fmt(I * R2, False)} V", f"Güç: {fmt(V * I, False)} W"]
        return lines, f"{'Paralel' if par else 'Seri'} bağlantıda eşdeğer direnç {fmt(Req)} ohm, toplam akım {fmt(I)} amper, güç {fmt(V * I)} watt."
    if key == "dalga":
        f1, f2 = p["f1"], p["f2"]
        beat = abs(f1 - f2)
        return ([f"Dalga 1 periyodu: {fmt(1 / f1, False)} s", (f"Dalga 2 periyodu: {fmt(1 / f2, False)} s" if f2 > 0 else "Dalga 2 kapalı"), f"Vuru frekansı: {fmt(beat, False)} Hz", f"En büyük toplam genlik: {fmt(p['A1'] + p['A2'], False)}"],
                f"Vuru frekansı {fmt(beat)} hertz. Tepeler çakıştığında toplam genlik {fmt(p['A1'] + p['A2'])} olur.")
    if key == "kirilma":
        n1, n2, a = p["n1"], p["n2"], math.radians(p["a"])
        s = n1 * math.sin(a) / n2
        if s > 1:
            crit = math.degrees(math.asin(n2 / n1))
            return ([f"Tam yansıma! Sınır açısı: {fmt(crit, False)}°", "Işık ikinci ortama geçemez, geri yansır."], f"Gelme açısı sınır açısı olan {fmt(crit)} dereceyi aştı, ışık tamamen yansıyor.")
        r = math.degrees(math.asin(s))
        lines = [f"Kırılma açısı: {fmt(r, False)}°", f"Üst ortamda ışık hızı: {fmt(3e8 / n1, False)} m/s", f"Alt ortamda ışık hızı: {fmt(3e8 / n2, False)} m/s"]
        if n1 > n2:
            lines.append(f"Sınır açısı: {fmt(math.degrees(math.asin(n2 / n1)), False)}°")
        return lines, f"Kırılma açısı yaklaşık {fmt(r)} derece. Işık {'normale yaklaşır' if n2 > n1 else 'normalden uzaklaşır' if n2 < n1 else 'doğrultusunu korur'}."
    if key == "carpisma":
        m1, v1, m2, v2, e = p["m1"], p["v1"], p["m2"], p["v2"], p["e"]
        u1 = ((m1 - e * m2) * v1 + (1 + e) * m2 * v2) / (m1 + m2)
        u2 = ((m2 - e * m1) * v2 + (1 + e) * m1 * v1) / (m1 + m2)
        ke0 = 0.5 * m1 * v1 ** 2 + 0.5 * m2 * v2 ** 2
        ke1 = 0.5 * m1 * u1 ** 2 + 0.5 * m2 * u2 ** 2
        return ([f"Çarpışma sonrası hızlar: {fmt(u1, False)} ve {fmt(u2, False)} m/s", f"Toplam momentum: {fmt(m1 * v1 + m2 * v2, False)} kg·m/s (korunur)",
                 f"Kinetik enerji: {fmt(ke0, False)} J → {fmt(ke1, False)} J", f"Kaybolan enerji: {fmt(ke0 - ke1, False)} J"],
                f"Çarpışmadan sonra birinci cisim {fmt(u1)}, ikinci cisim {fmt(u2)} metre bölü saniye hızla gider. Momentum korunur, {fmt(ke0 - ke1)} joule kinetik enerji kaybolur.")
    if key == "mercek":
        f, d = p["f"] if abs(p["f"]) >= 1 else (1 if p["f"] >= 0 else -1), p["d"]
        if abs(1 / f - 1 / d) < 1e-9:
            return (["Görüntü sonsuzda oluşur (cisim odakta)."], "Cisim tam odakta, ışınlar paralel çıkar, görüntü sonsuzda oluşur.")
        di = 1 / (1 / f - 1 / d)
        M = -di / d
        kind = "gerçek ve ters" if di > 0 else "sanal ve düz"
        size = "büyük" if abs(M) > 1.05 else "küçük" if abs(M) < 0.95 else "aynı boyda"
        return ([f"Görüntü uzaklığı: {fmt(di, False)} cm", f"Büyütme: {fmt(M, False)}×", f"Görüntü: {kind}, {size}"], f"Görüntü mercekten {fmt(abs(di))} santimetre uzakta, {kind} ve {size}. Büyütme {fmt(abs(M))} kat.")
    if key == "duzlem":
        a, mu, m = math.radians(p["a"]), p["mu"], p["m"]
        par, N = m * g * math.sin(a), m * g * math.cos(a)
        fr = mu * N
        acc = g * (math.sin(a) - mu * math.cos(a))
        if acc <= 0:
            return ([f"Kaydırıcı bileşen: {fmt(par, False)} N", f"Maksimum sürtünme: {fmt(fr, False)} N", "Cisim kaymaz, durur."], "Sürtünme yeterince büyük, cisim kaymıyor.")
        return ([f"İvme: {fmt(acc, False)} m/s²", f"Kaydırıcı bileşen: {fmt(par, False)} N", f"Normal kuvvet: {fmt(N, False)} N", f"Sürtünme: {fmt(fr, False)} N"], f"Cisim {fmt(acc)} metre bölü saniye kare ivmeyle kayar.")
    from lab_more_sim import results as _more_results
    r = _more_results(key, p) or _ag_results(key, p)
    if r:
        return r
    return [], ""


def _ag_results(key, p):
    """Astronomi ve jeoloji deneylerinin hesapları: (satırlar, sözlü özet)."""
    if key == "ayevre":
        gun = p["gun"]
        lit = (1 - math.cos(gun / 29.53 * 2 * math.pi)) / 2
        import astro
        name = astro.phase_name(gun / 29.53 * 360)
        return ([f"Evre: {name}", f"Aydınlık oran: %{fmt(lit * 100, False)}", f"Ay'ın yaşı: {fmt(gun, False)} gün"],
                f"{fmt(gun)} günlük Ay, {name.lower()} evresinde; yüzeyinin yaklaşık yüzde {fmt(lit * 100)} kadarı aydınlık görünür.")
    if key == "mevsim":
        N, eg, lat = p["gun"], p["egim"], 37.3
        dec = eg * math.sin(math.radians(360 * (N - 80) / 365))
        cosH = -math.tan(math.radians(lat)) * math.tan(math.radians(dec))
        day = 0.0 if cosH >= 1 else 24.0 if cosH <= -1 else 2 * math.degrees(math.acos(cosH)) / 15
        noon = 90 - abs(lat - dec)
        season = "kış" if dec < -eg * 0.5 else "yaz" if dec > eg * 0.5 else "ilkbahar ya da sonbahar"
        return ([f"Güneş'in sapması: {fmt(dec, False)}°", f"Gün uzunluğu (37° kuzey enlemi): {fmt(day, False)} saat", f"Öğle Güneş yüksekliği: {fmt(noon, False)}°", f"Kuzey yarımkürede mevsim: {season}"],
                f"Güneş'in sapması {fmt(dec)} derece. 37° enleminde gün {fmt(day)} saat sürer, öğle Güneş'i {fmt(noon)} derece yüksekte; kuzey yarımkürede {season}.")
    if key == "kepler":
        a, e = p["a"], p["e"]
        T = a ** 1.5
        return ([f"Periyot: {fmt(T, False)} yıl", f"Yakın nokta: {fmt(a * (1 - e), False)} AB", f"Uzak nokta: {fmt(a * (1 + e), False)} AB", f"Hız oranı (yakın/uzak): {fmt((1 + e) / (1 - e), False)}×"],
                f"Periyot {fmt(T)} yıl. Güneş'e en yakın nokta {fmt(a * (1 - e))}, en uzak nokta {fmt(a * (1 + e))} astronomik birim. Yakın noktada gezegen uzak noktadakinden {fmt((1 + e) / (1 - e))} kat hızlı gider.")
    if key == "yorunge":
        v, vc, ve = p["v"], 7.67, 10.85
        ratio2 = (v / vc) ** 2
        if v >= ve:
            kind, say = "Kaçış: Dünya'dan ayrılır", "Hız kaçış hızını aştı, cisim Dünya'dan ayrılır."
        elif abs(v - vc) < 0.08:
            kind, say = "Dairesel yörünge", "Hız dairesel yörünge hızına çok yakın, cisim Dünya'yı daire çizerek dolaşır."
        elif v > vc:
            kind, say = "Eliptik yörünge (uzak nokta yükselir)", "Hız dairesel hızdan büyük, cisim uzak noktası yüksek bir elips çizer."
        else:
            kind, say = "Eliptik ya da düşen yörünge", "Hız dairesel hızdan küçük; elipsin yakın noktası Dünya'nın içinde kalırsa cisim düşer."
        lines = [kind, f"Hız: {fmt(v, False)} km/s (dairesel {fmt(vc, False)}, kaçış {fmt(ve, False)})"]
        if ratio2 < 2:
            a_ = 1 / (2 - ratio2) * 6771
            lines.append(f"Yarı büyük eksen ≈ {fmt(a_, False)} km")
            lines.append(f"Periyot ≈ {fmt(2 * math.pi * math.sqrt(a_ ** 3 / 398600) / 60, False)} dakika")
        return lines, say
    if key == "hr":
        m = p["m"]
        L, life, T = m ** 3.5, 10 * m ** -2.5, 5772 * m ** 0.505
        cls = "O" if T > 30000 else "B" if T > 10000 else "A" if T > 7500 else "F" if T > 6000 else "G" if T > 5200 else "K" if T > 3700 else "M"
        end = "çok sönük kırmızı cüce olarak uzun süre yaşar" if m < 0.5 else "kızıl dev, ardından beyaz cüce" if m < 8 else "süpernova, ardından nötron yıldızı" if m < 25 else "süpernova, ardından kara delik"
        return ([f"Parlaklık: {fmt(L, False)} Güneş", f"Yüzey sıcaklığı: {fmt(T, False)} K (sınıf {cls})", f"Ana kol ömrü: {fmt(life, False)} milyar yıl", f"Sonu: {end}"],
                f"{fmt(m)} Güneş kütleli yıldız, Güneş'ten {fmt(L)} kat parlak ve yaklaşık {fmt(life)} milyar yıl yaşar. Sonunda: {end}.")
    if key == "tutulma":
        beta, tur = p["beta"], p["tur"] >= 0.5
        ab = abs(beta)
        kind = ("tam" if ab < 0.9 else "kısmi") if ab < 1.5 else None
        nm = "Ay tutulması" if tur else "Güneş tutulması"
        if kind:
            return [f"{nm}: {kind} tutulma", f"Sapma: {fmt(beta, False)}°"], f"{nm} oluşur: {kind} tutulma."
        return ([f"{nm} olmaz", f"Sapma {fmt(beta, False)}° çok büyük; Ay gölgenin üstünden ya da altından geçer."], f"Sapma {fmt(ab)} derece, fazla büyük; tutulma olmaz.")
    if key == "agirlik":
        k = p["k"]
        lines = [f"{n}: {fmt(k * g, False)} N  ({fmt(k * g / 9.81, False)} kg-kuvvet)" for n, g in D2.BODY_G]
        return lines, f"{fmt(k)} kilogram kütle Dünya'da {fmt(k * 9.81)} newton çeker. Ay'da {fmt(k * 1.62)}, Mars'ta {fmt(k * 3.71)}, Jüpiter'de {fmt(k * 24.79)} newton çeker."
    if key == "levha":
        tur, hiz = int(round(p["tur"])), p["hiz"]
        names = ["Iraksak sınır (okyanus ortası sırt)", "Yakınsak sınır: okyanus-kıta (dalma-batma)", "Yakınsak sınır: kıta-kıta (çarpışma)", "Doğrultu atımlı sınır (yanal fay)"]
        feat = ["Yeni kabuk oluşur, sırt ve yarık vadisi; örnek: Atlantik Sırtı, Doğu Afrika Rifti", "Okyanus çukuru ve volkanik kıyı dağları; örnek: And Dağları",
                "Dev dağ sıraları yükselir; örnek: Himalayalar, Bitlis-Zagros kuşağı", "Kabuk ne oluşur ne yok olur, büyük depremler olur; örnek: Kuzey Anadolu Fayı, San Andreas"]
        return ([names[tur], feat[tur], f"Hız {fmt(hiz, False)} cm/yıl: bir milyon yılda {fmt(hiz * 10, False)} km yer değiştirir"],
                f"{names[tur]}. {feat[tur]}. Levha bir milyon yılda yaklaşık {fmt(hiz * 10)} kilometre yer değiştirir.")
    if key == "deprem":
        M, km = p["M"], p["km"]
        E = 10 ** (1.5 * M + 4.8)
        tnt = E / 4.184e9
        tp, ts = km / 6.0, km / 3.5
        mmi = max(1, min(12, 1.5 * M - 1.4 * math.log10(max(km, 5)) + 0.5))
        sev = "hissedilmez" if mmi < 3 else "hafif sarsıntı" if mmi < 5 else "orta şiddette hasar" if mmi < 7 else "ciddi hasar" if mmi < 9 else "yıkıcı etki"
        return ([f"Enerji: {E:.2e} J (≈ {fmt(tnt, False)} ton TNT)", f"P dalgası varışı: {fmt(tp, False)} s", f"S dalgası varışı: {fmt(ts, False)} s (fark {fmt(ts - tp, False)} s)", f"Bu uzaklıkta yaklaşık etki: {sev}"],
                f"{fmt(M)} büyüklüğündeki deprem yaklaşık {fmt(tnt)} ton TNT enerjisi açığa çıkarır. {fmt(km)} kilometrede P dalgası {fmt(tp)}, S dalgası {fmt(ts)} saniyede gelir; etki: {sev}.")
    if key == "kayac":
        steps = ["Magma soğuyup katılaşır: MAGMATİK kayaç oluşur (granit, bazalt)", "Rüzgâr, su ve buz kayayı AŞINDIRIR, parçalar taşınır", "Parçalar birikir ve sıkışıp çimentolanır: TORTUL kayaç oluşur (kumtaşı, kireçtaşı)",
                 "Isı ve basınç kayacı değiştirir: METAMORFİK kayaç oluşur (mermer, gnays)", "Çok derinde kayaç ERİYİP magma olur", "Her kayaç uygun koşulda diğer türe dönüşebilir; döngü kapanır"]
        i = int(max(1, min(6, round(p["adim"])))) - 1
        return [f"Adım {i + 1}/6: {steps[i]}"], steps[i] + "."
    if key == "katman":
        yil = p["m"] * 1000 / p["mm"]
        return [f"Birikme süresi: {fmt(yil, False)} yıl", f"Birikme hızı: {fmt(p['mm'], False)} mm/yıl", "Alttaki katman en yaşlıdır"], f"{fmt(p['m'])} metrelik katman yaklaşık {fmt(yil)} yılda birikir."
    if key == "radyo":
        kalan, yom = p["kalan"], p["yom"]
        t = yom * math.log2(100 / kalan)
        return [f"Yaş: {fmt(t, False)} yıl", f"Geçen yarı ömür sayısı: {fmt(t / yom, False)}", f"Kalan: %{fmt(kalan, False)}"], f"Örnek yaklaşık {fmt(t)} yaşında; {fmt(t / yom)} yarı ömür geçmiş."
    if key == "volkan":
        si = p["si"]
        if si < 52:
            t, d = "Bazaltik: kalkan volkan", "Lav çok akıcıdır, yumuşak eğimli geniş bir kalkan oluşur, patlama hafiftir (örnek: Hawaii)."
        elif si < 63:
            t, d = "Andezitik: katmanlı volkan", "Lav kıvamlıdır, kül ve lav katmanları üst üste dizilir, orta şiddette patlamalar olur (örnek: Etna, Fuji)."
        else:
            t, d = "Riyolitik: şiddetli patlamalı kubbe", "Magma çok yapışkandır, gaz sıkışır ve şiddetle patlar (örnek: St. Helens)."
        return [t, d], f"{t}. {d}"
    if key == "mohs":
        s_ = int(max(1, min(10, round(p["s"]))))
        n, _, how = D2.MOHS[s_ - 1]
        return [f"{s_}. {n}: {how}", "Kendinden yumuşak minerallerin hepsini çizer"], f"Sertlik {s_}: {n}, {how}."
    if key == "zaman":
        my = p["my"]
        for a, b, name, ev in D2.GEO_TIME:
            if b <= my <= a:
                return [f"{fmt(my, False)} milyon yıl önce: {name}", ev], f"{fmt(my)} milyon yıl önce: {name}. {ev}"
        return [f"{fmt(my, False)} milyon yıl önce"], ""
    return None


UNIT_PAT = {  # değer -> (sembol, desen)
    "m": ("kütle", r"kg|kilogram|kilo"), "v": ("hız", r"m/s|metre/saniye|metre bölü saniye"), "a": ("ivme", r"m/s²|m/s2|m/s\^2"), "F": ("kuvvet", r"newton|\bn\b"),
}


def fz_formula(t: str):
    """Doğal dilden formül hesabı: '5 kg 3 m/s² kuvvet', '12 volt 4 ohm akım' vb. -> (kart, söz) ya da None."""
    q = t.replace("m/s²", " ivme_u ").replace("m/s2", " ivme_u ").replace("m/s^2", " ivme_u").replace("m/s", " hiz_u ")
    q = re.sub(r"(\d)(kg|g|n|j|w|v|a|m|s|hz|pa|ohm)\b", r"\1 \2", q)

    def val(pat):
        m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:" + pat + r")", q)
        return float(m.group(1).replace(",", ".")) if m else None

    mass = val(r"kg|kilogram|kilo")
    if mass is None:
        g_ = val(r"gram|gr\b")
        mass = g_ / 1000 if g_ is not None else None
    acc = val(r"ivme_u")
    vel = val(r"hiz_u")
    if vel is None:
        kmh = val(r"km/h|km/sa|kilometre")
        vel = kmh / 3.6 if kmh is not None else None
    force = val(r"newton|\bn\b")
    energy = val(r"joule|\bj\b")
    power = val(r"watt|\bw\b")
    volt = val(r"volt|\bv\b")
    amp = val(r"amper|\ba\b")
    ohm = val(r"ohm|ω")
    dist = val(r"metre|\bm\b")
    km = val(r"kilometre|\bkm\b")
    if km is not None and "km/h" not in q:
        dist = km * 1000 if dist is None else dist
    sec = val(r"saniye|\bsn\b|\bs\b")
    mnt = val(r"dakika|\bdk\b")
    if sec is None and mnt is not None:
        sec = mnt * 60
    area = val(r"m2|m²|metrekare")
    vol = val(r"m3|m³|metreküp")
    hz = val(r"hertz|\bhz\b")
    wl = val(r"dalga boyu")
    G = 9.81

    def out(title, formula, res, unit, say_name):
        line = f"{formula} = {fmt(res, False)} {unit}"
        return ({"title": title, "lines": [line]}, f"{say_name} yaklaşık {fmt(res)} {unit.replace('m/s²', 'metre bölü saniye kare').replace('m/s', 'metre bölü saniye').replace('N', 'newton').replace('J', 'joule').replace('W', 'watt').replace('Ω', 'ohm').replace('V', 'volt').replace('A', 'amper')}.")

    if re.search(r"kinetik", t) and mass is not None and vel is not None:
        return out("Kinetik enerji", f"½·{fmt(mass, False)}·{fmt(vel, False)}²", 0.5 * mass * vel ** 2, "J", "Kinetik enerji")
    if re.search(r"potansiyel|konum enerji", t) and mass is not None and dist is not None:
        return out("Potansiyel enerji", f"{fmt(mass, False)}·9,81·{fmt(dist, False)}", mass * G * dist, "J", "Potansiyel enerji")
    if re.search(r"momentum", t) and mass is not None and vel is not None:
        return out("Momentum", f"{fmt(mass, False)}·{fmt(vel, False)}", mass * vel, "kg·m/s", "Momentum")
    if re.search(r"ağırlık", t) and mass is not None:
        return out("Ağırlık", f"{fmt(mass, False)}·9,81", mass * G, "N", "Ağırlık")
    if re.search(r"kuvvet", t) and mass is not None and acc is not None:
        return out("Kuvvet (F = m·a)", f"{fmt(mass, False)}·{fmt(acc, False)}", mass * acc, "N", "Kuvvet")
    if re.search(r"ivme", t) and force is not None and mass is not None:
        return out("İvme (a = F/m)", f"{fmt(force, False)}/{fmt(mass, False)}", force / mass, "m/s²", "İvme")
    if re.search(r"ivme", t) and vel is not None and sec:
        return out("İvme (a = Δv/t)", f"{fmt(vel, False)}/{fmt(sec, False)}", vel / sec, "m/s²", "İvme")
    if re.search(r"\bgüç\b", t) and volt is not None and amp is not None:
        return out("Elektriksel güç (P = V·I)", f"{fmt(volt, False)}·{fmt(amp, False)}", volt * amp, "W", "Güç")
    if re.search(r"\bgüç\b", t) and energy is not None and sec:
        return out("Güç (P = W/t)", f"{fmt(energy, False)}/{fmt(sec, False)}", energy / sec, "W", "Güç")
    if re.search(r"\biş\b|enerji", t) and force is not None and dist is not None:
        return out("İş (W = F·x)", f"{fmt(force, False)}·{fmt(dist, False)}", force * dist, "J", "Yapılan iş")
    if re.search(r"direnç", t) and volt is not None and amp:
        return out("Direnç (R = V/I)", f"{fmt(volt, False)}/{fmt(amp, False)}", volt / amp, "Ω", "Direnç")
    if re.search(r"akım", t) and volt is not None and ohm:
        return out("Akım (I = V/R)", f"{fmt(volt, False)}/{fmt(ohm, False)}", volt / ohm, "A", "Akım")
    if re.search(r"gerilim", t) and amp is not None and ohm is not None:
        return out("Gerilim (V = I·R)", f"{fmt(amp, False)}·{fmt(ohm, False)}", amp * ohm, "V", "Gerilim")
    if re.search(r"basınç", t) and force is not None and area:
        return out("Basınç (P = F/A)", f"{fmt(force, False)}/{fmt(area, False)}", force / area, "Pa", "Basınç")
    if re.search(r"yoğunluk", t) and mass is not None and vol:
        return out("Yoğunluk (d = m/V)", f"{fmt(mass, False)}/{fmt(vol, False)}", mass / vol, "kg/m³", "Yoğunluk")
    if re.search(r"periyot", t) and hz:
        return out("Periyot (T = 1/f)", f"1/{fmt(hz, False)}", 1 / hz, "s", "Periyot")
    if re.search(r"frekans", t) and sec:
        return out("Frekans (f = 1/T)", f"1/{fmt(sec, False)}", 1 / sec, "Hz", "Frekans")
    if re.search(r"dalga hızı", t) and wl is not None and hz:
        return out("Dalga hızı (v = λ·f)", f"{fmt(wl, False)}·{fmt(hz, False)}", wl * hz, "m/s", "Dalga hızı")
    if re.search(r"\bhız\b|sürat", t) and dist is not None and sec:
        return out("Hız (v = x/t)", f"{fmt(dist, False)}/{fmt(sec, False)}", dist / sec, "m/s", "Hız")
    if re.search(r"\byol\b|alınan yol|gidilen", t) and vel is not None and sec:
        return out("Yol (x = v·t)", f"{fmt(vel, False)}·{fmt(sec, False)}", vel * sec, "m", "Alınan yol")
    return None


LAB_NAME = {"fizik": "Fizik", "astronomi": "Astronomi", "jeoloji": "Jeoloji"}
LAB_HINT = {"fizik": "Bir deney adı söyleyin, örneğin eğik atış ya da sarkaç; değerleri açıyı 60 yap gibi değiştirebilirsiniz. Formül için 5 kilo 3 m/s² kuvvet gibi söyleyin.",
            "astronomi": "Bir deney adı söyleyin, örneğin ay evreleri, mevsimler, Kepler ya da yıldız yaşamı; değerleri yapa çevirerek değiştirebilirsiniz. Kara delik nedir gibi kavramlar da sorabilirsiniz.",
            "jeoloji": "Bir deney adı söyleyin, örneğin levha tektoniği, deprem, kayaç döngüsü ya da volkan; değerleri büyüklüğü 7 yap gibi değiştirebilirsiniz. Fay nedir gibi kavramlar da sorabilirsiniz."}


def fizik(text: str, st: dict):
    return _lab("fizik", text, st)


def astronomi(text: str, st: dict):
    return _lab("astronomi", text, st)


def jeoloji(text: str, st: dict):
    return _lab("jeoloji", text, st)


def _lab(kind: str, text: str, st: dict):
    EXPS, CONC = CAT[kind]
    st["lab"] = kind
    t = _numwords(_norm(text))
    import lab_concepts as _K
    d = _K.find_detail(CONC, t)
    if d:
        return {"do": {"tab": "info", "concept": d[0]}, "say": _K.short_say(*d)}
    cur = st.get("exp")
    P = st.setdefault("params", {})
    # --- sekmeler
    if re.search(r"\b(deneyler|deney listesi)\b", t) and not re.search(r"\d", t):
        return {"do": {"tab": "exp"}, "say": f"{len(EXPS)} deney var: " + ", ".join(e["name"] for e in EXPS) + ". Birini söyleyin."}
    if re.search(r"\b(kavramlar|konu anlatım|konular)\b", t) and not re.search(r"nedir", t):
        return {"do": {"tab": "info"}, "say": "Kavramlar sekmesi açık efendim: " + ", ".join(c[0] for c in CONC[:6]) + " ve daha fazlası. Birini sorabilirsiniz."}
    if kind == "fizik" and (re.search(r"^(hesap|hesaplayıcı|hesaplama)$", t) or (not cur and re.search(r"^formül\w*$", t))):
        return {"do": {"tab": "calc"}, "say": "Formül hesaplayıcı efendim. Örneğin 5 kilogram 3 metre bölü saniye kare kuvvet, ya da 12 volt 4 ohm akım deyin."}
    # --- sonraki / önceki deney
    keys = [e["key"] for e in EXPS]
    if re.search(r"\b(sonraki|önceki)\b", t) and re.search(r"deney", t):
        i = keys.index(cur) if cur in keys else -1
        k = keys[(i + (1 if "sonraki" in t else -1)) % len(keys)]
        return _fz_open(k, st, kind)
    # --- parametre ayarı (açık deney varsa)
    if cur:
        changed = _fz_params(cur, t, P)
        if changed:
            lines, say = fz_results(cur, P)
            return {"do": {"tab": "exp", "exp": cur, "set": {k: P[k] for k in changed}, "result": {"title": FZ[cur]["name"], "lines": lines}},
                    "say": "Ayarladım efendim. " + say}
        if re.search(r"formül", t):
            return {"say": "Formüller. " + " ".join(FZ[cur]["formulas"])}
        if re.search(r"neden|nasıl oluyor|bilimsel|açıkla|niçin|anlat", t) and not _fz_pick(t, EXPS):
            return {"say": FZ[cur]["why"]}
        if re.search(r"sonuç|ne kadar|kaç|hesapla|değer|periyot|frekans|menzil|süre|yükseklik ne|akım|direnç ne|görüntü|büyütme|ivme|enerji ne", t) and not _fz_pick(t, EXPS) and not re.search(r"nedir|yasa|korunum", t):
            lines, say = fz_results(cur, P)
            return {"do": {"result": {"title": FZ[cur]["name"], "lines": lines}}, "say": say}
        if re.search(r"^(sıfırla|baştan|yeniden|tekrar)\b", t):
            P.clear()
            P.update(fz_defaults(cur))
            lines, say = fz_results(cur, P)
            return {"do": {"tab": "exp", "exp": cur, "set": dict(P), "result": {"title": FZ[cur]["name"], "lines": lines}}, "say": "Değerleri sıfırladım efendim."}
    # --- formül hesabı
    r = fz_formula(t) if kind == "fizik" else None
    if r:
        return {"do": {"tab": "calc", "result": r[0]}, "say": r[1]}
    # --- deney seçimi
    k = _fz_pick(t, EXPS)
    if k:
        return _fz_open(k, st, kind)
    n = re.search(r"(\d+)\s*(?:numara|nolu|numaralı|\.)\s*deney|deney\s*(\d+)", t)
    if n:
        i = int(n.group(1) or n.group(2))
        if 1 <= i <= len(keys):
            return _fz_open(keys[i - 1], st, kind)
    # --- kavram
    for title, pat, text_ in CONC:
        if re.search(pat, t) and re.search(r"nedir|ne demek|açıkla|anlat|hakkında|bilgi|nasıl|yasa", t):
            return {"do": {"tab": "info", "concept": title}, "say": __import__("lab_concepts").short_say(title, text_)}
    return {"say": f"{LAB_NAME[kind]} laboratuvarındayım efendim. {LAB_HINT[kind]}"}


def _fz_pick(t, exps=None):
    for e in (exps or D.FIZ_EXPS):
        if re.search(e["alias"], t):
            return e["key"]
    return None


def _fz_open(k, st, kind="fizik"):
    st["exp"] = k
    st["params"] = fz_defaults(k)
    e = FZ[k]
    lines, say = fz_results(k, st["params"])
    pnames = ", ".join(p[1].lower() for p in e["params"])
    return {"do": {"tab": "exp", "exp": k, "set": dict(st["params"]), "result": {"title": e["name"], "lines": lines}},
            "say": f"{e['name']}. {e['aim']} {say} Ayarlanabilir değerler: {pnames}. Bir değeri \"X yap\" diyerek değiştirebilirsiniz. Formülleri ya da nedenini de sorabilirsiniz."}


def _fz_params(key, t, P):
    changed = []
    # gezegen ön ayarı
    if "g" in P and re.search(r"(?:de|da|te|ta|için|gibi|yüzeyinde)\b|yerçekimi", t):
        for _, gv, pat in GRAV:
            if re.search(pat, t) and re.search(r"yerçekimi|yap|olsun|ayarla|deneyi|dene|taşı|\bde\b|\bda\b", t):
                P["g"] = gv
                changed.append("g")
                break
    if key == "ohm":
        if re.search(r"paralel", t) and re.search(r"bağla|yap|olsun|geç|çevir|devre", t):
            P["p"] = 1
            changed.append("p")
        elif re.search(r"\bseri\b", t) and re.search(r"bağla|yap|olsun|geç|çevir|devre", t):
            P["p"] = 0
            changed.append("p")
    pdef = {p[0]: p for p in FZ[key]["params"]}
    used = set()

    def grab(pk, pat):
        m = (re.search(r"(?:" + pat + r")\s*(?:i |ı |u |ü |yi |yı |yu |yü )?(?:=|:)?\s*(-?\d+(?:[.,]\d+)?)", t)
             or re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:derece|metre|m/s|kg|kilo|volt|ohm|hz|hertz|cm|n/m|newton)?\s*(?:" + pat + r")", t))
        if not m or m.start(1) in used:
            return
        used.add(m.start(1))
        lo, hi = pdef[pk][3], pdef[pk][4]
        P[pk] = max(lo, min(hi, float(m.group(1).replace(",", "."))))
        changed.append(pk)

    for tbl in (PARAM_PAT, PARAM_GEN):
        for pk in pdef:
            if pk not in changed and (key, pk) in tbl:
                grab(pk, tbl[(key, pk)])
    return changed


# ============================================================== MATEMATİK
SH = {s["key"]: s for s in D.SHAPES}
SH_PARAM_PAT = {"a": r"kenar\w*|uzunluk\w*", "b": r"genişlik\w*|en\b", "c": r"yükseklik\w*|boy\b", "h": r"yükseklik\w*|boy\b", "r": r"yarıçap\w*|r\b", "R": r"büyük yarıçap\w*"}


def sh_values(key, p):
    """(hacim, yüzey alanı, yardımcı satırlar)"""
    pi = math.pi
    if key == "kup":
        a = p["a"]
        return a ** 3, 6 * a * a, [f"Cisim köşegeni: {fmt(a * math.sqrt(3), False)}"]
    if key == "prizma":
        a, b, c = p["a"], p["b"], p["c"]
        return a * b * c, 2 * (a * b + b * c + a * c), [f"Cisim köşegeni: {fmt(math.sqrt(a * a + b * b + c * c), False)}"]
    if key == "piramit":
        a, h = p["a"], p["h"]
        l = math.sqrt(h * h + (a / 2) ** 2)
        return a * a * h / 3, a * a + 2 * a * l, [f"Yan yüz yüksekliği: {fmt(l, False)}"]
    if key == "silindir":
        r, h = p["r"], p["h"]
        return pi * r * r * h, 2 * pi * r * (r + h), [f"Yanal alan: {fmt(2 * pi * r * h, False)}"]
    if key == "koni":
        r, h = p["r"], p["h"]
        l = math.sqrt(r * r + h * h)
        return pi * r * r * h / 3, pi * r * (r + l), [f"Ana doğru uzunluğu: {fmt(l, False)}"]
    if key == "kure":
        r = p["r"]
        return 4 * pi * r ** 3 / 3, 4 * pi * r * r, []
    if key == "tetra":
        a = p["a"]
        return a ** 3 * math.sqrt(2) / 12, math.sqrt(3) * a * a, [f"Yükseklik: {fmt(a * math.sqrt(2 / 3), False)}"]
    if key == "okta":
        a = p["a"]
        return a ** 3 * math.sqrt(2) / 3, 2 * math.sqrt(3) * a * a, []
    if key == "simit":
        R, r = p["R"], p["r"]
        return 2 * pi * pi * R * r * r, 4 * pi * pi * R * r, []
    raise KeyError(key)


def sh_defaults(key):
    return {p[0]: float(p[2]) for p in SH[key]["params"]}


def sh_card(key, p):
    s = SH[key]
    V, A, extra = sh_values(key, p)
    lines = [f"Hacim = {s['V']} = {fmt(V, False)} birimküp", f"Yüzey alanı = {s['A']} = {fmt(A, False)} birimkare"] + extra + [s["info"]]
    if s["counts"]:
        v, e, f = s["counts"]
        lines.append(f"Euler: köşe − ayrıt + yüz = {v} − {e} + {f} = {v - e + f}")
    return {"title": s["name"] + " · " + ", ".join(f"{pp[1]} {fmt(p[pp[0]], False)}" for pp in s["params"]), "lines": lines}, V, A


def sh_pick(t):
    for s in D.SHAPES:
        if re.search(s["alias"], t):
            return s["key"]
    return None


def sh_params(key, t, base):
    """Cümledeki sayıları cismin parametrelerine yerleştirir (adı geçenler önce, kalanlar sırayla)."""
    p = dict(base)
    plist = D.SHAPES[[s["key"] for s in D.SHAPES].index(key)]["params"]
    used = set()
    for pk, label, _ in plist:
        pat = {"a": r"kenar\w*|taban\w*|uzunluk\w*", "b": r"genişlik\w*|\ben\b", "c": r"yükseklik\w*|boy\b", "h": r"yükseklik\w*|boy\b|irtifa", "r": r"yarıçap\w*|\br\b|küçük yarıçap\w*", "R": r"büyük yarıçap\w*"}.get(pk, label)
        m = re.search(r"(?:" + pat + r")\s*(?:i |ı |u |ü )?(?:=|:)?\s*(\d+(?:[.,]\d+)?)", t) or re.search(r"(\d+(?:[.,]\d+)?)\s*(?:birim|cm|m|metre|santim)?\s*(?:" + pat + r")", t)
        if m and m.start(1) not in used:
            p[pk] = float(m.group(1).replace(",", "."))
            used.add(m.start(1))
    if not used:
        nums = [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", t)]
        for (pk, _, _), v in zip(plist, nums):
            p[pk] = v
    return {k: max(0.1, min(1000, v)) for k, v in p.items()}


def _poly_coeffs(expr: str, var: str = "x", maxdeg: int = 6):
    """İfade x'in polinomu ise katsayılar (yüksekten düşüğe), değilse None."""
    f = f_of(expr)
    xs = np.arange(-3, 4, dtype=float) + 0.0
    ys = np.array([f(float(x)) for x in xs])
    if not np.all(np.isfinite(ys)):
        return None
    c = np.polyfit(xs, ys, maxdeg)
    c = np.where(np.abs(c) < 1e-7, 0, c)
    chk = [0.37, -4.3, 5.9, 1.77]
    for x in chk:
        v = f(x)
        if not math.isfinite(v) or abs(np.polyval(c, x) - v) > 1e-6 * (1 + abs(v)):
            return None
    c = np.trim_zeros(np.round(c, 8), "f")
    return list(c) if len(c) else [0.0]


def poly_str(c):
    deg = len(c) - 1
    parts = []
    for i, a in enumerate(c):
        p = deg - i
        if abs(a) < 1e-9:
            continue
        a_ = abs(a)
        coef = "" if (abs(a_ - 1) < 1e-9 and p > 0) else fmt(a_, False)
        term = coef + ("x" if p >= 1 else "") + (f"^{p}" if p > 1 else "")
        if not term:
            term = "1"
        parts.append(("- " if a < 0 else "+ ") + term)
    s = " ".join(parts).strip() or "0"
    return s[2:] if s.startswith("+ ") else ("-" + s[2:] if s.startswith("- ") else s)


def roots_numeric(f, lo=-30.0, hi=30.0, n=6000, limit=8):
    xs = np.linspace(lo, hi, n)
    ys = [f(float(x)) for x in xs]
    out = []
    for i in range(n - 1):
        a, b = ys[i], ys[i + 1]
        if not (math.isfinite(a) and math.isfinite(b)):
            continue
        if a == 0:
            out.append(float(xs[i]))
        elif a * b < 0 and abs(a - b) < 1e3:
            l, r = float(xs[i]), float(xs[i + 1])
            for _ in range(60):
                m = (l + r) / 2
                fm = f(m)
                if (f(l) < 0) == (fm < 0):
                    l = m
                else:
                    r = m
            if abs(f((l + r) / 2)) < 1e-4:
                out.append((l + r) / 2)
    ded = []
    for x in out:
        if not ded or abs(x - ded[-1]) > 1e-3:
            ded.append(x)
    if len(ded) > limit:                              # sıfıra en yakın olanlar
        ded = sorted(sorted(ded, key=abs)[:limit])
    return ded


def _expr_from(text: str) -> str:
    return speech_to_expr(text)


def solve_text(t_raw: str):
    """'x kare eksi 5x artı 6 eşittir 0 çöz' -> (kart, söz)."""
    low = t_raw.replace("İ", "i").replace("I", "ı").lower()
    conv = [_expr_from(c) for c in re.split(r"\s+ve\s+|;", low) if c.strip()]
    eqs = [e for e in conv if "=" in e]
    if len(eqs) >= 2 and any("y" in e for e in eqs):
        return solve_system(eqs[:2])
    s = " ".join(conv)
    if "=" not in s:
        s += " = 0"
    if s.count("=") != 1:
        raise MathErr("tek eşitlik gerekli")
    lhs, rhs = [x.strip() for x in s.split("=")]
    expr = f"({lhs}) - ({rhs or '0'})"
    parse(expr)
    c = _poly_coeffs(expr)
    show = f"{lhs} = {rhs}"
    if c is not None and len(c) >= 2:
        deg = len(c) - 1
        if deg == 1:
            a, b = c
            x = -b / a
            return ({"title": "Birinci derece denklem", "lines": [f"{poly_str(c)} = 0", f"x = −({fmt(b, False)}) / {fmt(a, False)}", f"x = {fmt(x, False)}"], "roots": [x], "graph": poly_str(c)},
                    f"Denklemin çözümü x eşittir {fmt(x)}.")
        if deg == 2:
            a, b, cc = c
            dl = b * b - 4 * a * cc
            lines = [f"{poly_str(c)} = 0", f"a = {fmt(a, False)}, b = {fmt(b, False)}, c = {fmt(cc, False)}", f"Δ = b² − 4ac = {fmt(b * b, False)} − {fmt(4 * a * cc, False)} = {fmt(dl, False)}"]
            if dl > 1e-12:
                x1, x2 = (-b - math.sqrt(dl)) / (2 * a), (-b + math.sqrt(dl)) / (2 * a)
                lines += ["Δ > 0: iki farklı gerçek kök", f"x₁ = {fmt(x1, False)}, x₂ = {fmt(x2, False)}"]
                return {"title": "İkinci derece denklem", "lines": lines, "roots": [x1, x2], "graph": poly_str(c)}, f"Delta {fmt(dl)}, pozitif. İki kök var: x bir eşittir {fmt(x1)}, x iki eşittir {fmt(x2)}."
            if abs(dl) <= 1e-12:
                x1 = -b / (2 * a)
                lines += ["Δ = 0: çakışık tek kök", f"x = {fmt(x1, False)}"]
                return {"title": "İkinci derece denklem", "lines": lines, "roots": [x1], "graph": poly_str(c)}, f"Delta sıfır, tek kök var: x eşittir {fmt(x1)}."
            re_, im = -b / (2 * a), math.sqrt(-dl) / (2 * abs(a))
            lines += ["Δ < 0: gerçek kök yok", f"Karmaşık kökler: {fmt(re_, False)} ± {fmt(im, False)}i"]
            return {"title": "İkinci derece denklem", "lines": lines, "roots": [], "graph": poly_str(c)}, f"Delta negatif, gerçek kök yok. Karmaşık kökler {fmt(re_)} artı eksi {fmt(im)} i."
        r = np.roots(c)
        real = sorted(float(z.real) for z in r if abs(z.imag) < 1e-7)
        cplx = [z for z in r if abs(z.imag) >= 1e-7]
        lines = [f"{poly_str(c)} = 0 ({deg}. derece)", "Gerçek kökler: " + (", ".join(fmt(x, False) for x in real) if real else "yok")]
        if cplx:
            lines.append(f"{len(cplx)} karmaşık kök de var.")
        return {"title": f"{deg}. derece denklem", "lines": lines, "roots": real, "graph": poly_str(c)}, ("Gerçek kökler: " + ", ".join(fmt(x) for x in real) + "." if real else "Gerçek kök yok.")
    f = f_of(expr)
    rts = roots_numeric(f)
    if not rts:
        return ({"title": "Denklem", "lines": [show, "−30 ile 30 arasında çözüm bulunamadı."], "roots": []}, "Bu aralıkta bir çözüm bulamadım efendim.")
    return ({"title": "Denklem (sayısal çözüm)", "lines": [show] + [f"x ≈ {fmt(x, False)}" for x in rts], "roots": rts, "graph": expr},
            "Çözümler yaklaşık: " + ", ".join(fmt(x) for x in rts) + ".")


def solve_system(eqs):
    rows = []
    for e in eqs:
        lhs, rhs = [x.strip() for x in e.split("=")]
        ex = f"({lhs}) - ({rhs or '0'})"
        parse(ex)
        f = f_of(ex)
        c0, cx, cy = f(0, 0), f(1, 0) - f(0, 0), f(0, 1) - f(0, 0)
        for p in [(2.5, -1.5), (-3, 4)]:
            if abs(f(*p) - (c0 + cx * p[0] + cy * p[1])) > 1e-7:
                raise MathErr("denklemler doğrusal olmalı")
        rows.append((cx, cy, -c0))
    (a1, b1, k1), (a2, b2, k2) = rows
    det = a1 * b2 - a2 * b1
    def lin(a, b, k):
        return f"{fmt(a, False)}x {'+' if b >= 0 else '−'} {fmt(abs(b), False)}y = {fmt(k, False)}"
    lines = [lin(a1, b1, k1), lin(a2, b2, k2), f"Determinant = {fmt(det, False)}"]
    if abs(det) < 1e-12:
        same = abs(a1 * k2 - a2 * k1) < 1e-9 and abs(b1 * k2 - b2 * k1) < 1e-9
        lines.append("Sonsuz çözüm var (doğrular çakışık)." if same else "Çözüm yok (doğrular paralel).")
        return {"title": "Denklem sistemi", "lines": lines}, ("Sonsuz çözüm var." if same else "Çözüm yok, doğrular paralel.")
    x, y = (k1 * b2 - k2 * b1) / det, (a1 * k2 - a2 * k1) / det
    lines += [f"x = {fmt(x, False)}", f"y = {fmt(y, False)}"]
    return {"title": "Denklem sistemi", "lines": lines}, f"Çözüm: x eşittir {fmt(x)}, y eşittir {fmt(y)}."


def _factor(n: int):
    out, d = [], 2
    while d * d <= n:
        while n % d == 0:
            out.append(d)
            n //= d
        d += 1
    if n > 1:
        out.append(n)
    return out


def _ints(t, k=None):
    xs = [int(x) for x in re.findall(r"\d+", t)]
    return xs if k is None else xs[:k]


def calc_text(t_raw: str, t: str):
    """(kart, söz) ya da None: temel hesaplar, sayı teorisi, kombinatorik, yüzde, türev ve integral."""
    n = _ints(t)
    if re.search(r"faktöriyel", t) and n:
        if n[0] > 170:
            return {"title": "Faktöriyel", "lines": ["Sayı çok büyük (en çok 170)."]}, "Bu sayı çok büyük efendim, en çok 170 faktöriyel hesaplayabilirim."
        v = math.factorial(n[0])
        return {"title": f"{n[0]}!", "lines": [f"{n[0]}! = {v if v < 10**15 else f'{v:.6e}'}"]}, f"{n[0]} faktöriyel {v if v < 10**15 else 'yaklaşık ' + f'{float(v):.4g}'.replace('.', ',')}."
    if re.search(r"asal çarpan|çarpanlarına ayır", t) and n and 1 < n[0] < 10**12:
        f = _factor(n[0])
        from collections import Counter
        cnt = Counter(f)
        s = " × ".join(f"{p}" + (f"^{e}" if e > 1 else "") for p, e in sorted(cnt.items()))
        return {"title": f"{n[0]} asal çarpanları", "lines": [f"{n[0]} = {s}"]}, f"{n[0]} sayısının asal çarpanları: " + ", ".join(f"{p}" + (f" üzeri {e}" if e > 1 else "") for p, e in sorted(cnt.items())) + "."
    if re.search(r"asal mı|asal sayı mı|asal mıdır", t) and n and n[0] < 10**12:
        pr = n[0] > 1 and len(_factor(n[0])) == 1
        return {"title": f"{n[0]} asal mı?", "lines": [f"{n[0]} " + ("asaldır." if pr else f"asal değildir ({' × '.join(map(str, _factor(n[0])))}).")]}, f"{n[0]} {'asal bir sayıdır' if pr else 'asal değildir'}."
    if re.search(r"ebob|ekok|obeb|okek", t) and len(n) >= 2:
        g = math.gcd(*n[:4])
        l = math.lcm(*n[:4])
        nums = " ve ".join(map(str, n[:4]))
        want_g, want_l = bool(re.search(r"ebob|obeb", t)), bool(re.search(r"ekok|okek", t))
        lines, say = [], []
        if want_g or not want_l:
            lines.append(f"EBOB({', '.join(map(str, n[:4]))}) = {g}")
            say.append(f"EBOB {g}")
        if want_l or not want_g:
            lines.append(f"EKOK({', '.join(map(str, n[:4]))}) = {l}")
            say.append(f"EKOK {l}")
        return {"title": "EBOB / EKOK", "lines": lines}, f"{nums} için " + ", ".join(say) + "."
    if re.search(r"kombinasyon", t) and len(n) >= 2 and n[0] <= 1000:
        a, b = (max(n[:2]), min(n[:2]))
        v = math.comb(a, b)
        return {"title": f"C({a},{b})", "lines": [f"C({a},{b}) = {a}! / ({b}!·{a - b}!) = {v}"]}, f"{a}'in {b}'li kombinasyonu {v}."
    if re.search(r"permütasyon", t) and len(n) >= 2 and n[0] <= 1000:
        a, b = (max(n[:2]), min(n[:2]))
        v = math.perm(a, b)
        return {"title": f"P({a},{b})", "lines": [f"P({a},{b}) = {a}! / {a - b}! = {v}"]}, f"{a}'in {b}'li permütasyonu {v}."
    if re.search(r"yüzde|%", t):
        nums = [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", t)]
        if len(nums) >= 2:
            m = re.search(r"yüzde\s*(\d+(?:[.,]\d+)?)|%\s*(\d+(?:[.,]\d+)?)", t)
            if m:
                pct = float((m.group(1) or m.group(2)).replace(",", "."))
                rest = list(nums)
                rest.remove(pct)
                base = rest[0]
            else:                                   # '15 yüzdesi 240'
                pct, base = nums[0], nums[1]
            v = base * pct / 100
            return {"title": "Yüzde", "lines": [f"{fmt(base, False)} sayısının %{fmt(pct, False)}'i = {fmt(v, False)}"]}, f"{fmt(base)} sayısının yüzde {fmt(pct)} kadarı {fmt(v)}."
    if re.search(r"türev|integral", t):
        body = re.sub(r"\b(türevi|türev|integrali|integral|nedir|bul|hesapla|alın|al|fonksiyon\w*|in|ın|un|ün|nin|nın)\b", " ", t)
        expr = _expr_from(body)
        c = _poly_coeffs(expr) if expr.strip() else None
        if c is None:
            return {"title": "Türev / integral", "lines": ["Yalnızca polinomların (örneğin 3x kare artı 2x eksi 5) türev ve integralini alabiliyorum."]}, "Şimdilik yalnızca polinomların türev ve integralini alabiliyorum efendim."
        if re.search(r"türev", t):
            d = [a * (len(c) - 1 - i) for i, a in enumerate(c[:-1])] or [0.0]
            return {"title": "Türev", "lines": [f"f(x) = {poly_str(c)}", f"f'(x) = {poly_str(d)}"], "graph": [poly_str(c), poly_str(d)]}, f"Türev: {poly_str(d).replace('^', ' üzeri ')}."
        ig = [a / (len(c) - i) for i, a in enumerate(c)] + [0.0]
        return {"title": "İntegral", "lines": [f"f(x) = {poly_str(c)}", f"∫f(x)dx = {poly_str(ig)} + C"]}, f"İntegral: {poly_str(ig).replace('^', ' üzeri ')} artı C."
    return None


def arith(t_raw: str):
    """Düz aritmetik: '12 çarpı 7 artı 3', 'karekök 144', '2 üzeri 10' -> (kart, söz) ya da None."""
    s = _expr_from(t_raw)
    s = re.sub(r"\b(kaç\w*|eder|nedir|hesapla|sonucu|sonuç|eşittir|yap)\b", " ", s)
    s = re.sub(r"=\s*$", "", s).strip()
    if not s or not re.search(r"\d|pi", s) or re.search(r"\bx\b|\by\b", s):
        return None
    if not re.search(r"[+\-*/^]|sqrt|sin|cos|tan|log|ln|abs|\(", s):
        return None
    try:
        v = evaluate(s)
    except (MathErr, TypeError):
        return None
    if isinstance(v, complex):
        return None
    return {"title": "Hesap", "lines": [f"{s} = {fmt(v, False)}"]}, f"Sonuç {fmt(v)}."


def trig_values(deg: float):
    r = math.radians(deg)
    s, c = math.sin(r), math.cos(r)
    tn = math.tan(r) if abs(c) > 1e-9 else float("inf")
    return s, c, tn


SPECIAL = {0: ("0", "1", "0"), 30: ("1/2", "√3/2", "√3/3"), 45: ("√2/2", "√2/2", "1"), 60: ("√3/2", "1/2", "√3"), 90: ("1", "0", "tanımsız"),
           120: ("√3/2", "−1/2", "−√3"), 135: ("√2/2", "−√2/2", "−1"), 150: ("1/2", "−√3/2", "−√3/3"), 180: ("0", "−1", "0"), 270: ("−1", "0", "tanımsız"), 360: ("0", "1", "0")}


def circle_card(deg: float):
    d = deg % 360 if deg >= 0 else deg % 360
    s, c, tn = trig_values(d)
    sp = SPECIAL.get(int(round(d)) if abs(d - round(d)) < 1e-9 else -1)
    lines = [f"Açı = {fmt(d, False)}° = {fmt(math.radians(d), False)} rad", f"sin = {fmt(s, False)}" + (f"  ({sp[0]})" if sp else ""), f"cos = {fmt(c, False)}" + (f"  ({sp[1]})" if sp else ""),
             "tan = " + (fmt(tn, False) if math.isfinite(tn) and abs(tn) < 1e9 else "tanımsız") + (f"  ({sp[2]})" if sp else "")]
    say = f"{fmt(d)} derecede sinüs {fmt(s)}, kosinüs {fmt(c)}, tanjant {fmt(tn) if math.isfinite(tn) and abs(tn) < 1e9 else 'tanımsız'}."
    return {"title": "Birim çember", "lines": lines}, say


def matematik_init():
    return {"shapes": [{"key": s["key"], "name": s["name"], "params": [list(p) for p in s["params"]], "V": s["V"], "A": s["A"], "info": s["info"]} for s in D.SHAPES],
            "concepts": [{"title": t, "text": x} for t, _, x in D.MATH_CONCEPTS],
            "examples": ["x kare eksi 4", "sinüs x", "x küp eksi 3 x", "2 üzeri x", "karekök x", "1 bölü x"]}


MAT_TABS = [("graph", r"grafik\w* (?:sekmesi|ekranı)|grafik modu"), ("solve", r"denklem sekmesi"), ("shape", r"cisimler|geometrik cisim|3b cisim|üç boyutlu"),
            ("circle", r"birim çember|trigonometri sekmesi"), ("calc", r"hesap sekmesi|hesap makinesi|hesaplayıcı"), ("info", r"kavramlar|konu anlatım")]


def matematik(text: str, st: dict):
    t = _norm(text)
    raw = text
    import lab_concepts as _K
    d = _K.find_detail([(a, b, c) for a, b, c in D.MATH_CONCEPTS], t)
    if d:
        return {"do": {"tab": "info", "concept": d[0]}, "say": _K.short_say(*d)}
    try:
        return _matematik(t, raw, st)
    except MathErr as e:
        return {"say": f"Bu ifadeyi anlayamadım efendim: {e}. Örneğin x kare eksi dört ya da sinüs x deyin."}


def _matematik(t, raw, st):
    tn = _numwords(t)
    for key, pat in MAT_TABS:
        if re.search(pat, t):
            names = {"graph": "Grafik ekranı efendim. Bir fonksiyon söyleyin: x kare eksi dört çiz.", "solve": "Denklem çözücü efendim. Örneğin x kare eksi beş x artı altı eşittir sıfır çöz.",
                     "shape": "Üç boyutlu cisimler efendim. Küp, silindir, küre gibi bir ad söyleyin.", "circle": "Birim çember efendim. Bir açı söyleyin, örneğin otuz derece.",
                     "calc": "Hesap ekranı efendim. İşlem söyleyin: 12 çarpı 7, 10 faktöriyel, 360 asal çarpanlar, 48 ve 36 ebob.", "info": "Kavramlar efendim. Pisagor, türev, olasılık gibi birini sorun."}
            return {"do": {"tab": key}, "say": names[key]}
    # --- grafik
    if re.search(r"\b(temizle|sil|kaldır)\b", t) and re.search(r"grafi|fonksiyon|hepsi|ekran", t):
        st["fns"] = []
        return {"do": {"tab": "graph", "fns": [], "reset": True}, "say": "Grafikleri temizledim efendim."}
    if re.search(r"yakınlaş|büyüt|zoom", t) and st.get("tab") == "graph":
        return {"do": {"zoom": 0.6}, "say": "Yakınlaştım efendim."}
    if re.search(r"uzaklaş|küçült", t) and st.get("tab") == "graph":
        return {"do": {"zoom": 1.6}, "say": "Uzaklaştım efendim."}
    if re.search(r"çiz|grafi|plot|fonksiyon", t) and not re.search(r"çöz|türev|integral|kombinasyon", t):
        body = re.sub(r"\b(grafiği|grafiğini|grafik|çizdir\w*|çiz\w*|fonksiyon\w*|ekle|göster|f\s*\(\s*x\s*\)|y\s*=)\b", " ", tn)
        body = re.sub(r"\by\s*=", " ", body)
        parts = [p for p in re.split(r"\s+ve\s+|\s+ile\s+|;|,", body) if p.strip()]
        exprs = []
        for p in parts[:4]:
            e = _expr_from(p)
            e = re.sub(r"^(y|f\(x\))\s*=\s*", "", e).strip()
            if not e:
                continue
            parse(e)
            exprs.append(e)
        if exprs:
            fns = (st.get("fns", []) if re.search(r"\bekle\b|bir de|üstüne", t) else []) + exprs
            fns = fns[-5:]
            st["fns"] = fns
            f = f_of(exprs[0])
            r = roots_numeric(f, -12.0, 12.0, 4000, 7)
            c = _poly_coeffs(exprs[0])
            lines = [f"y = {poly_str(c) if c else exprs[0]}"]
            if c and len(c) == 3:
                a, b, _ = c
                vx = -b / (2 * a)
                lines.append(f"Tepe noktası: ({fmt(vx, False)}, {fmt(f(vx), False)})")
            lines.append("Kökler (x eksenini kestiği yerler): " + (", ".join(fmt(x, False) for x in r) if r else "yok"))
            y0 = f(0.0)
            if math.isfinite(y0):
                lines.append(f"y eksenini kestiği nokta: {fmt(y0, False)}")
            st["tab"] = "graph"
            say = "Grafiği çizdim efendim. " + ("Kökleri: " + ", ".join(fmt(x) for x in r) + "." if r else "x eksenini kesmiyor.")
            return {"do": {"tab": "graph", "fns": fns, "result": {"title": "Grafik analizi", "lines": lines}}, "say": say}
    # --- denklem
    if re.search(r"çöz|denklem|kökleri|kökü", t) or ("=" in t and re.search(r"\bx\b", t)) or re.search(r"eşittir", t):
        card, say = solve_text(raw)
        d = {"tab": "solve", "result": {"title": card["title"], "lines": card["lines"]}}
        if card.get("graph"):
            d["fns"] = [card["graph"]]
        return {"do": d, "say": say}
    # --- cisimler
    k = sh_pick(t)
    if k and (re.search(r"hacim|alan|göster|aç|çiz|cisim|yüzey|model|modeli|yarıçap|kenar|yükseklik|\d", t) or re.fullmatch(r"(?:bir )?" + SH[k]["alias"] + r"\w*", t)):
        p = sh_params(k, tn, sh_defaults(k))
        st["shape"], st["sp"] = k, p
        card, V, A = sh_card(k, p)
        want_v, want_a = bool(re.search(r"hacim", t)), bool(re.search(r"alan|yüzey", t))
        s = SH[k]
        pre = ", ".join(f"{pp[1]} {fmt(p[pp[0]])}" for pp in s["params"])
        if want_v and not want_a:
            say = f"{s['name']}, {pre}. Hacmi {fmt(V)} birimküp."
        elif want_a and not want_v:
            say = f"{s['name']}, {pre}. Yüzey alanı {fmt(A)} birimkare."
        else:
            say = f"{s['name']}, {pre}. Hacmi {fmt(V)} birimküp, yüzey alanı {fmt(A)} birimkare. {s['info']}"
        return {"do": {"tab": "shape", "shape": k, "set": p, "result": card}, "say": say}
    if st.get("shape") and re.search(r"hacim|yüzey alan", t) and re.search(r"\d", t):
        p = sh_params(st["shape"], tn, st.get("sp") or sh_defaults(st["shape"]))
        st["sp"] = p
        card, V, A = sh_card(st["shape"], p)
        return {"do": {"tab": "shape", "shape": st["shape"], "set": p, "result": card}, "say": f"Hacim {fmt(V)} birimküp, yüzey alanı {fmt(A)} birimkare."}
    if st.get("shape") and re.search(r"hacim|yüzey alan", t):
        card, V, A = sh_card(st["shape"], st.get("sp") or sh_defaults(st["shape"]))
        return {"do": {"result": card}, "say": f"Hacim {fmt(V)} birimküp, yüzey alanı {fmt(A)} birimkare."}
    # --- trigonometri
    mm = re.search(r"(\d+(?:[.,]\d+)?)\s*(derece|°|radyan|pi)", tn)
    if mm and not re.search(r"\bx\b", t) and (re.search(r"sinüs|kosinüs|tanjant|sin\b|cos\b|tan\b|birim çember|açı", t) or re.fullmatch(r"[\d.,]+ (?:derece|radyan)", tn)):
        v = float(mm.group(1).replace(",", "."))
        deg = math.degrees(v) if mm.group(2) == "radyan" else v * 180 if mm.group(2) == "pi" else v
        card, say = circle_card(deg)
        return {"do": {"tab": "circle", "angle": deg % 360, "result": card}, "say": say}
    if st.get("tab") == "circle" and re.search(r"\b(derece|açı)\b", t) and _num(tn) is not None:
        deg = _num(tn)
        card, say = circle_card(deg)
        return {"do": {"tab": "circle", "angle": deg % 360, "result": card}, "say": say}
    # --- hesap
    c = calc_text(raw, tn)
    if c:
        card = {"title": c[0]["title"], "lines": c[0]["lines"]}
        if c[0].get("graph"):
            return {"do": {"tab": "graph", "fns": c[0]["graph"], "result": card}, "say": c[1]}
        return {"do": {"tab": "calc", "result": card}, "say": c[1]}
    a = arith(raw)
    if a:
        return {"do": {"tab": "calc", "result": a[0]}, "say": a[1]}
    # --- kavram
    for title, pat, text_ in D.MATH_CONCEPTS:
        if re.search(pat, t) and re.search(r"nedir|ne demek|açıkla|anlat|hakkında|bilgi|nasıl|teorem", t):
            return {"do": {"tab": "info", "concept": title}, "say": __import__("lab_concepts").short_say(title, text_)}
    return {"say": "Matematik laboratuvarındayım efendim. Grafik için x kare eksi dört çiz, denklem için çöz, cisim için küre ya da silindir, açı için otuz derece sinüs, işlem için on faktöriyel diyebilirsiniz."}


# ============================================================== kaydırıcılardan gelen anlık hesap (konuşmasız)
def sci_param(kind: str, d: dict):
    """Arayüzdeki kaydırıcı değişince sonuç kartını yeniler. Dönen: {'result': {...}} ya da None."""
    def clean(vals, defs):
        out = {}
        for pk, _, _, lo, hi, dv, _ in defs:
            try:
                v = float(vals.get(pk, dv))
            except (TypeError, ValueError):
                v = float(dv)
            out[pk] = max(lo, min(hi, v))
        return out

    if kind == "gokyuzu":
        try:
            ts = float(d.get("ts") or 0) or None
        except (TypeError, ValueError):
            ts = None
        return {"sky": sky_snapshot(ts)}
    if kind in CAT and d.get("exp") in FZ and isinstance(d.get("params"), dict):
        e = FZ[d["exp"]]
        p = clean(d["params"], e["params"])
        lines, _ = fz_results(d["exp"], p)
        return {"result": {"title": e["name"], "lines": lines}}
    if kind == "matematik" and d.get("shape") in SH and isinstance(d.get("params"), dict):
        s = SH[d["shape"]]
        p = {k: max(0.1, min(1000.0, float(d["params"].get(k, dv)))) for k, _, dv in s["params"]}
        card, _, _ = sh_card(d["shape"], p)
        return {"result": card}
    if kind == "matematik" and d.get("angle") is not None:
        try:
            deg = float(d["angle"])
        except (TypeError, ValueError):
            return None
        card, _ = circle_card(deg)
        return {"result": card}
    return None


# ============================================================== GÖKYÜZÜ HARİTASI
import sky_data as SK  # noqa: E402


def _sky_loc():
    """(ad, enlem, boylam): ayardaki şehir; bulunamazsa İstanbul."""
    try:
        import extras
        return extras._locate()
    except Exception:
        return ("İstanbul", 41.01, 28.98)


def gokyuzu_init():
    name, lat, lon = _sky_loc()
    return {"stars": {k: [v[0], v[1], v[2], v[3], v[4]] for k, v in SK.STARS.items()},
            "cons": {k: {"name": v[0], "lines": v[1], "lore": __import__("sky_lore").CONLORE.get(k, [])} for k, v in SK.CONSTELLATIONS.items()},
            "facts": __import__("sky_lore").STARFACT, "place": name, "lat": lat, "lon": lon}


def sky_snapshot(ts=None, lat=None, lon=None):
    """Güneş, Ay ve gezegenlerin verilen andaki konumları (sayfa isterse tekrar sorar)."""
    import datetime as dt
    import astro
    if lat is None:
        _, lat, lon = _sky_loc()
    t = dt.datetime.fromtimestamp(ts, dt.timezone.utc) if ts else dt.datetime.now(dt.timezone.utc)
    objs, L, j = astro.snapshot(t, lat, lon)
    for o in objs:
        if o["name"] == "Ay":
            o["phase_name"] = astro.phase_name(o["elong"])
    return objs


def _alt_text(o):
    a = o["alt"]
    if a < -0.8:
        return "ufkun altında, şu an görünmüyor"
    dirs = ["kuzey", "kuzeydoğu", "doğu", "güneydoğu", "güney", "güneybatı", "batı", "kuzeybatı"]
    d = dirs[int(((o["az"] + 22.5) % 360) // 45)]
    h = "ufka çok yakın" if a < 10 else "alçakta" if a < 30 else "gökyüzünde yüksekte" if a < 60 else "neredeyse tepenizde"
    return f"{d} yönünde, {fmt(a)} derece yükseklikte ({h})"


def gokyuzu(text: str, st: dict):
    import datetime as dt
    t = _norm(text)
    now_ts = st.get("ts") or None
    objs = None

    def snap():
        nonlocal objs
        if objs is None:
            objs = sky_snapshot(now_ts)
        return objs
    # zaman kontrolü
    m = re.search(r"(\d+|bir|iki|üç|dört|beş|altı|on|yirmi)?\s*(saat|gün|hafta|dakika)\s*(ileri|sonra|geri|önce)", _numwords(t))
    if m:
        n = float(m.group(1)) if (m.group(1) or "").isdigit() else 1.0
        unit = {"saat": 3600, "gün": 86400, "hafta": 604800, "dakika": 60}[m.group(2)]
        sign = 1 if m.group(3) in ("ileri", "sonra") else -1
        base = st.get("ts") or dt.datetime.now(dt.timezone.utc).timestamp()
        st["ts"] = base + sign * n * unit
        return {"do": {"ts": st["ts"]}, "say": f"Gökyüzü {fmt(n)} {m.group(2)} {'ileri' if sign > 0 else 'geri'} alındı efendim."}
    raw_l = text.replace("İ", "i").replace("I", "ı").lower()
    if re.search(r"\b(şimdi|şu an|bu an|gerçek zaman|normale)\b", raw_l) and re.search(r"göster|dön|al|ayarla|zaman|saat|gökyüzü", raw_l):
        st["ts"] = None
        return {"do": {"ts": 0}, "say": "Gökyüzü şu ana döndü efendim."}
    if re.search(r"\b(gece yarısı|gece)\b", t) and re.search(r"göster|git|al|ayarla", t):
        d = dt.datetime.now().replace(hour=23, minute=0, second=0, microsecond=0)
        st["ts"] = d.timestamp()
        return {"do": {"ts": st["ts"]}, "say": "Bu gece saat yirmi üç için gökyüzünü gösteriyorum efendim."}
    if re.search(r"takımyıldız\w* (çiz|çizgi\w*|göster|aç)|çizgileri (göster|aç)", t):
        return {"do": {"lines": True}, "say": "Takımyıldızı çizgilerini açtım efendim."}
    if re.search(r"(çizgileri|takımyıldız\w*|etiket\w*|isimleri) (gizle|kapat|kaldır)", t):
        return {"do": {"lines": False}, "say": "Çizgileri kapattım efendim."}
    if re.search(r"(isim|etiket|ad)\w* (göster|aç)", t):
        return {"do": {"labels": True}, "say": "İsimleri açtım efendim."}
    if re.search(r"ufuk|yön\w* (göster|aç)|pusula", t):
        return {"do": {"compass": True}, "say": "Ufuk yönleri ekranda efendim."}
    # gezegen / Ay / Güneş nerede
    pl = [("Güneş", r"güneş"), ("Ay", r"\bay\b|ayın|dolunay|hilal"), ("Merkür", r"merkür"), ("Venüs", r"venüs|çoban yıldızı|akşam yıldızı"), ("Mars", r"mars"), ("Jüpiter", r"jüpiter"), ("Satürn", r"satürn")]
    for name, pat in pl:
        if re.search(pat, t) and re.search(r"nerede|nerde|görün\w*|görebil\w*|hangi yön|bul|göster", t):
            o = next((x for x in snap() if x["name"] == name), None)
            if o:
                extra = f" Evresi: {o['phase_name'].lower()}, yüzde {fmt(o['phase'] * 100)} aydınlık." if name == "Ay" else ""
                return {"do": {"focus": {"kind": "obj", "name": name}}, "say": f"{name} şu an {_alt_text(o)}.{extra} {SK.NOTES.get(name, '')}"}
    # takımyıldızı / yıldız
    for k, (nm, _) in SK.CONSTELLATIONS.items():
        tr = _norm(nm.split(" (")[0])
        if tr and tr in t:
            lore = __import__("sky_lore").CONLORE.get(k, [])
            more = " ".join(lore if re.search(r"hikaye|efsane|mit|anlat|bilgi|ayrıntı|detay|nedir|kimdir", t) else lore[:1])
            return {"do": {"focus": {"kind": "con", "key": k}}, "say": f"{nm} takımyıldızını gösteriyorum efendim. {more}".strip()}
    for k, v in SK.STARS.items():
        if k != "navi" and _norm(v[0]) in t:
            return {"do": {"focus": {"kind": "star", "key": k}}, "say": f"{v[0]}, {v[4]} takımyıldızında, görünür kadiri {fmt(v[3])}. " + __import__("sky_lore").STARFACT.get(k, "")}
    if re.search(r"bu gece|şimdi|şu an|neler|ne görün\w*|gökyüzünde ne|görünen", t):
        vis = [o for o in snap() if o["alt"] > 0 and o["name"] not in ("Güneş",)]
        sun = next(x for x in snap() if x["name"] == "Güneş")
        night = sun["alt"] < -6
        if not vis:
            return {"say": "Şu an ufkun üstünde görebileceğiniz gezegen ya da Ay yok efendim."}
        parts = [f"{o['name']} ({_alt_text(o).split(',')[0]})" for o in vis]
        pre = "Gece." if night else "Şu an Güneş ufkun üstünde ya da alacakaranlık var, gezegenler zor seçilir."
        return {"say": f"{pre} Ufkun üstündekiler: " + "; ".join(parts) + "."}
    return {"say": "Gökyüzü haritasındayım efendim. Bir takımyıldızı ya da yıldız söyleyin, örneğin Büyük Ayı ya da Vega; Jüpiter nerede, bu gece ne görünür, bir saat ileri ve çizgileri göster de diyebilirsiniz."}
