"""Uzay modu: her gök cismi için ayrıntılı bilgi satırları (kart ekranda gösterir; 'ayrıntı' denince Jarvis sırayla okur).
Anahtarlar scenes.BODIES içindeki anahtarlardır."""

MORE = {
    "sun": [
        "Yaşı yaklaşık 4,6 milyar yıl; yaklaşık 5 milyar yıl sonra hidrojeni biter, kırmızı deve dönüşüp dış katmanlarını atacak ve beyaz cüce olarak sönecek.",
        "Kütlesinin yaklaşık yüzde 73'ü hidrojen, yüzde 25'i helyumdur. Çekirdek sıcaklığı yaklaşık 15 milyon kelvindir ve saniyede yaklaşık 600 milyon ton hidrojeni helyuma çevirir.",
        "Işığı Dünya'ya yaklaşık 8 dakika 20 saniyede ulaşır. Ekvatorda yaklaşık 25 günde, kutuplarda yaklaşık 35 günde döner; gaz küresi olduğu için farklı dönme hızları vardır.",
        "Güneş lekeleri çevresinden daha serin, manyetik alanı güçlü bölgelerdir. Etkinlik yaklaşık 11 yıllık döngüyle artıp azalır; Güneş patlamaları Dünya'da kutup ışığına ve uydu arızalarına yol açabilir.",
        "Dış atmosferi olan korona milyonlarca derece sıcaktır; yüzeyden çok daha sıcak olmasının nedeni hâlâ araştırılmaktadır. Parker Güneş Sondası koronanın içinden geçmiştir.",
    ],
    "mercury": [
        "Kütlesi Dünya'nın yaklaşık yirmide biri, yüzey çekimi 3,7 metre bölü saniye karedir. Atmosferi neredeyse yoktur, bu yüzden gündüz ile gece arasındaki sıcaklık farkı çok büyüktür.",
        "Kendi ekseni etrafında yaklaşık 58,6 günde döner ama Güneş'e göre bir gün yaklaşık 176 Dünya gününe eşittir: iki yılında üç kez döner (3'e 2 rezonans).",
        "Yüzeyi Ay'a benzer, kraterlerle doludur. En büyük yapısı yaklaşık 1550 kilometre çaplı Caloris Havzası'dır. Kutuplardaki hiç Güneş görmeyen kraterlerde su buzu bulunmuştur.",
        "Demir çekirdeği gezegenin yarıçapının yaklaşık yüzde 85'ini oluşturur; bu yüzden yoğunluğu Dünya'dan sonra ikinci sıradadır. Zayıf da olsa kendi manyetik alanı vardır.",
        "MESSENGER sondası 2011 ile 2015 arasında Merkür'ün yörüngesinde kalarak gezegenin tamamını haritaladı.",
    ],
    "venus": [
        "Atmosferinin yaklaşık yüzde 96,5'i karbondioksittir; yüzeydeki basınç Dünya'nın yaklaşık 92 katıdır. Kükürt asidi bulutları ve güçlü sera etkisi yüzeyi yaklaşık 465 dereceye ısıtır.",
        "Dünya'yla neredeyse ikiz boyuttadır ama ters yönde (doğudan batıya) ve çok yavaş döner: kendi etrafında bir turu yaklaşık 243 Dünya günüdür, Güneş çevresindeki bir turdan (225 gün) uzundur.",
        "Yüzey çekimi 8,87 metre bölü saniye karedir, yani Dünya'dakinin yaklaşık yüzde 90'ı. Gökyüzünde Güneş ve Ay'dan sonra en parlak cisimdir; bu yüzden çoğu kez 'akşam yıldızı' ya da 'sabah yıldızı' sanılır.",
        "Venera 7 (1970) başka bir gezegene yumuşak iniş yapıp veri gönderen ilk araç oldu; Venera 13 yüzeyde yaklaşık iki saat dayandı ve ilk renkli fotoğrafları çekti. Magellan sondası radarla yüzeyi haritaladı; binlerce yanardağ saptandı.",
    ],
    "earth": [
        "Yüzeyinin yaklaşık yüzde 71'i okyanuslarla kaplıdır. Atmosferin yüzde 78'i azot, yüzde 21'i oksijendir. Yaşı yaklaşık 4,54 milyar yıldır.",
        "Güneş çevresinde ortalama 29,8 kilometre bölü saniye hızla döner (saatte yaklaşık 107.000 kilometre). Kendi etrafında bir tur yaklaşık 23 saat 56 dakikadır; ekseni 23,5 derece eğik olduğu için mevsimler oluşur.",
        "İç yapısı kabuk, manto, sıvı dış çekirdek ve katı iç çekirdekten oluşur. Dış çekirdekteki sıvı demirin hareketi manyetik alan üretir ve bu alan Güneş rüzgarına karşı kalkan görevi görür.",
        "Yüzey çekimi 9,81 metre bölü saniye karedir. Gezegenin kayalık yüzeyi levhalardan oluşur ve levhalar yılda birkaç santimetre hareket eder.",
        "Güneş sistemindeki en yoğun gezegendir (5,51 gram bölü santimetreküp). Hayat için gerekli sıvı su, yaşanabilir bölgedeki konumu sayesinde yüzeyde bulunur.",
    ],
    "moon": [
        "Yüzey çekimi Dünya'nın altıda biridir (1,62 metre bölü saniye kare). Atmosferi neredeyse yoktur; sıcaklık gündüz yaklaşık 127, gece yaklaşık eksi 173 dereceye iner.",
        "Dünya'ya kilitlenmiş durumdadır: dönme süresi ile dolanma süresi eşit olduğu için hep aynı yüzünü gösterir. Her yıl Dünya'dan yaklaşık 3,8 santimetre uzaklaşır.",
        "En yaygın kuramına göre yaklaşık 4,5 milyar yıl önce Mars büyüklüğünde bir cismin (Theia) genç Dünya'ya çarpmasıyla oluşan döküntüden doğdu.",
        "Apollo programında 1969 ile 1972 arasında 12 astronot Ay yüzeyine ayak bastı; ilki Neil Armstrong'dur (20 Temmuz 1969). Kutup kraterlerinde su buzu bulunur.",
        "Dünya'daki gelgitlerin başlıca nedenidir ve Güneş tutulmasında Güneş'in tam önüne geçecek kadar uygun boyutta ve uzaklıktadır.",
    ],
    "mars": [
        "Yüzey çekimi 3,71 metre bölü saniye kare (Dünya'nın yaklaşık yüzde 38'i). Bir günü yaklaşık 24 saat 37 dakika, bir yılı 687 Dünya günüdür. Ortalama yüzey sıcaklığı yaklaşık eksi 60 derecedir.",
        "Atmosferi yaklaşık yüzde 95 karbondioksittir ve çok incedir; yüzey basıncı Dünya'nın yaklaşık yüzde 0,6'sı kadardır. Toz fırtınaları bazen tüm gezegeni sarar.",
        "Valles Marineris vadi sistemi yaklaşık 4000 kilometre uzunluğundadır. Kutuplarda su ve karbondioksit buzu, eski nehir yatakları ve göl tortuları geçmişte sıvı su bulunduğunu gösterir.",
        "Curiosity (2012) ve Perseverance (2021) gezgin araçları yüzeyde çalışır; Perseverance ile birlikte inen Ingenuity helikopteri başka bir gezegende uçan ilk araç oldu.",
        "Fobos Mars'ın çevresinde günde yaklaşık üç kez döner ve çekim etkisiyle yavaş yavaş gezegene yaklaşır; milyonlarca yıl sonra parçalanması ya da çarpması beklenir.",
    ],
    "jupiter": [
        "Kütlesi Dünya'nın yaklaşık 318 katıdır ve diğer tüm gezegenlerin toplam kütlesinin yaklaşık 2,5 katıdır. Hacmine yaklaşık 1300 Dünya sığar.",
        "Neredeyse tümüyle hidrojen ve helyumdan oluşur; katı bir yüzeyi yoktur. Kendi etrafındaki dönüşü Güneş sisteminde en hızlıdır: yaklaşık 9 saat 56 dakika.",
        "Büyük Kırmızı Leke Dünya'dan büyük bir fırtına sistemidir ve en az 350 yıldır sürmektedir; son yüzyılda küçülmektedir.",
        "Galile uydularını Galileo 1610'da keşfetti: Io (yanardağlı), Europa (buz kabuğunun altında okyanus), Ganymede (Güneş sisteminin en büyük uydusu) ve Callisto.",
        "Güçlü manyetik alanı ve yoğun radyasyon kuşakları vardır. Juno sondası 2016'dan beri yörüngede kutupları, atmosferi ve iç yapıyı inceliyor.",
    ],
    "saturn": [
        "Ortalama yoğunluğu 0,69 gram bölü santimetreküptür, yani suyun altında; bu yüzden yeterince büyük bir havuzda yüzerdi. Gün uzunluğu yaklaşık 10 saat 33 dakikadır; bir yılı yaklaşık 29,4 Dünya yılıdır.",
        "Halkaları çoğunlukla su buzu parçalarından oluşur; genişlikleri yaklaşık 280.000 kilometreyi bulur ama kalınlıkları çoğu bölgede yalnızca on metre civarındadır. Halkaların yaşı konusunda tartışma sürüyor.",
        "En büyük uydusu Titan, Merkür'den büyüktür ve yoğun azot atmosferi vardır; yüzeyinde sıvı metan ve etan gölleri bulunur. Enceladus'tan fışkıran su buharı jetleri, buz kabuğunun altında okyanus olduğunu gösterir.",
        "Kuzey kutbunda altıgen biçimli bir jet akımı bulunur. Cassini-Huygens görevi 2004 ile 2017 arasında Satürn'ü inceledi; Huygens, Titan'a inen ilk araç oldu.",
    ],
    "uranus": [
        "Eksen eğikliği yaklaşık 98 derece olduğu için 'yan yatarak' yuvarlanır; kutuplar 42 yıl boyunca sürekli Güneş görür, sonraki 42 yıl karanlıkta kalır. Dönüşü diğer gezegenlere göre ters yöndedir.",
        "Atmosferindeki metan kırmızı ışığı soğurduğu için mavi-yeşil görünür. Atmosferi Güneş sisteminin en soğuğudur: yaklaşık eksi 224 dereceye iner.",
        "Buz devidir: iç yapısında su, amonyak ve metan buzları ağır basar. 13 bilinen halkası ve 27 uydusu vardır; uydularının adları Shakespeare ve Pope eserlerindeki karakterlerden gelir (Miranda, Ariel, Titania, Oberon).",
        "Voyager 2 sondası 1986'da Uranüs'ün yakınından geçen tek araçtır. 1781'de William Herschel tarafından teleskopla keşfedilen ilk gezegendir.",
    ],
    "neptune": [
        "Varlığı gözlemle değil matematikle önceden bulunan ilk gezegendir: Urbain Le Verrier ve John Couch Adams Uranüs yörüngesindeki sapmalardan konumunu hesapladı, Johann Galle 1846'da teleskopla buldu.",
        "Güneş sisteminin en şiddetli rüzgârları buradadır: saatte yaklaşık 2100 kilometreye ulaşır. Bir yılı yaklaşık 165 Dünya yılıdır; keşfinden bu yana ilk tam turunu 2011'de tamamladı.",
        "En büyük uydusu Triton gezegenin dönüş yönüne ters yönde dolanır; muhtemelen Kuiper Kuşağı'ndan yakalanmış bir cisimdir. Yüzeyinde azot jetleri fışkırır ve sıcaklığı yaklaşık eksi 235 derecedir.",
        "Voyager 2 sondası 1989'da Neptün'e yaklaştı ve Büyük Karanlık Leke'yi ve halkaları görüntüledi.",
    ],
    "pluto": [
        "1930'da Clyde Tombaugh tarafından keşfedildi. Uluslararası Astronomi Birliği 2006'da gezegenin tanımını yeniden yaptı: yörüngesini diğer cisimlerden temizleyemediği için Plüton cüce gezegen sayılır.",
        "New Horizons sondası 2015'te yakından geçti. Yüzeyinde kalp biçimli Tombaugh Bölgesi (azot buzu ovası), su buzundan dağlar ve ince bir azot atmosferi görüldü.",
        "Beş uydusu vardır: Charon (Plüton'un yaklaşık yarısı boyutunda, bu yüzden ikili sistem sayılır), Styx, Nix, Kerberos ve Hydra. Charon her zaman aynı yüzünü Plüton'a gösterir.",
        "Güneş çevresindeki bir turu yaklaşık 248 Dünya yılıdır. Yörüngesi dışmerkezli ve eğiktir; bazen Neptün'ün yörüngesinden Güneş'e daha yakın geçer. Kuiper Kuşağı'nın en bilinen cismidir.",
    ],
    "io": [
        "Jüpiter'in en içteki büyük Galile uydusudur; yarıçapı yaklaşık 1822 kilometredir. Güneş sistemindeki en aktif volkanik gökcismidir ve yüzeyinde yüzlerce yanardağ bulunur.",
        "Jüpiter'in güçlü çekimi ve komşu uydularının yarattığı gelgit kuvvetleri iç kısmı sürekli esnetip ısıtır; bu ısınma yanardağları besler.",
        "Yüzeyi kükürt ve kükürt dioksit donlarıyla kaplıdır; bu yüzden sarı, turuncu ve kırmızı renklerle parlak görünür.",
        "Voyager 1 1979'da aktif yanardağları ilk kez görüntüledi. Galileo sondası 1995 ile 2003 arasında Io'nun yakınından defalarca geçerek patlamaları izledi.",
    ],
    "europa": [
        "Jüpiter'in Galile uydularından biridir; yarıçapı yaklaşık 1561 kilometredir ve Ay'dan biraz küçüktür.",
        "Yüzeyi buz kabuğuyla kaplıdır; bu kabuğun altında tuzlu su okyanusunun bulunduğu düşünülür. Okyanusun Dünya'nın okyanuslarından daha fazla su içerebileceği tahmin edilir.",
        "Yüzeyindeki çizgi ve çatlaklar buz kabuğunun hareket ettiğini ve altındaki sıvı suyun yüzeye yakın olabileceğini gösterir.",
        "Galileo sondası 1995 ile 2003 arasında Europa'yı inceledi. NASA'nın Europa Clipper görevi 2024'te yola çıktı ve 2030'larda uydunun defalarca yakınından geçecek.",
    ],
    "ganymede": [
        "Güneş sisteminin en büyük uydusudur; yarıçapı yaklaşık 2634 kilometredir ve Merkür'den daha büyüktür.",
        "Hem kayalık hem buzlu bir yapıya sahiptir; iç kısmında demir çekirdek ve yüzeyinin altında tuzlu su okyanusu bulunabileceği düşünülür.",
        "Bilinen tek uydu olarak kendi manyetik alanına sahiptir; bu alan Jüpiter'in manyetosferi içinde küçük bir koruma alanı oluşturur.",
        "Yüzeyinde eski ve yoğun kraterli koyu bölgeler ile daha genç açık renkli bölgeler birlikte görülür.",
    ],
    "callisto": [
        "Jüpiter'in dış Galile uydusudur; yarıçapı yaklaşık 2410 kilometredir ve Güneş sistemindeki en çok kraterli cisimlerden biridir.",
        "Jüpiter'in yoğun radyasyon kuşaklarından uzakta olduğu için yüzeyi diğer büyük Galile uydularına göre çok daha az radyasyona maruz kalır.",
        "Kraterler çok eski olduğu için yüzey jeolojik olarak neredeyse hiç değişmemiştir. Altında tuzlu bir okyanus olabileceği tahmin edilmektedir.",
        "Galileo sondası 1995 ile 2003 arasında Callisto'nun yakınından birkaç kez geçti; Jüpiter'in diğer büyük uydularından farklı olarak yörüngesi bir rezonans zincirine bağlı değildir.",
    ],
    "titan": [
        "Satürn'ün en büyük uydusudur; yarıçapı yaklaşık 2575 kilometredir ve Merkür'den büyüktür.",
        "Güneş sistemindeki yoğun atmosferi olan tek uydudur; yüzey basıncı Dünya'nın yaklaşık 1,5 katıdır ve atmosferi büyük ölçüde azottan oluşur.",
        "Yüzeyinde sıvı metan ve etan gölleri ile nehir yatakları bulunur; bu sıvılar Dünya'daki su döngüsüne benzeyen bir metan döngüsü oluşturur.",
        "Huygens iniş aracı 2005'te Titan'a inen ilk araç oldu ve yüzeyden görüntü gönderdi. Titan her zaman aynı yüzünü Satürn'e gösterir.",
    ],
    "enceladus": [
        "Satürn'ün küçük ama çok parlak bir uydusudur; yarıçapı yaklaşık 252 kilometredir ve Güneş ışığının neredeyse tamamını yansıtan taze buzla kaplıdır.",
        "Güney kutbundaki çatlaklardan fışkıran su buharı ve buz taneleri jetler oluşturur; bu jetler Satürn'ün E halkasını besler.",
        "Buz kabuğunun altında sıvı su okyanusu olduğu düşünülür ve bu okyanusta hidrotermal aktivite bulunabileceği tahmin edilir.",
        "Cassini sondası 2005'te jetleri keşfetti; 2008 ile 2015 arasında bu jetlerin içinden geçerek su ve organik madde örneği aldı.",
    ],
    "triton": [
        "Neptün'ün en büyük uydusudur; yarıçapı yaklaşık 1353 kilometredir ve Güneş sistemindeki en soğuk yüzeylerden birine sahiptir.",
        "Neptün'ün dönüş yönünün tersine dolanır; bu, Triton'un muhtemelen Kuiper Kuşağı'ndan yakalanmış bir cisim olduğunu düşündürür.",
        "Yüzeyinde azot buzu ovaları bulunur; Voyager 2 1989'da yüzeyden fışkıran azot gazı jetlerini görüntüledi.",
        "Neptün'ün gelgit kuvvetleri yüzünden yörüngesi yavaşça küçülmektedir ve milyarlarca yıl sonra parçalanıp bir halka oluşturabileceği tahmin edilmektedir.",
    ],
    "charon": [
        "Plüton'un en büyük uydusudur; çapı yaklaşık 1212 kilometredir, yani Plüton'un yarısı kadardır.",
        "Plüton ile ortak bir ağırlık merkezi etrafında döner ve bu ikili sistem, ağırlık merkezi Plüton'un dışında kaldığı için özel kabul edilir.",
        "Yüzeyinin büyük bölümü su buzuyla kaplıdır; kuzey kutbunda kırmızımsı bir bölge görülür.",
        "New Horizons sondası 2015'te Charon'un ayrıntılı görüntülerini çekti ve yüzeyde uzun kanyonlar keşfetti.",
    ],
    "ceres": [
        "Mars ile Jüpiter arasındaki asteroit kuşağındaki en büyük cisimdir; çapı yaklaşık 940 kilometredir ve cüce gezegen olarak sınıflandırılır.",
        "1801'de İtalyan astronom Giuseppe Piazzi tarafından keşfedildi. İlk başta gezegen sanıldı, sonra asteroit olarak sınıflandırıldı ve 2006'da cüce gezegen oldu.",
        "Yüzeyinde parlak lekeler bulunur; bunların tuz yataklarından oluştuğu düşünülür. En belirgin lekeler Occator Krateri'nde toplanmıştır.",
        "Dawn sondası 2015'ten 2018'e kadar Ceres'in yörüngesinde kaldı ve bir cüce gezegenin yörüngesine giren ilk araç oldu.",
    ],
    "halley": [
        "Yaklaşık 76 yılda bir Güneş'in yakınından geçen en bilinen kuyruklu yıldızdır. Son geçişi 1986'da gerçekleşti ve bir sonraki yaklaşımı 2061 civarında beklenmektedir.",
        "Çekirdeği yaklaşık 15 kilometre uzunluğunda ve 8 kilometre genişliğinde, karanlık ve buzlu bir cisimdir.",
        "Kuyruğu Güneş rüzgârının etkisiyle Güneş'in tersi yönde uzanır; toz kuyruğu ve iyon kuyruğu olmak üzere iki ayrı yapıdan oluşur.",
        "Edmond Halley, 1758'de geri döneceğini önceden tahmin etti; bu, gök cisimlerinin yörüngesinin hesaplanabildiğini gösteren ilk örneklerden biridir.",
    ],
    "eris": [
        "Güneş sisteminin en kütleli bilinen cüce gezegenidir; kütlesi Plüton'un yaklaşık yüzde 27 fazladır.",
        "2005'te Mike Brown'ın ekibi tarafından keşfedildi; bu keşif Plüton'un cüce gezegen olarak yeniden sınıflandırılmasına yol açtı.",
        "Kuiper Kuşağı'nın dışındaki dağınık diskte dolanır; Güneş çevresindeki bir turu yaklaşık 558 Dünya yılıdır ve yörünge eğikliği yaklaşık 44 derecedir.",
        "Yüzeyi metan ve azot donlarıyla kaplıdır ve Güneş sisteminin en parlak yüzeylerinden biridir. Uydusunun adı Dysnomia'dır ve Eris'in kızının adını taşır.",
    ],
}

EXTRA_BODIES = [
    ("karadelik", "blackhole", r"kara ?delik|kara ?delig", "Karadelik: yoğunluğu o kadar yüksek bir kütlenin çökmesiyle oluşan bölgedir ki kaçış hızı ışık hızını geçer; ışık bile dışarı çıkamaz. Bu gösterimdeki karadelik Güneş sisteminin çok dışındadır ve gerçek uzaklığı ışık yılı ile ölçülür; burada yalnızca görünümünü göstermek için ölçek dışı uzakta çizilmiştir. Çevresindeki parlak halka, çekilen gazın ısınıp X ışını yaydığı toplanma diskidir."),
    ("io", "io", r"\bio\b", "Io: Jüpiter'in en içteki büyük uydusudur ve Güneş sistemindeki en volkanik gökcismidir. Yüzeyinde yüzlerce aktif yanardağ bulunur ve kükürt donları yüzeyi sarı, turuncu ve kırmızı renklerle boyar."),
    ("europa", "europa", r"europa|avrupa uydusu", "Europa: Jüpiter'in buzla kaplı uydusudur ve buz kabuğunun altında tuzlu bir okyanus olabileceği düşünülür. Bu nedenle Güneş sistemindeki yaşam arayışlarının en önemli hedeflerinden biridir."),
    ("ganymede", "ganymede", r"ganymede|ganimet", "Ganymede: Güneş sisteminin en büyük uydusudur ve Merkür'den daha büyüktür. Bilinen tek uydu olarak kendi manyetik alanına sahiptir ve yüzeyinin altında bir okyanus bulunabilir."),
    ("callisto", "callisto", r"callisto|kalisto", "Callisto: Jüpiter'in dış Galile uydusudur ve Güneş sistemindeki en çok kraterli cisimlerden biridir. Jüpiter'in yoğun radyasyonundan uzakta olduğu için yüzeyi büyük ölçüde değişmemiştir."),
    ("titan", "titan", r"titan", "Titan: Satürn'ün en büyük uydusudur ve Güneş sisteminde yoğun atmosferi olan tek uydudur. Yüzeyinde sıvı metan ve etan gölleri bulunur, Huygens iniş aracı 2005'te buraya inmiştir."),
    ("enceladus", "enceladus", r"enceladus|enseladus", "Enceladus: Satürn'ün küçük ama çok parlak bir uydusudur. Güney kutbundan fışkıran su jetleri, buz kabuğunun altında sıvı su okyanusu olduğunu gösterir ve yaşam arayışı açısından önemli bir hedeftir."),
    ("triton", "triton", r"triton", "Triton: Neptün'ün en büyük uydusudur ve gezegenin dönüş yönünün tersine döner. Muhtemelen Kuiper Kuşağı'ndan yakalanmış bir cisimdir ve yüzeyinden azot gazı fışkırmaları gözlenmiştir."),
    ("charon", "charon", r"charon|karon|şaron", "Charon: Plüton'un en büyük uydusudur ve çapı Plüton'un yarısı kadardır. Plüton ile ortak bir ağırlık merkezi etrafında döner, New Horizons sondası 2015'te ayrıntılı görüntülerini gönderdi."),
    ("ceres", "ceres", r"ceres|seres", "Ceres: Mars ile Jüpiter arasındaki asteroit kuşağında bulunan en büyük cisimdir ve cüce gezegen olarak sınıflandırılır. 1801'de Giuseppe Piazzi tarafından keşfedildi; Dawn sondası 2015'te yörüngesine giren ilk araç oldu."),
    ("halley kuyruklu yıldızı", "halley", r"halley|kuyruklu", "Halley kuyruklu yıldızı: Yaklaşık 76 yılda bir Güneş'in yakınından geçen en bilinen kuyruklu yıldızdır. Son geçişi 1986'da gerçekleşti ve bir sonraki yaklaşımı 2061 civarında beklenmektedir."),
    ("eris", "eris", r"\beris\b", "Eris: Güneş sisteminin en kütleli bilinen cüce gezegenidir ve kütlesi Plüton'dan fazladır. 2005'te keşfedilmesi, Plüton'un cüce gezegen olarak yeniden sınıflandırılmasına yol açtı."),
]

FACTS = {
    "sun": {"tur": "Yıldız (G tipi)", "cap": "1.392.000 km", "cap_km": 1392000, "kutle": "333.000 Dünya", "cekim": "274 m/s²", "gun": "ekvatorda ~25 gün", "yil": "yok", "uzaklik": "yok", "sicaklik": "yüzey ~5.500 °C", "uydu": "yok", "kesif": "antik çağdan beri"},
    "mercury": {"tur": "Karasal gezegen", "cap": "4.879 km", "cap_km": 4879, "kutle": "0,055 Dünya", "cekim": "3,7 m/s²", "gun": "58,6 gün", "yil": "88 gün", "uzaklik": "57,9 milyon km", "sicaklik": "-180 ila 430 °C", "uydu": "0", "kesif": "antik çağdan beri"},
    "venus": {"tur": "Karasal gezegen", "cap": "12.104 km", "cap_km": 12104, "kutle": "0,815 Dünya", "cekim": "8,87 m/s²", "gun": "243 gün (ters)", "yil": "225 gün", "uzaklik": "108,2 milyon km", "sicaklik": "ort. 465 °C", "uydu": "0", "kesif": "antik çağdan beri"},
    "earth": {"tur": "Karasal gezegen", "cap": "12.742 km", "cap_km": 12742, "kutle": "1 Dünya", "cekim": "9,81 m/s²", "gun": "23 sa 56 dk", "yil": "365,25 gün", "uzaklik": "149,6 milyon km", "sicaklik": "ort. 15 °C", "uydu": "1", "kesif": "antik çağdan beri"},
    "moon": {"tur": "Doğal uydu", "cap": "3.474 km", "cap_km": 3474, "kutle": "0,0123 Dünya", "cekim": "1,62 m/s²", "gun": "27,3 gün", "yil": "27,3 gün", "uzaklik": "Dünya'ya 384.400 km", "sicaklik": "-173 ila 127 °C", "uydu": "yok", "kesif": "antik çağdan beri"},
    "mars": {"tur": "Karasal gezegen", "cap": "6.779 km", "cap_km": 6779, "kutle": "0,107 Dünya", "cekim": "3,71 m/s²", "gun": "24 sa 37 dk", "yil": "687 gün", "uzaklik": "227,9 milyon km", "sicaklik": "ort. -60 °C", "uydu": "2", "kesif": "antik çağdan beri"},
    "jupiter": {"tur": "Gaz devi", "cap": "139.820 km", "cap_km": 139820, "kutle": "318 Dünya", "cekim": "24,79 m/s²", "gun": "9 sa 56 dk", "yil": "11,86 yıl", "uzaklik": "778,5 milyon km", "sicaklik": "ort. -110 °C", "uydu": "90+", "kesif": "antik çağdan beri"},
    "saturn": {"tur": "Gaz devi", "cap": "116.460 km", "cap_km": 116460, "kutle": "95 Dünya", "cekim": "10,44 m/s²", "gun": "10 sa 33 dk", "yil": "29,4 yıl", "uzaklik": "1,43 milyar km", "sicaklik": "ort. -140 °C", "uydu": "140+", "kesif": "antik çağdan beri"},
    "uranus": {"tur": "Buz devi", "cap": "50.724 km", "cap_km": 50724, "kutle": "14,5 Dünya", "cekim": "8,69 m/s²", "gun": "17 sa 14 dk (ters)", "yil": "84 yıl", "uzaklik": "2,87 milyar km", "sicaklik": "ort. -195 °C", "uydu": "27", "kesif": "1781 (Herschel)"},
    "neptune": {"tur": "Buz devi", "cap": "49.244 km", "cap_km": 49244, "kutle": "17,1 Dünya", "cekim": "11,15 m/s²", "gun": "16 sa 6 dk", "yil": "165 yıl", "uzaklik": "4,5 milyar km", "sicaklik": "ort. -200 °C", "uydu": "16", "kesif": "1846 (Galle)"},
    "pluto": {"tur": "Cüce gezegen", "cap": "2.377 km", "cap_km": 2377, "kutle": "0,0022 Dünya", "cekim": "0,62 m/s²", "gun": "6,4 gün", "yil": "248 yıl", "uzaklik": "5,9 milyar km", "sicaklik": "ort. -230 °C", "uydu": "5", "kesif": "1930 (Tombaugh)"},
    "io": {"tur": "Uydu (Jüpiter)", "cap": "3.643 km", "cap_km": 3643, "kutle": "0,015 Dünya", "cekim": "1,80 m/s²", "gun": "1,77 gün", "yil": "1,77 gün", "uzaklik": "Jüpiter'e 421.700 km", "sicaklik": "ort. -130 °C", "uydu": "yok", "kesif": "1610 (Galileo)"},
    "europa": {"tur": "Uydu (Jüpiter)", "cap": "3.122 km", "cap_km": 3122, "kutle": "0,008 Dünya", "cekim": "1,31 m/s²", "gun": "3,55 gün", "yil": "3,55 gün", "uzaklik": "Jüpiter'e 671.100 km", "sicaklik": "ort. -160 °C", "uydu": "yok", "kesif": "1610 (Galileo)"},
    "ganymede": {"tur": "Uydu (Jüpiter)", "cap": "5.268 km", "cap_km": 5268, "kutle": "0,025 Dünya", "cekim": "1,43 m/s²", "gun": "7,15 gün", "yil": "7,15 gün", "uzaklik": "Jüpiter'e 1.070.400 km", "sicaklik": "ort. -160 °C", "uydu": "yok", "kesif": "1610 (Galileo)"},
    "callisto": {"tur": "Uydu (Jüpiter)", "cap": "4.821 km", "cap_km": 4821, "kutle": "0,018 Dünya", "cekim": "1,24 m/s²", "gun": "16,7 gün", "yil": "16,7 gün", "uzaklik": "Jüpiter'e 1.882.700 km", "sicaklik": "ort. -140 °C", "uydu": "yok", "kesif": "1610 (Galileo)"},
    "titan": {"tur": "Uydu (Satürn)", "cap": "5.150 km", "cap_km": 5150, "kutle": "0,0225 Dünya", "cekim": "1,35 m/s²", "gun": "15,9 gün", "yil": "15,9 gün", "uzaklik": "Satürn'e 1.221.870 km", "sicaklik": "ort. -179 °C", "uydu": "yok", "kesif": "1655 (Huygens)"},
    "enceladus": {"tur": "Uydu (Satürn)", "cap": "504 km", "cap_km": 504, "kutle": "0,00002 Dünya", "cekim": "0,11 m/s²", "gun": "1,37 gün", "yil": "1,37 gün", "uzaklik": "Satürn'e 238.000 km", "sicaklik": "ort. -201 °C", "uydu": "yok", "kesif": "1789 (Herschel)"},
    "triton": {"tur": "Uydu (Neptün)", "cap": "2.707 km", "cap_km": 2707, "kutle": "0,0036 Dünya", "cekim": "0,78 m/s²", "gun": "5,88 gün (ters)", "yil": "5,88 gün", "uzaklik": "Neptün'e 354.800 km", "sicaklik": "ort. -235 °C", "uydu": "yok", "kesif": "1846 (Lassell)"},
    "charon": {"tur": "Uydu (Plüton)", "cap": "1.212 km", "cap_km": 1212, "kutle": "0,0003 Dünya", "cekim": "0,29 m/s²", "gun": "6,39 gün", "yil": "6,39 gün", "uzaklik": "Plüton'a 19.600 km", "sicaklik": "ort. -220 °C", "uydu": "yok", "kesif": "1978 (Christy)"},
    "ceres": {"tur": "Cüce gezegen", "cap": "946 km", "cap_km": 946, "kutle": "0,00016 Dünya", "cekim": "0,28 m/s²", "gun": "9 sa 4 dk", "yil": "4,6 yıl", "uzaklik": "414 milyon km", "sicaklik": "ort. -105 °C", "uydu": "yok", "kesif": "1801 (Piazzi)"},
    "halley": {"tur": "Kuyruklu yıldız", "cap": "yaklaşık 11 km", "cap_km": 11, "kutle": "bilinmiyor", "cekim": "çok düşük", "gun": "52 sa", "yil": "76 yıl", "uzaklik": "ort. 2.660 milyon km", "sicaklik": "bilinmiyor", "uydu": "yok", "kesif": "antik çağdan beri"},
    "eris": {"tur": "Cüce gezegen", "cap": "2.326 km", "cap_km": 2326, "kutle": "0,0028 Dünya", "cekim": "0,82 m/s²", "gun": "bilinmiyor", "yil": "558 yıl", "uzaklik": "ort. 10.170 milyon km", "sicaklik": "yaklaşık -243 °C", "uydu": "1", "kesif": "2005 (Brown)"},
}

LAYERS = {
    "sun": [("Çekirdek", 0.25), ("Işınım bölgesi", 0.7), ("Taşınım bölgesi", 1.0)],
    "mercury": [("Demir çekirdek", 0.85), ("Manto", 0.99), ("Kabuk", 1.0)],
    "venus": [("Çekirdek", 0.55), ("Manto", 0.99), ("Kabuk", 1.0)],
    "earth": [("İç çekirdek", 0.19), ("Dış çekirdek", 0.55), ("Manto", 0.99), ("Kabuk", 1.0)],
    "moon": [("Küçük çekirdek", 0.2), ("Manto", 0.78), ("Kabuk", 1.0)],
    "mars": [("Çekirdek", 0.53), ("Manto", 0.95), ("Kabuk", 1.0)],
    "jupiter": [("Kayalık çekirdek", 0.2), ("Metalik hidrojen", 0.9), ("Gaz katmanı", 1.0)],
    "saturn": [("Kayalık çekirdek", 0.3), ("Metalik hidrojen", 0.8), ("Gaz katmanı", 1.0)],
    "uranus": [("Kayalık çekirdek", 0.3), ("Buz manto", 0.85), ("Gaz katmanı", 1.0)],
    "neptune": [("Kayalık çekirdek", 0.3), ("Buz manto", 0.85), ("Gaz katmanı", 1.0)],
    "pluto": [("Kayalık çekirdek", 0.7), ("Buz kabuğu", 1.0)],
    "io": [("Demir-sülfür çekirdek", 0.4), ("Silikat manto", 0.98), ("Kabuk", 1.0)],
    "europa": [("Kayalık çekirdek", 0.6), ("Su okyanusu", 0.9), ("Buz kabuğu", 1.0)],
    "ganymede": [("Demir çekirdek", 0.4), ("Kayalık manto", 0.75), ("Tuzlu su okyanusu", 0.9), ("Buz kabuğu", 1.0)],
    "callisto": [("Kayalık çekirdek", 0.5), ("Buz-su karışımı", 0.9), ("Buz kabuğu", 1.0)],
    "titan": [("Kayalık çekirdek", 0.6), ("Yüksek basınçlı buz", 0.9), ("Buz kabuğu", 1.0)],
    "enceladus": [("Kayalık çekirdek", 0.6), ("Tuzlu su okyanusu", 0.9), ("Buz kabuğu", 1.0)],
    "triton": [("Kayalık çekirdek", 0.7), ("Buz manto", 0.95), ("Buz kabuğu", 1.0)],
    "charon": [("Kayalık çekirdek", 0.6), ("Buz kabuğu", 1.0)],
    "ceres": [("Kaya çekirdek", 0.5), ("Buzlu manto", 0.9), ("Kabuk", 1.0)],
    "eris": [("Kayalık çekirdek", 0.7), ("Buz kabuğu", 1.0)],
}

ATMO = {
    "sun": [("Hidrojen", 92.1), ("Helyum", 7.8)],
    "venus": [("Karbondioksit", 96.5), ("Azot", 3.5)],
    "earth": [("Azot", 78.1), ("Oksijen", 20.9), ("Argon", 0.9)],
    "mars": [("Karbondioksit", 95.1), ("Azot", 2.7), ("Argon", 1.6)],
    "jupiter": [("Hidrojen", 89.8), ("Helyum", 10.2)],
    "saturn": [("Hidrojen", 96.3), ("Helyum", 3.3)],
    "uranus": [("Hidrojen", 82.5), ("Helyum", 15.2), ("Metan", 2.3)],
    "neptune": [("Hidrojen", 80.0), ("Helyum", 19.0), ("Metan", 1.5)],
    "titan": [("Azot", 98.4), ("Metan", 1.4)],
    "triton": [("Azot", 99.9)],
}

MISSIONS = {
    "sun": [(1995, "SOHO", "Güneş'i sürekli izleyen gözlemevi"), (2018, "Parker Güneş Sondası", "Koronaya en yakın uçuşlar"), (2020, "Solar Orbiter", "Güneş'in kutup bölgelerini görüntüledi")],
    "mercury": [(1974, "Mariner 10", "Merkür'ün ilk yakın uçuşları"), (2011, "MESSENGER", "Merkür'ün yörüngesine girdi"), (2018, "BepiColombo", "Merkür'e gitmek üzere yola çıktı")],
    "venus": [(1970, "Venera 7", "Venüs yüzeyine inip veri gönderen ilk araç"), (1978, "Pioneer Venus", "Venüs'ü yörüngeden inceledi"), (1990, "Magellan", "Venüs yüzeyini radarla haritaladı")],
    "moon": [(1959, "Luna 2", "Ay'a ulaşan ilk insan yapımı cisim"), (1966, "Luna 9", "Ay'a yumuşak iniş ve yüzey görüntüleri"), (1969, "Apollo 11", "İlk insanlı Ay inişi"), (1972, "Apollo 17", "Apollo programının son Ay görevi")],
    "mars": [(1976, "Viking 1", "İlk başarılı iniş ve yüzey fotoğrafları"), (1997, "Pathfinder", "Sojourner gezgin aracı Mars'ta gezdi"), (2012, "Curiosity", "Gale Krateri'nde yüzeyde çalışıyor"), (2021, "Perseverance", "Jezero Krateri'nde çalışıyor; Ingenuity uçtu")],
    "jupiter": [(1973, "Pioneer 10", "Jüpiter'in yakınından geçen ilk araç"), (1995, "Galileo", "Jüpiter'in yörüngesine girdi, atmosfere dalış yaptı"), (2016, "Juno", "Jüpiter'in kutuplarını ve iç yapısını inceliyor")],
    "saturn": [(1979, "Pioneer 11", "Satürn'ün yakınından ilk geçiş"), (2004, "Cassini-Huygens", "Satürn'ün yörüngesine girdi"), (2005, "Huygens", "Titan'a inen ilk araç"), (2017, "Cassini", "Görevini Satürn'e dalışla tamamladı")],
    "pluto": [(2006, "New Horizons", "Plüton ve Charon'a doğru fırlatıldı"), (2015, "New Horizons", "Plüton'un yakınından geçti")],
    "io": [(1979, "Voyager 1", "Aktif yanardağları ilk kez görüntüledi"), (1995, "Galileo", "Yanardağ patlamalarını yakından izledi")],
    "europa": [(1995, "Galileo", "Buz kabuğundaki çizgi ve çatlakları görüntüledi"), (2024, "Europa Clipper", "Fırlatıldı; 2030'larda Europa'yı inceleyecek")],
    "ganymede": [(1996, "Galileo", "Ganymede'in kendi manyetik alanını ölçtü"), (2023, "JUICE", "Fırlatıldı; Ganymede'i incelemek üzere yola çıktı")],
    "callisto": [(1995, "Galileo", "Yüzeyini birkaç kez yakından gözledi"), (2023, "JUICE", "Callisto'yu da incelemeyi planlıyor")],
    "titan": [(1980, "Voyager 1", "Titan'ın kalın atmosferini yakından gözledi"), (2005, "Huygens", "Titan'a inen ilk araç"), (2017, "Cassini", "Görevini Satürn'e dalışla tamamladı")],
    "enceladus": [(2005, "Cassini", "Güney kutbundaki su jetlerini keşfetti"), (2008, "Cassini", "Jetlerin içinden geçip su ve organik madde ölçtü")],
    "charon": [(2006, "New Horizons", "Plüton ve Charon'a doğru fırlatıldı"), (2015, "New Horizons", "Charon'un ayrıntılı görüntülerini çekti")],
    "ceres": [(2007, "Dawn", "Vesta'nın ardından Ceres'e gönderildi"), (2015, "Dawn", "Bir cüce gezegenin yörüngesine giren ilk araç")],
    "halley": [(1986, "Giotto", "Çekirdeğe en yakın yaklaşım ve yakın görüntüler"), (1986, "Vega 1", "Kuyruklu yıldıza yaklaşarak görüntüledi")],
}


# ---- ek ayrıntılar (2026-11): kaynağı net olan eksikler tamamlandı
ATMO["pluto"] = [("Azot", 90.0), ("Metan", 0.5)]
MISSIONS["uranus"] = [(1986, "Voyager 2", "Uranüs'ün yakınından geçen tek uzay aracı")]
MISSIONS["neptune"] = [(1989, "Voyager 2", "Neptün'ü ziyaret eden tek uzay aracı; Büyük Karanlık Leke'yi gözlemledi")]
MISSIONS["triton"] = [(1989, "Voyager 2", "Triton'un yakınından geçti, ters yönde dönen yüzeyini görüntüledi")]
MISSIONS["halley"] = [(1986, "Giotto", "Halley'in çekirdeğine en yakın geçen uzay aracı"), (1986, "Vega 1 ve Vega 2", "Kuyruklu yıldızın çekirdeğini fotoğrafladı")]
