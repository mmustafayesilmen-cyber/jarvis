"""Pomodoro modu komut işleyicisi. Süreleri sesle ayarlar: 'çalışma 30 dakika', 'mola 10 dakika', '45 dakika çalış 10 dakika mola',
'uzun mola 20 dakika', '3 turda bir uzun mola', 'müzik aç', 'otomatik devam kapat'. Yalnızca pomodoro durumunu değiştirir; güç/ışık/ses komutu yok."""
import re

import pomodoro as pm
import scenes

_W = "|".join(sorted(list(scenes._TENS) + list(scenes._ONES), key=len, reverse=True))
_NUM = rf"(\d{{1,3}}|(?:{_W})(?: (?:{_W}))?)"
_DUR = re.compile(_NUM + r"\s*(?:dakika|dk)\w*")


def _roles(t: str):
    """'45 dakika çalış 10 dakika mola' gibi cümlelerden [(rol, dakika)] çıkarır. Rol: work | short | long."""
    out = []
    for m in _DUR.finditer(t):
        n = scenes.num_in(m.group(1))
        if not n:
            continue
        after = " ".join(t[m.end():].split()[:2])
        before = " ".join(t[:m.start()].split()[-2:])
        role = None
        for ctx in (after, before):                  # önce sayıdan sonraki sözcüklere, sonra öncekilere bakılır
            if re.search(r"\buzun\b", ctx) and re.search(r"mola|ara|dinlen", ctx):
                role = "long"
            elif re.search(r"mola|\bara\b|dinlen|\bkısa\b", ctx):
                role = "short"
            elif re.search(r"çalış|odak|ders|süre", ctx):
                role = "work"
            if role:
                break
        if role:
            out.append((role, n))
    return out


def _playing() -> bool:
    """Müzik şu an çalıyorsa liste değişince yeniden başlatılır."""
    try:
        import study_music
        return bool(pm.cfg["music"] and study_music.active())
    except Exception:
        return False


def _fmt_cfg() -> str:
    c = pm.cfg
    return (f"Çalışma {c['work']} dakika, kısa mola {c['short']} dakika, uzun mola {c['long']} dakika, {c['rounds']} turda bir uzun mola. "
            f"Otomatik devam {'açık' if c['auto'] else 'kapalı'}, çalışırken müzik {'açık' if c['music'] else 'kapalı'}"
            f"{', listenizde ' + str(len(c['songs'])) + ' şarkı var' if c['songs'] else ', varsayılan ders şarkıları'}.")


def _apply(role: str, n: int):
    key = {"work": "work", "short": "short", "long": "long"}[role]
    v, clipped = pm.set_cfg(key, n)
    label = {"work": "Çalışma süresi", "short": "Kısa mola", "long": "Uzun mola"}[role]
    return f"{label} {v} dakika" + (f" (sınır nedeniyle {n} yerine)" if clipped else "")


def pomodoro(text: str, st: dict):
    t = scenes.norm(text)
    snap = pm.snapshot()
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Başlat, duraklat, devam, atla, bitir, çalışma otuz dakika, mola on dakika, uzun mola yirmi dakika, dört turda bir uzun mola, "
                       "beş dakika ekle, kalan süre, ayarlar, otomatik devam aç ya da kapat, müzik aç ya da kapat diyebilirsiniz."}
    # --- çalışma müziği şarkı listesi
    songs = pm.cfg["songs"]
    m = (re.search(r"(?:müzik|şarkı|çalışma müziği|odak müziği)\w*\s*liste\w*\s+(.+?)\s+ekle\w*$", t)
         or re.search(r"^(.+?)\s+(?:müzik |şarkı )?liste\w*\s+ekle\w*$", t) or re.search(r"^şarkı\s+ekle\w*\s+(.+)$", t))
    if m:
        name = m.group(1).strip()
        ok = pm.add_song(name)
        return {"do": {"cfg": True}, "music": "restart" if _playing() else None,
                "say": (f"{name} listeye eklendi efendim, listede {len(pm.cfg['songs'])} şarkı var." if ok else "Bu şarkı zaten listede ya da liste dolu efendim.")}
    m = re.search(r"(\d{1,2})\s*(?:\.\s*)?(?:şarkıyı|şarkı)\s*(?:listeden\s*)?(?:sil|çıkar|kaldır)\w*", t)
    if m or (re.search(r"liste\w*\s+(.+?)\s+(?:sil|çıkar|kaldır)\w*", t) and re.search(r"liste", t) and songs):
        if m:
            name = pm.remove_song(int(m.group(1)))
        else:
            q = re.search(r"liste\w*\s+(.+?)\s+(?:sil|çıkar|kaldır)\w*", t).group(1)
            hit = next((i for i, x in enumerate(songs, 1) if q in scenes.norm(x)), 0)
            name = pm.remove_song(hit) if hit else None
        return {"do": {"cfg": True}, "music": "restart" if (name and _playing()) else None,
                "say": f"{name} listeden çıkarıldı efendim." if name else "Böyle bir şarkı bulamadım efendim."}
    if re.search(r"\b(şarkı|müzik)\w*\s*liste\w*", t) and re.search(r"temizle|sıfırla|boşalt|sil\b|silsene", t):
        n = pm.clear_songs()
        return {"do": {"cfg": True}, "music": "restart" if _playing() else None,
                "say": f"Şarkı listesini temizledim efendim, {n} şarkı silindi. Müzik açılırsa varsayılan ders şarkıları çalar."}
    if re.search(r"\b(şarkı|müzik)\w*\s*liste\w*|şarkılarım|hangi şarkılar", t) and not re.search(r"ekle", t):
        if not songs:
            return {"say": "Kendi şarkı listeniz boş efendim, bu yüzden varsayılan ders şarkıları çalıyor. Müzik listesine bir şarkı adı ve ekle diyerek ekleyebilirsiniz."}
        return {"say": f"Listenizde {len(songs)} şarkı var: " + ", ".join(songs[:8]) + (" ve diğerleri." if len(songs) > 8 else ".")}
    # --- ayarlar (süre içeren cümleler)
    roles = _roles(t)
    rounds = re.search(_NUM + r"\s*tur\w*", t)
    if rounds and re.search(r"uzun|tur sayı|turda|tur olsun|tur yap", t) and not re.search(r"kaç tur", t):
        n = scenes.num_in(rounds.group(1))
        if n:
            v, clipped = pm.set_cfg("rounds", n)
            msg = f"{v} turda bir uzun mola verilecek"
            applied = [msg + (" (sınır nedeniyle)" if clipped else "")]
            for role, mins in roles:
                applied.append(_apply(role, mins))
            return {"do": {"cfg": True}, "say": "Tamam efendim. " + ", ".join(applied) + "."}
    if roles and not re.search(r"\b(ekle|uzat|artır|çıkar|kısalt|azalt)\w*", t) and not re.search(r"kalan|ne kadar|kaç", t):
        applied = [_apply(r, m) for r, m in roles]
        say = "Tamam efendim. " + ", ".join(applied) + "."
        if re.search(r"\b(başla|başlat|başlıyoruz|hadi|çalış|çalışalım|çalışıyorum)\w*\b", t.replace("çalışma", "")) and snap["phase"] == "idle":
            pm.start()
            say += " Çalışma başladı, bol şans."
            return {"do": {"cfg": True, "started": True}, "say": say, "music": "work"}
        return {"do": {"cfg": True}, "say": say + ("" if snap["phase"] == "idle" else " Yeni süre bir sonraki evreden itibaren geçerli.")}
    # --- ekle / çıkar
    m = re.search(_NUM + r"\s*(?:dakika|dk)\w*\s*(?:daha\s*)?(ekle|uzat|artır|çıkar|kısalt|azalt|eksilt)", t)
    if m:
        n = scenes.num_in(m.group(1)) or 0
        if snap["phase"] == "idle":
            return {"say": "Henüz bir evre çalışmıyor efendim, önce başlat deyin."}
        if n and pm.extend(n if m.group(2) in ("ekle", "uzat", "artır") else -n):
            s = pm.snapshot()
            return {"do": {"tick": True}, "say": f"Tamam efendim, {pm.NAMES[s['phase']].lower()} için kalan süre {pm.mmss(s['left'])}."}
    if re.search(r"\b(daha|biraz|az) (uzat|ekle)|\buzat\b", t) and snap["phase"] != "idle":
        pm.extend(5)
        return {"do": {"tick": True}, "say": f"Beş dakika ekledim efendim, kalan süre {pm.mmss(pm.snapshot()['left'])}."}
    # --- ayar anahtarları
    if re.search(r"otomatik|kendiliğinden|sürekli devam|arka arkaya", t):
        on = not re.search(r"kapat|kapa|durdur|hayır|kaldır|iptal", t)
        pm.set_cfg("auto", on)
        return {"do": {"cfg": True}, "say": "Evreler birbirini otomatik izleyecek efendim." if on else "Her evre bitince sizin başlat demenizi bekleyeceğim efendim."}
    # --- şarkı çalar paneli (elle açılan tek şarkı; pomodoro molası buna dokunmaz)
    if re.search(r"döngü\w*|tekrarla|tekrar çal|sürekli çal", t):
        on = not re.search(r"kapat|kapa|kaldır|çık|bitir|durdur|iptal", t)
        return {"music": ("loop", on), "say": "Şarkı döngüde efendim, bitince baştan çalacak." if on else "Döngüyü kapattım efendim."}
    if re.fullmatch(r"(çalan |bu )?(şarkıyı|parçayı|şarkı) (durdur|kapat|kapa|sustur|kes)\w*|şarkıyı bitir", t):
        return {"music": "stopall", "say": "Şarkıyı durdurdum efendim."}
    m = re.fullmatch(r"(?:şarkı çal\s+)?(.+?)\s+(?:şarkısını |parçasını )?(?:çal|çalsana|oynat|aç)", t) or re.fullmatch(r"şarkı çal\s+(.+)", t)
    if m and not re.fullmatch(r"(müzi\w*|şarkı\w*|ders müziği|çalışma müziği|odak müziği|otomatik.*|liste\w*|pomodoro.*|odak modu\w*|pencere\w*|kılavuz\w*)", m.group(1)):
        q = m.group(1)
        return {"music": ("play", q), "say": f"{q} aranıyor efendim."}
    if re.search(r"\bmüzi\w*|\bşarkı\w*", t) and re.search(r"aç|kapat|kapa|başlat|durdur|olsun|olmasın|çal", t):
        on = not re.search(r"kapat|kapa|durdur|olmasın|kaldır|istemiyorum", t)
        pm.set_cfg("music", on)
        what = "kendi şarkı listeniz" if pm.cfg["songs"] else "ders şarkıları"
        play_now = on and (snap["phase"] == "idle" or (snap["phase"] == "work" and not snap["paused"]))
        if not on:
            say = "Çalışırken müzik çalmayacak efendim."
        elif play_now:
            say = f"Müzik açıldı efendim, {what} birazdan çalacak. Molalarda susacak."
        else:
            say = f"Müzik açık efendim, {what} çalışma evresi başlayınca çalacak."
        return {"do": {"cfg": True}, "say": say, "music": "music_on" if play_now else "stopall" if not on else None}
    if re.search(r"\bayar\w*|\bsüreler\w*|ne kadar çalış|kaç dakika (çalış|mola)", t) and not re.search(r"\b(kalan|kaldı)\b", t):
        return {"say": _fmt_cfg()}
    if re.search(r"\b(varsayılan|sıfırla|eski haline)\b", t) and re.search(r"ayar|süre|varsayılan", t):
        for k, v in pm.DEFAULTS.items():
            if k != "songs":                         # şarkı listeniz varsayılana dönünce silinmez
                pm.set_cfg(k, v)
        return {"do": {"cfg": True}, "say": "Ayarları varsayılana döndürdüm efendim: " + _fmt_cfg()}
    # --- kontrol
    if re.search(r"\b(kalan|kaldı|ne kadar kaldı|süre ne|durum)\w*", t) or re.search(r"\bkaç (tur|pomodoro)\w*|\bbugün\b", t):
        if re.search(r"kaç (tur|pomodoro)|bugün|kaç kere|toplam", t):
            return {"say": f"Bugün {snap['done_today']} çalışma turu tamamladınız, toplam {snap['work_min_today']} dakika odaklandınız efendim."}
        if snap["phase"] == "idle":
            return {"say": "Henüz başlamadık efendim. Başlat demeniz yeterli."}
        return {"say": f"{pm.NAMES[snap['phase']]} evresinde {pm.mmss(snap['left'])} kaldı efendim"
                       + (", şu an duraklatıldı." if snap["paused"] and not snap["waiting"] else ".")}
    if re.search(r"\b(atla|geç|molayı (bitir|kes|geç)|mola yeter|mola bitti|sonraki|mola ver|mola istiyorum|mola zamanı)\b", t) and not re.search(r"\b(oturum|pomodoro)\w* bitir", t):
        if snap["phase"] == "idle":
            return {"say": "Atlanacak bir evre yok efendim."}
        ev = pm.skip()
        to = pm.snapshot()
        return {"do": {"tick": True}, "say": f"Atladım efendim. Şimdi {pm.NAMES[ev['to']].lower()} evresi, {pm.mmss(to['left'])}.", "music": "work" if ev["to"] == "work" else "off"}
    if re.search(r"\b(duraklat|beklet|bir dakika dur|dur)\b", t) and not re.search(r"\b(oturum|pomodoro)\w* (durdur|bitir)", t):
        if pm.pause():
            return {"do": {"tick": True}, "say": "Duraklattım efendim. Devam et deyince sürer.", "music": "pause"}
        return {"say": "Zaten duraklatılmış ya da çalışan bir evre yok efendim."}
    if re.search(r"\b(devam|sürdür|başlat|başla|hazırım|başlıyoruz|hadi|çalışmaya başla|oturumu başlat)\w*", t):
        r = pm.start()
        s = pm.snapshot()
        if r == "running":
            return {"say": f"Zaten çalışıyoruz efendim, {pm.mmss(s['left'])} kaldı."}
        if r == "resumed":
            return {"do": {"tick": True}, "say": f"Devam ediyoruz efendim, {pm.mmss(s['left'])} kaldı.", "music": "work" if s["phase"] == "work" else "resume"}
        return {"do": {"started": True, "tick": True}, "say": f"Başladık efendim. {pm.cfg['work']} dakika odaklanma, sonra {pm.cfg['short']} dakika mola. Bol şans.", "music": "work"}
    if re.search(r"\b(bitir|sonlandır|iptal|sıfırla|durdur|baştan)\w*", t):
        s = pm.snapshot()
        was = pm.stop()
        return {"do": {"tick": True}, "say": (f"Oturumu bitirdim efendim. Bugün {s['done_today']} tur, {s['work_min_today']} dakika odaklandınız." if was else "Zaten çalışan bir oturum yok efendim."),
                "music": "off"}
    return {"say": "Anlayamadım efendim. Başlat, duraklat, atla, bitir, çalışma otuz dakika, mola on dakika ya da yardım diyebilirsiniz."}


def event_say(ev: dict) -> str:
    """Evre geçişinde söylenecek cümle (main.py'deki zamanlayıcı döngüsü çağırır)."""
    s = pm.snapshot()
    if ev["from"] == "work":
        kind = "uzun" if ev["to"] == "long" else "kısa"
        base = f"Efendim, çalışma turu bitti, bugün {ev['done_today']}. turunuzu tamamladınız. {pm.cfg['long' if kind == 'uzun' else 'short']} dakikalık {kind} mola zamanı."
        if kind == "uzun":
            base += " Oturumun bir döngüsünü bitirdiniz, uzun bir ara hak ettiniz."
    else:
        base = f"Mola bitti efendim. {pm.cfg['work']} dakikalık yeni bir çalışma turu."
    if not ev["auto"]:
        base += " Hazır olduğunuzda başlat deyin."
    return base
