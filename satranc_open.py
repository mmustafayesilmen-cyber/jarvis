"""Satranç açılış tanıma: oynanan hamle dizisinin (SAN) en uzun eşleşen açılışı (ad, fikir). Hamle sırası beyaz-siyah ardışık yazılır."""

OPEN = [
    ("İtalyan Oyunu", "e4 e5 Nf3 Nc6 Bc4", "Beyaz fili merkeze ve f7 karesine yöneltir; hızlı gelişim ve merkez kontrolü hedefler."),
    ("Giuoco Piano", "e4 e5 Nf3 Nc6 Bc4 Bc5", "İtalyan Oyunu'nun sakin kolu: iki taraf da fillerini aktif karelere çıkarır."),
    ("Evans Gambiti", "e4 e5 Nf3 Nc6 Bc4 Bc5 b4", "Beyaz bir piyon feda ederek merkez ve hızlı atak kazanmaya çalışır."),
    ("İspanyol Oyunu (Ruy Lopez)", "e4 e5 Nf3 Nc6 Bb5", "Beyaz, merkezi koruyan atı baskı altına alır; en köklü açılışlardan biridir."),
    ("Berlin Savunması", "e4 e5 Nf3 Nc6 Bb5 Nf6", "Çok sağlam bir savunmadır; vezirler erken değişir ve oyun uzun, teknik bir oyuna döner."),
    ("İskoç Oyunu", "e4 e5 Nf3 Nc6 d4", "Beyaz hemen merkezi açar; açık oyun ve hızlı gelişim yaratır."),
    ("Rus Savunması (Petrov)", "e4 e5 Nf3 Nf6", "Siyah beyazın e4 piyonuna karşı saldırır; simetrik ve sağlam bir yapı kurar."),
    ("Kral Gambiti", "e4 e5 f4", "Beyaz f piyonunu feda ederek merkez ve açık f hattı kazanmaya çalışır; romantik dönem açılışıdır."),
    ("Viyana Oyunu", "e4 e5 Nc3", "Beyaz önce atı çıkarıp f4 hamlesini hazırlar; esnek bir açık oyundur."),
    ("Sicilya Savunması", "e4 c5", "Siyah, beyazın merkezine kanattan karşı koyar; en keskin ve en çok oynanan savunmadır."),
    ("Sicilya: Açık Varyant", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3", "Beyaz merkezi açar; siyah karşı oyun için kanat hattı kullanır (Najdorf, Dragon, Scheveningen bu yapıdan gelir)."),
    ("Sicilya: Najdorf", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6", "Siyah a6 ile b5 hazırlığı ve esneklik arar; Fischer ve Kasparov'un sevdiği silahtır."),
    ("Fransız Savunması", "e4 e6", "Siyah sağlam bir piyon yapısı kurar ve d5 ile merkeze karşı çıkar; açık fili (c8) sıkışabilir."),
    ("Caro-Kann Savunması", "e4 c6", "Siyah d5 hazırlığı yapar; piyon yapısı sağlamdır ve fil ön plana çıkar."),
    ("İskandinav Savunması", "e4 d5", "Siyah hemen merkez piyonuna saldırır; vezir erken açılır."),
    ("Pirc Savunması", "e4 d6 d4 Nf6 Nc3 g6", "Siyah merkezi beyaza bırakıp sonra kanat ve fianketto ile saldırır."),
    ("Alekhine Savunması", "e4 Nf6", "Siyah beyazı piyonlarla ileri çekmeye teşvik eder, sonra merkezi hedef alır."),
    ("Vezir Gambiti", "d4 d5 c4", "Beyaz c piyonunu sunarak merkez üstünlüğü ister; en köklü kapalı açılıştır."),
    ("Vezir Gambiti Reddedildi", "d4 d5 c4 e6", "Siyah piyonu almaz, sağlam bir yapı kurar."),
    ("Slav Savunması", "d4 d5 c4 c6", "Siyah d5'i c6 ile destekler ve açık fili (c8) dışarı çıkarmayı hedefler."),
    ("Vezir Gambiti Kabul Edildi", "d4 d5 c4 dxc4", "Siyah piyonu alır; beyaz merkezi ve gelişim farkını geri kazanmaya çalışır."),
    ("Kral Hindistan Savunması", "d4 Nf6 c4 g6", "Siyah merkezi beyaza bırakıp sonra karşı vuruşla saldırır; şah tarafı atak hedeflenir."),
    ("Vezir Hindistan Savunması", "d4 Nf6 c4 e6 Nf3 b6", "Siyah fili b7'ye fianketto ederek merkezi uzaktan denetler."),
    ("Nimzo-Hint Savunması", "d4 Nf6 c4 e6 Nc3 Bb4", "Siyah beyazın atını bağlar ve e4'ü denetler; modern ve esnek bir savunmadır."),
    ("Grünfeld Savunması", "d4 Nf6 c4 g6 Nc3 d5", "Siyah merkezi beyaza verip sonra piyon baskısıyla çözer; dinamik ve keskin."),
    ("Londra Sistemi", "d4 d5 Nf3 Nf6 Bf4", "Beyaz basit bir kurulum yapar (fil f4, e3, c3); her karşıya aynı planla oynanabilir."),
    ("Colle Sistemi", "d4 d5 Nf3 Nf6 e3", "Beyaz sakin gelişir ve e4 itişini hedefler."),
    ("Hollanda Savunması", "d4 f5", "Siyah f5 ile e4 karesini denetler; asimetrik ve saldırgan bir kuruluştur."),
    ("İngiliz Açılışı", "c4", "Beyaz kanattan merkezi denetler; esnek, çoğu zaman diğer açılışlarla geçiş yapar."),
    ("Réti Açılışı", "Nf3 d5 c4", "Beyaz merkezi piyonla değil atla ve fianketto ile denetler; hipermodern bir düşüncedir."),
    ("Kral Hindistan Hücumu", "Nf3 d5 g3", "Beyaz fili g2'ye çıkarıp kısa rok yapar; sağlam ve esnek."),
    ("Bird Açılışı", "f4", "Beyaz e5 karesini denetlemek için f piyonunu oynar."),
    ("Larsen Açılışı", "b3", "Beyaz fili b2'ye fianketto ederek uzun diyagonali denetler."),
    ("Kral Piyonu Açılışı", "e4 e5", "En klasik açık oyun: iki taraf da merkezde piyon dengesi kurar."),
    ("Vezir Piyonu Açılışı", "d4 d5", "En klasik kapalı oyun: iki taraf merkezde karşılıklı piyon yapısı kurar."),
    ("Kral Piyonu Açılışı", "e4", "En çok oynanan ilk hamle: merkez, fil ve vezir hatlarını açar."),
    ("Vezir Piyonu Açılışı", "d4", "Merkezde sağlam piyon kurar; stratejik, pozisyonel oyunlara yol açar."),
]


def name_for(san):
    """Oynanan SAN listesine (['e4','e5',...]) en uzun uyan açılışı döndürür: (ad, fikir) ya da None. En az 1, en çok ilk 14 hamle."""
    moves = [m.rstrip("+#!?") for m in san[:14]]
    best = None
    for name, seq, idea in OPEN:
        ms = seq.split()
        if len(ms) <= len(moves) and moves[:len(ms)] == ms and (best is None or len(ms) > best[0]):
            best = (len(ms), name, idea)
    return (best[1], best[2]) if best else None
