"""Astronomi ve jeoloji laboratuvarı verileri (deney kataloğu, kavramlar, tablolar). Çizimler ui/scene_sci.html içindedir."""

# params: (anahtar, ad, birim, en az, en çok, varsayılan, adım)
AST_EXPS = [
    {"key": "ayevre", "name": "Ay evreleri", "aim": "Ay'ın Dünya etrafında dönerken neden farklı biçimlerde göründüğünü görmek.",
     "params": [("gun", "Ay'ın yaşı (yeni aydan beri)", "gün", 0, 29.5, 7, 0.5)],
     "formulas": ["Eş zamanlı dönüş (sinodik) süresi ≈ 29,53 gün", "Aydınlık oran = (1 − cos θ) / 2  (θ: Güneş-Dünya-Ay açısı)", "Yeni ay → ilk dördün → dolunay → son dördün"],
     "why": "Ay'ın her zaman yarısı Güneş tarafından aydınlanır. Dünya'dan bu aydınlık yüzün ne kadarını gördüğümüz, Ay'ın yörüngedeki konumuna bağlıdır. Evre değişir, Ay'ın şekli değişmez; Dünya'nın gölgesi evreleri yapmaz, o tutulmadır.",
     "alias": r"ay evre\w*|ayın evre\w*|hilal|dolunay|yeni ay|evre"},
    {"key": "mevsim", "name": "Mevsimler ve eksen eğikliği", "aim": "Mevsimlerin Dünya'nın eksen eğikliğinden doğduğunu görmek.",
     "params": [("gun", "Yılın günü", "", 0, 365, 172, 1), ("egim", "Eksen eğikliği", "°", 0, 45, 23.4, 0.1)],
     "formulas": ["Güneş'in sapması: δ ≈ eğiklik · sin(360° · (N − 80) / 365)", "Gün uzunluğu: cos H = −tan(enlem) · tan(δ),  süre = 2H / 15", "Öğle yüksekliği = 90° − |enlem − δ|"],
     "why": "Mevsimler Dünya'nın Güneş'e yakın ya da uzak olmasından değil, ekseninin eğik olmasından doğar. Yaz yarımkürede Güneş ışınları daha dik gelir ve gün uzar. Eğiklik sıfır olsaydı mevsim olmazdı.",
     "alias": r"mevsim\w*|eksen\w*|ekinoks|gündönümü"},
    {"key": "kepler", "name": "Kepler yasaları", "aim": "Gezegenlerin elips yörüngede nasıl hızlanıp yavaşladığını görmek.",
     "params": [("e", "Yörünge dışmerkezliği", "", 0, 0.9, 0.5, 0.01), ("a", "Yarı büyük eksen", "AB", 0.4, 5, 1.5, 0.05)],
     "formulas": ["1. yasa: yörünge Güneş'in odakta olduğu bir elipstir", "2. yasa: eşit sürede eşit alan tarar", "3. yasa: T² = a³  (T yıl, a astronomik birim)", "Yakın nokta: a(1 − e),  uzak nokta: a(1 + e)"],
     "why": "Gezegen Güneş'e yaklaştıkça hızlanır, uzaklaştıkça yavaşlar; öyle ki Güneş'e çizilen doğru eşit sürelerde eşit alan tarar. Yörünge büyüdükçe periyot büyük ölçüde uzar.",
     "alias": r"kepler|elips|yörünge yasa\w*|dışmerkez\w*"},
    {"key": "yorunge", "name": "Yörünge hızı ve kaçış", "aim": "Bir cismi Dünya çevresinde yörüngeye oturtmak için gereken hızı bulmak.",
     "params": [("v", "Fırlatma hızı (400 km yükseklikte)", "km/s", 3, 13, 7.67, 0.05)],
     "formulas": ["Dairesel yörünge hızı: v = √(GM / r) ≈ 7,67 km/s", "Kaçış hızı: v = √(2GM / r) ≈ 10,85 km/s", "Enerji: ε = v²/2 − GM/r  (ε < 0 bağlı yörünge)"],
     "why": "Yeterince hızlı atılan cisim yere düşerken Dünya'nın eğimi kadar uzaklaşır; bu sürekli düşmeye yörünge denir. Hız az ise cisim düşer, daire hızından fazlaysa elips çizer, kaçış hızını geçerse Dünya'dan ayrılır.",
     "alias": r"yörünge hız\w*|kaçış\w*|uydu\w*|fırlat\w*|yörüngeye"},
    {"key": "hr", "name": "Yıldız yaşamı ve HR diyagramı", "aim": "Yıldızın kütlesinin parlaklığını, ömrünü ve sonunu nasıl belirlediğini görmek.",
     "params": [("m", "Yıldız kütlesi", "Güneş", 0.1, 40, 1, 0.1)],
     "formulas": ["Parlaklık: L ≈ M^3,5  (Güneş = 1)", "Ömür: t ≈ 10 milyar yıl · M^−2,5", "Yüzey sıcaklığı ≈ 5772 K · M^0,5 (yaklaşık)"],
     "why": "Büyük yıldızlar çok daha hızlı yakıt tüketir; bu yüzden çok parlaktır ama kısa ömürlüdür. Güneş gibi yıldızlar kızıl dev olup beyaz cüceye dönüşür; çok büyükler süpernova olur, geriye nötron yıldızı ya da kara delik kalır.",
     "alias": r"hr diyagram\w*|hertzsprung|yıldız yaşam\w*|yıldız kütle\w*|ana kol|beyaz cüce|kızıl dev"},
    {"key": "tutulma", "name": "Güneş ve Ay tutulması", "aim": "Tutulmaların ne zaman ve neden oluştuğunu görmek.",
     "params": [("beta", "Ay'ın ekliptikten sapması", "°", -3, 3, 0, 0.1), ("tur", "0 Güneş tutulması, 1 Ay tutulması", "", 0, 1, 0, 1)],
     "formulas": ["Güneş tutulması: yeni ayda Ay, Güneş ile Dünya arasına girer", "Ay tutulması: dolunayda Ay, Dünya'nın gölgesine girer", "Ay yörüngesi ekliptiğe 5,1° eğiktir; tutulma için sapma yaklaşık 1,5° altında olmalı"],
     "why": "Ay'ın yörüngesi Dünya'nın yörünge düzlemine eğik olduğu için her yeni ay ve dolunayda tutulma olmaz; yalnızca Güneş, Dünya ve Ay aynı doğrultuya (düğüm noktalarına) yakın olduğunda olur.",
     "alias": r"tutulma\w*|gölge\w*"},
    {"key": "agirlik", "name": "Gezegenlerde ağırlık", "aim": "Aynı kütlenin farklı gökcisimlerinde nasıl farklı ağırlıkta olduğunu görmek.",
     "params": [("k", "Kütleniz", "kg", 1, 150, 60, 1)],
     "formulas": ["Ağırlık: G = m · g", "g(Ay) = 1,62 · g(Mars) = 3,71 · g(Dünya) = 9,81 · g(Jüpiter) = 24,8 m/s²", "Kütle her yerde aynıdır, ağırlık değişir"],
     "why": "Kütle bir maddenin miktarıdır ve değişmez. Ağırlık ise o gökcisminin kütle çekimine bağlıdır: Ay'da altıda bire düşer, Jüpiter'de iki buçuk katına çıkar.",
     "alias": r"ağırlık\w*|gezegenlerde"},
]
BODY_G = [("Merkür", 3.70), ("Venüs", 8.87), ("Ay", 1.62), ("Dünya", 9.81), ("Mars", 3.71), ("Jüpiter", 24.79), ("Satürn", 10.44), ("Uranüs", 8.87), ("Neptün", 11.15)]

AST_CONCEPTS = [
    ("Büyük Patlama", r"büyük patlama|evrenin başlangıcı|evrenin yaşı", "Evren yaklaşık 13,8 milyar yıl önce çok sıcak ve yoğun bir hâlden genişlemeye başladı. Bu genişleme hâlâ sürüyor; uzak gökadaların ışığı bu yüzden kırmızıya kayar."),
    ("Kara delik", r"kara delik", "Kara delik, çekimi o kadar güçlü olan bir bölgedir ki içinden ışık bile kaçamaz. Çok büyük yıldızların çökmesiyle oluşur; olay ufku denen sınırın içine giren geri dönemez."),
    ("Işık yılı", r"ışık yılı", "Işık yılı bir zaman değil, uzaklık birimidir: ışığın bir yılda aldığı yol, yaklaşık 9,46 trilyon kilometre. Bize en yakın yıldız Proxima Centauri 4,2 ışık yılı uzaktadır."),
    ("Kırmızıya kayma", r"kırmızıya kayma|kızıl kayma|doppler|hubble", "Bir kaynak bizden uzaklaşırken ışığının dalga boyu uzar, yani kırmızıya kayar. Hubble, uzak gökadaların bizden daha hızlı uzaklaştığını bulmuş ve evrenin genişlediğini göstermiştir."),
    ("Gökada (galaksi)", r"gökada|galaksi|samanyolu|andromeda", "Gökada, milyarlarca yıldızın, gazın ve tozun kütle çekimiyle bir arada durduğu dev bir topluluktur. Samanyolu'nun yüz milyarlarca yıldızı vardır; en yakın büyük komşusu Andromeda'dır."),
    ("Güneş sisteminin oluşumu", r"güneş sisteminin oluş\w*|güneş sistemi nasıl", "Güneş sistemi yaklaşık 4,6 milyar yıl önce dönen bir gaz ve toz bulutunun çökmesiyle oluştu. Merkezde Güneş doğdu, kalan disk çarpışarak gezegenlere dönüştü."),
    ("Güneş", r"güneş nedir|güneşin yapısı|güneşin ömrü", "Güneş, hidrojeni helyuma çevirerek enerji üreten orta büyüklükte bir yıldızdır. Yaklaşık 4,6 milyar yaşındadır ve ömrünün yarısındadır; yaklaşık 5 milyar yıl sonra kızıl dev olacaktır."),
    ("Ötegezegenler", r"ötegezegen|dış gezegen|yaşanabilir bölge", "Başka yıldızları dolaşan gezegenlere ötegezegen denir; beş binden fazlası bulunmuştur. Yaşanabilir bölge, sıvı suyun yüzeyde bulunabileceği uzaklık kuşağıdır."),
]

GEO_EXPS = [
    {"key": "levha", "name": "Levha tektoniği", "aim": "Yer kabuğu levhalarının sınırlarda nasıl hareket ettiğini görmek.",
     "params": [("tur", "Sınır türü (0 ıraksak, 1 okyanus-kıta, 2 kıta-kıta, 3 yanal atım)", "", 0, 3, 1, 1), ("hiz", "Levha hızı", "cm/yıl", 1, 15, 5, 0.5)],
     "formulas": ["Yer değiştirme = hız · zaman  (1 cm/yıl = 10 km / milyon yıl)", "Iraksak: yeni kabuk oluşur (okyanus ortası sırt)", "Yakınsak: dalma-batma ya da çarpışma (çukur, volkan, dağ)", "Yanal atım: levhalar yan yana kayar (fay)"],
     "why": "Yer'in sert dış kabuğu birkaç büyük ve çok sayıda küçük levhaya ayrılmıştır ve altındaki akışkan gibi davranan manto üzerinde yılda birkaç santimetre hareket eder. Depremler, volkanlar ve dağlar levha sınırlarında yoğunlaşır.",
     "alias": r"levha\w*|tektonik\w*|kıta kayması|dalma batma|okyanus sırtı"},
    {"key": "deprem", "name": "Deprem dalgaları ve büyüklük", "aim": "Deprem dalgalarının yayılışını ve büyüklüğün enerjisini anlamak.",
     "params": [("M", "Deprem büyüklüğü", "Mw", 3, 9, 6.5, 0.1), ("km", "Merkez üssüne uzaklık", "km", 10, 1000, 200, 10)],
     "formulas": ["Enerji: log₁₀ E = 1,5·M + 4,8  (E joule)", "Her 1 birim artış ≈ 32 kat enerji", "P dalgası ≈ 6 km/s, S dalgası ≈ 3,5 km/s", "Uzaklık ≈ (tS − tP) · 8,4 km/s"],
     "why": "P dalgaları sıkıştırma dalgalarıdır ve ilk gelir; S dalgaları kesme dalgalarıdır, daha yavaştır ama daha yıkıcıdır. İkisinin varış farkından merkez üssüne uzaklık bulunur. Büyüklük logaritmiktir: 7 büyüklüğündeki deprem 6'dakinin yaklaşık 32 katı enerji açığa çıkarır.",
     "alias": r"deprem\w*|sismik\w*|sismograf\w*|richter|büyüklük|p dalga\w*|s dalga\w*"},
    {"key": "kayac", "name": "Kayaç döngüsü", "aim": "Üç ana kayaç türü arasındaki dönüşümü izlemek.",
     "params": [("adim", "Döngü adımı (1-6)", "", 1, 6, 1, 1)],
     "formulas": ["Magmatik: magmanın soğuyup katılaşması (granit, bazalt)", "Tortul: parçaların birikip çimentolanması (kumtaşı, kireçtaşı)", "Metamorfik: ısı ve basınçla değişim (mermer, gnays)"],
     "why": "Kayaçlar yok olmaz, biçim değiştirir. Magma soğuyarak magmatik kayaç olur, aşınıp birikerek tortul, ısı ve basınçla metamorfik kayaca dönüşür; yeterince ısınınca yeniden erir. Döngü milyonlarca yıl sürer.",
     "alias": r"kayaç\w*|kaya döngü\w*|magmatik|tortul kayaç\w*|metamorfik|granit|mermer"},
    {"key": "katman", "name": "Tortul katmanlar ve yaş", "aim": "Katman kalınlığından göreli yaşı kestirmek.",
     "params": [("mm", "Birikme hızı", "mm/yıl", 0.1, 5, 1, 0.1), ("m", "Katman kalınlığı", "m", 1, 1000, 100, 1)],
     "formulas": ["Süre = kalınlık / hız", "Alttaki katman üsttekinden yaşlıdır (üst üste gelme ilkesi)", "Fosiller katmanın yaşını ve eski ortamı gösterir"],
     "why": "Tortul katmanlar yatay birikir ve üstteki her zaman daha gençtir. Yavaş birikme çok uzun süre demektir: yılda 1 mm hızla 100 metrelik bir katman yaklaşık 100 bin yılda birikir.",
     "alias": r"katman\w*|fosil\w*|stratigrafi"},
    {"key": "radyo", "name": "Radyometrik yaş tayini", "aim": "Radyoaktif bozunmayla bir örneğin yaşını hesaplamak.",
     "params": [("kalan", "Kalan radyoaktif madde", "%", 1, 100, 50, 1), ("yom", "Yarı ömür (C-14 = 5730)", "yıl", 100, 10000, 5730, 10)],
     "formulas": ["Kalan oran = (½)^(t / yarı ömür)", "Yaş: t = yarı ömür · log₂(100 / kalan %)", "C-14 ≈ 5730 yıl (50 bin yıla kadar), U-238 ≈ 4,5 milyar yıl"],
     "why": "Radyoaktif atomlar sabit bir hızla bozunur; her yarı ömürde yarısı kalır. Kalan miktarı ölçerek geçen süre bulunur. Organik kalıntılar için karbon-14, çok yaşlı kayaçlar için uranyum-kurşun gibi uzun ömürlü çiftler kullanılır.",
     "alias": r"radyometrik|karbon 14|karbon-14|yarı ömür\w*|yaş tayin\w*|radyoaktif"},
    {"key": "volkan", "name": "Volkan türleri", "aim": "Magmanın bileşiminin patlamayı nasıl belirlediğini görmek.",
     "params": [("si", "Magmanın silika oranı", "%", 45, 75, 52, 1)],
     "formulas": ["Silika az (< 52 %): bazaltik, akıcı lav, kalkan volkan", "Orta (52–63 %): andezitik, katmanlı volkan", "Silika çok (> 63 %): riyolitik, yapışkan, şiddetli patlama"],
     "why": "Silika oranı arttıkça magma kıvamlaşır; gaz kaçamayınca basınç birikir ve patlama şiddetlenir. Hawaii'deki bazaltik volkanlar akıcı lav akıtır, Vezüv ve St. Helens gibi katmanlı volkanlar kül ve gazla patlar.",
     "alias": r"volkan\w*|yanardağ\w*|lav\w*|magma\w*"},
    {"key": "mohs", "name": "Mohs sertlik ölçeği", "aim": "Minerallerin birbirini çizme sırasını öğrenmek.",
     "params": [("s", "Sertlik", "", 1, 10, 3, 1)],
     "formulas": ["1 Talk · 2 Alçıtaşı · 3 Kalsit · 4 Florit · 5 Apatit", "6 Ortoklaz · 7 Kuvars · 8 Topaz · 9 Korindon · 10 Elmas", "Tırnak ≈ 2,5 · bakır para ≈ 3,5 · çelik çivi ≈ 5,5 · cam ≈ 5,5"],
     "why": "Daha sert mineral daha yumuşağı çizer, tersi olmaz. Ölçek sıralamadır, orantılı değildir: elmas, korindondan yaklaşık dört kat daha serttir.",
     "alias": r"mohs|sertlik\w*|mineral\w*|elmas|kuvars"},
    {"key": "zaman", "name": "Jeolojik zaman çizelgesi", "aim": "Yer'in 4,6 milyar yıllık tarihinde olayları sırayla görmek.",
     "params": [("my", "Şimdiden kaç milyon yıl önce", "milyon yıl", 0, 4600, 66, 1)],
     "formulas": ["Yer'in yaşı ≈ 4,54 milyar yıl", "Eonlar: Hadeyen, Arkeen, Proterozoyik, Fanerozoyik", "Fanerozoyik: Paleozoyik → Mezozoyik → Senozoyik"],
     "why": "Yer'in tarihi çok uzundur; yaşamın görünür hâle geldiği Fanerozoyik, son yaklaşık yüzde on iki'sini oluşturur. Tüm tarih 24 saate sıkıştırılsa insan günün son saniyelerinde ortaya çıkar.",
     "alias": r"jeolojik zaman\w*|zaman çizelge\w*|dinozor\w*|buzul\w*|devir\w*|çağ\w*"},
]
GEO_CONCEPTS = [
    ("Yer'in iç yapısı", r"iç yapısı|çekirdek|manto|kabuk", "Yer, dıştan içe doğru kabuk, manto, dış çekirdek (sıvı) ve iç çekirdekten (katı) oluşur. Kabuk çok incedir; manto hacmin büyük kısmını kaplar. Merkezde sıcaklık yaklaşık 5000 °C'dir."),
    ("Deprem ve fay", r"deprem nasıl|fay nedir|kuzey anadolu|deprem nedir", "Deprem, kayaların biriken gerilmeye dayanamayıp fay boyunca kırılmasıyla oluşan sarsıntıdır. Türkiye, Anadolu, Arap ve Avrasya levhalarının buluştuğu bölgede olduğu için Kuzey ve Doğu Anadolu fayları gibi aktif faylara sahiptir."),
    ("Mineral ve kayaç farkı", r"mineral nedir|kayaç nedir|mineral ile kayaç", "Mineral, belirli kimyasal bileşimi ve kristal yapısı olan doğal katıdır (kuvars gibi). Kayaç ise bir ya da daha fazla mineralin topluluğudur (granit: kuvars, feldispat, mika)."),
    ("Erozyon ve aşınma", r"erozyon|aşınma|ayrışma", "Aşınma, kayaların su, rüzgâr, buz ve sıcaklık değişimiyle parçalanması; erozyon ise bu parçaların taşınmasıdır. Kanyonlar ve deltalar bu süreçlerin ürünüdür."),
    ("Fosiller", r"fosil nedir|fosilleşme", "Fosil, geçmişte yaşamış canlıların kayaçlarda korunmuş kalıntı ya da izidir. Genellikle tortul kayaçlarda bulunur ve eski ortamları ile katman yaşlarını anlamamıza yardım eder."),
    ("Toplu yok oluşlar", r"yok oluş|dinozorların yok|kretase", "Yaklaşık 66 milyon yıl önce büyük bir göktaşı çarpması ve volkanik etkiler dinozorların yok oluşuna yol açtı. Yer tarihinde beş büyük toplu yok oluş bilinir; en büyüğü yaklaşık 252 milyon yıl önceydi."),
]
GEO_TIME = [
    (4600, 4000, "Hadeyen eonu", "Yer oluşuyor; yüzey erimiş, Ay'ı oluşturan dev çarpma gerçekleşiyor."),
    (4000, 2500, "Arkeen eonu", "İlk kıta çekirdekleri ve ilk tek hücreli yaşam (bakteriler) ortaya çıkıyor."),
    (2500, 539, "Proterozoyik eonu", "Fotosentez atmosfere oksijen katıyor; ilk çok hücreliler ve buzul çağları."),
    (539, 485, "Kambriyen", "Kambriyen patlaması: çok sayıda hayvan grubu ortaya çıkıyor, trilobitler."),
    (485, 359, "Ordovisiyen-Devoniyen", "Balıklar çeşitleniyor, bitkiler karaya çıkıyor, ilk ormanlar."),
    (359, 252, "Karbonifer-Permiyen", "Dev bataklık ormanları (kömür), ilk sürüngenler; Permiyen sonunda en büyük yok oluş."),
    (252, 201, "Triyas", "Dinozorlar ve ilk memeliler ortaya çıkıyor; Pangea tek kıta."),
    (201, 145, "Jura", "Dev dinozorlar, ilk kuşlar; Pangea ayrılmaya başlıyor."),
    (145, 66, "Kretase", "Çiçekli bitkiler yayılıyor; dönem sonunda göktaşı ve dinozorların yok oluşu."),
    (66, 2.6, "Paleojen-Neojen", "Memeliler çeşitleniyor, Himalayalar ve Alpler yükseliyor, ilk insansı atalar."),
    (2.6, 0, "Kuvaterner", "Buzul çağları ve ısınma dönemleri; Homo sapiens ortaya çıkıyor (yaklaşık 300 bin yıl önce)."),
]
MOHS = [("Talk", 1, "tırnakla kolay çizilir, pudra gibi"), ("Alçıtaşı (jips)", 2, "tırnakla çizilir"), ("Kalsit", 3, "bakır parayla çizilir"), ("Florit", 4, "çelik çiviyle kolay çizilir"),
        ("Apatit", 5, "çelik çiviyle zor çizilir, camı zor çizer"), ("Ortoklaz (feldispat)", 6, "çelik eğeyle çizilir, camı çizer"), ("Kuvars", 7, "camı kolay çizer, çelik eğe çizemez"),
        ("Topaz", 8, "kuvarsı çizer"), ("Korindon (yakut, safir)", 9, "topazı çizer"), ("Elmas", 10, "bilinen en sert mineral, her şeyi çizer")]

from lab_more_ag import AST_X, GEO_X
from lab_more_kb import with_title
AST_CONCEPTS[:0] = with_title(AST_X)
GEO_CONCEPTS[:0] = with_title(GEO_X)
from lab_more_ref import AST_REF, GEO_REF
AST_CONCEPTS[:0] = with_title(AST_REF)
GEO_CONCEPTS[:0] = with_title(GEO_REF)
from lab_more_sim import AST_SIM_X, GEO_SIM_X
AST_EXPS.extend(AST_SIM_X)
GEO_EXPS.extend(GEO_SIM_X)
