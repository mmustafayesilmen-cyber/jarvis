"""Fizik, astronomi ve jeoloji laboratuvarları için ek simülasyonlar: veri girdileri, hesaplar ve sesle parametre desenleri.
Çizim kodu ui/scene_sci.html içindedir (dDoppler, dKaldirma, dKacis, dHubble, dTsunami). Girdiler sci_data/sci_data2 listelerine eklenir."""
import math

FIZ_SIM_X = [
    {"key": "doppler", "name": "Doppler etkisi", "aim": "Kaynak ya da gözlemci hareket edince duyulan frekansın nasıl değiştiğini görmek.",
     "params": [("vs", "Kaynak hızı", "m/s", 0, 400, 60, 5), ("f0", "Kaynak frekansı", "Hz", 100, 2000, 500, 50), ("vo", "Gözlemci hızı (kaynağa doğru)", "m/s", 0, 100, 0, 5)],
     "formulas": ["Yaklaşan kaynak: f' = f0 · (c + vo) / (c − vs)", "Uzaklaşan kaynak: f' = f0 · (c − vo) / (c + vs)", "Ses hızı c ≈ 343 m/s (20 °C)", "Süpersonik (vs > c): Mach açısı sin θ = c / vs"],
     "why": "Kaynak yaklaşırken dalga cepheleri sıkışır, dalga boyu kısalır ve frekans yükselir; uzaklaşırken uzar ve frekans düşer. Ambulans sireninin geçerken 'iyuuu' diye ince sesten kalın sese inmesi bu yüzdendir. Işıkta aynı etki, uzak galaksilerin kırmızıya kaymasına yol açar.",
     "alias": "doppler|siren|ambulans|frekans kayması|yaklaşan kaynak|mach"},
    {"key": "kaldirma", "name": "Arşimet kaldırma kuvveti", "aim": "Bir cismin sıvıda yüzmesi ya da batmasının yoğunluklara bağlı olduğunu görmek.",
     "params": [("ro", "Cismin yoğunluğu", "kg/m³", 100, 12000, 600, 50), ("V", "Cismin hacmi", "L", 1, 50, 10, 1), ("rs", "Sıvının yoğunluğu", "kg/m³", 700, 13600, 1000, 50)],
     "formulas": ["Kaldırma kuvveti: F = ρ_sıvı · V_batan · g", "Ağırlık: G = ρ_cisim · V · g", "Yüzme şartı: ρ_cisim < ρ_sıvı", "Batan hacim oranı: ρ_cisim / ρ_sıvı (yüzerken)"],
     "why": "Sıvıya batan cisim, yer değiştirdiği sıvının ağırlığı kadar yukarı itilir (Arşimet prensibi). Kaldırma, ağırlıktan büyükse cisim yüzer ve yalnızca yoğunluk oranı kadarı batar; küçükse batar. Buz (917 kg/m³) suda %92 batar, deniz suyunda (1025) %89; cıvada ise demir bile yüzer.",
     "alias": "arşimet|kaldırma|yüz\\w*|bat\\w*|yoğunluk|buz dağı|gemi"},
]

AST_SIM_X = [
    {"key": "kacis", "name": "Kaçış hızı ve yüzey çekimi", "aim": "Bir gökcisminin kütlesi ve yarıçapının çekimi ve kaçış hızını nasıl belirlediğini görmek.",
     "params": [("M", "Kütle (Dünya = 1)", "M⊕", 0.01, 400, 1, 0.01), ("R", "Yarıçap (Dünya = 1)", "R⊕", 0.1, 12, 1, 0.05)],
     "formulas": ["Yüzey çekimi: g = G·M / R² (Dünya'da 9,81 m/s²)", "Kaçış hızı: v = √(2·G·M / R) (Dünya'da 11,19 km/s)", "Dairesel yörünge hızı (yüzeyde): v/√2", "Kütle 4 kat, yarıçap 2 kat olursa çekim aynı kalır, kaçış hızı √2 kat artar"],
     "why": "Kaçış hızı, bir cismi yüzeyden sonsuza götürmek için gereken en küçük başlangıç hızıdır; yalnızca kütleye ve yarıçapa bağlıdır, cismin kütlesine bağlı değildir. Ay'ın düşük çekimi (2,4 km/s) atmosferini tutamaz; Jüpiter'in (59,5 km/s) hidrojeni bile tutar. Kütleyi ışığın kaçamayacağı kadar sıkıştırırsanız kara delik elde edersiniz.",
     "alias": "kaçış hızı ve yüzey|yüzey çekimi|çekim ivmesi|gezegen çekimi|kütle ve yarıçap"},
    {"key": "hubble", "name": "Hubble yasası: genişleyen evren", "aim": "Galaksilerin uzaklaşma hızının uzaklıkla orantılı olduğunu ve evrenin yaşını tahmin etmeyi görmek.",
     "params": [("d", "Galaksinin uzaklığı", "Mpc", 1, 1000, 200, 1), ("H0", "Hubble sabiti", "km/s/Mpc", 50, 100, 70, 1)],
     "formulas": ["v = H0 · d", "Kırmızıya kayma: z ≈ v / c (c = 299.792 km/s)", "Evrenin yaşı (kabaca): t ≈ 1 / H0 ≈ 977,8 / H0 milyar yıl", "1 Mpc ≈ 3,26 milyon ışık yılı"],
     "why": "Uzak galaksilerin ışığı, uzaklaştıkları için kırmızıya kayar ve uzaklıkla orantılı hızla gider. Bunun anlamı evrenin genişlemesidir: galaksiler uzayda hareket etmez, aralarındaki uzay büyür. H0'ın tersi, genişlemenin geçmişe sarıldığında bir noktada başladığı süreyi, yani evrenin yaklaşık 14 milyar yıllık yaşını verir.",
     "alias": "hubble|genişleyen evren|evren genişle\\w*|kırmızıya kayma|evrenin yaşı|galaksiler uzaklaş\\w*"},
]

GEO_SIM_X = [
    {"key": "tsunami", "name": "Tsunami hızı ve kıyıya varış süresi", "aim": "Tsunaminin okyanus derinliğine göre hızını ve kıyıya varış süresini hesaplamak.",
     "params": [("h", "Okyanus derinliği", "m", 10, 6000, 4000, 10), ("d", "Kıyıya uzaklık", "km", 10, 10000, 2000, 10)],
     "formulas": ["Dalga hızı: v = √(g · h)   (g = 9,81 m/s²)", "Varış süresi: t = uzaklık / v", "Kıyıya yaklaşırken derinlik azalır, hız düşer, dalga yüksekliği artar (Green yasası: A ∝ h^(−1/4))"],
     "why": "Tsunami dalgasının dalga boyu yüzlerce kilometre olduğundan tüm su sütununu hareket ettirir ve hızı derinliğe bağlıdır. 4000 metrede yaklaşık 200 m/s (saatte 700 km) ile ilerler: Pasifik'i yaklaşık 10 saatte geçer. Kıyıya yaklaşıp derinlik azalınca yavaşlar ve enerji sıkışarak dalga yüksekliği birkaç metreden onlarca metreye çıkar.",
     "alias": "tsunami|deniz depremi|dev dalga|kıyıya varış|okyanus dalgası"},
]

PARAM_PAT_X = {
    ("doppler", "vs"): r"kaynak hız\w*|hız\w*|sürat\w*", ("doppler", "f0"): r"frekans\w*", ("doppler", "vo"): r"gözlemci\w*",
    ("kaldirma", "ro"): r"cisim\w* yoğunluk\w*|cisim\w*|yoğunluk\w*", ("kaldirma", "V"): r"hacim\w*", ("kaldirma", "rs"): r"sıvı\w* yoğunluk\w*|sıvı\w*",
    ("kacis", "M"): r"kütle\w*", ("kacis", "R"): r"yarıçap\w*|yarı çap\w*",
    ("hubble", "d"): r"uzaklık\w*|mesafe\w*", ("hubble", "H0"): r"hubble sabit\w*|sabit\w*",
    ("tsunami", "h"): r"derinlik\w*", ("tsunami", "d"): r"uzaklık\w*|mesafe\w*|kıyı\w*",
}


def results(key, p):
    """(satırlar, sözlü özet) ya da None (bu modülün deneyi değilse)."""
    from scenes_sci import fmt
    if key == "doppler":
        c, vs, f0, vo = 343.0, p["vs"], p["f0"], p["vo"]
        if vs >= c:
            ang = math.degrees(math.asin(c / vs))
            return ([f"Mach sayısı: {fmt(vs / c, False)}", f"Mach konisi yarı açısı: {fmt(ang, False)}°", "Kaynak sesten hızlı: önünde ses duyulmaz, şok dalgası (sonik patlama) oluşur."],
                    f"Kaynak sesten hızlı, Mach {fmt(vs / c)}. Şok dalgası {fmt(ang)} derecelik bir koni oluşturur; yaklaşırken ses duyulmaz.")
        fa, fu = f0 * (c + vo) / (c - vs), f0 * (c - vo) / (c + vs)
        return ([f"Yaklaşırken duyulan: {fmt(fa, False)} Hz", f"Uzaklaşırken duyulan: {fmt(fu, False)} Hz", f"Frekans farkı: {fmt(fa - fu, False)} Hz"],
                f"Kaynak yaklaşırken {fmt(fa)} hertz, uzaklaşırken {fmt(fu)} hertz duyulur; kaynağın gerçek frekansı {fmt(f0)} hertz.")
    if key == "kaldirma":
        ro, V, rs, g = p["ro"], p["V"] / 1000.0, p["rs"], 9.81
        G = ro * V * g
        if ro < rs:
            frac = ro / rs
            return ([f"Cisim yüzer: batan hacim %{fmt(frac * 100, False)}", f"Ağırlık: {fmt(G, False)} N", f"Tam batık olsa kaldırma: {fmt(rs * V * g, False)} N"],
                    f"Cismin yoğunluğu sıvıdan küçük, yüzer; hacminin yüzde {fmt(frac * 100)} kadarı batar.")
        F = rs * V * g
        return ([f"Cisim batar", f"Ağırlık: {fmt(G, False)} N", f"Kaldırma kuvveti: {fmt(F, False)} N", f"Net aşağı kuvvet: {fmt(G - F, False)} N"],
                f"Cismin yoğunluğu sıvıdan büyük, batar. Ağırlık {fmt(G)} newton, kaldırma {fmt(F)} newton.")
    if key == "kacis":
        M, R = p["M"], p["R"]
        g = 9.81 * M / (R * R)
        ve = 11.186 * math.sqrt(M / R)
        return ([f"Yüzey çekimi: {fmt(g, False)} m/s²", f"Kaçış hızı: {fmt(ve, False)} km/s", f"Yüzeyde dairesel yörünge hızı: {fmt(ve / math.sqrt(2), False)} km/s"],
                f"Yüzey çekimi {fmt(g)} metre bölü saniye kare, kaçış hızı saniyede {fmt(ve)} kilometre.")
    if key == "hubble":
        d, H0 = p["d"], p["H0"]
        v = H0 * d
        z = v / 299792.458
        return ([f"Uzaklaşma hızı: {fmt(v, False)} km/s", f"Kırmızıya kayma z ≈ {fmt(z, False)}", f"Uzaklık: {fmt(d * 3.2616, False)} milyon ışık yılı", f"Evrenin yaşı (1/H0): {fmt(977.8 / H0, False)} milyar yıl"],
                f"Galaksi saniyede {fmt(v)} kilometre hızla uzaklaşıyor, kırmızıya kayma yaklaşık {fmt(z)}. H0 değerine göre evrenin yaşı yaklaşık {fmt(977.8 / H0)} milyar yıl.")
    if key == "tsunami":
        h, d = p["h"], p["d"]
        v = math.sqrt(9.81 * h)
        t = d * 1000 / v / 3600
        vs = math.sqrt(9.81 * 10)
        return ([f"Dalga hızı: {fmt(v, False)} m/s ({fmt(v * 3.6, False)} km/h)", f"Kıyıya varış süresi: {fmt(t, False)} saat", f"10 metre derinlikte hız: {fmt(vs * 3.6, False)} km/h"],
                f"Tsunami bu derinlikte saniyede {fmt(v)} metre, yani saatte {fmt(v * 3.6)} kilometre hızla gider ve kıyıya yaklaşık {fmt(t)} saatte varır.")
    return None
