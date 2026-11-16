"""Kimya ve biyoloji laboratuvarları için kısa kavram açıklamaları: (başlık, arama kalıbı, açıklama)."""

CHEM = [
    ("Atom", r"\batom\b|atom nedir|atomun yapısı", "Atom, maddenin kimyasal özelliğini taşıyan en küçük yapı taşıdır. Çekirdeğinde proton ve nötron, çevresinde elektronlar bulunur. Çapı yaklaşık 0,1 nanometredir; kütlesinin neredeyse tamamı çekirdektedir."),
    ("Proton, nötron, elektron", r"proton|nötron|elektron", "Proton artı yüklü, nötron yüksüz, elektron eksi yüklüdür. Protonlar ve nötronlar çekirdekte yer alır. Elektronun kütlesi protonun yaklaşık 1836'da biridir. Atom numarası proton sayısına eşittir."),
    ("İzotop", r"izotop", "İzotoplar, proton sayısı aynı ama nötron sayısı farklı olan aynı elementin atomlarıdır. Örneğin karbon-12 ve karbon-14. Karbon-14 radyoaktiftir ve arkeolojide yaş tayini için kullanılır."),
    ("İyon", r"\biyon\b|katyon|anyon", "İyon, elektron alıp vererek yüklü hale gelmiş atom ya da atom grubudur. Elektron veren artı yüklü katyon, elektron alan eksi yüklü anyon olur. Sofra tuzu Na artı ve Cl eksi iyonlarından oluşur."),
    ("Mol", r"\bmol\b|avogadro|mol nedir", "Bir mol, 6,022 çarpı 10 üzeri 23 tanecik demektir (Avogadro sayısı). Bir mol maddenin kütlesi, atom ya da molekül kütlesine eşit sayıda gramdır; örneğin bir mol su yaklaşık 18 gramdır."),
    ("Kimyasal bağlar", r"\bbağ\b|bağlar|iyonik|kovalent|metalik bağ", "Üç ana bağ türü vardır. İyonik bağda elektron bir atomdan diğerine geçer. Kovalent bağda atomlar elektron paylaşır. Metalik bağda elektronlar metal atomları arasında serbestçe dolaşır, bu yüzden metaller iletkendir."),
    ("Asit ve baz", r"\basit\b|\bbaz\b|asit nedir|baz nedir|asit baz", "Arrhenius tanımına göre asit suda hidrojen iyonu, baz hidroksit iyonu verir. Brønsted-Lowry tanımında asit proton verici, baz proton alıcıdır. Asitlerin pH değeri 7'den küçük, bazların 7'den büyüktür."),
    ("pH", r"\bph\b|ph nedir|ph ölçeği", "pH, çözeltideki hidrojen iyonu derişiminin eksi logaritmasıdır. Ölçek 0'dan 14'e gider; 7 nötrdür. Her bir pH birimi, hidrojen iyonu derişiminde on kat fark demektir."),
    ("Tampon çözelti", r"tampon", "Tampon çözelti, az miktarda asit ya da baz eklenince pH'ı hemen hemen sabit tutan çözeltidir. Kanımız karbonik asit-bikarbonat tamponu sayesinde pH 7,4 civarında kalır."),
    ("Yükseltgenme ve indirgenme", r"yükseltgen|indirgen|redoks|oksidasyon", "Yükseltgenme elektron vermek, indirgenme elektron almaktır ve birlikte gerçekleşir. Pas oluşumunda demir yükseltgenir, oksijen indirgenir. Pillerde bu elektron akışı elektrik üretir."),
    ("Katalizör", r"katalizör|katalitik", "Katalizör, tepkime hızını artıran ama tepkimede kendisi harcanmayan maddedir. Aktivasyon enerjisini düşürür. Canlılardaki biyolojik katalizörlere enzim denir."),
    ("Tepkime hızı", r"tepkime hızı|reaksiyon hızı|hız", "Tepkime hızı sıcaklık arttıkça, derişim arttıkça, katı maddenin yüzey alanı büyüdükçe ve katalizör kullanıldıkça artar. Çünkü taneciklerin etkili çarpışma sayısı artar."),
    ("Kimyasal denge", r"denge|le chatelier|le châtelier", "Tersinir bir tepkimede ileri ve geri hız eşitlendiğinde denge kurulur. Le Chatelier ilkesine göre dengeye dışarıdan müdahale edilirse sistem etkiyi azaltacak yönde kayar."),
    ("Periyodik tablo", r"periyodik tablo nedir|periyodik|grup|periyot", "Periyodik tablo elementleri atom numarasına göre ve benzer özelliklere göre sıralar. Yatay sıralara periyot, dikey sütunlara grup denir. Aynı gruptaki elementlerin kimyasal özellikleri benzerdir."),
    ("Elektronegatiflik", r"elektronegatif", "Elektronegatiflik, bir atomun bağ elektronlarını çekme eğilimidir. Periyodik tabloda soldan sağa ve aşağıdan yukarıya doğru artar; en elektronegatif element flordur."),
    ("Element, bileşik, karışım", r"element|bileşik|karışım|saf madde", "Element tek tür atomdan oluşur. Bileşik, iki ya da daha çok elementin sabit oranda kimyasal olarak birleşmesidir. Karışımda maddeler kimliklerini korur ve fiziksel yöntemlerle ayrılabilir."),
    ("Hâl değişimleri", r"hal değişim|hâl değişim|erime|donma|buharlaş|yoğuş|süblim", "Erime katıdan sıvıya, donma sıvıdan katıya, buharlaşma sıvıdan gaza, yoğuşma gazdan sıvıya, süblimleşme katıdan doğrudan gaza geçiştir. Hâl değişimi sırasında sıcaklık sabit kalır."),
    ("Yoğunluk", r"yoğunluk", "Yoğunluk, kütlenin hacme oranıdır: d eşittir m bölü V. Suyun yoğunluğu yaklaşık 1 gram bölü santimetreküptür; yoğunluğu sudan küçük olan cisimler yüzer."),
    ("Gaz yasaları", r"gaz yasası|ideal gaz|boyle|charles|pv", "İdeal gaz denklemi PV eşittir nRT'dir. Sabit sıcaklıkta basınç ve hacim ters orantılıdır (Boyle); sabit basınçta hacim mutlak sıcaklıkla doğru orantılıdır (Charles)."),
    ("Ekzotermik ve endotermik", r"ekzotermik|endotermik|entalpi", "Ekzotermik tepkime ortama ısı verir (yanma gibi), endotermik tepkime ortamdan ısı alır (anlık soğutma paketleri gibi). Entalpi değişimi bu ısı alışverişini ölçer."),
    ("Organik kimya", r"organik|hidrokarbon|fonksiyonel", "Organik kimya karbon bileşiklerini inceler. Hidrokarbonlar yalnız karbon ve hidrojen içerir. Alkol, asit, eter gibi fonksiyonel gruplar bileşiğin özelliğini belirler."),
    ("Polimer", r"polimer|plastik", "Polimer, küçük birimlerin (monomerlerin) birbirine zincir gibi bağlanmasıyla oluşan büyük moleküldür. Plastikler, naylon, kauçuk, ve doğada nişasta, protein ve DNA polimerdir."),
    ("Sabun nasıl temizler", r"sabun", "Sabun molekülünün bir ucu suyu, diğer ucu yağı sever. Yağ lekesini sarıp misel adı verilen kürecikler oluşturur ve suyla birlikte uzaklaştırır. Ayrıca suyun yüzey gerilimini düşürür."),
    ("Yanma", r"\byanma\b|yanma tepkimesi|yanma nedir", "Yanma, bir maddenin oksijenle hızla tepkimeye girip ısı ve ışık vermesidir. Hidrokarbonlar tam yanınca karbondioksit ve su verir; oksijen yetersizse karbon monoksit ve kurum oluşur."),
    ("Radyoaktivite", r"radyoaktif|alfa|beta|gama", "Kararsız çekirdekler enerji ya da parçacık salarak bozunur. Alfa parçacığı helyum çekirdeğidir ve kâğıtla durur; beta elektrondur ve ince metalle durur; gama ışını çok nüfuz edici elektromanyetik ışımadır, kurşun ya da kalın beton ister."),
    ("Çözünürlük", r"çözünürlük|çözünme|doymuş", "Çözünürlük, belirli bir sıcaklıkta bir çözücüde çözünebilen en fazla madde miktarıdır. Katılarda genelde sıcaklıkla artar, gazlarda sıcaklıkla azalır. Doymuş çözeltide daha fazla madde çözünmez."),
    ("Atık ve güvenlik", r"atık|çevre", "Kimyasal atıklar lavaboya ya da çöpe gelişigüzel atılmaz. Asitler ve bazlar nötrleştirilir, çözücüler ve ağır metaller ayrı toplanır. Kullanılmayan maddeleri başka kaplara boşaltıp bırakmayın, etiketleyin."),
]

BIO = [
    ("Hücre kuramı", r"hücre kuramı|hücre teorisi", "Hücre kuramına göre tüm canlılar bir ya da daha fazla hücreden oluşur, hücre yaşamın temel birimidir ve her hücre başka bir hücreden meydana gelir."),
    ("Mitoz", r"mitoz", "Mitoz, bir hücrenin kendisiyle aynı kromozom sayısına sahip iki hücreye bölünmesidir. Büyüme, yenilenme ve yara iyileşmesi için gereklidir. Evreleri profaz, metafaz, anafaz ve telofazdır."),
    ("Mayoz", r"mayoz", "Mayoz, üreme hücrelerinin oluştuğu özel bölünmedir; kromozom sayısını yarıya indirir ve bir hücreden dört hücre oluşturur. Parçalanma ve çaprazlanmayla genetik çeşitlilik sağlar."),
    ("DNA", r"\bdna\b|dna nedir", "DNA, genetik bilgiyi taşıyan çift sarmal bir moleküldür. Dört bazdan oluşur: adenin, timin, guanin ve sitozin. Adenin timinle, guanin sitozinle eşleşir. İnsan genomu yaklaşık 3 milyar baz çiftinden oluşur."),
    ("RNA", r"\brna\b|mrna|trna|rrna", "RNA genellikle tek zincirlidir, riboz şekeri taşır ve timin yerine urasil içerir. mRNA bilgiyi çekirdekten ribozoma taşır, tRNA amino asitleri getirir, rRNA ribozomun yapısında yer alır."),
    ("Gen ve kromozom", r"\bgen\b|kromozom|genom", "Gen, bir proteini ya da işlevsel RNA'yı kodlayan DNA parçasıdır. Kromozom, DNA'nın sıkıca paketlenmiş halidir. İnsan vücut hücrelerinde 46 kromozom, yani 23 çift vardır."),
    ("Protein sentezi", r"protein sentezi|transkripsiyon|translasyon", "Protein sentezi iki aşamalıdır. Transkripsiyonda DNA'dan mRNA yazılır (çekirdekte). Translasyonda ribozom mRNA'daki üçlü kodonları okuyup tRNA'ların getirdiği amino asitleri sırayla bağlar."),
    ("Fotosentez", r"fotosentez", "Fotosentez, bitkilerin, alglerin ve bazı bakterilerin ışık enerjisiyle karbondioksit ve sudan glikoz ve oksijen üretmesidir. Işığa bağımlı tepkimeler granalarda, Calvin döngüsü stromada gerçekleşir."),
    ("Hücresel solunum", r"hücresel solunum|solunum tepkime|atp", "Hücresel solunum glikozdan ATP üretir. Glikoliz sitoplazmada, Krebs döngüsü ve elektron taşıma zinciri mitokondride gerçekleşir. Oksijenli solunum bir glikozdan yaklaşık 30 ATP verir."),
    ("Fermantasyon", r"fermantasyon|mayalanma", "Oksijensiz ortamda glikoz kısmen yıkılır. Mayada alkol ve karbondioksit, kaslarda ya da süt bakterilerinde laktik asit oluşur. Ekmek, yoğurt ve turşu fermantasyona dayanır."),
    ("Ozmoz ve difüzyon", r"ozmoz|difüzyon|aktif taşıma", "Difüzyon, maddelerin derişimi yüksekten düşüğe yayılmasıdır. Ozmoz, suyun yarı geçirgen zardan geçişidir. Aktif taşımada hücre ATP harcayarak maddeyi derişimin düşük olduğu yerden yüksek olduğu yere taşır."),
    ("Enzim", r"enzim", "Enzimler tepkimeleri hızlandıran protein yapılı biyolojik katalizörlerdir. Her enzim belirli bir maddeye (substrat) özgüdür. Sıcaklık ve pH aşırı olursa enzim yapısı bozulur."),
    ("Kalıtım", r"kalıtım|mendel|baskın|çekinik", "Mendel bezelyelerle yaptığı çaprazlamalarla kalıtımın temel yasalarını buldu. Bir özellik için iki alel bulunur; baskın alel çekinik aleli maskeleyebilir. Genotip genetik yapı, fenotip görünür özelliktir."),
    ("Mutasyon", r"mutasyon", "Mutasyon, DNA dizisindeki kalıcı değişikliktir. Çoğu etkisizdir, bazıları zararlı, nadiren yararlıdır. Evrim için çeşitlilik kaynağıdır."),
    ("Evrim ve doğal seçilim", r"evrim|doğal seçilim|darwin", "Doğal seçilimde bir ortamda hayatta kalma ve üremede avantaj sağlayan kalıtsal özellikler sonraki nesillerde daha yaygın hale gelir. Evrim, popülasyonların zaman içinde değişmesidir; fosiller, karşılaştırmalı anatomi ve DNA benzerlikleriyle desteklenir."),
    ("Besin zinciri", r"besin zinciri|ekosistem|besin ağı", "Üreticiler (bitkiler) ışık enerjisini besine çevirir; otçul tüketiciler bitkileri, etçil tüketiciler otçulları yer; ayrıştırıcılar ölü maddeyi parçalar. Enerji her basamakta yaklaşık onda bir oranında aktarılır."),
    ("Homeostazi", r"homeostazi|denge durumu", "Homeostazi, vücudun iç ortamını (sıcaklık, kan şekeri, su dengesi) dar sınırlar içinde tutmasıdır. Genellikle olumsuz geri bildirimle çalışır: değişim algılanır ve tersi yönde düzeltilir."),
    ("Hormonlar ve sinirler", r"hormon|sinirsel|nörotransmitter", "Sinir sistemi hızlı ve kısa süreli elektrik-kimyasal sinyallerle, hormonlar yavaş ama uzun süreli kimyasal haberlerle kan yoluyla iş görür. İkisi birlikte vücudu koordine eder."),
    ("Aşı ve bağışıklık", r"aşı|bağışıklık|antikor", "Aşı, zayıflatılmış ya da etkisiz hale getirilmiş mikrop parçası verip bağışıklık sisteminin hafıza hücreleri oluşturmasını sağlar. Gerçek enfeksiyonla karşılaşınca vücut hızlı ve güçlü yanıt verir."),
    ("Antibiyotik", r"antibiyotik", "Antibiyotikler bakterilere karşı etkilidir, virüslere değil. Gereksiz ya da yarım bırakılarak kullanılmaları bakterilerde direnç gelişmesine neden olur."),
    ("Virüs", r"virüs|virus", "Virüsler hücresel yapıda değildir; bir genetik madde ve protein kılıftan oluşur ve çoğalmak için konak hücreye ihtiyaç duyarlar. Canlı sayılıp sayılmayacağı tartışmalıdır."),
    ("Bakteri", r"bakteri nedir|bakteriler", "Bakteriler çekirdeksiz tek hücrelidir. Çoğu zararsız ya da yararlıdır; bağırsak florası, yoğurt, toprağı verimli kılma gibi görevleri vardır. Bir kısmı hastalık yapar."),
    ("Kök hücre", r"kök hücre", "Kök hücreler kendini yenileyebilen ve farklı hücre tiplerine dönüşebilen hücrelerdir. Kemik iliğindeki kök hücreler kan hücrelerini üretir; tedavide kullanılır."),
    ("CRISPR", r"crispr|gen düzenleme", "CRISPR-Cas9, DNA'da belirli bir noktayı hedefleyip kesebilen gen düzenleme yöntemidir. Bakterilerin virüslere karşı savunma sisteminden uyarlanmıştır. Tıpta ve tarımda araştırılır, etik tartışmaları da vardır."),
    ("PCR", r"\bpcr\b", "PCR, çok az DNA'yı kopyalayarak milyarlarca kopya yapan yöntemdir. Isıtma ve soğutma döngüleriyle çalışır; hastalık testlerinde ve adli bilimde kullanılır."),
    ("Kan grupları", r"kan grup", "ABO sisteminde A, B, AB ve O kan grupları vardır; ayrıca Rh faktörü (artı ya da eksi) bulunur. Kan nakli ve gebelikte uyum önemlidir. O negatif kan grubu herkese verilebilir."),
    ("Biyoçeşitlilik", r"biyoçeşitlilik|biyolojik çeşitlilik", "Biyoçeşitlilik, bir bölgedeki tür, gen ve ekosistem çeşitliliğidir. Ekosistemin dayanıklılığını artırır. Habitat kaybı ve iklim değişikliği ciddi tehditlerdir."),
    ("DNA parmak izi", r"dna parmak|adli", "DNA parmak izi, kişiler arasında farklı olan kısa tekrar dizilerini karşılaştırır. Adli olaylarda, babalık testlerinde ve akrabalık analizinde kullanılır."),
]


# ---- ayrıntılı kavramlar (lab_more_kb.py) listelerin başına eklenir: özel desenler genel olanlardan önce eşleşsin
from lab_more_kb import CHEM_X, BIO_X
from lab_more_kb import with_title
CHEM[:0] = with_title(CHEM_X)
BIO[:0] = with_title(BIO_X)


def sentences(text: str):
    import re
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9(])", text) if s.strip()]


DETAIL = r"ayrıntılı|detaylı|derinlemesine|kapsamlı|geniş bilgi"


def find_detail(items, t):
    """'… hakkında ayrıntılı bilgi' gibi isteklerde deneylerden önce kavram anlatımını arar: (başlık, metin) ya da None."""
    import re
    if not re.search(DETAIL, t):
        return None
    for title, pat, text in items:
        if re.search(pat, t):
            return title, text
    return None


def short_say(title: str, text: str, limit: int = 380) -> str:
    """Sesli cevap için: uzun anlatımda ilk cümleleri (~limit karakter) okur, geri kalanı ekranda bırakır."""
    if len(text) <= limit:
        return f"{title}. {text}"
    out = ""
    for s in sentences(text):
        if out and len(out) + len(s) > limit:
            break
        out += (" " if out else "") + s
    return f"{title}. {out} Ayrıntıların tamamı ekranda efendim."

from lab_more_ref import CHEM_REF, BIO_REF
CHEM[:0] = with_title(CHEM_REF)
BIO[:0] = with_title(BIO_REF)
