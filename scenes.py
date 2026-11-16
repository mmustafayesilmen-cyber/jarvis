"""Tam ekran sahne modları: Ortam (ses+animasyon), Uzay (güneş sistemi), Müzik görselleştirici. Mod açıkken normal Jarvis dinlemez;
konuşulan her cümle yalnızca buradaki handle(kind, ...) işlevine gider. Çizim ve ses ui/scene_<ad>.html içindedir."""
import re

KINDS = ("ortam", "uzay", "muzik", "kimya", "biyoloji", "fizik", "matematik", "astronomi", "jeoloji", "gokyuzu", "notlar", "yuvam", "hologram", "rapor", "sistem", "ders", "pomodoro", "kartlar", "gelisim", "satranc", "oyunlar", "kuran", "harita", "listeler", "vpn", "mola", "uyku", "tarif", "spor", "panel", "telefon", "sinav", "odak", "planlama", "nasil", "yemek", "sohbet", "ultron", "friday", "luna", "optik", "tahta", "masa", "okuma", "kelime", "butce", "cark", "baslatici", "gune", "pano", "zirh", "gorev", "brifing", "starklab", "dunya", "odakoda", "guvenlik", "kopru", "elektronik", "ruya", "nefes", "ritim", "nota", "mors", "renk", "kum", "simya", "kapsul", "hikaye", "ekitap")


def norm(text: str) -> str:
    t = text.replace("İ", "i").replace("I", "ı").lower()
    t = re.sub(r"['’]\w*", "", t)
    t = re.sub(r"[^\w\sçğıöşü%]", " ", t)
    t = re.sub(r"\b(jarvis|hey|lütfen|bana|şunu|efendim|hadi|şimdi|bir)\b", " ", t)
    return " ".join(t.split())


EXIT_RE = (r"\b(mod\w*|pencere\w*|ekran\w*|ortam\w*|uzay\w*|müzik\w*|görselleştirici\w*|laboratuvar\w*|lab|kimya|biyoloji|fizik|matematik|astronomi|jeoloji|gökyüzü|gökyüz\w*|not|notlar\w*|not defteri|yuvam\w*|evim|hologram\w*)\b.*\b(kapat|kapa|çık|çıkış|bitir|dön|sonlandır)\w*|"
           r"\b(çık|çıkış|çıkalım|bitti|güle güle|görüşürüz)\b|normale dön")
_ONES = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9}
_TENS = {"on": 10, "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50, "altmış": 60, "yetmiş": 70, "seksen": 80, "doksan": 90, "yüz": 100}


def num_in(t: str):
    m = re.search(r"(\d{1,3})", t)
    if m:
        return int(m.group(1))
    words = [w for w in t.split() if w in _ONES or w in _TENS]
    if words and len(words) <= 3:
        return sum(_ONES.get(w, 0) + _TENS.get(w, 0) for w in words) or None
    return None


# ============================================================== ORTAM
ORTAM = [("yağmur", "rain", r"yağmur|yağış"), ("fırtına", "storm", r"fırtına|şimşek|gök gürültü\w*"), ("deniz", "sea", r"deniz|dalga|okyanus"),
         ("orman", "forest", r"orman|kuş|doğa"), ("şömine", "fire", r"şömine|ateş|odun|kamp"), ("kafe", "cafe", r"kafe|kahve|cafe"),
         ("gece", "night", r"gece|cırcır|böcek|kurbağa"), ("rüzgar", "wind", r"rüzgar|rüzgâr|fırlama"), ("nehir", "river", r"nehir|dere|akarsu|şelale"),
         ("beyaz gürültü", "white", r"beyaz|gürültü|odak sesi|kahverengi|pembe")]


def ortam_init():
    return {"presets": [{"key": k, "name": n} for n, k, _ in ORTAM]}


def ortam(text: str, st: dict):
    t = norm(text)
    if re.search(r"\b(liste|neler var|hangileri|seçenek\w*|yardım)\b", t):
        return {"do": {"list": True}, "say": "Ortam sesleri: " + ", ".join(n for n, _, _ in ORTAM) + ". Birini söyleyin."}
    m = re.search(r"(\d{1,3}|[a-zçğıöşü]+(?: [a-zçğıöşü]+)?)\s*(dakika|dk|saat)\w*\s*(sonra|içinde|kadar)?", t)
    if m and re.search(r"kapat|uyku|zamanlay\w*|sayaç|sonra|ayarla|kur", t) and not re.search(r"\b(yağmur|fırtına|deniz)\b.*\b(aç|çal)\b", t):
        n = num_in(m.group(1)) or 0
        if n:
            mins = n * (60 if m.group(2).startswith("saat") else 1)
            return {"do": {"sleep": mins}, "say": f"Uyku zamanlayıcısı {mins} dakikaya ayarlandı efendim. Süre dolunca sesi yavaşça kısıp kapanacağım."}
    if re.search(r"\b(sustur|sessiz|durdur|dur|sesi kapat|kes)\b", t) and not re.search(r"\bçık\b", t):
        return {"do": {"preset": None}, "say": "Ortam sesi durdu efendim."}
    if re.search(r"\b(ses|sesi|yüksek|gür)\w*", t) and re.search(r"artır|yükselt|aç|güçlendir|daha yüksek", t):
        return {"do": {"vol": 0.12}, "say": "Sesi artırdım efendim."}
    if re.search(r"\b(ses|sesi)\w*", t) and re.search(r"azalt|kıs|düşür|alçalt|daha düşük", t):
        return {"do": {"vol": -0.12}, "say": "Sesi kıstım efendim."}
    n = num_in(t)
    if n is not None and re.search(r"ses|yüzde|%", t):
        return {"do": {"volset": max(0, min(100, n)) / 100}, "say": f"Ses yüzde {max(0, min(100, n))} efendim."}
    if re.search(r"\b(sonraki|başka|diğeri|değiştir)\b", t):
        return {"do": {"next": 1}, "say": "Sıradaki ortama geçiyorum efendim."}
    for name, key, pat in ORTAM:
        if re.search(pat, t) or name in t:
            return {"do": {"preset": key}, "say": f"{name.capitalize() if name != 'şömine' else 'Şömine'} ortamı açıldı efendim."}
    return {"say": "Bu modda yalnızca ortam seslerini yönetiyorum efendim. Bir ortam adı söyleyin ya da liste deyin."}


# ============================================================== UZAY
BODIES = [
    ("güneş", "sun", r"güneş|yıldız", "Güneş: sistemin merkezindeki yıldız. Çapı yaklaşık 1,4 milyon kilometre, yani Dünya'dan 109 kat büyük. Yüzey sıcaklığı yaklaşık 5500 derece. Güneş sistemi kütlesinin yüzde 99,8'i onda."),
    ("merkür", "mercury", r"merkür", "Merkür: Güneş'e en yakın gezegen, yaklaşık 58 milyon kilometre. Çapı 4880 kilometre. Bir yılı sadece 88 gün. Uydusu yok. Gündüz 430 dereceye çıkar, gece eksi 180'e düşer."),
    ("venüs", "venus", r"venüs|zühre", "Venüs: Güneş sisteminin en sıcak gezegeni, yüzeyi yaklaşık 465 derece. Çapı 12100 kilometre, Dünya'ya çok yakın boyutta. Ters yönde döner ve bir günü bir yılından uzundur."),
    ("dünya", "earth", r"dünya|gezegenimiz|yer", "Dünya: bildiğimiz tek yaşam gezegeni. Güneş'e yaklaşık 150 milyon kilometre. Çapı 12740 kilometre. Bir uydusu var: Ay. Bir yılı 365 gün, 6 saat."),
    ("ay", "moon", r"\bay\b|uydu", "Ay: Dünya'nın tek doğal uydusu, 384 bin kilometre uzakta. Çapı 3475 kilometre. Dünya etrafında 27 günde döner, hep aynı yüzünü bize gösterir."),
    ("mars", "mars", r"mars|kızıl gezegen", "Mars: kızıl gezegen. Çapı 6780 kilometre, Güneş'e yaklaşık 228 milyon kilometre. İki küçük uydusu var: Fobos ve Deimos. Güneş sisteminin en büyük volkanı Olimpos Dağı onda, yaklaşık 22 kilometre yüksekliğinde."),
    ("jüpiter", "jupiter", r"jüpiter|jupiter", "Jüpiter: en büyük gezegen, çapı yaklaşık 140 bin kilometre. Güneş'e 778 milyon kilometre. 90'dan fazla uydusu var. Büyük Kırmızı Leke, yüzyıllardır süren dev bir fırtına."),
    ("satürn", "saturn", r"satürn|saturn", "Satürn: muhteşem halkalarıyla ünlü. Çapı yaklaşık 116 bin kilometre, Güneş'e 1,4 milyar kilometre. 140'tan fazla uydusu var. Yoğunluğu sudan düşük, yani yeterince büyük bir havuzda yüzerdi."),
    ("uranüs", "uranus", r"uranüs|uranus", "Uranüs: yan yatmış bir gezegen, dönme ekseni yaklaşık 98 derece eğik. Çapı 50700 kilometre, Güneş'e 2,9 milyar kilometre. 27 bilinen uydusu var. Bir yılı 84 Dünya yılı."),
    ("neptün", "neptune", r"neptün|neptun", "Neptün: en uzak gezegen, Güneş'e yaklaşık 4,5 milyar kilometre. Çapı 49200 kilometre. Rüzgârları saatte 2000 kilometreye yaklaşır. Bir yılı 165 Dünya yılı."),
    ("plüton", "pluto", r"plüton|pluto|cüce", "Plüton: 2006'dan beri cüce gezegen sayılıyor. Çapı yaklaşık 2380 kilometre, Güneş'e ortalama 5,9 milyar kilometre. Yörüngesi dışmerkezli ve eğik."),
]


def _uzay_all():
    """Gezegenler + uzay_data.EXTRA_BODIES (uydular, cüce gezegenler, kuyruklu yıldız)."""
    try:
        from uzay_data import EXTRA_BODIES
    except Exception:
        EXTRA_BODIES = []
    return BODIES + list(EXTRA_BODIES)


def uzay_init():
    import uzay_data as U
    def _info(k, info):
        more = U.MORE.get(k)
        return info + ("\n" + "\n".join("• " + x for x in more) if more else "")
    out = []
    for n, k, _, info in _uzay_all():
        b = {"key": k, "name": n.split()[0].capitalize() if n != "ay" else "Ay", "info": _info(k, info)}
        for field, src in (("facts", "FACTS"), ("layers", "LAYERS"), ("atmo", "ATMO"), ("missions", "MISSIONS")):
            v = getattr(U, src, {}).get(k)
            if v:
                b[field] = v
        out.append(b)
    return {"bodies": out}


def uzay(text: str, st: dict):
    t = norm(text)
    ALL = _uzay_all()
    keys = [b[1] for b in ALL]
    cur = st.get("focus", "overview")
    if re.search(r"\b(ayrıntı\w*|detay\w*|daha fazla|devam|bir tane daha)\b", t) and cur != "overview":
        from uzay_data import MORE
        lst = MORE.get(cur) or []
        i = st.get("dtl", {}).get(cur, 0)
        if not lst:
            return {"say": "Bu cisim için ek ayrıntı yok efendim."}
        st.setdefault("dtl", {})[cur] = i + 2 if i + 2 < len(lst) else 0
        return {"do": {"focus": cur}, "say": " ".join(lst[i:i + 2]) + (" Devamı için ayrıntı deyin." if i + 2 < len(lst) else " Bu kadar efendim.")}
    if re.search(r"\b(sistem\w*|hepsi\w*|genel|tümü|baştan|dışarı çık)\b", t) and re.search(r"göster|genel|bak|hepsi|uzaklaş|tüm|sistem", t) and not re.search(r"hızlı|yavaş", t):
        st["focus"] = "overview"
        return {"do": {"focus": "overview"}, "say": "Güneş sisteminin genel görünümü efendim. Bir gezegen adı söyleyin ya da sonraki deyin."}
    if re.search(r"\b(sonraki|ileri|diğer|bir sonraki)\b", t):
        i = keys.index(cur) + 1 if cur in keys else 0
        k = keys[i % len(keys)]
        st["focus"] = k
        b = next(x for x in ALL if x[1] == k)
        return {"do": {"focus": k}, "say": b[3]}
    if re.search(r"\b(önceki|geri)\b", t):
        i = keys.index(cur) - 1 if cur in keys else len(keys) - 1
        k = keys[i % len(keys)]
        st["focus"] = k
        b = next(x for x in ALL if x[1] == k)
        return {"do": {"focus": k}, "say": b[3]}
    if re.search(r"yakınlaş\w*|büyüt|zoom|yaklaş\w*", t):
        return {"do": {"zoom": 1.35}, "say": "Yakınlaşıyorum efendim."}
    if re.search(r"uzaklaş\w*|küçült", t):
        return {"do": {"zoom": 1 / 1.35}, "say": "Uzaklaşıyorum efendim."}
    if re.search(r"hızlan\w*|hızlandır\w*|daha hızlı", t):
        return {"do": {"speed": 2.0}, "say": "Zamanı hızlandırdım efendim."}
    if re.search(r"yavaşla\w*|yavaşlat\w*|daha yavaş", t):
        return {"do": {"speed": 0.5}, "say": "Zamanı yavaşlattım efendim."}
    if re.search(r"zamanı durdur|durdur|dondur|duraklat", t):
        return {"do": {"speed": 0}, "say": "Zaman durdu efendim."}
    if re.search(r"devam|başlat|normal hız", t):
        return {"do": {"speed": 1, "absolute": True}, "say": "Zaman akıyor efendim."}
    if re.search(r"yörünge\w*|çizgi\w*", t):
        return {"do": {"orbits": not re.search(r"kapat|gizle|kaldır", t)}, "say": "Yörünge çizgilerini değiştirdim efendim."}
    if re.search(r"etiket\w*|isim\w*|ad\w* göster", t):
        return {"do": {"labels": not re.search(r"kapat|gizle|kaldır", t)}, "say": "Etiketleri değiştirdim efendim."}
    if re.search(r"\b(anlat|bilgi|özellik\w*|nedir|kimdir|hakkında|açıkla)\b", t) and cur in keys:
        b = next(x for x in ALL if x[1] == cur)
        return {"do": {"card": True}, "say": b[3]}
    if re.search(r"\b(anlat|bilgi|özellik\w*|nedir|kimdir|hakkında|açıkla)\b", t) and cur not in keys:
        return {"say": "Önce bir gezegen seçin efendim, örneğin mars ya da satürn deyin."}
    if re.search(r"\b(liste|hangi gezegen\w*|neler var)\b", t):
        return {"say": "Güneş, Merkür, Venüs, Dünya, Ay, Mars, Jüpiter, Satürn, Uranüs, Neptün ve Plüton. Ayrıca uydular Io, Europa, Ganymede, Callisto, Titan, Enceladus, Triton ve Charon ile Ceres, Eris ve Halley kuyruklu yıldızı. Birini söyleyin efendim."}
    for name, key, pat, info in ALL[len(BODIES):] + BODIES:
        if re.search(pat, t):
            st["focus"] = key
            return {"do": {"focus": key}, "say": info}
    return {"say": "Bu modda yalnızca uzayı gösteriyorum efendim. Bir gezegen adı söyleyin, sonraki deyin ya da genel görünüm isteyin."}


# ============================================================== MÜZİK GÖRSELLEŞTİRİCİ
STYLES = [("çubuklar", "bars", r"çubuk|bar|spektrum"), ("dalga", "wave", r"dalga|osiloskop|çizgi"), ("daire", "ring", r"daire|halka|çember"),
          ("parçacık", "dust", r"parçacık|toz|konfeti"), ("tünel", "tunnel", r"tünel|girdap"), ("kaleydoskop", "kaleid", r"kaleydoskop|simetri"),
          ("şehir", "city", r"şehir|bina|ekolayzer|equalizer"), ("yıldız", "warp", r"yıldız|uzay yolculuğu|ışık hızı|warp"), ("sarmal", "spiral", r"sarmal|galaksi|spiral"),
          ("ağ", "net", r"\bağ\b|şebeke|nöron|bağlantı"), ("ızgara", "grid", r"ızgara|retro|synthwave|neon yol")]
COLORS = [("mavi", "blue", r"mavi|buz|turkuaz|camgöbeği"), ("kırmızı", "red", r"kırmızı|ateş"), ("yeşil", "green", r"yeşil|matrix"),
          ("mor", "purple", r"mor|menekşe|pembe"), ("gökkuşağı", "rainbow", r"gökkuşağı|renkli|çok renkli|gökkusağı")]


def muzik_init():
    return {"styles": [{"key": k, "name": n} for n, k, _ in STYLES], "colors": [{"key": k, "name": n} for n, k, _ in COLORS]}


def media_key(vk: int) -> None:
    """Tarayıcıda (YouTube Music vb.) çalan müziği yönetmek için sistem medya tuşu gönderir."""
    import ctypes
    u = ctypes.windll.user32
    u.keybd_event(vk, 0, 0, 0)
    u.keybd_event(vk, 0, 2, 0)


VK_NEXT, VK_PREV, VK_PLAYPAUSE = 0xB0, 0xB1, 0xB3


def _clean_query(q: str) -> str:
    return re.sub(r"\b(şarkısını|şarkısı|şarkıyı|parçasını|parçayı|müziği|youtube|müzikte|müzik|sıraya|kuyruğa|ekle|ekler misin)\b", " ", q).strip()


def muzik(text: str, st: dict):
    import study_music
    t = norm(text)
    if re.search(r"^(ders müziği|ders şarkıları)\w*( çal| aç| başlat)?$", t):
        study_music.start()
        return {"say": "Ders şarkıları sırayla çalıyor efendim. Görselleştirici bilgisayarın sesini dinliyor."}
    # --- kuyruk
    m = re.search(r"(?:^|\b)(?:sıraya|kuyruğa) ekle\s+(.+)$|^(.+?)\s+(?:sıraya|kuyruğa) ekle$", t)
    if m:
        q = _clean_query(m.group(1) or m.group(2))
        if q:
            return {"say": f"{q} aranıp kuyruğa ekleniyor efendim.",
                    "later": lambda: (f"{n} kuyruğa eklendi efendim." if (n := study_music.enqueue(q)) else "Şarkıyı bulamadım efendim.")}
    if re.search(r"^(kuyruk|sıra|çalma listesi|liste)( neler)?( ne| ne var| göster| oku)?$|^kuyruğu (göster|oku)$", t):
        q = study_music.queue_titles()
        if not q:
            return {"say": "Kuyruk boş efendim. Bir şarkı adı ve çal deyin, ya da sıraya ekle deyin."}
        return {"say": f"Kuyrukta {len(q)} şarkı var: " + ", ".join(x.replace('▶ ', 'şu an çalan ') for x in q[:5]) + "."}
    # --- döngü
    if re.search(r"^(şarkıyı |müziği )?(döngüye al|döngüde çal|tekrarla|tekrar çal|sürekli çal|döngü(yü)? aç)$", t):
        study_music.set_repeat(True)
        return {"say": "Şarkı döngüde efendim."}
    if re.search(r"^(döngüyü|tekrarı) (kapat|durdur|kaldır|bitir)$|^döngüden çıkar$", t):
        study_music.set_repeat(False)
        return {"say": "Döngüyü kapattım efendim."}
    # --- çalma denetimi
    if re.search(r"^(şarkıyı |parçayı |müziği )?(geç|atla)$|^(sonraki|bir sonraki|diğer|yeni) (şarkı|parça)\w*$|^(şarkıyı|parçayı) (geç|atla|değiştir)$", t):
        if study_music.skip():
            return {"say": "Sıradaki şarkıya geçtim efendim."}
        media_key(VK_NEXT)
        return {"say": "Tarayıcıdaki müziği sonraki şarkıya geçirdim efendim."}
    if re.search(r"^(önceki|bir önceki|geri) (şarkı|parça)\w*$|^(şarkıyı|parçayı) (başa sar|geri al)$", t):
        if study_music.prev():
            return {"say": "Önceki şarkıya döndüm efendim."}
        media_key(VK_PREV)
        return {"say": "Tarayıcıdaki müziği önceki şarkıya aldım efendim."}
    if re.search(r"^(müziği |şarkıyı )?(duraklat|beklet)$|^(müziği |şarkıyı )?durdur$", t) and not re.search(r"\b(mod|pencere|ekran|görselleştirici)\b", t):
        if re.search(r"durdur", t) and study_music.active():
            study_music.stop()
            return {"say": "Müziği durdurdum efendim."}
        if study_music.active():
            return {"say": "Müzik duraklatıldı efendim. Devam et deyince sürer." if study_music.pause() else "Müzik zaten duraklatılmış efendim."}
        media_key(VK_PLAYPAUSE)
        return {"say": "Tarayıcıdaki müziği duraklattım ya da sürdürdüm efendim."}
    if re.search(r"^(müziği |şarkıyı )?(devam( et\w*)?|sürdür|oynat)$", t):
        if study_music.active():
            return {"say": "Müzik devam ediyor efendim." if study_music.resume() else "Müzik zaten çalıyor efendim."}
        media_key(VK_PLAYPAUSE)
        return {"say": "Tarayıcıdaki müziği sürdürdüm efendim."}
    if re.search(r"^(müziği |şarkıyı )?(kapat|kes|sustur)$", t) and not re.search(r"\b(mod|pencere|ekran|görselleştirici)\b", t):
        study_music.stop()
        return {"say": "Müziği durdurdum efendim."}
    if re.search(r"ne çalıyor|hangi şarkı|şarkı adı|bu (şarkı|parça) ne|şu an ne|çalan şarkı", t):
        return {"do": {"ask_np": True}, "say": ""}
    # --- sözler
    if re.search(r"\bsöz\w*\b|\blyrics\b", t):
        off = bool(re.search(r"kapat|gizle|kaldır|kapa\b|göster(me)?me", t))
        return {"do": {"lyrics": not off}, "say": "Sözleri kapattım efendim." if off else "Şarkı sözlerini açtım efendim. Sözler bulunursa çalan satır vurgulanır."}
    m = re.fullmatch(r"(?:youtube(?:da| müzikte)?\s+)?(.+?)\s+(?:çal|çalsana|oynat|aç)", t)
    if m and not re.search(r"\b(stil|renk|görselleştirici|çubuk|dalga|daire|tünel|kaleydoskop|parçacık|şehir|yıldız|sarmal|ızgara|mavi|kırmızı|yeşil|mor|gökkuşağı)\b", t):
        q = m.group(1)
        return {"say": f"{q} aranıyor efendim. Ses Jarvis'in kendi oynatıcısından gelir, görselleştirici bilgisayarın sesini dinler.",
                "later": lambda: (f"{n} çalıyor efendim." if (n := study_music.play_query(q)) else "Şarkıyı bulamadım efendim.")}
    if re.search(r"\b(hassasiyet|duyarlılık|ses seviyesi)\b|daha (hassas|duyarlı)", t):
        up = not re.search(r"azalt|düşür|kıs|az", t)
        return {"do": {"gain": 1.35 if up else 0.74}, "say": "Hassasiyeti artırdım efendim." if up else "Hassasiyeti azalttım efendim."}
    if re.search(r"\b(sonraki|başka|diğeri|değiştir|stil)\b", t) and not re.search(r"renk", t):
        i = (st.get("style", 0) + 1) % len(STYLES)
        st["style"] = i
        return {"do": {"style": STYLES[i][1]}, "say": f"{STYLES[i][0].capitalize()} stili efendim."}
    if re.search(r"\b(önceki|geri)\b", t):
        i = (st.get("style", 0) - 1) % len(STYLES)
        st["style"] = i
        return {"do": {"style": STYLES[i][1]}, "say": f"{STYLES[i][0].capitalize()} stili efendim."}
    for name, key, pat in COLORS:
        if re.search(pat, t):
            return {"do": {"color": key}, "say": f"Renk {name} efendim."}
    for i, (name, key, pat) in enumerate(STYLES):
        if re.search(pat, t) or name in t:
            st["style"] = i
            return {"do": {"style": key}, "say": f"{name.capitalize()} stili efendim."}
    if re.search(r"\b(liste|neler var|stiller|yardım)\b", t):
        return {"say": "Stiller: " + ", ".join(n for n, _, _ in STYLES) + ". Renkler: " + ", ".join(n for n, _, _ in COLORS) + ". Müzik için şarkı adı ve çal, sıraya ekle, sonraki şarkı, önceki şarkı, duraklat, devam et, kuyruk ve sözler komutları var."}
    return {"say": "Bu modda görselleştiriciyi yönetiyorum efendim. Stil ya da renk söyleyin, bir şarkı adı ve çal deyin."}


HANDLERS = {"ortam": ortam, "uzay": uzay, "muzik": muzik}
INITS = {"ortam": ortam_init, "uzay": uzay_init, "muzik": muzik_init}
TITLES = {"ortam": "JARVIS ORTAM", "uzay": "JARVIS UZAY", "muzik": "JARVIS MÜZİK"}
EXIT_SAY = {"ortam": "Ortam modu kapanıyor efendim, normale dönüyorum.", "uzay": "Uzay modu kapanıyor efendim, normale dönüyorum.",
            "muzik": "Müzik görselleştirici kapanıyor efendim, normale dönüyorum."}


def handle(kind: str, text: str, state: dict):
    t = norm(text)
    if not t and not (kind in ("oyunlar", "satranc") and str(text).strip()):   # norm 'bir' sözcüğünü atar; "bir bir bir" ya da "a bir" bir cevaptır
        return None
    if kind in ("hologram", "rapor", "sistem", "ders"):   # "hologramı döndür" / "raporu gönder" / "kategoriyi kapat" çıkış sayılmasın
        if re.search(r"\b(çık|çıkış|çıkalım|bitti|güle güle|görüşürüz|normale dön)\b|\b(hologram|rapor|sistem|quiz)\w* (modunu|modu|ekranını|penceresini|analizini) (kapat|kapa|bitir|sonlandır)\w*|\bhologram\w* (kapat|kapa|bitir|sonlandır)\w*|\bsistem analiz\w* (modunu |modu )?(kapat|kapa|bitir|sonlandır)\w*|\b(modu|mod|pencereyi|pencere) (kapat|kapa|bitir)\w*", t):
            return {"exit": True, "say": EXIT_SAY[kind]}
    elif kind in ("kartlar", "gelisim", "satranc", "oyunlar", "kuran", "harita", "listeler", "vpn"):              # "kartı sil" / "raporu gönder" / "bitti" çıkış sayılmasın
        if re.search(r"\b(çık|çıkış|çıkalım|güle güle|görüşürüz|normale dön)\b|\b(kart\w*|ezber\w*|gelişim\w*|satranç\w*|oyun\w*|kur\w*|kuran\w*|harita\w*|dünya\w*|liste\w*|vpn\w*)\s*(modunu|modu|ekranını|penceresini|panelini|paneli) (kapat|kapa|bitir|sonlandır)\w*|\b(modu|mod|pencereyi|pencere|paneli) (kapat|kapa)\w*", t):
            return {"exit": True, "say": EXIT_SAY[kind]}
    elif kind == "planlama":                          # görev adındaki "çık" / "bitti" çıkış sayılmasın; yalnızca açık çıkış ifadeleri
        if re.fullmatch(r"(çık|çıkış|çıkalım|güle güle|görüşürüz|normale dön)", t) or re.search(r"\b(planlama|plan)\w* (modunu|modu|ekranını|penceresini) (kapat|kapa|bitir|sonlandır)\w*|\b(modu|mod|pencereyi|pencere) (kapat|kapa)\w*", t):
            return {"exit": True, "say": EXIT_SAY[kind]}
    elif kind in ("optik", "tahta", "masa", "okuma", "kelime", "butce", "cark", "baslatici", "gune", "pano", "zirh", "gorev", "brifing", "starklab", "dunya", "guvenlik", "kopru", "elektronik", "ruya", "nefes", "ritim", "nota", "mors", "renk", "kum", "simya", "kapsul", "hikaye", "ekitap"):    # "teslim et" / "bitti" / "sil" / "kapat" iş komutudur; yalnızca açık çıkış ifadeleri
        if re.fullmatch(r"(çık|çıkış|çıkalım|güle güle|görüşürüz|normale dön)", t) or re.search(r"\b(modu|modunu|ekranını|simülatörünü|tahtayı|masayı|laboratuvarı|laboratuvarını|labı|labını|günlüğünü|rehberini|stüdyosunu|kutusunu|atölyesini|bahçesini|zarlarını|kapsülünü|kitabı|kitabını|e-kitabı|günlüğü|rehberi|stüdyosu|kutusu|atölyesi|bahçesi|zarları|kapsülü) (kapat|kapa|bitir|sonlandır)\w*|\b(modu|mod) (kapat|kapa)\w*|\bmoddan çık\w*", t):
            return {"exit": True, "say": EXIT_SAY[kind]}
    elif kind == "sohbet":                            # serbest konuşma: "bitti", "kapat" gibi sözler sohbet içinde geçer; yalnızca açık çıkış ifadeleri
        if re.fullmatch(r"(çık|çıkış|çıkalım|güle güle|görüşürüz|normale dön|sohbeti bitir|sohbeti kapat)", t) or re.search(r"\bsohbet\w* (modunu |modu |ekranını |penceresini )?(kapat|kapa|bitir|sonlandır)\w*|\b(modu|mod|pencereyi|pencere) (kapat|kapa)\w*|\bmoddan çık\w*", t):
            return {"exit": True, "say": EXIT_SAY[kind]}
    elif kind == "ultron":                            # serbest konuşma: yalnızca açık çıkış ifadeleri ("dön" Jarvis'e dönmek demektir; norm 'jarvis' sözcüğünü atar)
        if re.fullmatch(r"(çık|çıkış|çıkalım|güle güle|görüşürüz|normale dön|dön|geri dön|ana menüye dön|ana menü|menüye dön)", t) or re.search(r"\bultron\w* (modunu |modu |ekranını |penceresini )?(kapat|kapa|bitir|sonlandır)\w*|\b(modu|mod|pencereyi|pencere) (kapat|kapa)\w*|\bmoddan çık\w*", t):
            return {"exit": True, "say": EXIT_SAY[kind]}
    elif kind == "friday":                            # serbest komutlar ("bitti", "kapat" iş cümlesidir); yalnızca açık çıkış ifadeleri
        if re.fullmatch(r"(çık|çıkış|çıkalım|güle güle|görüşürüz|normale dön|dön|geri dön|ana menüye dön|ana menü|menüye dön)", t) or re.search(r"\bfriday\w* (modunu |modu |ekranını |penceresini )?(kapat|kapa|bitir|sonlandır)\w*|\b(modu|mod|pencereyi|pencere) (kapat|kapa)\w*|\bmoddan çık\w*", t):
            return {"exit": True, "say": EXIT_SAY[kind]}
    elif kind == "luna":                              # serbest konuşma: yalnızca açık çıkış ifadeleri ("dön" Jarvis'e dönmek demektir)
        if re.fullmatch(r"(çık|çıkış|çıkalım|güle güle|görüşürüz|normale dön|dön|geri dön|ana menüye dön|ana menü|menüye dön)", t) or re.search(r"\bluna\w* (modunu |modu |ekranını |penceresini )?(kapat|kapa|bitir|sonlandır)\w*|\b(modu|mod|pencereyi|pencere) (kapat|kapa)\w*|\bmoddan çık\w*", t):
            return {"exit": True, "say": EXIT_SAY[kind]}
    elif kind == "yemek":                             # "bitti" sonraki adım, "patates yok" malzeme komutudur; yalnızca açık çıkış ifadeleri
        if re.fullmatch(r"(çık|çıkış|çıkalım|güle güle|görüşürüz|normale dön)", t) or re.search(r"\b(yemek|mutfak)\w* (modunu|modu|ekranını|penceresini) (kapat|kapa|bitir|sonlandır)\w*|\b(modu|mod|pencereyi|pencere) (kapat|kapa)\w*|\b(moddan|yemek modundan) çık\w*", t):
            return {"exit": True, "say": EXIT_SAY[kind]}
    elif kind in ("pomodoro", "odakoda"):             # "molayı bitir" / "bitti" çıkış sayılmasın
        if re.search(r"\b(çık|çıkış|çıkalım|güle güle|görüşürüz|normale dön)\b|\b(pomodoro|odak)\w* (modunu|modu|ekranını|penceresini) (kapat|kapa|bitir|sonlandır)\w*|\b(modu|mod|pencereyi|pencere) (kapat|kapa)\w*", t) and not re.search(r"döngü", t):
            return {"exit": True, "say": EXIT_SAY[kind]}
    elif re.search(EXIT_RE, t) and not re.search(r"\b(sesi kapat|müziği kapat|sesi durdur)\b", t):
        return {"exit": True, "say": EXIT_SAY[kind]}
    return HANDLERS[kind](text, state)


# ------------------------------------------------------------------ laboratuvar modları (scenes_lab.py)
import scenes_lab  # noqa: E402

HANDLERS["kimya"] = scenes_lab.kimya
HANDLERS["biyoloji"] = scenes_lab.biyoloji
INITS["kimya"] = scenes_lab.kimya_init
INITS["biyoloji"] = scenes_lab.biyoloji_init
TITLES["kimya"] = "JARVIS KİMYA LABORATUVARI"
TITLES["biyoloji"] = "JARVIS BİYOLOJİ LABORATUVARI"
EXIT_SAY["kimya"] = "Kimya laboratuvarı kapanıyor efendim, normale dönüyorum."
EXIT_SAY["biyoloji"] = "Biyoloji laboratuvarı kapanıyor efendim, normale dönüyorum."


# ------------------------------------------------------------------ fizik ve matematik laboratuvarları (scenes_sci.py)
import scenes_sci  # noqa: E402

HANDLERS["fizik"] = scenes_sci.fizik
HANDLERS["matematik"] = scenes_sci.matematik
INITS["fizik"] = scenes_sci.fz_init
INITS["matematik"] = scenes_sci.matematik_init
TITLES["fizik"] = "JARVIS FİZİK LABORATUVARI"
TITLES["matematik"] = "JARVIS MATEMATİK LABORATUVARI"
EXIT_SAY["fizik"] = "Fizik laboratuvarı kapanıyor efendim, normale dönüyorum."
EXIT_SAY["matematik"] = "Matematik laboratuvarı kapanıyor efendim, normale dönüyorum."
HANDLERS["astronomi"] = scenes_sci.astronomi
HANDLERS["jeoloji"] = scenes_sci.jeoloji
HANDLERS["gokyuzu"] = scenes_sci.gokyuzu
INITS["astronomi"] = lambda: scenes_sci.lab_init("astronomi")
INITS["jeoloji"] = lambda: scenes_sci.lab_init("jeoloji")
INITS["gokyuzu"] = scenes_sci.gokyuzu_init
TITLES["astronomi"] = "JARVIS ASTRONOMİ LABORATUVARI"
TITLES["jeoloji"] = "JARVIS JEOLOJİ LABORATUVARI"
TITLES["gokyuzu"] = "JARVIS GÖKYÜZÜ"
EXIT_SAY["astronomi"] = "Astronomi laboratuvarı kapanıyor efendim, normale dönüyorum."
EXIT_SAY["jeoloji"] = "Jeoloji laboratuvarı kapanıyor efendim, normale dönüyorum."
EXIT_SAY["gokyuzu"] = "Gökyüzü haritası kapanıyor efendim, normale dönüyorum."
import scenes_notes  # noqa: E402
import notes as _notes  # noqa: E402

HANDLERS["notlar"] = scenes_notes.notlar
INITS["notlar"] = _notes.init_payload
TITLES["notlar"] = "JARVIS NOTLAR"
EXIT_SAY["notlar"] = "Not modu kapanıyor efendim, normale dönüyorum."
import scenes_yuvam  # noqa: E402

HANDLERS["yuvam"] = scenes_yuvam.yuvam_cmd
INITS["yuvam"] = scenes_yuvam.init_payload
TITLES["yuvam"] = "JARVIS EVİM"
EXIT_SAY["yuvam"] = "Evim modu kapanıyor efendim, normale dönüyorum."
import scenes_hologram  # noqa: E402

HANDLERS["hologram"] = scenes_hologram.hologram
INITS["hologram"] = scenes_hologram.init_payload
TITLES["hologram"] = "JARVIS HOLOGRAM"
EXIT_SAY["hologram"] = "Hologram modu kapanıyor efendim, normale dönüyorum."
import scenes_rapor  # noqa: E402

HANDLERS["rapor"] = scenes_rapor.rapor
INITS["rapor"] = scenes_rapor.init_payload
TITLES["rapor"] = "JARVIS RAPOR"
EXIT_SAY["rapor"] = "Rapor modu kapanıyor efendim, normale dönüyorum."
import scenes_sistem  # noqa: E402

HANDLERS["sistem"] = scenes_sistem.sistem
INITS["sistem"] = scenes_sistem.init_payload
TITLES["sistem"] = "JARVIS SİSTEM ANALİZİ"
EXIT_SAY["sistem"] = "Sistem analizi kapanıyor efendim, normale dönüyorum."
import scenes_ders  # noqa: E402

HANDLERS["ders"] = scenes_ders.ders
INITS["ders"] = scenes_ders.init_payload
TITLES["ders"] = "JARVIS QUIZ"
EXIT_SAY["ders"] = "Quiz modu kapanıyor efendim, normale dönüyorum."
import scenes_pomodoro  # noqa: E402

HANDLERS["pomodoro"] = scenes_pomodoro.pomodoro
INITS["pomodoro"] = lambda: __import__("pomodoro").snapshot()
TITLES["pomodoro"] = "JARVIS POMODORO"
EXIT_SAY["pomodoro"] = "Pomodoro modu kapanıyor efendim, normale dönüyorum."
import scenes_kartlar  # noqa: E402
import scenes_gelisim  # noqa: E402

HANDLERS["kartlar"] = scenes_kartlar.kartlar
INITS["kartlar"] = scenes_kartlar.init_payload
TITLES["kartlar"] = "JARVIS EZBER KARTLARI"
EXIT_SAY["kartlar"] = "Ezber kartları kapanıyor efendim, normale dönüyorum."
HANDLERS["gelisim"] = scenes_gelisim.gelisim
INITS["gelisim"] = scenes_gelisim.init_payload
TITLES["gelisim"] = "JARVIS GELİŞİM"
EXIT_SAY["gelisim"] = "Gelişim paneli kapanıyor efendim, normale dönüyorum."
import scenes_satranc  # noqa: E402
import scenes_oyunlar  # noqa: E402

HANDLERS["satranc"] = scenes_satranc.satranc
INITS["satranc"] = scenes_satranc.init_payload
TITLES["satranc"] = "JARVIS SATRANÇ"
EXIT_SAY["satranc"] = "Satranç kapanıyor efendim, oyun kaldığı yerden devam edebilir. Normale dönüyorum."
HANDLERS["oyunlar"] = scenes_oyunlar.oyunlar
INITS["oyunlar"] = scenes_oyunlar.init_payload
TITLES["oyunlar"] = "JARVIS ZİHİN OYUNLARI"
EXIT_SAY["oyunlar"] = "Zihin oyunları kapanıyor efendim, normale dönüyorum."
import scenes_kuran  # noqa: E402

HANDLERS["kuran"] = scenes_kuran.kuran
INITS["kuran"] = scenes_kuran.init_payload
TITLES["kuran"] = "JARVIS KUR'AN-I KERİM"
EXIT_SAY["kuran"] = "Kur'an-ı Kerim kapanıyor efendim, kaldığınız sayfa kayıtlı."
import scenes_harita  # noqa: E402

HANDLERS["harita"] = scenes_harita.harita
INITS["harita"] = scenes_harita.init_payload
TITLES["harita"] = "JARVIS DÜNYA HARİTASI"
EXIT_SAY["harita"] = "Dünya haritası kapanıyor efendim, normale dönüyorum."
import scenes_listeler  # noqa: E402

HANDLERS["listeler"] = scenes_listeler.listeler
INITS["listeler"] = scenes_listeler.init_payload
TITLES["listeler"] = "JARVIS MÜZİK LİSTELERİ"
EXIT_SAY["listeler"] = "Müzik listeleri kapanıyor efendim. Çalan şarkı çalmaya devam ediyor, durdurmak için müziği durdur demeniz yeterli."
import scenes_vpn  # noqa: E402

HANDLERS["vpn"] = scenes_vpn.vpn_mode
INITS["vpn"] = scenes_vpn.init_payload
TITLES["vpn"] = "JARVIS VPN"
EXIT_SAY["vpn"] = "VPN modu kapanıyor efendim. Bağlantı açıksa arka planda sürer, kapatmak için VPN kapat demeniz yeterli."
import scenes_mola  # noqa: E402

HANDLERS["mola"] = scenes_mola.mola
INITS["mola"] = lambda: __import__("mola").snapshot()
TITLES["mola"] = "JARVIS MOLA"
EXIT_SAY["mola"] = "Mola modu kapanıyor efendim, çalışmaya dönebilirsiniz."
import scenes_uyku, scenes_tarif, scenes_spor, scenes_panel, scenes_telefon, scenes_sinav, scenes_odak  # noqa: E402

HANDLERS["uyku"] = scenes_uyku.uyku
INITS["uyku"] = scenes_uyku.init_payload
TITLES["uyku"] = "JARVIS UYKU"
EXIT_SAY["uyku"] = "Uyku modu kapandı efendim. İyi geceler."
HANDLERS["tarif"] = scenes_tarif.tarif
INITS["tarif"] = scenes_tarif.init_payload
TITLES["tarif"] = "JARVIS TARİF"
EXIT_SAY["tarif"] = "Tarif modu kapanıyor efendim, afiyet olsun."
HANDLERS["spor"] = scenes_spor.spor
INITS["spor"] = scenes_spor.init_payload
TITLES["spor"] = "JARVIS SPOR"
EXIT_SAY["spor"] = "Spor modu kapanıyor efendim."
HANDLERS["panel"] = scenes_panel.panel
INITS["panel"] = scenes_panel.init_payload
TITLES["panel"] = "JARVIS PANEL"
EXIT_SAY["panel"] = "Panel kapanıyor efendim."
HANDLERS["telefon"] = scenes_telefon.telefon
INITS["telefon"] = scenes_telefon.init_payload
TITLES["telefon"] = "JARVIS TELEFON"
EXIT_SAY["telefon"] = "Telefon modu kapandı efendim, uzaktan bağlantı da kapatıldı."
HANDLERS["sinav"] = scenes_sinav.sinav
INITS["sinav"] = scenes_sinav.init_payload
TITLES["sinav"] = "JARVIS SINAV"
EXIT_SAY["sinav"] = "Sınav modu kapandı efendim, iyi çalışmalar."
HANDLERS["odak"] = scenes_odak.odak
INITS["odak"] = scenes_odak.init_payload
TITLES["odak"] = "JARVIS DERİN ODAK"
EXIT_SAY["odak"] = "Odak modu kapandı efendim."
import scenes_planlama  # noqa: E402

HANDLERS["planlama"] = scenes_planlama.planlama_mode
INITS["planlama"] = lambda: __import__("planlama").snapshot()
TITLES["planlama"] = "JARVIS PLANLAMA"
EXIT_SAY["planlama"] = "Planlama modu kapandı efendim, planınız kayıtlı."
import scenes_nasil  # noqa: E402

HANDLERS["nasil"] = scenes_nasil.nasil_mode
INITS["nasil"] = lambda: __import__("nasil").snapshot()
TITLES["nasil"] = "JARVIS NASIL ÇALIŞIR"
EXIT_SAY["nasil"] = "Nasıl çalışır modu kapandı efendim, merakınız hiç bitmesin."
import scenes_yemek  # noqa: E402

HANDLERS["yemek"] = scenes_yemek.yemek_mode
INITS["yemek"] = scenes_yemek.init_payload
TITLES["yemek"] = "JARVIS YEMEK"
EXIT_SAY["yemek"] = "Yemek modu kapandı efendim, afiyet olsun."
import scenes_sohbet  # noqa: E402

HANDLERS["sohbet"] = scenes_sohbet.sohbet_mode
INITS["sohbet"] = scenes_sohbet.init_payload
TITLES["sohbet"] = "JARVIS SOHBET"
EXIT_SAY["sohbet"] = "Sohbet modu kapandı efendim, konuşmak güzeldi."
import scenes_ultron  # noqa: E402

HANDLERS["ultron"] = scenes_ultron.ultron_mode
INITS["ultron"] = scenes_ultron.init_payload
TITLES["ultron"] = "JARVIS ULTRON"          # başlığın JARVIS ile başlaması "masaüstüne geç" (peek_desktop) için gerekli
import scenes_friday  # noqa: E402

HANDLERS["friday"] = scenes_friday.friday_mode
INITS["friday"] = scenes_friday.init_payload
TITLES["friday"] = "JARVIS FRIDAY"          # başlığın JARVIS ile başlaması "masaüstüne geç" (peek_desktop) için gerekli
EXIT_SAY["friday"] = "Friday ayrıldı efendim, işlerine devam edecek. Ben buradayım."
EXIT_SAY["ultron"] ="Ultron ayrıldı efendim. Ama araştırmaya devam edeceğini söyledi. Ben buradayım."
import scenes_luna  # noqa: E402

HANDLERS["luna"] = scenes_luna.luna_mode
INITS["luna"] = scenes_luna.init_payload
TITLES["luna"] = "JARVIS LUNA"              # başlığın JARVIS ile başlaması "masaüstüne geç" (peek_desktop) için gerekli
EXIT_SAY["luna"] = "Luna ayrıldı efendim. Ama araştırmaya devam edeceğini söyledi. Ben buradayım."
import scenes_yeni  # noqa: E402

for _k, _fn, _ti, _ex in (
        ("optik", scenes_yeni.optik, "JARVIS SINAV SİMÜLATÖRÜ", "Sınav simülatörü kapandı efendim, sonuçlarınız kayıtlı."),
        ("tahta", scenes_yeni.tahta, "JARVIS FİKİR TAHTASI", "Fikir tahtası kapandı efendim, notlarınız kayıtlı."),
        ("masa", scenes_yeni.masa, "JARVIS MASA", "Masa kapandı efendim, ayarlarınız kayıtlı."),
        ("okuma", scenes_yeni.okuma, "JARVIS HIZLI OKUMA", "Hızlı okuma kapandı efendim, ilerlemeniz kayıtlı."),
        ("kelime", scenes_yeni.kelime, "JARVIS KELİME KUTUSU", "Kelime kutusu kapandı efendim, ilerlemeniz kayıtlı."),
        ("butce", scenes_yeni.butce, "JARVIS BÜTÇE", "Bütçe kapandı efendim, kayıtlarınız duruyor."),
        ("cark", scenes_yeni.cark, "JARVIS KARAR ÇARKI", "Karar çarkı kapandı efendim."),
        ("baslatici", scenes_yeni.baslat, "JARVIS HIZLI BAŞLATICI", "Hızlı başlatıcı kapandı efendim.")):
    HANDLERS[_k] = _fn
    INITS[_k] = (lambda k=_k: scenes_yeni.init_payload(k))
    TITLES[_k] = _ti
    EXIT_SAY[_k] = _ex
import scenes_gunluk  # noqa: E402

for _k, _fn, _in, _ti, _ex in (
        ("gune", scenes_gunluk.gune, scenes_gunluk.gune_init, "JARVIS GÜNE BAŞLA", "Güne başla kapandı efendim, güzel bir gün dilerim."),
        ("pano", scenes_gunluk.pano_mode, scenes_gunluk.pano_init, "JARVIS PANO", "Pano geçmişi kapandı efendim. Kayıtlar yalnızca bellekte duruyor.")):
    HANDLERS[_k] = _fn
    INITS[_k] = _in
    TITLES[_k] = _ti
    EXIT_SAY[_k] = _ex
import scenes_stark  # noqa: E402
import scenes_pomodoro as _spm  # noqa: E402

for _k, _fn, _in, _ti, _ex in (
        ("zirh", scenes_stark.zirh, scenes_stark.zirh_init, "JARVIS ZIRH KONTROLÜ", "Zırh kontrolü kapandı efendim."),
        ("gorev", scenes_stark.gorev, lambda: scenes_stark.gorev_view(), "JARVIS GÖREV MASASI", "Görev masası kapandı efendim, görevleriniz kayıtlı."),
        ("brifing", scenes_stark.brifing, scenes_stark.brifing_init, "JARVIS BRİFİNG", "Brifing kapandı efendim."),
        ("starklab", scenes_stark.lab, scenes_stark.lab_init, "JARVIS STARK LABORATUVARI", "Stark laboratuvarı kapandı efendim, projeleriniz kayıtlı."),
        ("dunya", scenes_stark.dunya, scenes_stark.dunya_init, "JARVIS HOLOGRAFİK DÜNYA", "Holografik dünya kapandı efendim, yerleriniz kayıtlı."),
        ("odakoda", _spm.pomodoro, lambda: __import__("pomodoro").snapshot(), "JARVIS ODAK ODASI", "Odak odası kapandı efendim."),
        ("guvenlik", scenes_stark.guvenlik, scenes_stark.guvenlik_init, "JARVIS GÜVENLİK MERKEZİ", "Güvenlik merkezi kapandı efendim."),
        ("kopru", scenes_stark.kopru, scenes_stark.kopru_init, "JARVIS ASİSTAN KÖPRÜSÜ", "Asistan köprüsü kapandı efendim.")):
    HANDLERS[_k] = _fn
    INITS[_k] = _in
    TITLES[_k] = _ti
    EXIT_SAY[_k] = _ex
import scenes_elektronik  # noqa: E402

HANDLERS["elektronik"] = scenes_elektronik.elektronik
INITS["elektronik"] = scenes_elektronik.init_payload
TITLES["elektronik"] = "JARVIS ELEKTRONİK LABORATUVARI"          # başlığın JARVIS ile başlaması "masaüstüne geç" (peek_desktop) için gerekli
EXIT_SAY["elektronik"] = "Elektronik laboratuvarı kapandı efendim, kartlarınız kayıtlı."
import scenes_yaratici  # noqa: E402

scenes_yaratici.register()
import scenes_ekitap  # noqa: E402

scenes_ekitap.register()
