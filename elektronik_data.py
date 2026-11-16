"""Elektronik Laboratuvarı: parça kataloğu, çözümleme tabloları (SEM), takma adlar ve hazır devre şablonları. Yalnızca veri.
PARTS: sayfaya giden bilgi (3B modeller bu id'lere göre çizilir). SEM: yalnızca Python tarafının devre çözümlemesi için (sayfaya gitmez).
Pin SIRASI önemlidir: 2 bacaklı kutuplu parçada [0]=artı/anot, [1]=eksi/katot; DIP entegrelerde gerçek numara sırası; kart tipinde `satir`."""

KATS = [("pasif", "Pasif parçalar"), ("yariiletken", "Yarı iletkenler"), ("entegre", "Entegreler"), ("kart", "Mikrodenetleyici kartları"),
        ("sensor", "Sensörler"), ("cikis", "Çıkış / gösterge"), ("guc", "Güç"), ("baglanti", "Bağlantı"), ("haberlesme", "Haberleşme ve sürücü")]


def _e12():
    base = (10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82)
    return [b * d for d in (1, 10, 100, 1000, 10000) for b in base] + [1000000]


def fmt_ohm(v: float) -> str:
    if v >= 1e6:
        return f"{v / 1e6:g}MΩ"
    if v >= 1e3:
        return f"{v / 1e3:g}kΩ"
    return f"{v:g}Ω"


E12 = _e12()
DIRENC_DEG = [fmt_ohm(v) for v in E12]
POT_DEG = ["1kΩ", "5kΩ", "10kΩ", "20kΩ", "50kΩ", "100kΩ", "500kΩ"]
KOND_SER = ["10pF", "22pF", "100pF", "1nF", "10nF", "100nF", "1µF"]
KOND_ELK = ["1µF", "4.7µF", "10µF", "22µF", "47µF", "100µF", "220µF", "470µF", "1000µF", "2200µF"]
LED_RENK = ["kirmizi", "yesil", "mavi", "sari", "beyaz", "turuncu"]
VF = {"kirmizi": 2.0, "yesil": 2.1, "mavi": 3.2, "sari": 2.1, "beyaz": 3.2, "turuncu": 2.0}

_ACIK = {"VCC": "Besleme (+)", "VDD": "Besleme (+)", "GND": "Toprak (-)", "SDA": "I2C veri", "SCL": "I2C saat", "DATA": "Veri", "OUT": "Çıkış",
         "SIG": "Sinyal", "A": "Anot (+)", "K": "Katot (-)", "+": "Artı", "-": "Eksi", "B": "Taban (base)", "C": "Kolektör", "E": "Emiter",
         "G": "Kapı (gate)", "D": "Savak (drain)", "S": "Kaynak (source)", "TRIG": "Tetik", "ECHO": "Yankı", "AO": "Analog çıkış", "DO": "Dijital çıkış",
         "IN": "Giriş", "NO": "Normalde açık", "NC": "Normalde kapalı", "COM": "Ortak", "1": "Uç 1", "2": "Uç 2", "W": "Orta uç (kayar)",
         "MOSI": "SPI veri çıkışı", "MISO": "SPI veri girişi", "SCK": "SPI saat", "CS": "SPI seçim", "TX": "Gönder", "RX": "Al", "EN": "Etkinleştirme",
         "RESET": "Sıfırlama", "VBUS": "USB 5 V", "DIN": "Veri girişi", "CLK": "Saat"}


def _pins(s):
    out = []
    for tok in s.split("|"):
        f = tok.split(":", 2)
        ad = f[0]
        ac = f[2] if len(f) > 2 and f[2] else _ACIK.get(ad.rstrip("0123456789") if ad not in _ACIK else ad, "")
        out.append({"ad": ad, "tip": f[1], "acik": ac})
    return out


PARTS: dict = {}


def P(id, ad, kat, ref, kisa, bilgi, pins, oz, kullanim, dikkat, **ek):
    PARTS[id] = {"ad": ad, "kat": kat, "ref": ref, "kisa": kisa, "bilgi": bilgi, "pinler": _pins(pins), "ozellik": oz, "kullanim": kullanim, "dikkat": dikkat, **ek}


def _rng(prefix, a, b, tip="gc"):
    return "|".join(f"{prefix}{i}:{tip}" for i in range(a, b + 1))


# ============================================================ PASİF
P("direnc", "Direnç", "pasif", "R", "Akımı sınırlar, gerilim böler.",
  "Dirençten geçen akım uçlarındaki gerilimle orantılıdır (Ohm kanunu: V = I × R). Devrede LED'in akımını sınırlamak, giriş pinlerini pull-up/pull-down yapmak ve gerilim bölmek için kullanılır. Kutbu yoktur, iki yöne de takılır.",
  "1:pasif|2:pasif", {"Değer": "10 Ω – 1 MΩ (E12)", "Güç": "1/4 W", "Tolerans": "%5", "Paket": "eksenel"},
  "LED'in önüne seri (220 Ω–1 kΩ); butonda 10 kΩ pull-up/down.", "Direnç gücü 1/4 W'ı aşmamalı: P = I² × R.",
  degerler=DIRENC_DEG, varsayilan="220Ω")
P("potansiyometre", "Potansiyometre", "pasif", "RV", "Döndürerek değişen direnç; gerilim bölücü.",
  "Üç uçlu ayarlı dirençtir: iki uç arasındaki toplam direnç sabit, orta uç (kayar) milin konumuna göre bir uca yaklaşır. Uçlardan birini 5V'a, diğerini GND'ye bağlarsan orta uçtan 0–5 V arası ayarlanabilir gerilim alırsın. Ses, parlaklık ve servo konumu ayarında kullanılır.",
  "1:pasif|W:analog|2:pasif", {"Değer": "10 kΩ (seçilebilir)", "Dönüş": "~270°", "Eğri": "doğrusal"},
  "Uçlar 5V ve GND, orta uç (W) analog pine (A0).", "Orta ucu güç hattına bağlama; uçlardan birini boşta bırakma.", degerler=POT_DEG, varsayilan="10kΩ")
P("trimpot", "Trimpot", "pasif", "RT", "Tornavidayla ayarlanan küçük potansiyometre.",
  "Devre kartına lehimlenip bir kez ayarlanan küçük değişken dirençtir. Eşik gerilimi, kontrast (LCD) ya da hassasiyet ayarında kullanılır. Çalışma prensibi potansiyometreyle aynıdır.",
  "1:pasif|W:analog|2:pasif", {"Değer": "10 kΩ (seçilebilir)", "Dönüş": "~25 tur / 1 tur", "Paket": "3296 / mavi küp"},
  "Sensör modüllerinin eşik ayarı gibi.", "Küçük tornavidayı zorlama; uç dönme sınırında durur.", degerler=POT_DEG, varsayilan="10kΩ")
P("ldr", "LDR (ışık sensörü)", "pasif", "LDR", "Işık arttıkça direnci düşer.",
  "Işığa duyarlı dirençtir: karanlıkta yüzlerce kΩ-MΩ, aydınlıkta birkaç yüz Ω-kΩ olur. Tek başına gerilim vermez; sabit bir direnç ile gerilim bölücü yapıp analog pinle okunur.",
  "1:pasif|2:pasif", {"Karanlık": "~1 MΩ", "Aydınlık": "~1-10 kΩ", "Çap": "5 mm"},
  "Bir ucu 5V, diğer ucu hem A0'a hem 10 kΩ ile GND'ye.", "Sadece LDR'yi pine bağlamak çalışmaz; bölücü gerekir.")
P("termistor", "Termistör (NTC)", "pasif", "TH", "Sıcaklık arttıkça direnci düşer.",
  "NTC termistörün direnci sıcaklık yükseldikçe azalır, bu eğri doğrusal değildir. Gerilim bölücü ile okunur ve Steinhart-Hart denklemiyle sıcaklığa çevrilir. LM35'ten ucuzdur ama hesap gerektirir.",
  "1:pasif|2:pasif", {"Değer (25°C)": "10 kΩ", "Tür": "NTC", "B değeri": "~3950"},
  "5V - termistör - A0 - 10 kΩ - GND bölücüsü.", "Kendi ısınmasını önlemek için ölçüm akımını küçük tut.", degerler=["10kΩ NTC", "100kΩ NTC"], varsayilan="10kΩ NTC")
P("kondansator_seramik", "Seramik kondansatör", "pasif", "C", "Küçük değerli, kutupsuz; filtre ve zamanlama.",
  "Elektrik yükünü depolayan iki plakalı elemandır. Seramik olanlar kutupsuzdur ve yüksek frekansta iyidir; besleme gürültüsünü süzmek (100 nF) ve osilatör devrelerinde kullanılır. DC akımı geçirmez.",
  "1:pasif|2:pasif", {"Değer": "10 pF – 1 µF", "Kutup": "yok", "Gerilim": "50 V"},
  "Entegrenin VCC-GND arasına 100 nF (yakın).", "Değerin yazısını (104 = 100 nF) doğru oku.", degerler=KOND_SER, varsayilan="100nF")
P("kondansator_elektrolitik", "Elektrolitik kondansatör", "pasif", "C", "Büyük kapasiteli, KUTUPLU.",
  "Büyük kapasite (µF) sağlar; besleme dalgalanmasını düzeltmek ve zamanlama için kullanılır. Kutupludur: uzun bacak artıdır, gövdedeki şerit eksi tarafı gösterir. Ters bağlanırsa ısınır ve patlayabilir.",
  "+:pasif:Artı (uzun bacak)|-:pasif:Eksi (şeritli bacak)", {"Değer": "1 µF – 2200 µF", "Kutup": "var", "Gerilim": "16 V"},
  "Regülatör çıkışına 100-470 µF, 555'te zamanlama.", "Kutup ve gerilim değeri: besleme gerilimini aşma.", degerler=KOND_ELK, varsayilan="100µF")
P("bobin", "Bobin (indüktör)", "pasif", "L", "Akım değişimine direnir, enerji depolar.",
  "Sarılı telden oluşur; manyetik alanda enerji depolar. DC'de neredeyse kısa devre gibi davranır, AC'de akımı zorlar. Anahtarlamalı güç kaynaklarında (buck/boost) ve filtrelerde kullanılır.",
  "1:pasif|2:pasif", {"Değer": "10 µH – 10 mH", "Tür": "eksenel"}, "Buck dönüştürücüde diyot ve kondansatörle.", "Doyma akımı aşılırsa değeri çöker.",
  degerler=["10µH", "100µH", "1mH", "10mH"], varsayilan="100µH")
P("kristal", "Kristal osilatör", "pasif", "Y", "Mikrodenetleyiciye kararlı saat verir.",
  "Kuvars kristali belirli bir frekansta titreşir ve mikrodenetleyiciye doğru saat sinyali sağlar. İki uç iki küçük kondansatör (~22 pF) ile GND'ye bağlanır. Arduino Uno'da 16 MHz kristal bulunur.",
  "1:pasif|2:pasif", {"Frekans": "16 MHz", "Yük": "~22 pF", "Kutup": "yok"}, "ATmega328P'nin XTAL1/XTAL2 uçlarına, her uç 22 pF ile GND.", "Kristal ile çip arasını kısa tut.",
  degerler=["32.768kHz", "8MHz", "12MHz", "16MHz", "20MHz"], varsayilan="16MHz")
P("sigorta", "Sigorta", "pasif", "F", "Aşırı akımda erir, devreyi korur.",
  "İnce bir tel aşırı akımda ısınıp eriyerek devreyi açar ve diğer parçaları korur. Pil/adaptör çıkışına seri bağlanır. Eridikten sonra değiştirilmesi gerekir.",
  "1:pasif|2:pasif", {"Akım": "500 mA", "Tür": "cam tüp"}, "Güç kaynağının artı ucuna seri.", "Sigortayı asla tel ile köprüleme.",
  degerler=["100mA", "500mA", "1A", "2A"], varsayilan="500mA")

# ============================================================ YARI İLETKEN
P("diyot", "Diyot (1N4007)", "yariiletken", "D", "Akımı tek yöne geçirir.",
  "Anottan katoda doğru akım geçirir, ters yönde engeller. Ters bağlantıya karşı koruma, röle/motor bobinine paralel (geri tepme) ve doğrultma için kullanılır. Gövdedeki gümüş şerit katot tarafıdır.",
  "A:pasif:Anot (+)|K:pasif:Katot (şerit)", {"Ters gerilim": "1000 V", "Akım": "1 A", "İleri düşüm": "~0,7 V"}, "Röle bobinine ters paralel; pil girişine seri.", "Şerit katotu gösterir; ters takılırsa akım geçmez.")
P("zener", "Zener diyot", "yariiletken", "DZ", "Ters yönde belirli gerilimde iletir; gerilim sabitler.",
  "Ters bağlandığında belirli bir gerilimde (Zener gerilimi) iletime geçip o gerilimi sabit tutar. Seri direnç ile birlikte basit gerilim referansı ve koruma için kullanılır.",
  "A:pasif:Anot (+)|K:pasif:Katot (şerit)", {"Gerilim": "5,1 V (seçilebilir)", "Güç": "0,5 W"}, "Katot artıya, anot GND'ye; önüne direnç.", "Seri direnç olmadan bağlama, aşırı akımla yanar.",
  degerler=["3.3V", "4.7V", "5.1V", "6.2V", "9.1V", "12V"], varsayilan="5.1V")
P("schottky", "Schottky diyot", "yariiletken", "D", "Düşük gerilim düşümlü hızlı diyot.",
  "Normal diyodun ~0,7 V düşümüne karşılık yaklaşık 0,3 V düşer ve çok hızlı anahtarlanır. Düşük gerilimli devrelerde ters kutup koruması ve anahtarlamalı güç kaynaklarında kullanılır (1N5819).",
  "A:pasif:Anot (+)|K:pasif:Katot (şerit)", {"İleri düşüm": "~0,3 V", "Akım": "1 A", "Ters gerilim": "40 V"}, "Pil girişinde kayıp az olsun diye.", "Ters kaçak akımı normal diyottan yüksektir.")
P("kopru_diyot", "Köprü diyot (doğrultucu)", "yariiletken", "BR", "AC'yi DC'ye çevirir (tam dalga).",
  "Dört diyottan oluşur; AC girişin yönü ne olursa olsun çıkışta tek yönlü (DC) gerilim verir. Trafo çıkışını doğrultmak veya DC girişte kutup bağımsızlığı sağlamak için kullanılır.",
  "ACa:pasif:AC giriş|ACb:pasif:AC giriş|DC+:pasif:DC artı|DC-:pasif:DC eksi", {"Akım": "1 A", "Düşüm": "~1,4 V (iki diyot)"}, "AC uçlara trafo, DC+ ve DC- arasına kondansatör.", "DC+/DC- yüzünü yanlış okuma; gövde üzerinde yazar.")
P("led", "LED", "yariiletken", "LED", "Akım geçince ışık veren diyot.",
  "Işık yayan diyottur: uzun bacak anot (+), kısa bacak katot (-). Akım sınırlama yeteneği yoktur; mutlaka seri dirençle kullanılır. Rengine göre ileri gerilimi (Vf) 1,8–3,3 V arasındadır.",
  "A:pasif:Anot (+, uzun bacak)|K:pasif:Katot (-, kısa bacak)", {"Vf": "2,0 V (kırmızı)", "Akım": "10-20 mA", "Paket": "5 mm"}, "Pin - 220 Ω - LED anot, katot GND.", "Dirençsiz bağlarsan LED ya da pin yanar.",
  renkler=LED_RENK)
P("rgb_led", "RGB LED (ortak katot)", "yariiletken", "LED", "Kırmızı, yeşil, mavi tek gövdede.",
  "İçinde üç ayrı LED vardır; ortak katot (K) GND'ye bağlanır, R/G/B bacaklarına PWM verilerek her renk elde edilir. Her renk kolu için ayrı direnç gerekir.",
  "R:pasif:Kırmızı anot|K:pasif:Ortak katot (-)|G:pasif:Yeşil anot|B:pasif:Mavi anot", {"Tür": "ortak katot", "Akım": "20 mA / renk", "Vf": "2,0 / 3,0 / 3,2 V"}, "Her renk: pin - 220 Ω - R/G/B; K = GND.", "Ortak anotlu türde mantık ters çalışır.")
P("ir_led", "IR LED (kızılötesi)", "yariiletken", "LED", "Gözle görünmez kızılötesi ışık yayar.",
  "Uzaktan kumanda ve engel algılama için kullanılır; ışığı kamerada (telefon) mor görünür. Akım sınırlayıcı dirençle bağlanır.",
  "A:pasif:Anot (+)|K:pasif:Katot (-)", {"Dalga boyu": "940 nm", "Vf": "~1,2 V", "Akım": "20-50 mA"}, "Pin - 100 Ω - IR LED, katot GND.", "Gözle görülmez; telefon kamerasıyla yandığını kontrol et.")
P("lazer", "Lazer diyot modülü", "yariiletken", "LS", "Kırmızı nokta lazer modülü (KY-008).",
  "Küçük bir lazer diyodu ve sürücü direnci taşıyan modüldür. Sinyal pini HIGH olunca ışık yayar. Işık gözlere zararlıdır.",
  "S:giris:Sinyal|VCC:guc|GND:gnd", {"Gerilim": "5 V", "Güç": "<5 mW", "Renk": "kırmızı"}, "S bir dijital pine, VCC 5V, GND.", "Lazeri asla göze veya yansıtıcı yüzeye doğrultma.")
P("transistor_npn", "NPN transistör (BC547)", "yariiletken", "Q", "Küçük akımla büyük akımı anahtarlar.",
  "Taban (B) akımı ile kolektör (C) - emiter (E) yolunu açar. Mikrodenetleyici pini taban direnci (1 kΩ) üzerinden sürülür; kolektöre motor/röle/LED şeridi bağlanır. Emiter GND'ye gider. Pinout BC547'ye göre C-B-E'dir; 2N2222'de E-B-C olabilir.",
  "C:pasif:Kolektör|B:giris:Taban (base)|E:pasif:Emiter", {"Akım (Ic)": "100 mA", "Gerilim": "45 V", "Kazanç": "~200"}, "Pin - 1 kΩ - B; C yüke, E GND.", "Tabana dirençsiz bağlama; yük akımı 100 mA'i aşmasın.")
P("transistor_pnp", "PNP transistör (BC557)", "yariiletken", "Q", "Artı hattı anahtarlar (high-side).",
  "NPN'in tersidir: taban GND'ye (düşük) çekilince emiter-kolektör yolu açılır. Yükü besleme artısı tarafından anahtarlamak için kullanılır.",
  "C:pasif:Kolektör|B:giris:Taban (base)|E:pasif:Emiter", {"Akım (Ic)": "100 mA", "Gerilim": "45 V", "Kutup": "PNP"}, "E artıya, C yüke, B direnç ile pin.", "Mantık ters: pin LOW iken açar.")
P("mosfet_n", "N-kanal MOSFET (IRLZ44N)", "yariiletken", "Q", "Gerilimle sürülen güç anahtarı.",
  "Kapı (G) gerilimi ile savak (D) - kaynak (S) yolunu açar; kapıdan neredeyse akım çekmez. Mantık seviyeli (logic-level) türü 5 V ile tam iletime geçer. Motor ve şerit LED sürmek için idealdir.",
  "G:giris:Kapı (gate)|D:pasif:Savak (drain)|S:pasif:Kaynak (source)", {"Akım": "47 A", "Gerilim": "55 V", "Rds(on)": "~25 mΩ"}, "G pin (+10 kΩ GND), D yük, S GND.", "Kapıyı boşta bırakma; 10 kΩ ile GND'ye çek.")
P("regulator_7805", "7805 regülatör", "yariiletken", "U", "Girişi 5 V'a sabitler.",
  "9 V gibi daha yüksek bir girişten sabit 5 V üretir; fazla gerilimi ısı olarak harcar. Giriş ve çıkışa kondansatör bağlanır. Giriş çıkıştan en az ~2 V yüksek olmalıdır.",
  "IN:guc:Giriş (7-35 V)|GND:gnd|OUT:guc:Çıkış 5 V", {"Çıkış": "5 V", "Giriş": "7-35 V", "Akım": "1 A"}, "IN'e 9 V, GND ortak, OUT'a 5 V yük.", "Yüksek girişte ısınır; akım yüksekse soğutucu gerekir.")
P("ams1117", "AMS1117-3.3 regülatör", "yariiletken", "U", "Girişi 3,3 V'a düşürür.",
  "5 V'tan 3,3 V üreten düşük kayıplı regülatördür (LDO). ESP32/ESP8266 ve 3,3 V sensörleri beslemek için kullanılır. Girişe ve çıkışa 10 µF kondansatör önerilir.",
  "GND:gnd|VOUT:guc:Çıkış 3,3 V|VIN:guc:Giriş (4,5-15 V)", {"Çıkış": "3,3 V", "Giriş": "4,5-15 V", "Akım": "800 mA"}, "VIN 5 V, VOUT 3,3 V hattı.", "Pin sırası üreticiye göre değişir; veri sayfasına bak.", m="to220")

# ============================================================ ENTEGRELER
P("ne555", "NE555 zamanlayıcı", "entegre", "U", "Yanıp sönen/zamanlayıcı devreleri kurar.",
  "İçinde iki karşılaştırıcı ve bir flip-flop bulunur. Astable (kararsız) modda sürekli kare dalga üretir (LED flaşörü, buzzer), monostable modda tek darbe verir. Frekansı R1, R2 ve C belirler: f = 1,44 / ((R1 + 2×R2) × C).",
  "GND:gnd|TRIG:giris:Tetik (2)|OUT:cikis:Çıkış (3)|RESET:giris:Sıfırlama (4)|CTRL:giris:Kontrol (5)|THR:giris:Eşik (6)|DIS:cikis:Boşaltma (7)|VCC:guc:Besleme (8)",
  {"Besleme": "4,5-16 V", "Çıkış akımı": "200 mA", "Paket": "DIP-8"}, "Astable: R1 VCC-DIS, R2 DIS-THR, THR-TRIG köprü, C THR-GND; RESET VCC'ye.", "RESET (4) mutlaka VCC'ye bağlanmalı; CTRL'ye 10 nF koy.")
P("lm358", "LM358 işlemsel yükselteç", "entegre", "U", "Çift kanallı op-amp.",
  "İki bağımsız işlemsel yükselteç içerir: karşılaştırıcı, yükselteç ve sensör sinyali kuvvetlendirme için kullanılır. Tek besleme ile çalışır. Kullanılmayan kanalın girişleri boşta bırakılmamalıdır.",
  "OUT1:cikis|IN1-:giris:Eviren (-)|IN1+:giris:Evirmeyen (+)|GND:gnd|IN2+:giris|IN2-:giris|OUT2:cikis|VCC:guc:Besleme (+)", {"Besleme": "3-32 V", "Kanal": "2", "Paket": "DIP-8"},
  "Karşılaştırıcı: IN+ sensör, IN- eşik gerilimi.", "Çıkış 'raya kadar' tam çıkmaz (VCC-1,5 V).", opt=["IN2+", "IN2-", "OUT2"])
P("hc595", "74HC595 kaydırmalı yazmaç", "entegre", "U", "3 pinle 8 çıkış sağlar.",
  "Seri veriyi alıp 8 paralel çıkışa dağıtır; böylece 3 mikrodenetleyici pini ile 8 LED veya bir 7 segment sürülebilir. Birden fazla yazmaç zincirlenebilir.",
  "Q1:cikis|Q2:cikis|Q3:cikis|Q4:cikis|Q5:cikis|Q6:cikis|Q7:cikis|GND:gnd|QH:cikis:Seri çıkış|MR:giris:Sıfırla (LOW=sıfırla)|SH_CP:giris:Kaydırma saati|ST_CP:giris:Mandal saati|OE:giris:Çıkış etkin (LOW)|DS:giris:Seri veri|Q0:cikis|VCC:guc",
  {"Besleme": "2-6 V", "Çıkış": "8 bit", "Paket": "DIP-16"}, "DS, SH_CP, ST_CP mikrodenetleyiciye; MR VCC'ye, OE GND'ye.", "Her LED çıkışına direnç koy; MR ve OE boşta kalmasın.")
P("cd4017", "CD4017 dekad sayıcı", "entegre", "U", "Her saat darbesinde bir sonraki çıkışı açar.",
  "Her saat (CLK) darbesinde 10 çıkıştan sıradakini HIGH yapar; LED kovalamaca ve sıralayıcı devrelerde 555 ile birlikte kullanılır.",
  "Q5:cikis|Q1:cikis|Q0:cikis|Q2:cikis|Q6:cikis|Q7:cikis|Q3:cikis|GND:gnd|Q8:cikis|Q4:cikis|Q9:cikis|CO:cikis:Taşma|CLKINH:giris:Saat engelle|CLK:giris:Saat|RST:giris:Sıfırla|VCC:guc",
  {"Besleme": "3-15 V", "Çıkış": "10", "Paket": "DIP-16"}, "CLK'ya 555 çıkışı; RST ve CLKINH GND'ye.", "CLKINH ve RST boşta kalmasın.", opt=[])
P("l293d", "L293D motor sürücü", "entegre", "U", "İki DC motoru iki yönde sürer (H-köprü).",
  "İçinde iki H-köprü bulunur; her biri bir DC motoru ileri/geri döndürür. Mantık beslemesi (VCC) 5 V, motor beslemesi (VS) ayrıdır. Entegre içi koruma diyotları vardır.",
  "EN12:giris:Etkin 1-2|IN1:giris|OUT1:cikis|GND:gnd|GND2:gnd|OUT2:cikis|IN2:giris|VS:guc:Motor beslemesi|EN34:giris:Etkin 3-4|IN3:giris|OUT3:cikis|GND3:gnd|GND4:gnd|OUT4:cikis|IN4:giris|VCC:guc:Mantık 5 V",
  {"Motor": "4,5-36 V", "Akım": "600 mA / kanal", "Paket": "DIP-16"}, "EN12 5V, IN1/IN2 pinlere, motor OUT1-OUT2 arasına.", "Motor beslemesi ile Arduino toprağını ortak yap.")
P("uln2003", "ULN2003 Darlington dizisi", "entegre", "U", "7 kanallı düşük taraf anahtar.",
  "Küçük mantık sinyali ile 500 mA'e kadar yükü GND tarafından anahtarlayan yedi transistör içerir. Step motor, röle ve LED sürmek için kullanılır. COM ucu bobin geri tepme diyotları için yük beslemesine bağlanır.",
  "1B:giris|2B:giris|3B:giris|4B:giris|5B:giris|6B:giris|7B:giris|GND:gnd|COM:pasif:Ortak (yük artısı)|7C:cikis|6C:cikis|5C:cikis|4C:cikis|3C:cikis|2C:cikis|1C:cikis",
  {"Akım": "500 mA / kanal", "Gerilim": "50 V", "Paket": "DIP-16"}, "Girişler (B) pinlere, yük bir uç C çıkışına, diğer uç artıya.", "Çıkış LOW'a çeker (sink); yükün artısı dışarıdan gelir.", opt=["1B", "2B", "3B", "4B", "5B", "6B", "7B", "COM"])
P("pc817", "PC817 optokuplör", "entegre", "U", "İki devreyi ışıkla birbirinden yalıtır.",
  "İçinde bir LED ve bir foto transistör vardır; giriş tarafındaki LED yanınca çıkış transistörü iletir. Devreleri elektriksel olarak yalıtmak için (ör. şebeke tarafı) kullanılır. Giriş LED'i için seri direnç gerekir.",
  "A:pasif:Anot (1)|K:pasif:Katot (2)|E:pasif:Emiter (3)|C:pasif:Kolektör (4)", {"Giriş akımı": "5-20 mA", "Yalıtım": "5000 V", "Paket": "DIP-4"}, "A - 330 Ω - pin, K GND; C/E çıkış tarafı.", "Giriş LED'i dirençsiz bağlanmaz.")
P("attiny85", "ATtiny85", "entegre", "U", "8 bacaklı küçük AVR mikrodenetleyici.",
  "Arduino benzeri ama çok küçük (5 giriş/çıkış pini) mikrodenetleyicidir. Arduino ISP ile programlanır; dahili 8 MHz osilatörü vardır. Küçük projelerde kullanılır.",
  "PB5:giris:RESET / PB5|PB3:gc|PB4:gc|GND:gnd|PB0:gc:SDA|PB1:gc|PB2:gc:SCL|VCC:guc", {"Bellek": "8 KB", "Pin": "6 GPIO", "Besleme": "2,7-5,5 V"}, "VCC 5V, GND; LED PB0'a direnç ile.", "Programlamak için ISP programlayıcı gerekir.", opt=["PB5"])
P("atmega328p", "ATmega328P (DIP-28)", "entegre", "U", "Arduino Uno'nun beyni.",
  "Arduino Uno'da kullanılan AVR mikrodenetleyicisidir. Breadboard'a takılıp 16 MHz kristal ve iki 22 pF kondansatörle kendi başına çalışabilir; bootloader yazılmış olmalıdır.",
  "RESET:giris:PC6 / RESET|PD0:gc|PD1:gc|PD2:gc|PD3:gc|PD4:gc|VCC:guc|GND:gnd|XTAL1:pasif|XTAL2:pasif|PD5:gc|PD6:gc|PD7:gc|PB0:gc|PB1:gc|PB2:gc|PB3:gc|PB4:gc|PB5:gc|AVCC:guc|AREF:pasif|GND2:gnd|PC0:analog|PC1:analog|PC2:analog|PC3:analog|PC4:analog:SDA|PC5:analog:SCL",
  {"Flash": "32 KB", "Saat": "16 MHz", "Besleme": "1,8-5,5 V"}, "VCC+AVCC 5V, 2 GND, RESET 10 kΩ ile 5V.", "AVCC bağlanmazsa analog okuma çalışmaz.", opt=["XTAL1", "XTAL2", "AREF"])

# ============================================================ KARTLAR
P("arduino_uno", "Arduino Uno", "kart", "U", "En yaygın öğrenme kartı (ATmega328P, 5 V).",
  "14 dijital (6'sı PWM) ve 6 analog pini olan, USB ile programlanan 5 V mantıklı karttır. 5V ve 3V3 pinlerinden küçük sensörleri besleyebilirsin. Pin başına en çok 20 mA önerilir.",
  _rng("D", 0, 13) + "|GND3:gnd|RESET:giris:Sıfırlama|3V3:guc:3,3 V çıkış|5V:guc:5 V|GND:gnd|GND2:gnd|VIN:guc:Harici giriş (7-12 V)|" + _rng("A", 0, 5, "analog"),
  {"Mantık": "5 V", "Pin akımı": "20 mA (maks 40)", "Flash": "32 KB", "Saat": "16 MHz"}, "USB ile besle, 5V/GND hatlarını breadboard'a taşı.", "D0/D1 USB seriyle paylaşılır; yüklerken bağlı bırakma.", satir=[15, 12])
P("arduino_nano", "Arduino Nano", "kart", "U", "Uno'nun küçük breadboard dostu sürümü.",
  "Uno ile aynı ATmega328P'yi taşır ama çok küçüktür ve breadboard'a doğrudan takılır. A6 ve A7 yalnızca analog giriştir. Mini-USB ile programlanır.",
  "D1:gc:TX|D0:gc:RX|RST:giris:Sıfırlama|GND:gnd|D2:gc|D3:gc:PWM|D4:gc|D5:gc:PWM|D6:gc:PWM|D7:gc|D8:gc|D9:gc:PWM|D10:gc:PWM|D11:gc:PWM|D12:gc|VIN:guc:Harici giriş (7-12 V)|GND2:gnd|RST2:giris|5V:guc:5 V|A7:analog|A6:analog|A5:analog:SCL|A4:analog:SDA|A3:analog|A2:analog|A1:analog|A0:analog|AREF:pasif|3V3:guc:3,3 V|D13:gc:Dahili LED",
  {"Mantık": "5 V", "Pin akımı": "20 mA (maks 40)", "Flash": "32 KB"}, "Breadboard orta çizgisine tak; 5V/GND hatlarını besle.", "VIN en az 7 V ister; USB ile 5V'tan çalışır.", satir=[15, 15], opt=["RST2", "AREF"])
P("arduino_mega", "Arduino Mega 2560", "kart", "U", "Çok pinli büyük kart (ATmega2560).",
  "54 dijital ve 16 analog pini olan büyük karttır; çok sensör ve çıkış gereken projelerde seçilir. Burada sık kullanılan bir pin alt kümesi gösterilir. I2C pinleri D20 (SDA) ve D21 (SCL)'dir.",
  _rng("D", 0, 21) + "|5V:guc:5 V|3V3:guc:3,3 V|VIN:guc:Harici giriş (7-12 V)|GND:gnd|GND2:gnd|RESET:giris:Sıfırlama|" + _rng("A", 0, 9, "analog"),
  {"Mantık": "5 V", "Pin akımı": "20 mA (maks 40)", "Flash": "256 KB"}, "Çok servo / ekran / sensör projeleri.", "Uno kütüphanelerinin çoğu çalışır ama I2C pinleri farklıdır.", satir=[22, 16])
P("esp32", "ESP32 DevKit", "kart", "U", "Wi-Fi ve Bluetooth'lu, 3,3 V mantıklı güçlü kart.",
  "Çift çekirdekli, yerleşik Wi-Fi ve Bluetooth'u olan karttır. Tüm pinler 3,3 V mantıkla çalışır ve 5 V'a dayanmaz. G34-G39 yalnızca girişir. I2C varsayılanı SDA=G21, SCL=G22'dir.",
  "EN:giris:Etkinleştir|G36:analog:Yalnızca giriş (VP)|G39:analog:Yalnızca giriş (VN)|G34:analog:Yalnızca giriş|G35:analog:Yalnızca giriş|G32:analog|G33:analog|G25:gc|G26:gc|G27:gc|G14:gc|G12:gc|G13:gc|GND:gnd|VIN:guc:5 V giriş|"
  "G23:gc:MOSI|G22:gc:SCL|G1:gc:TX0 (USB)|G3:gc:RX0 (USB)|G21:gc:SDA|G19:gc:MISO|G18:gc:SCK|G5:gc|G17:gc:TX2|G16:gc:RX2|G4:gc|G2:gc:Dahili LED|G15:gc|GND2:gnd|3V3:guc:3,3 V",
  {"Mantık": "3,3 V", "Pin akımı": "12 mA önerilen", "Saat": "240 MHz", "Kablosuz": "Wi-Fi + BT"}, "USB ile besle; sensörlere 3V3 hattı ver.", "5 V'luk bir çıkışı doğrudan GPIO'ya bağlama (HC-SR04 ECHO için bölücü).", satir=[15, 15])
P("nodemcu", "NodeMCU (ESP8266)", "kart", "U", "Ucuz Wi-Fi'li 3,3 V kart.",
  "ESP8266 çipli Wi-Fi kartıdır; tek analog girişi (A0, 0-1 V aralığı kartta bölücüyle 3,3 V) vardır. Pinler 3,3 V mantıkla çalışır. D4 dahili LED'dir.",
  "A0:analog:Tek analog giriş|D0:gc|D5:gc:SCK|D6:gc:MISO|D7:gc:MOSI|D8:gc|RX:gc|TX:gc|GND:gnd|3V3:guc:3,3 V|VIN:guc:5 V giriş|GND2:gnd|RST:giris|EN:giris|3V3b:guc:3,3 V|D4:gc:Dahili LED|D3:gc|D2:gc:SDA|D1:gc:SCL",
  {"Mantık": "3,3 V", "Pin akımı": "12 mA", "Saat": "80 MHz", "Kablosuz": "Wi-Fi"}, "IoT: sıcaklık verisini web'e gönder.", "Boot sırasında D3/D4/D8 seviyelerine dikkat; 5 V verme.", satir=[10, 9], opt=["RST", "EN", "3V3b"])
P("raspberry_pico", "Raspberry Pi Pico", "kart", "U", "RP2040'lı 3,3 V kart; MicroPython/C.",
  "Çift çekirdekli RP2040 çipli karttır. USB sürücü gibi görünür, MicroPython veya Arduino-Pico ile programlanır. ADC pinleri GP26-GP28'dir; tüm pinler 3,3 V'dur.",
  "GP0:gc|GP1:gc|GND:gnd|GP2:gc|GP3:gc|GP4:gc:SDA|GP5:gc:SCL|GND2:gnd|GP6:gc|GP7:gc|GP8:gc|GP9:gc|GND3:gnd|GP10:gc|GP11:gc|GP12:gc|GP13:gc|GND4:gnd|GP14:gc|GP15:gc|"
  "VBUS:guc:USB 5 V|VSYS:guc:Sistem besleme|GND5:gnd|3V3_EN:giris|3V3:guc:3,3 V çıkış|ADC_VREF:pasif|GP28:analog|GND6:gnd|GP27:analog|GP26:analog|RUN:giris|GP22:gc|GND7:gnd|GP21:gc|GP20:gc|GP19:gc|GP18:gc|GND8:gnd|GP17:gc|GP16:gc",
  {"Mantık": "3,3 V", "Pin akımı": "12 mA", "Saat": "133 MHz", "Flash": "2 MB"}, "USB ile besle; 3V3 hattından sensörleri çalıştır.", "Pinler 5 V'a dayanmaz.", satir=[20, 20], opt=["3V3_EN", "ADC_VREF", "RUN", "VSYS", "VBUS"])

# ============================================================ SENSÖRLER
P("dht11", "DHT11 sıcaklık-nem", "sensor", "S", "Sıcaklık ve nemi tek telle verir.",
  "Dijital sensördür: sıcaklık (0-50 °C) ve nemi (%20-80) tek veri hattıyla gönderir. Modülünde pull-up direnci hazırdır. Saniyede en fazla 1 kez okunur.",
  "DATA:veri:Veri|VCC:guc|GND:gnd", {"Besleme": "3,3-5 V", "Sıcaklık": "0-50 °C (±2)", "Nem": "%20-80 (±5)"}, "DATA bir dijital pine; DHT kütüphanesi.", "Saniyede 1 kereden sık okuma.")
P("dht22", "DHT22 sıcaklık-nem", "sensor", "S", "DHT11'in daha hassas türü.",
  "DHT11'e göre geniş aralık ve daha doğru ölçüm (-40..80 °C, %0-100 nem) sağlar. Okuma 2 sn'de bir yapılabilir.",
  "DATA:veri:Veri|VCC:guc|GND:gnd", {"Besleme": "3,3-6 V", "Sıcaklık": "-40..80 °C (±0,5)", "Nem": "%0-100 (±2)"}, "DHT kütüphanesinde DHT22 türünü seç.", "2 sn'den sık okuma.")
P("hcsr04", "HC-SR04 ultrasonik mesafe", "sensor", "S", "Ses dalgasıyla mesafe ölçer.",
  "TRIG pinine 10 µs darbe verilince ultrasonik ses yollar; yankının dönüş süresi ECHO'dan okunur. Mesafe = süre × 0,0343 / 2 (cm). 5 V ile çalışır; ECHO 5 V çıkar.",
  "VCC:guc|TRIG:giris:Tetik|ECHO:cikis:Yankı|GND:gnd", {"Besleme": "5 V", "Aralık": "2-400 cm", "Açı": "15°"}, "TRIG ve ECHO dijital pinlere.", "ECHO 5 V verir; 3,3 V kartta (ESP32) bölücü kullan.")
P("pir", "PIR hareket sensörü (HC-SR501)", "sensor", "S", "İnsan hareketini algılar.",
  "Kızılötesi ısı değişimini algılar; hareket olunca OUT pini HIGH olur. Üzerindeki iki trimpot ile hassasiyet ve bekleme süresi ayarlanır. Açılışta ~30-60 sn ısınır.",
  "VCC:guc|OUT:cikis:Hareket çıkışı|GND:gnd", {"Besleme": "5-20 V", "Aralık": "3-7 m", "Çıkış": "3,3 V HIGH"}, "OUT bir dijital pine, digitalRead.", "İlk dakika yanlış alarm verebilir.")
P("lm35", "LM35 sıcaklık sensörü", "sensor", "S", "Sıcaklığı 10 mV/°C gerilimle verir.",
  "Çıkış gerilimi sıcaklıkla doğrusal artar: 10 mV / °C. Analog pinle okunup Vref'e göre °C'ye çevrilir: °C = analogRead × (5,0 / 1023) × 100.",
  "VCC:guc:+Vs|OUT:analog:Çıkış|GND:gnd", {"Besleme": "4-30 V", "Hassasiyet": "10 mV/°C", "Aralık": "2-150 °C"}, "OUT analog pine (A0).", "Düz yüzü sana bakarken soldan: VCC, OUT, GND.")
P("ds18b20", "DS18B20 sıcaklık sensörü", "sensor", "S", "Tek telli dijital sıcaklık sensörü.",
  "Su geçirmez sondalı türü de yaygındır. 1-Wire ile çalışır: DQ ucu ile VDD arasına 4,7 kΩ pull-up direnç gerekir. Tek hatta birden çok sensör bağlanabilir.",
  "GND:gnd|DQ:veri:Veri (1-Wire)|VDD:guc", {"Besleme": "3-5,5 V", "Aralık": "-55..125 °C", "Hassasiyet": "±0,5 °C"}, "DQ dijital pine; DQ-VDD arasına 4,7 kΩ.", "Pull-up direnci yoksa sensör bulunamaz.")
P("mpu6050", "MPU6050 ivme + jiroskop", "sensor", "S", "3 eksen ivme ve 3 eksen dönüş ölçer (I2C).",
  "Hareket ve eğim ölçmek için kullanılır; I2C ile veri verir. Denge robotu ve dron gibi projelerde temel parçadır. Adres 0x68'dir (AD0 HIGH ise 0x69).",
  "VCC:guc|GND:gnd|SCL:veri|SDA:veri|XDA:veri:Yardımcı veri|XCL:veri:Yardımcı saat|AD0:giris:Adres seçimi|INT:cikis:Kesme", {"Besleme": "3,3-5 V (modül)", "Arayüz": "I2C", "Adres": "0x68"}, "SDA/SCL'yi kartın I2C pinlerine bağla.", "Gerilimi modül regülatörüne göre ver; kütüphane gerekir.", opt=["XDA", "XCL", "AD0", "INT"])
P("bmp280", "BMP280 basınç sensörü", "sensor", "S", "Basınç ve sıcaklık ölçer (3,3 V).",
  "Hava basıncını ve sıcaklığı ölçer; basınçtan yükseklik de hesaplanır. 3,3 V ile çalışır, I2C veya SPI'dır. Adres 0x76 veya 0x77.",
  "VCC:guc:3,3 V|GND:gnd|SCL:veri|SDA:veri|CSB:giris:SPI seçim|SDO:giris:Adres", {"Besleme": "1,8-3,6 V", "Basınç": "300-1100 hPa", "Arayüz": "I2C/SPI"}, "3V3'e bağla, SDA/SCL'yi I2C pinlerine.", "5 V verme (çoğu modül 3,3 V).", opt=["CSB", "SDO"])
P("toprak_nem", "Toprak nem sensörü", "sensor", "S", "Toprağın ne kadar ıslak olduğunu ölçer.",
  "Kapasitif türü toprak nemine göre analog gerilim verir: kuru = yüksek değer, ıslak = düşük değer. Bitki sulama otomasyonunda kullanılır. Direnç tipleri zamanla paslanır, kapasitif olanı seç.",
  "AO:analog:Analog çıkış|VCC:guc|GND:gnd", {"Besleme": "3,3-5,5 V", "Çıkış": "analog", "Tür": "kapasitif"}, "AO'yu A0'a; eşik için analogRead.", "Elektronik kısmı toprağa gömme, yalnızca probu batır.")
P("mq2", "MQ-2 gaz sensörü", "sensor", "S", "Duman, LPG ve metan algılar.",
  "Isıtıcılı gaz sensörüdür; gaz yoğunluğuna göre analog (AO) ve eşiği geçince dijital (DO) çıkış verir. Isınma süresi ~20 sn, ısıtıcı yüzünden ~150 mA çeker.",
  "VCC:guc|GND:gnd|DO:cikis:Dijital çıkış|AO:analog:Analog çıkış", {"Besleme": "5 V", "Akım": "~150 mA", "Isınma": "~20 sn"}, "AO analog pine; eşik trimpot ile.", "Isınır; kapalı kutuya koyma.", opt=["DO", "AO"])
P("mikrofon", "Mikrofon / ses sensörü (KY-038)", "sensor", "S", "Ses şiddetini algılar.",
  "Elektret mikrofonlu modüldür; ses yüksek olduğunda DO pini HIGH olur, AO ise ses seviyesini analog verir. Eşik trimpotla ayarlanır. Alkış sensörü yapılabilir.",
  "AO:analog|GND:gnd|VCC:guc|DO:cikis", {"Besleme": "3,3-5 V", "Çıkış": "analog + dijital"}, "DO'yu dijital pine alkışla aç/kapa.", "Kelimeleri tanımaz, yalnızca şiddeti ölçer.", opt=["AO", "DO"])
P("ir_alici", "IR alıcı (VS1838)", "sensor", "S", "Uzaktan kumanda sinyalini alır.",
  "38 kHz kızılötesi kumanda sinyallerini alıp demodüle eder. IRremote kütüphanesi ile tuş kodları okunur.",
  "OUT:cikis|GND:gnd|VCC:guc", {"Besleme": "2,7-5,5 V", "Frekans": "38 kHz", "Mesafe": "~10 m"}, "OUT dijital pine.", "Pin sırası modele göre değişir.")
P("hall", "Hall sensörü (A3144)", "sensor", "S", "Mıknatıs yakınlığını algılar.",
  "Manyetik alan algılayınca çıkışı LOW olur (açık-kolektör). Devir sayma, kapı sensörü gibi işlerde kullanılır. Çıkışa 10 kΩ pull-up gerekir (veya INPUT_PULLUP).",
  "VCC:guc|GND:gnd|OUT:cikis", {"Besleme": "4,5-24 V", "Çıkış": "açık kolektör", "Tür": "kilitlemeli"}, "OUT pine, INPUT_PULLUP.", "Mıknatısın kutbuna duyarlıdır.")
P("ir_engel", "IR engel sensörü", "sensor", "S", "Önündeki engeli algılar.",
  "Kızılötesi verici ve alıcı taşır; engel yakınsa OUT LOW olur. Robot araçlarda engel/çizgi algılama için kullanılır. Menzil trimpotla ayarlanır.",
  "VCC:guc|GND:gnd|OUT:cikis", {"Besleme": "3,3-5 V", "Mesafe": "2-30 cm", "Çıkış": "dijital"}, "OUT dijital pine.", "Parlak güneş ışığında yanlış okuyabilir.")
P("joystick", "Joystick modülü", "sensor", "S", "İki eksen analog + buton.",
  "İki potansiyometre (X, Y) ve basılabilir bir buton içerir. Orta konumda ~512 okunur. Oyun kolu ve robot kontrolünde kullanılır.",
  "GND:gnd|VCC:guc|VRX:analog:X ekseni|VRY:analog:Y ekseni|SW:cikis:Buton (LOW)", {"Besleme": "3,3-5 V", "Eksen": "2 analog", "Buton": "1"}, "VRX/VRY analog pinlere, SW dijital pine + INPUT_PULLUP.", "Orta noktada küçük sapma olur; ölü bölge koy.")
P("enkoder", "Döner enkoder (KY-040)", "sensor", "S", "Sonsuz dönen düğme + buton.",
  "Döndürüldüğünde CLK ve DT pinlerinde kaydırılmış darbeler üretir; hangisinin önce değiştiğine bakılarak yön bulunur. Basınca SW LOW olur. Menü ve ses seviyesi ayarında kullanılır.",
  "GND:gnd|VCC:guc|SW:cikis:Buton|DT:cikis:Veri|CLK:cikis:Saat", {"Besleme": "3,3-5 V", "Darbe": "20 / tur", "Buton": "var"}, "CLK, DT ve SW'yi dijital pinlere.", "Gürültü için yazılımda debounce gerekir.")
P("rfid", "RFID okuyucu (RC522)", "sensor", "S", "13,56 MHz kart/etiket okur.",
  "Yakındaki RFID kartın/anahtarlığın kimlik numarasını (UID) okur. SPI ile haberleşir ve YALNIZCA 3,3 V ile beslenir. Kapı kilidi ve yoklama sistemleri yapılır.",
  "SDA:giris:SS (SPI seçim)|SCK:giris|MOSI:giris|MISO:cikis|IRQ:cikis|GND:gnd|RST:giris|3V3:guc:3,3 V", {"Besleme": "3,3 V", "Frekans": "13,56 MHz", "Arayüz": "SPI"}, "3V3'e bağla; SPI pinleri kartta sabit.", "5 V verirsen yanar; sinyaller de 3,3 V.", opt=["IRQ"])
P("rtc", "RTC modülü (DS3231)", "sensor", "S", "Elektrik kesilse de saati tutar.",
  "Pil yedekli gerçek zaman saatidir: tarih ve saati I2C ile verir, yılda saniyeler kadar sapar. Alarm ve veri kaydı projelerinde kullanılır.",
  "SQW:cikis:Kare dalga|SCL:veri|SDA:veri|VCC:guc|GND:gnd", {"Besleme": "2,3-5,5 V", "Arayüz": "I2C", "Adres": "0x68"}, "SDA/SCL'yi I2C pinlerine.", "Şarj edilemeyen CR2032 türü için şarj direncini kaldır.", opt=["SQW"])
P("tus_takimi", "4x4 tuş takımı", "sensor", "K", "16 tuşlu matris keypad.",
  "Satır ve sütunlarda 8 pin ile 16 tuşu okur: sütunlar sırayla LOW yapılır, satırlar okunur. Keypad kütüphanesi hazır işi yapar.",
  "R1:pasif|R2:pasif|R3:pasif|R4:pasif|C1:pasif|C2:pasif|C3:pasif|C4:pasif", {"Tuş": "16", "Pin": "8", "Tür": "matris"}, "Her pin ayrı dijital pine.", "8 pini de bağlamak gerekir.", satir=[4, 4])

# ============================================================ ÇIKIŞ
P("buzzer", "Buzzer (pasif)", "cikis", "BZ", "Frekansa göre ses çıkarır.",
  "Pasif buzzer, verilen frekansta titreşip ses çıkarır; tone() ile farklı notalar çalınabilir. Aktif buzzer ise dahili osilatörlüdür, yalnızca besleme verince öter. Bu parça pasif türdür.",
  "+:pasif:Artı (uzun bacak)|-:pasif:Eksi", {"Tür": "pasif piezo", "Gerilim": "3-5 V", "Akım": "~30 mA"}, "Pin - buzzer(+), buzzer(-) GND; tone(pin, 1000).", "Akım küçük pinleri zorlamaz ama sürekli DC verme.")
P("hoparlor", "Hoparlör (8 Ω)", "cikis", "SP", "Ses çıkışı; yükselteç ister.",
  "8 Ω empedanslı küçük hoparlördür. Doğrudan pinle sürülürse akım çok yüksek olur (5 V / 8 Ω = 625 mA); bu yüzden transistör ya da ses yükseltici (LM386) ve seri direnç / kondansatör gerekir.",
  "+:pasif|-:pasif", {"Empedans": "8 Ω", "Güç": "0,5 W", "Çap": "40 mm"}, "Pin - 100 Ω - kondansatör - hoparlör.", "Pine doğrudan bağlama: pin yanar.")
P("yedi_segment", "7 segment gösterge (ortak katot)", "cikis", "DS", "Tek haneli rakam gösterir.",
  "Sekiz LED (A-G + nokta) bir kasada toplanmıştır. Ortak katot türünde COM pini GND'ye bağlanır, yakılacak parçalar HIGH yapılır. Her segmentin ayrı direnci gerekir (220 Ω).",
  "E:pasif|D:pasif|COM:pasif:Ortak katot|C:pasif|DP:pasif:Nokta|B:pasif|A:pasif|COM2:pasif:Ortak katot|F:pasif|G:pasif", {"Tür": "ortak katot", "Akım": "10 mA / segment", "Hane": "1"}, "Segmentler direnç üzerinden pinlere veya 74HC595'e.", "Direnci unutma; COM ikisinden biri GND'de olmalı.", satir=[5, 5], opt=["DP", "COM2"])
P("lcd1602", "LCD 16x2 (I2C)", "cikis", "LCD", "16 karakter x 2 satır yazı ekranı.",
  "Arkasında I2C sırtlığı olduğu için yalnızca 4 kabloyla (GND, VCC, SDA, SCL) bağlanır. Adres genelde 0x27'dir. Kontrast arkadaki trimpotla ayarlanır.",
  "GND:gnd|VCC:guc|SDA:veri|SCL:veri", {"Besleme": "5 V", "Arayüz": "I2C", "Adres": "0x27 / 0x3F"}, "SDA/SCL'yi I2C pinlerine; LiquidCrystal_I2C.", "Yazı görünmezse kontrast trimpotunu çevir.")
P("oled", "OLED 0,96\" (SSD1306, I2C)", "cikis", "OLED", "128x64 piksel küçük ekran.",
  "Kendi ışığını üreten küçük ekran: yazı, grafik ve bitmap gösterir. I2C ile bağlanır; adres 0x3C'dir. 3,3-5 V ile çalışır.",
  "GND:gnd|VCC:guc|SCL:veri|SDA:veri", {"Çözünürlük": "128x64", "Arayüz": "I2C", "Adres": "0x3C"}, "Adafruit_SSD1306 veya U8g2.", "Aynı yazıyı uzun süre bırakma (yanma).")
P("neopixel", "NeoPixel (WS2812B şerit)", "cikis", "NP", "Tek pinle yönetilen renkli LED şerit.",
  "Her LED içinde sürücü çipi vardır; tek veri hattıyla yüzlerce LED ayrı ayrı renklendirilir. Her LED tam beyazda ~60 mA çeker; şerit için ayrı 5 V besleme kullan. Veri hattına 330 Ω direnç önerilir.",
  "GND:gnd|DIN:giris:Veri girişi|VCC:guc", {"Besleme": "5 V", "Akım": "60 mA / LED", "Veri": "800 kHz"}, "DIN dijital pine (330 Ω), VCC 5V, GND ortak.", "Birkaç LED'den fazlasını Arduino 5V'una bağlama.")
P("led_matris", "8x8 LED matris (MAX7219)", "cikis", "M", "64 LED'i 3 pinle sürer.",
  "MAX7219 sürücülü modül; DIN, CS ve CLK ile 8x8 LED'e şekil ve kayan yazı gösterilir. Modüller zincirlenebilir.",
  "VCC:guc|GND:gnd|DIN:giris|CS:giris|CLK:giris", {"Besleme": "5 V", "Boyut": "8x8", "Arayüz": "SPI benzeri"}, "LedControl kütüphanesi.", "Parlaklığı düşük tut; akım çeker.")
P("servo", "Servo motor (SG90)", "cikis", "SV", "Belirli açıya dönen motor (0-180°).",
  "PWM sinyalinin darbe genişliği (1-2 ms) ile açısı belirlenen küçük motordur. Robot kolu, kapı mandalı ve radar tarayıcı gibi işlerde kullanılır. Sinyal pini herhangi bir dijital pin olabilir.",
  "GND:gnd:Kahverengi|VCC:guc:Kırmızı|SIG:giris:Turuncu (sinyal)", {"Besleme": "4,8-6 V", "Tork": "1,8 kg·cm", "Açı": "0-180°"}, "SIG pine, Servo kütüphanesi.", "Hareket ederken akım çeker: büyük servoda harici 5 V kullan.")
P("dc_motor", "DC motor", "cikis", "M", "Verilen gerilimle sürekli döner.",
  "Fırçalı küçük DC motor; gerilim arttıkça hızlanır, kutup değişince ters döner. Pine doğrudan bağlanmaz, transistör, MOSFET ya da L298N/L293D sürücü gerekir. Ters EMK için paralel diyot koy.",
  "+:pasif:Artı|-:pasif:Eksi", {"Gerilim": "3-6 V", "Akım": "100-250 mA", "Hız": "~10000 rpm"}, "Transistör/MOSFET veya sürücü ile.", "Mikrodenetleyici pinine doğrudan bağlama.")
P("step_motor", "Step motor (28BYJ-48 + ULN2003)", "cikis", "M", "Adım adım hassas döner.",
  "Her adımda belirli bir açı dönen motor; ULN2003 sürücü kartıyla birlikte gelir. IN1-IN4 dört dijital pine bağlanır, Stepper kütüphanesi ile döndürülür. Yaklaşık 2048 adım = 1 tur.",
  "IN1:giris|IN2:giris|IN3:giris|IN4:giris|VCC:guc:5 V|GND:gnd", {"Besleme": "5 V", "Adım": "2048 / tur", "Akım": "~240 mA"}, "IN1-IN4 pinlere; sıra Stepper(…, IN1, IN3, IN2, IN4).", "Güç kartın 5V'undan değil harici 5 V'tan verilmeli.")
P("titresim_motoru", "Titreşim motoru", "cikis", "M", "Telefon gibi titreşim verir.",
  "Eksantrik ağırlıklı küçük motordur; çalışınca titrer. Akımı pin sınırının üstünde olduğu için transistörle sürülür; ters EMK diyodu koy.",
  "+:pasif|-:pasif", {"Gerilim": "3 V", "Akım": "~80 mA"}, "Transistör + diyot ile.", "Pine doğrudan bağlama.")
P("role", "Röle modülü (1 kanal)", "cikis", "K", "Küçük sinyalle büyük yükü açar/kapar.",
  "Mekanik anahtardır: IN pini sürülünce COM ile NO uçları birleşir. Üzerinde sürücü transistörü ve opto/koruma bulunur. Pompa, lamba gibi yükleri anahtarlar. Çoğu modül LOW ile tetiklenir (aktif-düşük).",
  "VCC:guc|GND:gnd|IN:giris:Tetik|NO:pasif:Normalde açık|COM:pasif:Ortak|NC:pasif:Normalde kapalı", {"Bobin": "5 V", "Kontak": "10 A / 250 V AC", "Tetik": "genelde LOW"}, "IN bir pine; yük COM-NO arasına.", "Şebeke gerilimi öldürücüdür; yalnızca düşük gerilim dene.", opt=["NC"])

# ============================================================ GÜÇ
P("pil_9v", "9 V pil", "guc", "BT", "Küçük devreler için 9 V.",
  "9 V kare pil, düşük akımlı devreleri (555, Arduino VIN) besler. Kapasitesi düşüktür (~500 mAh); motor gibi güçlü yükleri çok kısa süre taşır.",
  "+:guc:Artı|-:gnd:Eksi", {"Gerilim": "9 V", "Kapasite": "~500 mAh", "Tür": "alkalin"}, "Arduino VIN'e veya regülatöre.", "Ters bağlama; kısa devre yapma.")
P("pil_aa", "AA pil yuvası", "guc", "BT", "1,5 V pillerin seri yuvası.",
  "AA piller seri bağlanınca gerilimler toplanır (4 pil = 6 V). Kapasitesi 9 V pile göre yüksektir; servo ve motor için uygundur.",
  "+:guc:Artı|-:gnd:Eksi", {"Gerilim": "1,5 V × pil sayısı", "Kapasite": "~2000 mAh", "Tür": "alkalin"}, "Servo ve motor gibi güç isteyen yükler için.", "Yeni ve eski pili karıştırma.",
  degerler=["1.5V (1 pil)", "3V (2 pil)", "4.5V (3 pil)", "6V (4 pil)"], varsayilan="6V (4 pil)")
P("dugme_pil", "Düğme pil (CR2032)", "guc", "BT", "3 V küçük pil.",
  "Saat modülü, küçük LED ve düşük akımlı devreler için 3 V verir. Birkaç mA'in üstünde çekilmemelidir.",
  "+:guc|-:gnd", {"Gerilim": "3 V", "Kapasite": "225 mAh", "Akım": "<10 mA"}, "RTC yedek, LED yanıp söner.", "Şarj edilmez; akımı düşük tut.")
P("lipo", "LiPo pil (3,7 V)", "guc", "BT", "Şarj edilebilir lityum polimer.",
  "Dolu iken 4,2 V, boşken ~3,0 V'tur; yüksek akım verebilir. TP4056 ile güvenle şarj edilir. 3,0 V altına boşaltma, delme ve kısa devre yapma.",
  "+:guc|-:gnd", {"Gerilim": "3,7 V (4,2 V dolu)", "Kapasite": "1000 mAh", "Tür": "Li-Po"}, "TP4056 şarj modülü ile birlikte kullan.", "Koruma devresiz kullanma; yangın riski.")
P("dc_jak", "DC jak (5,5 mm)", "guc", "J", "Adaptör girişi.",
  "Adaptör fişinin takıldığı dişi jaktır. Dıştaki halka genelde eksi, orta pim artıdır (merkez pozitif).",
  "+:guc:Orta pim (+)|-:gnd:Gövde (-)", {"Gerilim": "5-12 V", "Akım": "2 A", "Çap": "5,5 / 2,1 mm"}, "Adaptörle devreyi besle.", "Adaptör gerilimi ve polaritesini kontrol et.", degerler=["5V", "9V", "12V"], varsayilan="9V")
P("usb_c", "USB-C besleme modülü", "guc", "J", "5 V USB besleme girişi.",
  "USB-C bağlantısından 5 V verir; CC dirençleri modül üzerindedir. Devreyi bilgisayardan ya da şarj adaptöründen beslemek için kullanılır.",
  "VBUS:guc:5 V|GND:gnd|CC1:pasif|CC2:pasif", {"Gerilim": "5 V", "Akım": "1-3 A"}, "5 V hattını besle.", "CC dirençleri olmayan modülle 5 V gelmeyebilir.", opt=["CC1", "CC2"])
P("lm2596", "LM2596 buck modülü", "guc", "U", "Gerilim düşürücü (ayarlanabilir).",
  "Daha yüksek gerilimi verimli şekilde ayarlanabilir düşük gerilime çevirir (7805'ten az ısınır). Çıkış gerilimi modüldeki trimpotla ayarlanır; çıkışı çok yüksek bırakmadan önce ölç.",
  "IN+:guc:Giriş +|IN-:gnd:Giriş -|OUT+:guc:Çıkış +|OUT-:gnd:Çıkış -", {"Giriş": "4,5-40 V", "Çıkış": "1,25-35 V", "Akım": "3 A"}, "12 V adaptör - modül - 5 V hat.", "Bağlamadan önce çıkış gerilimini multimetre ile ayarla.",
  degerler=["3.3V", "5V", "6V", "9V", "12V"], varsayilan="5V")
P("tp4056", "TP4056 LiPo şarj modülü", "guc", "U", "Li-ion/LiPo pili USB'den şarj eder.",
  "Tek hücreli pilleri 4,2 V'a kadar güvenle şarj eden modüldür. Koruma devreli türde pil uçları B+/B-, yük uçları OUT+/OUT-'dır.",
  "IN+:guc:USB giriş +|IN-:gnd:USB giriş -|B+:pasif:Pil +|B-:pasif:Pil -|OUT+:pasif:Yük +|OUT-:gnd:Yük -", {"Giriş": "5 V", "Şarj akımı": "1 A", "Bitiş": "4,2 V"}, "Pil B+/B-, yük OUT+/OUT-.", "Pil kutbunu ters bağlama.", opt=["IN+", "IN-"])
P("gunes_paneli", "Güneş paneli (6 V)", "guc", "BT", "Işıktan elektrik üretir.",
  "Küçük panel ışık şiddetine göre 6 V'a kadar gerilim ve birkaç yüz mA akım üretir. Pil şarjı için diyot ve şarj modülüyle kullanılır.",
  "+:guc|-:gnd", {"Gerilim": "6 V", "Akım": "~200 mA", "Güç": "1,2 W"}, "Diyot + TP4056 ile pili şarj et.", "Karanlıkta pil panele akım verebilir: diyot koy.")

# ============================================================ BAĞLANTI
P("buton", "Buton (push)", "baglanti", "SW", "Basınca iki ucu birleştirir.",
  "Basıldığında iki ucunu bağlayan anlık anahtardır. Mikrodenetleyici girişi için bir ucu pine, diğer ucu GND'ye bağla ve INPUT_PULLUP kullan: basılınca pin LOW okunur.",
  "1:pasif|2:pasif", {"Tür": "anlık (NO)", "Akım": "50 mA", "Paket": "6 mm"}, "Pin - buton - GND, pinMode(INPUT_PULLUP).", "Pull-up/down olmadan giriş boşta kalır (rastgele okuma).")
P("anahtar", "Kaydırmalı anahtar", "baglanti", "SW", "Aç/kapa anahtarı (kalıcı).",
  "Konumunu koruyan anahtardır: açıkken yolu bağlar, kapalıyken keser. Güç hattına seri bağlanıp devrenin ana şalteri olur.",
  "1:pasif|2:pasif", {"Tür": "SPST", "Akım": "0,5 A"}, "Pilin artısına seri.", "Akım değerini aşma.")
P("dip_switch", "DIP anahtar (4'lü)", "baglanti", "SW", "4 küçük anahtar bir arada.",
  "Dört bağımsız küçük anahtardır; adres seçimi ve ayar bitleri için kullanılır. Her anahtarın iki ucu vardır.",
  "S1A:pasif|S1B:pasif|S2A:pasif|S2B:pasif|S3A:pasif|S3B:pasif|S4A:pasif|S4B:pasif", {"Anahtar": "4", "Akım": "25 mA"}, "Her anahtar bir giriş pinini GND'ye çeker.", "Çok akım geçirmez.", satir=[4, 4], opt=["S1A", "S1B", "S2A", "S2B", "S3A", "S3B", "S4A", "S4B"])
P("pin_header", "Erkek pin header (8'li)", "baglanti", "J", "Kart bağlantı noktaları.",
  "Kart üzerine lehimlenen erkek konektör sırasıdır; kablo ya da modül takmak için kullanılır. Her pin bağımsızdır.",
  _rng("", 1, 8, "pasif"), {"Pin": "8", "Aralık": "2,54 mm"}, "Dış devreleri karta takmak için.", "Kısa pinli tarafı karta lehimle; kablo yönünü karıştırma.", opt=[str(i) for i in range(1, 9)])
P("disi_header", "Dişi header (8'li)", "baglanti", "J", "Modül takılan dişi soket.",
  "Modülün (sensör, ESP) çıkarılabilir takılması için kullanılan dişi soket sırasıdır.",
  _rng("", 1, 8, "pasif"), {"Pin": "8", "Aralık": "2,54 mm"}, "Modülleri lehimsiz değiştirmek için.", "Modül pin sırasının soketle aynı yönde olduğundan emin ol.", opt=[str(i) for i in range(1, 9)])
P("klemens", "Klemens (2'li)", "baglanti", "J", "Vidalı kablo bağlantısı.",
  "Kabloyu vidayla sıkıp devreye bağlamak için kullanılır; adaptör ve motor kabloları için idealdir.",
  "1:pasif|2:pasif", {"Pin": "2", "Akım": "10 A"}, "Dış güç ve motor kabloları.", "Vidayı gevşek bırakma.", opt=["1", "2"])

# ============================================================ HABERLEŞME / SÜRÜCÜ
P("hc05", "HC-05 Bluetooth", "haberlesme", "BT", "Seri Bluetooth modülü.",
  "Telefon ile mikrodenetleyici arasında kablosuz seri haberleşme sağlar. 3,6-6 V ile beslenir ama RX pini 3,3 V mantıktır: 5 V'luk TX'i bölücü ile düşür.",
  "STATE:cikis|RX:giris:3,3 V mantık|TX:cikis|GND:gnd|VCC:guc|EN:giris", {"Besleme": "3,6-6 V", "Hız": "9600 baud", "Menzil": "10 m"}, "TX→kartın RX'i, RX→bölücü ile kartın TX'i.", "RX'e 5 V verme (1k + 2k bölücü).", opt=["STATE", "EN"])
P("nrf24", "nRF24L01 radyo", "haberlesme", "RF", "2,4 GHz kablosuz haberleşme.",
  "İki kart arasında düşük güçlü, hızlı telsiz bağlantı sağlar. Besleme 3,3 V'tur (5 V yakar); modülün besleme hattına 10 µF kondansatör koy.",
  "GND:gnd|VCC:guc:3,3 V|CE:giris|CSN:giris|SCK:giris|MOSI:giris|MISO:cikis|IRQ:cikis", {"Besleme": "1,9-3,6 V", "Menzil": "~100 m", "Arayüz": "SPI"}, "3V3'e bağla; RF24 kütüphanesi.", "5 V verirsen yanar.", opt=["IRQ"])
P("esp01", "ESP-01 (ESP8266)", "haberlesme", "U", "Küçük Wi-Fi modülü.",
  "Seri komutlarla Wi-Fi bağlantısı sağlar. 3,3 V ile çalışır ve ~200 mA çeker; bu yüzden Arduino 3,3 V pinine takma, ayrı regülatör kullan. CH_PD yüksek olmalıdır.",
  "GND:gnd|GPIO2:gc|GPIO0:gc|RX:giris|VCC:guc:3,3 V|RST:giris|CH_PD:giris:Etkinleştir|TX:cikis", {"Besleme": "3,0-3,6 V", "Akım": "~200 mA", "Hız": "115200"}, "AT komutları ile Wi-Fi.", "5 V'a dayanmaz; CH_PD'yi 3,3 V'a bağla.", opt=["GPIO2", "GPIO0", "RST"])
P("lora", "LoRa modülü (SX1278)", "haberlesme", "RF", "Kilometrelerce menzilli radyo.",
  "Düşük veri hızlı ama çok uzun menzilli radyo modülüdür. 3,3 V ile çalışır ve SPI ile bağlanır; anten bağlamadan çalıştırma.",
  "GND:gnd|3V3:guc:3,3 V|RESET:giris|DIO0:cikis|NSS:giris|MOSI:giris|MISO:cikis|SCK:giris", {"Besleme": "1,8-3,7 V", "Menzil": "~2 km", "Frekans": "433 MHz"}, "SPI pinleri ve DIO0 kesmesi.", "Antensiz çalıştırma: modül yanar.", opt=["DIO0", "RESET"])
P("sd_kart", "SD kart modülü", "haberlesme", "U", "Veri kaydı için SD kart okuyucu.",
  "SPI ile SD karta veri yazar/okur; sıcaklık kaydı (data logger) için kullanılır. Bu modül 3,3 V içindir; seviye dönüştürücülü modüller 5 V alır.",
  "3V3:guc:3,3 V|CS:giris|MOSI:giris|SCK:giris|MISO:cikis|GND:gnd", {"Besleme": "3,3 V", "Arayüz": "SPI", "Kart": "microSD"}, "SD kütüphanesi; CS bir dijital pin.", "5 V mantık sinyalini doğrudan bağlama.")
P("l298n", "L298N motor sürücü modülü", "haberlesme", "U", "İki DC motoru iki yönde sürer.",
  "Üzerinde 12 V girişi, 5 V regülatör ve iki H-köprü bulunur. IN1/IN2 yönü, ENA PWM ile hızı belirler. Motor gerilimi (6-35 V) ve mantık toprağı ortak olmalıdır.",
  "OUT1:cikis|OUT2:cikis|12V:guc:Motor beslemesi|GND:gnd|5V:guc:5 V (regülatör)|OUT3:cikis|OUT4:cikis|ENA:giris|IN1:giris|IN2:giris|IN3:giris|IN4:giris|ENB:giris",
  {"Motor": "6-35 V", "Akım": "2 A / kanal", "Mantık": "5 V"}, "IN pinlere, motorlar OUT'a, GND'ler ortak.", "Düşüm yüksek (~2 V); GND'leri birleştirmeyi unutma.", satir=[7, 6], opt=["ENA", "ENB", "5V", "OUT3", "OUT4", "IN3", "IN4"])
P("a4988", "A4988 step sürücü", "haberlesme", "U", "Step motoru STEP/DIR ile sürer.",
  "Her STEP darbesinde motoru bir adım (veya mikro-adım) döndürür, DIR yönü belirler. Akım sınırı trimpotla ayarlanır. VMOT'a 100 µF kondansatör koy.",
  "VMOT:guc:Motor beslemesi|GND:gnd|2B:cikis|2A:cikis|1A:cikis|1B:cikis|VDD:guc:Mantık 5 V|GND2:gnd|DIR:giris|STEP:giris|SLEEP:giris|RESET:giris|MS3:giris|MS2:giris|MS1:giris|EN:giris",
  {"Motor": "8-35 V", "Akım": "2 A", "Adım": "1/16'ya kadar"}, "STEP/DIR pinlere, motor 1A-1B-2A-2B'ye.", "Beslemeyi bağlı iken motor takma; sürücü yanar.", satir=[8, 8], opt=["SLEEP", "RESET", "MS1", "MS2", "MS3", "EN"])
P("tm1637", "TM1637 4 haneli gösterge", "haberlesme", "DS", "4 haneli saat/sayaç ekranı (2 pin).",
  "TM1637 sürücülü 4 haneli 7 segment gösterge; yalnızca CLK ve DIO ile sürülür. Saat, sayaç ve sıcaklık göstermek için idealdir.",
  "CLK:giris|DIO:giris:Veri|VCC:guc|GND:gnd", {"Besleme": "3,3-5 V", "Hane": "4", "Arayüz": "2 tel"}, "TM1637Display kütüphanesi.", "Yalnızca iki pin gerektirir.", m="modul")
P("seviye_donusturucu", "Seviye dönüştürücü (2 kanal)", "haberlesme", "U", "3,3 V ile 5 V sinyali çevirir.",
  "İki farklı gerilimli devrenin (ör. 5 V Arduino ve 3,3 V ESP32) birbirini yakmadan konuşmasını sağlar. LV tarafı 3,3 V, HV tarafı 5 V alır.",
  "LV:guc:Alçak taraf|LV1:pasif|LV2:pasif|GND:gnd|HV1:pasif|HV2:pasif|HV:guc:Yüksek taraf", {"LV": "3,3 V", "HV": "5 V", "Kanal": "2"}, "Her iki tarafın GND'sini ortak yap.", "Her iki besleme ucu da bağlı olmalı.", m="modul")

# ============================================================ ÇÖZÜMLEME TABLOSU (sayfaya gitmez)
# src: {pin: V | ("dep", V, girişPini, enAzGiriş) | ("deger",) | ("depd", girişPini, fark)}   vcc/bidi: {pin: (en az, en çok)}
# y: [(a, b, tür[, çarpan])] tür: r direnç, k kısa, d diyot(a→b)   l: [(tür, a, b)] yükler (tür led|buzzer|motor|hoparlor|lazer)
# c: [(a, b, kontrolPini, koşul)] koşul hi|gnd|lo|led   d: [(çıkışPini, kontrolPini|None)] sürücü çıkışları   ctl: kontrol pinleri
SEM: dict = {
    "direnc": {"y": [("1", "2", "r")]},
    "potansiyometre": {"y": [("1", "W", "r", 0.5), ("W", "2", "r", 0.5)]},
    "trimpot": {"y": [("1", "W", "r", 0.5), ("W", "2", "r", 0.5)]},
    "ldr": {"y": [("1", "2", "r")], "rdef": 10000},
    "termistor": {"y": [("1", "2", "r")], "rdef": 10000},
    "kondansator_elektrolitik": {"pol": ("+", "-")},
    "bobin": {"y": [("1", "2", "k")]},
    "sigorta": {"y": [("1", "2", "k")]},
    "diyot": {"y": [("A", "K", "d")], "pol": ("A", "K")},
    "zener": {"y": [("A", "K", "d")], "pol": ("A", "K")},
    "schottky": {"y": [("A", "K", "d")], "pol": ("A", "K")},
    "kopru_diyot": {"y": [("ACa", "DC+", "d"), ("ACb", "DC+", "d"), ("DC-", "ACa", "d"), ("DC-", "ACb", "d")]},
    "led": {"l": [("led", "A", "K")]},
    "rgb_led": {"l": [("led", "R", "K"), ("led", "G", "K"), ("led", "B", "K")], "vf": {"R": 2.0, "G": 3.0, "B": 3.2}},
    "ir_led": {"l": [("led", "A", "K")], "vf1": 1.2},
    "lazer": {"vcc": {"VCC": (3.0, 5.5)}, "ctl": ["S"]},
    "transistor_npn": {"c": [("C", "E", "B", "hi")]},
    "transistor_pnp": {"c": [("E", "C", "B", "gnd")]},
    "mosfet_n": {"c": [("D", "S", "G", "hi")]},
    "regulator_7805": {"src": {"OUT": ("dep", 5.0, "IN", 7.0)}, "vcc": {"IN": (7.0, 35.0)}},
    "ams1117": {"src": {"VOUT": ("dep", 3.3, "VIN", 4.5)}, "vcc": {"VIN": (4.5, 15.0)}},
    "ne555": {"vcc": {"VCC": (4.5, 16.0)}, "d": [("OUT", None)]},
    "lm358": {"vcc": {"VCC": (3.0, 32.0)}},
    "hc595": {"vcc": {"VCC": (2.0, 6.0)}, "d": [(f"Q{i}", None) for i in range(8)]},
    "cd4017": {"vcc": {"VCC": (3.0, 15.0)}, "d": [(f"Q{i}", "CLK") for i in range(10)]},
    "l293d": {"vcc": {"VCC": (4.5, 7.0), "VS": (4.5, 36.0)}, "d": [("OUT1", "IN1"), ("OUT2", "IN2"), ("OUT3", "IN3"), ("OUT4", "IN4")]},
    "uln2003": {"c": [(f"{k}C", "GND", f"{k}B", "hi") for k in range(1, 8)]},
    "pc817": {"l": [("led", "A", "K")], "c": [("C", "E", "A", "led")], "vf1": 1.2},
    "attiny85": {"vcc": {"VCC": (2.7, 5.5)}, "mcu": {"v": 5.0, "imax": (20, 40), "i2c": ("PB0", "PB2"), "kind": "avr", "usb": False}},
    "atmega328p": {"vcc": {"VCC": (1.8, 5.5), "AVCC": (1.8, 5.5)}, "mcu": {"v": 5.0, "imax": (20, 40), "i2c": ("PC4", "PC5"), "kind": "avr", "usb": False}},
    "arduino_uno": {"src": {"5V": 5.0, "3V3": 3.3}, "bidi": {"VIN": (7.0, 12.0)}, "mcu": {"v": 5.0, "imax": (20, 40), "i2c": ("A4", "A5"), "kind": "avr", "usb": True,
                    "pwm": ["D3", "D5", "D6", "D9", "D10", "D11"], "adc": [f"A{i}" for i in range(6)]}},
    "arduino_nano": {"src": {"5V": 5.0, "3V3": 3.3}, "bidi": {"VIN": (7.0, 12.0)}, "mcu": {"v": 5.0, "imax": (20, 40), "i2c": ("A4", "A5"), "kind": "avr", "usb": True,
                     "pwm": ["D3", "D5", "D6", "D9", "D10", "D11"], "adc": [f"A{i}" for i in range(8)], "inonly": ["A6", "A7"]}},
    "arduino_mega": {"src": {"5V": 5.0, "3V3": 3.3}, "bidi": {"VIN": (7.0, 12.0)}, "mcu": {"v": 5.0, "imax": (20, 40), "i2c": ("D20", "D21"), "kind": "avr", "usb": True,
                     "pwm": [f"D{i}" for i in range(2, 14)], "adc": [f"A{i}" for i in range(10)]}},
    "esp32": {"src": {"3V3": 3.3}, "alt": {"VIN": 5.0}, "bidi": {"VIN": (4.5, 12.0)}, "mcu": {"v": 3.3, "imax": (12, 40), "i2c": ("G21", "G22"), "kind": "esp32", "usb": True,
                "adc": ["G36", "G39", "G34", "G35", "G32", "G33"], "inonly": ["G34", "G35", "G36", "G39"]}},
    "nodemcu": {"src": {"3V3": 3.3, "3V3b": 3.3}, "alt": {"VIN": 5.0}, "bidi": {"VIN": (4.5, 12.0)}, "mcu": {"v": 3.3, "imax": (12, 12), "i2c": ("D2", "D1"), "kind": "esp8266", "usb": True, "adc": ["A0"]}},
    "raspberry_pico": {"src": {"3V3": 3.3, "VBUS": 5.0}, "bidi": {"VSYS": (1.8, 5.5)}, "mcu": {"v": 3.3, "imax": (12, 16), "i2c": ("GP4", "GP5"), "kind": "pico", "usb": True, "adc": ["GP26", "GP27", "GP28"]}},
    "dht11": {"vcc": {"VCC": (3.0, 5.5)}}, "dht22": {"vcc": {"VCC": (3.3, 6.0)}},
    "hcsr04": {"vcc": {"VCC": (4.5, 5.5)}, "l5": ["ECHO"]},
    "pir": {"vcc": {"VCC": (4.5, 20.0)}, "o33": ["OUT"]},
    "lm35": {"vcc": {"VCC": (4.0, 30.0)}},
    "ds18b20": {"vcc": {"VDD": (3.0, 5.5)}, "pullup": ("DQ", "VDD")},
    "mpu6050": {"vcc": {"VCC": (3.0, 5.5)}}, "bmp280": {"vcc": {"VCC": (1.7, 3.6)}},
    "toprak_nem": {"vcc": {"VCC": (3.3, 5.5)}}, "mq2": {"vcc": {"VCC": (4.5, 5.5)}}, "mikrofon": {"vcc": {"VCC": (3.0, 5.5)}},
    "ir_alici": {"vcc": {"VCC": (2.7, 5.5)}}, "hall": {"vcc": {"VCC": (4.5, 24.0)}}, "ir_engel": {"vcc": {"VCC": (3.0, 5.5)}},
    "joystick": {"vcc": {"VCC": (3.0, 5.5)}}, "enkoder": {"vcc": {"VCC": (3.0, 5.5)}},
    "rfid": {"vcc": {"3V3": (2.5, 3.6)}}, "rtc": {"vcc": {"VCC": (2.3, 5.5)}},
    "buzzer": {"l": [("buzzer", "+", "-")]},
    "hoparlor": {"l": [("hoparlor", "+", "-")]},
    "yedi_segment": {"l": [("led", s, "COM") for s in ("A", "B", "C", "D", "E", "F", "G", "DP")], "y": [("COM", "COM2", "k")]},
    "lcd1602": {"vcc": {"VCC": (4.5, 5.5)}}, "oled": {"vcc": {"VCC": (3.0, 5.5)}},
    "neopixel": {"vcc": {"VCC": (3.5, 5.5)}, "ctl": ["DIN"]}, "led_matris": {"vcc": {"VCC": (4.0, 5.5)}, "ctl": ["DIN"]},
    "servo": {"vcc": {"VCC": (4.5, 6.0)}, "ctl": ["SIG"]},
    "dc_motor": {"l": [("motor", "+", "-")]}, "titresim_motoru": {"l": [("motor", "+", "-")]},
    "step_motor": {"vcc": {"VCC": (4.5, 12.0)}, "ctl": ["IN1", "IN2", "IN3", "IN4"]},
    "role": {"vcc": {"VCC": (4.5, 5.5)}, "ctl": ["IN"], "c": [("COM", "NO", "IN", "hi"), ("COM", "NC", "IN", "lo")]},
    "pil_9v": {"src": {"+": 9.0}}, "pil_aa": {"src": {"+": ("deger",)}}, "dugme_pil": {"src": {"+": 3.0}}, "lipo": {"src": {"+": 3.7}},
    "dc_jak": {"src": {"+": ("deger",)}}, "usb_c": {"src": {"VBUS": 5.0}}, "gunes_paneli": {"src": {"+": 6.0}},
    "lm2596": {"src": {"OUT+": ("depd", "IN+", 1.5)}, "vcc": {"IN+": (4.5, 40.0)}, "y": [("IN-", "OUT-", "k")]},
    "tp4056": {"vcc": {"IN+": (4.0, 8.0)}, "y": [("B+", "OUT+", "k"), ("B-", "OUT-", "k")]},
    "buton": {"y": [("1", "2", "k")]}, "anahtar": {"y": [("1", "2", "k")]},
    "dip_switch": {"y": [(f"S{i}A", f"S{i}B", "k") for i in range(1, 5)]},
    "hc05": {"vcc": {"VCC": (3.6, 6.0)}, "l33": ["RX"]},
    "nrf24": {"vcc": {"VCC": (1.9, 3.6)}},
    "esp01": {"vcc": {"VCC": (3.0, 3.6)}, "l33": ["RX", "GPIO0", "GPIO2", "RST", "CH_PD"]},
    "lora": {"vcc": {"3V3": (1.8, 3.7)}}, "sd_kart": {"vcc": {"3V3": (3.0, 3.6)}, "l33": ["CS", "MOSI", "SCK"]},
    "l298n": {"vcc": {"12V": (6.0, 35.0)}, "bidi": {"5V": (4.5, 5.5)}, "d": [("OUT1", "IN1"), ("OUT2", "IN2"), ("OUT3", "IN3"), ("OUT4", "IN4")]},
    "a4988": {"vcc": {"VMOT": (8.0, 35.0), "VDD": (3.0, 5.5)}, "d": [("1A", "STEP"), ("1B", "STEP"), ("2A", "STEP"), ("2B", "STEP")]},
    "tm1637": {"vcc": {"VCC": (3.0, 5.5)}},
    "seviye_donusturucu": {"vcc": {"LV": (1.8, 3.6), "HV": (3.0, 5.5)}},
}
# başlıkta/klemenste eksik bağlantı uyarısı verilmeyen parçalar
SKIP_FLOAT = {"pin_header", "disi_header", "klemens", "dip_switch"}

# ============================================================ TAKMA ADLAR (sesli/yazılı komutta parça adı)
ALIAS = {
    "direnc": ["direnç", "resistor", "rezistans"], "potansiyometre": ["potansiyometre", "pot", "potansiyometr"], "trimpot": ["trimpot", "trimer", "ayarlı direnç"],
    "ldr": ["ldr", "foto direnç", "fotodirenç", "ışık sensörü", "ışığa duyarlı direnç"], "termistor": ["termistör", "ntc", "sıcaklık direnci"],
    "kondansator_seramik": ["seramik kondansatör", "kondansatör", "kapasitör", "sığaç"], "kondansator_elektrolitik": ["elektrolitik kondansatör", "elektrolitik", "elektrolitik kapasitör"],
    "bobin": ["bobin", "indüktör"], "kristal": ["kristal", "osilatör", "quartz"], "sigorta": ["sigorta", "fuse"],
    "diyot": ["diyot", "diode"], "zener": ["zener", "zener diyot"], "schottky": ["schottky", "şotki", "schottky diyot"], "kopru_diyot": ["köprü diyot", "doğrultucu", "köprü doğrultucu"],
    "led": ["led", "ışık yayan diyot"], "rgb_led": ["rgb led", "üç renkli led", "rgb"], "ir_led": ["ir led", "kızılötesi led", "infrared led"], "lazer": ["lazer", "lazer diyot"],
    "transistor_npn": ["transistör", "npn transistör", "npn", "bc547", "2n2222", "transistor"], "transistor_pnp": ["pnp transistör", "pnp", "bc557"],
    "mosfet_n": ["mosfet", "mos fet", "irlz44n"], "regulator_7805": ["7805", "regülatör", "voltaj regülatörü", "gerilim regülatörü"], "ams1117": ["ams1117", "3.3 regülatör", "1117"],
    "ne555": ["555", "ne555", "zamanlayıcı entegre", "555 entegresi"], "lm358": ["lm358", "opamp", "op amp", "işlemsel yükselteç"], "hc595": ["74hc595", "hc595", "595", "kaydırmalı yazmaç"],
    "cd4017": ["cd4017", "4017", "dekad sayıcı"], "l293d": ["l293d", "l293"], "uln2003": ["uln2003", "uln"], "pc817": ["pc817", "optokuplör", "optokuplor", "optocoupler"],
    "attiny85": ["attiny85", "attiny"], "atmega328p": ["atmega328", "atmega328p", "atmega"],
    "arduino_uno": ["arduino uno", "arduino", "uno"], "arduino_nano": ["arduino nano", "nano"], "arduino_mega": ["arduino mega", "mega"],
    "esp32": ["esp32", "esp 32"], "nodemcu": ["nodemcu", "node mcu", "esp8266"], "raspberry_pico": ["raspberry pico", "pico", "rp2040", "raspberry pi pico"],
    "dht11": ["dht11", "dht 11", "sıcaklık nem sensörü"], "dht22": ["dht22", "dht 22"], "hcsr04": ["hcsr04", "hc sr04", "ultrasonik", "mesafe sensörü", "ultrasonik sensör"],
    "pir": ["pir", "hareket sensörü", "pir sensör"], "lm35": ["lm35", "sıcaklık sensörü"], "ds18b20": ["ds18b20", "ds 18b20", "su geçirmez sıcaklık sensörü"],
    "mpu6050": ["mpu6050", "mpu 6050", "jiroskop", "ivme ölçer", "ivmeölçer"], "bmp280": ["bmp280", "basınç sensörü"], "toprak_nem": ["toprak nem sensörü", "nem sensörü", "toprak nem"],
    "mq2": ["mq2", "mq 2", "gaz sensörü", "duman sensörü"], "mikrofon": ["mikrofon", "ses sensörü"], "ir_alici": ["ir alıcı", "kızılötesi alıcı", "vs1838", "kumanda alıcısı"],
    "hall": ["hall sensörü", "hall", "manyetik sensör"], "ir_engel": ["ir engel sensörü", "engel sensörü", "çizgi sensörü"], "joystick": ["joystick", "kumanda kolu"],
    "enkoder": ["enkoder", "encoder", "döner enkoder"], "rfid": ["rfid", "rc522", "kart okuyucu"], "rtc": ["rtc", "ds3231", "gerçek zamanlı saat", "saat modülü"],
    "tus_takimi": ["tuş takımı", "keypad", "tuş takımı 4x4"],
    "buzzer": ["buzzer", "zil", "bip"], "hoparlor": ["hoparlör", "speaker"], "yedi_segment": ["yedi segment", "7 segment", "7segment", "7seg"],
    "lcd1602": ["lcd", "lcd ekran", "ekran", "1602", "lcd1602"], "oled": ["oled", "oled ekran"], "neopixel": ["neopixel", "ws2812", "adreslenebilir led", "led şerit"],
    "led_matris": ["led matris", "matris", "max7219"], "servo": ["servo", "servo motor", "servo motoru"], "dc_motor": ["dc motor", "motor", "fırçalı motor"],
    "step_motor": ["step motor", "adım motoru", "step", "28byj", "stepper"], "titresim_motoru": ["titreşim motoru", "vibrasyon motoru", "titreşim"], "role": ["röle", "role", "röle modülü"],
    "pil_9v": ["9v pil", "9 volt pil", "pil"], "pil_aa": ["aa pil", "kalem pil", "pil yuvası"], "dugme_pil": ["düğme pil", "cr2032", "para pil"],
    "lipo": ["lipo", "lityum pil", "li po"], "dc_jak": ["dc jak", "adaptör girişi", "jak"], "usb_c": ["usb c", "usb girişi", "usb besleme"],
    "lm2596": ["lm2596", "buck", "düşürücü", "gerilim düşürücü"], "tp4056": ["tp4056", "şarj modülü"], "gunes_paneli": ["güneş paneli", "solar panel"],
    "buton": ["buton", "düğme", "tuş", "push button", "basmalı düğme"], "anahtar": ["anahtar", "switch", "şalter"], "dip_switch": ["dip switch", "dip anahtar"],
    "pin_header": ["pin header", "erkek header", "header"], "disi_header": ["dişi header", "disi header"], "klemens": ["klemens", "terminal blok"],
    "hc05": ["hc05", "hc 05", "bluetooth", "bluetooth modülü"], "nrf24": ["nrf24", "nrf24l01", "nrf"], "esp01": ["esp01", "esp 01"], "lora": ["lora", "sx1278"],
    "sd_kart": ["sd kart", "sd kart modülü", "hafıza kartı"], "l298n": ["l298n", "l298", "motor sürücü"], "a4988": ["a4988", "step sürücü"],
    "tm1637": ["tm1637", "4 haneli gösterge", "dört haneli gösterge"], "seviye_donusturucu": ["seviye dönüştürücü", "level shifter", "gerilim seviye dönüştürücü"],
}

# ============================================================ HAZIR DEVRE ŞABLONLARI
# p: (anahtar, parça id, {ayar}) ; t: (anahtar, pin, anahtar, pin) ; adim: öğretici adımlar ("sıradaki adım ne" ile okunur)
SABLONLAR = [
    {"id": "yanip_sonen_led", "ad": "Yanıp sönen LED", "acik": "Arduino Uno + LED + 220 Ω direnç: ilk devre.", "w": 36, "h": 24,
     "ad_alt": ["yanıp sönen led", "blink", "led yak söndür", "ilk devre"],
     "p": [("u", "arduino_uno", {}), ("r", "direnc", {"deger": "220Ω"}), ("l", "led", {"renk": "kirmizi"})],
     "t": [("u", "D13", "r", "1"), ("r", "2", "l", "A"), ("l", "K", "u", "GND")],
     "adim": ["Arduino Uno'yu karta yerleştir.", "220 Ω direnci ekle: LED'in akımını sınırlar.", "LED'i ekle: uzun bacağı (anot) dirence bağlanır.",
              "D13 pinini direncin bir ucuna, direncin diğer ucunu LED anoduna bağla.", "LED katodunu GND'ye bağla.", "Devreyi kontrol et, sonra kodu üret."]},
    {"id": "butonla_led", "ad": "Butonla LED", "acik": "Butona basınca LED yanar (INPUT_PULLUP).", "w": 36, "h": 24,
     "ad_alt": ["butonla led", "buton led", "düğmeyle led"],
     "p": [("u", "arduino_uno", {}), ("b", "buton", {}), ("r", "direnc", {"deger": "220Ω"}), ("l", "led", {"renk": "yesil"})],
     "t": [("u", "D2", "b", "1"), ("b", "2", "u", "GND"), ("u", "D13", "r", "1"), ("r", "2", "l", "A"), ("l", "K", "u", "GND")],
     "adim": ["Arduino ve butonu ekle.", "Butonun bir ucunu D2'ye, diğer ucunu GND'ye bağla; kodda INPUT_PULLUP kullanılacak.", "LED ve 220 Ω direnci ekle.",
              "D13 - direnç - LED anot, LED katot GND.", "Kontrol et: dirençsiz LED ve boşta bacak olmamalı."]},
    {"id": "trafik_lambasi", "ad": "Trafik lambası", "acik": "Kırmızı, sarı, yeşil LED sırayla yanar.", "w": 40, "h": 28,
     "ad_alt": ["trafik lambası", "trafik ışığı", "trafik lambasi"],
     "p": [("u", "arduino_uno", {}), ("r1", "direnc", {"deger": "220Ω"}), ("r2", "direnc", {"deger": "220Ω"}), ("r3", "direnc", {"deger": "220Ω"}),
           ("k", "led", {"renk": "kirmizi"}), ("s", "led", {"renk": "sari"}), ("y", "led", {"renk": "yesil"})],
     "t": [("u", "D8", "r1", "1"), ("r1", "2", "k", "A"), ("k", "K", "u", "GND"), ("u", "D9", "r2", "1"), ("r2", "2", "s", "A"), ("s", "K", "u", "GND"),
           ("u", "D10", "r3", "1"), ("r3", "2", "y", "A"), ("y", "K", "u", "GND")],
     "adim": ["Arduino Uno'yu ekle.", "Üç LED (kırmızı, sarı, yeşil) ve üç adet 220 Ω direnç ekle.", "D8, D9, D10 pinlerini ayrı dirençlerle LED anotlarına bağla.",
              "Üç LED katodunu da GND'ye bağla.", "Kodu üret: LED'ler sırayla yanar."]},
    {"id": "park_sensoru", "ad": "Park sensörü", "acik": "Mesafe azalınca buzzer öter (HC-SR04 + buzzer).", "w": 40, "h": 28,
     "ad_alt": ["park sensörü", "mesafe alarmı", "ultrasonik alarm", "geri vites sensörü"],
     "p": [("u", "arduino_uno", {}), ("h", "hcsr04", {}), ("z", "buzzer", {})],
     "t": [("h", "VCC", "u", "5V"), ("h", "GND", "u", "GND"), ("h", "TRIG", "u", "D9"), ("h", "ECHO", "u", "D10"), ("z", "+", "u", "D8"), ("z", "-", "u", "GND")],
     "adim": ["Arduino ve HC-SR04'ü ekle.", "VCC'yi 5V'a, GND'yi GND'ye bağla.", "TRIG'i D9'a, ECHO'yu D10'a bağla.", "Buzzer'ı ekle: artı D8, eksi GND.", "Kodu üret: mesafe 30 cm altına inince öter."]},
    {"id": "sicaklik_nem", "ad": "Sıcaklık-nem istasyonu", "acik": "DHT11 ölçer, LCD ekranda gösterir.", "w": 40, "h": 28,
     "ad_alt": ["sıcaklık nem istasyonu", "hava istasyonu", "termometre", "sıcaklık nem"],
     "p": [("u", "arduino_uno", {}), ("d", "dht11", {}), ("e", "lcd1602", {})],
     "t": [("d", "VCC", "u", "5V"), ("d", "GND", "u", "GND"), ("d", "DATA", "u", "D2"), ("e", "VCC", "u", "5V"), ("e", "GND", "u", "GND"), ("e", "SDA", "u", "A4"), ("e", "SCL", "u", "A5")],
     "adim": ["Arduino, DHT11 ve LCD'yi ekle.", "DHT11: VCC 5V, GND GND, DATA D2.", "LCD'nin SDA'sı A4, SCL'si A5; VCC 5V, GND GND.", "Kodu üret ve DHT ile LiquidCrystal_I2C kütüphanelerini kur."]},
    {"id": "gece_lambasi", "ad": "Gece lambası (mikrodenetleyicisiz)", "acik": "LDR + transistör: karanlıkta LED yanar.", "w": 40, "h": 28,
     "ad_alt": ["gece lambası", "otomatik lamba", "karanlık lambası", "ldr lamba"],
     "p": [("b", "pil_aa", {"deger": "6V (4 pil)"}), ("r1", "direnc", {"deger": "10kΩ"}), ("l", "ldr", {}), ("q", "transistor_npn", {}), ("r2", "direnc", {"deger": "330Ω"}), ("d", "led", {"renk": "beyaz"})],
     "t": [("b", "+", "r1", "1"), ("r1", "2", "q", "B"), ("r1", "2", "l", "1"), ("l", "2", "b", "-"), ("b", "+", "r2", "1"), ("r2", "2", "d", "A"), ("d", "K", "q", "C"), ("q", "E", "b", "-")],
     "adim": ["4×AA pil yuvası, 10 kΩ direnç, LDR, NPN transistör, 330 Ω direnç ve LED'i ekle.", "Pilin artısından 10 kΩ direnç, direncin ucu transistör tabanına ve LDR'ye.",
              "LDR'nin diğer ucu pilin eksisine: aydınlıkta tabanı GND'ye çeker.", "LED'i 330 Ω ile pilin artısından transistör kolektörüne bağla.", "Emiteri pilin eksisine bağla; karanlıkta LED yanar."]},
    {"id": "ne555_flasor", "ad": "555 flaşör", "acik": "NE555 astable: LED yaklaşık 1 Hz yanıp söner.", "w": 44, "h": 28,
     "ad_alt": ["555 flaşör", "555 led", "555 yanıp sönen", "555 devresi"],
     "p": [("b", "pil_9v", {}), ("u", "ne555", {}), ("r1", "direnc", {"deger": "1kΩ"}), ("r2", "direnc", {"deger": "68kΩ"}), ("c", "kondansator_elektrolitik", {"deger": "10µF"}),
           ("c2", "kondansator_seramik", {"deger": "10nF"}), ("r3", "direnc", {"deger": "470Ω"}), ("l", "led", {"renk": "kirmizi"})],
     "t": [("b", "+", "u", "VCC"), ("b", "-", "u", "GND"), ("u", "RESET", "u", "VCC"), ("b", "+", "r1", "1"), ("r1", "2", "u", "DIS"), ("u", "DIS", "r2", "1"), ("r2", "2", "u", "THR"),
           ("u", "THR", "u", "TRIG"), ("u", "THR", "c", "+"), ("c", "-", "b", "-"), ("u", "CTRL", "c2", "1"), ("c2", "2", "b", "-"), ("u", "OUT", "r3", "1"), ("r3", "2", "l", "A"), ("l", "K", "b", "-")],
     "adim": ["9 V pil ve NE555'i ekle: artı VCC (8), eksi GND (1).", "RESET (4) pinini VCC'ye bağla.", "R1 (1 kΩ): VCC ile DIS (7) arası; R2 (68 kΩ): DIS ile THR (6) arası.",
              "THR (6) ile TRIG (2) pinlerini birleştir; 10 µF kondansatörü THR ile GND arasına koy (artı THR tarafı).", "CTRL (5) pinine 10 nF ile GND.",
              "OUT (3) - 470 Ω - LED - GND. Frekans f = 1,44 / ((R1+2R2)·C) ≈ 1 Hz."]},
    {"id": "servo_pot", "ad": "Servo + potansiyometre", "acik": "Potu çevir, servo aynı açıya döner.", "w": 40, "h": 26,
     "ad_alt": ["servo pot", "servo potansiyometre", "servo kontrol", "potla servo"],
     "p": [("u", "arduino_uno", {}), ("s", "servo", {}), ("p", "potansiyometre", {"deger": "10kΩ"})],
     "t": [("p", "1", "u", "5V"), ("p", "W", "u", "A0"), ("p", "2", "u", "GND"), ("s", "VCC", "u", "5V"), ("s", "GND", "u", "GND"), ("s", "SIG", "u", "D9")],
     "adim": ["Arduino, servo ve potansiyometreyi ekle.", "Potun uçları 5V ve GND, orta ucu A0.", "Servo: kırmızı 5V, kahverengi GND, turuncu sinyal D9.", "Kodu üret: analogRead değeri 0-180°'ye çevrilir."]},
    {"id": "hareket_alarmi", "ad": "Hareket alarmı", "acik": "PIR hareket görünce buzzer öter, LED yanar.", "w": 40, "h": 28,
     "ad_alt": ["hareket alarmı", "pir alarm", "hırsız alarmı", "hareket sensörlü alarm"],
     "p": [("u", "arduino_uno", {}), ("s", "pir", {}), ("z", "buzzer", {}), ("r", "direnc", {"deger": "220Ω"}), ("l", "led", {"renk": "kirmizi"})],
     "t": [("s", "VCC", "u", "5V"), ("s", "GND", "u", "GND"), ("s", "OUT", "u", "D2"), ("z", "+", "u", "D8"), ("z", "-", "u", "GND"), ("u", "D13", "r", "1"), ("r", "2", "l", "A"), ("l", "K", "u", "GND")],
     "adim": ["Arduino ve PIR sensörünü ekle: VCC 5V, GND GND, OUT D2.", "Buzzer: artı D8, eksi GND.", "LED + 220 Ω direnç: D13 - direnç - LED - GND.", "Kodu üret: hareket olunca LED yanar ve buzzer öter. PIR ilk dakika ısınır."]},
    {"id": "akilli_sulama", "ad": "Akıllı sulama", "acik": "Toprak kuruysa röle pompayı çalıştırır.", "w": 44, "h": 30,
     "ad_alt": ["akıllı sulama", "otomatik sulama", "bitki sulama", "sulama sistemi"],
     "p": [("u", "arduino_uno", {}), ("n", "toprak_nem", {}), ("k", "role", {}), ("m", "dc_motor", {}), ("b", "pil_9v", {})],
     "t": [("n", "VCC", "u", "5V"), ("n", "GND", "u", "GND"), ("n", "AO", "u", "A0"), ("k", "VCC", "u", "5V"), ("k", "GND", "u", "GND"), ("k", "IN", "u", "D7"),
           ("b", "+", "k", "COM"), ("k", "NO", "m", "+"), ("m", "-", "b", "-")],
     "adim": ["Arduino, nem sensörü ve röle modülünü ekle.", "Sensör: AO A0'a, VCC 5V, GND GND.", "Röle: VCC 5V, GND GND, IN D7.", "Pompayı (DC motor) ve 9 V pili ekle: pil artısı röle COM'a, röle NO motorun artısına, motor eksisi pil eksisine.",
              "Kodu üret: değer eşikten büyükse (kuru) röle çeker."]},
]
