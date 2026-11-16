"""Kimya laboratuvarı için ek molekül modelleri (chem_data.MOLECULES sonuna eklenir). Koordinatlar bağ uzunluğu (angström) ve
VSEPR bağ açılarından hesaplanır; yaklaşık ama gerçeğe yakındır. Biçim: {'name','formula','geom','polar','desc','atoms':[(sembol,x,y,z)],'bonds':[(i,j,mertebe)]}."""
import math

_TET = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]


def _norm(v, r):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(round(c / n * r, 3) for c in v)


def _mol(name, formula, geom, polar, desc, atoms, bonds):
    return {"name": name, "formula": formula, "geom": geom, "polar": polar, "desc": desc,
            "atoms": [(s, round(x, 3), round(y, 3), round(z, 3)) for s, x, y, z in atoms], "bonds": bonds}


def _central(center, ligs, vecs):
    """merkez atom (0,0,0) + ligandlar: ligs = [(sembol, uzunluk)], vecs = yön vektörleri"""
    atoms = [(center, 0, 0, 0)]
    bonds = []
    for k, ((s, r), v) in enumerate(zip(ligs, vecs)):
        atoms.append((s,) + _norm(v, r))
        bonds.append((0, k + 1, 1))
    return atoms, bonds


def _bent(center, lig, r, ang):
    a = math.radians(ang) / 2
    return _central(center, [(lig, r)] * 2, [(math.sin(a), math.cos(a), 0), (-math.sin(a), math.cos(a), 0)])


def _planar3(center, ligs):
    vec = [(math.cos(math.radians(a)), math.sin(math.radians(a)), 0) for a in (90, 210, 330)]
    return _central(center, ligs, vec)


def build():
    out = []
    a, b = _bent("S", "H", 1.34, 92.1)
    out.append(_mol("Hidrojen sülfür", "H2S", "kırık (açısı yaklaşık 92°)", True, "Çürük yumurta kokulu zehirli gazdır; volkanik gazlarda ve çürüyen organik maddelerde bulunur. Suya göre çok daha zayıf hidrojen bağı yapar, bu yüzden oda koşullarında gazdır.", a, b))
    out.append(_mol("Hidrojen florür", "HF", "doğrusal", True, "Çok kutupludur ve güçlü hidrojen bağı yapar; zayıf bir asittir ama camı çözebildiği için plastik kaplarda saklanır. Dişlere ve kemiğe nüfuz edip ağır yanıklara yol açar.", [("H", -0.46, 0, 0), ("F", 0.46, 0, 0)], [(0, 1, 1)]))
    a, b = _planar3("B", [("F", 1.31)] * 3)
    out.append(_mol("Bor triflorür", "BF3", "üçgen düzlem (120°)", False, "Bor oktetten az elektron taşır (6 elektron), bu yüzden güçlü bir Lewis asididir: ortaklanmamış çifti olan moleküllerden elektron çifti kabul eder. Üç kutuplu bağ vardır ama simetri nedeniyle molekül apolardır.", a, b))
    a, b = _central("C", [("Cl", 1.77)] * 4, _TET)
    out.append(_mol("Karbon tetraklorür", "CCl4", "dörtyüzlü (109,5°)", False, "Dört C–Cl bağı kutupludur ama simetri nedeniyle kutuplar birbirini götürür: molekül apolardır. Eskiden kuru temizlemede ve yangın söndürücülerde kullanıldı; karaciğere zararlı ve ozon tabakasını inceltici olduğu için yasaklanmıştır.", a, b))
    h = (_norm((1, 1, 1), 1.09), _norm((1, -1, -1), 1.09), _norm((-1, 1, -1), 1.09))
    out.append(_mol("Klorometan (metil klorür)", "CH3Cl", "dörtyüzlü", True, "Metan'ın bir hidrojeninin klorla yer değiştirmesiyle oluşur. C–Cl bağı kutuplu olduğundan molekül kutupludur. Eskiden soğutucu gaz olarak kullanıldı; doğada deniz yosunlarından ve yangınlardan da salınır.",
                  [("C", 0, 0, 0), ("H",) + h[0], ("H",) + h[1], ("H",) + h[2], ("Cl",) + _norm((-1, -1, 1), 1.78)], [(0, 1, 1), (0, 2, 1), (0, 3, 1), (0, 4, 1)]))
    a, b = _central("S", [("F", 1.56)] * 6, [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)])
    out.append(_mol("Kükürt hekzaflorür", "SF6", "sekizyüzlü (90°)", False, "Çok kararlı, yalıtkan ve ağır bir gazdır; yüksek gerilim anahtarlarında yalıtım gazı olarak kullanılır. Güçlü bir sera gazıdır: CO₂'den yaklaşık 23.000 kat daha etkilidir. Kükürt burada oktetten fazla elektron (12) taşır.", a, b))
    out.append(_mol("Hidrojen siyanür", "HCN", "doğrusal", True, "Çok zehirli, bademimsi kokulu bir gazdır; hücresel solunumu engeller. Kayısı, elma ve badem çekirdeklerinde çok az miktarda bağlı hâlde bulunur. Karbon-azot arasında üçlü bağ vardır.", [("H", -1.06, 0, 0), ("C", 0, 0, 0), ("N", 1.16, 0, 0)], [(0, 1, 1), (1, 2, 3)]))
    out.append(_mol("Diazot monoksit (gülme gazı)", "N2O", "doğrusal", True, "Anestezik ve ağrı kesici olarak diş hekimliğinde kullanılır; krem şantide itici gaz olarak bulunur. Aynı zamanda CO₂'den yaklaşık 300 kat daha güçlü bir sera gazıdır.", [("N", -1.13, 0, 0), ("N", 0, 0, 0), ("O", 1.19, 0, 0)], [(0, 1, 3), (1, 2, 2)]))
    out.append(_mol("Formaldehit", "CH2O", "üçgen düzlem", True, "En basit aldehittir. Sulu çözeltisi (formalin) numune saklamada ve dezenfektanda kullanılır. Reçine ve plastik üretiminin hammaddesidir; zehirli ve tahriş edicidir.",
                  [("C", 0, 0, 0), ("O", 1.21, 0, 0), ("H", -0.58, 0.94, 0), ("H", -0.58, -0.94, 0)], [(0, 1, 2), (0, 2, 1), (0, 3, 1)]))
    # etan: iki CH3, kayık konum
    atoms = [("C", -0.77, 0, 0), ("C", 0.77, 0, 0)]
    bonds = [(0, 1, 1)]
    for sign, base in ((-1, 0), (1, 60)):
        for k in range(3):
            phi = math.radians(base + 120 * k)
            atoms.append(("H", sign * 0.77 - sign * -0.36 * -1 if False else sign * (0.77 + 0.36), 1.03 * math.cos(phi), 1.03 * math.sin(phi)))
            bonds.append((0 if sign < 0 else 1, len(atoms) - 1, 1))
    out.append(_mol("Etan", "C2H6", "her karbon dörtyüzlü (kayık konum)", False, "İkinci en basit alkandır; doğal gazın yaklaşık %5-10'unu oluşturur. Etilen (plastik hammaddesi) üretiminde kullanılır. C–C bağı etrafında CH₃ grupları serbestçe döner.", atoms, bonds))
    out.append(_mol("Klor", "Cl2", "doğrusal", False, "Sarı-yeşil, boğucu kokulu zehirli gazdır. İçme suyu ve havuz dezenfeksiyonunda, ayrıca PVC ve çamaşır suyu üretiminde kullanılır. Birinci Dünya Savaşı'nda kimyasal silah olarak kullanılmıştır.", [("Cl", -0.995, 0, 0), ("Cl", 0.995, 0, 0)], [(0, 1, 1)]))
    out.append(_mol("Flor", "F2", "doğrusal", False, "En reaktif elementin iki atomlu gazıdır; hemen hemen her maddeyle, cam ve su dahil, tepkimeye girer. Bağı zayıf olduğu için çok etkindir.", [("F", -0.71, 0, 0), ("F", 0.71, 0, 0)], [(0, 1, 1)]))
    out.append(_mol("Azot monoksit", "NO", "doğrusal", True, "Tek sayıda elektronlu bir moleküldür (radikal). Canlıda kan damarlarını genişleten bir sinyal molekülüdür (1998 Nobel Tıp), atmosferde yıldırımla ve motorlarda oluşur, havada hızla NO₂'ye dönüşür.", [("N", -0.575, 0, 0), ("O", 0.575, 0, 0)], [(0, 1, 2)]))
    a, b = _central("N", [("H", 1.03)] * 4, _TET)
    out.append(_mol("Amonyum iyonu", "NH4+", "dörtyüzlü (109,5°)", False, "Amonyağın bir proton alarak oluşturduğu pozitif yüklü iyondur. Gübrelerin (amonyum nitrat, amonyum sülfat) temel bileşenidir. Dört N–H bağının biri koordinat kovalent bağdır ama hepsi eşdeğerdir.", a, b))
    a, b = _planar3("C", [("O", 1.29)] * 3)
    out.append(_mol("Karbonat iyonu", "CO3^2-", "üçgen düzlem (120°)", False, "Kireçtaşı, mermer, deniz kabuğu ve kabartma tozunun anyonudur. Elektronlar üç oksijen arasında eşit paylaşıldığı için üç C–O bağı aynı uzunluktadır (rezonans yapı).", a, b))
    a, b = _central("S", [("O", 1.43), ("O", 1.43), ("O", 1.57), ("O", 1.57)], _TET)
    ox = len(a)
    a = a + [("H",) + tuple(round(c, 3) for c in (a[3][1] + 0.5, a[3][2] + 0.6, a[3][3] + 0.3)), ("H",) + tuple(round(c, 3) for c in (a[4][1] + 0.5, a[4][2] - 0.6, a[4][3] + 0.3))]
    b = b + [(3, ox, 1), (4, ox + 1, 1)]
    b[0], b[1] = (0, 1, 2), (0, 2, 2)
    out.append(_mol("Sülfürik asit", "H2SO4", "kükürt etrafında dörtyüzlü", True, "Dünyada en çok üretilen kimyasaldır; gübre, akü, boya ve deterjan üretiminde kullanılır. Çok güçlü bir asit ve güçlü bir su çekicidir: şekeri ve kâğıdı kömürleştirir. Seyreltirken asit suya eklenir, tersi yapılmaz.", a, b))
    return out
