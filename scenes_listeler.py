"""Müzik listeleri modu komutları. Örnekler: 'yeni liste çalışma', 'çalışma listesine tarkan kuzu kuzu ekle', 'listeye sezen aksu gülpembe ekle',
'çalan şarkıyı listeye ekle', '2. şarkıyı sil', 'çalışma listesinden gülpembeyi çıkar', 'çalışma listesini çal', 'karışık çal', 'çalışma listesini sil',
'listenin adını sınav yap', 'listelerim'. Şarkı arama ağ işi olduğu için 'later' ile arka planda yapılır; sonuç sayfaya ve sesle bildirilir."""
import re

import muzik_listeleri as ML
import scenes
import study_music

NUMS = {"birinci": 1, "ikinci": 2, "üçüncü": 3, "dördüncü": 4, "beşinci": 5, "altıncı": 6, "yedinci": 7, "sekizinci": 8, "dokuzuncu": 9, "onuncu": 10}


def _low(t: str) -> str:
    return " ".join(str(t).replace("İ", "i").replace("I", "ı").lower().replace("’", "'").split())


def _cap(name: str) -> str:
    """Baş harfi Türkçe kurallarıyla büyütür: 'sınav' -> 'Sınav', 'ilk liste' -> 'İlk liste'."""
    name = ML._name(name)
    return (name[:1].replace("i", "İ").replace("ı", "I").upper() + name[1:]) if name else name


def _strip_suffix(name: str) -> str:
    """'çalışma listesi' / 'çalışma' + Türkçe ekler -> 'çalışma'."""
    n = re.sub(r"\s+(listesi|listem|listemi|listeyi|listesini|listesine|listesinden|listesinin|liste)\b.*$", "", _low(name)).strip(" '\"")
    return re.sub(r"['’]\w+$", "", n)


def _sel(d):
    return ML._get(d, ML.S["sel"])


def _list_say(d) -> str:
    if not d["lists"]:
        return "Henüz müzik listeniz yok efendim. Yeni liste çalışma diyerek oluşturabilirsiniz."
    return "Listeleriniz: " + ", ".join(f"{x['name']} ({len(x['songs'])} şarkı)" for x in d["lists"][:10]) + "."


def _fmt_dur(s: int) -> str:
    s = int(s or 0)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def _target(d, name: str, st: dict):
    """Komutta liste adı verildiyse onu, yoksa seçili listeyi döner. (liste, hata_metni)."""
    if name:
        x = ML.find(d, name)
        if x:
            ML.S["sel"] = x["id"]
            return x, None
        return None, f"{name} adında tek bir liste bulamadım efendim. " + _list_say(d)
    x = _sel(d)
    if x:
        return x, None
    return None, "Önce bir liste seçin ya da yeni liste oluşturun efendim."


def _add_job(lid: str, query: str):
    """Arka plan: şarkıyı bul ve listeye ekle. Sonuç: {'say'}."""
    def job():
        ML.S["busy"] = f"“{query[:40]}” aranıyor…"
        try:
            r = ML.resolve(query)
        except Exception as e:
            ML.S["busy"] = ""
            return {"say": f"Şarkı aramasına ulaşamadım efendim, internet bağlantısını kontrol edin. ({type(e).__name__})"}
        ML.S["busy"] = ""
        if not r:
            return {"say": f"{query} diye bir şarkı bulamadım efendim."}
        d = ML._load()
        x = ML._get(d, lid)
        if not x:
            return {"say": "Liste artık yok efendim."}
        if "playlist" in r:
            name, items = r["playlist"]
            n = ML.add_many(lid, items)
            return {"say": f"{name} listesinden {n} şarkı {x['name']} listesine eklendi efendim." if n else "Bu şarkıların hepsi listede zaten vardı efendim."}
        res = ML.add_item(lid, r)
        t = r["title"]
        if res == "added":
            return {"say": f"{t} {x['name']} listesine eklendi efendim."}
        if res == "dup":
            return {"say": f"{t} zaten {x['name']} listesinde efendim."}
        return {"say": f"{x['name']} listesi dolu efendim, en fazla {ML.MAX_SONGS} şarkı tutabilir."}
    return job


def _now_playing_item():
    return study_music.current_item()


def listeler(text: str, st: dict):
    raw = " ".join(str(text).split())
    low = _low(raw)
    t = scenes.norm(text)
    d = ML._load()
    # --- bekleyen onay (liste silme)
    if st.get("confirm"):
        lid, st["confirm"] = st["confirm"], None
        if re.match(r"^(evet|onaylıyorum|tamam|sil|evet sil)\b", t):
            x = ML._get(d, lid)
            n = ML.delete(lid)
            return {"say": f"{x['name'] if x else 'Liste'} silindi efendim, içindeki {max(n, 0)} şarkı listeden çıkarıldı."}
        return {"say": "Vazgeçtim efendim, listeye dokunmadım."}
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Yeni liste çalışma, çalışma listesine tarkan kuzu kuzu ekle, listeden gülpembeyi sil, çalışma listesini çal, karışık çal, "
                       "listelerim, çalan şarkıyı listeye ekle ve listeyi sil diyebilirsiniz. Şarkı adı yerine YouTube bağlantısı da yapıştırabilirsiniz."}
    # --- çalma denetimi
    if re.fullmatch(r"(sonraki|bir sonraki|sonraki şarkı|geç|atla|şarkıyı geç)", t):
        return {"say": "Sıradaki şarkıya geçtim efendim." if study_music.skip() else "Şu an çalan bir şarkı yok efendim."}
    if re.fullmatch(r"(önceki|önceki şarkı|geri|bir önceki)", t):
        return {"say": "Önceki şarkıya döndüm efendim." if study_music.prev() else "Şu an çalan bir şarkı yok efendim."}
    if re.fullmatch(r"(duraklat|beklet|müziği duraklat)", t):
        return {"say": "Duraklattım efendim." if study_music.pause() else "Çalan bir şarkı yok ya da zaten duraklatılmış efendim."}
    if re.fullmatch(r"(devam|devam et|sürdür|oynat)", t):
        return {"say": "Devam ediyor efendim." if study_music.resume() else "Zaten çalıyor ya da duraklatılmış bir şarkı yok efendim."}
    if re.fullmatch(r"(durdur|müziği durdur|müziği kapat|şarkıyı durdur|sustur|dur)", t):
        ML.S["playing"] = None
        return {"say": "Müziği durdurdum efendim." if study_music.stop() else "Zaten çalan bir şey yok efendim."}
    if re.fullmatch(r"(döngüye al|döngüde çal|tekrarla|şarkıyı tekrarla)", t):
        study_music.set_repeat(True)
        return {"say": "Şarkı döngüde efendim."}
    if re.fullmatch(r"(döngüyü kapat|döngüden çık|tekrarı kapat)", t):
        study_music.set_repeat(False)
        return {"say": "Döngüyü kapattım efendim."}
    # --- listelerim
    if re.search(r"\b(listelerim|hangi listeler|listeler neler|liste listesi|kaç listem)\b", t):
        return {"say": _list_say(d)}
    # --- liste oluştur
    m = (re.match(r"^(?:yeni liste|liste oluştur|liste yap|liste ekle|yeni müzik listesi)\s*[:,]?\s*(.+)$", low)
         or re.match(r"^(.+?)\s+(?:adında|isminde|adlı|isimli)\s+(?:bir\s+)?(?:yeni\s+)?(?:müzik\s+)?liste\w*\s+(?:oluştur|yap|aç|ekle)\w*$", low)
         or re.match(r"^(.+?)\s+listesi\s+(?:oluştur|yap|aç)\w*$", low))
    if m:
        name = raw[len(raw) - len(m.group(1)):] if low.endswith(m.group(1)) else m.group(1)
        name = re.sub(r"\s+(?:adında|isminde|adlı|isimli).*$", "", name).strip(" :,")
        x = ML.create(_cap(name))
        if not x:
            return {"say": "Listeyi oluşturamadım efendim, en fazla 50 liste tutabilirim ya da ad boş."}
        if x.get("existed"):
            return {"do": {"sel": x["id"]}, "say": f"{x['name']} listesi zaten var efendim, onu açtım."}
        return {"do": {"sel": x["id"]}, "say": f"{x['name']} listesi oluşturuldu efendim. Şarkı eklemek için şarkı adını söyleyip listeye ekle deyin."}
    # --- liste adını değiştir
    m = re.match(r"^(?:(.+?)\s+listesinin|listenin|bu listenin)\s+adını\s+(.+?)\s+(?:yap|olarak değiştir|olsun)$", low)
    if m:
        x, err = _target(d, _strip_suffix(m.group(1) or ""), st)
        if err:
            return {"say": err}
        old = x["name"]
        new = _cap(m.group(2))
        return {"say": f"{old} listesinin adı {new} oldu efendim." if ML.rename(x["id"], new) else "Adı değiştiremedim efendim."}
    # --- liste sil
    m = re.match(r"^(?:(.+?)\s+listesini|listeyi|bu listeyi)\s+(?:sil|kaldır)$", low)
    if m:
        x, err = _target(d, _strip_suffix(m.group(1) or ""), st)
        if err:
            return {"say": err}
        st["confirm"] = x["id"]
        return {"say": f"{x['name']} listesini ve içindeki {len(x['songs'])} şarkıyı silmemi onaylıyor musunuz efendim? Evet ya da hayır deyin."}
    # --- liste seç / göster
    m = re.match(r"^(.+?)\s+listesini\s+(?:aç|göster|seç|getir)$", low) or re.match(r"^liste\s+(?:aç|göster|seç)\s+(.+)$", low)
    if m:
        x, err = _target(d, _strip_suffix(m.group(1)), st)
        if err:
            return {"say": err}
        return {"do": {"sel": x["id"]}, "say": f"{x['name']} listesi, {len(x['songs'])} şarkı." + (" Toplam " + _fmt_dur(sum(s["dur"] for s in x["songs"])) + "." if x["songs"] else " Boş.")}
    # --- çalan şarkıyı listeye ekle
    m = re.match(r"^(?:çalan şarkıyı|bu şarkıyı|şu an çalanı)\s+(?:(.+?)\s+listesine|listeye|bu listeye)\s+ekle$", low)
    if m:
        x, err = _target(d, _strip_suffix(m.group(1) or ""), st)
        if err:
            return {"say": err}
        it = _now_playing_item()
        if not it:
            return {"say": "Şu an çalan bir şarkı yok efendim."}
        res = ML.add_item(x["id"], it)
        return {"say": {"added": f"{it['title']} {x['name']} listesine eklendi efendim.", "dup": f"{it['title']} zaten {x['name']} listesinde efendim.",
                        "full": f"{x['name']} listesi dolu efendim."}.get(res, "Eklenemedi efendim.")}
    # --- şarkı ekle
    m = (re.match(r"^(.+?)\s+listesine\s+(.+?)\s+(?:ekle|ekler misin|ekleyin|ekleyebilir misin)$", low)
         or re.match(r"^(?:listeye|bu listeye)\s+(.+?)\s+(?:ekle|ekler misin|ekleyin)$", low)
         or re.match(r"^(.+?)\s+(?:listeye|bu listeye)\s+(?:ekle|ekler misin|ekleyin)$", low)
         or re.match(r"^(?:şarkı ekle|şarkı)\s*[:,]?\s+(.+)$", low))
    if m:
        if len(m.groups()) == 2:
            lname, query = _strip_suffix(m.group(1)), m.group(2)
        else:
            lname, query = "", m.group(1)
        urls = re.findall(r"https?://\S+", raw)                   # bağlantıda büyük/küçük harf önemli: özgün metinden alınır
        query = urls[0] if urls else re.sub(r"\s+(şarkısını|şarkısı|şarkıyı|parçasını|parçayı)$", "", query)
        x, err = _target(d, lname, st)
        if err:
            return {"say": err}
        if not query:
            return {"say": "Hangi şarkıyı ekleyeyim efendim?"}
        return {"do": {"sel": x["id"]}, "say": f"{query[:50]} aranıyor efendim.", "later": _add_job(x["id"], query)}
    # --- şarkı sil (önce sıra numarasıyla: "2. şarkıyı sil", "ikinci şarkıyı çıkar"; sonra adla)
    mn = re.match(r"^(?:(.+?)\s+listesinden\s+)?(\d{1,3}|" + "|".join(NUMS) + r")\s*\.?\s*(?:şarkıyı|şarkı|sıradakini)\s+(?:sil|çıkar|kaldır)\w*$", low)
    m = None if mn else (re.match(r"^(?:(.+?)\s+listesinden|listeden)\s+(.+?)\s+(?:sil|çıkar|kaldır)\w*$", low) or re.match(r"^(.+?)\s+(?:şarkısını|şarkıyı)\s+(?:sil|çıkar|kaldır)\w*$", low))
    if mn or m:
        if mn:
            lname, what = _strip_suffix(mn.group(1) or ""), mn.group(2)
        elif len(m.groups()) == 2:
            lname, what = _strip_suffix(m.group(1) or ""), m.group(2)
        else:
            lname, what = "", m.group(1)
        x, err = _target(d, lname, st)
        if err:
            return {"say": err}
        ref = int(what) if re.fullmatch(r"\d{1,3}", what) else NUMS.get(what)
        s = ML.remove_song(x["id"], ref) if ref else (lambda f: ML.remove_song(x["id"], f["id"]) if f else None)(ML.find_song(x, what))
        return {"say": f"{s['title']} {x['name']} listesinden çıkarıldı efendim." if s else f"{what} diye tek bir şarkı bulamadım efendim."}
    # --- çal
    m = (re.match(r"^(?:(.+?)\s+listesini|listeyi|bu listeyi)\s*(karışık\s+)?(?:çal|oynat|dinle|başlat|dinlet)\w*$", low)
         or re.match(r"^(karışık)\s+çal$", low) or re.match(r"^(?:(.+?)\s+listesini)\s+(karışık)\s+(?:çal|oynat)$", low))
    if m:
        shuffle = "karışık" in low
        lname = _strip_suffix(m.group(1) or "") if m.group(1) and m.group(1) != "karışık" else ""
        x, err = _target(d, lname, st)
        if err:
            return {"say": err}
        loop = not re.search(r"döngüsüz|tekrarsız|bir kez", low)
        n = ML.play(x["id"], shuffle=shuffle, loop=loop)
        if not n:
            return {"say": f"{x['name']} listesi boş efendim, önce şarkı ekleyin."}
        return {"do": {"sel": x["id"]}, "say": f"{x['name']} listesi {'karışık ' if shuffle else ''}çalıyor efendim, {n} şarkı."}
    return {"say": "Anlayamadım efendim. Yeni liste, listeye şarkı ekle, listeyi çal ya da yardım diyebilirsiniz."}


def ws(d: dict, st: dict):
    """Penceredeki düğmeler. Tüm kimlikler ve sayılar muzik_listeleri.py içinde doğrulanır."""
    t = str(d.get("type", ""))[9:]
    s = lambda k, n=300: str(d.get(k) or "")[:n]
    dd = ML._load()
    if t == "sel":
        ML.select(s("id", 12) or None)
        return {}
    if t == "create":
        x = ML.create(s("name", 60))
        return {"say": f"{x['name']} listesi oluşturuldu." if x and not x.get("existed") else ("Bu liste zaten var." if x else "Liste oluşturulamadı.")}
    if t == "rename":
        return {"say": "Liste adı değişti." if ML.rename(s("id", 12), s("name", 60)) else "Ad değiştirilemedi."}
    if t == "delete":
        n = ML.delete(s("id", 12))
        return {"say": f"Liste silindi ({n} şarkı)." if n >= 0 else "Liste bulunamadı."}
    if t == "add":
        lid, q = s("id", 12), s("q", 300).strip()
        if not q:
            return {}
        if not ML._get(dd, lid):
            return {"say": "Önce bir liste seçin."}
        return {"say": f"{q[:50]} aranıyor…", "later": _add_job(lid, q)}
    if t == "remove":
        try:
            i = int(d.get("i")) + 1
        except (TypeError, ValueError):
            return {}
        r = ML.remove_song(s("id", 12), i)
        return {"say": f"{r['title']} çıkarıldı." if r else ""}
    if t == "move":
        try:
            ML.move_song(s("id", 12), int(d.get("i")), int(d.get("j")))
        except (TypeError, ValueError):
            pass
        return {}
    if t == "play":
        try:
            start = int(d.get("start") or 0)
        except (TypeError, ValueError):
            start = 0
        n = ML.play(s("id", 12), start=start, shuffle=bool(d.get("shuffle")), loop=d.get("loop", True) is not False)
        return {"say": f"{n} şarkı çalıyor." if n else "Liste boş ya da bulunamadı."}
    if t == "ctl":
        k = s("k", 10)
        if k == "next":
            study_music.skip()
        elif k == "prev":
            study_music.prev()
        elif k == "pause":
            study_music.pause()
        elif k == "resume":
            study_music.resume()
        elif k == "stop":
            ML.S["playing"] = None
            study_music.stop()
        elif k == "loop":
            study_music.set_repeat(not study_music.repeat_on())
        return {}
    if t == "addnow":
        it = study_music.current_item()
        res = ML.add_item(s("id", 12), it) if it else None
        return {"say": {"added": "Çalan şarkı listeye eklendi.", "dup": "Bu şarkı listede zaten var.", "full": "Liste dolu."}.get(res, "Çalan şarkı yok.")}
    return {}


def init_payload():
    v = ML.view()
    v["np"] = study_music.status()
    return v
