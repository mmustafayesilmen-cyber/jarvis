"""Fizik ve matematik laboratuvarı verileri: deney/cisim kataloğu, kavramlar. Çizimler ui/scene_sci.html içindedir."""

# ----------------------------------------------------------------------------- FİZİK
# params: (anahtar, ad, birim, en az, en çok, varsayılan, adım)
FIZ_EXPS = [
    {"key": "atis", "name": "Eğik atış", "aim": "Bir cismin hız ve açıyla fırlatıldığında nasıl bir yol izlediğini incelemek.",
     "params": [("v", "Başlangıç hızı", "m/s", 2, 60, 20, 1), ("a", "Atış açısı", "°", 5, 85, 45, 1), ("g", "Yerçekimi", "m/s²", 1.6, 25, 9.8, 0.1), ("h", "Başlangıç yüksekliği", "m", 0, 50, 0, 1)],
     "formulas": ["Yatay hız: vx = v·cos(a)", "Düşey hız: vy = v·sin(a) − g·t", "Uçuş süresi: t = (vy0 + √(vy0² + 2·g·h)) / g", "Menzil: x = vx·t", "En büyük yükseklik: h + vy0² / (2g)"],
     "why": "Yatay yönde kuvvet yoktur, hız sabit kalır. Düşey yönde yerçekimi cismi yavaşlatır, sonra aşağı çeker. İkisinin birleşimi parabol çizer. Hava direnci yok sayılır; sürtünmesiz ortamda 45 derece en uzak menzili verir.",
     "alias": r"eğik atış|atış|top atma|parabol|mermi"},
    {"key": "sarkac", "name": "Basit sarkaç", "aim": "Sarkacın periyodunun neye bağlı olduğunu görmek.",
     "params": [("L", "İp uzunluğu", "m", 0.2, 5, 1.5, 0.1), ("t0", "Başlangıç açısı", "°", 5, 80, 30, 1), ("g", "Yerçekimi", "m/s²", 1.6, 25, 9.8, 0.1)],
     "formulas": ["Periyot: T = 2π·√(L / g)", "Frekans: f = 1 / T", "Küçük açılarda (yaklaşık 15° altı) periyot genliğe bağlı değildir."],
     "why": "Geri çağıran kuvvet, ağırlığın ipe dik bileşenidir. İp uzadıkça periyot uzar; kütle periyodu etkilemez. Ay'da yerçekimi az olduğu için sarkaç daha yavaş sallanır.",
     "alias": r"sarkaç|sarkac|saat sarkacı"},
    {"key": "yay", "name": "Yay-kütle (basit harmonik hareket)", "aim": "Yaya bağlı kütlenin titreşimini ve enerji dönüşümünü izlemek.",
     "params": [("m", "Kütle", "kg", 0.1, 5, 1, 0.1), ("k", "Yay sabiti", "N/m", 5, 200, 40, 1), ("A", "Genlik", "m", 0.1, 1, 0.5, 0.05)],
     "formulas": ["Periyot: T = 2π·√(m / k)", "Açısal frekans: ω = √(k / m)", "En büyük hız: v = A·ω", "Toplam enerji: E = ½·k·A²"],
     "why": "Hooke yasası: yayın kuvveti uzanımla orantılıdır (F = −kx). Kütle hareket ederken enerji yay potansiyeli ile kinetik enerji arasında gider gelir; toplam sabit kalır.",
     "alias": r"yay|harmonik|hooke|titreşim"},
    {"key": "ohm", "name": "Ohm yasası devresi", "aim": "Gerilim, direnç ve akım ilişkisini seri ve paralel bağlantıda görmek.",
     "params": [("V", "Pil gerilimi", "V", 1, 24, 9, 1), ("R1", "Direnç 1", "Ω", 1, 100, 10, 1), ("R2", "Direnç 2", "Ω", 1, 100, 20, 1), ("p", "Bağlantı (0 seri, 1 paralel)", "", 0, 1, 0, 1)],
     "formulas": ["Ohm yasası: V = I·R", "Seri: Reş = R1 + R2 (akım aynı, gerilim paylaşılır)", "Paralel: 1/Reş = 1/R1 + 1/R2 (gerilim aynı, akım paylaşılır)", "Güç: P = V·I"],
     "why": "Seri bağlamada akım tek yoldan geçer, dirençler toplanır. Paralelde akım kollara ayrılır, eşdeğer direnç en küçük dirençten bile küçük olur; evdeki prizler bu yüzden paralel bağlıdır.",
     "alias": r"ohm|devre|direnç|akım|seri|paralel"},
    {"key": "dalga", "name": "Dalgalar ve girişim", "aim": "İki dalganın üst üste binmesini (süperpozisyon) gözlemlemek.",
     "params": [("f1", "Dalga 1 frekansı", "Hz", 0.5, 6, 2, 0.1), ("A1", "Dalga 1 genliği", "", 0.1, 1, 0.8, 0.05), ("f2", "Dalga 2 frekansı", "Hz", 0, 6, 2.5, 0.1), ("A2", "Dalga 2 genliği", "", 0, 1, 0.6, 0.05)],
     "formulas": ["Dalga hızı: v = λ·f", "Periyot: T = 1 / f", "Üst üste binme: y = y1 + y2", "Frekans farkı küçükse vuru (çarpışma) oluşur: f vuru = |f1 − f2|"],
     "why": "Aynı yerde buluşan dalgalar toplanır. Tepeler tepelerle buluşursa genlik büyür (yapıcı girişim), tepe çukurla buluşursa söner (yıkıcı girişim). Yakın frekanslarda ses dalgalanır; buna vuru denir.",
     "alias": r"dalga|girişim|süperpozisyon|vuru|ses dalgası"},
    {"key": "kirilma", "name": "Işığın kırılması (Snell yasası)", "aim": "Işığın iki ortam arasında nasıl yön değiştirdiğini görmek.",
     "params": [("n1", "Üst ortam kırıcılık indisi", "", 1, 2.5, 1, 0.01), ("n2", "Alt ortam kırıcılık indisi", "", 1, 2.5, 1.5, 0.01), ("a", "Gelme açısı", "°", 0, 85, 40, 1)],
     "formulas": ["Snell yasası: n1·sin(θ1) = n2·sin(θ2)", "Işığın ortamdaki hızı: v = c / n", "Tam yansıma sınır açısı: sin(θc) = n2 / n1 (n1 > n2 iken)"],
     "why": "Işık daha yoğun ortama girince yavaşlar ve normale yaklaşır. Hava 1,00, su 1,33, cam yaklaşık 1,5, elmas 2,42 indise sahiptir. Yoğun ortamdan seyrek ortama geçerken belli açıdan sonra ışık dışarı çıkamaz, tamamen yansır.",
     "alias": r"kırılma|snell|ışık|kırıcılık|yansıma|tam yansıma"},
    {"key": "carpisma", "name": "Çarpışma ve momentum", "aim": "İki cismin çarpışmasında momentum ve enerjinin nasıl davrandığını görmek.",
     "params": [("m1", "Kütle 1", "kg", 1, 10, 3, 1), ("v1", "Hız 1", "m/s", 0, 10, 5, 0.5), ("m2", "Kütle 2", "kg", 1, 10, 2, 1), ("v2", "Hız 2", "m/s", -10, 5, -1, 0.5), ("e", "Esneklik (1 esnek, 0 yapışır)", "", 0, 1, 1, 0.1)],
     "formulas": ["Momentum: p = m·v", "Momentumun korunumu: m1·v1 + m2·v2 = m1·v1' + m2·v2'", "Esnek çarpışmada kinetik enerji de korunur", "v1' = ((m1 − e·m2)·v1 + (1 + e)·m2·v2) / (m1 + m2)"],
     "why": "Dış kuvvet yoksa toplam momentum her çarpışmada korunur. Esnek çarpışmada kinetik enerji de korunur; esnek olmayanda bir kısmı ısıya ve deformasyona gider, tam esnek olmayanda cisimler yapışıp birlikte gider.",
     "alias": r"çarpışma|momentum|çarpışsın|vagon|bilardo"},
    {"key": "mercek", "name": "İnce kenarlı mercek", "aim": "Mercekte görüntünün nerede ve nasıl oluştuğunu bulmak.",
     "params": [("f", "Odak uzaklığı (− ıraksak)", "cm", -12, 12, 6, 1), ("d", "Cisim uzaklığı", "cm", 2, 30, 14, 1)],
     "formulas": ["Mercek denklemi: 1/f = 1/d + 1/d'", "Büyütme: M = −d' / d", "f > 0: yakınsak (ince kenarlı), f < 0: ıraksak (kalın kenarlı)", "d > f iken gerçek ve ters görüntü, d < f iken sanal ve düz görüntü oluşur."],
     "why": "Yakınsak mercek ışınları odakta toplar. Cisim odağın ötesindeyse ters, gerçek görüntü ekranda yakalanır (projeksiyon, kamera). Odak içindeyse büyüteç gibi düz ve büyük, sanal bir görüntü görürsünüz. Iraksak mercek her zaman küçük, düz, sanal görüntü verir.",
     "alias": r"mercek|büyüteç|odak|optik|görüntü oluş"},
    {"key": "duzlem", "name": "Eğik düzlem ve sürtünme", "aim": "Eğik düzlemde cismin hareketini ve sürtünmenin etkisini görmek.",
     "params": [("a", "Düzlem açısı", "°", 0, 60, 30, 1), ("mu", "Sürtünme katsayısı", "", 0, 1, 0.2, 0.05), ("m", "Kütle", "kg", 1, 10, 2, 1)],
     "formulas": ["Düzleme paralel bileşen: m·g·sin(a)", "Normal kuvvet: N = m·g·cos(a)", "Sürtünme: f = μ·N", "İvme: a = g·(sin(a) − μ·cos(a))", "Cisim kayması için tan(a) > μ olmalı."],
     "why": "Ağırlık iki bileşene ayrılır: biri yüzeye dik, biri yüzey boyunca. Sürtünme kuvveti normal kuvvetle orantılıdır. Açı arttıkça kaydırıcı bileşen artar, sürtünme azalır; tan(açı) sürtünme katsayısını aşınca cisim kaymaya başlar.",
     "alias": r"eğik düzlem|düzlem|sürtünme|kayma|kızak"},
]

FIZ_CONCEPTS = [
    ("Newton'un hareket yasaları", r"newton|hareket yasa|eylemsizlik|etki tepki",
     "Birinci yasa (eylemsizlik): net kuvvet sıfırsa cisim durumunu korur. İkinci yasa: F = m·a, net kuvvet kütle çarpı ivmedir. Üçüncü yasa: her etkiye eşit ve zıt yönde bir tepki vardır."),
    ("Enerjinin korunumu", r"enerji\w* korunum\w*|kinetik enerji|potansiyel enerji|enerji nedir",
     "Enerji yoktan var olmaz, vardan yok olmaz; yalnızca biçim değiştirir. Kinetik enerji ½·m·v², yer çekimi potansiyel enerjisi m·g·h'dir. Sürtünmesiz sistemde ikisinin toplamı sabit kalır."),
    ("İş ve güç", r"iş nedir|güç nedir|iş ve güç|watt|joule",
     "İş, kuvvetin yol boyunca etkisidir: W = F·x (joule). Güç, birim zamanda yapılan iştir: P = W / t (watt). Bir beygir gücü yaklaşık 746 watt'tır."),
    ("Basınç ve Pascal prensibi", r"basınç|pascal",
     "Basınç, birim yüzeye uygulanan dik kuvvettir: P = F / A (pascal). Kapalı sıvıda uygulanan basınç her yöne aynen iletilir; hidrolik kriko bu prensiple çalışır. Sıvı basıncı P = ρ·g·h ile derinlikle artar."),
    ("Arşimet kaldırma kuvveti", r"arşimet|kaldırma kuvveti|yüzme|batma",
     "Sıvıya batan cisme yukarı yönde, yer değiştirdiği sıvının ağırlığı kadar kuvvet etki eder: F = ρ·g·V. Cismin yoğunluğu sıvıdan küçükse yüzer."),
    ("Ohm yasası ve elektrik", r"ohm yasası|elektrik akımı|gerilim nedir|direnç nedir",
     "Akım, gerilimle doğru, dirençle ters orantılıdır: I = V / R. Akım amper, gerilim volt, direnç ohm ile ölçülür. Elektriksel güç P = V·I'dır."),
    ("Ses", r"ses nedir|ses dalgası|desibel|yankı|doppler",
     "Ses, ortamın titreşimiyle yayılan boyuna bir dalgadır; boşlukta yayılmaz. Havada hızı yaklaşık 340 m/s, suda yaklaşık 1500 m/s'dir. Doppler olayında kaynak yaklaşırken ses incelir, uzaklaşırken kalınlaşır."),
    ("Işık ve renkler", r"ışık nedir|ışık hızı|renkler|gökkuşağı|prizma",
     "Işık, boşlukta saniyede yaklaşık 300 bin kilometre hızla yayılan elektromanyetik dalgadır. Beyaz ışık prizmada kırılarak renklerine ayrılır, çünkü her rengin kırılma indisi biraz farklıdır."),
    ("Isı ve sıcaklık", r"ısı nedir|sıcaklık|kalori|ısı geçişi|iletim|konveksiyon",
     "Isı bir enerji aktarımıdır, sıcaklık ise ortalama taneciklerin kinetik enerjisinin ölçüsüdür. Isı üç yolla geçer: iletim, konveksiyon (taşınım) ve ışıma. Q = m·c·ΔT ile hesaplanır."),
    ("Yerçekimi", r"yerçekimi|kütle çekim|ağırlık|serbest düşme",
     "Kütleler birbirini çeker: F = G·m1·m2 / r². Dünya yüzeyinde serbest düşen her cismin ivmesi yaklaşık 9,8 m/s²'dir; hava direnci olmasaydı tüy ile taş aynı anda düşerdi. Ağırlık G = m·g'dir, kütle değişmez ama ağırlık değişir."),
    ("Momentum", r"momentum nedir|itme|çizgisel momentum",
     "Momentum kütle çarpı hızdır (p = m·v). Bir cismi durdurmak için gereken itme, momentum değişimine eşittir: F·Δt = Δp. Kask ve hava yastığı çarpışma süresini uzatıp kuvveti azaltır."),
    ("Manyetizma", r"manyetizma|mıknatıs|manyetik alan|elektromıknatıs",
     "Hareketli yükler manyetik alan oluşturur, değişen manyetik alan da elektrik akımı doğurur (indüksiyon). Mıknatısın aynı kutupları iter, zıt kutupları çeker. Jeneratörler ve transformatörler bu prensiple çalışır."),
]

# ----------------------------------------------------------------------------- MATEMATİK
# 3B cisimler: params (anahtar, ad, varsayılan)
SHAPES = [
    {"key": "kup", "name": "Küp", "params": [("a", "kenar", 3)], "alias": r"küp\w*|kup",
     "V": "a³", "A": "6·a²", "info": "6 yüz, 12 ayrıt, 8 köşe. Bütün yüzleri eş karedir.", "counts": (8, 12, 6)},
    {"key": "prizma", "name": "Dikdörtgenler prizması", "params": [("a", "uzunluk", 4), ("b", "genişlik", 3), ("c", "yükseklik", 2)], "alias": r"prizma|dikdörtgen|kutu",
     "V": "a·b·c", "A": "2·(ab + bc + ac)", "info": "6 yüz, 12 ayrıt, 8 köşe. Karşılıklı yüzler eşit dikdörtgendir.", "counts": (8, 12, 6)},
    {"key": "piramit", "name": "Kare piramit", "params": [("a", "taban kenarı", 4), ("h", "yükseklik", 3)], "alias": r"piramit",
     "V": "a²·h / 3", "A": "a² + 2·a·l  (l = yan yüz yüksekliği)", "info": "5 yüz, 8 ayrıt, 5 köşe. Tabanı kare, yan yüzleri eş üçgendir.", "counts": (5, 8, 5)},
    {"key": "silindir", "name": "Silindir", "params": [("r", "yarıçap", 2), ("h", "yükseklik", 4)], "alias": r"silindir|boru|tüp",
     "V": "π·r²·h", "A": "2·π·r·(r + h)", "info": "2 dairesel taban ve bir eğri yüzey. Açınımı iki daire ve bir dikdörtgendir.", "counts": None},
    {"key": "koni", "name": "Koni", "params": [("r", "yarıçap", 2), ("h", "yükseklik", 4)], "alias": r"\bkoni|külah",
     "V": "π·r²·h / 3", "A": "π·r·(r + l)  (l = √(r² + h²))", "info": "Bir dairesel taban, bir tepe noktası ve eğri yüzey.", "counts": None},
    {"key": "kure", "name": "Küre", "params": [("r", "yarıçap", 3)], "alias": r"küre|top\b|gezegen",
     "V": "4·π·r³ / 3", "A": "4·π·r²", "info": "Her noktası merkezden aynı uzaklıkta olan yüzey. Aynı hacimde en az yüzey alanına sahip cisimdir.", "counts": None},
    {"key": "tetra", "name": "Düzgün dörtyüzlü", "params": [("a", "kenar", 3)], "alias": r"dörtyüzlü|tetra|düzgün dört",
     "V": "a³·√2 / 12", "A": "√3·a²", "info": "4 eşkenar üçgen yüz, 6 ayrıt, 4 köşe.", "counts": (4, 6, 4)},
    {"key": "okta", "name": "Düzgün sekizyüzlü", "params": [("a", "kenar", 3)], "alias": r"sekizyüzlü|okta|düzgün sekiz",
     "V": "a³·√2 / 3", "A": "2·√3·a²", "info": "8 eşkenar üçgen yüz, 12 ayrıt, 6 köşe.", "counts": (6, 12, 8)},
    {"key": "simit", "name": "Simit (torus)", "params": [("R", "büyük yarıçap", 3), ("r", "küçük yarıçap", 1)], "alias": r"simit|torus|halka cisim",
     "V": "2·π²·R·r²", "A": "4·π²·R·r", "info": "Bir dairenin, kendi düzlemindeki bir eksen etrafında döndürülmesiyle oluşur.", "counts": None},
]

MATH_CONCEPTS = [
    ("Pisagor teoremi", r"pisagor", "Dik üçgende dik kenarların kareleri toplamı hipotenüsün karesine eşittir: a² + b² = c². Örneğin 3, 4, 5 üçgeni."),
    ("Asal sayılar", r"asal sayı", "Yalnızca 1'e ve kendisine bölünen, 1'den büyük sayılara asal denir. 2 tek çift asaldır. Sonsuz sayıda asal vardır; Öklid bunu yaklaşık iki bin üç yüz yıl önce kanıtladı."),
    ("Pi sayısı", r"\bpi\b|pi sayısı", "Bir çemberin çevresinin çapına oranıdır, yaklaşık 3,14159. İrrasyoneldir, yani ondalık açılımı hiç bitmez ve tekrar etmez."),
    ("Türev", r"türev nedir|türev ne", "Türev, bir fonksiyonun bir noktadaki anlık değişim hızıdır, yani teğetinin eğimi. x'in n'inci kuvvetinin türevi n çarpı x üzeri n eksi bir'dir."),
    ("İntegral", r"integral nedir|integral ne", "İntegral, eğri altında kalan alanı bulur ve türevin tersidir. x üzeri n'in integrali x üzeri n artı bir bölü n artı bir, artı bir sabittir."),
    ("İkinci derece denklem", r"ikinci derece|diskriminant|delta", "ax² + bx + c = 0 denkleminde delta = b² − 4ac'dir. Delta pozitifse iki gerçek kök, sıfırsa tek kök, negatifse gerçek kök yoktur. Kökler x = (−b ± √delta) / 2a'dır."),
    ("Trigonometri", r"trigonometri|sinüs nedir|kosinüs nedir", "Dik üçgende sinüs karşı kenarın hipotenüse, kosinüs komşu kenarın hipotenüse, tanjant karşının komşuya oranıdır. Birim çemberde sinüs ve kosinüs, açının noktasının y ve x koordinatıdır. sin² + cos² = 1."),
    ("Logaritma", r"logaritma nedir", "Logaritma üssün tersidir: 2 üzeri 3 sekiz ise log 2 tabanında 8 üç eder. Çarpmayı toplamaya çevirir: log(ab) = log a + log b."),
    ("Olasılık", r"olasılık", "Bir olayın olasılığı, istenen durum sayısının tüm durum sayısına oranıdır; 0 ile 1 arasındadır. Zar atınca altı gelme olasılığı 1/6'dır."),
    ("Kombinasyon ve permütasyon", r"kombinasyon nedir|permütasyon nedir", "Permütasyonda sıra önemlidir: P(n,r) = n! / (n−r)!. Kombinasyonda sıra önemsizdir: C(n,r) = n! / (r!·(n−r)!). Örneğin 10 kişiden 3 kişilik takım C(10,3) = 120 yolla kurulur."),
]

from lab_more_fm import FIZ_X, MATH_X
from lab_more_kb import with_title
FIZ_CONCEPTS[:0] = with_title(FIZ_X)
MATH_CONCEPTS[:0] = with_title(MATH_X)
from lab_more_ref import FIZ_REF, MAT_REF
FIZ_CONCEPTS[:0] = with_title(FIZ_REF)
MATH_CONCEPTS[:0] = with_title(MAT_REF)
from lab_more_sim import FIZ_SIM_X
FIZ_EXPS.extend(FIZ_SIM_X)
