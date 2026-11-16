"""Biyoloji laboratuvarı verisi: hücreler, organeller, vücut sistemleri, deneyler, genetik (Punnett, DNA->protein), sınıflandırma."""
import itertools, random, re
from collections import Counter

# ------------------------------------------------------------------ ORGANELLER
ORG = {
    "membrane": ("Hücre zarı", "Hücreyi çevreler ve madde giriş-çıkışını kontrol eder (seçici geçirgen). Fosfolipit çift katman ve içine gömülü proteinlerden oluşur (akışkan mozaik modeli).", "Yağda çözünen küçük moleküller zardan kolay geçer; iyonlar ve büyük moleküller taşıyıcı proteinlere ihtiyaç duyar."),
    "cytoplasm": ("Sitoplazma", "Organellerin içinde yüzdüğü jelimsi sıvı. Birçok kimyasal tepkime burada olur, glikoz yıkımının ilk basamağı (glikoliz) burada gerçekleşir.", "Sitoplazma sürekli hareket eder; buna sitoplazmik akış denir."),
    "nucleus": ("Çekirdek", "DNA'yı barındırır; hücre faaliyetlerini ve kalıtımı yönetir. Çift zarlıdır ve zarında gözenekler vardır.", "Her insan hücresindeki DNA açılsa yaklaşık iki metre uzunluğundadır."),
    "nucleolus": ("Çekirdekçik", "Ribozomları oluşturan rRNA'yı üretir ve ribozom alt birimlerini bir araya getirir.", "Çok protein üreten hücrelerde çekirdekçik daha belirgindir."),
    "mito": ("Mitokondri", "Hücresel solunumla besinden ATP (hücrenin enerji parası) üretir. Çift zarlıdır; iç zarı kristalarla kıvrımlıdır.", "Kendi DNA'sı vardır ve insanda yalnızca anneden gelir. Kas hücrelerinde çok sayıdadır."),
    "er": ("Endoplazmik retikulum", "Kanalcık ağıdır. Pürüzlü ER'nin üzerinde ribozom olup protein sentezler; düz ER lipit üretir, zehirli maddeleri etkisizleştirir ve kalsiyum depolar.", "Karaciğer hücrelerinde düz ER bol bulunur; zehirsizleştirmeden sorumludur."),
    "ribosome": ("Ribozom", "mRNA'daki bilgiyi okuyup amino asitleri bağlayarak protein sentezler. Zarsızdır; tüm hücrelerde bulunur.", "Bakterilerde ribozomlar küçüktür; bazı antibiyotikler yalnızca bakteri ribozomunu engeller."),
    "golgi": ("Golgi aygıtı", "Proteinleri ve lipitleri değiştirir, paketler ve hücre içinde ya da dışına gönderir (salgılar).", "Adını 1898'de keşfeden İtalyan bilim insanı Camillo Golgi'den alır."),
    "lysosome": ("Lizozom", "Sindirim enzimleri içerir; besin parçacıklarını, yaşlı organelleri ve mikropları parçalar.", "Enzimleri hücreyi kendi kendine sindirmesin diye zarla kapalı tutulur."),
    "vacuole": ("Koful (vakuol)", "Su, besin ve atık depolar. Bitki hücresinde büyük ve merkezidir; turgor basıncıyla bitkiyi dik tutar.", "Susuz kalan bitki, kofullar boşalınca solar."),
    "chloroplast": ("Kloroplast", "Fotosentez yapar: ışık enerjisiyle karbondioksit ve sudan glikoz ve oksijen üretir. İçinde klorofil taşıyan granalar ve stroma bulunur.", "Kendi DNA'sı vardır; endosimbiyoz kuramına göre eskiden bağımsız siyanobakteriydi."),
    "cellwall": ("Hücre duvarı", "Bitkilerde selülozdan, mantarlarda kitinden, bakterilerde peptidoglikandan oluşan sert dış yapı; şekil ve destek verir.", "Hücre duvarı hayvan hücrelerinde yoktur."),
    "centrosome": ("Sentrozom (sentriyol)", "Hücre bölünmesinde iğ ipliklerini düzenler. Hayvan hücrelerinde iki dik sentriyolden oluşur.", "Bitki hücrelerinde (çoğunlukla) sentriyol bulunmaz."),
    "nucleoid": ("Nükleoid", "Bakterinin halkasal kromozomunun bulunduğu bölge. Çekirdek zarı yoktur.", "Bakteri DNA'sı tek halkasal kromozomdur."),
    "plasmid": ("Plazmit", "Kromozomdan ayrı küçük halkasal DNA. Antibiyotik direnci gibi genler taşıyabilir.", "Genetik mühendisliğinde gen taşıyıcısı olarak kullanılır."),
    "flagellum": ("Kamçı (flagellum)", "Bakteriyi döndürerek hareket ettiren ipliksi yapı.", "Bazı bakteriler saniyede kendi boylarının onlarca katı yol alabilir."),
    "capsule": ("Kapsül", "Bazı bakterileri saran koruyucu şekerli tabaka; bağışıklık sisteminden kaçmaya ve yüzeye yapışmaya yardım eder.", ""),
    "pili": ("Pilus (fimbria)", "Yüzeye tutunmayı sağlar; özel pilusla bakteriler arasında DNA aktarımı (konjügasyon) olur.", ""),
}
CELLS = {
    "animal": {"name": "Hayvan hücresi", "intro": "Ökaryot hücre: zarlı çekirdek ve organeller vardır. Hücre duvarı ve kloroplast yoktur.",
               "parts": [("membrane", 0, 0, 1), ("cytoplasm", 0, 0, 1), ("nucleus", 0, -6, 1), ("nucleolus", 0, -6, 1), ("er", -34, -8, 1), ("mito", -58, 26, 1), ("mito", 52, 34, 1), ("mito", 40, -42, 1), ("golgi", 52, -6, 1),
                         ("lysosome", -50, -44, 1), ("lysosome", 20, 46, 1), ("lysosome", -20, 40, 1), ("centrosome", -52, -14, 1), ("vacuole", 62, 18, .6), ("ribosome", 0, 0, 1)]},
    "plant": {"name": "Bitki hücresi", "intro": "Ökaryot hücre: hücre duvarı, kloroplastlar ve büyük merkezi koful ile hayvan hücresinden ayrılır.",
              "parts": [("cellwall", 0, 0, 1), ("membrane", 0, 0, 1), ("cytoplasm", 0, 0, 1), ("vacuole", 8, 8, 1.6), ("nucleus", -52, -30, .9), ("nucleolus", -52, -30, .9), ("chloroplast", -62, 30, 1), ("chloroplast", 58, -32, 1), ("chloroplast", 62, 36, 1),
                        ("chloroplast", -10, -50, 1), ("mito", -30, 42, .9), ("mito", 76, 0, .8), ("er", -76, -4, .9), ("golgi", 24, -52, .9), ("ribosome", 0, 0, 1)]},
    "bacteria": {"name": "Bakteri hücresi", "intro": "Prokaryot hücre: zarlı çekirdek ve zarlı organeller yoktur. DNA sitoplazmada nükleoidde bulunur.",
                 "parts": [("capsule", 0, 0, 1), ("cellwall", 0, 0, 1), ("membrane", 0, 0, 1), ("cytoplasm", 0, 0, 1), ("nucleoid", -6, 0, 1), ("plasmid", 48, -14, 1), ("plasmid", 40, 20, .8), ("ribosome", 0, 0, 1), ("flagellum", 88, 0, 1), ("pili", -70, 0, 1)]},
}

# ------------------------------------------------------------------ SİSTEMLER
SYSTEMS = [
    {"key": "dolasim", "name": "Dolaşım sistemi", "anim": "heart", "organs": "kalp, atardamarlar, toplardamarlar, kılcal damarlar, kan",
     "function": "Kan yoluyla oksijen, besin, hormon ve atıkları taşır; vücut ısısını dengeler.",
     "facts": ["Kalp dinlenme halinde dakikada yaklaşık 60-100 kez atar; günde yaklaşık 100 bin kez.", "Kan damarlarının toplam uzunluğu yaklaşık 100 bin kilometredir, Dünya'yı iki buçuk kez dolaşır.", "Kırmızı kan hücreleri yaklaşık 120 gün yaşar; kemik iliğinde sürekli yenilenir.", "Kalp dört odacıklıdır: iki kulakçık, iki karıncık. Kan akciğerlere gidip temizlenerek geri döner."]},
    {"key": "solunum", "name": "Solunum sistemi", "anim": "lungs", "organs": "burun, soluk borusu, bronşlar, akciğerler, alveoller, diyafram",
     "function": "Havadaki oksijeni kana verir, kandaki karbondioksiti dışarı atar.",
     "facts": ["Akciğerlerde yüzlerce milyon alveol vardır; açılsa yüzey alanı bir tenis kortu kadar olur.", "Nefes alırken diyafram kasılıp aşağı iner, göğüs boşluğu genişler ve hava içeri girer.", "Dinlenirken dakikada yaklaşık 12-20 nefes alırız.", "Kandaki karbondioksit miktarı, beynin solunum merkezini uyararak nefes hızını ayarlar."]},
    {"key": "sindirim", "name": "Sindirim sistemi", "anim": "gut", "organs": "ağız, yemek borusu, mide, ince bağırsak, kalın bağırsak, karaciğer, pankreas, safra kesesi",
     "function": "Besinleri parçalar, besin öğelerini kana geçirir, artıkları atar.",
     "facts": ["Mide asidinin pH değeri yaklaşık 1,5-3,5'tir; protein sindirimini başlatır.", "İnce bağırsak yaklaşık 6-7 metre uzunluğundadır; emilim bol sayıdaki villuslarla gerçekleşir.", "Sindirim ağızda tükürük amilaziyle nişasta parçalanmasıyla başlar.", "Karaciğer safra üretir; safra yağların sindirimine yardım eder."]},
    {"key": "sinir", "name": "Sinir sistemi", "anim": "neuron", "organs": "beyin, omurilik, sinirler, duyu organları",
     "function": "Elektriksel ve kimyasal sinyallerle vücudu denetler ve çevreyi algılamayı sağlar.",
     "facts": ["Sinir hücreleri (nöronlar) sinyali saniyede yaklaşık 1 ile 120 metre hızla iletir.", "İnsan beyninde yaklaşık 86 milyar nöron vardır.", "İki nöron arasında sinaps denilen boşluktan nörotransmitter maddelerle sinyal geçer.", "Refleksler beyne uğramadan omurilikte işlenir, bu yüzden çok hızlıdır."]},
    {"key": "bosaltim", "name": "Boşaltım sistemi", "anim": "kidney", "organs": "böbrekler, idrar kanalları, idrar kesesi",
     "function": "Kanı süzer, atıkları ve fazla suyu idrarla atar; su-tuz dengesini ve kan pH'ını korur.",
     "facts": ["Böbrekler günde yaklaşık 180 litre kanı süzer, bunun yaklaşık 1,5 litresi idrar olur.", "Her böbrekte yaklaşık bir milyon nefron (süzme birimi) vardır.", "Vücudumuz kütlece yaklaşık yüzde 60 sudur.", "Terleme ve solunum da atık atılmasına katkı sağlar."]},
    {"key": "endokrin", "name": "Endokrin (hormon) sistemi", "anim": "pulse", "organs": "hipofiz, tiroit, pankreas, böbrek üstü bezleri, yumurtalık ve testis",
     "function": "Hormonlarla büyüme, metabolizma, kan şekeri ve üreme gibi uzun süreli işleri düzenler.",
     "facts": ["Pankreastan salgılanan insülin kandaki glikoz miktarını düşürür; yetersizliği şeker hastalığına yol açar.", "Hipofiz 'ana bez' olarak bilinir; birçok bezi yönetir.", "Adrenalin, böbrek üstü bezlerinden gelir ve 'savaş ya da kaç' tepkisini hazırlar.", "Hormonlar kan yoluyla taşınır, sadece hedef hücrelerdeki reseptörlere etki eder."]},
    {"key": "iskelet", "name": "Kas ve iskelet sistemi", "anim": "pulse", "organs": "kemikler, eklemler, kaslar, tendonlar",
     "function": "Vücuda şekil ve destek verir, organları korur, hareketi sağlar; kemik iliği kan hücrelerini üretir.",
     "facts": ["Bir yetişkinde yaklaşık 206 kemik, 600'den fazla iskelet kası bulunur.", "Vücudun en uzun kemiği uyluk kemiğidir (femur).", "Kemikler canlı dokudur ve sürekli yenilenir.", "Kaslar çiftler halinde çalışır: biri kasılırken diğeri gevşer."]},
    {"key": "bagisiklik", "name": "Bağışıklık sistemi", "anim": "pulse", "organs": "akyuvarlar, lenf düğümleri, dalak, timüs, kemik iliği",
     "function": "Mikropları (bakteri, virüs, parazit) tanır ve yok eder; hastalıklara karşı hafıza oluşturur.",
     "facts": ["Aşılar, hastalığa yol açmadan bağışıklık hafızası oluşturur.", "Akyuvarlar (lökositler) vücudun savunma hücreleridir.", "Antikorlar, belirli mikroplara bağlanan Y biçimli proteinlerdir.", "Cilt ve mukus ilk savunma hattıdır."]},
    {"key": "duyu", "name": "Duyu organları", "anim": "pulse", "organs": "göz, kulak, burun, dil, deri",
     "function": "Işık, ses, koku, tat ve dokunmayı elektrik sinyallerine çevirip beyne gönderir.",
     "facts": ["Gözde ışığa duyarlı çubuk ve koni hücreleri bulunur; koniler renkleri algılar.", "Tat tomurcukları dilde ve ağızda bulunur; tatlı, ekşi, tuzlu, acı ve umami olmak üzere beş temel tat vardır.", "Her göz görüntüyü ters çevirir; beyin bunu düzeltir.", "Deri, vücudun en büyük organıdır."]},
]

# ------------------------------------------------------------------ DENEYLER
def _x(key, name, level, mins, anim, aim, mats, steps, observe, why, safety):
    return {"key": key, "name": name, "level": level, "mins": mins, "anim": anim, "aim": aim, "mats": mats, "steps": steps, "observe": observe, "why": why, "safety": safety}


EXPERIMENTS = [
    _x("sogan", "Soğan zarı ve hücreler", "Orta", 20, "onion", "Bitki hücrelerini mikroskopla görmek.",
       ["Soğan", "Mikroskop, lam ve lamel", "Damlalık, su", "İyot tentürü (seyreltik)", "Cımbız"],
       ["Soğanın iç katmanından ince, şeffaf zarı cımbızla soyun.", "Lam üzerine bir damla su koyup zarı yatırın ve lamelle üstünü kapatın.", "Küçük büyütmede inceleyin, sonra bir damla seyreltik iyotla boyayın."],
       "Dikdörtgen hücreler, hücre duvarı ve koyu boyanan çekirdek görülür.", "İyot, nişasta ve çekirdeği boyayarak yapıları belirginleştirir. Soğanın alt zarı yeşil kısım yok, çünkü kök kısmı kloroplast içermez.", "Cımbız ve lameller kırılabilir. İyotu yutmayın, cildinizi lekeleyebilir."),
    _x("plazmoliz", "Plazmoliz: hücre büzüşür", "Orta", 20, "plasmolysis", "Ozmozla hücreden su çıkışını görmek.",
       ["Soğan zarı ya da su bitkisi (Elodea)", "Mikroskop", "Tuzlu su (yüzde 5-10)", "Saf su"],
       ["Zarı suda gözleyin.", "Zarın üzerine tuzlu su damlatın.", "Birkaç dakika sonra tekrar gözleyin, sonra saf suyla yıkayın."],
       "Hücre zarı duvardan ayrılıp içe çekilir; saf suyla yıkanınca geri döner.", "Dışarısı daha derişikse su, hücreden dışarı ozmozla çıkar; sitoplazma küçülür (plazmoliz). Saf suda su geri girer (deplazmoliz).", "Tuzlu su hücreleri öldürürse geri dönmeyebilir. Lamelleri dikkatli tutun."),
    _x("patates", "Patates ozmozu", "Kolay", 40, "osmosis", "Su geçişinin derişime bağlı olduğunu ölçmek.",
       ["Patates", "Üç kap", "Saf su, hafif tuzlu su, çok tuzlu su", "Terazi", "Cetvel"],
       ["Aynı boyda patates çubukları kesin, tartın.", "Her çubuğu bir kaba koyun.", "Bir saat sonra çıkarıp kurulayın ve yeniden tartın."],
       "Saf suda çubuk şişer ve sertleşir, çok tuzlu suda küçülür ve yumuşar.", "Su, derişimin düşük olduğu yerden yüksek olduğu yere hücre zarından geçer (ozmoz).", "Keskin bıçağı yetişkin kullansın."),
    _x("dna", "Çilekten DNA özütleme", "Orta", 30, "dna", "DNA'yı gözle görülür hale getirmek.",
       ["Çilek (olgun)", "Zip poşet", "Bulaşık deterjanı, tuz, su", "Süzgeç ya da kahve filtresi", "Soğuk alkol (eczane, yüzde 70 üstü)", "Şeffaf bardak"],
       ["Çileği poşette ezin.", "Deterjan, tuz ve suyla hazırladığınız çözeltiyi ekleyip karıştırın.", "Karışımı süzüp bardağa alın.", "Soğuk alkolü bardağın kenarından yavaşça ekleyin; katmanlar karışmasın."],
       "Alkol katmanında beyaz, ipliksi, bulutsu bir yumak (DNA) belirir.", "Deterjan hücre zarlarını eritir, tuz DNA'yı bir arada tutar, DNA alkolde çözünmez ve çöker.", "Alkol yanıcıdır, ateşten uzak tutun, içmeyin. Yetişkin gözetiminde yapın."),
    _x("maya", "Maya mantarı ve balon", "Kolay", 30, "yeast", "Fermantasyonla gaz oluşumunu görmek.",
       ["Kuru maya", "Şeker", "Ilık su", "Şişe", "Balon"],
       ["Şişeye ılık su, bir kaşık şeker ve bir paket maya koyup karıştırın.", "Balonu şişenin ağzına geçirin.", "Bir süre bekleyin."],
       "Balon karbondioksitle şişer, maya kokusu gelir.", "Maya şekeri oksijensiz solunumla (fermantasyon) alkol ve karbondioksite çevirir; gaz balonu şişirir.", "Su kaynar sıcaklıkta olmasın; maya ölür. Güvenli."),
    _x("kereviz", "Kerevizle bitkide su taşınması", "Kolay", 20, "celery", "Bitkinin su ve mineral taşıma dokusunu görmek.",
       ["Kereviz sapı ya da beyaz karanfil", "Gıda boyası", "Su, bardak"],
       ["Boyalı su hazırlayın ve sapı içine koyun.", "Birkaç saat ya da bir gece bekleyin.", "Sapı enine kesip bakın."],
       "Sap boyunca renkli çizgiler ve kesitte renkli noktalar oluşur.", "Su, odunsu borulardan (ksilem) kılcallık ve yapraktan terleme çekimiyle yukarı çıkar.", "Boya kıyafete leke yapar."),
    _x("fasulye", "Fasulyenin çimlenmesi", "Kolay", 15, "germ", "Çimlenmenin koşullarını anlamak.",
       ["Kuru fasulye", "Pamuk", "Kavanoz", "Su"],
       ["Kavanozu ıslak pamukla doldurun, fasulyeleri yerleştirin.", "Işık alan bir yere koyun, pamuğu nemli tutun.", "Her gün ölçüp not edin."],
       "Önce kök, sonra gövde ve yapraklar çıkar.", "Çimlenme için su, uygun sıcaklık ve oksijen gerekir; ışık yaprakların yeşillenmesi için önemlidir.", "Güvenli. Küf oluşursa atın."),
    _x("foto", "Bitki ışığa yönelir (fototropizm)", "Kolay", 20, "photo", "Bitkilerin ışığa tepkisini görmek.",
       ["Çimlenmiş küçük bitki", "Karton kutu", "Kutuya bir pencere"],
       ["Bitkiyi kutuya koyup yalnız yan taraftaki küçük delikten ışık gelmesini sağlayın.", "Birkaç gün bekleyip bakın."],
       "Gövde ışığa doğru eğilir.", "Işıktan uzak tarafta oksin hormonu birikir, o taraftaki hücreler uzar ve gövde ışığa doğru bükülür.", "Güvenli."),
    _x("nisasta", "Besinlerde nişasta testi", "Kolay", 10, "bubbles", "Nişastayı iyotla tanımak.",
       ["Ekmek, patates, elma, peynir", "Seyreltik iyot çözeltisi", "Damlalık"],
       ["Besin parçalarına birer damla iyot damlatın."],
       "Nişastalı besinler mavi-siyaha döner.", "İyot, nişasta zincirinin içine girip özel mavi-mor bir kompleks yapar.", "İyot cildi boyar; yutmayın."),
    _x("enzim", "Meyve enzimi ve jelatin", "Kolay", 40, "enzyme", "Enzimlerin proteini parçaladığını görmek.",
       ["Taze kivi ya da ananas", "Konserve ananas", "Jelatin", "Kaplar"],
       ["Jelatin hazırlayıp dondurun.", "Taze meyve ve konserve meyveyi jelatinin üstüne koyun.", "Bir süre bekleyin."],
       "Taze meyvenin altındaki jelatin sulanır, konservede kalmaz.", "Taze kivi ve ananas proteini parçalayan enzimler (proteaz) içerir; konserve ısıl işlemle bu enzimleri kaybeder.", "Alerjiniz varsa meyveyi yemeyin."),
    _x("stoma", "Yaprak gözenekleri (stoma)", "İleri", 30, "bubbles", "Yaprağın alt yüzündeki stomaları görmek.",
       ["Yaprak (ör. sardunya)", "Şeffaf oje", "Şeffaf bant", "Mikroskop"],
       ["Yaprağın alt yüzüne ince bir tabaka oje sürüp kurutun.", "Şeffaf bantla ojeyi soyup lam üzerine alın.", "Mikroskopla inceleyin."],
       "Fasulye benzeri bekçi hücrelerle çevrili gözenekler görülür.", "Stomalar gaz alışverişini ve terlemeyi düzenler; bekçi hücrelerinin şişip sönmesiyle açılıp kapanır.", "Oje yanıcı ve kokuludur; havalandırın."),
    _x("nabiz", "Nabız ve egzersiz", "Kolay", 10, "heart", "Egzersizin kalp atış hızına etkisini ölçmek.",
       ["Saat ya da kronometre"],
       ["Dinlenirken bileğinizde 30 saniye nabzı sayıp ikiyle çarpın.", "Bir dakika yerinde zıplayın ve tekrar ölçün.", "Dinlenme sürelerini kaydedin."],
       "Egzersizden sonra nabız belirgin artar ve birkaç dakikada normale döner.", "Kaslar daha çok oksijene ihtiyaç duyar; kalp daha hızlı atarak kanı hızlandırır.", "Rahatsızlığınız varsa egzersiz yapmayın."),
    _x("reaksiyon", "Reaksiyon süresi (cetvel testi)", "Kolay", 10, "ruler", "Sinir sisteminin tepki hızını ölçmek.",
       ["30 cm'lik cetvel", "Arkadaş"],
       ["Arkadaşınız cetveli dikey tutup bırakır.", "Siz parmaklarınızla yakalayın.", "Cetvelin düştüğü mesafeyi okuyun."],
       "Ortalama tepki süresi yaklaşık 0,2 saniyedir.", "Görme, beyne iletim, karar ve kas kasılması zinciri birkaç yüz milisaniye sürer.", "Güvenli."),
    _x("korNokta", "Kör nokta testi", "Kolay", 5, "bubbles", "Gözdeki kör noktayı bulmak.",
       ["Kağıt", "Kalem"],
       ["Kağıda sol tarafa artı, sağa yaklaşık 8 cm uzağa bir nokta çizin.", "Sol gözünüzü kapatıp sağ gözle artıya bakarken kağıdı yavaş yavaş yaklaştırın."],
       "Belli bir mesafede nokta kaybolur.", "Görme siniri retinadan ayrıldığı yerde ışık algılayan hücre yoktur; beyin boşluğu çevreye bakarak doldurur.", "Güvenli."),
    _x("parmakizi", "Parmak izini incelemek", "Kolay", 10, "bubbles", "Parmak izi desenlerini sınıflandırmak.",
       ["Kurşun kalem", "Şeffaf bant", "Beyaz kağıt", "Büyüteç"],
       ["Kalemle kağıda koyu bir leke çizin, parmağınızı lekeye bastırın.", "Parmağa bandı yapıştırıp kaldırın, beyaz kağıda yapıştırın.", "Desenlere bakın: ilmek, kemer, girdap."],
       "Her insanın parmak izi farklıdır; ikizlerde bile aynı değildir.", "Parmak izi, cildin kabartılı desenleridir ve anne karnında oluşur; yaşam boyu değişmez.", "Güvenli."),
    _x("elodea", "Su bitkisiyle fotosentez", "Orta", 30, "photosyn", "Işıkta oksijen üretildiğini görmek.",
       ["Elodea ya da akvaryum bitkisi", "Cam kap, su", "Karbonat (az kabartma tozu)", "Lamba", "Kronometre"],
       ["Bitkiyi suya ters çevrilmiş huni altına koyun, suya bir tutam kabartma tozu ekleyin.", "Lambayı yaklaştırıp bir dakikada çıkan kabarcıkları sayın.", "Lambayı uzaklaştırıp tekrar sayın."],
       "Işık yakınken kabarcık sayısı artar.", "Işık yoğunluğu arttıkça fotosentez ve oksijen çıkışı hızlanır; kabartma tozu karbondioksit sağlar.", "Lamba sıcaktır; suya dökmeyin."),
    _x("yumurtazar", "Yumurta zarı ve ozmoz", "Orta", 30, "egg", "Zar geçirgenliğini ve ozmozu görmek.",
       ["Yumurta", "Sirke", "Bal ya da şurup", "Saf su"],
       ["Yumurtayı sirkede bekleterek kabuğunu çözün.", "Bir kısmını bal gibi derişik bir çözeltiye, bir kısmını saf suya koyun.", "Birkaç saat sonra boyutlarını karşılaştırın."],
       "Saf suda şişer, şurupta büzülür.", "Zar seçici geçirgendir; su derişimi düşük bölgeden yükseğe doğru ozmozla geçer.", "Çiğ yumurta sonrası elleri yıkayın."),
    _x("kromo", "Yaprak pigmentlerinin kromatografisi", "İleri", 40, "chroma", "Yeşil yaprağın içindeki pigmentleri ayırmak.",
       ["Ispanak yaprağı", "Kahve filtresi", "Ispirto ya da aseton (yetişkin)", "Cam bardak"],
       ["Yaprağı ezip kağıt şeridine çizgi şeklinde sürün.", "Şeridin ucunu az alkole daldırın, çizgi alkolün üstünde kalsın.", "Çözücü yükselene dek bekleyin."],
       "Yeşil, sarı ve turuncu pigment bantları ayrılır (klorofil, ksantofil, karoten).", "Pigmentler kağıda ve çözücüye farklı yatkınlıkta olduğu için farklı hızda taşınır.", "Ispirto ve aseton yanıcıdır ve buharı zararlıdır; havalandırma ve yetişkin gözetimi şart."),
    _x("mikroskop", "Su damlasından mikroskop", "Orta", 20, "bubbles", "Basit bir büyüteç yapmak.",
       ["Karton", "Şeffaf plastik", "Su damlası", "Bir ağ ya da metin"],
       ["Kartona delik açıp deliğin üstüne şeffaf plastik gerin.", "Plastiğe bir damla su damlatın.", "Damlanın içinden küçük yazıya bakın."],
       "Su damlası mercek gibi çalışıp görüntüyü büyütür.", "Damlanın dışbükey yüzeyi ışığı kırar; bu, mercek ilkesidir.", "Güvenli."),
    _x("bakteri", "Bakteri ürettirme (yalnızca laboratuvar)", "Yetişkin", 0, "bubbles", "Bakteri kültürünü anlamak.",
       ["Okul laboratuvarında hazır besiyeri", "Steril ekim araçları"],
       ["Sadece eğitmen gözetiminde, uygun güvenlik düzeyi olan laboratuvarda yapılır."],
       "Besiyerinde koloniler görülür.", "Bakteri kolonileri hızla üreyerek görülebilir hale gelir.", "Evde bakteri üretmeyin; hastalık yapıcı mikroplar üreyebilir. Kapalı petri kaplarını açmayın."),
]

# ------------------------------------------------------------------ GENETİK
_BASES = "TCAG"
_AA = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
AA_TR = {"F": "Fenilalanin", "L": "Lösin", "S": "Serin", "Y": "Tirozin", "C": "Sistein", "W": "Triptofan", "P": "Prolin", "H": "Histidin", "Q": "Glutamin",
         "R": "Arjinin", "I": "İzolösin", "M": "Metiyonin", "T": "Treonin", "N": "Asparajin", "K": "Lizin", "V": "Valin", "A": "Alanin", "D": "Aspartik asit",
         "E": "Glutamik asit", "G": "Glisin", "*": "DUR"}
CODON = {}
for _i, (_a, _b, _c) in enumerate(itertools.product(_BASES, repeat=3)):
    CODON[(_a + _b + _c).replace("T", "U")] = _AA[_i]


def dna_translate(seq: str) -> dict:
    """Verilen (kalıp) DNA zincirinden mRNA (tamamlayıcı) ve protein dizisi. Başlangıç kodonunu aramaz, baştan çevirir."""
    s = re.sub(r"[^ATGC]", "", seq.upper())
    if len(s) < 3:
        raise ValueError("en az 3 baz gerekli")
    comp = {"A": "U", "T": "A", "G": "C", "C": "G"}
    mrna = "".join(comp[b] for b in s)
    codons = [mrna[i:i + 3] for i in range(0, len(mrna) - len(mrna) % 3, 3)]
    prot = []
    for c in codons:
        aa = CODON[c]
        if aa == "*":
            prot.append("DUR")
            break
        prot.append(AA_TR[aa])
    return {"dna": s, "mrna": mrna, "codons": codons, "protein": prot, "leftover": len(mrna) % 3}


def _gametes(g: str):
    pairs = [g[i:i + 2] for i in range(0, len(g), 2)]
    return ["".join(c) for c in itertools.product(*[(p[0], p[1]) for p in pairs])]


def punnett(p1: str, p2: str) -> dict:
    """'Aa' x 'Aa' ya da 'AaBb' x 'AaBb'. Genotip ve fenotip oranlarını hesaplar (tam baskınlık)."""
    for g in (p1, p2):
        if not re.fullmatch(r"(?:[A-Za-z]{2}){1,3}", g) or any(g[i].lower() != g[i + 1].lower() for i in range(0, len(g), 2)):
            raise ValueError("genotip 'Aa' ya da 'AaBb' gibi olmalı")
    g1, g2 = _gametes(p1), _gametes(p2)
    grid = []
    for a in g1:
        row = []
        for b in g2:
            geno = "".join(sorted(x + y for x, y in zip([a[i] for i in range(len(a))], [b[i] for i in range(len(b))])) if False else
                           [("".join(sorted((a[i], b[i]), key=lambda ch: (ch.islower(), ch)))) for i in range(len(a))])
            row.append(geno)
        grid.append(row)
    cnt = Counter(c for r in grid for c in r)
    pheno = Counter()
    for c, k in cnt.items():
        key = "".join(c[i].upper() if any(ch.isupper() for ch in c[i:i + 2]) else c[i] for i in range(0, len(c), 2))
        pheno[key] += k
    total = sum(cnt.values())
    return {"gametes1": g1, "gametes2": g2, "grid": grid, "geno": dict(cnt), "pheno": dict(pheno), "total": total}


def punnett_say(p1: str, p2: str) -> str:
    r = punnett(p1, p2)
    geno = ", ".join(f"{c} tane {k}" for k, c in sorted(r["geno"].items()))
    ph = sorted(r["pheno"].items(), key=lambda kv: -kv[1])
    ratio = " : ".join(str(c) for _, c in ph)
    names = ", ".join(f"{k}" for k, _ in ph)
    if len(p1) == 2:
        dom = [c for k, c in ph if k[0].isupper()]
        rec = [c for k, c in ph if k[0].islower()]
        pheno = f"Fenotipte {sum(dom)} baskın, {sum(rec)} çekinik özellik beklenir" if dom and rec else "Fenotipin hepsi baskın özellikte olur"
    else:
        pheno = f"Fenotip oranı {ratio} ({names})"
    return f"{p1} çarpı {p2} çaprazlamasında {r['total']} kutu var. Genotipler: {geno}. {pheno}."


CLASSIF = {
    "levels": ["Tür", "Cins", "Familya", "Takım", "Sınıf", "Şube", "Alem", "Üst alem"],
    "human": ["Homo sapiens", "Homo", "Hominidae", "Primates", "Mammalia", "Chordata", "Animalia", "Eukarya"],
    "kingdoms": [
        ("Bakteriler", "Zarlı çekirdeksiz tek hücreliler (prokaryot). Örn. E. coli, süt bakterileri."),
        ("Arkeler", "Aşırı ortamlarda (sıcak, tuzlu, asidik) yaşayabilen prokaryotlar; bakterilerden ayrı bir üst alem."),
        ("Protistler", "Ökaryot, çoğu tek hücreli. Amip, paramesyum, alg."),
        ("Mantarlar", "Hücre duvarı kitinli, ışık yerine hazır besin emerek beslenir. Maya, küf, şapkalı mantar."),
        ("Bitkiler", "Hücre duvarı selülozlu, fotosentez yapar. Yosun benzerleri, çiçekli bitkiler, ağaçlar."),
        ("Hayvanlar", "Çok hücreli, hareketli, hazır besin alan ökaryotlar. Omurgalılar ve omurgasızlar."),
    ],
    "note": "Üst alemler: Bakteriler, Arkeler ve Ökaryotlar. Bilim insanları sınıflandırmayı DNA verileriyle sürekli günceller.",
}

FACT_POOL = [
    "Vücudunuzda yaklaşık 37 trilyon hücre vardır.",
    "İnsan genomu yaklaşık 3 milyar baz çiftinden oluşur ve yaklaşık yirmi bin gen içerir.",
    "İnsanlarla şempanzelerin DNA'sı yaklaşık yüzde 98-99 oranında benzerdir.",
    "Vücudunuzdaki bakteri sayısı insan hücresi sayısıyla aynı mertebededir; çoğu bağırsakta yaşar ve yararlıdır.",
    "Kırmızı kan hücrelerinde çekirdek yoktur, bu sayede daha çok hemoglobin taşırlar.",
    "Beyin vücut ağırlığının yaklaşık yüzde 2'si olduğu halde enerjinin yaklaşık yüzde 20'sini kullanır.",
    "Ahtapotun üç kalbi vardır; kanı mavidir, çünkü hemoglobin yerine bakır içeren hemosiyanin taşır.",
    "Ağaçlar, mantar ağlarıyla (mikoriza) birbirlerine besin ve su aktarabilir.",
    "Bir kan hücresi vücutta bir tur atmak için yaklaşık bir dakika harcar.",
    "Bitkiler yeşildir çünkü klorofil kırmızı ve mavi ışığı kullanıp yeşili yansıtır.",
    "Mitokondri sayısı enerji ihtiyacı yüksek hücrelerde (kalp, kas) binlerce olabilir.",
    "Kemik, aynı ağırlıktaki çelikten daha hafif ama bazı yönlerde benzer derecede dayanıklıdır.",
    "Sıcak kanlı hayvanlar enerjilerinin büyük bölümünü vücut ısısını korumak için harcar.",
    "Bir mayoz bölünme sonunda dört hücre oluşur; her biri kromozom sayısını yarıya indirir.",
    "Mayoz ve çaprazlanma sayesinde kardeşler aynı ebeveynden bile farklı gen kombinasyonları alır.",
    "Penisilin, 1928'de Alexander Fleming'in küf kontaminasyonunu fark etmesiyle keşfedildi.",
]

from lab_more_exp import BIO_EXP_X
EXPERIMENTS.extend(BIO_EXP_X)
