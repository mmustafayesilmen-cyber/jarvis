"""Planlama modu: görevler ve ödüller ağ olarak bağlanır; bir ödüle bağlı tüm görevler bitince ödül kazanılır.
Komutları hem ses ('görev ekle ödev yap', 'ödev ile kitap ödülünü bağla') hem sayfa ('@taşı', '@bağla'... gizli komutlar) aynı yoldan gönderir.
Veri planlama.py'de; çıkışı scenes.handle'daki planlama kolu denetler (görev adındaki 'çık' / 'bitti' çıkış sayılmasın)."""
import re

import planlama

HELP = ("Görev ekle, ödev yap ya da ödül ekle, film izle diyebilirsiniz. İki şeyi bağlamak için ödev ile film ödülünü bağla deyin. "
        "Ödevi bitir derseniz görev yeşile döner; bir ödüle bağlı bütün görevler bitince ödül kazanılır. "
        "Ödevi sil, bağını kes, biten görevleri temizle, durum ve geri al da diyebilirsiniz. Sayfada düğümleri sürükleyip bağlayabilirsiniz.")


def _cap(s: str) -> str:
    return ("İ" if s[:1] == "i" else s[:1].upper()) + s[1:]


def _clean(q: str) -> str:
    q = re.sub(r"\b(görev\w*|ödül\w*)\b", " ", q)
    return " ".join(q.split())


def _out(say: str, won=(), extra=None):
    do = {"snap": planlama.snapshot()}
    if won:
        do["won"] = [n["id"] for n in won]
        say = (say + " " if say else "") + " ".join(f"Tebrikler efendim, {n['text']} ödülünü kazandınız!" for n in won)
    if extra:
        do.update(extra)
    return {"do": do, "say": say}


def _node(q: str, t: str = ""):
    return planlama.find(_clean(q), t) or planlama.find(q, t)


def _raw(text: str, st: dict):
    """Sayfanın gizli komutları: @taşı id x y · @bağla a b · @kes a b · @sil id · @tamam id · @ekle g|o ad · @ad id yeni"""
    w = text.strip()[1:].split()
    if not w:
        return None
    c, a = w[0], w[1:]
    rest = (text.strip()[1:].split(None, 2) + ["", ""])[2]          # ekle/ad komutlarında boşluklu metin
    try:
        if c == "taşı" and len(a) == 3:
            planlama.move(a[0], float(a[1]), float(a[2]))
            return {"do": {"snap": planlama.snapshot()}, "say": ""}
        if c == "tamam" and a:
            _, won = planlama.toggle(a[0])
            return _out("", won)
        if c == "bağla" and len(a) == 2:
            _, won = planlama.link(a[0], a[1])
            return _out("", won)
        if c == "kes" and len(a) == 2:
            _, won = planlama.unlink(a[0], a[1])
            return _out("", won)
        if c == "sil" and a:
            _, won = planlama.remove(a[0])
            return _out("", won)
        if c == "ekle" and len(a) >= 2 and a[0] in ("g", "o"):
            return _out("" if planlama.add(a[0], rest) else "Düğüm sınırına ulaştınız efendim.")
        if c == "ad" and len(a) >= 2:
            _, won = planlama.rename(a[0], rest)
            return _out("", won)
    except (ValueError, IndexError):
        pass
    return _out("")


def planlama_mode(text: str, st: dict):
    if text.strip().startswith("@"):
        return _raw(text, st)
    import scenes
    t = scenes.norm(text)
    if not t:
        return None
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": HELP}
    snap = planlama.snapshot()["stat"]
    m = re.match(r"^(?:yeni\s+)?(görev|ödül)\s+(?:ekle|oluştur)\s+(.+)$", t) or re.match(r"^yeni\s+(görev|ödül)\s+(.+)$", t)
    kind, name = (m.group(1), m.group(2)) if m else (None, None)
    if not m:
        m = re.match(r"^(.+?)\s+(görev|ödül)\w*\s+(?:ekle|oluştur)\w*$", t)
        kind, name = (m.group(2), m.group(1)) if m else (None, None)
    if m:
        n = planlama.add("g" if kind == "görev" else "o", _cap(name))
        if not n:
            return {"say": "Düğüm sınırına ulaştınız efendim; bitenleri temizleyebilirsiniz."}
        return _out(f"{'Görev' if n['t'] == 'g' else 'Ödül'} eklendi efendim: {n['text']}. Bağlamak için '{n['text'].lower()} ile … bağla' diyebilirsiniz.")
    m = re.match(r"^(.+?)\s+ile\s+(.+?)\s+(?:bağını|bağlantısını|bağlantısını|ilişkisini)\s+(?:kes|kaldır|sil|ayır)\w*$", t) or re.match(r"^(.+?)\s+ile\s+(.+?)\s+(?:ayır|ayrıl)\w*$", t)
    if m:
        a, b = _node(m.group(1)), _node(m.group(2))
        if not a or not b:
            return {"say": "Bu isimlerle iki düğüm bulamadım efendim."}
        n, won = planlama.unlink(a["id"], b["id"])
        return _out("Bağı kopardım efendim." if n else "Aralarında bağ yoktu efendim.", won)
    m = re.match(r"^(.+?)\s+ile\s+(.+?)\s+(?:bağla|birleştir|ilişkilendir|ilişki kur)\w*$", t)
    if m:
        a, b = _node(m.group(1)), _node(m.group(2))
        if not a or not b:
            return {"say": "Bu isimlerle iki düğüm bulamadım efendim."}
        if a["id"] == b["id"]:
            return {"say": "Bir şeyi kendine bağlayamam efendim."}
        ok, won = planlama.link(a["id"], b["id"])
        return _out(f"{a['text']} ile {b['text']} bağlandı efendim." if ok else "Zaten bağlılar efendim.", won)
    if re.search(r"\b(biten|tamamlanan|bitmiş)\w*\s+görev\w*\s+(temizle|sil|kaldır)\w*|\bbitenleri\s+(temizle|sil)\w*", t):
        n, _ = planlama.clear_done()
        return _out(f"{n} biten görevi temizledim efendim." if n else "Temizlenecek biten görev yok efendim.")
    m = re.match(r"^(.+?)\s+(?:geri al\w*|yapılmadı|bitmedi|açık yap\w*)$", t)
    if m:
        n = _node(m.group(1), "g")
        if not n:
            return {"say": "Bu isimde bir görev bulamadım efendim."}
        if n.get("done"):
            planlama.toggle(n["id"], False)
        return _out(f"{n['text']} yeniden açıldı efendim.")
    m = re.match(r"^(.+?)\s+(?:bitti|bitir\w*|tamamla\w*|tamamlandı|yaptım|yapıldı|halloldu|tamam)$", t)
    if m:
        n = _node(m.group(1), "g")
        if not n:
            return {"say": "Bu isimde bir görev bulamadım efendim."}
        _, won = planlama.toggle(n["id"], True)
        return _out(f"{n['text']} tamamlandı efendim.", won)
    m = re.match(r"^(.+?)\s+(?:sil|kaldır|çıkar)\w*$", t) or re.match(r"^(?:sil|kaldır)\w*\s+(.+)$", t)
    if m:
        n = _node(m.group(1))
        if not n:
            return {"say": "Bu isimde bir düğüm bulamadım efendim."}
        planlama.remove(n["id"])
        return _out(f"{n['text']} silindi efendim.")
    if re.search(r"\b(durum|ilerleme|kaç görev|kaç ödül|ne kadar kaldı|özet)\w*", t):
        s = planlama.snapshot()
        if not s["stat"]["g"] and not s["stat"]["o"]:
            return {"say": "Planınız boş efendim. Görev ekle ya da ödül ekle diyerek başlayabilirsiniz."}
        said = [f"{s['stat']['g']} görevden {s['stat']['gd']} tanesi tamam"]
        pend = [n for n in s["nodes"] if n["t"] == "o" and not n.get("got")]
        for n in pend[:3]:
            said.append(f"{n['text']} ödülüne {n['prog'][1] - n['prog'][0]} görev kaldı" if n["prog"][1] else f"{n['text']} ödülüne henüz görev bağlanmadı")
        if s["stat"]["od"]:
            said.append(f"{s['stat']['od']} ödül kazanıldı")
        return {"say": ", ".join(said) + " efendim."}
    return {"say": "Anlayamadım efendim. Görev ekle, ödül ekle, ödev ile film ödülünü bağla ya da ödevi bitir diyebilirsiniz."}
