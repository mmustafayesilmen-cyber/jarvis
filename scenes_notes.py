"""Not modu komut işleyicisi (sesle/yazıyla). Çıktı: {'do': sayfaya giden komut, 'say': konuşulacak metin}."""
import html as _html
import re

import notes

COLORS = {"kırmızı": "#ff5a5a", "mavi": "#5aa8ff", "yeşil": "#5ee08a", "sarı": "#ffd84a", "turuncu": "#ff9a3c", "mor": "#b58cff", "pembe": "#ff7ac8", "siyah": "#111111",
          "beyaz": "#ffffff", "gri": "#9aa4ad", "turkuaz": "#3fe0d0", "lacivert": "#1d3a8a", "kahverengi": "#8a5a32", "altın": "#e8b84a"}
BG = {"koyu mavi": "#10233f", "koyu yeşil": "#10301f", "koyu kırmızı": "#3a1414", "koyu mor": "#26143f", "açık sarı": "#fff6c8", "açık mavi": "#d8ecff", "açık yeşil": "#dcf5df",
      "açık pembe": "#ffe0ee", "krem": "#f5ecd7", "siyah": "#0a0a0a", "beyaz": "#fafafa", "gri": "#2a2d31"}
SYM = {"yıldız": "✦", "kalp": "♥", "çiçek": "❀", "kuş": "✈", "güneş": "☀", "ay": "☾", "müzik": "♪", "onay": "✔", "ok": "➤", "kalem": "✎", "şimşek": "⚡", "elmas": "◆", "çan": "🔔"}
FONT_WORDS = {"georgia": "Georgia", "consolas": "Consolas", "comic": "Comic Sans MS", "trebuchet": "Trebuchet MS", "impact": "Impact", "palatino": "Palatino Linotype",
              "times": "Times New Roman", "courier": "Courier New", "el yazısı": "Segoe Script", "el yazisi": "Segoe Script", "verdana": "Verdana", "arial": "Arial", "segoe": "Segoe UI",
              "bahnschrift": "Bahnschrift", "candara": "Candara", "constantia": "Constantia", "ink free": "Ink Free", "lucida": "Lucida Handwriting", "brush": "Brush Script MT"}


def _norm(text: str) -> str:
    t = text.replace("İ", "i").replace("I", "ı").lower()
    t = re.sub(r"['’]\w*", "", t)
    t = re.sub(r"[^\w\sçğıöşü%:,.+\-]", " ", t)
    t = re.sub(r"\b(jarvis|hey|lütfen|bana|şunu|efendim|hadi|şimdi)\b", " ", t)
    return " ".join(t.split())


def _color_in(t: str):
    for k in sorted(COLORS, key=len, reverse=True):
        if re.search(r"\b" + k + r"\b", t):
            return COLORS[k]
    return None


def _titles(n=8):
    return [x["title"] for x in notes.listing()[:n]]


def notlar(text: str, st: dict):
    t = _norm(text)
    raw = " ".join(text.split())
    if st.get("confirm") == "all":
        st["confirm"] = None
        if re.match(r"^(evet|onaylıyorum|onaylıyorum|tamam|sil|evet sil)\b", t):
            n = notes.delete_all()
            return {"do": {"notes": notes.listing(), "closeEditor": True}, "say": f"{n} notun hepsi kalıcı olarak silindi efendim."}
        return {"say": "Vazgeçtim efendim, notlara dokunmadım."}
    if re.search(r"^(yeni|boş) not( aç| oluştur| başlat)?$|^not oluştur$|^yeni sayfa$", t):
        return {"do": {"new": True}, "say": "Yeni not hazır efendim. Başlık söyleyip içeriği yaz diyerek ekleyebilirsiniz."}
    # --- yazma (dikte)
    m = re.match(r"^(?:başlık|konu)\s*[:,]?\s+(.+)$", t)
    if m:
        title = raw.split(None, 1)[1].lstrip(":, ").strip() if len(raw.split(None, 1)) > 1 else m.group(1)
        return {"do": {"title": title[:120]}, "say": f"Başlık: {title[:60]}."}
    m = re.match(r"^((?:[a-zçğıöşü]+ ){0,3}?)(yaz|ekle|not et|not al|dikte et)\b\s*[:,]?\s*(.+)$", t)
    if m and not re.search(r"\b(sil|kaydet|aç|oku|listele)\b", m.group(1)):
        pre = m.group(1)
        # özgün yazımı koru (büyük harf, noktalama)
        body = re.split(r"\b(?:yaz|ekle|not et|not al|dikte et)\b\s*[:,]?\s*", raw, maxsplit=1, flags=re.I)
        body = (body[1] if len(body) > 1 else m.group(3)).strip()
        if body:
            a = {"text": body[:2000]}
            if re.search(r"kalın|bold|koyu", pre):
                a["bold"] = True
            if re.search(r"italik|eğik", pre):
                a["italic"] = True
            if re.search(r"altı çizili|altını çiz", pre):
                a["underline"] = True
            if re.search(r"büyük", pre):
                a["size"] = 28
            if re.search(r"küçük", pre):
                a["size"] = 12
            if re.search(r"başlık", pre):
                a["heading"] = True
            if re.search(r"madde|liste", pre):
                a["bullet"] = True
            c = _color_in(pre)
            if c:
                a["color"] = c
            return {"do": {"append": a}, "say": "Yazdım efendim."}
    m = re.match(r"^madde(?: ekle)?\s*[:,]?\s*(.+)$", t)
    if m:
        body = re.split(r"madde(?: ekle)?\s*[:,]?\s*", raw, maxsplit=1, flags=re.I)[-1]
        return {"do": {"append": {"text": body[:500], "bullet": True}}, "say": "Madde eklendi efendim."}
    if re.search(r"^(çizgi|ayraç|ayırıcı) (ekle|çiz|koy)$", t):
        return {"do": {"insert": "divider"}, "say": "Süslü ayraç eklendi efendim."}
    if re.search(r"^(kutu|çerçeve|vurgu kutusu|uyarı kutusu) (ekle|çiz|koy)$", t):
        return {"do": {"insert": "box"}, "say": "Çerçeveli kutu eklendi efendim."}
    for k, v in SYM.items():
        if re.search(r"^" + k + r" (ekle|koy|çiz)$", t):
            return {"do": {"insert": "sym", "sym": v}, "say": f"{v} eklendi efendim."}
    # --- biçim (seçili metne ya da yazılacak yere)
    if re.search(r"^(kalın|bold)( yap| olsun)?$", t):
        return {"do": {"fmt": {"bold": True}}, "say": "Kalın yaptım efendim."}
    if re.search(r"^(italik|eğik)( yap| olsun)?$", t):
        return {"do": {"fmt": {"italic": True}}, "say": "İtalik yaptım efendim."}
    if re.search(r"^(altını çiz|altı çizili( yap)?)$", t):
        return {"do": {"fmt": {"underline": True}}, "say": "Altını çizdim efendim."}
    if re.search(r"^(üstünü çiz|üstü çizili( yap)?)$", t):
        return {"do": {"fmt": {"strike": True}}, "say": "Üstünü çizdim efendim."}
    if re.search(r"^(ortala|ortaya al)$", t):
        return {"do": {"fmt": {"align": "center"}}, "say": "Ortaladım efendim."}
    if re.search(r"^(sola yasla|sola al)$", t):
        return {"do": {"fmt": {"align": "left"}}, "say": "Sola yasladım efendim."}
    if re.search(r"^(sağa yasla|sağa al)$", t):
        return {"do": {"fmt": {"align": "right"}}, "say": "Sağa yasladım efendim."}
    m = re.search(r"(?:zemin|arka plan|sayfa)\w* (?:rengi|renk)\w*\s*(.+)$|(?:zemini|arka planı|sayfayı)\s+(.+?)\s*(?:yap|olsun)?$", t)
    if m:
        name = (m.group(1) or m.group(2) or "").strip()
        for k in sorted(BG, key=len, reverse=True):
            if k in name:
                return {"do": {"bg": BG[k]}, "say": f"Not zemini {k} oldu efendim."}
    m = re.search(r"(?:vurgula|işaretle|fosforla)\s*(\w+)?", t)
    if m and re.search(r"^(vurgula|işaretle|fosforla)", t):
        c = _color_in(t) or "#ffd84a"
        return {"do": {"fmt": {"hilite": c}}, "say": "Vurguladım efendim."}
    if re.search(r"(yazı|yazının|harf)\w* (rengi|renk)|rengini|renk yap", t) or re.fullmatch(r"(\w+) (yap|olsun)", t):
        c = _color_in(t)
        if c:
            return {"do": {"fmt": {"color": c}}, "say": "Yazı rengini değiştirdim efendim."}
    m = re.search(r"(?:yazı tipi|yazı tipini|font|fontu|yazı stilini|yazı stili)\s+(.+?)(?:\s+(?:yap|olsun))?$", t)
    if m:
        name = m.group(1)
        for k, v in FONT_WORDS.items():
            if k in name:
                return {"do": {"fmt": {"font": v}}, "say": f"Yazı tipi {v} oldu efendim."}
    m = re.search(r"(?:yazı boyutu|yazı boyutunu|boyut|punto|puntoyu)\s*(\d{1,2})|(\d{1,2})\s*punto", t)
    if m:
        n = max(8, min(72, int(m.group(1) or m.group(2))))
        return {"do": {"fmt": {"size": n}}, "say": f"Yazı boyutu {n} oldu efendim."}
    # --- kaydet / sil / aç / liste
    if re.search(r"^(kaydet|notu kaydet|kaydı yap)$", t):
        return {"do": {"save": True}, "say": "Notu kaydettim efendim."}
    if re.search(r"^(tüm|bütün|hepsini|bütün notları|tüm notları|notların hepsini)\w* (notları |notlarım )?(sil|temizle)|^(tüm|bütün) notları (sil|temizle)$|^notların hepsini sil$", t):
        st["confirm"] = "all"
        return {"say": f"Tüm notlar kalıcı olarak silinecek, geri dönüşü yok. Onaylıyor musunuz? Evet ya da vazgeç deyin."}
    if re.search(r"^(bu |açık |şu )?notu sil$|^notu kaldır$", t):
        return {"do": {"delete_current": True}, "say": "Açık notu sildim efendim."}
    m = re.search(r"^(.+?) not(?:unu|u|um)? (sil|kaldır)$", t)
    if m and m.group(1) not in ("bu", "açık", "şu"):
        n = notes.find(m.group(1))
        if n:
            notes.delete(n["id"])
            return {"do": {"notes": notes.listing(), "closeEditor": True}, "say": f"{n['title']} notunu sildim efendim."}
        return {"say": "Böyle bir not bulamadım efendim."}
    if re.search(r"^(notları|notlarımı|notlar)( listele| göster| say| oku)?$|^neler yazmışım$|^kaç notum var$", t):
        ti = _titles()
        if not ti:
            return {"do": {"tab": "notes"}, "say": "Henüz hiç notunuz yok efendim."}
        return {"do": {"tab": "notes"}, "say": f"{len(notes.listing())} notunuz var. En yeniler: " + ", ".join(ti[:5]) + "."}
    if re.search(r"^hatıra\w*( göster| listele| oku)?$|^neleri hatırlıyorsun$", t):
        return {"do": {"tab": "facts"}, "say": "Jarvis'in hatırladıkları ekranda efendim. Silmek için yanındaki düğmeye basın."}
    m = re.search(r"^(.+?) not(?:unu|u|um)? (aç|oku|göster)$|^(?:son not|son notu)( oku| aç| göster)?$", t)
    if m:
        n = notes.find(m.group(1)) if m.group(1) else (notes.listing() or [None])[0]
        if n:
            body = notes.plain(n["html"])
            return {"do": {"open": n["id"]}, "say": f"{n['title']}. " + (body[:400] if body != n["title"] else "")}
        return {"say": "Böyle bir not bulamadım efendim."}
    return {"say": "Not penceresindeyim efendim. Yeni not, başlık: …, yaz: …, kalın yaz: …, kırmızı yaz: …, madde: …, kaydet, notu sil, notları listele ya da yazı tipi georgia, yazı boyutu 24, zemin rengi koyu mavi diyebilirsiniz."}


def quick_add(text: str) -> str:
    r = notes.add_text(text, "jarvis")
    return f"Not aldım efendim: {r['title']}" if r else "Not alacak bir şey duymadım efendim."
