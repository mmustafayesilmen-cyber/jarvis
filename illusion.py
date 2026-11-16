"""Görsel illüzyon modu: 50 klasik görsel yanılsama (hepsi bu programda çizilen özgün animasyonlar). Mod açıkken normal Jarvis dinlemez:
konuşulan her cümle yalnızca buraya gelir. Çizimler ui/illusion.html içindedir; numara sırası aynıdır."""
import re

# (ad, açıklama = ne görmelisiniz / nasıl bakmalısınız, arama kalıbı)
ILL = [
    ("Müller-Lyer", "İki çizgi aynı uzunlukta ama ok uçlu olan daha kısa görünür. Ortadaki işaretlere bakıp uzunluklarını karşılaştırın.", r"m[uü]ller|lyer|ok uçlu"),
    ("Ponzo", "İki yatay çizgi aynı boyda ama raylara yakın olan üstteki daha uzun görünür. Beyin perspektifi boyut sanıyor.", r"ponzo|ray"),
    ("Ebbinghaus", "Ortadaki iki turuncu daire aynı boyda. Küçük dairelerle çevrili olan daha büyük görünür.", r"ebbinghaus|titchener|daire boyut"),
    ("Hermann ızgarası", "Beyaz çizgilerin kesişimlerinde sönük gri noktalar görürsünüz. Bakmaya çalıştığınız kesişimde kaybolurlar.", r"hermann|ızgara"),
    ("Kıvılcımlı ızgara", "Kesişimlerde beliren ve yanıp sönen siyah noktalar var ama aslında yok. Gözünüzü gezdirin.", r"kıvılcım|scintil|yanıp sön"),
    ("Kafe duvarı", "Yatay çizgiler birbirine paralel ama eğimli görünür. Kaydırılmış siyah beyaz karolar bunu yapar.", r"kafe|cafe|duvar"),
    ("Zöllner", "Uzun çizgiler birbirine paralel, ama üzerindeki kısa çizgiler yüzünden yamuk görünür.", r"z[oö]llner|zollner"),
    ("Hering", "İki düz yatay çizgi, arkadaki ışınlar yüzünden dışa doğru bükülmüş görünür.", r"hering|ışın"),
    ("Wundt", "İki düz çizgi, arkadaki ışınlar yüzünden ortada içe doğru bükülmüş görünür.", r"wundt"),
    ("Poggendorff", "Eğik çizgi dikdörtgenin iki yanında aynı hizada ama kaymış görünür. Cetvelle kontrol edin.", r"poggendorff|eğik çizgi"),
    ("Kanizsa üçgeni", "Gerçekte olmayan parlak bir üçgen görürsünüz. Beyniniz eksik kenarları tamamlıyor.", r"kanizsa üçgen|hayali üçgen"),
    ("Kanizsa karesi", "Dört parçalı dairenin ortasında parlak bir kare belirir, ama çizilmiş hiçbir kenarı yok.", r"kanizsa kare|hayali kare"),
    ("Necker küpü", "Küpün hangi yüzünün önde olduğu kendiliğinden değişir. Birkaç saniye bakın, derinlik tersine döner.", r"necker|küp"),
    ("Dönen küre", "Sadece noktalardan oluşan küre dönüyor. Hangi yöne döndüğü belirsizdir, beyniniz seçer ve zamanla değişir.", r"dönen küre|küre|nokta küre"),
    ("Spiral sonrası etkisi", "Spirale 20 saniye bakın, sonra durunca sanki ters yönde akıyormuş gibi görünür.", r"spiral sonrası|sonrası etki|hareket sonrası"),
    ("Şelale etkisi", "Aşağı akan çizgilere bakın, durunca sabit görüntü yukarı doğru kayıyormuş gibi görünür.", r"şelale|waterfall"),
    ("Fraser sarmalı", "Spiral gibi görünen şey aslında eşmerkezli dairelerdir. Parmağınızla bir daireyi takip edin.", r"fraser|sarmal"),
    ("Çevresel kayma", "Gözünüz ortada dururken halkaların kenarlarda yavaşça döndüğünü görürsünüz. Hepsi sabit bir resim.", r"çevresel|kayma|dönen halka"),
    ("Leylak kovalayıcı", "Ortadaki artıya bakın. Pembe noktalar tek tek kaybolur, yerine yeşil bir nokta dolaşıyormuş gibi görünür.", r"leylak|kovalay|pembe nokta"),
    ("Troxler solması", "Ortadaki noktaya gözünüzü kırpmadan bakın. Çevredeki bulanık halka birkaç saniyede kaybolur.", r"troxler|solma|bulanık halka"),
    ("Renkli art-görüntü", "Ortadaki noktaya 20 saniye bakın, sonra beyaz ekrana geçilince tamamlayıcı renkleri göreceksiniz.", r"art.?görüntü|afterimage|renkli art"),
    ("Gölge satranç", "A ve B karelerinin rengi tamı tamına aynı. Aradaki gri köprüye bakın, fark kayboluyor.", r"gölge satranç|satranç|checker"),
    ("Eşzamanlı kontrast", "İki iç dikdörtgen aynı gri, ama koyu zeminde olan daha açık görünür.", r"eşzamanlı|kontrast"),
    ("Mach bantları", "Her basamağın kenarında sanki hafif bir aydınlanma ve kararma var, ama her basamak düzgün tek renktir.", r"mach|bant|basamak"),
    ("Cornsweet", "İki yarı aynı gri ama ortadaki gölgeli kenar yüzünden sol taraf daha koyu görünür.", r"cornsweet|corn"),
    ("Bezold yayılması", "Aynı kırmızı çizgiler, beyaz zeminde daha pembe, siyah zeminde daha koyu görünür.", r"bezold|renk yayıl"),
    ("Munker-White", "Aynı gri şeritler, mavi çizgilerin altında koyu, sarı çizgilerin altında açık görünür.", r"munker|white"),
    ("Koffka halkası", "Gri halka bütünken tek renk. Ortasından ikiye ayrılınca iki yarısı farklı tonda görünür.", r"koffka"),
    ("Renk derinliği", "Kırmızı ve mavi bazı gözlere farklı derinlikte görünür: biri öne, biri geriye çıkar.", r"renk derinliği|kromostereo|derinlik"),
    ("Moiré çizgiler", "İki ince çizgi kümesi üst üste gelince dönerken geniş, dalgalı yeni desenler doğar.", r"moir[eé] çizgi|moire çizgi|moir[eé]$"),
    ("Moiré daireler", "Üst üste gelen iki halka deseni, hareketlenince hayali eğriler ve dalgalar oluşturur.", r"moir[eé] daire|halka desen"),
    ("Berber direği", "Çizgiler dönerken yukarı doğru çıkıyormuş gibi görünür, oysa sadece yatay dönüyor.", r"berber|direk"),
    ("Phi hareketi", "İki sabit nokta sırayla yanıp sönünce tek bir nokta hareket ediyormuş gibi görünür.", r"phi|yanıp sönen nokta"),
    ("Çarpışma mı, geçiş mi?", "İki nokta birbirine geliyor. Çarpışıp geri mi dönüyorlar yoksa üst üste geçiyorlar mı? Beyin ikisini de görür.", r"çarpış|geçiş|bounce"),
    ("Genişleyen tünel", "Merkezden çıkan halkalar sizi tünelde ileri gidiyormuş gibi hissettirir.", r"tünel|genişleyen"),
    ("Hipnotik spiral", "Dönen spirale bakınca merkeze çekiliyormuş ya da dışarı itiliyormuş gibi olursunuz.", r"hipnotik|spiral"),
    ("Ouchi", "Ortadaki daire, arkadaki farklı yönlü desenden ayrılıp kendi kendine kayıyor ya da titriyormuş gibi görünür.", r"ouchi"),
    ("Pinna halkaları", "Halkaların içindeki küçük çizgiler dönüyormuş gibi görünür. Yaklaşıp uzaklaşınca yön değişir.", r"pinna|çizgili halka"),
    ("Ay yanılsaması", "Ufka yakın ay daha büyük görünür. İki daire aynı boyda, ama zemin hissi boyutu değiştirir.", r"ay yanılsama|ay "),
    ("Koridor boyutu", "Koridordaki üç figür aynı boyda ama uzaktakiler daha büyük görünür. Derinlik ipuçları boyutu bozuyor.", r"koridor|figür"),
    ("Dikey-yatay", "Aynı uzunluktaki dikey çizgi yataydan daha uzun görünür.", r"dikey.?yatay|t harfi"),
    ("Sander paralelkenarı", "İki köşegen aynı uzunlukta ama soldaki daha uzun görünür.", r"sander|paralelkenar"),
    ("Delboeuf", "İki ortadaki disk aynı boyda. Dar bir halkayla çevrilen daha büyük, geniş halkalı daha küçük görünür.", r"delboeuf"),
    ("Orbison", "Düzgün kare ve daire, arkadaki eşmerkezli çizgilerle bükülmüş görünür.", r"orbison"),
    ("Jastrow", "İki yay şekli aynı boyda, ama alttaki daha büyük görünür.", r"jastrow|yay"),
    ("İmkansız üçgen", "Üç kolun birleştiği bu şekil gerçek hayatta var olamaz. Her köşe ayrı ayrı mantıklı, bütünü imkansız.", r"imkansız|penrose|imkânsız"),
    ("Yüz mü vazo mu?", "Beyaz vazo ya da iki siyah yüz profili görürsünüz. Beyin aynı anda ikisini göremez.", r"vazo|yüz profil|rubin"),
    ("Araba tekerleği", "Hızlanan tekerlek bir an geri dönüyormuş ya da duruyormuş gibi görünür. Kare hızı yanılsaması bunu yapar.", r"tekerlek|wagon"),
    ("Ehrenstein", "Kesik çizgilerin ortasında beliren parlak daire gerçekte yok. Beyniniz boşluğu tamamlar.", r"ehrenstein"),
    ("Kaleydoskop", "Simetrik, sürekli değişen renkli desen. Gözünüz her yerinde bir şey bulur, hipnotik bir etki yapar.", r"kaleydoskop|kaleidoskop|renkli desen"),
]


def titles():
    return [i[0] for i in ILL]


def init_payload():
    return {"type": "ill_init", "items": [{"name": n, "desc": d} for n, d, _ in ILL]}


_ONES = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9}
_TENS = {"on": 10, "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50}


def norm(text: str) -> str:
    t = text.replace("İ", "i").replace("I", "ı").lower()
    t = re.sub(r"['’]\w*", "", t)
    t = re.sub(r"[^\w\sçğıöşü]", " ", t)
    t = re.sub(r"\b(jarvis|hey|lütfen|bana|şunu|efendim|hadi|şimdi|bir)\b", " ", t)
    return " ".join(t.split())


def parse_number(t: str):
    m = re.fullmatch(r"(?:illüzyon |numara |no )?(\d{1,2})(?: numara\w*| nolu| numaralı)?(?: olanı| yap| aç| göster)?", t)
    if m:
        return int(m.group(1))
    words = re.sub(r"\b(numara\w*|nolu|olanı|yap|aç|göster|illüzyon\w*)\b", " ", t).split()
    if words and len(words) <= 3 and all(w in _ONES or w in _TENS for w in words):
        v = sum(_ONES.get(w, 0) + _TENS.get(w, 0) for w in words)
        return v or None
    return None


def handle(text: str, state: dict):
    """-> {'exit':True} | {'n':k,...} | {'nav':'next'|'prev'} | {'auto':bool} | {'list':True} | {'say':...}. state['n'] = geçerli numara."""
    t = norm(text)
    if not t:
        return None
    if re.search(r"\b(illüzyon\w*|mod\w*|pencere\w*|ekran\w*)\b.*\b(kapat|kapa|çık|çıkış|bitir|dön|sonlandır)\w*|\b(çık|çıkış|çıkalım|bitti|güle güle|görüşürüz)\b|normale dön", t):
        return {"exit": True, "say": "İllüzyon modu kapanıyor efendim, normale dönüyorum."}
    cur = state.get("n", 1)
    if re.search(r"\b(sonraki|ileri|diğeri|başka|sıradaki|next)\b", t):
        n = cur % len(ILL) + 1
        return {"n": n, "say": f"{n}. {ILL[n - 1][0]}. {ILL[n - 1][1]}"}
    if re.search(r"\b(önceki|geri|bir önceki|prev)\b", t):
        n = (cur - 2) % len(ILL) + 1
        return {"n": n, "say": f"{n}. {ILL[n - 1][0]}. {ILL[n - 1][1]}"}
    if re.search(r"\b(otomatik|sırayla|gezdir|hepsini göster|slayt|gösteri)\w*", t):
        return {"auto": True, "say": "Otomatik gezintiye başlıyorum efendim. İlk illüzyondan itibaren sırayla göstereceğim. Durdurmak için dur deyin."}
    if re.search(r"\b(dur|durdur|bekle|sabit|otomatiği kapat)\b", t):
        return {"auto": False, "say": "Otomatik gezinti durdu efendim."}
    if re.search(r"\b(liste\w*|hepsi|neler var|hangileri|menü|yardım)\b", t):
        return {"list": True, "say": "50 illüzyon listede efendim. Numarasını ya da adını söyleyin, sonraki ya da önceki diyebilirsiniz."}
    if re.search(r"\b(açıkla|anlat|nedir|ne bu|neden|nasıl oluyor|ne görmeliyim|tekrar)\w*", t):
        return {"n": cur, "say": ILL[cur - 1][1], "same": True}
    n = parse_number(t)
    if n is not None:
        if 1 <= n <= len(ILL):
            return {"n": n, "say": f"{ILL[n - 1][0]}. {ILL[n - 1][1]}"}
        return {"say": "İllüzyon numaraları 1 ile 50 arasında efendim."}
    for i, (name, desc, pat) in enumerate(ILL, 1):          # önce tam ad
        if norm(name) in t:
            return {"n": i, "say": f"{name}. {desc}"}
    for i, (name, desc, pat) in enumerate(ILL, 1):          # sonra anahtar kelime kalıbı
        if re.search(pat, t):
            return {"n": i, "say": f"{name}. {desc}"}
    return {"say": "Bu modda yalnızca illüzyonları gösteriyorum efendim. Bir numara ya da ad söyleyin, ya da liste deyin."}
