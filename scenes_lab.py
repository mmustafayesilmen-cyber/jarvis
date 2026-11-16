"""Kimya ve biyoloji laboratuvarı modlarının komut işleyicileri. Çıktı: {'do': sayfaya giden komut, 'say': konuşulacak metin}."""
import random, re

import bio_data as B
import chem_data as C
import lab_concepts as K


def _norm(text: str) -> str:
    t = text.replace("İ", "i").replace("I", "ı").lower()
    t = re.sub(r"['’]\w*", "", t)
    t = re.sub(r"[^\w\sçğıöşü%.,]", " ", t)
    t = re.sub(r"\b(jarvis|hey|lütfen|bana|şunu|efendim|hadi|şimdi|bir|bize)\b", " ", t)
    return " ".join(t.split())


def _num(t: str):
    m = re.search(r"(\d+(?:[.,]\d+)?)", t)
    return float(m.group(1).replace(",", ".")) if m else None


_W = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10, "on bir": 11, "on iki": 12, "on üç": 13,
      "on dört": 14, "on beş": 15, "on altı": 16, "on yedi": 17, "on sekiz": 18, "on dokuz": 19, "yirmi": 20, "yirmi bir": 21}


def _ordinal(t: str):
    m = re.search(r"(\d{1,3})\s*(?:numara|nolu|numaralı|\.|inci|ıncı|uncu|üncü)", t)
    if m:
        return int(m.group(1))
    for w, v in sorted(_W.items(), key=lambda kv: -len(kv[0])):
        if re.search(r"\b" + w + r"\s*(numara|nolu|numaralı)", t):
            return v
    return None


# ------------------------------------------------------------------ canlı araştırma (internet)
def research_say(q: str):
    import tools
    try:
        raw = tools.research(q)
    except Exception:
        return None, "İnternete şu an ulaşamadım efendim, bağlantınızı kontrol eder misiniz?"
    lines = [l for l in raw.splitlines() if l.strip()]
    if not lines:
        return None, "Bu konuda güncel bir sonuç bulamadım efendim."
    items = []
    for l in lines[:4]:
        m = re.match(r"^- (.*?): (.*?) \((https?://[^)]+)\)\s*$", l)
        items.append((m.group(1), m.group(2), m.group(3)) if m else (l[:60], l, ""))
    say = "İnternette şunları buldum efendim. " + " ".join(f"{t}. {b[:200].rstrip()}." for t, b, _ in items[:2])
    card = {"title": "Güncel arama: " + q, "lines": [f"{t}: {b[:260]}" + (f"  [{u}]" if u else "") for t, b, u in items]}
    return card, say


from lab_more_exp import CHEM_ALIAS_X, BIO_ALIAS_X


def _exp_pick(aliases, t):
    for key, pat in aliases:
        if re.search(pat, t):
            return key
    return None


def _exp_sections(e, t):
    if re.search(r"malzeme", t):
        return "Malzemeler: " + ", ".join(e["mats"]) + "."
    if re.search(r"adım|nasıl yap|yapılış", t):
        return "Adımlar. " + " ".join(f"{i}. {s}" for i, s in enumerate(e["steps"], 1))
    if re.search(r"gözlem|ne gözlen|ne olur|sonuç", t):
        return "Ne gözlenir: " + e["observe"]
    if re.search(r"neden|nasıl oluyor|bilimsel|açıklama|niçin", t):
        return "Neden: " + e["why"]
    if re.search(r"güvenlik|dikkat|tehlike|önlem", t):
        return "Güvenlik: " + e["safety"]
    return None


def _exp_intro(e):
    return f"{e['name']}. Seviye {e['level'].lower()}" + (f", yaklaşık {e['mins']} dakika. " if e["mins"] else ". ") + f"Amaç: {e['aim']} Malzemeleri, adımları, ne gözlendiğini, nedenini ya da güvenlik uyarısını sorabilirsiniz."


def _concept(items, t):
    if not re.search(r"nedir|ne demek|açıkla|anlat|hakkında|kimdir|bilgi|nasıl çalış|ne işe", t):
        return None
    for title, pat, text in items:
        if re.search(pat, t):
            return {"title": title, "lines": K.sentences(text), "concept": title}, K.short_say(title, text)
    return None


# ============================================================== KİMYA
CHEM_EXP_ALIAS = [("lahana", r"lahana|ph gösterge"), ("volkan", r"volkan"), ("fil", r"fil diş|köpük şelale|fil"), ("lav", r"lav lamba|\blav\b"), ("sut", r"süt|renk dans"),
                  ("yogunluk", r"yoğunluk kule|yoğunluk deney"), ("kristal", r"kristal"), ("mum", r"\bmum\b|mum deney"), ("yumurta", r"yumurta"), ("limonpil", r"limonlu pil|meyve pili|limon pil"),
                  ("elektroliz", r"elektroliz"), ("gizlimurekkep", r"görünmez|gizli mürekkep|limonlu mürekkep"), ("kromato", r"kromatograf|mürekkep"), ("buztuz", r"buz.*tuz|tuz.*buz|donma noktası"),
                  ("balon", r"balon"), ("coz", r"çözünme hız|sıcak.*soğuk su|şeker.*çözün"), ("tyndall", r"tyndall|ışığın yolu"), ("oobleck", r"oobleck|nişasta"), ("biber", r"biber"),
                  ("pas", r"\bpas\b|paslan"), ("gevrek", r"gevrek")]
CHEM_TABS = [("table", r"periyodik tablo|elementler|tablo"), ("mol", r"moleküller|molekül modeli|molekül listesi|moleküle geç"), ("exp", r"deneyler|deney listesi|deneylere geç"),
             ("ph", r"ph skala|ph ölçeği|asit baz skala|asit baz"), ("calc", r"hesap|hesaplama|hesaplayıcı"), ("info", r"kavramlar|kavram listesi"), ("safe", r"güvenlik")]
COMMON = {"su": "H2O", "tuz": "NaCl", "sofra tuzu": "NaCl", "şeker": "C12H22O11", "glikoz": "C6H12O6", "karbondioksit": "CO2", "amonyak": "NH3", "metan": "CH4",
          "asetik asit": "CH3COOH", "kabartma tozu": "NaHCO3", "kireç taşı": "CaCO3", "etanol": "C2H5OH", "alkol": "C2H5OH", "oksijen": "O2", "hidrojen": "H2",
          "azot": "N2", "sülfürik asit": "H2SO4", "hidroklorik asit": "HCl", "tuz ruhu": "HCl", "sodyum hidroksit": "NaOH", "kostik": "NaOH", "propan": "C3H8", "bütan": "C4H10"}


def _recase(tok: str):
    s, out, i = tok, "", 0
    while i < len(s):
        ch = s[i]
        if ch.isdigit() or ch in "()":
            out += ch
            i += 1
        else:
            two = ch.upper() + (s[i + 1].lower() if i + 1 < len(s) and s[i + 1].isalpha() else "")
            if len(two) == 2 and two in C.SYM and not (s[i + 1:i + 2].isalpha() and (s[i + 1:i + 2].isupper())):
                out += two
                i += 2
            elif ch.upper() in C.SYM:
                out += ch.upper()
                i += 1
            else:
                return None
    return out


def find_formula(raw: str, t: str):
    for name, f in sorted(COMMON.items(), key=lambda kv: -len(kv[0])):
        if re.search(r"\b" + name + r"\b", t):
            return f
    cands = re.findall(r"[A-Z][A-Za-z0-9()·.]*[A-Za-z0-9)]", raw) + re.findall(r"\b[A-Z][a-z]?\d*\b", raw)
    for c in sorted(cands, key=len, reverse=True):
        try:
            C._parse_formula(c)
            return c
        except Exception:
            continue
    for tok in re.findall(r"[a-z][a-z0-9()]*\d[a-z0-9()]*|\b[a-z]{1,3}\b", raw.lower()):
        r = _recase(tok)
        if r:
            try:
                C._parse_formula(r)
                return r
            except Exception:
                pass
    return None


CHEM_EXP_ALIAS[:0] = CHEM_ALIAS_X


def kimya_init():
    return {"elements": [C.element_info(z) for z in range(1, 119)], "molecules": C.MOLECULES, "experiments": C.EXPERIMENTS,
            "ph": [{"name": n, "ph": v, "desc": d} for n, v, d in C.PH], "safety": C.SAFETY,
            "concepts": [{"title": t, "lines": K.sentences(x)} for t, _, x in K.CHEM]}


def _mol_find(t):
    for i, m in enumerate(C.MOLECULES):
        if re.search(r"\b" + re.escape(m["formula"].lower()) + r"\b", t):
            return i
    for i, m in enumerate(C.MOLECULES):
        nm = _norm(m["name"])
        if re.search(r"\b" + re.escape(nm.split(" (")[0]) + r"\b", t):
            if len(nm) <= 3 and not re.search(r"molekül|model|yapı", t):
                continue
            return i
    return None


def kimya(text: str, st: dict):
    t = _norm(text)
    raw = text
    d = K.find_detail(K.CHEM, t)
    if d:
        return {"do": {"tab": "info", "result": {"title": d[0], "lines": K.sentences(d[1]), "concept": d[0]}}, "say": K.short_say(*d)}
    if re.search(r"^(araştır|güncel|internetten|haber|en son)", t) or re.search(r"\b(araştır\w*|güncel bilgi)\b", t):
        q = re.sub(r"\b(araştır\w*|güncel|bilgi|internetten|bul|hakkında|kimya)\b", " ", t).strip() or "kimya haberleri"
        card, say = research_say(q + " kimya" if "kimya" not in t else q)
        return {"do": {"tab": "calc", "result": card} if card else {}, "say": say}
    if re.search(r"(bilgi ver|ilginç|bir bilgi|merak)", t):
        f = random.choice(C.FACT_POOL)
        return {"do": {"fact": f}, "say": f}
    # --- hesaplayıcılar
    if re.search(r"denkleştir|dengele|denklem", t):
        eq = re.sub(r"(?i)\b(denkleştir\w*|dengele\w*|denklemini?|denklem)\b[: ]*", " ", raw)
        eq = re.sub(r"(?i)\b(artı)\b", "+", eq)
        eq = re.sub(r"(?i)\b(ok|eşittir|tepkime verir|oluşturur)\b", "->", eq)
        eq = re.sub(r"[.,]+$", "", eq.strip())
        try:
            res = C.balance(eq)
        except Exception as e:
            return {"say": f"Denklemi denkleştiremedim efendim: {e}. Örneğin H2 artı O2 ok H2O şeklinde yazın."}
        return {"do": {"tab": "calc", "result": {"title": "Denkleştirilmiş denklem", "lines": [res]}}, "say": "Denkleştirilmiş denklem: " + res.replace("→", "ok").replace("+", "artı") + "."}
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(gram|g\b|mol\b|kilo|kg\b)", t)
    if m and re.search(r"kaç (mol|gram)|mol hesab|gram|molü|molu", t):
        f = find_formula(raw, t)
        if f:
            M = C.molar_mass(f)
            v = float(m.group(1).replace(",", "."))
            unit = m.group(2)
            if unit.startswith("mol"):
                g = v * M
                lines = [f"{v:g} mol {f} = {g:.3g} gram", f"Molar kütle: {M:.3f} g/mol"]
                return {"do": {"tab": "calc", "result": {"title": f"{f} mol → gram", "lines": lines}}, "say": f"{v:g} mol {f}, yaklaşık {g:.3g} gram eder. Molar kütlesi {M:.2f} gram bölü mol."}
            if unit.startswith("k"):
                v *= 1000
            n = v / M
            lines = [f"{v:g} g {f} = {n:.3g} mol", f"Molar kütle: {M:.3f} g/mol"]
            return {"do": {"tab": "calc", "result": {"title": f"{f} gram → mol", "lines": lines}}, "say": f"{v:g} gram {f}, yaklaşık {n:.3g} mol eder. Molar kütlesi {M:.2f} gram bölü mol."}
    if re.search(r"molekül kütle|mol kütle|molar kütle|mol ağırlı|molekül ağırlı|kütlesi", t):
        f = find_formula(raw, t)
        if f:
            comp = C._parse_formula(f)
            M = C.molar_mass(f)
            lines = [f"{e}: {c} × {C.MASS[e]:.3f} = {c * C.MASS[e]:.3f}" for e, c in comp.items()] + [f"Toplam: {M:.3f} g/mol"]
            return {"do": {"tab": "calc", "result": {"title": f"{f} molar kütlesi", "lines": lines}}, "say": f"{f} bileşiğinin molar kütlesi yaklaşık {M:.2f} gram bölü moldür."}
    if re.search(r"\bph\b|ph'", t) or re.search(r"ph\s*\d", t):
        v = _num(re.sub(r"\bph\b", "", t))
        if v is not None and 0 <= v <= 14:
            return {"do": {"tab": "ph", "ph": v}, "say": C.ph_text(v)}
        for n, ph, d in C.PH:
            if re.search(r"\b" + re.escape(_norm(n).split()[0]), t):
                return {"do": {"tab": "ph", "ph": ph, "name": n}, "say": f"{n}: pH yaklaşık {ph:g}. {d}"}
        return {"do": {"tab": "ph"}, "say": "pH ölçeği ekranda efendim. 0 ile 14 arasında bir değer ya da bir madde adı söyleyin."}
    for n, ph, d in C.PH:
        if re.search(r"\b" + re.escape(_norm(n).split()[0]) + r"\w*\s+(ph|asit|baz)", t):
            return {"do": {"tab": "ph", "ph": ph, "name": n}, "say": f"{n}: pH yaklaşık {ph:g}. {d}"}
    # --- sekme geçişi
    for key, pat in CHEM_TABS:
        if re.fullmatch(r"(?:.*\b)?(?:" + pat + r")(?:\b.*)?", t) and re.search(r"göster|aç|geç|git|listele|^[a-zçğıöşü ]{0,24}$", t) and not re.search(r"deney\w* (lahana|volkan)", t):
            if key == "safe":
                return {"do": {"tab": "safe"}, "say": "Güvenlik kuralları: " + " ".join(C.SAFETY[:4]) + " Devamı ekranda."}
            if key == "exp":
                return {"do": {"tab": "exp"}, "say": f"{len(C.EXPERIMENTS)} deney var: " + ", ".join(e["name"] for e in C.EXPERIMENTS[:8]) + " ve devamı ekranda. Birini söyleyin."}
            if key == "mol":
                return {"do": {"tab": "mol"}, "say": f"{len(C.MOLECULES)} molekül modeli var: " + ", ".join(m["name"] for m in C.MOLECULES[:8]) + " ve diğerleri. Birini söyleyin."}
            if key == "table":
                return {"do": {"tab": "table"}, "say": "Periyodik tablo ekranda efendim. Bir element adı, sembolü ya da atom numarasını söyleyin."}
            if key == "ph":
                return {"do": {"tab": "ph"}, "say": "pH ölçeği ekranda efendim."}
            if key == "info":
                return {"do": {"tab": "info"}, "say": f"{len(K.CHEM)} ayrıntılı kavram var efendim, listesi ekranda. Birini seçin ya da, örneğin, titrasyon nedir diye sorun."}
            if key == "calc":
                return {"do": {"tab": "calc"}, "say": "Hesaplayıcı: molekül kütlesi, gram-mol çevirme ve denklem denkleştirme. Örneğin H2SO4 molekül kütlesi, ya da 36 gram su kaç mol, ya da H2 artı O2 ok H2O denkleştir."}
    if re.search(r"karıştır\w*|tehlikeli karışım|birlikte kullan", t) and re.search(r"tehlike|zarar|yapma|asla", t):
        s = [C.SAFETY[i] for i in (2, 3, 4)]
        return {"do": {"tab": "safe"}, "say": "Asla karıştırılmaması gerekenler. " + " ".join(s)}
    if re.search(r"güvenlik|dikkat edilecek|laboratuvar kural", t):
        return {"do": {"tab": "safe"}, "say": "Güvenlik kuralları. " + " ".join(C.SAFETY[:5])}
    # --- deney
    exp_sec = None
    cur = st.get("exp")
    if cur:
        e = next(x for x in C.EXPERIMENTS if x["key"] == cur)
        exp_sec = _exp_sections(e, t)
        if exp_sec:
            return {"say": exp_sec}
    k = _exp_pick(CHEM_EXP_ALIAS, t) if re.search(r"deney|nasıl|yap|göster|aç|anlat", t) or True else None
    n = _ordinal(t) if re.search(r"deney", t) else None
    if n and 1 <= n <= len(C.EXPERIMENTS):
        k = C.EXPERIMENTS[n - 1]["key"]
    if re.search(r"\b(sonraki|önceki)\b", t) and re.search(r"deney", t):
        keys = [x["key"] for x in C.EXPERIMENTS]
        i = keys.index(cur) if cur in keys else -1
        k = keys[(i + (1 if "sonraki" in t else -1)) % len(keys)]
    if k:
        e = next(x for x in C.EXPERIMENTS if x["key"] == k)
        st["exp"] = k
        return {"do": {"tab": "exp", "exp": k}, "say": _exp_intro(e)}
    # --- molekül
    mi = _mol_find(t)
    if mi is not None:
        m = C.MOLECULES[mi]
        st["mol"] = mi
        return {"do": {"tab": "mol", "mol": mi}, "say": f"{m['name']}, formülü {m['formula']}. Geometrisi {m['geom']}, {'polar' if m['polar'] else 'apolar'} bir yapı. {m['desc']}"}
    if re.search(r"\b(sonraki|önceki)\b", t) and re.search(r"molekül", t):
        i = st.get("mol", -1) + (1 if "sonraki" in t else -1)
        i %= len(C.MOLECULES)
        st["mol"] = i
        m = C.MOLECULES[i]
        return {"do": {"tab": "mol", "mol": i}, "say": f"{m['name']}, formülü {m['formula']}. {m['desc']}"}
    # --- element
    if re.search(r"\b(sonraki|önceki)\b", t) and re.search(r"element", t):
        z = (st.get("z", 0) + (1 if "sonraki" in t else -1) - 1) % 118 + 1
        st["z"] = z
        return {"do": {"tab": "table", "el": z}, "say": C.element_say(z)}
    z = C.find_element(t if not re.search(r"\b[A-Z][a-z]?\b", raw) else raw + " " + t)
    if z:
        st["z"] = z
        return {"do": {"tab": "table", "el": z}, "say": C.element_say(z)}
    # --- kavram
    r = _concept(K.CHEM, t)
    if r:
        return {"do": {"tab": "info", "result": r[0]}, "say": r[1]}
    return {"say": "Kimya laboratuvarındayım efendim. Bir element, molekül, deney ya da kavram söyleyin; hesap için molekül kütlesi, gram mol ya da denkleştir diyebilirsiniz."}


# ============================================================== BİYOLOJİ
BIO_EXP_ALIAS = [("sogan", r"soğan"), ("plazmoliz", r"plazmoliz"), ("patates", r"patates|ozmoz deney"), ("dna", r"dna özüt|çilek|dna deney"), ("maya", r"maya|fermantasyon deney"),
                 ("kereviz", r"kereviz|karanfil|ksilem"), ("fasulye", r"fasulye|çimlen"), ("foto", r"fototropizm|ışığa yön"), ("nisasta", r"nişasta"), ("enzim", r"kivi|ananas|enzim deney"),
                 ("stoma", r"stoma|gözenek"), ("nabiz", r"nabız|egzersiz"), ("reaksiyon", r"reaksiyon|cetvel"), ("korNokta", r"kör nokta"), ("parmakizi", r"parmak izi"),
                 ("elodea", r"elodea|su bitkisi|fotosentez deney"), ("yumurtazar", r"yumurta"), ("kromo", r"yaprak pigment|kromatograf"), ("mikroskop", r"mikroskop yap|su damla"),
                 ("bakteri", r"bakteri ürett|bakteri kült")]
BIO_TABS = [("cell", r"hücre modeli|hücrelere|hücreler"), ("sys", r"sistemler|vücut sistem|organ sistem"), ("exp", r"deneyler|deney listesi"), ("gen", r"genetik|kalıtım laboratuvar"),
            ("cls", r"sınıflandırma|alemler|taksonomi"), ("info", r"bilgi sekme|bilgi kartı|kavramlar|kavram listesi")]
SYS_ALIAS = [("dolasim", r"dolaşım|kalp|kan damar"), ("solunum", r"solunum sistem|akciğer"), ("sindirim", r"sindirim|mide|bağırsak"), ("sinir", r"sinir sistem|beyin|nöron|omurilik"),
             ("bosaltim", r"boşaltım|böbrek"), ("endokrin", r"endokrin|hormon sistem|salgı bez"), ("iskelet", r"iskelet|kemik|kas sistem"), ("bagisiklik", r"bağışıklık sistem"), ("duyu", r"duyu organ|göz|kulak")]
ORG_ALIAS = [("nucleolus", r"çekirdekçik"), ("nucleus", r"çekirdek"), ("mito", r"mitokondri"), ("er", r"endoplazmik|\ber\b|retikulum"), ("ribosome", r"ribozom"), ("golgi", r"golgi"),
             ("lysosome", r"lizozom"), ("vacuole", r"koful|vakuol|vakuol"), ("chloroplast", r"kloroplast"), ("cellwall", r"hücre duvarı"), ("membrane", r"hücre zarı|plazma zarı"),
             ("cytoplasm", r"sitoplazma"), ("centrosome", r"sentriyol|sentrozom"), ("nucleoid", r"nükleoid|nukleoid"), ("plasmid", r"plazmit|plazmid"), ("flagellum", r"kamçı|flagel"),
             ("capsule", r"kapsül"), ("pili", r"pilus|fimbria")]


BIO_EXP_ALIAS[:0] = BIO_ALIAS_X


def biyoloji_init():
    return {"cells": B.CELLS, "org": {k: {"name": v[0], "func": v[1], "fact": v[2]} for k, v in B.ORG.items()}, "systems": B.SYSTEMS, "experiments": B.EXPERIMENTS,
            "classif": B.CLASSIF, "concepts": [{"title": t, "lines": K.sentences(x)} for t, _, x in K.BIO]}


def _cell_for(org):
    if org in ("chloroplast", "cellwall") or (org == "vacuole"):
        return "plant"
    if org in ("nucleoid", "plasmid", "flagellum", "capsule", "pili"):
        return "bacteria"
    return None


def biyoloji(text: str, st: dict):
    t = _norm(text)
    raw = text
    d = K.find_detail(K.BIO, t)
    if d:
        return {"do": {"tab": "info", "result": {"title": d[0], "lines": K.sentences(d[1]), "concept": d[0]}}, "say": K.short_say(*d)}
    if re.search(r"^(araştır|güncel|internetten|haber|en son)", t) or re.search(r"\b(araştır\w*|güncel bilgi)\b", t):
        q = re.sub(r"\b(araştır\w*|güncel|bilgi|internetten|bul|hakkında)\b", " ", t).strip() or "biyoloji haberleri"
        card, say = research_say(q if "biyoloji" in t else q + " biyoloji")
        return {"do": {"tab": "info", "result": card} if card else {}, "say": say}
    if re.search(r"(bilgi ver|ilginç|bir bilgi|merak)", t):
        f = random.choice(B.FACT_POOL)
        return {"do": {"tab": "info", "fact": f}, "say": f}
    # --- genetik
    if re.search(r"punnett|çaprazla|genotip|çarpı|\bx\b|×", t + " " + raw) and re.search(r"([A-Za-z]{2,6})\s*(?:x|×|çarpı|ile|\*)\s*([A-Za-z]{2,6})", raw):
        m = re.search(r"\b([A-Za-z]{2,6})\s*(?:x|×|çarpı|ile|\*)\s*([A-Za-z]{2,6})\b", raw)
        a, b = m.group(1), m.group(2)
        try:
            say = B.punnett_say(a, b)
            r = B.punnett(a, b)
        except Exception as e:
            return {"say": f"Çaprazlamayı hesaplayamadım efendim: {e}. Örneğin Aa çarpı Aa deyin."}
        return {"do": {"tab": "gen", "punnett": {"p1": a, "p2": b, **r}}, "say": say}
    if re.search(r"\bdna\b|\brna\b|dizi|çevir|protein", t) and re.search(r"[ATGCatgc ]{6,}", raw):
        seq = re.sub(r"[^ATGCatgc]", "", re.sub(r"(?i)\b(dna|rna|dizisi|çevir\w*|kalıp|zincir\w*|protein\w*|ne|olur|bu|mrna|şunu|dizi)\b", " ", raw))
        if len(seq) >= 3:
            try:
                d = B.dna_translate(seq)
            except Exception as e:
                return {"say": f"Diziyi çeviremedim efendim: {e}."}
            say = f"Kalıp DNA {d['dna']} için mRNA {d['mrna']}. Protein: " + ", ".join(d["protein"]) + "."
            return {"do": {"tab": "gen", "dna": d}, "say": say}
    mm = re.search(r"\b([AUGCaugc]{3})\b", raw)
    if mm and re.search(r"kodon", t):
        cod = mm.group(1).upper()
        aa = B.CODON.get(cod)
        if aa:
            return {"do": {"tab": "gen"}, "say": f"{cod} kodonu {B.AA_TR[aa]} amino asidini kodlar." if aa != "*" else f"{cod} bir dur kodonudur."}
    # --- sınıflandırma
    if re.search(r"sınıflandırma|alemler|taksonomi|insanın sınıf", t):
        c = B.CLASSIF
        steps = ", ".join(f"{l}: {v}" for l, v in zip(c["levels"][::-1], c["human"][::-1]))
        return {"do": {"tab": "cls"}, "say": "Canlılar basamak basamak sınıflandırılır: üst alem, alem, şube, sınıf, takım, familya, cins ve tür. İnsan için: " + steps + ". " + c["note"]}
    # --- organel / hücre
    for key, pat in ORG_ALIAS:
        if re.search(pat, t):
            name, func, fact = B.ORG[key]
            cell = _cell_for(key) or st.get("cell", "animal")
            if key == "vacuole" and re.search(r"hayvan", t):
                cell = "animal"
            st["cell"] = cell
            return {"do": {"tab": "cell", "cell": cell, "org": key}, "say": f"{name}. {func} {fact}".strip()}
    for key, nm in (("animal", r"hayvan hücre"), ("plant", r"bitki hücre"), ("bacteria", r"bakteri hücre|prokaryot")):
        if re.search(nm, t):
            st["cell"] = key
            return {"do": {"tab": "cell", "cell": key}, "say": f"{B.CELLS[key]['name']}. {B.CELLS[key]['intro']} Organellerden birini söyleyin ya da ekrandan tıklayın."}
    if re.search(r"hücre", t) and not re.search(r"nedir|kuramı|teori", t):
        return {"do": {"tab": "cell"}, "say": "Hücre modeli ekranda. Hayvan, bitki ya da bakteri hücresi ve organel adlarını söyleyebilirsiniz."}
    # --- sistemler
    if cur_sys := st.get("sys"):
        s = next(x for x in B.SYSTEMS if x["key"] == cur_sys)
        if re.search(r"organ|nelerden", t) and not re.search(r"organel", t):
            return {"say": f"{s['name']} şu organlardan oluşur: {s['organs']}."}
        if re.search(r"görev|ne işe|işlev", t):
            return {"say": s["function"]}
        if re.search(r"ilginç|bilgi|başka|devam|daha", t):
            i = st.get("fi", 0) % len(s["facts"])
            st["fi"] = i + 1
            return {"say": s["facts"][i]}
    for key, pat in SYS_ALIAS:
        if re.search(pat, t) and not re.search(r"nedir|ne demek", t) or (re.search(pat, t) and re.search(r"sistem", t)):
            s = next(x for x in B.SYSTEMS if x["key"] == key)
            st["sys"], st["fi"] = key, 1
            return {"do": {"tab": "sys", "sys": key}, "say": f"{s['name']}. {s['function']} Organları: {s['organs']}. {s['facts'][0]}"}
    # --- sekmeler
    for key, pat in BIO_TABS:
        if re.search(pat, t) and re.search(r"göster|aç|geç|git|listele|^[a-zçğıöşü ]{0,24}$", t):
            msg = {"cell": "Hücre modeli ekranda efendim.", "sys": "Vücut sistemleri ekranda: " + ", ".join(s["name"] for s in B.SYSTEMS) + ". Birini söyleyin.",
                   "exp": f"{len(B.EXPERIMENTS)} deney var: " + ", ".join(e["name"] for e in B.EXPERIMENTS[:8]) + " ve devamı ekranda.",
                   "gen": "Genetik: Punnett karesi için Aa çarpı Aa deyin, DNA çevirmek için DNA ve diziyi söyleyin, kodon için kodon AUG diyebilirsiniz.",
                   "cls": "Sınıflandırma ekranda efendim.", "info": "Bilgi kartları ekranda efendim."}[key]
            return {"do": {"tab": key}, "say": msg}
    # --- deney
    cur = st.get("exp")
    if cur:
        e = next(x for x in B.EXPERIMENTS if x["key"] == cur)
        sec = _exp_sections(e, t)
        if sec:
            return {"say": sec}
    k = _exp_pick(BIO_EXP_ALIAS, t)
    n = _ordinal(t) if re.search(r"deney", t) else None
    if n and 1 <= n <= len(B.EXPERIMENTS):
        k = B.EXPERIMENTS[n - 1]["key"]
    if re.search(r"\b(sonraki|önceki)\b", t) and re.search(r"deney", t):
        keys = [x["key"] for x in B.EXPERIMENTS]
        i = keys.index(cur) if cur in keys else -1
        k = keys[(i + (1 if "sonraki" in t else -1)) % len(keys)]
    if k:
        e = next(x for x in B.EXPERIMENTS if x["key"] == k)
        st["exp"] = k
        return {"do": {"tab": "exp", "exp": k}, "say": _exp_intro(e)}
    # --- kavram
    r = _concept(K.BIO, t)
    if r:
        return {"do": {"tab": "info", "result": r[0]}, "say": r[1]}
    return {"say": "Biyoloji laboratuvarındayım efendim. Bir organel, vücut sistemi, deney ya da kavram söyleyin; genetik için Aa çarpı Aa ya da DNA dizisi söyleyebilirsiniz."}
