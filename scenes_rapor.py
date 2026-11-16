"""Rapor modu komut işleyicisi (sesle/yazıyla). Çıktı: {'do': sayfaya giden komut, 'say': konuşulacak metin}.
Dikte edilen metin yalnızca sayfaya gider; günlüğe yazılmaz (rapor modu açıkken ses tanıma günlüğü metni gizler)."""
import re

import reports
import reports_parse
import scenes


def _cap(s: str) -> str:
    s = s.strip()
    return (("İ" if s[:1] == "i" else s[:1].upper()) + s[1:]) if s else s


def _after(raw: str, pattern: str) -> str:
    m = re.split(pattern, raw, maxsplit=1, flags=re.I)
    return (m[1] if len(m) > 1 else "").strip(" :,")


def rapor(text: str, st: dict):
    t = scenes.norm(text)
    raw = " ".join(text.split())
    c = st.get("confirm")
    if c:
        st["confirm"] = None
        if re.match(r"^(evet|onaylıyorum|tamam|sil|evet sil)\b", t):
            return {"do": {"deleteCurrent": True}, "say": "Raporu sildim efendim."}
        return {"say": "Vazgeçtim efendim, rapora dokunmadım."}
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Yeni rapor, başlık: …, yaz: …, kategori oluştur ders, kategori ders, tarih bugün, ders raporu şablonuyla yeni rapor, şablon kaydet haftalık, her cuma saat 17.00'de rapor hatırlat, raporu gönder, raporu sil ve raporları listele diyebilirsiniz."}
    if re.search(r"^(yeni|boş) rapor( aç| oluştur| başlat)?$|^rapor (oluştur|başlat|aç)$|^yeni sayfa$", t):
        return {"do": {"new": True}, "say": "Yeni rapor hazır efendim."}
    # ---- gönderme: yalnızca açık komutla, alıcı sabit
    if re.search(r"^rapor\w* ?(gönder|ilet|yolla)\w*$|^(gönder|ilet|yolla) (raporu|raporumu)$|^bunu (gönder|ilet)$", t):
        return {"do": {"requestSend": True}, "say": f"Raporu {reports.phone_label()} numarasına arka planda gönderiyorum efendim."}
    # ---- hatırlatıcı ("her cuma saat 17.00'de rapor yazmayı hatırlat")
    msg = reports_parse.handle(text)
    if msg:
        return {"do": {"data": reports.view()}, "say": msg}
    # ---- şablonlar
    if re.search(r"^şablon\w* (listele|göster|say|neler)\w*$|^(şablonlar|şablonlarım)$", t):
        names = [x["name"] for x in reports.view()["templates"]]
        return {"say": ("Şablonlarınız: " + ", ".join(names) + ".") if names else "Henüz şablonunuz yok efendim."}
    m = re.match(r"^şablon(?:u)?(?: olarak)? (?:kaydet|oluştur|ekle)\w*\s+(.+)$", t)
    if m:
        name = _cap(_after(raw, r"(?i)^şablon\w*(?: olarak)? (?:kaydet|oluştur|ekle)\w*"))[:30]
        return {"do": {"saveTemplate": name}, "say": f"Açık raporu {name} şablonu olarak kaydediyorum efendim."}
    m = re.match(r"^şablon\w* (?:sil|kaldır)\w*\s+(.+)$", t)
    if m:
        name = _after(raw, r"(?i)^şablon\w* (?:sil|kaldır)\w*")
        tp = reports.find_template(name)
        if tp and reports.delete_template(tp["name"]):
            return {"do": {"data": reports.view()}, "say": f"{tp['name']} şablonunu sildim efendim."}
        return {"say": "Böyle bir şablon bulamadım efendim."}
    m = re.match(r"^(.+?) şablon\w*(?: ile| yla| le| la)? (?:yeni rapor|rapor|başla|başlat|aç|kullan|getir)\w*$|^şablon\w*\s*[:,]?\s+(.+?)(?: kullan| aç| getir| başlat)?$", t)
    if m and not re.search(r"\b(listele|göster|kaydet|sil)\b", t):
        key = m.group(1) or m.group(2) or ""
        tp = reports.find_template(key)
        if not tp:
            return {"say": f"{key[:30]} adında bir şablon yok efendim. Şablonları listele diyebilirsiniz."}
        cat = reports.find_category(tp["cat"]) if tp["cat"] else ""
        return {"do": {"applyTemplate": {"title": tp["title"], "body": tp["body"], "cat": cat}}, "say": f"{tp['name']} şablonuyla yeni rapor hazır efendim."}
    # ---- kategori
    m = re.match(r"^kategori(?:si)? (?:oluştur|ekle|üret|yap|aç)\w*\s+(.+)$|^(.+?) kategori(?:si)?(?:ni)? (?:oluştur|ekle|üret)\w*$", t)
    if m:
        raw_name = _after(raw, r"(?i)kategori(?:si)?\s+(?:oluştur|ekle|üret|yap|aç)\w*") or (re.split(r"(?i)\s+kategori", raw)[0])
        name = reports.add_category(_cap(raw_name)[:30])
        if not name:
            return {"say": "Kategoriyi oluşturamadım efendim."}
        return {"do": {"data": reports.view(), "setCat": name}, "say": f"{name} kategorisini oluşturdum ve bu rapora verdim efendim."}
    m = re.match(r"^kategori(?:si|yi)? (?:sil|kaldır)\w*\s+(.+)$", t)
    if m:
        name = _after(raw, r"(?i)kategori(?:si|yi)?\s+(?:sil|kaldır)\w*")
        ok = reports.delete_category(name)
        return {"do": {"data": reports.view()}, "say": f"{name} kategorisini sildim, raporlar duruyor efendim."} if ok else {"say": "Böyle bir kategori yok efendim."}
    if re.search(r"^(kategoriyi|kategori) (kaldır|temizle|yok)", t):
        return {"do": {"setCat": ""}, "say": "Kategoriyi kaldırdım efendim."}
    m = re.match(r"^kategori(?:si|yi)?\s*[:,]?\s+(.+?)(?: yap| olsun)?$|^(.+?) kategori(?:si)?(?:ne)? (?:al|koy|ata|yap)$", t)
    if m:
        name_raw = _after(raw, r"(?i)^kategori(?:si|yi)?") if t.startswith("kategori") else re.split(r"(?i)\s+kategori", raw)[0]
        name_raw = re.sub(r"(?i)\s+(yap|olsun)$", "", name_raw).strip()
        name = reports.find_category(name_raw)
        if not name:
            return {"say": f"{name_raw[:30]} adında bir kategori yok efendim. Önce kategori oluştur {name_raw[:30]} deyin."}
        return {"do": {"setCat": name}, "say": f"Kategori {name} oldu efendim."}
    # ---- tarih
    if re.search(r"^tarih(?:i)? (bugün|bugünün tarihi|şimdi)\w*( yap)?$", t):
        return {"do": {"date": reports.view()["today"]}, "say": "Rapor tarihi bugün oldu efendim."}
    # ---- yazma (dikte)
    m = re.match(r"^(?:başlık|konu)\s*[:,]?\s+(.+)$", t)
    if m:
        title = _after(raw, r"(?i)^(?:başlık|konu)")
        return {"do": {"title": title[:120]}, "say": "Başlığı yazdım efendim."}
    m = re.match(r"^((?:[a-zçğıöşü]+ ){0,3}?)(yaz|ekle|dikte et|devam et)\b\s*[:,]?\s*(.+)$", t)
    if m and not re.search(r"\b(sil|kaydet|gönder|aç|oku|listele|kategori)\b", m.group(1)):
        body = _after(raw, r"(?i)\b(?:yaz|ekle|dikte et|devam et)\b")
        if body:
            return {"do": {"append": body[:4000]}, "say": "Yazdım efendim."}
    if re.search(r"^(son satırı|son cümleyi) (sil|kaldır)$", t):
        return {"do": {"undoLine": True}, "say": "Son satırı sildim efendim."}
    # ---- silme / liste / okuma
    if re.search(r"^(bu |açık )?(raporu|raporumu) (sil|kaldır)$|^raporu (iptal et)$", t):
        st["confirm"] = "one"
        return {"say": "Açık rapor kalıcı olarak silinecek. Onaylıyor musunuz? Evet ya da vazgeç deyin."}
    if re.search(r"^(raporları|raporlarımı|raporlar)( listele| göster| say| oku)?$|^kaç raporum var$", t):
        v = reports.view()
        n = len(v["reports"])
        if not n:
            return {"say": "Bekleyen rapor yok efendim."}
        return {"say": f"{n} taslak raporunuz var: " + ", ".join((r["title"] or "başlıksız") for r in v["reports"][:5]) + "."}
    if re.search(r"^(kategoriler|kategorileri)( listele| göster| say)?$", t):
        cs = reports.view()["categories"]
        return {"say": ("Kategorileriniz: " + ", ".join(cs) + ".") if cs else "Henüz kategori oluşturmadınız efendim. Kategori oluştur ders diyebilirsiniz."}
    return {"say": "Rapor modundayım efendim. Yazmak için yaz: …, başlık: …, kategori ders, raporu gönder diyebilirsiniz. Tüm komutlar için yardım deyin."}


def init_payload():
    return reports.view()
