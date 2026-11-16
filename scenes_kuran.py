"""Kur'an modu komutları: sure / ayet / sayfa / cüz açma, sayfa çevirme, görünüm (Arapça + meal, yalnız Arapça, yalnız meal), yazı boyutu,
yer işareti, 'meali dinle' / 'Arapçasını dinle' (açık yer YouTube Music'te). Jarvis Kur'an metnini kendisi okumaz, yorumlamaz, değiştirmez;
söyleyeceği tek şey konum bilgisidir (sure adı, ayet, sayfa)."""
import re

import kuran as K
import scenes


def _go(st: dict, page: int, sel=None, say: str = "") -> dict:
    page = max(1, min(604, int(page)))
    st["page"] = page
    st["sel"] = list(sel) if sel else None
    K.save_state(st)
    return {"do": {"page": page}, "say": say}


_ONES = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "dörd": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9}
_TENS = {"on": 10, "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50, "altmış": 60, "yetmiş": 70, "seksen": 80, "doksan": 90}


def tr_number(words: list):
    """Sondaki Türkçe sayı sözcüklerini okur: 'iki yüz elli beşinci' -> 255. Sayı yoksa None."""
    vals = []
    for w in reversed(words):
        for suf in ("inci", "ıncı", "uncu", "üncü", "nci", "ncı", "ncu", "ncü"):    # 'ikinci' = iki + nci, 'beşinci' = beş + inci
            if w.endswith(suf) and (w[:-len(suf)] in _ONES or w[:-len(suf)] in _TENS or w[:-len(suf)] == "yüz"):
                w = w[:-len(suf)]
                break
        if w in _ONES or w in _TENS or w == "yüz":
            vals.insert(0, w)
        elif vals:
            break
    if not vals:
        return None
    n, cur = 0, 0
    for w in vals:
        if w == "yüz":
            n += (cur or 1) * 100
            cur = 0
        else:
            cur += _ONES.get(w, 0) + _TENS.get(w, 0)
    return n + cur or None


def _word_num(raw: str, unit: str):
    """'elli ikinci sayfa' / 'sayfa elli iki' / 'otuzuncu cüz' -> sayı."""
    t = str(raw).replace("İ", "i").replace("I", "ı").lower()
    m = re.search(r"^(.*?)\s*\b" + unit + r"\w*\s*(.*)$", t)
    if not m:
        return None
    return tr_number(re.findall(r"[a-zçğıöşü]+", m.group(1))) or tr_number(re.findall(r"[a-zçğıöşü]+", m.group(2)))


def _ayah_in(raw: str):
    """Ayet numarası: '255. ayet', 'ayet 255', 'beşinci ayet', 'iki yüz elli beşinci ayet'. Ham metin üzerinde (norm 'bir'i siler)."""
    t = str(raw).replace("İ", "i").replace("I", "ı").lower()
    m = re.search(r"(\d{1,3})\s*\.?\s*(?:ayet|ayeti|ayetini|ayete|ayetten)\b", t) or re.search(r"\b(?:ayet|ayeti)\s*(\d{1,3})\b", t)
    if m:
        return int(m.group(1))
    m = re.search(r"^(.*?)\s*\bayet\w*", t)
    return tr_number(re.findall(r"[a-zçğıöşü]+", m.group(1))) if m else None


def _listen(kind: str, st: dict) -> dict:
    sel = st.get("sel")
    if sel:
        s, a = sel
    else:
        v = K.page_view(st["page"])                     # seçim yoksa: sayfada başlayan son sure, o da yoksa sayfanın ilk suresi
        heads = [it["s"] for it in v["items"] if it.get("head")]
        s, a = (heads[-1] if heads else v["sura"]), None
    name = K.data()["suras"][s - 1]["tr"]
    where = f"{name} suresi" + (f" {a}. ayet" if a and a > 1 else "")
    return {"open_url": K.listen_url(kind, s, a), "say": f"{where} için {'Türkçe meali' if kind == 'meal' else 'Arapça tilaveti'} YouTube Music'te açıyorum efendim."}


def kuran(text: str, st: dict):
    t = scenes.norm(text)
    if not st.get("_loaded"):
        st.update(K.state(), _loaded=True)
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Bir sure adı söyleyin, örneğin Yasin suresi ya da Bakara 255. ayet. Sayfa 50, cüz 30, sonraki sayfa, önceki sayfa diyebilirsiniz. "
                       "Meali dinle ya da Arapçasını dinle derseniz açık yeri YouTube Music'te açarım. Sadece meal, sadece Arapça, büyüt, küçült ve işaretle de var."}
    # --- dinleme (YouTube Music)
    if re.search(r"\b(dinle|dinlet|dinleyeyim|aç dinle|çal)\w*", t):
        if re.search(r"\b(meal\w*|türkçe\w*)\b", t):
            return _listen("meal", st)
        if re.search(r"\b(arapça\w*|tilavet\w*|kıraat\w*|okunuş\w*|hafız\w*|aslı\w*|orijinal\w*)\b", t):
            return _listen("ar", st)
        return {"say": "Meali mi yoksa Arapçasını mı dinlemek istersiniz efendim? Meali dinle ya da Arapçasını dinle deyin."}
    # --- görünüm
    if re.search(r"\b(sadece|yalnız|yalnızca)\s+(meal\w*|türkçe\w*)", t):
        st["view"] = "tr"; K.save_state(st)
        return {"do": {"view": "tr"}, "say": "Yalnızca meal gösteriliyor efendim."}
    if re.search(r"\b(sadece|yalnız|yalnızca)\s+(arapça\w*|asl\w*|orijinal\w*)", t):
        st["view"] = "ar"; K.save_state(st)
        return {"do": {"view": "ar"}, "say": "Yalnızca Arapça metin gösteriliyor efendim."}
    if re.search(r"\b(ikisi|ikisini|ikisi birden|meal ve arapça|arapça ve meal|mealiyle|meali göster)\b", t):
        st["view"] = "both"; K.save_state(st)
        return {"do": {"view": "both"}, "say": "Arapça metin ve meal yan yana efendim."}
    if re.search(r"\b(büyüt|yazıyı büyüt|daha büyük|yakınlaş)\w*", t):
        st["size"] = min(60, st["size"] + 4); K.save_state(st)
        return {"do": {"size": st["size"]}, "say": ""}
    if re.search(r"\b(küçült|yazıyı küçült|daha küçük|uzaklaş)\w*", t):
        st["size"] = max(22, st["size"] - 4); K.save_state(st)
        return {"do": {"size": st["size"]}, "say": ""}
    # --- yer işareti
    if re.search(r"\b(işaretle|işaret koy|kaldığım yeri kaydet|burayı kaydet|yer imi)\w*", t):
        v = K.page_view(st["page"])
        sel = st.get("sel") or [v["sura"], v["items"][0]["a"] if not v["items"][0].get("head") else v["items"][1]["a"]]
        name = K.data()["suras"][sel[0] - 1]["tr"]
        st["marks"] = [m for m in st["marks"] if m.get("page") != st["page"]][-29:] + [{"page": st["page"], "s": sel[0], "a": sel[1], "t": f"{name} {sel[1]}"}]
        K.save_state(st)
        return {"do": {"marks": True}, "say": f"Kaldığınız yeri işaretledim efendim: {name} suresi, sayfa {st['page']}."}
    if re.search(r"\b(kaldığım yer\w*|işaretime git|işaretli yer\w*|son işaret\w*)\b", t):
        if not st["marks"]:
            return {"say": "Henüz bir yer işaretiniz yok efendim. İşaretle diyerek kaydedebilirsiniz."}
        m = st["marks"][-1]
        return _go(st, m["page"], [m["s"], m["a"]], f"{m['t']}, sayfa {m['page']} efendim.")
    # --- sayfa çevirme
    if re.search(r"\b(sonraki|ileri|sonraki sayfa|sayfayı çevir|devam)\b", t):
        return _go(st, st["page"] + 1)
    if re.search(r"\b(önceki|geri|önceki sayfa)\b", t):
        return _go(st, st["page"] - 1)
    m = re.search(r"\bsayfa\w*\s*(\d{1,3})\b|\b(\d{1,3})\s*\.?\s*sayfa\w*", t)
    if m or (re.search(r"\bsayfa\w*\b", t) and _word_num(text, "sayfa")):
        n = int(m.group(1) or m.group(2)) if m else _word_num(text, "sayfa")
        if not n or not 1 <= n <= 604:
            return {"say": "Sayfa numarası 1 ile 604 arasında olmalı efendim."}
        return _go(st, n, None, f"Sayfa {n} efendim.")
    m = re.search(r"\bcüz\w*\s*(\d{1,2})\b|\b(\d{1,2})\s*\.?\s*cüz\w*", t)
    if m or (re.search(r"\bcüz\w*\b", t) and _word_num(text, "cüz")):
        n = int(m.group(1) or m.group(2)) if m else _word_num(text, "cüz")
        if not n or not 1 <= n <= 30:
            return {"say": "Cüz numarası 1 ile 30 arasında olmalı efendim."}
        return _go(st, K.juz_page(n), None, f"{n}. cüz, sayfa {K.juz_page(n)} efendim.")
    # --- sure / ayet
    if re.search(r"ayet\w*\s*el\s*kürs\w*|ayetelkürsi|ayet-el kürsi", t):
        return _go(st, K.page_of(2, 255), [2, 255], "Ayetel Kürsi, Bakara suresi 255. ayet efendim.")
    s = K.find_sura(text)
    a = _ayah_in(text)
    if s is None and a is None:
        m = re.fullmatch(r".*?\b(\d{1,3})\s*[: ]\s*(\d{1,3})\b.*", t)       # "2 255" ya da "2:255"
        if m and re.search(r"\bsure\w*\b", t):
            s, a = int(m.group(1)), int(m.group(2))
    if s is not None or a is not None:
        if s is None:
            s = K.page_view(st["page"])["sura"]
        if a is None:
            m = re.search(r"\b(\d{1,3})\b", t)                              # "Bakara 255"
            a = int(m.group(1)) if m and not re.search(r"sayfa|cüz", t) else 1
        su = K.data()["suras"][s - 1]
        if not 1 <= a <= su["ayahs"]:
            return {"say": f"{su['tr']} suresi {su['ayahs']} ayettir efendim."}
        return _go(st, K.page_of(s, a), [s, a],
                   f"{su['tr']} suresi" + (f", {a}. ayet" if a > 1 else f", {su['ayahs']} ayet, {su['type']}") + f". Sayfa {K.page_of(s, a)} efendim.")
    return {"say": "Anlayamadım efendim. Bir sure adı, sayfa ya da cüz söyleyin; meali dinle ya da Arapçasını dinle de diyebilirsiniz."}


def ws(d: dict, st: dict):
    t = str(d.get("type", ""))[6:]
    if not st.get("_loaded"):
        st.update(K.state(), _loaded=True)
    if t == "page":
        try:
            return _go(st, int(d.get("page")))
        except (TypeError, ValueError):
            return {}
    if t == "sel":
        try:
            s, a = int(d.get("s")), int(d.get("a"))
        except (TypeError, ValueError):
            return {}
        st["sel"] = [s, a] if K.page_of(s, a) else None
        K.save_state(st)
        return {}
    if t == "sura":
        try:
            s = int(d.get("s"))
        except (TypeError, ValueError):
            return {}
        return _go(st, K.page_of(s, 1)) if 1 <= s <= 114 else {}
    if t == "juz":
        try:
            return _go(st, K.juz_page(int(d.get("juz"))))
        except (TypeError, ValueError):
            return {}
    if t == "view" and d.get("view") in ("both", "ar", "tr"):
        st["view"] = d["view"]; K.save_state(st)
        return {}
    if t == "size":
        try:
            st["size"] = max(22, min(60, int(d.get("size"))))
        except (TypeError, ValueError):
            return {}
        K.save_state(st)
        return {}
    if t == "listen" and d.get("kind") in ("meal", "ar"):
        r = _listen(d["kind"], st)
        r["speak"] = True
        return r
    if t == "mark":
        return kuran("işaretle", st) | {"speak": True}
    if t == "unmark":
        st["marks"] = [m for m in st["marks"] if m.get("page") != d.get("page")]
        K.save_state(st)
        return {}
    return {}


def init_payload():
    return K.view()
