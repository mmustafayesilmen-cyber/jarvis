"""Kahraman modu: iki maske (kırmızı-altın Demir Zırh, ağ desenli Örümcek Maskesi), her birinde 30 özellik. Mod açıkken normal Jarvis dinlemez: konuşulan her cümle yalnızca
buraya gelir (LLM, araçlar, uyandırma kelimesi devre dışı). Eşleşme sabit kalıplarla yapılır; çizim ui/hero.html'de olur."""
import re

# (ad, desen, söylenecek cevap, öncelik)  — numara = listedeki sıra (1..30)
ARMOR = [
    ("Miğferi kapat", r"\b(miğfer|maske|siper|kask|yüz)\w* (kapat|tak|indir|ört)\w*", "Miğfer kapandı efendim.", 0),
    ("Miğferi aç", r"\b(miğfer|maske|siper|kask|yüz)\w* (aç|kaldır|çıkar|yukarı)\w*", "Miğfer açıldı efendim.", 0),
    ("Sistemleri başlat", r"sistem\w* (başlat|çalıştır|aç|devreye|kaldır)\w*|açılış|boot|başlat", "Tüm sistemler çevrimiçi efendim.", 0),
    ("Güç ver", r"\b(gü[cç]|enerji)\w* (ver|artır|yükselt|aktar|tam)\w*|tam gü[cç]|gü[cç] ver", "Güç yüzde yüze çıkıyor efendim.", 0),
    ("Güç düşür", r"\b(gü[cç]|enerji)\w* (düşür|azalt|kıs|kes)\w*|düşük gü[cç]|tasarruf", "Güç düşürüldü efendim.", 0),
    ("Gözler mavi", r"\bmavi\b", "Gözler mavi efendim.", 0),
    ("Gözler kırmızı", r"\bkırmızı\b", "Gözler kırmızı efendim.", 0),
    ("Gözler yeşil", r"\byeşil\b", "Gözler yeşil efendim.", 0),
    ("Gözler turuncu", r"\bturuncu\b", "Gözler turuncu efendim.", 0),
    ("Tarama modu", r"\btara\w*|\bscan\w*", "Çevre taranıyor efendim.", 0),
    ("Hedef kilitle", r"\bhedef\w*|\bkilitle\w*|\bnişan\w*", "Hedef kilitlendi efendim.", 0),
    ("Isı görüşü", r"\bısı\w*|termal|thermal", "Isı görüşü aktif efendim.", 0),
    ("Gece görüşü", r"gece görüş\w*|gece mod\w*|karanlık görüş\w*", "Gece görüşü aktif efendim.", 0),
    ("Röntgen görüşü", r"röntgen|x ?ray|içini göster", "Röntgen görüşü aktif efendim.", 0),
    ("Yakınlaştır", r"yakınlaş\w*|zoom (in|yap)|\bbüyüt\w*|yaklaş\w*", "Yakınlaştırıyorum efendim.", 0),
    ("Uzaklaştır", r"uzaklaş\w*|zoom out|\bküçült\w*", "Uzaklaştırıyorum efendim.", 0),
    ("Uçuş modu", r"\b(uçuş\w*|uç|uçalım|uçmaya\w*|havalan\w*|kalkış\w*|itici\w*)\b", "Uçuş modu aktif, iticiler çalışıyor efendim.", 0),
    ("İniş", r"\b(iniş\w*|yere in\w*|inelim|ineyim|in|konum al|park et)\b", "İniş yapıyorum efendim.", 0),
    ("Hız göstergesi", r"\bhız\w*|\bsürat\w*", "Hız göstergesi açık efendim.", 0),
    ("Silah sistemi", r"\bsilah\w*|savaş mod\w*|\bsavaş\w*", "Silah sistemleri çevrimiçi efendim.", 0),
    ("Ateş", r"\bateş\w*|\bvur\w*|repulsor|\bışın\w*|\blazer\w*", "Ateş ediyorum efendim.", 0),
    ("Kalkan", r"\bkalkan\w*|\bkoruma\w*", "Enerji kalkanı aktif efendim.", 0),
    ("Hasar raporu", r"\bhasar\w*|zarar\w*", "Hasar raporu ekranda efendim.", 1),
    ("Enerji raporu", r"\b(enerji|gü[cç]|pil)\w* (raporu|seviyesi|durumu|ne kadar|kaç)\w*|\bpil\w*|kaç gü[cç]", "Enerji seviyesi ekranda efendim.", 1),
    ("Sistem tanılama", r"tanılama|diagnos\w*|sistem\w* (kontrol|durumu|raporu|testi|tanı)\w*|kontrol et", "Sistem tanılaması yapılıyor efendim.", 1),
    ("Harita", r"\bharita\w*|\bkonum\w*|\bgps\b|navigasyon", "Harita açıldı efendim.", 0),
    ("Düşman tespiti", r"\bdüşman\w*|\btehdit\w*|\bradar\w*|\btespit\w*", "Radar taranıyor, hedefler işaretlendi efendim.", 0),
    ("Acil durum", r"\bacil\w*|\balarm\w*|\btehlike\w*", "Acil durum alarmı verildi efendim.", 0),
    ("Gizli mod", r"\bgizli\w*|\bgizlen\w*|görünmez\w*|stealth|sessiz mod\w*", "Gizli moddayız efendim.", 0),
    ("Gösteri", r"\bgösteri\w*|\bşov\b|\bshow\b|\bparti\w*|\bdans\w*", "Gösteri başlıyor efendim.", 0),
]
WEB = [
    ("Maskeyi tak", r"\b(maske|kukuleta|kapüşon)\w* (tak|giy|ört|kapat)\w*", "Maske takıldı efendim.", 0),
    ("Maskeyi çıkar", r"\b(maske|kukuleta|kapüşon)\w* (çıkar|aç|indir|kaldır)\w*", "Maske çıkarıldı efendim.", 0),
    ("Gözleri kıs", r"göz\w* (kıs|daralt|küçült)\w*|\bkıs\b", "Gözler kısıldı efendim.", 0),
    ("Gözleri aç", r"göz\w* (aç|büyüt|genişlet)\w*|gözler\w* aç", "Gözler açıldı efendim.", 0),
    ("Gözler sarı", r"\bsarı\b", "Gözler sarı efendim.", 0),
    ("Gözler beyaz", r"\bbeyaz\b", "Gözler beyaz efendim.", 0),
    ("Gözler turuncu", r"\bturuncu\b", "Gözler turuncu efendim.", 0),
    ("Gözler mor", r"\bmor\b", "Gözler mor efendim.", 0),
    ("Ağ at", r"\bağ\w* (at|fırlat|püskürt|salla)\w*|ağ at", "Ağ atıldı efendim.", 0),
    ("Ağı sağa fırlat", r"\bağ\w*.*\bsağ\w*|\bsağa\b.*\bağ|\bsağa (at|fırlat)\w*", "Ağ sağa fırlatıldı efendim.", 2),
    ("Ağı sola fırlat", r"\bağ\w*.*\bsol\w*|\bsola\b.*\bağ|\bsola (at|fırlat)\w*", "Ağ sola fırlatıldı efendim.", 2),
    ("Ağ ile sallan", r"\bsallan\w*|salıncak|swing", "Ağla sallanıyoruz efendim.", 0),
    ("Ağ kalkanı", r"\bağ\w* kalkan\w*|\bkalkan\w*", "Ağ kalkanı kuruldu efendim.", 1),
    ("Ağ tuzağı", r"\btuzak\w*|ağ tuzağı|\byakala\w*", "Ağ tuzağı kuruldu efendim.", 1),
    ("Ağ ört", r"\bağ\w* ör\w*|\bağ\w* ört\w*|\bört\w*|\bağla\w*|\bkapla\w*", "Her yer ağla kaplandı efendim.", 0),
    ("Ağı temizle", r"\bağ\w* (temizle|kaldır|sil|yok)\w*|temizle", "Ağlar temizlendi efendim.", 3),
    ("Duvara tırman", r"\btırman\w*|\bduvar\w*", "Duvara tırmanıyoruz efendim.", 0),
    ("Zıpla", r"\bzıpla\w*|\batla\b|\batla\w*|\bsıçra\w*", "Zıplıyoruz efendim.", 0),
    ("Takla at", r"\btakla\w*|ters dön\w*|\bdön\b", "Takla atıyoruz efendim.", 0),
    ("Refleks modu", r"\brefleks\w*|yavaş çekim\w*|\bslow\w*", "Refleks modu, zaman yavaşlıyor efendim.", 0),
    ("Tehlike hissi", r"\btehlike\w*|\bhissi\b|\bsezgi\w*|\buyarı\w*", "Tehlike hissi devrede efendim.", 0),
    ("Gece görüşü", r"gece görüş\w*|gece mod\w*|karanlık görüş\w*", "Gece görüşü aktif efendim.", 0),
    ("Yakınlaştır", r"yakınlaş\w*|zoom (in|yap)|\bbüyüt\w*|yaklaş\w*", "Yakınlaştırıyorum efendim.", 0),
    ("Uzaklaştır", r"uzaklaş\w*|zoom out|\bküçült\w*", "Uzaklaştırıyorum efendim.", 0),
    ("Şehir turu", r"\bşehir\w*|\btur\b|\btur\w* (at|yap)|gökdelen\w*|\bbina\w*", "Şehir turuna çıkıyoruz efendim.", 0),
    ("Kamufle ol", r"\bkamuf\w*|görünmez\w*|\bgizlen\w*|\bsaklan\w*", "Kamuflaj aktif efendim.", 0),
    ("Hız", r"\bhız\w*|\bkoş\w*|\bsürat\w*", "Hızlanıyoruz efendim.", 0),
    ("Güç ver", r"\bgü[cç]\w*|\bkuvvet\w*|\bkas\w*", "Güç artıyor efendim.", 0),
    ("Düşman tespiti", r"\bdüşman\w*|\btehdit\w*|\bradar\w*|\btespit\w*", "Düşmanlar tespit edildi efendim.", 0),
    ("Gösteri", r"\bgösteri\w*|\bşov\b|\bshow\b|\bparti\w*|\bdans\w*", "Gösteri başlıyor efendim.", 0),
]
MASKS = {"armor": {"title": "DEMİR ZIRH", "features": ARMOR}, "web": {"title": "ÖRÜMCEK MASKESİ", "features": WEB}}
ARMOR_ALIAS = r"\b(zırh\w*|iron\w*|ayr[ıi]n\w*|aymen|demir adam\w*|demir maske\w*)\b"
WEB_ALIAS = r"\b(örümcek\w*|spider\w*|spayd\w*|ağ maske\w*|ağ adam\w*|böcek\w*|böcek maske\w*)\b"

_ONES = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9}
_TENS = {"on": 10, "yirmi": 20, "otuz": 30}


def norm(text: str) -> str:
    t = text.replace("İ", "i").replace("I", "ı").lower()
    t = re.sub(r"['’]\w*", "", t)
    t = re.sub(r"[^\w\sçğıöşü]", " ", t)
    t = re.sub(r"\b(jarvis|hey|lütfen|bana|şunu|efendim|hadi|şimdi|bir)\b", " ", t)
    return " ".join(t.split())


def parse_number(t: str):
    """'17', 'on yedi', '17 numara', 'özellik 17', 'yirmi üç numaralı' -> 17. Bulamazsa None. Yalnızca numara belirten cümlelerde."""
    m = re.fullmatch(r"(?:özellik |numara |no )?(\d{1,2})(?: numara\w*| nolu| özellik\w*| numaralı)?(?: olanı| yap| aç| çalıştır| başlat)?", t)
    if m:
        return int(m.group(1))
    words = re.sub(r"\b(numara\w*|nolu|özellik\w*|no|olanı|yap|aç|çalıştır|başlat)\b", " ", t).split()
    if words and all(w in _ONES or w in _TENS for w in words) and len(words) <= 2:
        v = sum(_ONES.get(w, 0) + _TENS.get(w, 0) for w in words)
        return v or None
    return None


def match_feature(mask: str, t: str):
    feats = MASKS[mask]["features"]
    order = sorted(range(len(feats)), key=lambda i: -feats[i][3])
    for i in order:
        name, pat, reply, _ = feats[i]
        if re.search(pat, t):
            return i + 1
    return None


def init_payload(mask: str):
    return {"type": "hero_init", "mask": mask,
            "masks": {k: {"title": v["title"], "features": [f[0] for f in v["features"]]} for k, v in MASKS.items()}}


def handle(text: str, state: dict):
    """-> {'exit':True,'say':..} | {'mask':id,'say':..} (maske değişti) | {'mask':id,'n':k,'say':..} | {'list':True,'say':..} | {'say':..}"""
    t = norm(text)
    if not t:
        return None
    if re.search(r"\b(kahraman\w*|modu\w*|moddan|normal\w*|pencere\w*|ekran\w*)\b.*\b(kapat|kapa|çık|çıkış|bitir|dön|sonlandır)\w*|"
                 r"\b(çık|çıkış|çıkalım|bitti|güle güle|görüşürüz)\b|normale dön", t):
        return {"exit": True, "say": "Kahraman modu kapanıyor efendim, normale dönüyorum."}
    mask = state.get("mask", "armor")
    if re.search(r"\bpiksel\w*|\bpixel\w*|net görüntü|keskin görüntü", t):
        on = not re.search(r"kapat|kapa|net görüntü|keskin|düz|normal", t)
        return {"pixel": on, "say": "Piksel görünümü açıldı efendim." if on else "Net görünüme geçtim efendim."}
    if re.search(ARMOR_ALIAS, t) and re.search(r"maske|geç|seç|göster|aç|yükle|giy|mod|zırh|iron|demir|ayr", t) and not re.search(r"\b(gü[cç]|enerji)\b", t) \
            and not re.search(r"\b(miğfer|siper)\b", t):
        return {"mask": "armor", "say": "Demir zırh hazır efendim, 30 özellik emrinizde.", "switch": True}
    if re.search(WEB_ALIAS, t):
        return {"mask": "web", "say": "Örümcek maskesi hazır efendim, 30 özellik emrinizde.", "switch": True}
    if re.search(r"\b(sıfırla|sıfırlama|her şeyi kapat|hepsini kapat|normale|eski haline|temiz ekran|efektleri kapat)\w*", t):
        return {"mask": mask, "n": 0, "say": "Efektler sıfırlandı efendim."}
    if re.search(r"\b(liste\w*|özellikler\w*|komutlar\w*|neler yapabil\w*|ne yapabil\w*|yardım|menü)\b", t):
        return {"mask": mask, "list": True, "say": f"{'Demir zırh' if mask == 'armor' else 'Örümcek maskesi'} için 30 özellik ekranda efendim. Numarasını ya da adını söyleyin."}
    n = parse_number(t)
    if n is not None:
        if 1 <= n <= 30:
            return {"mask": mask, "n": n, "say": MASKS[mask]["features"][n - 1][2]}
        return {"say": "Özellik numaraları 1 ile 30 arasında efendim."}
    n = match_feature(mask, t)
    if n:
        return {"mask": mask, "n": n, "say": MASKS[mask]["features"][n - 1][2]}
    return {"say": "Bu maskede böyle bir komut yok efendim. Liste deyin, özellikleri göstereyim."}
