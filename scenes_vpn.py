"""VPN komutları: 'vpn aç', 'amerikadan bağlan', 'vpn kapat', 'vpn durumu', 'hangi ülkedeyim', 'vpn testi', 'ülkeyi almanya yap', 'vpn sunucularım'.
Aynı mantık hem VPN modunda hem normal konuşmada (extras.route_vpn) çalışır. Bağlanma birkaç saniye sürdüğü için arka planda yapılır; sonuç ana programdaki
vpn.ON_CHANGE işleyicisi tarafından sesle bildirilir. Konuşmaya/günlüğe IP adresi yazılmaz, yalnızca ülke ve şehir söylenir."""
import re
import threading

import jbrowser
import vpn


def _country(cfg, t: str):
    """Cümlede geçen ülkeye/sunucu adına göre sunucu: ('amerikadan' gibi ekli biçimler dahil)."""
    words = re.findall(r"[a-zçğıöşü0-9]+", t.replace("İ", "i").replace("I", "ı").lower())
    for n in (2, 1):
        for i in range(len(words) - n + 1):
            w = " ".join(words[i:i + n])
            for k, cand in enumerate((w, w[:-3], w[:-2], w[:-1])):
                if len(cand) >= (2 if k == 0 else 4):          # 2 harfli ülke kodu yalnızca tam sözcük olarak; ekli biçimlerde (almanya-dan) en az 4 harf
                    s = vpn.find_server(cfg, cand)
                    if s:
                        return s
    return None


ALIAS = {"amerika": "ABD", "abd": "ABD", "ingiltere": "İngiltere", "birleşik krallık": "İngiltere"}


def _named_country(t: str):
    """Cümlede bir ülke adı geçiyorsa (sunucumuz olmasa da) adını döner: 'Almanya için sunucunuz yok' diyebilmek için."""
    low = lambda x: x.replace("İ", "i").replace("I", "ı").lower()
    names = {low(n): n for n in vpn.COUNTRIES.values()}
    names.update({low(k): v for k, v in ALIAS.items()})
    for w in re.findall(r"[a-zçğıöşü0-9]+", low(t)):
        for cand in (w, w[:-3], w[:-2], w[:-1]):
            if len(cand) >= 3 and cand in names:
                return names[cand]
    return None


def _where(st: dict) -> str:
    i = st.get("info") or {}
    return (i.get("country") or "") + (f", {i['city']}" if i.get("city") else "")


def _direct_text() -> str:
    d = vpn.direct_ip()
    return (d["country"] + (f", {d['city']}" if d.get("city") else "")) if d else ""


def command(t: str, raw: str = ""):
    """VPN komutu değilse None; değilse {'say': ..., 'do': ...}."""
    # dar tutulur: "hangi ülkenin başkenti Paris" gibi genel sorular VPN sorusu sanılmasın
    if not re.search(r"\bvpn\b|\bip adres\w*|\bip\w* ne\b|\bipm\b|\bipim\b|hangi ülke(?:de|den)\w*\s*(?:yim|yiz|çık\w*|görün\w*|bağlı\w*)|\bçıkış ülke\w*|\btürkiye\w*\s+dön\w*|doğrudan bağlan", t):
        return None
    if re.search(r"\bvpn\s+(?:modu\w*|ekranı\w*|paneli\w*|yönet\w*|ayar\w*)", t):          # pencereyi açma isteği: extras.route_scene karşılar
        return None
    cfg = vpn.load()
    st = vpn.status()
    srv_in = _country(cfg, t)
    # --- kapat / doğrudan bağlantıya dön
    if (re.search(r"\bvpn\b", t) and re.search(r"\b(kapat|kes|durdur|sonlandır|bırak|devre dışı|kapa)\w*", t)) or re.search(r"\btürkiye\w*\s+dön\w*|doğrudan bağlan\w*|\bvpnsiz\w*", t):
        was = vpn.disconnect()
        return {"do": {"refresh": True}, "say": "VPN kapatıldı efendim, Jarvis tarayıcısı artık doğrudan Türkiye'den çıkıyor." if was else
                "VPN zaten kapalı efendim, tarayıcı doğrudan Türkiye'den çıkıyor."}
    # --- durum / ülke / ip
    if re.search(r"\b(durum\w*|açık mı|bağlı mı|hangi ülke\w*|ülkede\w*|nereden çık\w*|çıkış ülke\w*|ip adres\w*|ip\w* ne|ipm|ipim)\b", t) and not re.search(r"\b(aç|bağlan|başlat|test)\b", t):
        if st["state"] == "on":
            s = (st["server"] or {})
            return {"say": f"VPN açık efendim. Jarvis tarayıcısı {_where(st)} üzerinden çıkıyor" + (f" ({s.get('name')} sunucusu)" if s.get("name") else "") + "." + (" " + st["err"] if st.get("err") else "")}
        if st["state"] in ("connecting", "reconnecting"):
            return {"say": "VPN şu an bağlanıyor efendim, birkaç saniye bekleyin."}
        if st.get("kill"):
            return {"say": "VPN koptu efendim; güvenlik için tarayıcı internete çıkmıyor. VPN aç ya da VPN kapat deyin."}
        d = _direct_text()
        return {"say": "VPN kapalı efendim. Jarvis tarayıcısı doğrudan çıkıyor" + (f", yani {d} görünüyor." if d else ".")}
    # --- test
    if re.search(r"\b(test\w*|kontrol\w*|doğrula\w*|sızıntı\w*)\b", t) and re.search(r"\b(vpn|ip|sızıntı\w*)\b", t):
        d = _direct_text()
        if st["state"] != "on":
            return {"do": {"refresh": True}, "say": "VPN açık değil efendim, şu an doğrudan " + (d or "internete bağlısınız") + " görünüyorsunuz."}
        try:
            tun = vpn.tunnel_ip(st["port"])
        except Exception as e:
            return {"say": f"Tünel testi başarısız efendim ({type(e).__name__}). VPN'i kapatıp yeniden açmayı deneyin."}
        if not tun:
            return {"say": "Tünelden çıkış IP'si ölçülemedi efendim."}
        same = d and tun and (tun["ip"] == (vpn.S["direct"] or {}).get("ip"))
        if same:
            return {"say": "DİKKAT efendim: tünelden ölçülen IP, doğrudan IP ile aynı. Sunucu gerçekten başka bir yerden çıkmıyor olabilir; sunucunun konumunu kontrol edin."}
        return {"do": {"refresh": True}, "say": f"Test başarılı efendim. Doğrudan {d or 'bilinmiyor'}, tünelden {tun['country']}" + (f", {tun['city']}" if tun.get("city") else "") + " görünüyorsunuz."}
    named = None if srv_in else _named_country(t)
    if named and re.search(r"\b(aç|bağlan|bağla|başlat|yap|seç|değiştir|geç|olsun)\w*", t):
        return {"say": f"{named} için eklenmiş bir VPN sunucunuz yok efendim. VPN modunda o ülkede bir sunucu ekleyebilirsiniz."}
    # --- sunucu seç / ülke değiştir
    if (re.search(r"\b(ülke\w*|sunucu\w*)\b", t) and re.search(r"\b(yap|seç|değiştir|olsun|geç)\w*", t) and srv_in) or (srv_in and not re.search(r"\b(aç|bağlan|bağla|başlat)\w*", t) and re.search(r"\bvpn\b", t)):
        vpn.set_active(srv_in["id"])
        if st["state"] in ("on", "connecting", "reconnecting"):
            threading.Thread(target=vpn.connect, args=(srv_in["id"],), daemon=True).start()
            return {"do": {"refresh": True}, "say": f"{srv_in['name']} sunucusuna geçiyorum efendim."}
        return {"do": {"refresh": True}, "say": f"VPN ülkesi {srv_in['name']} oldu efendim. VPN aç dediğinizde oradan bağlanırım."}
    # --- sunucu listesi
    if re.search(r"\b(sunucu\w*|ülkeler\w*)\b", t) and not re.search(r"\b(ekle|sil|seç|değiştir|aç|bağlan|bağla|yap|geç)\w*", t):
        if not cfg["servers"]:
            return {"say": "Henüz VPN sunucusu eklenmemiş efendim. VPN modunu açıp ekleyin."}
        return {"say": "VPN sunucularınız: " + ", ".join(f"{s['name']} ({vpn.COUNTRIES.get(s['cc'], s['cc'])})" for s in cfg["servers"]) + "."}
    # --- bağlan
    if re.search(r"\b(aç|aktif|bağlan|bağla|başlat|çalıştır|devreye)\w*", t) and (re.search(r"\bvpn\b", t) or srv_in):
        if not cfg["servers"]:
            return {"say": "Henüz VPN sunucusu eklemediniz efendim. VPN modunu açın; orada kendi sunucunuzu eklemeniz için adım adım rehber var."}
        target = srv_in or next((s for s in cfg["servers"] if s["id"] == cfg["active"]), cfg["servers"][0])
        if st["state"] == "on" and (st["server"] or {}).get("id") == target["id"]:
            return {"say": f"VPN zaten açık efendim, {_where(st)} üzerinden çıkıyorsunuz."}
        if srv_in:
            vpn.set_active(target["id"])
        threading.Thread(target=vpn.connect, args=(target["id"],), daemon=True).start()
        return {"do": {"refresh": True}, "say": f"VPN {target['name']} sunucusuna bağlanıyor efendim, birkaç saniye sürer."}
    return None


def vpn_mode(text: str, st: dict):
    import scenes
    t = scenes.norm(text)
    raw = " ".join(str(text).split())
    r = command(t, raw)
    if r:
        return r
    if re.search(r"\b(bağlan|bağla|geç|yap|seç|değiştir)\w*", t) and (_country(vpn.load(), t) or _named_country(t)):       # mod içindeyken 'amerikadan bağlan' (VPN sözcüğü olmadan)
        r = command(t + " vpn", raw)
        if r:
            return r
    if len(t.split()) <= 2 and _country(vpn.load(), t) and not re.search(r"\b(sil|kapat|durum)\w*", t):          # yalnızca ülke adı söylendi: oraya bağlan
        r = command(t + " vpn aç", raw)
        if r:
            return r
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "VPN aç, Amerika'dan bağlan, VPN kapat, VPN durumu, hangi ülkedeyim, VPN testi, ülkeyi Almanya yap ve VPN sunucularım diyebilirsiniz. "
                       "Sunucu eklemek ve kurulum rehberi için ekrandaki bölümleri kullanın."}
    if re.search(r"\b(tarayıcı\w*)\b", t) and re.search(r"\b(aç|göster)\w*", t):
        jbrowser.open_url("https://www.google.com/")
        return {"say": "Jarvis tarayıcısını açtım efendim."}
    return {"say": "Anlayamadım efendim. VPN aç, VPN kapat, VPN durumu ya da VPN testi diyebilirsiniz."}


def ws(d: dict, st: dict):
    t = str(d.get("type", ""))[4:]
    s = lambda k, n=200: str(d.get(k) or "")[:n]
    if t == "connect":
        sid = s("id", 10) or None
        threading.Thread(target=vpn.connect, args=(sid,), daemon=True).start()
        return {"say": "Bağlanıyor…", "quiet_say": True}
    if t == "disconnect":
        vpn.disconnect()
        return {"say": "VPN kapatıldı.", "quiet_say": True}
    if t == "add":
        srv, err = vpn.add_server({"name": s("name", 30), "host": s("host", 253), "port": d.get("port"), "user": s("user", 32), "cc": s("cc", 2)})
        return {"say": (f"{srv['name']} sunucusu eklendi." if srv else err), "quiet_say": True}
    if t == "remove":
        return {"say": "Sunucu silindi." if vpn.remove_server(s("id", 10)) else "Sunucu bulunamadı.", "quiet_say": True}
    if t == "select":
        vpn.set_active(s("id", 10))
        return {}
    if t == "keygen":
        try:
            vpn.ensure_key()
        except Exception as e:
            return {"say": "Anahtar üretilemedi: " + str(e)[:120], "quiet_say": True}
        return {"say": "Anahtar hazır.", "quiet_say": True}
    if t == "forget":
        return {"say": "Parmak izi sıfırlandı; bir sonraki bağlantıda yeniden kaydedilecek." if vpn.forget_host(s("id", 10)) else "Parmak izi bulunamadı.", "quiet_say": True}
    if t == "pref":
        import settings
        if s("key", 20) == "own":
            settings.set("kendi_tarayici", bool(d.get("on")))
        return {}
    if t == "auto":
        cfg = vpn.load()
        cfg["auto"] = bool(d.get("on"))
        vpn.save(cfg)
        return {}
    if t == "test":
        def job():
            dd = vpn.direct_ip()
            stt = vpn.status()
            tun = None
            if stt["state"] == "on":
                try:
                    tun = vpn.tunnel_ip(stt["port"])
                except Exception:
                    tun = None
            if not dd and not tun:
                return {"say": "IP servisine ulaşılamadı."}
            vpn.S["info"] = tun or vpn.S["info"]
            msg = "Doğrudan: " + (f"{dd['country']}" if dd else "?")
            if stt["state"] == "on":
                msg += " · Tünelden: " + (tun["country"] if tun else "ölçülemedi")
            return {"say": msg}
        return {"say": "Test ediliyor…", "later": job, "quiet_say": True}
    if t == "browser":
        url = s("url", 300) or "https://www.google.com/"
        return {"say": "Jarvis tarayıcısı açıldı." if jbrowser.open_url(url) else "Adres geçersiz.", "quiet_say": True}
    if t == "browser_close":
        jbrowser.close()
        return {"say": "Jarvis tarayıcısı kapatıldı.", "quiet_say": True}
    return {}


def view() -> dict:
    """Arayüze giden bütün görünüm: VPN durumu + Jarvis tarayıcısı durumu + tercihler."""
    import settings
    v = vpn.view()
    v["own"] = settings.get("kendi_tarayici") is not False
    v["browser"] = jbrowser.status()
    return v


def init_payload():
    try:
        vpn.ensure_key()
    except Exception:
        pass
    return view()
