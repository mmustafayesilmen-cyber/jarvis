"""Yemek modu verisi: elinizdeki malzemeleri söylersiniz, Jarvis internette (yemek.com arama ucu) tarif arar, her adayın GERÇEK malzeme listesini
sayfanın schema.org Recipe JSON-LD verisinden okur ve elinizdekilerle ne kadar örtüştüğüne göre sıralar (eksik malzeme sayısı, kullanılan malzeme oranı).
Tuz, su, yağ, baharat, un, şeker, salça "temel" sayılır (evde var kabul edilir; 'evde un yok' denince o oturumda sayılmaz).
Arama ağ işi olduğu için ayrı iş parçacığında yapılır, sonuç NOTIFY ile sayfaya gider. Okunan tarifler yemek_cache.json'da saklanır (gitignored), aynı tarif
tekrar indirilmez; istek sayısı bilerek düşük tutulur (arama başına en çok ~8 arama sayfası + ~32 tarif sayfası). Ayrıştırıcı genel JSON-LD okur; başka
bir site eklemek için yalnızca SOURCES'a arama işlevi eklemek yeter."""
import html
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yemek_cache.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
NOTIFY = None                                      # main.py: NOTIFY(do, say) -> sayfaya iletir ve mod açıksa söyler
PENDING = []                                       # mod kapalıyken 'elimde X var' denince: mod açılınca bu malzemelerle aranır
S = {"items": [], "busy": "", "err": "", "res": [], "cur": None, "step": -1, "only": False, "nostaple": [], "show": 9, "q": 0}
_lock = threading.Lock()
_cache = None
MAX_PAGES = 32

# ------------------------------------------------------------------ malzeme sözlüğü
# (etiket, desenler, tür, üst) — desenler katlanmış (ç→c, ğ→g, ı→i, ö→o, ş→s, ü→u) küçük harf metinde sözcük başından eşleşir, sonuna ek gelebilir.
# Sıra önemlidir: özel olan (domates salçası, kaşar peyniri, toz biber) genelden (domates, peynir, biber) önce gelir; eşleşen kısım maskelenir.
# tür: "s" temel (evde var sayılır), "m" malzeme. üst: genel aile (kullanıcı 'peynir' derse kaşar da sayılır).
LEX = [
 ("et suyu", [r"(tavuk|et|kemik|sebze|dana|balik) suyu", r"bulyon", r"et bulyon", r"tavuk bulyon"], "s", None),
 ("salça", [r"(domates |biber |aci biber |tatli biber )?salca"], "s", None),
 ("pul biber", [r"pul biber", r"pul ?biber", r"kirmizi pul biber", r"isot", r"urfa biberi"], "s", None),
 ("toz biber", [r"(kirmizi )?(toz|tatli toz|aci toz) biber", r"paprika", r"kirmizi biber tozu"], "s", None),
 ("karabiber", [r"kara ?biber", r"tane karabiber"], "s", None),
 ("sarımsak tozu", [r"sarimsak tozu", r"sogan tozu", r"zencefil tozu"], "s", None),
 ("baharat", [r"kimyon", r"kekik", r"kuru nane", r"nane \(kuru\)", r"yenibahar", r"tarcin", r"zerdecal", r"kori", r"kari\b", r"sumak", r"defne", r"karanfil",
              r"muskat", r"kakule", r"kisnis", r"rezene", r"cemen", r"biberiye", r"susam", r"corek ?otu", r"haslanmis baharat", r"kofte baharati", r"baharat",
              r"tuz biber", r"reyhan", r"tarhun", r"(toz |kuru )?zencefil", r"vanilin", r"vanilya", r"kabartma tozu", r"karbonat", r"hardal tohumu", r"safran", r"pul tuz"], "s", None),
 ("tuz", [r"tuz\b", r"tuzu\b", r"deniz tuzu", r"kaya tuzu"], "s", None),
 ("tereyağı", [r"tere ?yag", r"margarin"], "m", None),
 ("sıvı yağ", [r"(sivi|aycicek|misirozu|misir|bitkisel|kizartma) ?yag", r"zeytin ?yag", r"yag\b", r"yagi\b"], "s", None),
 ("sirke", [r"(uzum |elma |nar )?sirke"], "s", None),
 ("şeker", [r"(toz |pudra |esmer )?seker\b", r"(toz |pudra |esmer )?sekeri\b", r"pudra sekeri"], "s", None),
 ("un", [r"un\b", r"unu\b", r"bugday unu", r"beyaz un"], "s", None),
 ("su", [r"(icme |maden |haslama |sise maden |sise )?suyu?\b", r"sicak su", r"ilik su", r"soguk su", r"kaynar su", r"buzlu su", r"soda\b"], "s", None),
 ("buz", [r"buz\b"], "s", None),
 # --- et, tavuk, balık
 ("tavuk", [r"(tavu[kg]|pilic|hindi)\w*( (eti|etleri|gogs\w*|gogus\w*|but\w*|baget\w*|kanad\w*|kanat\w*|incik\w*|bonfile\w*|pirzola\w*|kalca\w*|fileto\w*|kusbas\w*|kiyma\w*|derisi\w*|ciger\w*))?",
            r"baget", r"kanat", r"but\b", r"butlar", r"gogus eti", r"bonfile tavuk"], "m", None),
 ("kıyma", [r"((dana|kuzu|yagli|yagsiz|az yagli|orta yagli|kirmizi et) )?kiyma", r"kofte\b(?! baharat)", r"koftelik"], "m", None),
 ("sucuk", [r"sucu[kg]"], "m", None),
 ("pastırma", [r"pastirma"], "m", None),
 ("sosis", [r"sosis", r"salam", r"jambon", r"fume"], "m", None),
 ("et", [r"kusbasi", r"dana", r"kuzu", r"biftek", r"antrikot", r"bonfile", r"kontrfile", r"incik", r"kemikli et", r"etler?\b", r"eti\b", r"et\b", r"kavurma", r"pirzola", r"kaburga"], "m", None),
 ("ton balığı", [r"ton balig", r"ton\b"], "m", "balık"),
 ("somon", [r"somon"], "m", "balık"),
 ("karides", [r"karides"], "m", None),
 ("midye", [r"midye", r"kalamar", r"ahtapot"], "m", None),
 ("balık", [r"balik", r"levrek", r"cipura", r"hamsi", r"palamut", r"lufer", r"uskumru", r"sardalya", r"mezgit", r"istavrit", r"alabalik", r"lagos", r"barbun"], "m", None),
 # --- süt ürünleri, yumurta
 ("yumurta", [r"yumurta"], "m", None),
 ("kaşar", [r"kasar", r"cheddar", r"gouda", r"tost peynir"], "m", "peynir"),
 ("lor", [r"lor\b", r"lor peynir"], "m", "peynir"),
 ("mozzarella", [r"mozzarella", r"mozarella"], "m", "peynir"),
 ("parmesan", [r"parmesan", r"parmezan", r"eski kasar"], "m", "peynir"),
 ("krem peynir", [r"krem peynir", r"labne", r"mascarpone", r"maskarpone"], "m", "peynir"),
 ("peynir", [r"(beyaz |ezine |tulum |keci |inek |feta |dil |cecil |orgu )?peynir", r"feta"], "m", None),
 ("krema", [r"krema", r"sivi krema", r"krem santi", r"kaymak"], "m", None),
 ("yoğurt", [r"yogurt", r"suzme yogurt"], "m", None),
 ("süt", [r"sut\b", r"sutu\b", r"sicak sut", r"ilik sut", r"soguk sut", r"sut tozu"], "m", None),
 # --- tahıl, bakliyat, hamur
 ("pirinç", [r"pirinc", r"baldo", r"osmancik", r"basmati"], "m", None),
 ("bulgur", [r"bulgur"], "m", None),
 ("şehriye", [r"sehriye", r"arpa sehriye", r"tel sehriye"], "m", None),
 ("makarna", [r"makarna", r"spagetti", r"penne", r"fettucc?ine", r"burgu", r"kelebek makarna", r"eriste", r"noodle", r"lazanya", r"tagliatelle", r"linguine", r"farfalle", r"rigatoni", r"manti"], "m", None),
 ("kırmızı mercimek", [r"kirmizi mercimek"], "m", "mercimek"),
 ("yeşil mercimek", [r"yesil mercimek"], "m", "mercimek"),
 ("mercimek", [r"mercimek"], "m", None),
 ("nohut", [r"nohut"], "m", None),
 ("kuru fasulye", [r"kuru fasulye", r"barbunya", r"borulce"], "m", None),
 ("taze fasulye", [r"taze fasulye", r"cali fasulye", r"ayse kadin"], "m", None),
 ("yufka", [r"yufka"], "m", None),
 ("lavaş", [r"lavas", r"tortilla", r"durum"], "m", None),
 ("milföy", [r"milfoy", r"puf boregi hamuru"], "m", None),
 ("ekmek", [r"(bayat )?ekmek", r"galeta", r"panko", r"ekmek kirintisi", r"tost ekmegi", r"bazlama", r"pide\b", r"hamburger ekmegi", r"sandvic ekmegi"], "m", None),
 ("irmik", [r"irmik"], "m", None),
 ("nişasta", [r"nisasta"], "m", None),
 ("yulaf", [r"yulaf"], "m", None),
 ("kinoa", [r"kinoa"], "m", None),
 ("maya", [r"maya\b", r"kuru maya", r"yas maya", r"instant maya"], "m", None),
 # --- sebze
 ("patates", [r"patates"], "m", None),
 ("domates", [r"domates", r"cherry", r"ceri domates"], "m", None),
 ("yeşil soğan", [r"yesil sogan", r"taze sogan"], "m", "soğan"),
 ("soğan", [r"(kuru |mor |arpacik )?sogan", r"arpacik"], "m", None),
 ("sarımsak", [r"sarimsak"], "m", None),
 ("biber", [r"(sivri|carliston|kapya|dolmalik|yesil|kirmizi|sari|tatli|aci|kirmizi tatli|kirmizi kapya|kozlenmis|kaliforniya|jalapeno|kil|cin) ?biber", r"biber\b", r"biberi\b", r"biberler"], "m", None),
 ("havuç", [r"havuc"], "m", None),
 ("kabak", [r"kaba[kg]", r"bal kaba[kg]"], "m", None),
 ("patlıcan", [r"patlican"], "m", None),
 ("ıspanak", [r"ispanak"], "m", None),
 ("pazı", [r"pazi\b", r"pazilar"], "m", None),
 ("kapari", [r"kapari"], "m", None),
 ("pırasa", [r"pirasa"], "m", None),
 ("lahana", [r"(beyaz |kirmizi |mor |brüksel |bruksel )?lahana", r"karalahana"], "m", None),
 ("karnabahar", [r"karnabahar"], "m", None),
 ("brokoli", [r"brokoli"], "m", None),
 ("mantar", [r"mantar"], "m", None),
 ("bezelye", [r"bezelye"], "m", None),
 ("mısır", [r"misir\b", r"misir tanesi", r"konserve misir", r"misiri\b"], "m", None),
 ("kereviz", [r"kereviz"], "m", None),
 ("enginar", [r"enginar"], "m", None),
 ("bamya", [r"bamya"], "m", None),
 ("salatalık", [r"salatalik", r"hiyar", r"kornison", r"tursu"], "m", None),
 ("marul", [r"marul", r"kivircik", r"roka", r"iceberg", r"aysberg", r"yesillik"], "m", None),
 ("maydanoz", [r"maydanoz"], "m", None),
 ("dereotu", [r"dere ?otu"], "m", None),
 ("taze nane", [r"taze nane", r"nane yaprak", r"nane\b"], "m", None),
 ("fesleğen", [r"feslegen"], "m", None),
 ("pancar", [r"pancar"], "m", None),
 ("turp", [r"turp"], "m", None),
 ("semizotu", [r"semiz ?otu"], "m", None),
 ("asma yaprağı", [r"asma yapra", r"yaprak\b", r"sarmalik yaprak"], "m", None),
 ("zeytin", [r"zeytin\b", r"zeytinler", r"zeytini\b", r"siyah zeytin", r"yesil zeytin"], "m", None),
 # --- meyve, kuruyemiş, tatlı
 ("limon", [r"limon"], "m", None),
 ("portakal", [r"portakal"], "m", None),
 ("mandalina", [r"mandalina"], "m", None),
 ("greyfurt", [r"greyfurt"], "m", None),
 ("elma", [r"elma\b", r"elmal", r"elmayi", r"elmalar"], "m", None),
 ("muz", [r"muz\b", r"muzlar", r"muzu\b"], "m", None),
 ("çilek", [r"cilek"], "m", None),
 ("hindistan cevizi", [r"hindistan ?cevizi"], "m", None),
 ("ceviz", [r"ceviz"], "m", None),
 ("fındık", [r"findik"], "m", None),
 ("badem", [r"badem"], "m", None),
 ("fıstık", [r"(antep |cam |yer )?fisti[kg]"], "m", None),
 ("üzüm", [r"(kuru )?uzum", r"kus uzumu"], "m", None),
 ("kayısı", [r"kayisi"], "m", None),
 ("hurma", [r"hurma"], "m", None),
 ("avokado", [r"avokado"], "m", None),
 ("nar", [r"nar\b", r"nar eksisi", r"nar tanesi"], "m", None),
 ("çikolata", [r"cikolata", r"damla cikolata"], "m", None),
 ("kakao", [r"kakao"], "m", None),
 ("bal", [r"bal\b", r"bali\b"], "m", None),
 ("pekmez", [r"pekmez"], "m", None),
 ("tahin", [r"tahin"], "m", None),
 ("reçel", [r"recel", r"marmelat"], "m", None),
 ("bisküvi", [r"biskuvi", r"kedi dili"], "m", None),
 ("mayonez", [r"mayonez"], "m", None),
 ("ketçap", [r"ketcap", r"ketchup"], "m", None),
 ("hardal", [r"hardal"], "m", None),
 ("soya sosu", [r"soya sosu"], "m", None),
 ("domates sosu", [r"domates sosu", r"pasata", r"rendelenmis domates"], "m", "domates"),
]
_LEX = [(lab, re.compile(r"\b(?:" + "|".join(ps) + r")\w*"), kind, up) for lab, ps, kind, up in LEX]
BY_LABEL = {lab: (lab, rx, kind, up) for lab, rx, kind, up in _LEX}
STAPLES = [lab for lab, _p, kind, _u in LEX if kind == "s"]
_PURE = {"tuz", "su", "buz", "sıvı yağ", "karabiber", "pul biber", "toz biber", "baharat", "sarımsak tozu", "et suyu", "sirke"}

_FOLD = str.maketrans("çğıöşüâîûÇĞİÖŞÜÂÎÛ", "cgiosuaiucgiosuaiu")
_UNITS = (r"su bardag\w*|cay bardag\w*|kahve fincan\w*|cay fincan\w*|yemek kasig\w*|tatli kasig\w*|cay kasig\w*|kahve kasig\w*|kasik\w*|bardak\w*|fincan\w*|"
          r"kase\w*|kup\w*|litre\w*|lt|ml|gr|gram\w*|g|kg|kilo\w*|adet|tane\w*|dis\b|disi\b|demet\w*|bag\b|bagi\b|tutam\w*|avuc\w*|dilim\w*|paket\w*|kutu\w*|kavanoz\w*|"
          r"dal\b|dali\b|parca\w*|kucuk boy|orta boy|buyuk boy|boy\b|buyuk|orta|kucuk|yarim|ceyrek|silme|tepeleme|dolusu|kadar|yaklasik|cimdik|fiske|bir|iki|uc|dort|bes|alti|yedi|sekiz|dokuz|on")
_RX_UNITS = re.compile(r"\b(?:" + _UNITS + r")\b")
_RX_NUM = re.compile(r"[\d½¼¾⅓⅔.,/\-–]+")
_OPTIONAL = re.compile(r"istege bagli|susle|servis icin|uzeri icin|uzerine|garnitur|tercihe gore|arzuya gore|opsiyonel")
_ALT = re.compile(r"\b(veya|ya da|yerine|yoksa)\b")


def fold(s: str) -> str:
    s = str(s).replace("İ", "i").replace("I", "ı").lower().translate(_FOLD)
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s()]", " ", s)).strip()


def clean_line(line: str) -> str:
    """'1,5 su bardağı ceviz içi (iri kırılmış)' -> 'ceviz ici'"""
    t = re.sub(r"[()]", " ", fold(re.sub(r"\([^()]*\)", " ", re.sub(r"\([^()]*\)", " ", str(line)))))
    t = _RX_NUM.sub(" ", t)
    t = _RX_UNITS.sub(" ", t)
    return " ".join(t.split())


def label_of(word: str):
    """Kullanıcının söylediği malzeme -> sözlük etiketi (yoksa None)."""
    f = fold(word)
    for lab, rx, _k, _u in _LEX:
        m = rx.match(f)
        if m and m.end() >= len(f) - 3:
            return lab
    return None


def line_reqs(line: str):
    """Bir malzeme satırından gereksinimler: [(etiket kümesi, ad)], temel mi, isteğe bağlı mı. Etiket kümesi 'veya' ile alternatifleri tutar."""
    raw = fold(line)
    opt = bool(_OPTIONAL.search(raw))
    t = clean_line(line)
    if not t or raw.endswith(" icin") and not re.search(r"\d", raw):
        return [], True, opt
    found, masked = [], t
    for lab, rx, kind, _u in _LEX:
        for m in rx.finditer(masked):
            found.append((m.start(), lab, kind))
            masked = masked[:m.start()] + " " * (m.end() - m.start()) + masked[m.end():]
    found.sort()
    mains = [(lab, kind) for _s, lab, kind in found]
    if not mains:
        name = " ".join(t.split()[:4])
        return ([({"?" + name}, name)] if len(name) >= 3 else []), False, opt
    if re.search(r"kasig|tutam|cimdik|fiske", raw):        # '1 tatlı kaşığı kırmızı biber' toz biberdir
        mains = [(lab, "s" if lab == "biber" else kind) for lab, kind in mains]
    groups = [x for x in mains if x[1] == "m"]
    if not groups:
        return [], True, opt
    if _ALT.search(raw) and len(groups) > 1:
        return [({lab for lab, _k in groups}, " ya da ".join(lab for lab, _k in groups))], False, opt
    return [({lab}, lab) for lab, _k in dict.fromkeys(groups)], False, opt


# ------------------------------------------------------------------ kullanıcının söylediği malzemeler
_SAY_STOP = set(fold(w) for w in (
    "elimde evde buzdolabında buzdolabımda dolapta mutfakta var varsa olan bulunan sadece yalnızca bir biraz birkaç az çok tane adet kilo gram yarım ve ile de da "
    "ayrıca bir de hem ne neler yapabilirim yapsam pişirsem pişireyim yapayım yapılır pişirilir öner önerir öneri önerisi önerin bul bana bize tarif tarifi tarifler "
    "tarifleri yemek yemeği yemekler yemekleri internetten internette ara arar arasana bak bakar mısın mısın misin musun müsün olur şey şeyler kalan kaldı artık "
    "malzeme malzemeler malzemelerim malzemelerle bunlarla bunlardan şunlar şunlarla neyle hangi ne pişirebilirim yapabiliriz akşam öğle sabah kahvaltı için "
    "için lazım istiyorum isterim yemekte acıktım aç şu bu o ben benim bizim içinde içerisinde hazır taze kuru sıcak soğuk dondurulmuş konserve paket paketi "
    "yok ekle çıkar sil de da daha dahil hariç olmadan malzemeyle malzemelerimle evdekilerle elimdekilerle elimdekiler evdekiler mümkün kolay pratik hızlı "
    "akşam akşama akşamlık öğlen öğleye bugün yarın misafir misafire çocuk çocuklar kişilik kişi kişiye olsun olabilir güzel lezzetli sağlıklı nefis "
    "aramak araştır araştırır bulur bulabilir misin mısın söyle göster getir şey birşey yapalım pişirelim yiyelim yiyebilirim yemeklik "
    "mod modu modunu modundan modda ekran ekranı ekranını pencere penceresi aç açar açsana açın kapat kapa mutfak mutfağa mutfakta jarvis efendim lütfen hadi "
    "göre malzemeden malzemeye malzemelere elimdekilerle evdekilerle internet").split())
_SUFFIX = re.compile(r"(lerim|larim|lerimiz|larimiz|imiz|umuz|im|um|in|un|m|ler|lar|ı|i|u|yi|yu|yı|nin|nun|la|le|yla|yle)$")


def parse_items(text: str):
    """'elimde tavuk, patates ve biraz kaşar var' -> ['tavuk', 'patates', 'kaşar']. Bilinmeyen sözcükler (3+ harf) aranacak malzeme olarak kalır."""
    t = re.sub(r"\b(tarif|yardim|teklif|kontrol|servis|tavsiye) et\w*", " ", fold(text))
    out = []
    taken = t
    for lab, rx, kind, _u in _LEX:                  # önce çok sözcüklü/özel etiketler (sözlük sırası)
        for m in rx.finditer(taken):
            out.append((m.start(), lab))
            taken = taken[:m.start()] + " " * (m.end() - m.start()) + taken[m.end():]
    segs = [(m.start(), m.end()) for m in re.finditer(r"[^,;]+?(?=,|;|\bve\b|\bile\b|\bbir de\b|\bayrica\b|$)", t)]
    for m in re.finditer(r"\b[a-z]{3,}\b", taken):
        w = m.group(0)
        if w in _SAY_STOP:
            continue
        base = _SUFFIX.sub("", w)
        lab = label_of(base) if len(base) >= 3 else None
        if not lab:
            lab = _fuzzy(w)
        if lab:
            out.append((m.start(), lab))
            continue
        seg = next(((a, b) for a, b in segs if a <= m.start() < b), None)      # bilinmeyen sözcük yalnızca liste parçasında tek başınaysa ('hellim ve kuskus')
        if seg and base not in _SAY_STOP and len(w) >= 4:
            words = [x for x in re.findall(r"[a-z]{3,}", t[seg[0]:seg[1]]) if x not in _SAY_STOP]
            if words == [w] and t[seg[0]:seg[1]] == taken[seg[0]:seg[1]]:
                out.append((m.start(), w))
    out.sort()
    res = []
    for _s, lab in out:
        if lab not in res:
            res.append(lab)
    return res[:8]


def _fuzzy(w: str):
    try:
        from rapidfuzz import process, fuzz
    except ImportError:
        return None
    names = {fold(lab): lab for lab, _p, kind, _u in LEX if kind == "m"}
    hit = process.extractOne(w, list(names), scorer=fuzz.ratio, score_cutoff=84)
    return names[hit[0]] if hit else None


def _have(labs: set, items: list) -> bool:
    """Gereksinim (etiketler) kullanıcıdaki malzemelerden biriyle karşılanıyor mu? 'peynir' diyen kaşarı da karşılar."""
    for it in items:
        for lab in labs:
            if lab == it:
                return True
            if lab.startswith("?"):
                if fold(it) in lab:
                    return True
                continue
            up = BY_LABEL.get(lab, (None, None, None, None))[3]
            if up and up == it:
                return True
    return False


# ------------------------------------------------------------------ JSON-LD tarif ayrıştırma
def _txt(x) -> str:
    s = html.unescape(re.sub(r"<[^>]+>", " ", str(x or "")))
    return " ".join(s.split())


def _mins(iso) -> int:
    m = re.match(r"P(?:T)?(?:(\d+)H)?(?:(\d+)M)?", str(iso or ""))
    return (int(m.group(1) or 0) * 60 + int(m.group(2) or 0)) if m else 0


def _steps(ins) -> list:
    out = []
    if isinstance(ins, str):
        parts = [p for p in re.split(r"\n+|(?<=\.)\s+(?=\d+[.)-]\s)", _txt(ins.replace("<br", "\n<br").replace("</p>", "\n")))]
        out += parts
    elif isinstance(ins, dict):
        if ins.get("itemListElement"):
            out += _steps(ins["itemListElement"])
        else:
            out.append(_txt(ins.get("text") or ins.get("name")))
    elif isinstance(ins, list):
        for x in ins:
            out += _steps(x)
    return [re.sub(r"^\s*\d+\s*[.)-]\s*", "", s).strip() for s in out if s and len(s.strip()) > 3]


def _img(x) -> str:
    if isinstance(x, list):
        x = x[0] if x else ""
    if isinstance(x, dict):
        x = x.get("url") or ""
    x = str(x or "")
    return x if x.startswith("https://") else ""


def parse_recipe(page: str, url: str):
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', page, re.S | re.I):
        try:
            d = json.loads(m.group(1).strip())
        except ValueError:
            continue
        stack = [d]
        while stack:
            x = stack.pop()
            if isinstance(x, list):
                stack += x
                continue
            if not isinstance(x, dict):
                continue
            t = x.get("@type")
            if t == "Recipe" or isinstance(t, list) and "Recipe" in t:
                ing = [_txt(i) for i in (x.get("recipeIngredient") or x.get("ingredients") or []) if _txt(i)]
                st = _steps(x.get("recipeInstructions"))
                if len(ing) < 2 or not st:
                    return None
                y = x.get("recipeYield")
                y = y[0] if isinstance(y, list) and y else y
                rt = x.get("aggregateRating") or {}
                dk = _mins(x.get("totalTime")) or (_mins(x.get("prepTime")) + _mins(x.get("cookTime")))
                dk = dk if dk >= 5 else 0                 # sitede bazen 'PT2M' gibi yanlış süre var; bilinmiyor sayılır
                return {"url": url, "ad": _txt(x.get("name"))[:90], "mal": ing[:40], "adim": st[:30], "dk": dk, "kisi": _txt(y)[:20],
                        "img": _img(x.get("image")), "site": re.sub(r"^https?://(www\.)?", "", url).split("/")[0],
                        "puan": round(float(rt.get("ratingValue") or 0), 1) if isinstance(rt, dict) and str(rt.get("ratingValue", "")).replace(".", "", 1).isdigit() else 0}
            stack += [v for k, v in x.items() if k == "@graph"]
    return None


# ------------------------------------------------------------------ önbellek ve ağ
def _load():
    global _cache
    if _cache is None:
        try:
            with open(FILE, encoding="utf-8") as f:
                d = json.load(f)
            _cache = d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            _cache = {}
    return _cache


def _save():
    c = _load()
    if len(c) > 600:                                  # en eski kayıtlar düşer
        for k in sorted(c, key=lambda k: c[k].get("_t", 0))[:len(c) - 500]:
            c.pop(k, None)
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False)
    except OSError:
        pass


_http = requests.Session()                         # keep-alive: her istekte yeniden TLS el sıkışması yapılmaz
_http.mount("https://", requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=16))


def _get(url: str, **kw):
    return _http.get(url,headers={"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9", **kw.pop("headers", {})}, timeout=kw.pop("timeout", 9), **kw)


_SEARCH_CACHE = {}


def search_yemekcom(q: str, start: int = 0) -> list:
    """yemek.com sitesinin kendi arama ucu (sayfadaki arama kutusunun kullandığı). İlk sayfa 3, sonrakiler 9 tarif döner."""
    key = (q, start)
    if key in _SEARCH_CACHE and time.time() - _SEARCH_CACHE[key][0] < 3600:
        return _SEARCH_CACHE[key][1]
    r = _get("https://yemek.com/ara/sonuclar/", params={"q": q, "rows": 12, "recipes_start": start, "posts_start": 0},
             headers={"X-Requested-With": "XMLHttpRequest", "Referer": "https://yemek.com/ara/"})
    r.raise_for_status()
    out = []
    for x in (r.json().get("Data") or {}).get("Recipe") or []:
        u = str(x.get("Permalink") or "")
        if u.startswith("https://yemek.com/tarif/") and u.count("/") >= 5:
            out.append((u, _txt(x.get("Title"))))
    _SEARCH_CACHE[key] = (time.time(), out)
    return out


SOURCES = [search_yemekcom]


def fetch_recipe(url: str):
    c = _load()
    if url in c:
        return c[url] if c[url].get("ad") else None
    try:
        rec, buf = None, b""
        with _get(url, stream=True) as r:              # JSON-LD sayfanın başında: tarif bulununca okumayı keser (~20 KB yerine 200 KB indirmez)
            if not r.ok:
                return None
            for chunk in r.iter_content(16384):
                buf += chunk
                i = buf.find(b"ld+json")
                if i >= 0 and buf.rfind(b"</script>") > i:
                    rec = parse_recipe(buf.decode("utf-8", "ignore"), url)
                    if rec:
                        break
                if len(buf) > 800000:
                    break
        if rec is None:
            rec = parse_recipe(buf.decode("utf-8", "ignore"), url)
    except requests.RequestException:
        return None
    with _lock:
        c[url] = {**(rec or {}), "_t": time.time()}
    return rec


def _queries(items: list) -> list:
    """Önce hepsi birlikte, sonra ikili kombinasyonlar, en son tek tek. (sorgu, sayfa başlangıçları)"""
    main = [i for i in items if i not in _PURE][:5] or items[:5]      # kullanıcı un/şeker/salça dediyse aramaya katılır (kek, krep)
    qs = [(" ".join(main), (0, 3, 12))] if len(main) > 1 else []
    qs += [(f"{main[i]} {main[j]}", (0, 3)) for i in range(len(main)) for j in range(i + 1, len(main))][:3]
    qs += [(m, (0, 3) if len(main) <= 2 else (0,)) for m in main]
    return [(q, st) for q, st in qs if len(q) >= 3]          # site 3 harften kısa sorguyu reddeder ('un' -> 422)


def score(rec: dict, items: list, nostaple: list) -> dict:
    reqs, seen, used = [], set(), set()
    for line in rec["mal"]:
        groups, staple, opt = line_reqs(line)
        for labs, name in groups:
            key = frozenset(labs)
            if key in seen:
                continue
            seen.add(key)
            ok = _have(labs, items)
            for it in items:
                if _have(labs, [it]):
                    used.add(it)
            reqs.append({"ad": name, "ok": ok, "opt": opt})
        if staple and not groups:
            labs = {lab for lab, rx, kind, _u in _LEX if kind == "s" and rx.search(clean_line(line))}
            used |= labs & set(items)                  # kullanıcı 'un, şeker' dediyse bu tarifte kullanılıyor sayılır
            if labs & set(nostaple):
                key = frozenset(labs)
                if key not in seen:
                    seen.add(key)
                    reqs.append({"ad": sorted(labs & set(nostaple))[0], "ok": False, "opt": opt})
    need = [r for r in reqs if not r["opt"]]
    have = sum(r["ok"] for r in need)
    miss = [r["ad"] for r in need if not r["ok"]]
    cov = have / len(need) if need else 0
    use = len(used) / len(items) if items else 0
    title = fold(rec["ad"])
    in_title = sum(1 for it in used if BY_LABEL.get(it) and BY_LABEL[it][1].search(title) or fold(it) in title)
    s = 0.5 * cov + 0.4 * use - 0.07 * len(miss) + 0.05 * min(in_title, 2) + (0.02 * rec.get("puan", 0) if rec.get("puan") else 0)
    return {"miss": miss, "used": [i for i in items if i in used], "cov": round(cov, 2), "s": round(s, 3), "n": len(need)}


def search(items: list) -> None:
    """Ayrı iş parçacığında çalışır; bittiğinde NOTIFY ile sayfayı günceller ve sonucu söyler."""
    S.update(items=list(items), busy="Tarifler aranıyor…", err="", res=[], cur=None, step=-1, show=9, q=S["q"] + 1)
    qid = S["q"]
    _notify()

    def run():
        try:
            urls, titles = [], {}
            jobs = [(src, q, st) for q, starts in _queries(items) for st in starts for src in SOURCES]
            with ThreadPoolExecutor(min(len(jobs), 14)) as ex:
                pages = list(ex.map(lambda j: _safe(j[0], j[1], j[2]), jobs))
            for page in pages:                         # sorgu sırası korunur: önce tüm malzemeli sorgunun sonuçları
                for u, ttl in page:
                    if u not in titles:
                        titles[u] = ttl
                        urls.append(u)
            if not urls:
                raise RuntimeError("bos")
            def pri(u):                                 # başlığında malzeme geçen aday önce indirilir
                f = fold(titles[u])
                return -sum(1 for it in items if fold(it) in f or (BY_LABEL.get(it) and BY_LABEL[it][1].search(f)))
            urls = sorted(urls, key=pri)[:MAX_PAGES]
            if S["q"] != qid:
                return
            S["busy"] = f"{len(urls)} tarifin malzeme listesi okunuyor…"
            _notify()
            with ThreadPoolExecutor(12) as ex:
                recs = [r for r in ex.map(fetch_recipe, urls) if r]
            _save()
            if S["q"] != qid:
                return
            res = []
            for r in recs:
                sc = score(r, items, S["nostaple"])
                if sc["used"]:
                    res.append({**r, **sc})
            res.sort(key=lambda r: (-r["s"], len(r["miss"])))
            names = set()
            res = [r for r in res if not (fold(r["ad"]) in names or names.add(fold(r["ad"])))]     # aynı adlı tariflerden en uygunu kalır
            S.update(res=res, busy="", err="" if res else "Bu malzemelerle eşleşen tarif bulamadım.")
            _notify(summary())
        except Exception as e:
            print("yemek arama hatası:", type(e).__name__, e, flush=True)
            if S["q"] == qid:
                S.update(busy="", err="İnternete ulaşamadım ya da tarif sitesi yanıt vermedi.")
                _notify("İnternetten tarif alamadım efendim. Bağlantıyı kontrol edip tekrar ara deyin.")
    threading.Thread(target=run, daemon=True).start()


def _safe(src, q, start):
    try:
        return src(q, start)
    except Exception as e:
        print("yemek kaynak hatası:", src.__name__, type(e).__name__, flush=True)
        return []


def _notify(say: str = ""):
    if NOTIFY:
        try:
            NOTIFY({"snap": snapshot()}, say)
        except Exception as e:
            print("yemek bildirim hatası:", e, flush=True)


def say_list(items: list) -> str:
    """['tavuk', 'patates', 'soğan'] -> 'tavuk, patates ve soğan'"""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " ve " + items[-1] if items else ""


def visible() -> list:
    r = [x for x in S["res"] if not S["only"] or not x["miss"]]
    return r[:S["show"]]


def summary() -> str:
    res = visible()
    if not res:
        if S["only"] and S["res"]:
            return "Yalnızca elinizdekilerle yapılabilen tarif çıkmadı efendim. Tümünü göster derseniz eksiği az olanları gösteririm."
        return "Bu malzemelerle eşleşen tarif bulamadım efendim. Başka bir malzeme ekleyebilir ya da daha genel söyleyebilirsiniz."
    full = sum(1 for x in S["res"] if not x["miss"])
    head = f"{len(S['res'])} tarif inceledim; {full} tanesi tamamen elinizdekilerle yapılıyor. " if full else f"{len(S['res'])} tarif inceledim. "
    parts = []
    for i, x in enumerate(res[:3]):
        m = x["miss"]
        parts.append(f"{i + 1}, {x['ad']}" + (", eksik yok" if not m else f", eksik: {', '.join(m[:3])}" + (" ve fazlası" if len(m) > 3 else "")))
    return head + "En uygunları: " + ". ".join(parts) + ". Hangisini açayım?"


def cur():
    return next((x for x in S["res"] if x["url"] == S["cur"]), None)


def open_index(i: int):
    res = visible()
    if 0 <= i < len(res):
        S.update(cur=res[i]["url"], step=-1)
        return res[i]
    return None


def step_timer(text: str) -> int:
    """Adım metnindeki süre (dakika). '15-20 dakika' -> 15, '1 saat' -> 60, 'yarım saat' -> 30."""
    t = fold(text)
    if re.search(r"yarim saat", t):
        return 30
    m = re.search(r"(\d+)\s*(?:-|ila|ile|ya da|veya)?\s*(\d+)?\s*(saat|dakika|dk)\b", t)
    if not m:
        m2 = re.search(r"\b(bir|iki|uc|bes|on|onbes|yirmi|otuz|kirk|kirkbes|elli)\s*(saat|dakika|dk)\b", t)
        if not m2:
            return 0
        n = {"bir": 1, "iki": 2, "uc": 3, "bes": 5, "on": 10, "onbes": 15, "yirmi": 20, "otuz": 30, "kirk": 40, "kirkbes": 45, "elli": 50}[m2.group(1)]
        return n * (60 if m2.group(2) == "saat" else 1)
    n = int(m.group(1))
    return min(n * (60 if m.group(3) == "saat" else 1), 600)


def snapshot() -> dict:
    c = cur()
    card = lambda x: {"url": x["url"], "ad": x["ad"], "img": x["img"], "dk": x["dk"], "kisi": x["kisi"], "site": x["site"], "miss": x["miss"],
                      "used": x["used"], "cov": x["cov"], "n": x["n"], "puan": x.get("puan", 0)}
    out = {"items": S["items"], "busy": S["busy"], "err": S["err"], "only": S["only"], "nostaple": S["nostaple"], "total": len(S["res"]),
           "full": sum(1 for x in S["res"] if not x["miss"]), "list": [card(x) for x in visible()], "cur": None, "staples": STAPLES}
    if c:
        mal = []
        for line in c["mal"]:
            groups, staple, opt = line_reqs(line)
            ok = staple or all(_have(labs, S["items"]) for labs, _n in groups) if groups or staple else None
            if staple and set(S["nostaple"]) & {lab for lab, rx, kind, _u in _LEX if kind == "s" and rx.search(clean_line(line))}:
                ok = False
            mal.append({"t": line, "ok": ok, "st": staple and not groups, "opt": opt})
        out["cur"] = {**card(c), "mal": mal, "adim": [{"t": s, "dk": step_timer(s)} for s in c["adim"]], "step": S["step"]}
    return out
