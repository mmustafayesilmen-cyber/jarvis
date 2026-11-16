"""Kimya laboratuvarı verisi ve hesaplayıcıları: 118 element, moleküller, deneyler, pH, güvenlik, mol/denkleştirme."""
import re
from fractions import Fraction

# (sembol, Türkçe ad, standart atom kütlesi, kategori)
_E = """H Hidrojen 1.008 nmt|He Helyum 4.0026 nbl|Li Lityum 6.94 alk|Be Berilyum 9.0122 ear|B Bor 10.81 mtl|C Karbon 12.011 nmt|N Azot 14.007 nmt|O Oksijen 15.999 nmt|F Flor 18.998 hal|Ne Neon 20.180 nbl|
Na Sodyum 22.990 alk|Mg Magnezyum 24.305 ear|Al Alüminyum 26.982 pst|Si Silisyum 28.085 mtl|P Fosfor 30.974 nmt|S Kükürt 32.06 nmt|Cl Klor 35.45 hal|Ar Argon 39.948 nbl|
K Potasyum 39.098 alk|Ca Kalsiyum 40.078 ear|Sc Skandiyum 44.956 trn|Ti Titanyum 47.867 trn|V Vanadyum 50.942 trn|Cr Krom 51.996 trn|Mn Mangan 54.938 trn|Fe Demir 55.845 trn|Co Kobalt 58.933 trn|Ni Nikel 58.693 trn|Cu Bakır 63.546 trn|Zn Çinko 65.38 trn|Ga Galyum 69.723 pst|Ge Germanyum 72.630 mtl|As Arsenik 74.922 mtl|Se Selenyum 78.971 nmt|Br Brom 79.904 hal|Kr Kripton 83.798 nbl|
Rb Rubidyum 85.468 alk|Sr Stronsiyum 87.62 ear|Y İtriyum 88.906 trn|Zr Zirkonyum 91.224 trn|Nb Niyobyum 92.906 trn|Mo Molibden 95.95 trn|Tc Teknesyum 98 trn|Ru Rutenyum 101.07 trn|Rh Rodyum 102.91 trn|Pd Paladyum 106.42 trn|Ag Gümüş 107.87 trn|Cd Kadmiyum 112.41 trn|In İndiyum 114.82 pst|Sn Kalay 118.71 pst|Sb Antimon 121.76 mtl|Te Tellür 127.60 mtl|I İyot 126.90 hal|Xe Ksenon 131.29 nbl|
Cs Sezyum 132.91 alk|Ba Baryum 137.33 ear|La Lantan 138.91 lan|Ce Seryum 140.12 lan|Pr Praseodim 140.91 lan|Nd Neodim 144.24 lan|Pm Prometyum 145 lan|Sm Samaryum 150.36 lan|Eu Evropiyum 151.96 lan|Gd Gadolinyum 157.25 lan|Tb Terbiyum 158.93 lan|Dy Disprozyum 162.50 lan|Ho Holmiyum 164.93 lan|Er Erbiyum 167.26 lan|Tm Tulyum 168.93 lan|Yb İterbiyum 173.05 lan|Lu Lütesyum 174.97 lan|
Hf Hafniyum 178.49 trn|Ta Tantal 180.95 trn|W Tungsten 183.84 trn|Re Renyum 186.21 trn|Os Osmiyum 190.23 trn|Ir İridyum 192.22 trn|Pt Platin 195.08 trn|Au Altın 196.97 trn|Hg Cıva 200.59 trn|Tl Talyum 204.38 pst|Pb Kurşun 207.2 pst|Bi Bizmut 208.98 pst|Po Polonyum 209 pst|At Astatin 210 hal|Rn Radon 222 nbl|
Fr Fransiyum 223 alk|Ra Radyum 226 ear|Ac Aktinyum 227 act|Th Toryum 232.04 act|Pa Protaktinyum 231.04 act|U Uranyum 238.03 act|Np Neptünyum 237 act|Pu Plütonyum 244 act|Am Amerisyum 243 act|Cm Küriyum 247 act|Bk Berkelyum 247 act|Cf Kaliforniyum 251 act|Es Aynştaynyum 252 act|Fm Fermiyum 257 act|Md Mendelevyum 258 act|No Nobelyum 259 act|Lr Lavrensiyum 266 act|
Rf Rutherfordyum 267 trn|Db Dubniyum 268 trn|Sg Seaborgiyum 269 trn|Bh Bohriyum 270 trn|Hs Hasyum 277 trn|Mt Meitneryum 278 unk|Ds Darmstadtiyum 281 unk|Rg Röntgenyum 282 unk|Cn Kopernikyum 285 unk|Nh Nihonyum 286 unk|Fl Flerovyum 289 unk|Mc Moskovyum 290 unk|Lv Livermoryum 293 unk|Ts Tennessin 294 unk|Og Oganesson 294 unk"""
ELEMENTS = []
for _tok in _E.replace("\n", "").split("|"):
    _s, _n, _m, _c = _tok.split()
    ELEMENTS.append((_s, _n, float(_m), _c))
assert len(ELEMENTS) == 118, len(ELEMENTS)
SYM = {e[0]: i + 1 for i, e in enumerate(ELEMENTS)}
MASS = {e[0]: e[2] for e in ELEMENTS}
CATS = {"alk": "Alkali metal", "ear": "Toprak alkali metal", "trn": "Geçiş metali", "pst": "Zayıf metal", "mtl": "Yarı metal", "nmt": "Ametal",
        "hal": "Halojen", "nbl": "Soy gaz", "lan": "Lantanit", "act": "Aktinit", "unk": "Özellikleri tam bilinmiyor"}
GAS = {1, 2, 7, 8, 9, 10, 17, 18, 36, 54, 86}
LIQ = {35, 80}


def grid_pos(z: int):
    """(satır, sütun) — 18 sütunlu standart yerleşim; lantanitler 9., aktinitler 10. satırda."""
    if z == 1: return 1, 1
    if z == 2: return 1, 18
    if 3 <= z <= 4: return 2, z - 2
    if 5 <= z <= 10: return 2, z + 8
    if 11 <= z <= 12: return 3, z - 10
    if 13 <= z <= 18: return 3, z
    if 19 <= z <= 36: return 4, z - 18
    if 37 <= z <= 54: return 5, z - 36
    if 55 <= z <= 56: return 6, z - 54
    if 57 <= z <= 71: return 9, z - 54
    if 72 <= z <= 86: return 6, z - 68
    if 87 <= z <= 88: return 7, z - 86
    if 89 <= z <= 103: return 10, z - 86
    return 7, z - 100


def phase(z: int) -> str:
    if z in GAS: return "gaz"
    if z in LIQ: return "sıvı"
    if z >= 100: return "bilinmiyor (muhtemelen katı)"
    return "katı"


# Madelung sırasıyla elektron dağılımı (bazı geçiş metallerinde gerçek dağılım küçük farklarla değişir)
_ORDER = [(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0), (3, 2), (4, 1), (5, 0), (4, 2), (5, 1), (6, 0), (4, 3), (5, 2), (6, 1), (7, 0), (5, 3), (6, 2), (7, 1)]
_EXC = {24: "3d5 4s1", 29: "3d10 4s1", 41: "4d4 5s1", 42: "4d5 5s1", 44: "4d7 5s1", 45: "4d8 5s1", 46: "4d10", 47: "4d10 5s1",
        57: "5d1 6s2", 78: "4f14 5d9 6s1", 79: "4f14 5d10 6s1"}


def shells(z: int):
    """Bohr kabuklarındaki elektron sayıları [K, L, M, ...] (Madelung dolumuna göre)."""
    left, per = z, {}
    for n, l in _ORDER:
        c = min(left, 2 * (2 * l + 1))
        per[n] = per.get(n, 0) + c
        left -= c
        if left <= 0:
            break
    return [per[k] for k in sorted(per)]


def config(z: int) -> str:
    left, parts = z, []
    for n, l in _ORDER:
        c = min(left, 2 * (2 * l + 1))
        if c:
            parts.append(f"{n}{'spdf'[l]}{c}")
        left -= c
        if left <= 0:
            break
    s = " ".join(parts)
    if z in _EXC:
        s += f"  (gerçekte: …{_EXC[z]})"
    return s


FACTS = {
    1: "Evrenin en bol ve en hafif elementi. Yıldızlarda füzyonla helyuma dönüşür; suyun ve tüm organik bileşiklerin parçası.",
    2: "Soy gaz, yanmaz. Güneş'te tayf çizgisiyle keşfedildi (1868), Dünya'da sonradan bulundu. Sıvı hali yaklaşık eksi 269 derece, MR cihazlarını soğutur.",
    3: "En hafif metal, suda yüzer. Suyla tepkimeye girer. Şarj edilebilir lityum-iyon pillerde kullanılır.",
    6: "Yaşamın temeli. Elmas, grafit, grafen ve fullerenler aynı elementin farklı biçimleridir. Karbon-14 ile eski kalıntıların yaşı bulunur.",
    7: "Havanın yaklaşık yüzde 78'i. Amino asitlerin ve DNA'nın parçası. Haber-Bosch yöntemiyle amonyağa, oradan gübreye çevrilir.",
    8: "Havanın yaklaşık yüzde 21'i, suyun kütlece yüzde 89'u. Yanma ve solunum için gerekli. Ozon (O3) onun üç atomlu biçimidir.",
    9: "En elektronegatif element, çok reaktif. Diş macunlarındaki florür diş minesini güçlendirir.",
    10: "Soy gaz. Elektrik verilince kırmızımsı turuncu parlar; neon tabelaların adı buradan gelir.",
    11: "Yumuşak, gümüşi metal; suyla şiddetle tepkimeye girer, bu yüzden yağ altında saklanır. Sofra tuzu NaCl'nin yarısı. Alev testinde sarı renk verir.",
    12: "Yanarken göz alıcı beyaz ışık verir. Bitkilerde klorofilin merkez atomudur.",
    13: "Yer kabuğunun en bol metali. Hafif ve korozyona dayanıklı. Geri dönüştürmek, yeniden üretmekten yaklaşık yüzde 95 daha az enerji harcar.",
    14: "Yer kabuğunun ikinci bol elementi. Kum ve cam silisyum dioksitten yapılır. Yarı iletken olduğu için bilgisayar çiplerinin temelidir.",
    15: "DNA, RNA ve ATP'nin parçası. Kemiklerde ve dişlerde kalsiyum fosfat olarak bulunur. Beyaz fosfor havada kendiliğinden yanabilir.",
    16: "Sarı renkli katı. Volkanik bölgelerde bulunur. Sülfürik asit ve kauçuk vulkanizasyonu için kullanılır.",
    17: "Sarı-yeşil, zehirli bir gaz. Havuz ve içme suyunun dezenfeksiyonunda kullanılır. Sofra tuzunun diğer yarısı.",
    18: "Havanın yaklaşık yüzde 0,93'ü. Soy gaz; ampullerde ve kaynak işlerinde koruyucu gaz olarak kullanılır.",
    19: "Muzda ve birçok bitkide bulunur; sinir ve kalp çalışması için gerekli. Suyla mor alevle tepkimeye girer.",
    20: "Kemik, diş ve kabuklarda bulunur. Kireç taşı ve tebeşirin ana maddesi kalsiyum karbonattır.",
    22: "Çelik kadar sağlam ama yaklaşık yüzde 45 daha hafif. Uçak, implant ve gözlük çerçevelerinde kullanılır.",
    24: "Paslanmaz çeliğe dayanıklılık verir, krom kaplama parlak görünür.",
    26: "Dünya'nın çekirdeğinin ana maddesi. Hemoglobinin merkezinde bulunur ve kanda oksijen taşır. Pas, demirin oksijenle tepkimesidir.",
    27: "Mavi cam ve seramik pigmentlerinde kullanılır. B12 vitamininin merkez atomudur.",
    28: "Paslanmaz çelik ve bozuk paralarda bulunur. Mıknatıslanabilen birkaç elementten biri.",
    29: "Elektriği çok iyi iletir. Havada yeşil patina oluşturur. Kalayla karışımı bronzdur, insanlığın ilk alaşımlarından biri.",
    30: "Galvaniz kaplamada demiri paslanmaktan korur. Pillerde ve sinkoz bileşiklerinde kullanılır.",
    35: "Oda sıcaklığında sıvı olan iki elementten biri (diğeri cıva). Kırmızı-kahverengi, keskin kokulu.",
    47: "Elektriği ve ısıyı en iyi ileten metal. Ayna, takı ve elektronikte kullanılır.",
    50: "Teneke kutuların kaplamasında, lehimde ve bronzda kullanılır.",
    53: "Tiroid hormonlarının yapısında bulunur. Katı hali mor-siyah, buharı mordur. Nişasta ile mavi-siyah renk verir.",
    54: "Soy gaz. Araba far lambalarında ve bazı iyon iticilerinde kullanılır.",
    74: "Metaller arasında en yüksek erime noktasına (yaklaşık 3420 derece) sahiptir; eski ampullerin teli bundan yapılırdı.",
    78: "Değerli ve çok dayanıklı metal. Arabaların katalitik konvertörlerinde zararlı gazları dönüştürür.",
    79: "Paslanmaz, kolay işlenir. Bir gram altın yaklaşık bir metrekare ince yaprağa dövülebilir.",
    80: "Oda sıcaklığında sıvı tek metal. Eski termometrelerde kullanılırdı, buharı zehirlidir.",
    82: "Ağır ve zehirli metal. Aküler ve radyasyondan korunma için kullanılır; eski boyalarda zararlıydı.",
    86: "Radyoaktif soy gaz. Toprak ve kayalardan çıkıp kapalı evlerde birikebilir, havalandırmak önemli.",
    88: "Marie ve Pierre Curie tarafından keşfedildi. Radyoaktif; karanlıkta parladığı için eskiden saat kadranlarında kullanıldı.",
    84: "Marie Curie'nin Polonya'ya saygı olarak adlandırdığı, çok radyoaktif element.",
    92: "Radyoaktif ağır element. Uranyum-235 nükleer santrallerde yakıt olarak kullanılır.",
    94: "Yapay yolla üretilen radyoaktif element; adını Plüton'dan alır.",
    43: "Doğada neredeyse hiç bulunmaz; laboratuvarda üretilen ilk element (1937). Tıbbi görüntülemede kullanılır.",
    113: "Japonya'da keşfedilen ilk element; adı 'Japonya' anlamına gelen Nihon'dan gelir.",
    118: "Periyodik tablonun en son tamamlanan, 7. periyodu bitiren yapay elementi. Çok kararsız, saniyenin kesirlerinde bozunur.",
}


def element_info(z: int) -> dict:
    s, n, m, c = ELEMENTS[z - 1]
    r, col = grid_pos(z)
    fact = FACTS.get(z) or f"{n}: {CATS[c].lower()} grubunda yer alır."
    return {"z": z, "sym": s, "name": n, "mass": m, "cat": c, "catname": CATS[c], "phase": phase(z), "row": r, "col": col,
            "shells": shells(z), "config": config(z), "fact": fact}


def element_say(z: int) -> str:
    e = element_info(z)
    return (f"{e['name']}, sembolü {e['sym']}, atom numarası {z}, atom kütlesi yaklaşık {e['mass']:g}. {e['catname']}, oda sıcaklığında {e['phase']}. {e['fact']}")


def find_element(t: str):
    """'demir', 'fe', 'element 26', '26 numaralı element' -> atom numarası."""
    t = t.strip()
    m = re.search(r"\b(?:element |atom numarası |numara )?(\d{1,3})(?: numaralı| numara)?(?: element)?\b", t)
    if m and re.search(r"element|numara|atom", t) and 1 <= int(m.group(1)) <= 118:
        return int(m.group(1))
    low = t.lower()
    for i, (s, n, m_, c) in enumerate(ELEMENTS, 1):
        nn = n.lower().replace("İ", "i").replace("I", "ı")
        stem = nn[:max(4, len(nn) - 2)]
        if re.search(r"\b" + re.escape(stem), low.replace("İ", "i").replace("I", "ı")):
            return i
    for tok in re.findall(r"\b[A-Za-z]{1,2}\b", t):
        if tok[0].isupper() and tok in SYM and (len(tok) == 2 or t.strip() == tok):
            return SYM[tok]
    m = re.fullmatch(r"([a-z]{1,2})", low)
    if m and m.group(1).capitalize() in SYM:
        return SYM[m.group(1).capitalize()]
    return None


# ------------------------------------------------------------------ MOLEKÜLLER (basit 3B modeller, koordinatlar yaklaşık, Å)
def _mol(name, formula, geom, polar, desc, atoms, bonds):
    return {"name": name, "formula": formula, "geom": geom, "polar": polar, "desc": desc, "atoms": atoms, "bonds": bonds}


MOLECULES = [
    _mol("Hidrojen", "H2", "doğrusal", False, "En basit molekül. Yakıt hücrelerinde ve roketlerde kullanılır; yandığında yalnızca su oluşur.", [("H", -.37, 0, 0), ("H", .37, 0, 0)], [(0, 1, 1)]),
    _mol("Oksijen", "O2", "doğrusal", False, "Havanın yaklaşık yüzde 21'i. Çift bağlıdır. Solunum ve yanma için gerekli.", [("O", -.6, 0, 0), ("O", .6, 0, 0)], [(0, 1, 2)]),
    _mol("Azot", "N2", "doğrusal", False, "Havanın yaklaşık yüzde 78'i. Üçlü bağ çok güçlüdür, bu yüzden azot gazı tepkimeye girmekte isteksizdir.", [("N", -.55, 0, 0), ("N", .55, 0, 0)], [(0, 1, 3)]),
    _mol("Hidrojen klorür", "HCl", "doğrusal", True, "Suda çözününce hidroklorik asit olur; midemizdeki asidin ana maddesidir.", [("Cl", 0, 0, 0), ("H", 1.27, 0, 0)], [(0, 1, 1)]),
    _mol("Su", "H2O", "açısal (104,5°)", True, "Polar bir molekül; hidrojen bağları yüzünden kaynama noktası yüksek, buz sudan hafiftir ve yüzer. Yaşam için çözücü.", [("O", 0, 0, 0), ("H", .76, .59, 0), ("H", -.76, .59, 0)], [(0, 1, 1), (0, 2, 1)]),
    _mol("Karbondioksit", "CO2", "doğrusal", False, "Bağlar polar ama doğrusal olduğu için molekül apolar. Bitkiler fotosentezde kullanır; sera gazıdır; kuru buz katı halidir.", [("C", 0, 0, 0), ("O", -1.16, 0, 0), ("O", 1.16, 0, 0)], [(0, 1, 2), (0, 2, 2)]),
    _mol("Amonyak", "NH3", "üçgen piramit", True, "Keskin kokulu gaz. Gübre ve temizlik ürünlerinde kullanılır. Çamaşır suyuyla asla karıştırılmaz.", [("N", 0, 0, .1), ("H", .94, 0, -.3), ("H", -.47, .81, -.3), ("H", -.47, -.81, -.3)], [(0, 1, 1), (0, 2, 1), (0, 3, 1)]),
    _mol("Metan", "CH4", "düzgün dörtyüzlü", False, "Doğal gazın ana bileşeni. Güçlü bir sera gazıdır. Dört C-H bağı 109,5 derece açı yapar.", [("C", 0, 0, 0), ("H", .63, .63, .63), ("H", -.63, -.63, .63), ("H", -.63, .63, -.63), ("H", .63, -.63, -.63)], [(0, 1, 1), (0, 2, 1), (0, 3, 1), (0, 4, 1)]),
    _mol("Etilen (eten)", "C2H4", "düzlemsel", False, "Çift bağlı hidrokarbon. Plastik (polietilen) üretiminde kullanılır; meyvelerin olgunlaşmasını sağlayan bitki hormonudur.", [("C", -.67, 0, 0), ("C", .67, 0, 0), ("H", -1.24, .93, 0), ("H", -1.24, -.93, 0), ("H", 1.24, .93, 0), ("H", 1.24, -.93, 0)], [(0, 1, 2), (0, 2, 1), (0, 3, 1), (1, 4, 1), (1, 5, 1)]),
    _mol("Asetilen (etin)", "C2H2", "doğrusal", False, "Üçlü bağlı hidrokarbon. Yanınca çok sıcak alev verir, kaynak işinde kullanılır.", [("C", -.6, 0, 0), ("C", .6, 0, 0), ("H", -1.66, 0, 0), ("H", 1.66, 0, 0)], [(0, 1, 3), (0, 2, 1), (1, 3, 1)]),
    _mol("Ozon", "O3", "açısal", True, "Stratosferde Güneş'in zararlı mor ötesi ışınlarını tutar. Yer seviyesinde ise kirletici ve solunum için zararlıdır.", [("O", 0, .34, 0), ("O", -1.09, -.17, 0), ("O", 1.09, -.17, 0)], [(0, 1, 2), (0, 2, 1)]),
    _mol("Hidrojen peroksit", "H2O2", "çarpık, açısal", True, "Yüzde 3'lük çözeltisi yara dezenfektanıdır. Derişik halde yakıcı ve tehlikelidir. Katalizörle su ve oksijene ayrışır.", [("O", -.73, 0, 0), ("O", .73, 0, 0), ("H", -1.07, .87, -.3), ("H", 1.07, -.87, -.3)], [(0, 1, 1), (0, 2, 1), (1, 3, 1)]),
    _mol("Kükürt dioksit", "SO2", "açısal", True, "Volkanlardan ve fosil yakıt yanmasından çıkar; asit yağmurunun nedenlerinden biri. Gıdalarda koruyucu olarak az miktarda kullanılır.", [("S", 0, 0, 0), ("O", -1.24, .74, 0), ("O", 1.24, .74, 0)], [(0, 1, 2), (0, 2, 2)]),
    _mol("Kükürt trioksit", "SO3", "düzlemsel üçgen", False, "Sülfürik asit üretiminin ara ürünü. Suyla şiddetle tepkimeye girer.", [("S", 0, 0, 0), ("O", 1.42, 0, 0), ("O", -.71, 1.23, 0), ("O", -.71, -1.23, 0)], [(0, 1, 2), (0, 2, 2), (0, 3, 2)]),
    _mol("Karbon monoksit", "CO", "doğrusal", True, "Renksiz, kokusuz, çok zehirli gaz. Yetersiz yanmada oluşur; hemoglobine oksijenden güçlü bağlanır. Soba ve kombi güvenliği için önemli.", [("C", -.56, 0, 0), ("O", .56, 0, 0)], [(0, 1, 3)]),
    _mol("Azot dioksit", "NO2", "açısal", True, "Kızıl-kahverengi, zehirli gaz; egzoz gazlarından gelen hava kirliliği ve asit yağmuruna katkıda bulunur.", [("N", 0, 0, 0), ("O", -1.1, .65, 0), ("O", 1.1, .65, 0)], [(0, 1, 2), (0, 2, 1)]),
    _mol("Metanol", "CH3OH", "dörtyüzlü merkezli", True, "En basit alkol. Zehirlidir; içilmez. Yakıt ve çözücü olarak kullanılır.", [("C", 0, 0, 0), ("O", 1.43, 0, 0), ("H", 1.76, .93, 0), ("H", -.36, -.51, .89), ("H", -.36, -.51, -.89), ("H", -.36, 1.02, 0)], [(0, 1, 1), (1, 2, 1), (0, 3, 1), (0, 4, 1), (0, 5, 1)]),
    _mol("Etanol", "C2H5OH", "zikzak", True, "Alkollü içeceklerde ve kolonyada bulunan alkol; çözücü ve dezenfektan. Su ile her oranda karışır.",
         [("C", -1.25, -.2, 0), ("C", 0, .6, 0), ("O", 1.25, -.15, 0), ("H", -1.25, -.85, .89), ("H", -1.25, -.85, -.89), ("H", -2.15, .45, 0), ("H", 0, 1.25, .89), ("H", 0, 1.25, -.89), ("H", 2.0, .4, 0)],
         [(0, 1, 1), (1, 2, 1), (0, 3, 1), (0, 4, 1), (0, 5, 1), (1, 6, 1), (1, 7, 1), (2, 8, 1)]),
    _mol("Benzen", "C6H6", "düzlemsel altıgen", False, "Altı karbonlu halka; elektronlar halka boyunca dağılmıştır (aromatiklik). Birçok boya ve plastiğin hammaddesi; kanserojendir.",
         [("C", 1.4, 0, 0), ("C", .7, 1.21, 0), ("C", -.7, 1.21, 0), ("C", -1.4, 0, 0), ("C", -.7, -1.21, 0), ("C", .7, -1.21, 0),
          ("H", 2.48, 0, 0), ("H", 1.24, 2.15, 0), ("H", -1.24, 2.15, 0), ("H", -2.48, 0, 0), ("H", -1.24, -2.15, 0), ("H", 1.24, -2.15, 0)],
         [(0, 1, 2), (1, 2, 1), (2, 3, 2), (3, 4, 1), (4, 5, 2), (5, 0, 1), (0, 6, 1), (1, 7, 1), (2, 8, 1), (3, 9, 1), (4, 10, 1), (5, 11, 1)]),
    _mol("Sofra tuzu kristali", "NaCl", "iyonik kristal kafes", False, "Moleküller değil, Na+ ve Cl- iyonları değişimli dizilir. Katıyken elektriği iletmez, suda çözününce iletir. Kaynama noktası çok yüksektir.",
         [("Na", -1.4, -1.4, -1.4), ("Cl", 1.4, -1.4, -1.4), ("Cl", -1.4, 1.4, -1.4), ("Na", 1.4, 1.4, -1.4), ("Cl", -1.4, -1.4, 1.4), ("Na", 1.4, -1.4, 1.4), ("Na", -1.4, 1.4, 1.4), ("Cl", 1.4, 1.4, 1.4)],
         [(0, 1, 1), (0, 2, 1), (0, 4, 1), (3, 1, 1), (3, 2, 1), (3, 7, 1), (5, 1, 1), (5, 4, 1), (5, 7, 1), (6, 2, 1), (6, 4, 1), (6, 7, 1)]),
]

# ------------------------------------------------------------------ DENEYLER
def _x(key, name, level, mins, anim, aim, mats, steps, observe, why, safety):
    return {"key": key, "name": name, "level": level, "mins": mins, "anim": anim, "aim": aim, "mats": mats, "steps": steps, "observe": observe, "why": why, "safety": safety}


EXPERIMENTS = [
    _x("lahana", "Kırmızı lahana pH göstergesi", "Kolay", 20, "cabbage", "Evdeki maddelerin asit mi baz mı olduğunu renkle bulmak.",
       ["Kırmızı lahana", "Sıcak su", "Süzgeç", "Şeffaf bardaklar", "Limon suyu, sirke, kabartma tozu, sabunlu su, tuz"],
       ["Lahanayı doğrayıp sıcak suya koyun ve 10 dakika bekleyin.", "Suyu süzün; mor renkli gösterge sıvısı elde edersiniz.", "Her bardağa biraz gösterge koyun.", "Bardaklara sırayla limon suyu, sirke, kabartma tozu, sabunlu su ekleyin."],
       "Asitlerde kırmızı-pembe, nötr çözeltilerde mor, bazlarda mavi-yeşil-sarı renk oluşur.", "Lahanadaki antosiyanin pigmenti, ortamın pH'ına göre yapısını değiştirir ve rengi değişir.", "Sıcak suya dikkat edin. Hiçbir sıvıyı tatmayın."),
    _x("volkan", "Kabartma tozu - sirke volkanı", "Kolay", 15, "volcano", "Asit-baz tepkimesinde karbondioksit gazı oluşumunu görmek.",
       ["Kabartma tozu (sodyum bikarbonat)", "Sirke", "Gıda boyası", "Bulaşık deterjanı", "Şişe, tepsi"],
       ["Şişeyi tepsiye koyun, 2 kaşık kabartma tozu ekleyin.", "Birkaç damla boya ve deterjan ekleyin.", "Üzerine sirke dökün."],
       "Köpüren bir 'lav' taşar.", "Asetik asit, sodyum bikarbonatla tepkimeye girip karbondioksit, su ve sodyum asetat verir. Gaz kabarcıkları deterjanla köpük olur.", "Tepsi kullanın. Gözlerinize bulaştırmayın."),
    _x("fil", "Fil diş macunu (köpük şelalesi)", "Orta", 15, "foam", "Katalizörün tepkimeyi hızlandırmasını görmek.",
       ["Yüzde 3'lük hidrojen peroksit (eczane)", "Kuru maya", "Ilık su", "Bulaşık deterjanı", "Gıda boyası", "Plastik şişe, tepsi"],
       ["Mayayı birkaç kaşık ılık suda çözün.", "Şişeye hidrojen peroksit, deterjan ve boya koyun.", "Maya karışımını ekleyin ve geri çekilin."],
       "Dev bir köpük kolonu yükselir, şişe ısınır.", "Maya, katalaz enzimiyle H2O2'yi su ve oksijene hızla parçalar. Oksijen deterjanla köpük olur; tepkime ısı verir.", "Yalnızca yüzde 3'lük çözelti kullanın. Gözlük takın. Köpük sıcaktır ve yenmez. Derişik peroksit asla kullanmayın."),
    _x("lav", "Lav lambası", "Kolay", 20, "lava", "Yoğunluk ve çözünmezlik farkını gaz kabarcıklarıyla görmek.",
       ["Şeffaf şişe", "Bitkisel yağ", "Su", "Gıda boyası", "Efervesan (köpüren) tablet"],
       ["Şişenin dörtte üçünü yağla, kalanını suyla doldurun.", "Boya damlatın; damlalar yağın içinden suya iner.", "Bir tableti parçalayıp ekleyin."],
       "Renkli su kabarcıkları yukarı çıkıp iner.", "Yağ sudan hafiftir ve karışmaz. Tablet karbondioksit çıkarır; gaz kabarcığı renkli suyu yukarı taşır, gaz çıkınca damla geri düşer.", "Yağlı şişeyi bir kapta çalışın. Tableti yutmayın."),
    _x("sut", "Süt ve deterjanla renk dansı", "Kolay", 10, "milk", "Yüzey gerilimi ve deterjanın etkisini görmek.",
       ["Tam yağlı süt", "Gıda boyaları", "Bulaşık deterjanı", "Kürdan, tabak"],
       ["Tabağa süt koyun.", "Üzerine farklı renklerde birkaç damla boya damlatın.", "Kürdanın ucunu deterjana batırıp sütün ortasına dokundurun."],
       "Renkler hızla dağılıp dönerek karışır.", "Deterjan, sütteki yağ ve proteinle etkileşip yüzey gerilimini düşürür; sıvı hareketi renkleri sürükler.", "Süt yenmez hale gelir, içilmez."),
    _x("yogunluk", "Yoğunluk kulesi", "Orta", 25, "density", "Farklı yoğunluktaki sıvıların üst üste katmanlanması.",
       ["Bal", "Mısır şurubu ya da bal-su", "Bulaşık deterjanı", "Su (boyalı)", "Bitkisel yağ", "Alkol (eczane, çok az, yetişkinle)", "Uzun şeffaf bardak"],
       ["En yoğun sıvıdan başlayarak sırayla yavaşça, bardağın kenarından dökün.", "Her sıvıyı bir öncekinin üstüne kaşıkla yavaş akıtın."],
       "Sıvılar katman katman durur.", "Yoğunluk kütle bölü hacimdir. Daha yoğun sıvı alta, daha az yoğun üste yerleşir.", "Alkol yanıcıdır, ateşten uzak tutun."),
    _x("kristal", "Şeker ya da tuz kristali büyütmek", "Orta", 30, "crystal", "Doymuş çözeltiden kristalleşmeyi izlemek.",
       ["Şeker veya tuz", "Sıcak su", "Cam kavanoz", "İp, kalem"],
       ["Sıcak suya, çözünmeyene kadar şeker ya da tuz katın (doymuş çözelti).", "Çözeltiyi kavanoza alın; ipi kalemle askıya alıp çözeltiye daldırın.", "Birkaç gün hareket ettirmeden bekleyin."],
       "İpte yavaş yavaş kristaller oluşur.", "Su buharlaşır ve çözünürlük azalınca çözünen madde düzenli bir kafes yapısı kurarak kristal olur.", "Sıcak suya dikkat edin. Çocuklar yetişkinle çalışsın."),
    _x("mum", "Mum, bardak ve suyun yükselmesi", "Orta", 10, "candle", "Yanmanın oksijeni tükettiğini ve sıcaklık-basınç ilişkisini görmek.",
       ["Küçük mum", "Tabak", "Su", "Cam bardak", "Kibrit (yetişkin)"],
       ["Tabağa biraz boyalı su koyun, ortasına mumu yerleştirin.", "Mumu yetişkin yakıp bardağı hemen ters çevirin.", "Mumun sönmesini ve suyun yükselmesini izleyin."],
       "Mum söner, bardak içinde su seviyesi yükselir.", "Önce gaz ısınıp genleşir; oksijen yanmayla tükenince ve soğuyunca basınç düşer, dış basınç suyu bardağa iter. Yükselen su, havanın kabaca beşte birinin oksijen olduğunu hatırlatır.", "Ateşle çalışırken yetişkin bulunsun. Saçları toplayın, yanıcı maddeleri uzak tutun."),
    _x("yumurta", "Kabuğu sirkede eriyen yumurta", "Kolay", 5, "bubbles", "Asidin kalsiyum karbonatla tepkimesini görmek.",
       ["Çiğ yumurta", "Sirke", "Bardak"],
       ["Yumurtayı bardağa koyup üzerini sirkeyle kapatın.", "Kabarcıkları izleyin; 1-2 gün bekleyin.", "Sirkeyi değiştirip yumurtayı nazikçe çıkarıp durulayın."],
       "Kabuk erir, yumurta zar tabakasıyla zıplayan bir top gibi kalır.", "Kabuk kalsiyum karbonattır; asetik asitle karbondioksit, su ve kalsiyum asetat oluşur. Zar kalır.", "Çiğ yumurta sonrası ellerinizi yıkayın; yumurtayı yemeyin."),
    _x("limonpil", "Limonlu pil", "Orta", 20, "battery", "Kimyasal enerjiden elektrik üretmek.",
       ["Limonlar (3-4)", "Bakır para ya da tel", "Çinko kaplı çivi (galvaniz)", "Elektrik teli", "LED ya da voltmetre"],
       ["Her limona bir bakır ve bir çinko elektrot batırın (birbirine değmesin).", "Limonları seri bağlayın: birinin bakırı diğerinin çinkosuna.", "Uçlara LED ya da voltmetre bağlayın."],
       "Her limon yaklaşık 0,9 volt verir; LED için üç dört limon gerekir.", "Çinko elektronlarını verir (yükseltgenir), bakır tarafında hidrojen oluşur; limon suyu iyonları taşıyan elektrolittir.", "Güvenli, düşük gerilim. Elektrotlar kirli olabilir, yedirmeyin."),
    _x("elektroliz", "Suyun elektrolizi (düşük voltaj)", "Orta", 25, "electrolysis", "Suyu hidrojen ve oksijene ayırmak.",
       ["9 voltluk pil", "Kabartma tozu (az)", "Su", "İki kurşun kalem ucu ya da paslanmaz tel", "Cam kap"],
       ["Suya bir tutam kabartma tozu katın (iletkenlik için).", "Kalem uçlarını pilin iki ucuna bağlayıp suya batırın, uçlar birbirine değmesin.", "Kabarcıkları izleyin."],
       "Eksi elektrotta daha çok, artı elektrotta daha az kabarcık çıkar.", "2H2O → 2H2 + O2: hidrojenin hacmi oksijenin iki katıdır. Tuz kullanılırsa zehirli klor gazı çıkabilir, bu yüzden kabartma tozu tercih edilir.", "Tuz kullanmayın. Yalnızca 9 volt ve altı. Açık havada çalışın; çıkan gazı toplayıp ateşe yaklaştırmayın."),
    _x("kromato", "Mürekkep kromatografisi", "Kolay", 20, "chroma", "Bir renkteki gizli pigmentleri ayırmak.",
       ["Filtre kağıdı veya kahve filtresi", "Siyah suda yıkanabilir flomaster", "Su", "Bardak"],
       ["Kağıdın alt kenarına flomasterle bir nokta koyun.", "Kağıdın ucunu, nokta suyun üstünde kalacak şekilde suya sokun.", "Su yükselirken bekleyin."],
       "Siyah leke mavi, sarı, kırmızı gibi renk bantlarına ayrılır.", "Su kağıdın liflerinde kılcal olarak yükselir; pigmentler kağıda ve suya farklı yatkınlıkta olduğu için farklı hızlarda taşınır.", "Güvenli. Kalıcı kalemler suyla ayrılmaz."),
    _x("buztuz", "Buz ve tuz: donma noktası düşmesi", "Kolay", 15, "ice", "Çözünenin donma noktasını düşürmesini görmek.",
       ["Buz küpleri", "Sofra tuzu", "Termometre", "İki bardak"],
       ["İki bardağa buz koyun; birine tuz ekleyin.", "Termometreyle iki bardağın sıcaklığını ölçün.", "Dondurma yapmak için tuzlu buzun içine küçük bir kap koyun."],
       "Tuzlu buz, 0 derecenin çok altına (yaklaşık eksi 10 ila eksi 20) iner.", "Tuz, buzun yüzeyindeki suyun donma noktasını düşürür; eriyen buz ısı çekerek karışımı daha da soğutur.", "Çok soğuk yüzeye uzun süre dokunmayın."),
    _x("balon", "Balonu kendiliğinden şişiren tepkime", "Kolay", 10, "balloon", "Gaz çıkışını balonla görmek.",
       ["Şişe", "Sirke", "Kabartma tozu", "Balon, huni"],
       ["Şişeye sirke koyun.", "Balona huniyle kabartma tozu doldurun.", "Balonu şişenin ağzına takın ve tozu şişeye dökün."],
       "Balon karbondioksitle kendiliğinden şişer.", "Asit ve bikarbonat tepkimesi CO2 gazı üretir; gaz hacim kaplar ve balonu şişirir.", "Balonu sıkı takın, şişeyi sallamadan önce açık tutmayın."),
    _x("coz", "Sıcak mı soğuk suda mı daha hızlı çözünür?", "Kolay", 10, "dissolve", "Sıcaklığın çözünme hızına etkisini görmek.",
       ["İki bardak", "Sıcak ve soğuk su", "Şeker küpü ya da toz şeker", "Kronometre"],
       ["İki bardağa aynı miktar su koyun; biri sıcak, biri soğuk olsun.", "Aynı anda birer küp şeker atın.", "Tam çözünene kadar süreyi ölçün."],
       "Sıcak suda şeker belirgin şekilde daha hızlı çözünür.", "Sıcaklık arttıkça moleküllerin kinetik enerjisi artar; çözücü molekülleri çözünen taneciklere daha sık ve güçlü çarpar.", "Sıcak suya dikkat edin."),
    _x("tyndall", "Tyndall etkisi: ışığın yolu görünür olur", "Kolay", 10, "tyndall", "Çözelti ile kolloidi ayırt etmek.",
       ["İki cam bardak", "Su", "Birkaç damla süt", "El feneri", "Karanlık oda"],
       ["Bir bardakta sadece su, diğerinde su ve birkaç damla süt hazırlayın.", "Karanlıkta fenerin ışığını bardaklara yan taraftan tutun."],
       "Sütlü suda ışık demeti görünür, saf suda görünmez.", "Kolloid parçacıkları ışığı saçar; saf suda ışığı saçacak büyüklükte parçacık yoktur.", "Işığı gözlere doğrultmayın."),
    _x("oobleck", "Oobleck: hem katı hem sıvı davranan madde", "Kolay", 15, "oobleck", "Newtoniyen olmayan akışkanı keşfetmek.",
       ["Mısır nişastası", "Su", "Kase"],
       ["Kaseye 2 ölçü nişasta, 1 ölçü su koyun ve karıştırın.", "Hızla yumruklayın, sonra yavaşça elinizi batırın."],
       "Hızlı vurunca sertleşir, yavaşça girince akar.", "Nişasta taneleri sıvı içinde asılıdır; ani basınçta sıkışıp birbirine kilitlenir, yavaşta birbirinin üstünden kayar.", "Lavaboya dökmeyin, tıkar; çöpe atın."),
    _x("biber", "Biber ve sabun", "Kolay", 5, "pepper", "Yüzey gerilimini sabunun nasıl bozduğunu görmek.",
       ["Su dolu tabak", "Karabiber", "Sıvı sabun"],
       ["Suya karabiberi serpin.", "Parmağınızı suya sokun: biber yerinde kalır.", "Sabunlu parmağı batırın."],
       "Biberler hızla kenarlara kaçar.", "Su molekülleri arasındaki yüzey gerilimi sabunla azalır; gerilimi yüksek bölge biberleri çeker ve kenara iter.", "Güvenli."),
    _x("pas", "Pas deneyi: neler demiri paslandırır?", "Orta", 10, "rust", "Paslanmanın su ve oksijene bağlı olduğunu anlamak.",
       ["Dört çivi", "Dört kavanoz", "Su, tuzlu su, kaynatılıp yağ ile kapatılmış su", "Kuru ortam"],
       ["Birinci kavanoz: çivi kuru.", "İkinci: çivi saf suda.", "Üçüncü: çivi tuzlu suda.", "Dördüncü: kaynatılıp soğutulmuş suda, üzeri yağla kapatılmış.", "Birkaç gün gözlemleyin."],
       "Tuzlu suda en hızlı, kuruda ve oksijensizde en yavaş paslanma olur.", "Demir, oksijen ve suyla demir oksit (pas) oluşturur; tuz iyon taşımayı hızlandırır.", "Pas bulaşmış çivilerden yaralanmayın."),
    _x("gizlimurekkep", "Limonlu görünmez mürekkep", "Kolay", 10, "bubbles", "Organik asidin kâğıdı ısıyla kahverengileştirmesi.",
       ["Limon suyu", "Pamuklu çubuk", "Beyaz kâğıt", "Işık ampulü ya da ütü (yetişkin)"],
       ["Limon suyuyla kâğıda bir şey yazın, kurumasını bekleyin.", "Kâğıdı yetişkin ısıtsın (güvenli uzaklıkta lamba)."],
       "Yazı kahverengi olarak belirir.", "Limon suyundaki organik bileşikler kâğıt liflerinden daha çabuk yanar ve koyulaşır.", "Isı kaynağına çok yaklaşmayın; kâğıt yanabilir."),
    _x("gevrek", "Kahvaltılık gevrekte demir", "Kolay", 15, "bubbles", "Gevrek içine katılmış demiri mıknatısla görmek.",
       ["Demirle zenginleştirilmiş gevrek", "Güçlü mıknatıs", "Zip poşet, su"],
       ["Gevreği ezip poşete koyun ve su ekleyin.", "Mıknatısı poşetin dışında dolaştırın.", "Poşeti dikkatle sallayın."],
       "Mıknatıs küçük siyah demir parçacıklarını çeker.", "Bazı gıdalara besin değeri için çok ince demir tozu katılır; saf demir mıknatısa tepki verir.", "Gevrek yenmez hale gelir; güvenli."),
]

SAFETY = [
    "Her deneyde yetişkin gözetimi şart; koruyucu gözlük takın, uzun saçları toplayın.",
    "Hiçbir kimyasalı tatmayın, koklarken kabın üzerinden elinizle hava savurun.",
    "Çamaşır suyu ile amonyağı asla karıştırmayın: zehirli kloramin gazı çıkar.",
    "Çamaşır suyu ile sirke ya da tuz ruhu gibi asitleri asla karıştırmayın: zehirli klor gazı çıkar.",
    "Hidrojen peroksit ile sirkeyi karıştırmayın: aşındırıcı perasetik asit oluşur.",
    "Asitle çalışırken asidi suya ekleyin, suyu asidin üstüne dökmeyin.",
    "Açık alevle yanıcı sıvılar (alkol, aseton, benzin) bir arada olmasın; yanıcı sıvıyı ısıtmayın.",
    "Sodyum, potasyum gibi alkali metaller, sıvı azot, derişik asit ve baz evde ya da okulda öğrencilerce kullanılmaz.",
    "Deney alanında yemek yemeyin ve içecek içmeyin; deney sonrası ellerinizi yıkayın.",
    "Kimyasal atıkları lavaboya ya da çöpe gelişigüzel dökmeyin; kuralına uygun ayırın.",
    "Kırık cam, sıcak sıvı ve elektrik için ayrı dikkat; ıslak elle elektrikli alete dokunmayın.",
    "Yangın söndürücü, ilk yardım çantası ve temiz suyun yerini deneyden önce öğrenin.",
]

PH = [("Akü asidi", 0, "Sülfürik asit çözeltisi; çok güçlü asit, yakıcı."), ("Mide asidi", 1.5, "Hidroklorik asit içerir; besinleri parçalar."),
      ("Limon suyu", 2.0, "Sitrik asit; asidik tat."), ("Sirke", 2.5, "Yaklaşık yüzde 5 asetik asit."), ("Kola", 2.5, "Fosforik ve karbonik asit içerir."),
      ("Portakal suyu", 3.5, "Sitrik ve askorbik asit."), ("Domates", 4.5, "Hafif asidik."), ("Siyah kahve", 5.0, "Hafif asidik."),
      ("Yağmur suyu", 5.6, "Çözünmüş karbondioksit yüzünden doğal olarak hafif asidik."), ("Saf su", 7.0, "Nötr (25 derecede)."),
      ("İnsan kanı", 7.4, "Dar bir aralıkta (7,35-7,45) tutulur; sapma tehlikelidir."), ("Deniz suyu", 8.0, "Hafif bazik; okyanus asitlenmesi yavaşça düşürür."),
      ("Kabartma tozu", 8.3, "Sodyum bikarbonat çözeltisi, zayıf baz."), ("Sabun", 10.0, "Bazik; kaygan hissi verir."), ("Amonyak çözeltisi", 11.5, "Zayıf-orta baz, kokusu keskin."),
      ("Çamaşır suyu", 12.5, "Güçlü bazik ve oksitleyici; asitle karıştırılmaz."), ("Kostik soda", 14.0, "Sodyum hidroksit; çok güçlü baz, yakıcı.")]


# ------------------------------------------------------------------ HESAPLAYICILAR
def _parse_formula(f: str):
    f = f.replace("·", ".").replace("*", ".")
    total = {}
    for part in f.split("."):
        m = re.match(r"^(\d+)(.*)$", part)
        mult, body = (int(m.group(1)), m.group(2)) if m else (1, part)
        stack = [{}]
        i = 0
        while i < len(body):
            ch = body[i]
            if ch in "([":
                stack.append({})
                i += 1
            elif ch in ")]":
                j = i + 1
                while j < len(body) and body[j].isdigit():
                    j += 1
                k = int(body[i + 1:j] or 1)
                top = stack.pop()
                for e, c in top.items():
                    stack[-1][e] = stack[-1].get(e, 0) + c * k
                i = j
            else:
                m2 = re.match(r"([A-Z][a-z]?)(\d*)", body[i:])
                if not m2 or m2.group(1) not in SYM:
                    raise ValueError(f"bilinmeyen öğe: {body[i:i + 2]}")
                e, n = m2.group(1), int(m2.group(2) or 1)
                stack[-1][e] = stack[-1].get(e, 0) + n
                i += len(m2.group(0))
        for e, c in stack[0].items():
            total[e] = total.get(e, 0) + c * mult
    return total


def molar_mass(formula: str) -> float:
    return sum(MASS[e] * c for e, c in _parse_formula(formula).items())


def balance(eq: str):
    """'H2 + O2 -> H2O' -> '2 H2 + O2 -> 2 H2O'. Sağdaki ve soldaki öğe sayıları eşitlenir."""
    sides = re.split(r"\s*(?:->|→|=>|=)\s*", eq.strip())
    if len(sides) != 2:
        raise ValueError("denklem 'girenler -> ürünler' biçiminde olmalı")
    L = [s.strip() for s in sides[0].split("+") if s.strip()]
    R = [s.strip() for s in sides[1].split("+") if s.strip()]
    species = L + R
    comps = [_parse_formula(s) for s in species]
    elems = sorted({e for c in comps for e in c})
    rows = [[Fraction(c.get(e, 0) * (1 if i < len(L) else -1)) for i, c in enumerate(comps)] for e in elems]
    n = len(species)
    # indirgenmiş satır basamak formu
    piv, r = [], 0
    for c in range(n):
        p = next((i for i in range(r, len(rows)) if rows[i][c] != 0), None)
        if p is None:
            continue
        rows[r], rows[p] = rows[p], rows[r]
        rows[r] = [x / rows[r][c] for x in rows[r]]
        for i in range(len(rows)):
            if i != r and rows[i][c] != 0:
                rows[i] = [a - rows[i][c] * b for a, b in zip(rows[i], rows[r])]
        piv.append(c)
        r += 1
    free = [c for c in range(n) if c not in piv]
    if len(free) != 1:
        raise ValueError("bu denklem tek bir çözümle denkleştirilemedi")
    f = free[0]
    sol = [Fraction(0)] * n
    sol[f] = Fraction(1)
    for i, c in enumerate(piv):
        sol[c] = -rows[i][f]
    import math
    den = 1
    for x in sol:
        den = den * x.denominator // math.gcd(den, x.denominator)
    ints = [int(x * den) for x in sol]
    g = 0
    for x in ints:
        g = math.gcd(g, abs(x))
    ints = [x // g for x in ints]
    if any(x <= 0 for x in ints):
        raise ValueError("pozitif bir çözüm bulunamadı")
    fmt = lambda coef, sp: (f"{coef} " if coef != 1 else "") + sp
    return " + ".join(fmt(c, s) for c, s in zip(ints[:len(L)], L)) + " → " + " + ".join(fmt(c, s) for c, s in zip(ints[len(L):], R))


def ph_text(ph: float) -> str:
    if ph < 6.9:
        kind = "asidik"
    elif ph > 7.1:
        kind = "bazik"
    else:
        kind = "nötr"
    h = 10 ** (-ph)
    return f"pH {ph:g}: ortam {kind}. Hidrojen iyonu derişimi yaklaşık {h:.2e} mol/litre, pOH {14 - ph:g}."


FACT_POOL = [
    "Su, katı halinde sıvı halinden daha az yoğundur; bu yüzden buz suda yüzer ve göller yüzeyden donar.",
    "Elmas ve kurşun kalem ucundaki grafit aynı elementin, karbonun farklı biçimleridir.",
    "Altın o kadar kolay işlenir ki bir gram yaklaşık bir metrekare yaprağa dövülebilir.",
    "Neon tabelalarda kırmızı parlayan gaz neondur; diğer renkler farklı gazlar ve kaplamalarla yapılır.",
    "Sıvı helyum, bilinen en düşük sıcaklıklara yakın bir değerde, eksi 269 derecede kaynar.",
    "Bir damla suda yaklaşık 1,7 milyar trilyon (10 üzeri 21) su molekülü bulunur.",
    "Avogadro sayısı 6,022 çarpı 10 üzeri 23'tür; bir mol herhangi bir maddede bu kadar tanecik demektir.",
    "Katı karbondioksit olan kuru buz erimez, doğrudan gaza geçer; bu olaya süblimleşme denir.",
    "Pas, demirin oksijen ve suyla yavaş yanmasıdır.",
    "Kabartma tozu asitle birleşince karbondioksit çıkarır; kekin kabarmasının nedeni budur.",
    "Periyodik tabloyu 1869'da Dmitri Mendeleyev düzenledi ve henüz bulunmamış elementler için boşluk bıraktı.",
    "İnsan vücudunun kütlece yaklaşık yüzde 65'i oksijendir, çoğu su içinde.",
]

from lab_more_ag import ELEMENT_FACTS_X
for _z, _t in ELEMENT_FACTS_X.items():
    FACTS.setdefault(_z, _t)

from lab_more_exp import CHEM_EXP_X, PH_X, SAFETY_X
EXPERIMENTS.extend(CHEM_EXP_X)
PH.extend(PH_X)
PH.sort(key=lambda p: p[1])
SAFETY.extend(SAFETY_X)

from lab_more_mol import build as _build_mol
MOLECULES.extend(_build_mol())
