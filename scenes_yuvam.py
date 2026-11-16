"""Evim modu komut işleyicisi (sesle/yazıyla). Çıktı: {'do': sayfaya giden komut, 'say': konuşulacak metin}.
Mantık telefon uygulaması Yuvam ile aynı: 'kulaklığım nerede' arar, 'HyperX kulaklığı salonda TV ünitesinin sağ çekmecesine koydum' kaydeder."""
import re

import yuvam
from yuvam import normalize

QUERY_STOP = {"nerede", "nerde", "neredeydi", "nerededir", "nereye", "benim", "bana", "bul", "bulur", "musun", "misin", "bulabilir", "goster", "acaba", "hani", "ne",
              "var", "mi", "mu", "kaldi", "koymustum", "koydum", "biraktim", "yerini", "yeri", "soyle", "lutfen", "su", "bu", "o", "bir", "ben", "benin", "konumu",
              "konum", "nerdeydi", "neredeymis", "jarvis", "hey", "efendim", "mı", "mü"}
DETAIL_STARTS = {"sag", "sol", "ust", "alt", "orta", "on", "arka", "birinci", "ikinci", "ucuncu", "dorduncu"}
FILLER = {"koydum", "biraktim", "koy", "yerlestirdim", "ekle", "kaydet", "icine", "icinde", "uzerine", "uzerinde", "da", "de", "ta", "te", "dolabinda", "dolabina",
          "icindeki", "bulunuyor", "duruyor", "ve", "adli", "esya", "yeni", "bir", "tasidim", "tasi", "jarvis", "hey", "lutfen", "efendim", "yerlestir", "birak",
          "koyuyorum", "koyalim", "tasiyorum"}
STEMS = (("çekmece", "çekmece"), ("ünitesi", "ünitesi"), ("dolab", "dolap"), ("dolap", "dolap"), ("raf", "raf"), ("kutu", "kutu"), ("sandığ", "sandık"),
         ("sandık", "sandık"), ("bölme", "bölme"), ("kapak", "kapak"), ("komodin", "komodin"), ("masa", "masa"), ("sepet", "sepet"), ("gardırop", "gardırop"),
         ("vitrin", "vitrin"), ("kitaplığ", "kitaplık"), ("kitaplık", "kitaplık"), ("sehpa", "sehpa"), ("bavul", "bavul"), ("çanta", "çanta"), ("torba", "torba"),
         ("klasör", "klasör"), ("askılık", "askılık"), ("büfe", "büfe"), ("tezgah", "tezgah"), ("çekmecel", "çekmece"))
NOISE = re.compile(r"\b(jarvis|hey|lutfen|efendim|hadi|simdi)\b")


def _stem(w: str) -> str:
    """'çekmecesine' -> 'çekmece', 'ünitesinin' -> 'ünitesi' (bilinen mobilya sözcüklerinde hâl eklerini atar)."""
    nw = normalize(w)
    for pre, canon in STEMS:
        np_ = normalize(pre)
        if nw.startswith(np_) and len(nw) - len(np_) <= 7 and nw != "masal":
            return canon
    return w


def _is_stem(w: str) -> bool:
    return _stem(w) != w or any(normalize(w) == normalize(c) for _, c in STEMS)


def _cap(s: str) -> str:
    return (s[:1].replace("i", "İ").upper() + s[1:]) if s[:1] == "i" else s[:1].upper() + s[1:]


def _clean_words(text: str) -> list:
    text = re.sub(r"['’]\w*", "", text)                        # tv ünitesi'nin -> tv ünitesi
    text = re.sub(r"[^\w\s]", " ", text)
    return [w for w in text.split() if not NOISE.fullmatch(normalize(w))]


def extract_query(text: str) -> str:
    words = _clean_words(text)
    kept = [w for w in words if normalize(w) not in QUERY_STOP]
    return " ".join(kept or words)


def parse_add_phrase(text: str, room_names: list):
    """'HyperX kulaklığı salonda TV ünitesinin sağ çekmecesine koydum' -> (ad, oda, [konumlar]). Oda bilinmiyorsa oda boş döner."""
    words = _clean_words(text)
    if not words:
        return None
    known = list(room_names) + [r for r in yuvam.SUGGESTED_ROOMS if normalize(r) not in {normalize(x) for x in room_names}]
    rooms = [(r, normalize(r).split()[0]) for r in known if r]
    room_idx, room_name = -1, ""
    for i, w in enumerate(words):
        nw = normalize(w)
        for r, key in rooms:
            if len(key) >= 3 and nw.startswith(key[:max(3, len(key) - 1)]):
                room_idx, room_name = i, r
                break
        if room_idx >= 0:
            break
    if room_idx >= 0:
        before, after = words[:room_idx], words[room_idx + 1:]
    else:                                       # oda sözcüğü yok: ilk mobilya sözcüğünde eşya adı biter
        cut = next((i for i, w in enumerate(words) if i > 0 and _is_stem(w)), len(words))
        before, after = words[:cut], words[cut:]
    if room_name and len(room_name.split()) > 1 and after:
        after = after[1:]
    name_words = [w for w in before if normalize(w) not in FILLER]
    rest = [_stem(w) for w in after if normalize(w) not in FILLER]
    segs, cur = [], []
    for w in rest:
        if normalize(w) in DETAIL_STARTS and cur:
            segs.append(" ".join(cur))
            cur = []
        cur.append(w)
    if cur:
        segs.append(" ".join(cur))
    name = " ".join(name_words).strip()
    if not name:
        return None
    return _cap(name), room_name, [_cap(s) for s in segs]


def _say_item(d, it) -> str:
    p = yuvam.path_names(d, it)
    s = f"{it['name']}: {', '.join(p)}."
    if it.get("howToFind"):
        steps = [l for l in it["howToFind"].split("\n") if l][:3]
        s += " Nasıl bulunur: " + " ".join(steps)
    return s


def _data():
    return yuvam._load()


def _refresh(**extra):
    return {"data": _data(), **extra}


def _match_item(d, name: str):
    q = normalize(name)

    def same(a, b):
        if a == b:
            return True
        lo, hi = (a, b) if len(a) <= len(b) else (b, a)
        return len(lo) >= 4 and hi.startswith(lo) and len(hi) - len(lo) <= 3      # kulaklığı / kulaklığını
    ex = [i for i in d["items"] if same(normalize(i["name"]), q)]
    return ex[0] if ex else None


def _match_room(d, text: str):
    t = normalize(text)
    best = None
    for r in d["rooms"]:
        key = normalize(r["name"]).split()[0]
        if len(key) >= 3 and re.search(r"\b" + re.escape(key[:max(3, len(key) - 1)]), t):
            if best is None or len(key) > len(normalize(best["name"]).split()[0]):
                best = r
    return best


def _find_item(d, text: str):
    """'kulaklığı sil' gibi bir ifadedeki eşyayı bulur (tam ad, sonra arama)."""
    q = extract_query(text)
    it = _match_item(d, q)
    if it:
        return it
    res = yuvam.search(d, q)
    return res[0] if res else None


def _do_add(st, name, room_name, segs):
    d = _data()
    room = next((r for r in d["rooms"] if normalize(r["name"]) == normalize(room_name)), None) if room_name else None
    if room is None and room_name:
        room = yuvam.add_room(room_name)
    if not room:
        st["pending"] = {"name": name, "path": segs}
        return {"say": f"{name} için hangi odada olduğunu söyler misiniz efendim? Odalar: " + (", ".join(r["name"] for r in d["rooms"]) or "henüz oda yok, yeni bir oda adı söyleyin") + "."}
    exist = _match_item(d, name)
    if exist:
        it = yuvam.move_item(exist["id"], room["id"], segs)
        verb = "yeni yerine taşıdım"
    else:
        it = yuvam.add_item({"name": name, "roomId": room["id"], "locationPath": segs, "categoryId": None, "description": "", "howToFind": "", "isFavorite": False})
        verb = "kaydettim"
    if not it:
        return {"say": "Eşyayı kaydedemedim efendim, sınıra ulaşılmış olabilir."}
    d = _data()
    return {"do": _refresh(open=it["id"], tab="items"), "say": f"{it['name']} eşyasını {verb} efendim: {', '.join(yuvam.path_names(d, it))}."}


def yuvam_cmd(text: str, st: dict):
    raw = " ".join(text.split())
    t = NOISE.sub(" ", normalize(re.sub(r"['’]", "", raw)))
    t = " ".join(re.sub(r"[^\w\s]", " ", t).split())
    d = _data()

    # ---- bekleyen onay / soru
    c = st.get("confirm")
    if c:
        st["confirm"] = None
        if re.match(r"^(evet|onayliyorum|tamam|sil|evet sil|yukle|evet yukle)\b", t):
            if c["kind"] == "item":
                yuvam.delete_item(c["id"])
                return {"do": _refresh(closeDetail=True), "say": "Eşyayı kalıcı olarak sildim efendim."}
            if c["kind"] == "restore":
                n = yuvam.import_backup_file()
                if n < 0:
                    return {"say": "Yedek dosyası bulunamadı ya da geçersiz efendim, verilere dokunmadım."}
                return {"do": _refresh(tab="home"), "say": f"Yedeği yükledim efendim, {n} eşya var."}
            if c["kind"] == "reset":
                yuvam.reset_all()
                return {"do": _refresh(tab="home", closeDetail=True), "say": "Tüm Yuvam verileri silindi efendim."}
        return {"say": "Vazgeçtim efendim, hiçbir şeye dokunmadım."}
    p = st.get("pending")
    if p:
        st["pending"] = None
        if re.match(r"^(vazgec|iptal|bosver|hayir)\b", t):
            return {"say": "Vazgeçtim efendim."}
        room = _match_room(d, t)
        name = room["name"] if room else _cap(" ".join(re.sub(r"\b(odasi|odasinda|oda|de|da|in)\b", " ", raw).split()))
        if not name:
            return {"say": "Anlayamadım efendim, eşyayı kaydetmedim."}
        return _do_add(st, p["name"], name, p["path"])

    # ---- sayfalar
    if re.search(r"^(ana sayfa|ana ekran|baslangic|ev)( goster| ac)?$", t):
        return {"do": {"tab": "home"}, "say": "Ana sayfa efendim."}
    if re.search(r"^(odalar|odalarim|odalari)( goster| listele| ac)?$|^evdeki odalar", t):
        names = ", ".join(r["name"] for r in d["rooms"])
        return {"do": {"tab": "rooms"}, "say": f"{len(d['rooms'])} odanız var: {names}." if d["rooms"] else "Henüz oda eklemediniz efendim. Oda ekle, salon diyebilirsiniz."}
    if re.search(r"^(esyalar|esyalarim|tum esyalar|butun esyalar|esya listesi)( goster| listele| ac)?$", t):
        return {"do": {"tab": "items", "filter": {}}, "say": f"{len(d['items'])} eşyanız var efendim."}
    if re.search(r"^(favoriler|favorilerim|favori esyalar|favorileri goster)( goster| listele)?$", t):
        f = [i["name"] for i in d["items"] if i["isFavorite"]]
        return {"do": {"tab": "items", "filter": {"fav": True}}, "say": ("Favorileriniz: " + ", ".join(f[:8]) + ".") if f else "Henüz favori eşyanız yok efendim."}
    if re.search(r"^(profil|ayarlar|yedekleme|yedek)( goster| ac)?$", t):
        return {"do": {"tab": "profile"}, "say": "Profil ve yedekleme ekranı efendim."}
    if re.search(r"\b(kac|kadar) (esyam|esya)\b|^(esya sayisi|istatistik)", t):
        s = yuvam.stats()
        return {"say": f"{s['items']} eşya, {s['rooms']} oda ve {s['favorites']} favori eşyanız var efendim."}
    if re.search(r"^(son eklenen\w*|yeni eklenen\w*)( goster| listele)?$", t):
        r = sorted(d["items"], key=lambda i: -i["createdAt"])[:5]
        return {"do": {"tab": "home"}, "say": ("Son eklenenler: " + ", ".join(i["name"] for i in r) + ".") if r else "Henüz eşya yok efendim."}
    if re.search(r"^(esya ekle|yeni esya|esya kaydet)$", t):
        return {"do": {"form": {}}, "say": "Eşya formu açıldı efendim. Ayrıca doğrudan, örneğin kulaklığı salonda TV ünitesinin sağ çekmecesine koydum diyebilirsiniz."}
    m = re.match(r"^(?:yeni )?oda (?:ekle|olustur|kaydet)\s+(.+)$|^(.+?) odasi(?:ni)? (?:ekle|olustur)$", t)
    if m:
        mr = re.search(r"(?i)oda\s+(?:ekle|oluştur|kaydet)\s+(.+)$", raw) or re.match(r"(?i)(.+?)\s+oda[sş]?[ıi]\w*\s+(?:ekle|oluştur)\w*$", raw)
        name = _cap((mr.group(1) if mr else (m.group(1) or m.group(2))).strip())
        r = yuvam.add_room(name)
        if not r:
            return {"say": "Odayı ekleyemedim efendim."}
        return {"do": _refresh(tab="rooms"), "say": f"{r['name']} odasını ekledim efendim."}
    m = re.match(r"^kategori (?:ekle|olustur)\s+(.+)$", t)
    if m:
        mr = re.search(r"(?i)kategori\s+(?:ekle|oluştur)\s+(.+)$", raw)
        c = yuvam.add_category(_cap(mr.group(1)) if mr else m.group(1))
        return {"do": _refresh(), "say": f"{c['name']} kategorisi hazır efendim."} if c else {"say": "Kategoriyi ekleyemedim efendim."}
    m = re.match(r"^(.+?) odasi(?:ni)? (?:ac|goster|gor)$|^(.+?) odasina (?:git|bak)$", t)
    if m:
        r = _match_room(d, m.group(1) or m.group(2))
        if not r:
            return {"say": "Böyle bir oda bulamadım efendim."}
        n = [i["name"] for i in d["items"] if i["roomId"] == r["id"]]
        return {"do": {"room": r["id"]}, "say": f"{r['name']}: {len(n)} eşya." + (" " + ", ".join(n[:6]) + "." if n else "")}

    # ---- yedek / sıfırlama
    if re.search(r"^yedek al$|^yedekle$|^yedegi al$|^verileri disa aktar", t):
        p = yuvam.export_backup()
        return {"say": "Yedeği Jarvis klasörüne yuvam_yedek.json olarak yazdım efendim. Telefondaki Yuvam uygulamasına yedekten geri yükle ile aktarabilirsiniz."}
    if re.search(r"^yedekten (yukle|geri yukle)|^yedegi (yukle|geri yukle)", t):
        st["confirm"] = {"kind": "restore"}
        return {"say": "Mevcut verileriniz Jarvis klasöründeki yuvam_yedek.json ile değiştirilecek. Onaylıyor musunuz? Evet ya da vazgeç deyin."}
    if re.search(r"^(tum|butun) (yuvam )?(verileri|esyalari|kayitlari) (sil|temizle)$|^yuvam\w* sifirla$", t):
        st["confirm"] = {"kind": "reset"}
        return {"say": "Tüm odalar ve eşyalar kalıcı olarak silinecek, geri dönüşü yok. Onaylıyor musunuz? Evet ya da vazgeç deyin."}

    # ---- favori / silme / geçmiş / taşıma
    m = re.match(r"^(.+?) (?:favorile|favoriye ekle|favorilere ekle|favorilerden cikar|favoriden cikar|favori yap)$", t)
    if m:
        it = _find_item(d, m.group(1))
        if not it:
            return {"say": "Böyle bir eşya bulamadım efendim."}
        fav = yuvam.toggle_favorite(it["id"])
        return {"do": _refresh(), "say": f"{it['name']} favorilere eklendi efendim." if fav else f"{it['name']} favorilerden çıkarıldı efendim."}
    m = re.match(r"^(?:(.+?) (?:esyasini |esyayi )?sil|(?:bu )?esyayi sil)$", t)
    if m:
        it = _find_item(d, m.group(1)) if m.group(1) and m.group(1) not in ("bu",) else (_find_item(d, st.get("last", "")) if st.get("last") else None)
        if not it:
            return {"say": "Hangi eşyayı sileceğimi bulamadım efendim."}
        st["confirm"] = {"kind": "item", "id": it["id"]}
        return {"say": f"{it['name']} kalıcı olarak silinecek, geri dönüşü yok. Onaylıyor musunuz? Evet ya da vazgeç deyin."}
    m = re.match(r"^(.+?) (?:gecmisi|gecmisini|konum gecmisi|konum gecmisini)(?: goster| oku)?$", t)
    if m:
        it = _find_item(d, m.group(1))
        if not it:
            return {"say": "Böyle bir eşya bulamadım efendim."}
        h = sorted([x for x in d["history"] if x["itemId"] == it["id"]], key=lambda x: -x["changedAt"])
        if not h:
            return {"do": {"open": it["id"]}, "say": f"{it['name']} henüz hiç yer değiştirmemiş efendim."}
        return {"do": {"open": it["id"]}, "say": f"{it['name']} en son {h[0]['previousLocation'].replace(' → ', ', ')} yerinden {h[0]['newLocation'].replace(' → ', ', ')} yerine taşınmış. Toplam {len(h)} değişiklik."}

    # ---- kaydetme / taşıma: "... koydum"
    if re.search(r"\b(koydum|biraktim|yerlestirdim|koyuyorum|tasidim|tasiyorum|yerlestir|koy|tasi|kaydet|ekle)\b", t) and not re.search(r"\b(nerede|nerde)\b", t):
        parsed = parse_add_phrase(raw, [r["name"] for r in d["rooms"]])
        if not parsed:
            return {"say": "Eşyanın adını anlayamadım efendim. Örneğin: kulaklığı salonda TV ünitesinin sağ çekmecesine koydum."}
        name, room_name, segs = parsed
        return _do_add(st, name, room_name, segs)

    # ---- arama ("kulaklığım nerede")
    q = extract_query(raw)
    if not q.strip():
        return {"say": _help()}
    res = yuvam.search(d, q)
    if not res:
        return {"do": {"search": q, "tab": "items"}, "say": f"{q} adlı bir eşya bulamadım efendim. Eşyalarınıza gözatabilir ya da yeni eşyayı koydum diyerek kaydedebilirsiniz."}
    it = res[0]
    yuvam.mark_viewed(it["id"])
    st["last"] = it["name"]
    more = f" Eşleşen {len(res) - 1} eşya daha var, ekranda görebilirsiniz." if len(res) > 1 else ""
    return {"do": _refresh(open=it["id"], search=q if len(res) > 1 else "", tab="items"), "say": _say_item(_data(), it) + more}


def _help() -> str:
    return ("Evim modundayım efendim. Eşyanın yerini sorabilirsiniz: kulaklığım nerede. Kaydetmek için: kulaklığı salonda TV ünitesinin sağ çekmecesine koydum. "
            "Ayrıca odalar, favoriler, eşyalar, oda ekle salon, kulaklığı favorile, kulaklığı sil, kulaklığın geçmişi, yedek al ya da çık diyebilirsiniz.")


def init_payload():
    return yuvam.init_payload()
