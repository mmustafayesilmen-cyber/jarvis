"""Yemek modu komutları: 'elimde tavuk, patates ve soğan var', 'biber de var', 'patatesi çıkar', 'evde un yok', 'sadece elimdekilerle', 'daha fazla',
'ikinciyi aç', 'malzemeler', 'eksikler', 'başla', 'sonraki', 'önceki', 'tekrar', 'adım üç', 'sayaç kur', 'eksikleri listeye ekle', 'sonuçlara dön', 'yeniden ara'.
Arama yemek.search ile ayrı iş parçacığında yapılır, sonuç NOTIFY ile gelir. Sayfa '@aç n' / '@adım n' / '@çıkar malzeme' gizli komutlarını yollar."""
import re

import scenes
import yemek as Y

HELP = ("Elinizdeki malzemeleri söyleyin, örneğin elimde tavuk, patates ve soğan var. İnternette tarif arar, eksiği en az olandan sıralarım. "
        "Biber de var, patatesi çıkar, evde un yok, sadece elimdekilerle, daha fazla ve ikinciyi aç diyebilirsiniz. "
        "Tarif açıkken malzemeler, eksikler, başla, sonraki, önceki, tekrar, adım üç, sayaç kur ve eksikleri listeye ekle komutları var.")
_ORD = {"birinci": 1, "ilk": 1, "ilki": 1, "ilkini": 1, "ikinci": 2, "üçüncü": 3, "dördüncü": 4, "beşinci": 5, "altıncı": 6, "yedinci": 7, "sekizinci": 8, "dokuzuncu": 9, "onuncu": 10}
_CARD = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10}
_ADD = r"\b(de|da|bir de|ayrıca|ekle|ekleyelim|dahil)\b"
_DEL = r"\b(çıkar|çıkart|sil|kaldır|yok|olmasın|hariç|istemiyorum|bitti|kalmadı)\w*"


def _out(say: str, extra=None):
    do = {"snap": Y.snapshot()}
    if extra:
        do.update(extra)
    return {"do": do, "say": say}


def _step_say(c, i):
    a = c["adim"][i]
    dk = Y.step_timer(a)
    tail = f" Bu adım yaklaşık {dk} dakika sürüyor, sayaç kur derseniz kurarım." if dk >= 3 else ""
    end = " Son adım bu; bitince afiyet olsun!" if i == len(c["adim"]) - 1 else ""
    return f"Adım {i + 1} / {len(c['adim'])}: {a}{tail}{end}"


def _ordinal(raw: str):
    """'ikinciyi aç', '3 numara', '2. tarif', 'üç numaralı', 'sonuncu' -> 1 tabanlı sıra."""
    for w in re.findall(r"\w+", raw):
        for k, v in _ORD.items():
            if w.startswith(k) and len(w) - len(k) <= 4:       # 'ikinciyi', 'ilkini' ama 'ilkbahar' değil
                return v
    m = re.search(r"\b(\d{1,2})\s*(\.|'?(?:inci|ıncı|uncu|üncü|nci|ncı|ncu|ncü)|numara\w*|nolu|tarif\w*|yi|yı|u|ü|i|ı)?\b", raw)
    if m and (m.group(2) or re.search(r"\b(aç|göster|oku|seç)\b", raw)):
        return int(m.group(1))
    m = re.search(r"\b(bir|iki|üç|dört|beş|altı|yedi|sekiz|dokuz|on)(inci|nci|ncı|üncü|uncu|i|yi|ı|yı|u|ü|yu|yü)?\s*(numara\w*|nolu|tarif\w*|aç\w*|göster\w*)\b", raw)
    if m:
        return _CARD[m.group(1)]
    if re.search(r"\b(sonuncu\w*|en sondaki)\b", raw):
        return len(Y.visible())
    return None


def _open(i: int):
    r = Y.open_index(i)
    if not r:
        return _out(f"{i + 1}. sırada tarif yok efendim; ekranda {len(Y.visible())} tarif var.")
    kisi = f", {r['kisi']}" if r["kisi"] else ""
    sure = f", yaklaşık {r['dk']} dakika" if r["dk"] else ""
    miss = "Eksik malzemeniz yok." if not r["miss"] else "Eksikler: " + ", ".join(r["miss"]) + "."
    return _out(f"{r['ad']}{sure}{kisi}. {miss} Malzemeleri ekranda gösteriyorum; başla derseniz adımları okurum.")


def _by_name(t: str):
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return None
    q = Y.fold(re.sub(r"\b(tarif\w*|aç\w*|göster\w*|oku\w*|olanı|olan|şu)\b", " ", t))
    if len(q) < 4:
        return None
    best, bi = 0, None
    for i, x in enumerate(Y.visible()):
        sc = fuzz.token_set_ratio(q, Y.fold(x["ad"]))
        if sc > best:
            best, bi = sc, i
    return bi if best >= 82 else None


def _rescore():
    """Temel malzeme ayarı değişince (evde un yok) tarifler yeniden indirilmeden puanlanır."""
    for x in Y.S["res"]:
        x.update(Y.score(x, Y.S["items"], Y.S["nostaple"]))
    Y.S["res"].sort(key=lambda r: (-r["s"], len(r["miss"])))


def _search(items, lead=""):
    Y.search(items)
    return _out(f"{lead}{Y.say_list(items)} ile yapılabilecek tarifleri internette arıyorum efendim, birkaç saniye sürer.")


def _recipe_cmd(t: str, raw: str, c: dict):
    if re.search(r"\b(eksik\w*|neler eksik|ne eksik)\b", t) and not re.search(r"\b(ekle|liste\w*)\b", t):
        return _out("Eksik malzemeniz yok efendim." if not c["miss"] else "Eksikler: " + ", ".join(c["miss"]) + ".", {"show": "mal"})
    if re.search(r"\b(alışveriş|liste\w*)\b.*\b(ekle|at|yaz)\w*|\beksik\w* (ekle|yaz|listeye)", t):
        import tarif
        snap = Y.snapshot()["cur"]
        add = [m["t"] for m in snap["mal"] if m["ok"] is False and not m["opt"]]
        if not add:
            return _out("Eksik malzeme yok, listeye eklenecek bir şey çıkmadı efendim.")
        items = tarif.shopping()
        items += [x for x in add if x not in items]
        tarif.shopping_save(items)
        return _out(f"{len(add)} eksik malzemeyi alışveriş listesine ekledim efendim: " + ", ".join(c["miss"][:6]) + ".")
    if re.search(r"\b(malzeme\w*|neler lazım|ne lazım|ne gerek\w*)\b", t):
        return _out(f"{c['ad']} için malzemeler: " + "; ".join(c["mal"]) + ".", {"show": "mal"})
    if re.search(r"\b(sayaç|zamanlayıcı|süre tut)\b.*\b(kur|başlat|ayarla)\w*|\b(kur|başlat)\w*\b.*\b(sayaç|zamanlayıcı)|^(evet|olur|kur|sayaç kur)$", t):
        i = max(0, Y.S["step"])
        m = re.search(r"(\d{1,3})\s*(dakika|dk)", t)
        d = int(m.group(1)) if m else Y.step_timer(c["adim"][i])
        if not d:
            return _out("Bu adımda süre geçmiyor efendim. Örneğin on dakikalık sayaç kur diyebilirsiniz.")
        return _out(f"{d} dakikalık sayaç başladı efendim.", {"timer": d, "label": f"{c['ad']} · adım {i + 1}"})
    m = re.search(r"\badım\s+(\w+)", t)
    if m:
        n = scenes.num_in(m.group(1)) or _CARD.get(m.group(1)) or _ordinal(m.group(1))
        if n and n >= 1:
            i = min(n, len(c["adim"])) - 1
            Y.S["step"] = i
            return _out(_step_say(c, i))
    if re.search(r"\b(başla|başlayalım|başlat|hadi başla)\b", t) and Y.S["step"] < 0:
        Y.S["step"] = 0
        return _out("Başlıyoruz efendim. " + _step_say(c, 0))
    if re.search(r"\b(sonraki|devam|ileri|bitti|tamam|tamamdır|yaptım|oldu|geç|sıradaki)\b", t):
        i = Y.S["step"] + 1
        if i >= len(c["adim"]):
            Y.S["step"] = len(c["adim"]) - 1
            return _out(f"{c['ad']} hazır efendim, afiyet olsun!", {"done": True})
        Y.S["step"] = i
        return _out(_step_say(c, i))
    if re.search(r"\b(önceki|bir önceki|geri git|geri al)\b", t):
        i = max(0, Y.S["step"] - 1)
        Y.S["step"] = i
        return _out(_step_say(c, i))
    if re.search(r"\b(tekrar|tekrarla|yeniden oku|ne demiştin|anlamadım)\b", t) and not re.search(r"\bara\w*", t):
        return _out(_step_say(c, max(0, Y.S["step"])))
    if re.search(r"\b(ne kadar sürer|kaç dakika|süresi)\b", t):
        return _out(f"Yaklaşık {c['dk']} dakika efendim." if c["dk"] else "Sitede süre bilgisi yok efendim.")
    if re.search(r"\b(kaç kişilik|kaç kişi)\b", t):
        return _out(f"{c['kisi']} efendim." if c["kisi"] else "Sitede porsiyon bilgisi yok efendim.")
    if re.search(r"\b(kaynak\w*|hangi site\w*|nereden)\b", t):
        return _out(f"Bu tarif {c['site']} sitesinden efendim.")
    if re.search(r"\b(sonuç\w*|liste\w*|geri dön|geri|başka tarif|diğer tarif\w*|tariflere dön)\b", t):
        Y.S.update(cur=None, step=-1)
        return _out("Sonuçlara döndük efendim.")
    return None


def yemek_mode(text: str, st: dict):
    raw = text.strip()
    if raw.startswith("@"):                         # sayfa düğmeleri
        cmd, _, arg = raw[1:].partition(" ")
        if cmd == "aç" and arg.isdigit():
            return _open(int(arg))
        if cmd == "adım" and arg.isdigit() and Y.cur():
            c = Y.cur()
            Y.S["step"] = min(int(arg), len(c["adim"]) - 1)
            return _out(_step_say(c, Y.S["step"]))
        if cmd == "çıkar" and arg in Y.S["items"]:
            items = [x for x in Y.S["items"] if x != arg]
            return _search(items) if items else _clear()
        if cmd == "temel":                            # temel malzemeyi aç/kapat (evde yok)
            ns = Y.S["nostaple"]
            ns.remove(arg) if arg in ns else ns.append(arg)
            _rescore()
            return _out("")
        return None
    t = scenes.norm(text)
    low = raw.replace("İ", "i").replace("I", "ı").lower()
    if not t:
        return None
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar|nasıl kullan\w*)\b", t):
        return _out(HELP)
    c = Y.cur()
    if c:
        r = _recipe_cmd(t, low, c)
        if r is not None:
            return r
    if re.search(r"\b(temizle|sıfırla|yeni arama|baştan)\b", t):
        return _clear()
    if re.search(r"\b(tekrar ara|yeniden ara|yenile|bir daha ara|ara)\b", t) and not Y.parse_items(t):
        return _search(Y.S["items"]) if Y.S["items"] else _out("Önce elinizdeki malzemeleri söyleyin efendim.")
    if Y.S["busy"]:
        if not Y.parse_items(t):
            return _out("Hâlâ arıyorum efendim, birkaç saniye.")
    if re.search(r"\b(sadece|yalnızca)\b.*\b(elimde\w*|evde\w*|eksiksiz|bunlarla|olanlar\w*)|\beksiksiz\w*|\beksiği olmayan", t):
        Y.S.update(only=True, show=9)
        return _out(Y.summary())
    if re.search(r"\b(hepsini|tümünü|tamamını|eksikli\w*)\b.*\b(göster|getir|aç)\w*|\bhepsi\b", t):
        Y.S.update(only=False)
        return _out(Y.summary())
    if re.search(r"\b(daha fazla|daha çok|devamı\w*|başka (tarif|seçenek)\w*|diğer\w* tarif\w*|sonrakiler|fazlası)\b", t):
        if Y.S["show"] >= len([x for x in Y.S["res"] if not Y.S["only"] or not x["miss"]]):
            return _out("Gösterilecek başka tarif kalmadı efendim. Yeni bir malzeme ekleyerek aramayı genişletebilirsiniz.")
        Y.S["show"] += 9
        return _out(f"Ekranda şimdi {len(Y.visible())} tarif var efendim.")
    m = re.search(r"\b(evde|elimde|dolapta)?\s*(\w+)\s+(yok|kalmadı|bitti)\b", t)
    if m:
        lab = Y.label_of(m.group(2)) or Y.label_of(re.sub(r"(ı|i|u|ü|yı|yi|yu|yü)$", "", m.group(2)))
        if lab in Y.STAPLES:
            if lab not in Y.S["nostaple"]:
                Y.S["nostaple"].append(lab)
            _rescore()
            return _out(f"Tamam efendim, {lab} gerektiren tarifler artık eksikli sayılıyor. " + (Y.summary() if Y.S["res"] else ""))
    if re.search(r"\b(malzemelerim|elimdekiler|listem)\b.*\b(neler|ne|oku|söyle)\b|\bneler var\b", t) and not Y.parse_items(t):
        return _out(("Elinizdekiler: " + ", ".join(Y.S["items"]) + ".") if Y.S["items"] else "Henüz malzeme söylemediniz efendim.")
    n = _ordinal(low)
    if n and Y.visible():
        return _open(n - 1)
    items = Y.parse_items(text)
    if items:
        if re.search(_DEL, t) and Y.S["items"] and not re.search(r"\bvar\b", t):
            rest = [x for x in Y.S["items"] if x not in items]
            if len(rest) == len(Y.S["items"]):
                return _out(f"{', '.join(items)} zaten listede yok efendim.")
            return _search(rest, f"{', '.join(i for i in items if i in Y.S['items'])} çıkarıldı. ") if rest else _clear()
        if re.search(_ADD, t) and Y.S["items"] and not re.search(r"\b(elimde|evde|buzdolab\w*)\b.*\b(ve|,)", t):
            new = Y.S["items"] + [x for x in items if x not in Y.S["items"]]
            return _search(new[:8])
        return _search(items)
    i = _by_name(t)
    if i is not None:
        return _open(i)
    if not Y.S["items"]:
        return _out("Elinizdeki malzemeleri söyleyin efendim, örneğin elimde tavuk, patates ve soğan var.")
    return _out("Anlayamadım efendim. Malzeme ekleyebilir, ikinciyi aç diyebilir ya da yardım diyebilirsiniz.")


def _clear():
    Y.S.update(items=[], res=[], cur=None, step=-1, err="", busy="", only=False, show=9, q=Y.S["q"] + 1)
    return _out("Liste temizlendi efendim. Elinizdeki malzemeleri söyleyin.")


def init_payload():
    if Y.PENDING:                                   # mod normal Jarvis'ten 'elimde X var' ile açıldı
        items = list(Y.PENDING)
        Y.PENDING.clear()
        Y.search(items)
    return Y.snapshot()
