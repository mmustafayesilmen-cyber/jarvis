"""Ezber kartları modu komutları: çevir, bildim / bilmedim / zor / kolay, kartı oku, deste seç / oluştur, kart ekle, kart üret, sil, durum.
Yalnızca kartlar.json'a dokunur. Kart üretimi uzun sürdüğü için 'later' ile arka planda çalışır."""
import re

import kartlar as K
import scenes

GRADES = [(0, r"\b(bilmedim|bilemedim|bilmiyorum|hatırlamadım|yanlış|tekrar sor|tekrarla)\b"), (3, r"\b(çok kolay|kolay|kolaydı)\b"),
          (1, r"\b(zor|zordu|zorlandım|az kalsın)\b"), (2, r"\b(bildim|biliyorum|doğru|iyi|hatırladım|tamam bildim)\b")]
GNAME = {0: "Bilmedim", 1: "Zor", 2: "İyi", 3: "Kolay"}


def _status(v=None) -> str:
    v = v or K.view()
    h = v["here"]
    return (f"{v['deckName']}: {h['due']} tekrar ve {h['new']} yeni kart bekliyor, toplam {h['total']} kart. "
            f"Bugün {v['today']['rev']} kart çalıştınız, {v['today']['ok']} tanesini bildiniz.")


def _card_say(v) -> str:
    c = v["card"]
    if not c:
        return "Şimdilik çalışılacak kart kalmadı efendim. " + ("Yeni kart ekleyebilir ya da kart üret diyebilirsiniz." if not v["here"]["total"] else "Tekrarlar zamanı gelince açılacak.")
    return f"Sıradaki kart: {c['front']}"


def kartlar(text: str, st: dict):
    t = scenes.norm(text)
    raw = " ".join(str(text).split())
    low = raw.replace("İ", "i").replace("I", "ı").lower()
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Çevir, bildim, bilmedim, zor, kolay, kartı oku, deste ingilizce, yeni deste fizik, kart ekle apple eşittir elma, "
                       "hücre organelleri hakkında on kart üret, bu kartı sil, kaç kart kaldı diyebilirsiniz."}
    # --- kart üretimi: "hücre organelleri hakkında 10 kart üret", "kart üret: ingilizce renkler"
    m = re.search(r"(?:(.+?)\s+(?:hakkında|konusunda|ile ilgili|için)\s+)?(\d{1,2}|[a-zçğıöşü]+)?\s*(?:tane\s+)?kart\w*\s+(?:üret|oluştur|hazırla|yap)\w*\s*:?\s*(.*)$", low)
    if m and re.search(r"\b(üret|oluştur|hazırla)\w*", low) and not re.search(r"\bdeste\w*\s+(oluştur|aç)", low):
        topic = (m.group(1) or m.group(3) or "").strip(" :")
        n = scenes.num_in(m.group(2) or "") or 10
        v = K.view()
        if not v["deck"]:
            return {"say": "Önce bir deste seçin ya da yeni deste oluşturun efendim, kartları oraya ekleyeyim."}
        if not topic:
            return {"say": "Hangi konuda kart üreteyim efendim? Örneğin hücre organelleri hakkında on kart üret deyin."}
        deck = v["deck"]
        return {"do": {"gen": True}, "say": f"{topic} hakkında {n} kart hazırlıyorum efendim, bu bir dakika kadar sürebilir.",
                "later": lambda: K.generate(deck, topic, n)["msg"]}
    # --- kart ekleme: "kart ekle apple = elma", "kart ekle: güneşin yaşı ne : 4,6 milyar yıl"
    m = re.match(r"^(?:jarvis\W*)?(?:yeni\s+)?kart\s+ekle\w*\s*:?\s*(.+?)\s*(?:=|eşittir|anlamı|cevabı|karşılığı|arkası|\s:\s|–|—)\s*(.+)$", low)
    if m:
        v = K.view()
        if not v["deck"]:
            return {"say": "Önce bir deste seçin ya da yeni deste oluşturun efendim."}
        r = K.add_card(v["deck"], m.group(1), m.group(2))
        if r.get("dup"):
            return {"say": "Bu kart bu destede zaten var efendim."}
        return {"do": {"refresh": True}, "say": f"Kart eklendi efendim: {r['front']}." if r else "Kartı ekleyemedim efendim."}
    # --- desteler
    m = re.search(r"(?:yeni\s+deste|deste\s+(?:oluştur|aç|ekle)|deste\s+yap)\w*\s*:?\s*(.+)$|^(.+?)\s+destesi\s+(?:oluştur|yap|ekle)\w*$", low)
    if m:
        name = (m.group(1) or m.group(2) or "").strip()
        dk = K.add_deck(name)
        return {"do": {"refresh": True}, "say": f"{dk['name']} destesi hazır efendim. Kart ekle ya da kart üret diyebilirsiniz." if dk else "Desteyi oluşturamadım efendim."}
    if re.search(r"\b(tüm desteler|bütün desteler|hepsi|karışık)\b", t) and re.search(r"deste|çalış|geç|aç|hepsi", t):
        K.select_deck(None)
        return {"do": {"refresh": True}, "say": "Bütün destelerden karışık çalışıyoruz efendim. " + _card_say(K.view())}
    m = re.search(r"^(?:deste\w*\s+)(.+)$|^(.+?)\s+deste\w*\s*(?:aç|seç|geç|çalış)?\w*$|^(.+?)\s+(?:destesine|destesini)\s*(?:geç|aç|seç|çalış)?\w*$", t)
    if m and not re.search(r"\b(sil\w*|kaç|liste\w*|desteler\w*)\b", t):
        name = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        dk = K.select_deck(name)
        if dk:
            return {"do": {"refresh": True}, "say": f"{dk['name']} destesi efendim. " + _card_say(K.view())}
        return {"say": f"{name} adında bir deste bulamadım efendim. Yeni deste {name} diyerek oluşturabilirsiniz."}
    if re.search(r"\b(destelerim|hangi desteler|desteler|deste listesi)\b", t):
        v = K.view()
        if not v["decks"]:
            return {"say": "Henüz desteniz yok efendim. Yeni deste ingilizce gibi bir komutla başlayın."}
        return {"say": "Desteleriniz: " + ", ".join(f"{d['name']} ({d['total']} kart)" for d in v["decks"][:10]) + "."}
    # --- kart işlemleri
    if re.search(r"\b(bu kartı|kartı)\s+(sil|kaldır|çıkar)\w*", t):
        v = K.view()
        if not v["card"]:
            return {"say": "Silinecek bir kart yok efendim."}
        K.delete_card(v["card"]["id"])
        return {"do": {"refresh": True}, "say": "Kartı sildim efendim. " + _card_say(K.view())}
    if re.search(r"\b(çevir|arkasını|cevabı göster|cevap ne|cevabı söyle|cevabı ne|göster)\b", t):
        v = K.view()
        if not v["card"]:
            return {"say": _card_say(v)}
        K.flip(True)
        return {"do": {"refresh": True}, "say": v["card"]["back"]}
    if re.search(r"\b(oku|sesli oku|kartı oku|soru ne|ne yazıyor)\b", t):
        v = K.view()
        if not v["card"]:
            return {"say": _card_say(v)}
        return {"say": v["card"]["front"] + (". Cevap: " + v["card"]["back"] if v["flipped"] else "")}
    for g, pat in GRADES:
        if re.search(pat, t):
            v = K.view()
            if not v["card"]:
                return {"say": _card_say(v)}
            back = v["card"]["back"]
            r = K.grade(g)
            nv = K.view()
            pre = "" if v["flipped"] else f"Cevap: {back}. "
            return {"do": {"refresh": True, "graded": g}, "say": pre + f"{GNAME[g]}, {r['next']} sonra tekrar soracağım. " + _card_say(nv)}
    if re.search(r"\b(sonraki|geç|atla|başla|başlat|devam)\b", t):
        return {"do": {"refresh": True}, "say": _card_say(K.view())}
    if re.search(r"\b(kaç kart|durum|kalan|ne kadar kaldı|bugün)\b", t):
        return {"say": _status()}
    return {"say": "Anlayamadım efendim. Çevir, bildim, bilmedim, zor, kolay, kart ekle, kart üret ya da yardım diyebilirsiniz."}


def note_titles() -> list:
    try:
        import notes
        return [{"id": n["id"], "title": n["title"] or "(başlıksız)"} for n in notes.listing()[:60]]
    except Exception:
        return []


def ws(d: dict, st: dict):
    """Penceredeki düğmeler. Sayfadan gelen her değer burada süzülür; kart metinleri kartlar.py'de de kısaltılır."""
    t = str(d.get("type", ""))[8:]
    s = lambda k, n=300: str(d.get(k) or "")[:n]
    if t == "flip":
        K.flip()
        return {}
    if t == "grade":
        v = K.view()
        if not v["card"]:
            return {}
        r = K.grade(int(d.get("g", 2)) if str(d.get("g", "")).isdigit() else 2)
        return {"do": {"graded": int(d.get("g", 2))}, "say": f"{r['next']} sonra tekrar." if r else ""}
    if t == "deck":
        K.select_deck(s("id", 20) or None)
        return {}
    if t == "newdeck":
        dk = K.add_deck(s("name", 40))
        return {"say": f"{dk['name']} destesi hazır." if dk else "Deste oluşturulamadı."}
    if t == "deldeck":
        n = K.delete_deck(s("id", 20))
        return {"say": f"Deste ve içindeki {n} kart silindi." if n >= 0 else "Deste bulunamadı."}
    if t == "add":
        v = K.view()
        if not v["deck"]:
            return {"say": "Önce bir deste seçin."}
        r = K.add_card(v["deck"], s("front"), s("back"))
        return {"do": {"added": bool(r and not r.get("dup"))}, "say": "Bu kart zaten var." if r.get("dup") else ("Kart eklendi." if r else "Kartın iki yüzünü de yazın.")}
    if t == "del":
        return {"say": "Kart silindi." if K.delete_card(s("id", 20)) else ""}
    if t == "edit":
        return {"say": "Kart güncellendi." if K.edit_card(s("id", 20), s("front"), s("back")) else "Kart güncellenemedi."}
    if t == "speak":
        v = K.view()
        if v["card"]:
            return {"say": v["card"]["front"] + (". Cevap: " + v["card"]["back"] if v["flipped"] else ""), "speak": True}
        return {}
    if t == "notes":
        return {"do": {"notes": note_titles()}}
    if t == "gen":
        v = K.view()
        if not v["deck"]:
            return {"say": "Önce bir deste seçin ya da oluşturun."}
        n = int(d.get("n") or 10) if str(d.get("n") or "10").isdigit() else 10
        src = s("topic", 300)
        if d.get("note"):
            try:
                import notes
                nt = next((x for x in notes.listing() if x["id"] == s("note", 40)), None)
            except Exception:
                nt = None
            if not nt:
                return {"say": "Not bulunamadı."}
            src = f"Not başlığı: {nt['title']}\n{notes.plain(nt['html'])}"
        if not src.strip():
            return {"say": "Bir konu yazın ya da bir not seçin."}
        deck = v["deck"]
        return {"do": {"gen": True}, "say": f"{n} kart hazırlanıyor, bir dakika kadar sürebilir.", "later": lambda: K.generate(deck, src, n)["msg"]}
    return {}


def init_payload():
    return K.view()
