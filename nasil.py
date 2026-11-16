"""'Nasıl Çalışır?' modu verisi: bir cihazın / olayın işleyişini adım adım anlatır. 14 konu yerleşiktir (internet ve model gerekmez);
listede olmayan bir konu sorulunca yerel dil modeli (Ollama) aynı biçimde bir anlatım üretir, sonuç nasil_cache.json'da saklanır (gitignored).
Üretilen içerik arayüzde 'yapay zekâ ile üretildi' diye işaretlenir. Konu: ad, kat, ikon, ozet, benzetme, adim[(başlık, metin)], bilgi, soru[{q, s[3], c}]."""
import json
import os
import re
import threading

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nasil_cache.json")
NOTIFY = None                                      # main.py: NOTIFY(do, say) -> sayfaya iletir ve gerekirse söyler
S = {"id": None, "step": -1, "q": -1, "busy": "", "score": [0, 0]}
_lock = threading.Lock()


def _q(q, s, c):
    return {"q": q, "s": s, "c": c}


TOPICS = [
 {"id": "buzdolabi", "ad": "Buzdolabı", "kat": "Ev", "ikon": "🧊",
  "ozet": "Buzdolabı soğuk üretmez; içerideki ısıyı bir gazla toplayıp dışarı taşır.",
  "benzetme": "Terlediğinde serinlemen gibi: buharlaşan sıvı ısıyı alıp götürür. Buzdolabı bunu kapalı bir boruda tekrar tekrar yapar.",
  "adim": [("Kompresör sıkıştırır", "Arkadaki kompresör soğutucu gazı sıkıştırır. Sıkışan gaz ısınır ve basıncı yükselir."),
           ("Arkada ısı atılır", "Sıcak gaz arkadaki kıvrımlı borulardan (yoğuşturucu) geçer, ısısını odaya verir ve sıvıya dönüşür. Buzdolabının arkası bu yüzden ılıktır."),
           ("Genleşme valfi", "Sıvı dar bir delikten geçince basıncı birden düşer ve çok soğur."),
           ("İçeride ısı emilir", "Soğuk sıvı, dolabın içindeki borulardan (buharlaştırıcı) geçerken içerideki ısıyı emer ve yeniden gaza dönüşür."),
           ("Termostat döngüyü yönetir", "İçerisi istenen sıcaklığa inince termostat kompresörü durdurur, ısınınca yeniden çalıştırır. Duyduğun uğultu bu açılıp kapanmadır.")],
  "bilgi": "Kapağı açık bırakılan buzdolabı odayı soğutmaz, tersine ısıtır: arkadan attığı ısı, içeriden çektiğinden fazladır.",
  "soru": [_q("Buzdolabının arkası neden ılıktır?", ["Motor bozuk olduğu için", "İçeriden alınan ısı orada dışarı atıldığı için", "Elektrik kabloları ısındığı için"], 1),
           _q("Soğutucu sıvı içerideki ısıyı emince neye dönüşür?", ["Gaza", "Buza", "Suya"], 0)]},
 {"id": "mikrodalga", "ad": "Mikrodalga fırın", "kat": "Ev", "ikon": "📡",
  "ozet": "Mikrodalgalar yiyecekteki su moleküllerini hızla döndürür; bu sürtünme ısıya dönüşür.",
  "benzetme": "Ellerini hızlı hızlı birbirine sürtünce ısınması gibi: su molekülleri saniyede milyarlarca kez dönüp birbirine sürtünür.",
  "adim": [("Magnetron dalga üretir", "Fırının içindeki magnetron, elektriği yaklaşık 2,45 GHz frekanslı mikrodalgalara çevirir."),
           ("Dalgalar içeride sekmesi", "Metal duvarlar dalgaları yansıtır; dalgalar kutunun içinde sekerek yiyeceğe her yönden ulaşır."),
           ("Su molekülleri döner", "Su molekülünün bir ucu artı, bir ucu eksi yüklüdür. Değişen elektrik alanı molekülleri sürekli döndürür."),
           ("Sürtünme ısıya dönüşür", "Dönen moleküller komşularına çarpar, bu hareket ısı olarak yiyeceği ısıtır."),
           ("Döner tabla eşitler", "Dalgalar bazı noktalarda güçlü, bazılarında zayıftır. Döner tabla yemeğin her yerinin eşit ısınmasına yardım eder.")],
  "bilgi": "Mikrodalga fırın, bir mühendisin cebindeki çikolatanın radar cihazının yanında eridiğini fark etmesiyle 1945'te keşfedildi.",
  "soru": [_q("Mikrodalga yiyecekte en çok neyi hareket ettirir?", ["Tuz kristallerini", "Su moleküllerini", "Yağ damlalarını"], 1),
           _q("Döner tabla ne işe yarar?", ["Yemeği eşit ısıtmaya", "Dalga üretmeye", "Kapağı kilitlemeye"], 0)]},
 {"id": "dokunmatik", "ad": "Dokunmatik ekran", "kat": "Teknoloji", "ikon": "📱",
  "ozet": "Telefon ekranı, parmağının vücut elektriğiyle bozduğu küçük elektrik alanından dokunduğun yeri bulur.",
  "benzetme": "Gergin bir örümcek ağına dokununca titreşimin nereden geldiğinin anlaşılması gibi; ekran da alanın nerede bozulduğunu ölçer.",
  "adim": [("Görünmez ızgara", "Camın altında saydam iletken tellerden (ITO) yatay ve dikey ince bir ızgara vardır."),
           ("Elektrik alanı", "Izgaranın kesişim noktalarında sürekli küçük bir elektrik yükü (kapasitans) tutulur."),
           ("Parmak yükü çeker", "Vücudun elektriği iletir. Parmağın yaklaşınca o noktadaki yükün bir kısmını kendine çeker."),
           ("Değişim ölçülür", "Denetleyici çip, saniyede yüzlerce kez tüm noktaları tarar ve yükün nerede azaldığını bulur."),
           ("Koordinata çevrilir", "Değişen noktalar x-y koordinatına çevrilir; telefon dokunmayı, kaydırmayı ya da iki parmakla yakınlaştırmayı buradan anlar.")],
  "bilgi": "Normal eldivenle ekran çalışmaz çünkü kumaş elektriği iletmez; dokunmatik eldivenlerin parmak uçlarında iletken iplik vardır.",
  "soru": [_q("Ekran neden eldivenle çalışmaz?", ["Eldiven çok kalın olduğu için", "Kumaş elektriği iletmediği için", "Ekran ısıyı ölçtüğü için"], 1),
           _q("Dokunma yerini hangi parça hesaplar?", ["Denetleyici çip", "Batarya", "Kamera"], 0)]},
 {"id": "gps", "ad": "GPS", "kat": "Teknoloji", "ikon": "🛰️",
  "ozet": "Telefonun, en az dört uydudan gelen sinyalin ne kadar sürede ulaştığını ölçerek yerini hesaplar.",
  "benzetme": "Şimşeği görüp gök gürültüsünü saydığında fırtınanın uzaklığını bulman gibi: gecikme mesafeyi verir.",
  "adim": [("Uydular saat yayını yapar", "Dünya çevresinde 30 kadar GPS uydusu döner; her biri çok hassas atom saatiyle 'şu anki saat ve konumum' bilgisini yayınlar."),
           ("Sinyal gecikir", "Sinyal ışık hızında gelir ama yine de birkaç yüzde bir saniyede ulaşır. Alıcı bu gecikmeyi ölçer."),
           ("Gecikme mesafeye dönüşür", "Gecikme ışık hızıyla çarpılınca o uyduya olan uzaklık bulunur."),
           ("Kesişim yeri bulur", "Üç uydunun uzaklık küreleri tek bir noktada kesişir (trilaterasyon). Dördüncü uydu telefonun saatindeki hatayı düzeltir."),
           ("Harita üstüne konur", "Bulunan enlem, boylam ve yükseklik haritada gösterilir; sinyal birkaç metre hassasiyet verir.")],
  "bilgi": "Uydular hızlı hareket ettiği ve yerçekimi zayıf olduğu için saatleri bizimkinden farklı akar; Einstein'ın görelilik düzeltmesi yapılmasa GPS günde 10 km kadar şaşardı.",
  "soru": [_q("Konum hesaplamak için en az kaç uydu gerekir?", ["Bir", "İki", "Dört"], 2),
           _q("GPS uzaklığı neyden hesaplar?", ["Sinyalin gecikme süresinden", "Sinyalin renginden", "Uydunun boyutundan"], 0)]},
 {"id": "internet", "ad": "İnternet", "kat": "Teknoloji", "ikon": "🌐",
  "ozet": "Bir web sayfası küçük paketlere bölünür, yönlendiriciler bunları en uygun yoldan sana taşır, tarayıcı yeniden birleştirir.",
  "benzetme": "Bir kitabı sayfa sayfa ayrı zarflarla postalamak gibi: her zarfta adres ve sayfa numarası vardır, varınca sırayla dizilir.",
  "adim": [("Adres sorulur (DNS)", "Tarayıcıya 'eba.gov.tr' yazınca, DNS sunucusu bu adı bilgisayarların anladığı IP numarasına çevirir."),
           ("İstek gönderilir", "Tarayıcı o IP'deki sunucuya 'bu sayfayı ver' isteği yollar."),
           ("Veri paketlere bölünür", "Sunucu sayfayı binlerce küçük pakete böler; her pakette gönderen, alıcı ve sıra numarası yazar."),
           ("Yönlendiriciler taşır", "Paketler modem, operatör ve deniz altındaki fiber kablolar üzerinden yönlendiriciden yönlendiriciye atlayarak gelir; farklı yollardan gelebilirler."),
           ("Birleştirilir ve çizilir", "Bilgisayar paketleri sıraya koyar, eksik olanı yeniden ister ve tarayıcı sayfayı ekrana çizer.")],
  "bilgi": "Kıtalar arası internet trafiğinin %95'ten fazlası uydudan değil, okyanus tabanına döşenmiş fiber optik kablolardan geçer.",
  "soru": [_q("DNS ne işe yarar?", ["Site adını IP numarasına çevirir", "Virüsleri siler", "Wi-Fi şifresini saklar"], 0),
           _q("Kıtalar arası verinin çoğu nereden geçer?", ["Uydulardan", "Deniz altı kablolardan", "Radyo kulelerinden"], 1)]},
 {"id": "wifi", "ad": "Wi-Fi", "kat": "Teknoloji", "ikon": "📶",
  "ozet": "Modem, bilgiyi radyo dalgalarına çevirip havaya yayar; cihazın bu dalgaları geri bilgiye çevirir.",
  "benzetme": "El feneriyle Mors kodu yollamak gibi, ama göremediğimiz bir ışıkla (radyo dalgası) ve saniyede milyonlarca kez.",
  "adim": [("Veri modeme gelir", "İnternetten gelen veri kablo ya da fiberle evdeki modeme ulaşır."),
           ("Radyo dalgasına çevrilir", "Modemin içindeki verici, 0 ve 1'leri 2,4 GHz ya da 5 GHz radyo dalgasının küçük değişimlerine kodlar."),
           ("Antenler yayar", "Antenler dalgayı odaya yayar; duvarlar ve su (insan vücudu bile) dalgayı zayıflatır."),
           ("Cihaz çözer", "Telefonundaki Wi-Fi çipi dalgayı yakalar ve yeniden 0 ve 1'lere çevirir."),
           ("Şifre korur", "Şifre (WPA2/WPA3) ile veri karıştırılır; şifreyi bilmeyen yakalasa bile anlamlı bir şey okuyamaz.")],
  "bilgi": "5 GHz Wi-Fi daha hızlıdır ama duvarlardan 2,4 GHz kadar iyi geçemez; bu yüzden uzak odada 2,4 GHz daha iyi çeker.",
  "soru": [_q("Wi-Fi bilgiyi neyle taşır?", ["Ses dalgasıyla", "Radyo dalgasıyla", "Kızılötesi ışıkla"], 1),
           _q("Hangisi duvarlardan daha iyi geçer?", ["2,4 GHz", "5 GHz", "İkisi aynı"], 0)]},
 {"id": "gunespaneli", "ad": "Güneş paneli", "kat": "Enerji", "ikon": "☀️",
  "ozet": "Güneş ışığı silikondaki elektronları yerinden oynatır; panel bu elektronları tek yöne akıtıp elektrik yapar.",
  "benzetme": "Bilardo topuna vurmak gibi: ışık parçacığı (foton) elektrona çarpar ve onu harekete geçirir.",
  "adim": [("İki kat silikon", "Panel hücresi iki ince silikon katmandan yapılır: biri elektron fazlası (n), diğeri elektron eksiği (p) olacak şekilde hazırlanır."),
           ("Sınırda alan oluşur", "İki katmanın birleştiği yerde, elektronları tek yöne iten doğal bir elektrik alanı oluşur."),
           ("Foton çarpar", "Güneş ışığındaki fotonlar silikona çarpar ve elektronları atomlarından koparır."),
           ("Elektron akar", "Serbest kalan elektronlar alan tarafından tek yöne itilir; üstteki ince metal çizgiler onları toplar. Bu doğru akımdır (DC)."),
           ("Evde kullanılır", "İnvertör doğru akımı prizlerdeki alternatif akıma (AC) çevirir; fazlası aküde saklanabilir ya da şebekeye verilir.")],
  "bilgi": "Güneş panelleri sıcakta değil soğuk ve güneşli havada daha verimli çalışır; ısı verimi düşürür.",
  "soru": [_q("Panelde elektronları yerinden oynatan nedir?", ["Rüzgâr", "Işık parçacıkları (foton)", "Panelin ısısı"], 1),
           _q("İnvertör ne yapar?", ["DC'yi AC'ye çevirir", "Paneli temizler", "Işığı toplar"], 0)]},
 {"id": "motor", "ad": "Elektrik motoru", "kat": "Enerji", "ikon": "⚙️",
  "ozet": "Elektrik akımı bir mıknatıs oluşturur; bu mıknatıs sabit mıknatıslarla itişip çekişerek mili döndürür.",
  "benzetme": "İki mıknatısı yaklaştırınca birinin döndüğünü hissedersin; motor bunu kutupları sürekli değiştirerek hiç durmadan yapar.",
  "adim": [("Sabit mıknatıslar", "Motor gövdesinin içinde kuzey ve güney kutuplu sabit mıknatıslar (stator) vardır."),
           ("Bobin mıknatısa döner", "Ortadaki dönen parçadaki (rotor) tel sargılardan akım geçince sargı bir elektromıknatısa dönüşür."),
           ("İtme ve çekme", "Benzer kutuplar iter, zıt kutuplar çeker; bu kuvvet rotoru döndürmeye başlar."),
           ("Kutup değişir", "Rotor yarım tur dönünce fırçalar ve kolektör akımın yönünü ters çevirir; böylece itme hep aynı yönde sürer."),
           ("Mil iş yapar", "Dönen mile bağlı pervane, tekerlek ya da fan hareket eder: elektrik enerjisi hareket enerjisine dönüşmüştür.")],
  "bilgi": "Motoru elle döndürürsen ters çalışır ve elektrik üretir; jeneratörler de aynı yapıdadır.",
  "soru": [_q("Motorda akım geçen sargı neye dönüşür?", ["Elektromıknatısa", "Pile", "Isıtıcıya"], 0),
           _q("Motor hangi enerjiyi hangisine çevirir?", ["Isıyı elektriğe", "Elektriği harekete", "Işığı sese"], 1)]},
 {"id": "ucak", "ad": "Uçak nasıl uçar", "kat": "Ulaşım", "ikon": "✈️",
  "ozet": "Kanat havayı aşağı doğru iter; tepki olarak hava da kanadı yukarı iter. Buna kaldırma kuvveti denir.",
  "benzetme": "Hareket eden arabanın camından elini hafif eğik çıkarınca elinin yukarı kalkması gibi.",
  "adim": [("Motor iter", "Jet motoru ya da pervane havayı geriye üfler, uçak ileri itilir (itki)."),
           ("Hava kanattan akar", "Uçak hızlandıkça kanatların üstünden ve altından hızla hava akar."),
           ("Kanat havayı saptırır", "Kanadın kavisli şekli ve hafif eğik duruşu (hücum açısı) havayı aşağı yönlendirir; kanadın üstünde basınç düşer, altında artar."),
           ("Kaldırma kuvveti", "Basınç farkı ve aşağı itilen hava kanadı yukarı kaldırır. Kaldırma, uçağın ağırlığını geçince uçak havalanır."),
           ("Kumanda yüzeyleri yönlendirir", "Kuyruk ve kanatlardaki hareketli kapakçıklar burnu kaldırır, uçağı yatırır ve döndürür.")],
  "bilgi": "Bir yolcu uçağı kalkışta saatte yaklaşık 250-290 km hıza ulaşmadan yerden kesilemez.",
  "soru": [_q("Kaldırma kuvvetini asıl oluşturan nedir?", ["Motorun sesi", "Kanadın havayı aşağı saptırması", "Uçağın hafifliği"], 1),
           _q("Uçağı ileri iten kuvvete ne denir?", ["İtki", "Sürtünme", "Ağırlık"], 0)]},
 {"id": "bilgisayar", "ad": "Bilgisayar", "kat": "Teknoloji", "ikon": "💻",
  "ozet": "Bilgisayar her şeyi 0 ve 1'lere çevirir; işlemci milyarlarca minik anahtarla bunlar üzerinde çok hızlı hesap yapar.",
  "benzetme": "Mutfaktaki aşçı (işlemci), tezgâh (RAM) ve kiler (disk) gibi: malzeme kilerden tezgâha gelir, aşçı orada çalışır.",
  "adim": [("Her şey 0 ve 1", "Yazı, resim, ses: hepsi sayılara, sayılar da 0 ve 1'lerden oluşan bitlere çevrilir."),
           ("Transistörler anahtardır", "İşlemcide milyarlarca transistör vardır; her biri açık (1) ya da kapalı (0) olan minik bir elektrik anahtarıdır."),
           ("Disk saklar", "Programlar ve dosyalar, elektrik kesilse de silinmeyen diskte (SSD) durur."),
           ("RAM çalışma masasıdır", "Bir program açılınca hızlı erişim için RAM'e yüklenir. RAM hızlıdır ama elektrik gidince boşalır."),
           ("İşlemci komutları yürütür", "İşlemci RAM'den komutları sırayla alır, hesaplar ve sonucu ekrana, hoparlöre ya da diske gönderir; bunu saniyede milyarlarca kez yapar.")],
  "bilgi": "Bir işlemcideki transistörler o kadar küçüktür ki bir saç telinin kalınlığına binlercesi sığar.",
  "soru": [_q("Elektrik kesilince içeriği silinen bellek hangisi?", ["Disk (SSD)", "RAM", "USB bellek"], 1),
           _q("Transistör neye benzer?", ["Açılıp kapanan bir anahtara", "Bir pile", "Bir hoparlöre"], 0)]},
 {"id": "asi", "ad": "Aşı", "kat": "Vücut", "ikon": "💉",
  "ozet": "Aşı, bağışıklık sistemine mikrobun zararsız bir 'fotoğrafını' gösterip gerçeğiyle karşılaşmadan önce hazırlık yaptırır.",
  "benzetme": "Yangın tatbikatı gibi: gerçek yangın çıkmadan herkes ne yapacağını öğrenir, gerçeğinde hızlı davranır.",
  "adim": [("Zararsız örnek verilir", "Aşı, mikrobun öldürülmüş ya da zayıflatılmış hâlini veya yalnızca bir parçasının tarifini içerir; hastalık yapmaz."),
           ("Bağışıklık fark eder", "Akyuvarlar bu yabancı parçayı (antijen) tanır ve alarm verir."),
           ("Antikor üretilir", "B hücreleri bu mikroba özel antikorlar üretmeyi öğrenir. Hafif ateş ya da kol ağrısı bu çalışmanın işaretidir."),
           ("Hafıza hücreleri kalır", "Bazı hücreler 'hafıza hücresi' olarak yıllarca vücutta kalır ve mikrobu hatırlar."),
           ("Gerçek mikrop yenilir", "Gerçek mikrop gelince vücut onu hemen tanır ve hastalık başlamadan hızla yok eder.")],
  "bilgi": "Çok kişi aşılanınca mikrop yayılacak kişi bulamaz; bu 'toplum bağışıklığı' aşı olamayan bebekleri de korur.",
  "soru": [_q("Aşı vücuda ne öğretir?", ["Mikrobu tanımayı", "Daha hızlı büyümeyi", "Ateşi düşürmeyi"], 0),
           _q("Mikrobu yıllarca hatırlayan hücreler hangileri?", ["Kırmızı kan hücreleri", "Hafıza hücreleri", "Sinir hücreleri"], 1)]},
 {"id": "yazici3d", "ad": "3D yazıcı", "kat": "Teknoloji", "ikon": "🖨️",
  "ozet": "3D yazıcı, eritilmiş plastiği ince katmanlar hâlinde üst üste dökerek nesneyi alttan yukarı inşa eder.",
  "benzetme": "Pastanın üstüne krema sıkmak gibi, ama yüzlerce katı üst üste koyarak bir heykel yapmak.",
  "adim": [("3B model çizilir", "Nesne bilgisayarda üç boyutlu olarak tasarlanır ya da hazır bir model indirilir."),
           ("Dilimlenir", "Dilimleyici program modeli 0,1-0,3 mm kalınlığında yüzlerce yatay katmana böler ve yazıcıya yol tarifi çıkarır."),
           ("Plastik erir", "Makaradaki plastik tel (PLA) yaklaşık 200 °C'ye ısınan uçta erir."),
           ("Katman katman çizer", "Uç, tarif edilen yolda gezerek ilk katmanı çizer; sonra tabla biraz iner ve sıradaki katman üstüne dökülür."),
           ("Soğur ve sertleşir", "Her katman hemen soğuyup bir öncekine yapışır; saatler sonra nesne tamamlanır.")],
  "bilgi": "Bugün 3D yazıcılarla protez eller, ev duvarları ve hatta roket motoru parçaları basılıyor.",
  "soru": [_q("3D yazıcı nesneyi nasıl oluşturur?", ["Kalıba dökerek", "Katman katman üst üste", "Bloğu oyarak"], 1),
           _q("Modeli katmanlara bölen program hangisi?", ["Dilimleyici", "Antivirüs", "Tarayıcı"], 0)]},
 {"id": "deprem", "ad": "Deprem", "kat": "Doğa", "ikon": "🌋",
  "ozet": "Yer kabuğunun parçaları (levhalar) birbirine sürtünerek gerilim biriktirir; gerilim aniden boşalınca yer sallanır.",
  "benzetme": "Cetveli iki elinle bükmek gibi: bir süre dayanır, sonra birden kırılır ve titrer.",
  "adim": [("Levhalar hareket eder", "Yer kabuğu, yılda birkaç santimetre hareket eden dev levhalardan oluşur."),
           ("Fay takılır", "İki levhanın sınırındaki fay hattında kayalar sürtünmeyle birbirine takılır."),
           ("Gerilim birikir", "Levhalar hareket etmeye devam ettikçe kayalar bükülür ve yıllarca enerji biriktirir."),
           ("Ani kırılma", "Gerilim kayaların dayanımını aşınca fay birden kayar; biriken enerji saniyeler içinde boşalır."),
           ("Dalgalar yayılır", "Enerji sismik dalgalar olarak her yöne yayılır; önce hızlı P dalgaları, sonra daha yıkıcı S ve yüzey dalgaları gelir.")],
  "bilgi": "Türkiye; Kuzey Anadolu ve Doğu Anadolu fayları üzerinde, Avrasya, Afrika ve Arap levhalarının sıkıştırdığı bir bölgededir.",
  "soru": [_q("Depremde biriken enerji nerede boşalır?", ["Fay hattında", "Okyanusun ortasında", "Atmosferde"], 0),
           _q("İlk ulaşan hızlı dalgalar hangileri?", ["S dalgaları", "P dalgaları", "Yüzey dalgaları"], 1)]},
 {"id": "gokkusagi", "ad": "Gökkuşağı", "kat": "Doğa", "ikon": "🌈",
  "ozet": "Güneş ışığı yağmur damlalarına girerken kırılır, içinde yansır, çıkarken renklerine ayrılır.",
  "benzetme": "Prizmadan geçen beyaz ışığın renklere ayrılması gibi; her yağmur damlası minik bir prizmadır.",
  "adim": [("Beyaz ışık karışımdır", "Güneş ışığı aslında tüm renklerin karışımıdır."),
           ("Damlaya girerken kırılır", "Işık su damlasına girerken yön değiştirir (kırılır); her renk biraz farklı açıyla kırılır."),
           ("İçeride yansır", "Işık damlanın arka yüzüne çarpıp geri yansır."),
           ("Çıkarken ayrışır", "Damladan çıkarken bir kez daha kırılır; renkler iyice ayrılır. Kırmızı en az, mor en çok sapar."),
           ("Doğru açıdan görülür", "Güneş arkanda, yağmur önündeyken yaklaşık 42 derecelik açıdan gelen ışığı görürsün; bu yüzden gökkuşağı bir yay şeklindedir.")],
  "bilgi": "Uçaktan bakınca gökkuşağı yay değil tam bir daire olarak görülebilir; yerde ufuk yarısını keser.",
  "soru": [_q("Gökkuşağını görmek için güneş nerede olmalı?", ["Önünde", "Arkanda", "Tam tepende"], 1),
           _q("Işığın damlaya girerken yön değiştirmesine ne denir?", ["Kırılma", "Erime", "Buharlaşma"], 0)]},
]
BY_ID = {t["id"]: t for t in TOPICS}
CATS = ["Ev", "Teknoloji", "Enerji", "Ulaşım", "Vücut", "Doğa", "Yapay zekâ"]


def _load_cache() -> dict:
    try:
        with open(FILE, encoding="utf-8") as f:
            d = json.load(f)
        return {k: v for k, v in d.items() if isinstance(v, dict) and v.get("adim")} if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_cache(d: dict) -> None:
    items = dict(list(d.items())[-40:])                   # en son 40 üretilen konu
    with open(FILE + ".tmp", "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    os.replace(FILE + ".tmp", FILE)


def get(i: str):
    return BY_ID.get(i) or _load_cache().get(i)


def all_topics() -> list:
    out = [{"id": t["id"], "ad": t["ad"], "kat": t["kat"], "ikon": t["ikon"]} for t in TOPICS]
    out += [{"id": k, "ad": v["ad"], "kat": "Yapay zekâ", "ikon": v.get("ikon") or "✨"} for k, v in _load_cache().items()]
    return out


def _key(s: str) -> str:
    s = s.lower().replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")
    return re.sub(r"[^a-z0-9]+", "", s)[:30] or "konu"


_ALIASES = {"buzdolabi": r"buzdolab|dolap soğut|soğutucu", "mikrodalga": r"mikrodalga", "dokunmatik": r"dokunmatik|ekran dokun|telefon ekran",
            "gps": r"\bgps\b|konum bul|navigasyon|uydu konum", "internet": r"internet|web sayfa|site nasıl", "wifi": r"wi ?fi|kablosuz|vay ?fay",
            "gunespaneli": r"güneş panel|güneş enerji|solar", "motor": r"elektrik motor|motor nasıl|\bmotor\b", "ucak": r"uçak|kanat",
            "bilgisayar": r"bilgisayar|işlemci", "asi": r"\başı\b|aşılar|aşının|aşıyı", "yazici3d": r"3 ?d yazıcı|üç boyutlu yazıcı|3d printer",
            "deprem": r"deprem|fay hatt", "gokkusagi": r"gökkuşağı|gök kuşağı"}


def find(q: str):
    """Yerleşik ya da önbellekteki konuyu bulur; yoksa None."""
    q = q.lower()
    for i, pat in _ALIASES.items():
        if re.search(pat, q):
            return BY_ID[i]
    for k, v in _load_cache().items():
        if v["ad"].lower() in q or _key(q) == k:
            return v
    return None


def snapshot() -> dict:
    t = get(S["id"]) if S["id"] else None
    return {"topics": all_topics(), "cats": CATS, "cur": t, "step": S["step"], "q": S["q"], "busy": S["busy"], "score": S["score"]}


def select(t: dict, step: int = -1) -> None:
    S.update(id=t["id"], step=step, q=-1)


# ------------------------------------------------------------------ yapay zekâ ile yeni konu
_PROMPT = """Bir 9. sınıf öğrencisine "{konu}" nasıl çalışır, Türkçe ve bilimsel olarak DOĞRU biçimde anlat. Emin olmadığın sayı ya da tarih yazma.
YALNIZCA şu JSON'u döndür, başka hiçbir şey yazma:
{{"ad": "kısa konu adı", "ikon": "tek emoji", "ozet": "tek cümle özet", "benzetme": "günlük hayattan tek cümlelik benzetme",
"adim": [["kısa başlık (en çok 4 kelime)", "1-2 cümle açıklama"], ... toplam 5 adım, oluş sırasına göre],
"bilgi": "ilginç ve doğru tek bir bilgi",
"soru": [{{"q": "soru", "s": ["şık", "şık", "şık"], "c": doğru şıkkın 0-2 sırası}}, {{"q": "...", "s": ["...", "...", "..."], "c": 0}}]}}"""


def _valid(d) -> bool:
    try:
        ok = isinstance(d, dict) and d.get("ad") and d.get("ozet") and isinstance(d.get("adim"), list) and 3 <= len(d["adim"]) <= 8
        ok = ok and all(isinstance(a, (list, tuple)) and len(a) == 2 and all(isinstance(x, str) and x.strip() for x in a) for a in d["adim"])
        d["soru"] = [q for q in d.get("soru") or [] if isinstance(q, dict) and q.get("q") and isinstance(q.get("s"), list) and len(q["s"]) == 3
                     and isinstance(q.get("c"), int) and 0 <= q["c"] <= 2]
        return bool(ok)
    except Exception:
        return False


def _generate(konu: str) -> None:
    import ders_ai
    d = None
    for _ in range(2):
        d = ders_ai._json(ders_ai._llm(_PROMPT.format(konu=konu), num_predict=1400, temp=0.3, urgent_call=True))
        if _valid(d):
            break
        d = None
    S["busy"] = ""
    if not d:
        if NOTIFY:
            NOTIFY({"snap": snapshot()}, f"Üzgünüm efendim, {konu} için güvenilir bir anlatım hazırlayamadım. Başka türlü sormayı deneyin.")
        return
    k = _key(d["ad"])
    d.update(id=k, kat="Yapay zekâ", ai=True, ikon=(d.get("ikon") or "✨")[:2], adim=[list(a) for a in d["adim"]], bilgi=d.get("bilgi") or "")
    with _lock:
        c = _load_cache()
        c.pop(k, None)
        c[k] = d
        _save_cache(c)
    select(d)
    if NOTIFY:
        NOTIFY({"snap": snapshot()}, f"{d['ad']} hazır efendim. {d['ozet']} Başla derseniz adım adım anlatırım. Bu anlatımı yapay zekâ üretti, hata olabilir.")


def generate(konu: str) -> bool:
    """Arka planda üretimi başlatır; zaten bir üretim sürüyorsa False."""
    if S["busy"]:
        return False
    S["busy"] = konu
    threading.Thread(target=_generate, args=(konu,), daemon=True).start()
    return True


def forget(i: str) -> bool:
    with _lock:
        c = _load_cache()
        if i not in c:
            return False
        c.pop(i)
        _save_cache(c)
    if S["id"] == i:
        S.update(id=None, step=-1, q=-1)
    return True
