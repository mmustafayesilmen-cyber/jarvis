"""Basit ve sık komutları LLM'e sormadan, doğrudan ve hatasız çalıştırır. Eşleşmezse None döner."""
import os, re, datetime
import tools

GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _say_datetime(t: str) -> str:
    n = datetime.datetime.now()
    if "saat" in t:
        return f"Saat {n:%H:%M} efendim."
    return f"Bugün {n.day} {AYLAR[n.month - 1]} {n.year}, {GUNLER[n.weekday()]} efendim."


def _say_wifi(raw: str = None) -> str:
    raw = raw if raw is not None else tools.wifi_name()
    m = re.match(r"SSID: (.+?), sinyal: (.+)", raw)
    return f"{m.group(1)} ağına bağlısınız, sinyal gücü {m.group(2)} efendim." if m else "Şu anda bir Wi-Fi ağına bağlı değilsiniz efendim."


def _say_system(raw: str = None) -> str:
    raw = raw if raw is not None else tools.system_info()
    cpu, ram, disk = (re.search(p, raw) for p in (r"CPU %(\d+)", r"RAM %(\d+)", r"Disk doluluğu %(\d+)"))
    return (f"İşlemci yüzde {cpu.group(1)}, bellek yüzde {ram.group(1)}, disk yüzde {disk.group(1)} dolu efendim."
            if cpu and ram and disk else "Sistem bilgisini okuyamadım efendim.")


def _say_list(raw: str, empty_words=("yok", "Henüz")) -> str:
    if any(raw.startswith(w) or w in raw[:40] for w in empty_words):
        return raw.rstrip(".") + " efendim."
    return raw.replace("\n- ", ", ").replace("\n", ", ").lstrip("- ") + "."


def _say_whatsapp(raw: str = None) -> str:
    raw = raw if raw is not None else tools.read_whatsapp()
    if raw.startswith("HATA"):
        return "WhatsApp'ı şu an okuyamadım efendim. " + raw[5:].strip().strip("()").rstrip(".") + "."
    if raw.startswith(("Okunmamış WhatsApp sohbeti yok", "Yeni WhatsApp mesajı yok")):
        return "Okunmamış WhatsApp mesajınız yok efendim."
    items = []
    for line in raw.splitlines():
        who, _, msg = line.partition(": ")
        who, msg = who.strip(), msg.strip()
        if not who:
            continue
        m = re.match(r"^(.*?) \((\d+) mesaj\)$", who)
        name, n = (m.group(1), int(m.group(2))) if m else (who, 1)
        if msg.startswith("(metin okunamadı"):
            items.append(f"{name} size yazmış ama mesajı okuyamadım.")
        elif n > 1:
            items.append(f"{name} size {n} mesaj yazmış, sonuncusu: {msg if msg[-1] in '.!?' else msg + '.'}")
        else:
            items.append(f"{name} yazmış: {msg if msg[-1] in '.!?' else msg + '.'}")
    if not items:
        return "Okunmamış WhatsApp mesajınız yok efendim."
    head = f"{len(items)} okunmamış sohbetiniz var efendim." if len(items) > 1 else "Bir okunmamış sohbetiniz var efendim."
    return head + " " + " ".join(items[:5]) + (f" Ayrıca {len(items) - 5} sohbet daha var." if len(items) > 5 else "")


# Kesin veri döndüren araçlar: sonucu modele yorumlatmadan doğrudan söyle (küçük model sayıları uydurabiliyor)
DIRECT = {
    "read_whatsapp": lambda raw: _say_whatsapp(raw),
    "system_info": lambda raw: _say_system(raw),
    "wifi_name": lambda raw: _say_wifi(raw),
    "datetime_now": lambda raw: _say_datetime("tarih"),
    "list_reminders": lambda raw: "Bekleyen hatırlatmalarınız: " + _say_list(raw) if "yok" not in raw else "Bekleyen bir hatırlatmanız yok efendim.",
    "recall": lambda raw: "Bana şunları söylemiştiniz efendim: " + _say_list(raw) if not raw.startswith("Henüz") else "Henüz hatırlamamı istediğiniz bir şey yok efendim.",
}

SITES = {"youtube": "youtube.com", "google": "google.com", "gmail": "mail.google.com", "github": "github.com",
         "instagram": "instagram.com", "twitter": "x.com", "netflix": "netflix.com", "chatgpt": "chatgpt.com",
         "haritalar": "maps.google.com", "harita": "maps.google.com", "twitch": "twitch.tv",}
MUSIC = {"youtube müzik", "youtube music", "yt music", "yt müzik", "müzik", "youtube musik"}
NOISE = re.compile(r"\b(jarvis|hey|lütfen|bana|şunu|bir|efendim|acaba|hadi|sen)\b")


def _norm(t: str) -> str:
    t = t.replace("İ", "i").replace("I", "ı").lower()
    t = re.sub(r"['’]\w*", "", t)          # Spotify'ı -> spotify, youtube'da -> youtube
    t = re.sub(r"[^\w\sçğıöşü%]", " ", t)
    t = NOISE.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


def _candidates(w: str):
    """Ek almış olabilecek bir ismin olası kökleri (en uzundan kısaya): 'spotifyı' -> spotifyı, spotify, spotif."""
    out = [w]
    for n in (1, 2):
        if len(w) - n >= 4 and w[-n:] in ("ı", "i", "u", "ü", "yı", "yi", "yu", "yü", "nı", "ni", "nu", "nü", "a", "e", "ya", "ye"):
            out.append(w[:-n])
    return out


def _failed(res: str) -> bool:
    return any(k in res for k in ("Start-Process", "Cannot", "cannot", "bulunamadı", "hata", "HATA"))


def route(text: str, _in_routine: bool = False):
    if not _in_routine:
        import extras
        sel = extras.site_select(text)                # "site modu" listesinden sonra gelen numara
        if sel:
            return sel
        rr = route_routine(text)                      # rutin oluştur / çalıştır / sil / listele
        if rr:
            return rr
    t = _norm(text)
    if not t:
        return None
    extra = route_tr_extra(t)
    if extra:
        return extra
    import extras
    ex = extras.route(t, text)
    if ex:
        return ex

    if re.fullmatch(r"(saat kaç|saat kaçtı|şu an saat kaç|saati söyle|saat ne|tarih ne|bugünün tarihi ne|bugün ayın kaçı|bugün günlerden ne|bugün hangi gün|hangi gündeyiz|günlerden ne)", t):
        return _say_datetime(t)
    if (re.search(r"wifi|wi fi|kablosuz ağ", t) and re.search(r"(ad|isim|ne|hangi)", t)) or re.fullmatch(r"(hangi|ne) (internete|ağa) bağlıyım|internetim ne", t):
        return _say_wifi()
    m = re.fullmatch(r"(?:sesi|ses seviyesini|ses)\s*(?:yüzde\s*)?%?\s*(\d{1,3})\s*(?:yap|olsun|ayarla|yüzde)?", t)
    if m:
        return tools.set_volume(min(100, int(m.group(1)))) and f"Ses yüzde {min(100, int(m.group(1)))} efendim."
    if re.fullmatch(r"(sonraki|sonraki şarkı|bir sonraki şarkı|şarkıyı geç|geç)", t):
        import study_music
        if not study_music.skip():
            tools.media_key("next")
        return "Sonraki şarkı efendim."
    if re.fullmatch(r"(önceki|önceki şarkı|bir önceki şarkı|geri al)", t):
        tools.media_key("prev"); return "Önceki şarkı efendim."
    if re.fullmatch(r"(şarkıyı |müziği |bunu )?(döngüye al|döngüde çal|tekrarla|tekrar çal|sürekli çal|döngüye koy|döngü(yü)? aç)", t):
        import study_music
        study_music.set_repeat(True)
        return "Şarkı döngüde efendim." if study_music.active() else "Döngü açık, bir sonraki şarkı tekrar edecek efendim."
    if re.fullmatch(r"(şarkı |müzik )?(döngüyü|tekrarı) (kapat|durdur|kaldır|bitir)|döngüden çıkar|döngüyü kapat", t):
        import study_music
        study_music.set_repeat(False)
        return "Döngüyü kapattım efendim."
    if re.fullmatch(r"(durdur|duraklat|müziği durdur|şarkıyı durdur|devam et|müziği devam ettir|şarkıyı durdur)", t):
        tools.media_key("playpause"); return "Tamam efendim."
    if re.fullmatch(r"(sistem durumu|bilgisayar(ımın|ın)? durumu|bilgisayar(ım)? nasıl|bilgisayarımın durumu nasıl|sistem nasıl|sistemin durumu( nasıl)?)( nasıl)?", t):
        return _say_system()

    if re.fullmatch(r"ders (müziği|müzikleri|şarkıları|listesi)(ni)?( çal| aç| başlat)?", t):
        tools.play_study_music(); return "Ders şarkıları sırayla, döngüde çalıyor efendim."
    if re.fullmatch(r"ders (müziği|müzikleri|şarkıları|listesi)(ni)? (durdur|kapat|bitir|kes)", t):
        import study_music
        return "Ders müziğini durdurdum efendim." if study_music.stop() else "Ders müziği zaten çalmıyor efendim."

    # "... çal / oynat"
    m = re.fullmatch(r"(?:youtube(?:'?da| müzikte| musicte)?\s+)?(.+?)\s+(?:çal|çalsana|çalar mısın|oynat|dinlet|dinleyelim)", t)
    if m and len(t.split()) <= 8:
        q = m.group(1)
        return f"{q} çalıyorum efendim." if "çalıyor" in tools.play_music(q) else f"{q} adlı şarkıyı bulamadım efendim."
    m = re.fullmatch(r"(?:şarkı|müzik)\s+(?:aç|çal)\s+(.+)", t)
    if m:
        q = m.group(1)
        return f"{q} çalıyorum efendim." if "çalıyor" in tools.play_music(q) else f"{q} adlı şarkıyı bulamadım efendim."
    if re.fullmatch(r"(mikrofonu|dinlemeyi) (kapat|durdur)|beni dinleme|dinleme", t):
        if tools.MIC_HOOK:
            tools.MIC_HOOK(True)
            return "Mikrofonu kapattım efendim. Artık yalnızca Hey Jarvis dediğinizde uyanırım, ayar siz açana kadar böyle kalır. Tamamen açmak için ekrandaki mikrofon düğmesine basın ya da yazarak mikrofonu aç deyin."
    if re.fullmatch(r"(mikrofonu|dinlemeyi) (aç|başlat)|dinlemeye başla", t):
        if tools.MIC_HOOK:
            tools.MIC_HOOK(False)
            return "Mikrofon açık efendim, dinliyorum."

    # "youtube'da X izle/ara/aç"
    m = re.fullmatch(r"youtube\s+(.+?)\s+(?:izle|aç|ara|arat|bul)", t)
    if m and m.group(1) not in MUSIC:
        tools.play_youtube(m.group(1)); return f"{m.group(1)} açılıyor efendim."

    # "X kapat"
    m = re.fullmatch(r"(.+?)\s+(?:kapat|kapatır mısın|kapatsana|sonlandır)", t)
    if m and len(m.group(1).split()) <= 3 and "kendini" not in m.group(1) and "bilgisayar" not in m.group(1):
        for name in _candidates(m.group(1).split()[-1]):
            if not tools.close_app(name).startswith("0 "):
                return f"{name} kapatıldı efendim."
        return f"{m.group(1)} çalışmıyor efendim."

    # "X aç"
    m = re.fullmatch(r"(.+?)\s+(?:aç|açar mısın|açsana|açın|başlat|çalıştır|göster)", t)
    if m and len(m.group(1).split()) <= 3:
        target = m.group(1).strip()
        key = target
        for c in _candidates(target):
            if c in SITES or c in MUSIC:
                key = c
        if target in MUSIC or key in MUSIC:
            tools.open_website("music.youtube.com"); return "YouTube Music açılıyor efendim."
        if key in SITES or target in SITES:
            tools.open_website(SITES.get(key) or SITES[target]); return f"{target} açılıyor efendim."
        if re.fullmatch(r"[\w.-]+\.(com|net|org|tr|io|gov|edu)(\.tr)?", target):
            tools.open_website(target); return f"{target} açılıyor efendim."
        for name in _candidates(target):
            if not _failed(tools.open_app(name)):
                return f"{name} açılıyor efendim."
        return None
    return None


NUMS = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10,
        "on beş": 15, "yirmi": 20, "otuz": 30, "kırk": 40, "kırk beş": 45, "elli": 50, "yarım": 0.5, "bir buçuk": 1.5}
_NUM = r"(\d+(?:[.,]\d+)?|" + "|".join(sorted(NUMS, key=len, reverse=True)) + r")"
_UNIT = {"saniye": 1 / 60, "dakika": 1, "saat": 60}


def _num(s):
    return float(s.replace(",", ".")) if re.match(r"\d", s) else NUMS[s]


def _dur_text(n, unit):
    return f"{n:g} {unit}"


def text_hint(t: str) -> str:
    return t


FAN_LEVELS = {"çok yavaş": 20, "yavaş": 35, "orta": 60, "hızlı": 85, "çok hızlı": 100, "tam": 100, "maksimum": 100, "en hızlı": 100}


def _fan_do(pct: int) -> str:
    res = tools.set_fan(pct)
    if res.startswith("HATA"):
        return "Fana ulaşamadım efendim, Arduino kartının bağlı olduğundan emin olun."
    return "Fanı kapattım efendim." if pct == 0 else f"Fanı yüzde {pct} hızda çalıştırıyorum efendim."


def _route_fan(t: str):
    if not re.search(r"\b(fan\w*|pervane\w*|vantilatör\w*)\b", t):
        return None
    if re.search(r"\b(kapat\w*|durdur\w*|söndür\w*|sustur\w*)\b", t) and not re.search(r"\d", t):
        return _fan_do(0)
    m = re.search(r"%?\s*(\d{1,3})\s*(?:yüzde|%)?", t)
    if m and re.search(r"yüzde|%|hız|yap|ayarla|olsun", t):
        return _fan_do(min(100, int(m.group(1))))
    for name in sorted(FAN_LEVELS, key=len, reverse=True):
        if re.search(rf"\b{name}\b", t):
            return _fan_do(FAN_LEVELS[name])
    if re.search(r"\b(aç\w*|çalıştır\w*|başlat\w*)\b", t):
        return _fan_do(60)
    return None


def _say_home(device: str, state: str) -> str:
    res = tools.home_control(device, state)
    if res.startswith("HATA"):
        return res[6:].strip().rstrip(".") + " efendim."
    if "zaten" in res:
        return res.rstrip(".") + " efendim."
    name = res.rsplit(" ", 2)[0]
    return f"Tamam efendim, {'ışık açıldı' if state == 'on' else 'ışık kapatıldı'}." if not device else f"Tamam efendim, {name} {'açıldı' if state == 'on' else 'kapatıldı'}."


def _say_phonelink(action: str) -> str:
    res = tools.phone_link(action)
    return res[6:].strip().rstrip(".") + " efendim." if res.startswith("HATA") else res.rstrip(".") + " efendim."


_NUMW = {"sıfır": 0, "bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10,
         "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50, "altmış": 60, "yetmiş": 70, "seksen": 80, "doksan": 90, "yüz": 100}


def _numwords_to_digits(s: str) -> str:
    """'yüzde otuz beş' -> 'yüzde 35', 'elli' -> '50' (tek sayı ya da onlar+birler birleşimi)."""
    toks, out, i = s.split(), [], 0
    while i < len(toks):
        w = toks[i]
        if w in _NUMW:
            v = _NUMW[w]
            if 10 <= v < 100 and i + 1 < len(toks) and toks[i + 1] in _NUMW and 0 < _NUMW[toks[i + 1]] < 10:
                v += _NUMW[toks[i + 1]]
                i += 1
            out.append(str(v))
        else:
            out.append(w)
        i += 1
    return " ".join(out)


def _say_volume(t: str):
    """Ses komutları: artır / azalt / kapat-sustur / aç / yüzde N / ne kadar. None = ses komutu değil."""
    m = re.match(r"^(?:bilgisayar\w*\s+|hoparlör\w*\s+|müzik\w*\s+)?(?:sesi|sesini|ses seviyesini|ses düzeyini|ses seviyesi|ses düzeyi|ses)\b\s*(?P<rest>.*)$", t)
    if not m or re.match(r"^(?:sesli|seslen)", t):
        return None
    rest = _numwords_to_digits(m.group("rest").strip())
    ms = re.match(r"^sınır\w*\s*(?:yüzde\s*)?%?\s*(\d{1,3})?\s*(yap|olsun|ayarla|koy|ne|kaç|nedir)?$", rest)
    if ms:
        import settings
        if ms.group(1):
            settings.set("volume_max", max(5, min(100, int(ms.group(1)))))
            return f"Ses sınırını yüzde {settings.get('volume_max')} yaptım efendim. Bundan yüksek sese çıkmayacağım."
        return f"Ses sınırı yüzde {settings.get('volume_max')} efendim."
    num = re.search(r"(\d{1,3})", rest)
    n = int(num.group(1)) if num else None
    big = re.search(r"\b(çok|iyice|epey|bayağı|fazla)\b", rest)
    small = re.search(r"\b(biraz|azıcık|azıcık|hafif|bir tık|tık)\b", rest)
    step = n if (n and re.search(r"artır|yükselt|azalt|kıs|düşür|indir|alçalt", rest)) else (5 if big else 1 if small else 2)
    try:
        if re.search(r"ne kadar|kaç|nedir|\bne$", rest) and not n:
            return f"Ses seviyesi yüzde {tools.get_volume()} efendim." + (" Ama ses şu anda kapalı." if tools.is_muted() else "")
        if re.search(r"sessizden çıkar|geri aç|sessizi kapat|sessiz modu kapat", rest):
            tools.set_mute(False)
            return f"Sesi açtım efendim, yüzde {tools.get_volume()}."
        if re.search(r"kapat|sustur|kes|sessiz|mute", rest):
            tools.set_mute(True)
            return "Sesi kapattım efendim."
        if re.search(r"\btam\b|maksimum|sonuna kadar|en yüksek|en fazla", rest):
            tools.set_volume(100)
            return f"Sesi izin verilen en yüksek seviyeye çıkardım efendim, yüzde {tools.get_volume()}."
        if re.search(r"en düşük|minimum|en aza|en kısık", rest):
            tools.set_volume(2)
            return "Sesi en düşük seviyeye indirdim efendim."
        if re.search(r"artır|yükselt|güçlendir|çoğalt|yüksel|aç\b|açar|açsana", rest) and not re.search(r"azalt|kıs", rest):
            if re.search(r"^aç\b|^açar|^açsana", rest) and tools.is_muted():
                tools.set_mute(False)
                return f"Sesi açtım efendim, yüzde {tools.get_volume()}."
            tools.change_volume(step)
            return f"Sesi artırdım efendim, şimdi yüzde {tools.get_volume()}."
        if re.search(r"azalt|kıs|düşür|alçalt|indir|düşük|kısalım", rest) and not re.search(r"çok düşük|çok kısık", rest):
            tools.change_volume(-step)
            return f"Sesi azalttım efendim, şimdi yüzde {tools.get_volume()}."
        if re.search(r"çok (yüksek|fazla|açık|gürültülü)", rest):
            tools.change_volume(-3)
            return f"Sesi kıstım efendim, şimdi yüzde {tools.get_volume()}."
        if re.search(r"çok (düşük|az|kısık|kısık)", rest):
            tools.change_volume(3)
            return f"Sesi yükselttim efendim, şimdi yüzde {tools.get_volume()}."
        if n is not None and re.fullmatch(r"(?:yüzde\s*)?%?\s*\d{1,3}\s*(?:yap|olsun|ayarla|yüzde|e getir|a getir|yapar mısın)?", rest):
            tools.set_volume(n)
            now = tools.get_volume()
            return (f"Sesi yüzde {now} yaptım efendim." if now == min(n, 100) else
                    f"Ses sınırı yüzde {now} olduğu için sesi en fazla yüzde {now} yapabildim efendim.")
    except Exception as e:
        return f"Ses ayarına ulaşamadım efendim: {str(e)[:60]}."
    return None


def route_tr_extra(t: str):
    import reminders, memory
    if re.search(r"(ses|tanı|tanıma) kayıt\w*", t) and re.search(r"\b(sil|temizle|kaldır)", t):
        import glob
        files = glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "diag", "*.wav"))
        for f in files:
            try:
                os.remove(f)
            except OSError:
                pass
        return f"{len(files)} ses kaydını sildim efendim." if files else "Silinecek ses kaydı yoktu efendim."
    if re.search(r"(ses|tanı|tanıma) kayıt\w*", t) and re.search(r"\b(kapat|durdur|tutma|saklama)", t):
        import settings
        settings.set("save_clips", False)
        return "Artık ses parçalarını saklamayacağım efendim."
    v = _say_volume(t)
    if v:
        return v
    if re.search(r"telefon", t):
        if re.search(r"\b(bul|çaldır|çalsın|nerede|ses çıkar)", t):
            return _say_phonelink("find")
        if re.search(r"fotoğraf|resim|galeri", t):
            return _say_phonelink("photos")
        if re.search(r"mesaj|sms", t) and not re.search(r"\b(yaz|gönder|at)\b", t):
            return _say_phonelink("messages")
        if re.search(r"arama|aramalar", t):
            return _say_phonelink("calls")
        if re.search(r"telefon\w* (bağlantı\w*|link)|phone link", t) and re.search(r"\b(aç|göster|getir|başlat)\b", t) and not re.search(r"kablosuz|wi ?fi", t):
            return _say_phonelink("open")                     # "telefon bağlantısını aç" = Windows uygulaması
        if re.fullmatch(r"telefon\w*\s*(ekran\w*\s*)?(kapat|söndür|uyut)|telefon\w* ekran\w* (kapat|söndür)\w*", t):
            import phone
            return phone.wake(False)
        if re.fullmatch(r"telefon\w*\s*(aç|açar mısın|açsana|uyandır|uyandırsana|ekranı|ekranını aç|ekranı aç|ekran aç|göster|getir|yak)|telefon\w* ekran\w*( aç\w*| yak\w*)?", t):
            import phone
            return phone.wake(True)
        if re.search(r"(uygulama|site|internet|youtube|whatsapp|instagram|chrome)", t) and re.search(r"\b(aç|başlat|git|gir)\b", t):
            return ("Telefon Bağlantısı bu telefonda uygulama açmayı desteklemiyor efendim. Telefondaki bir uygulamayı açmak "
                    "için kablolu bağlantıya, yani USB hata ayıklamaya ihtiyacım var.")
    m = re.fullmatch(r"(.*?)\s*\b(ışı\w*|lamba\w*|spot\w*|avize\w*|priz\w*|switch\w*|anahtar\w*)\s*(.*?)\s*(aç|açar mısın|açsana|yak|yakar mısın|yaksana|kapat|kapatır mısın|kapatsana|söndür|söndürsene)",
                     t)
    if m and not re.search(r"\b(whatsapp|ekran|youtube|hatırlat)\b", t):
        phrase = " ".join(x for x in (m.group(1), m.group(2), m.group(3)) if x)
        on = m.group(4).startswith(("aç", "yak"))
        return _say_home(phrase if re.sub(r"\bışı\w*|lamba\w*", "", phrase).strip() not in ("", "benim", "odamın", "odamdaki") else "",
                         "on" if on else "off")
    if re.search(r"w?h?a?t+s+a+p+|vatsap|vatsapp|watsap|whatsap|uatsap|mesaj", t) \
            and re.search(r"\boku|okur|var mı|geldi|neler|kim|yeni|göster|kontrol|gelen", t) \
            and not re.search(r"\b(yaz|gönder|at|yazsın)\b", t) and not re.search(r"telefon|sms", t):
        return _say_whatsapp()
    # hatırlatıcı: "10 dakika sonra çayı hatırlat" / "yarım saat sonra bana toplantıyı hatırlat"
    m = re.fullmatch(_NUM + r"\s*(saniye|dakika|saat)\s*sonra\s+(?:bana\s+)?(.+?)\s*(?:diye\s+)?(?:hatırlat|hatırlatır mısın|hatırlatsana|söyle)", t)
    if m:
        n, unit, msg = _num(m.group(1)), m.group(2), m.group(3)
        reminders.add(n * _UNIT[unit] * 60, msg, "object")      # 'çayı' -> 'çayı hatırlatmamı istemiştiniz'
        return f"Tamam efendim, {m.group(1)} {unit} sonra size {msg} hatırlatacağım."
    # "25 dakikalık zamanlayıcı kur", "1 saat 30 dakika sayaç", "iki buçuk saatlik tam ekran zamanlayıcı"
    m = re.fullmatch(r"(?:" + _NUM + r"\s*saat(?:lık|lik)?\s*(?:ve\s+)?)?" + _NUM + r"\s*(saniye|dakika|saat)(?:lık|lik)?\s*(?:bir\s+)?"
                     r"(tam ekran\s+|ekranda\s+|ekranda gösteren\s+)?(zamanlayıcı|sayaç|alarm)\w*\s*(?:kur|başlat|ayarla|göster|aç)?", t)
    if m and not (m.group(1) and m.group(3) == "saat"):
        h_part = _num(m.group(1)) * 60 if m.group(1) else 0
        n, unit = _num(m.group(2)), m.group(3)
        minutes = h_part + n * _UNIT[unit]
        label = (f"{m.group(1)} saat " if m.group(1) else "") + f"{m.group(2)} {unit}"
        if m.group(5) == "alarm" and not m.group(4):          # düz "alarm": ekransız, süre dolunca sesli haber
            reminders.add(minutes * 60, label, "timer")
            return f"Tamam efendim, {label} sonra haber vereceğim."
        tools.show_timer(minutes, (_CURRENT_ROUTINE["name"] or "Zamanlayıcı"))
        return f"{label} için tam ekran sayacı başlattım efendim."
    if re.fullmatch(r"(hatırlatmaları|hatırlatıcıları|zamanlayıcıları|alarmları)\s*(iptal et|sil|kapat)", t):
        n = reminders.cancel_all()
        return f"Bekleyen {n} hatırlatmayı iptal ettim efendim." if n else "Bekleyen bir hatırlatma yoktu efendim."
    if re.fullmatch(r"(hatırlatmalarım|bekleyen hatırlatmalar|hatırlatmaları söyle|hangi hatırlatmalar var|hatırlatmalarım neler)", t):
        items = reminders.pending()
        if not items:
            return "Bekleyen bir hatırlatmanız yok efendim."
        parts = [f"saat {datetime.datetime.fromtimestamp(i['due']):%H:%M} için " +
                 (f"{reminders.lik(i['message'])} zamanlayıcı" if i["kind"] == "timer" else f"{i['message']} hatırlatması") for i in items]
        return "Bekleyen hatırlatmalarınız şunlar efendim: " + ", ".join(parts) + "."
    # fan (Arduino)
    r = _route_fan(t)
    if r:
        return r
    # hafıza
    m = re.fullmatch(r"(.+?)\s*(?:bunu\s+)?(?:hatırla|unutma|aklında tut|aklında bulunsun)", t)
    if m and not re.search(r"\b(sonra|ne|neyi|neler)\b", m.group(1)):
        res = tools.remember(m.group(1))
        if res.startswith("Güvenlik"):
            return "Güvenliğiniz için şifre, kart ya da kimlik bilgisi saklamıyorum efendim."
        return "Bunu zaten biliyorum efendim." if res.startswith("Bunu zaten") else "Tamam efendim, bunu hatırlayacağım."
    if re.fullmatch(r"(benimle ilgili |hakkımda )?(neleri|ne|neler) hatırlıyorsun|(benim )?hakkımda (ne|neler) biliyorsun|benimle ilgili (ne|neler) biliyorsun|hafızanda (ne|neler) var", t):
        f = memory.facts()
        return ("Bana şunları söylemiştiniz efendim: " + "; ".join(f) + ".") if f else "Henüz bana hatırlamamı istediğiniz bir şey söylemediniz efendim."
    m = re.fullmatch(r"(.+?)\s*(?:bilgisini\s+)?unut", t)
    if m and m.group(1) not in ("beni", "her şeyi"):
        res = tools.forget(m.group(1))
        return "Tamam efendim, onu unuttum." if not res.startswith("Bununla") else "Bununla ilgili bir şey hatırlamıyordum efendim."
    # ekranı görme
    if re.search(r"ekran", t) and re.search(r"ne var|bak|oku|anlat|özetle|açıkla|gör", t):
        return tools.look_at_screen(text_hint(t))
    # ses motoru
    if re.search(r"(yerel|çevrimdışı|offline) ses", t) and re.search(r"geç|kullan|aç", t):
        import settings
        settings.set("tts", "piper")
        return "Artık tamamen yerel sesle konuşuyorum efendim."
    if re.search(r"(internet|doğal|microsoft|eski) ses", t) and re.search(r"geç|kullan|aç", t):
        import settings
        settings.set("tts", "edge")
        return "Daha doğal internet sesine geçtim efendim. Söylediklerim seslendirme için Microsoft'a gönderilecek."
    if re.search(r"telefon", t) and re.search(r"bağla|bağlan|aktar", t) and not re.search(r"mesaj|fotoğraf|arama|kablosuz|wi ?fi|ağ üzerinden", t):
        import phone
        return phone.connect("tr")
    if re.search(r"telefon", t) and re.search(r"kes|ayır|kopar", t):
        import phone
        return phone.disconnect()
    return None


EN_SITES = SITES


def route_en(text: str):
    """English quick commands; answers in English. Returns None if not matched."""
    t = re.sub(r"[^\w\s%.]", " ", text.lower())
    t = re.sub(r"\b(jarvis|hey|please|can you|could you|would you|for me|the|now)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" .")
    n = datetime.datetime.now()
    if re.fullmatch(r"(what time is it|what s time|time|tell me time)", t):
        return f"It's {n:%H:%M}, sir."
    if re.fullmatch(r"(what s date|what day is it|what is date|what s date today|what day is today)", t):
        return f"Today is {n:%A, %d %B %Y}, sir."
    if "wifi" in t.replace("-", "").replace(" ", "") and re.search(r"name|which|what", t):
        m = re.match(r"SSID: (.+?), sinyal: (.+)", tools.wifi_name())
        return f"You're connected to {m.group(1)}, sir." if m else "You're not connected to any Wi-Fi network, sir."
    if re.search(r"phone", t) and re.search(r"connect", t):
        import phone
        return phone.connect("en")
    m = re.fullmatch(r"(?:play|put on)\s+(.+?)(?:\s+on youtube music| on youtube)?", t)
    if m:
        tools.play_music(m.group(1)); return f"Playing {m.group(1)}, sir."
    m = re.fullmatch(r"(?:close|quit|kill)\s+(.+)", t)
    if m and len(m.group(1).split()) <= 3:
        n_ = tools.close_app(m.group(1).split()[-1])
        return f"{m.group(1)} is closed, sir." if not n_.startswith("0 ") else f"{m.group(1)} isn't running, sir."
    m = re.fullmatch(r"(?:open|launch|start)\s+(.+)", t)
    if m and len(m.group(1).split()) <= 3:
        target = m.group(1).strip()
        if target in ("youtube music", "yt music", "music"):
            tools.open_website("music.youtube.com"); return "Opening YouTube Music, sir."
        if target in EN_SITES:
            tools.open_website(EN_SITES[target]); return f"Opening {target}, sir."
        if re.fullmatch(r"[\w.-]+\.(com|net|org|io|dev|tr)", target):
            tools.open_website(target); return f"Opening {target}, sir."
        if not _failed(tools.open_app("hesap makinesi" if target == "calculator" else target)):
            return f"Opening {target}, sir."
    return None


# ---------------------------------------------------------------- rutinler
_STEP_SPLIT = re.compile(r"\s*(?:,|;|(?<!\d)\.(?!\d)|\bve sonra\b|\bardından\b|\bdaha sonra\b|\bsonra\b|\bve\b)\s*")
_FORBIDDEN_STEP = re.compile(r"\b(sil\w*|formatla\w*|sistemi|bilgisayarı|bilgisayar|yeniden başlat\w*|rutin\w*|gönder\w*)\b")
_SUFFIX = r"(?:modunu|modu|moduna|rutinini|rutini|rutin)"


def _rname(s: str) -> str:
    s = re.sub(r"^(jarvis|hey|lütfen|bir|yeni)\b[\s,]*", "", s.strip(), flags=re.I)
    s = re.sub(r"\s*" + _SUFFIX + r"\s*$", "", s.strip())
    return " ".join(s.split()).strip(" ,.:;")


def _words(low: str) -> list:
    return re.findall(r"[\wçğıöşü]+", low)


_MODE_W = re.compile(r"^(mod\w*|rutin\w*)$")
_DROP_W = re.compile(r"^(jarvis|hey|lütfen|bir|başlat\w*|çalıştır\w*|başla|etkinleştir\w*|geç|geçelim|al)$")


_CURRENT_ROUTINE = {"name": None}


def _run_steps(name: str, steps: list, say: str = None) -> str:
    _CURRENT_ROUTINE["name"] = name
    failed, infos = [], []
    for step in steps:
        info = step.lower().startswith("söyle:")
        cmd = step.split(":", 1)[1].strip() if info else step
        try:
            res = route(cmd, True)
        except Exception:
            res = None
        if not res:
            failed.append(cmd)
        elif info:
            infos.append(res)
    _CURRENT_ROUTINE["name"] = None
    head = say or f"{name.capitalize()} modunu başlattım efendim."
    if infos:
        head = head.rstrip(".") + ". " + " ".join(infos)
    if failed:
        head += f" Ama şu adımı yapamadım: {failed[0]}."
    return head


def _find_routine(low: str):
    """Cümleden bir rutin bul: (ad, adımlar, söylenecek metin) ya da None. Kullanıcının kendi rutini hazır olanı geçer."""
    import routines
    toks = _words(low)
    had_mode = any(_MODE_W.match(w) for w in toks)
    clean = " ".join(w for w in toks if not _MODE_W.match(w) and not _DROP_W.match(w))
    if not clean:
        return None
    custom = routines.get(clean) if had_mode else None
    if custom:
        return clean, custom["steps"], None
    for name, b in routines.BUILTIN.items():
        if clean in b["phrases"] or (had_mode and clean in b["names"]):
            return name, b["steps"], b["say"]
    return None


def route_routine(text: str):
    import routines
    low = text.replace("İ", "i").replace("I", "ı").lower().strip()
    low = re.sub(r"^(jarvis|hey)\b[\s,]*", "", low).strip()
    if re.search(r"rutin|\bmod", low):
        # --- oluştur: "film modu rutini oluştur: ışığımı kapat, sesi yüzde 30 yap, youtube aç"
        m = (re.match(r"^(?:yeni\s+)?rutin\s+(?:oluştur\w*|kaydet\w*|ekle\w*|tanımla\w*)\s*[:,]?\s*(?P<name>[^:,]+?)\s*[:,]\s*(?P<steps>.+)$", low)
             or re.match(r"^(?P<name>[^:,]+?)\s+" + _SUFFIX + r"\s*(?:diye\s+)?(?:oluştur\w*|kaydet\w*|ekle\w*|tanımla\w*)\s*[:,]?\s*(?P<steps>.+)$", low))
        if m:
            name = _rname(m.group("name"))
            steps = [s.strip(" .!?") for s in _STEP_SPLIT.split(m.group("steps")) if s.strip(" .!?")]
            if not name or not steps:
                return "Rutinin adını ve adımlarını anlayamadım efendim. Örneğin: akşam modu rutini oluştur, ışığımı aç, müzik çal."
            bad = [s for s in steps if _FORBIDDEN_STEP.search(s)]
            if bad:
                return f"Güvenlik nedeniyle rutinlere silme, kapatma ya da mesaj gönderme adımı eklemiyorum efendim: {bad[0]}."
            if len(steps) > routines.MAX_STEPS:
                return f"Bir rutinde en fazla {routines.MAX_STEPS} adım olabilir efendim."
            routines.add(name, steps)
            return (f"{name.capitalize()} rutinini kaydettim efendim. İçinde {len(steps)} adım var: " + ", ".join(steps) +
                    f". Çalıştırmak için {name} modu demeniz yeterli.")
        # --- listele
        if re.match(r"^(rutinlerim|rutinleri (söyle|listele|say|oku|anlat)|hangi (rutinler|modlar) var|rutinlerim neler|rutinler neler|modlar neler|modlarım)", low):
            ns = [n.capitalize() for n in routines.BUILTIN] + [n.capitalize() for n in routines.names() if n not in routines.BUILTIN]
            return "Hazır ve kayıtlı rutinleriniz: " + ", ".join(ns) + ". Birini çalıştırmak için adını ve modu deyin, örneğin film modu."
        # --- ne yapar
        m = re.match(r"^(?P<name>.+?)\s*(?:" + _SUFFIX + r")?\s*(?:ne yapar|neler yapar|içinde ne var|ne yapıyor)$", low)
        if m:
            f = _find_routine(_rname(m.group("name")) + " modu")
            if f:
                return f"{f[0].capitalize()} modu şunları yapar efendim: " + ", ".join(s.split(":", 1)[-1].strip() for s in f[1]) + "."
        # --- sil
        m = re.match(r"^(?P<name>.+?)\s+" + _SUFFIX + r"\s+(?:sil\w*|kaldır\w*)$", low)
        if m:
            nm = _rname(m.group("name"))
            if routines.delete(nm):
                return f"{nm.capitalize()} rutinini sildim efendim."
            if any(nm in ([k] + b["names"]) for k, b in routines.BUILTIN.items()):
                return "Bu hazır bir rutin, silemem efendim. Aynı adla kendi rutininizi oluşturarak değiştirebilirsiniz."
            return "Böyle bir rutin kayıtlı değil efendim."
    # --- çalıştır
    if re.match(r"^yemek modu\w*(\s+(aç|başlat|göster)\w*)?$", low):      # 'yemek modu' = yemek (malzemeden tarif) modu; zamanlayıcılı 'yemek' rutini artık 'yemek yiyeceğim / yemek zamanı' ile çalışır
        return None
    f = _find_routine(low)
    if f:
        return _run_steps(f[0], f[1], f[2])
    return None


# ---------------------------------------------------------------- komut düzeltici
# Whisper kısık sesli Türkçede küçük hatalar yapabiliyor ("başlar", "telefon mu aç"). Duyulan cümle bilinen bir komuta çok
# benziyorsa o komuta çevrilir. Yalnızca SABİT komutlar (boşluk doldurulan "X çal" gibi olanlar değil).
SNAP_THRESHOLD = 88
_STATIC_COMMANDS = [
    "ışığımı aç", "ışığımı kapat", "sesi artır", "sesi azalt", "sesi kapat", "sesi aç", "sesi biraz artır", "sesi biraz azalt",
    "sesi çok artır", "ses ne kadar", "ses sınırı ne", "saat kaç", "bugün günlerden ne", "bugün ayın kaçı", "sistem durumu",
    "bilgisayarımın durumu nasıl", "yeni whatsapp mesajlarımı oku", "whatsapp mesajlarımı oku", "telefonumu aç", "telefonumu bul",
    "telefondaki fotoğrafları aç", "telefon mesajlarımı aç", "telefon aramalarımı aç", "rutinlerim", "hatırlatmalarım",
    "hatırlatmaları iptal et", "sonraki şarkı", "önceki şarkı", "şarkıyı durdur", "youtube aç", "youtube müzik aç", "google aç",
    "github aç", "spotify aç", "hesap makinesi aç", "not defteri aç", "geçmişi sil", "ekranımda ne var", "neleri hatırlıyorsun",
    "wifi adı ne", "wifi ağımın adı ne", "yeni mesajlarımı oku", "mesajlarımı oku", "kendini kapat", "teşekkürler jarvis",
    "sistemi kapat", "bilgisayarı kapat", "iptal", "telefona bağlan", "hava durumu", "yarın hava nasıl", "ekranı kilitle",
    "kılavuzu aç", "neler yapabilirsin", "pencereyi sola yasla", "pencereyi sağa yasla", "masaüstünü göster", "dolar kaç lira",
    "euro kaç lira", "ders müziğini durdur", "günaydın jarvis", "sabah özeti", "kahraman modu", "illüzyon modu", "ortam modu", "uzay modu", "müzik görselleştirici", "kimya laboratuvarı", "biyoloji laboratuvarı", "fizik laboratuvarı", "matematik laboratuvarı", "astronomi laboratuvarı", "jeoloji laboratuvarı", "gökyüzü haritası", "site modu", "siteleri listele",
]


def _snap_norm(s: str) -> str:
    s = s.replace("İ", "i").replace("I", "ı").lower()
    s = re.sub(r"[^\w\sçğıöşü]", " ", s)
    s = re.sub(r"^(jarvis|hey)\b\s*", "", " ".join(s.split()))
    return " ".join(s.split())


def known_commands() -> list:
    import routines
    out = list(_STATIC_COMMANDS)
    for name, b in routines.BUILTIN.items():
        out += [f"{name} modu", f"{name} modunu başlat"] + list(b["phrases"])
    for name in routines.names():
        out += [f"{name} modu", f"{name} modunu başlat"]
    return sorted(set(_snap_norm(c) for c in out))


def snap(text: str) -> str:
    """Bilinen bir komuta %88+ benziyorsa o komutu döndür, yoksa metni aynen bırak."""
    t = _snap_norm(text)
    if len(t) < 8 or len(t.split()) < 2 and len(t) < 10:
        return text
    cmds = known_commands()
    if t in cmds:
        return text
    from rapidfuzz import fuzz, process
    best = process.extractOne(t, cmds, scorer=fuzz.ratio)
    if best and best[1] >= SNAP_THRESHOLD:
        print(f"DÜZELTME: {t!r} -> {best[0]!r} (benzerlik {best[1]:.0f})", flush=True)
        return best[0]
    return text
