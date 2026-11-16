"""Kur'an modu verisi ve gezinme. Metin kuran_data.json'dan SALT OKUNUR olarak gelir; hiçbir yerde değiştirilmez, üretilmez, yapay zekâya verilmez.
Kaynak: Tanzil Projesi Uthmani 1.1 (CC BY 3.0) + Diyanet İşleri meali (tanzil.net); sayfa/cüz: Medine mushafı (604 sayfa).
Diyanet mealinde bazı ardışık ayetler birlikte çevrilmiştir; kaynak bu metni her ayette tekrarlar. Görünümde böyle bir grup bir kez, ayet aralığıyla gösterilir.
Kullanıcı durumu (son sayfa, yer işaretleri, görünüm) ayrı dosyada: kuran_durum.json."""
import json
import os
import re
import threading
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "kuran_data.json")
STATE = os.path.join(HERE, "kuran_durum.json")
_lock = threading.Lock()
_D = {}


def data() -> dict:
    if not _D:
        with open(DATA, encoding="utf-8") as f:
            d = json.load(f)
        _D["src"] = d["source"]
        _D["suras"] = d["suras"]
        _D["basmala"] = {int(k): v for k, v in d["basmala"].items()}
        _D["ayahs"] = d["ayahs"]                         # [sure, ayet, arapça, meal, sayfa, cüz, secde]
        _D["by_page"] = {}
        for i, a in enumerate(d["ayahs"]):
            _D["by_page"].setdefault(a[4], []).append(i)
        _D["index"] = {(a[0], a[1]): i for i, a in enumerate(d["ayahs"])}
        # meal grupları: ardışık ve birebir aynı meal metinleri (aynı surede)
        grp, start = [0] * len(d["ayahs"]), 0
        for i, a in enumerate(d["ayahs"]):
            if i and not (a[0] == d["ayahs"][i - 1][0] and a[3] == d["ayahs"][i - 1][3]):
                start = i
            grp[i] = start
        _D["grp"] = grp
        _D["grp_end"] = {}
        for i, s in enumerate(grp):
            _D["grp_end"][s] = i
    return _D


# ------------------------------------------------------------------ kullanıcı durumu
def state() -> dict:
    try:
        with open(STATE, encoding="utf-8") as f:
            s = json.load(f)
        if not isinstance(s, dict):
            raise ValueError
    except (OSError, ValueError):
        s = {}
    s.setdefault("page", 1)
    s.setdefault("view", "both")          # both | ar | tr
    s.setdefault("size", 34)
    s.setdefault("marks", [])
    s.setdefault("sel", None)             # [sure, ayet] seçili ayet
    return s


def save_state(s: dict) -> None:
    keep = {k: s[k] for k in ("page", "view", "size", "marks", "sel") if k in s}       # sahne durumundaki geçici anahtarlar yazılmaz
    with _lock:
        tmp = STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(keep, f, ensure_ascii=False, indent=1)
        os.replace(tmp, STATE)


# ------------------------------------------------------------------ arama
def _fold(t: str) -> str:
    t = str(t).replace("İ", "i").replace("I", "ı").lower()
    t = t.translate(str.maketrans("âîûêôáíú", "aiueoaiu"))
    return re.sub(r"[^a-zçğıöşü0-9]", "", t)


ALIASES = {"yasin": 36, "yasinşerif": 36, "aliimran": 3, "alimran": 3, "imran": 3, "enam": 6, "araf": 7, "rad": 13, "ibrahim": 14, "isra": 17, "taha": 20,
           "muminun": 23, "mominun": 23, "furkan": 25, "şuara": 26, "ankebut": 29, "lokman": 31, "ahzab": 33, "sebe": 34, "fatır": 35, "fatir": 35, "saffat": 37,
           "sad": 38, "zümer": 39, "mümin": 40, "gafir": 40, "fussilet": 41, "şura": 42, "duhan": 44, "casiye": 45, "ahkaf": 46, "hucurat": 49, "kaf": 50,
           "zariyat": 51, "rahman": 55, "vakıa": 56, "vakia": 56, "hadid": 57, "mücadele": 58, "mümtehine": 60, "münafikun": 63, "münafikün": 63,
           "teğabün": 64, "tegabün": 64, "talak": 65, "tahrim": 66, "hakka": 69, "mearic": 70, "müzzemmil": 73, "müddessir": 74, "kıyame": 75, "kiyame": 75,
           "insan": 76, "dehr": 76, "mürselat": 77, "nebe": 78, "naziat": 79, "tekvir": 81, "infitar": 82, "mutaffifin": 83, "inşikak": 84, "büruc": 85,
           "tarık": 86, "tarik": 86, "ala": 87, "gaşiye": 88, "inşirah": 94, "şerh": 94, "tin": 95, "zilzal": 99, "adiyat": 100, "karia": 101, "tekasür": 102,
           "hümeze": 104, "fil": 105, "maun": 107, "kafirun": 109, "tebbet": 111, "leheb": 111, "ihlas": 112, "fatiha": 1, "elham": 1, "kadir": 97, "kadr": 97}


def find_sura(text: str):
    """Metindeki sure adını bulur: sure numarası ya da None. Kelime başı eşleşmesi (Türkçe ekler kabul: 'Bakara'yı', 'Yasini');
    'durum' içindeki 'rum' gibi kelime içi eşleşmeler sayılmaz. Sure adı ancak cümlede 'sure' geçiyorsa ya da cümle onunla başlıyorsa kabul edilir."""
    d = data()
    raw = str(text).replace("İ", "i").replace("I", "ı").lower()
    words = [_fold(w) for w in re.split(r"[\s\-]+", raw) if _fold(w)]
    if not words:
        return None
    has_sure = any(w.startswith("sure") for w in words)
    cands = []                                           # (kelime dizisi birleşimi, başlangıç sırası)
    for i in range(len(words)):
        for j in range(i + 1, min(len(words), i + 3) + 1):
            cands.append(("".join(words[i:j]), i))
    keys = [(_fold(s["tr"]), s["n"]) for s in d["suras"]] + list(ALIASES.items())
    best, blen = None, 0
    for k, n in keys:
        for c, pos in cands:
            if c in ("nasıl", "nasılsın", "nasılız"):
                continue
            if c.startswith(k) and len(c) - len(k) <= 6 and len(k) > blen and (has_sure or pos == 0):
                best, blen = n, len(k)
    return best


# ------------------------------------------------------------------ görünüm
def page_view(page: int, sel=None) -> dict:
    d = data()
    page = max(1, min(604, int(page)))
    idx = d["by_page"][page]
    items, starts = [], []
    for i in idx:
        s, a, ar, tr, pg, jz, sj = d["ayahs"][i]
        if a == 1:
            su = d["suras"][s - 1]
            starts.append(s)
            items.append({"head": True, "s": s, "tr": su["tr"], "ar": su["ar"], "ayahs": su["ayahs"], "type": su["type"], "basmala": d["basmala"].get(s)})
        items.append({"s": s, "a": a, "ar": ar, "sj": sj})
    meal, seen = [], set()
    for i in idx:
        g = d["grp"][i]
        if g in seen:
            continue
        seen.add(g)
        e = d["grp_end"][g]
        s0, a0 = d["ayahs"][g][0], d["ayahs"][g][1]
        a1 = d["ayahs"][e][1]
        meal.append({"s": s0, "a0": a0, "a1": a1, "tr": d["ayahs"][g][3], "head": d["suras"][s0 - 1]["tr"] if a0 == 1 else None,
                     "out": g not in idx or e not in idx})       # grubun bir kısmı başka sayfada
    first = d["ayahs"][idx[0]]
    cur = first[0]
    if sel and d["index"].get((sel[0], sel[1])) in idx:      # açılan / seçili ayet bu sayfadaysa başlık o sure olur (ör. Yâsîn, Fâtır'ın sonuyla başlayan sayfada)
        cur = sel[0]
    su = d["suras"][cur - 1]
    return {"page": page, "juz": first[5], "sura": cur, "suraName": su["tr"], "suraAr": su["ar"], "items": items, "meal": meal,
            "range": f"{d['suras'][first[0]-1]['tr']} {first[1]} – {d['suras'][d['ayahs'][idx[-1]][0]-1]['tr']} {d['ayahs'][idx[-1]][1]}",
            "sel": sel}


def page_of(sura: int, ayah: int = 1):
    d = data()
    i = d["index"].get((int(sura), int(ayah)))
    return d["ayahs"][i][4] if i is not None else None


def juz_page(juz: int):
    d = data()
    return next((a[4] for a in d["ayahs"] if a[5] == int(juz)), None)


def sura_list() -> list:
    return [{"n": s["n"], "tr": s["tr"], "ayahs": s["ayahs"], "page": s["page"], "type": s["type"]} for s in data()["suras"]]


def source() -> dict:
    s = data()["src"]
    return {"text": s["text"], "meal": s["meal"], "pages": s["pages"], "verification": s["verification"]}


def view() -> dict:
    st = state()
    v = page_view(st["page"], st.get("sel"))
    v.update(view=st["view"], size=st["size"], marks=st["marks"][-30:], suras=sura_list(), source=source())
    return v


def listen_url(kind: str, sura: int, ayah=None) -> str:
    """YouTube Music araması: kind 'meal' (Türkçe meal) ya da 'ar' (Arapça tilavet). Seçili ayet varsa aramaya eklenir."""
    name = data()["suras"][int(sura) - 1]["tr"].translate(str.maketrans("âîûÂÎÛ", "aiuAIU"))       # aramada yaygın yazım: Yasin, Al-i Imran
    q = f"{name} Suresi"
    if ayah and int(ayah) > 1:
        q += f" {int(ayah)}. ayet"
    q += " Türkçe meali" if kind == "meal" else " tilaveti"
    return "https://music.youtube.com/search?q=" + urllib.parse.quote(q)
