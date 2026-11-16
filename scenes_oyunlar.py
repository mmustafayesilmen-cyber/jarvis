"""Zihin oyunları modu komutları: oyun seçimi (sayı dizisi, eşleştirme, hızlı hesap, renk dizisi), başla, menü, rekorlarım.
Oyun içindeki cevaplar ('yedi üç dokuz', 'on iki') sayfaya iletilir; doğru/yanlış kararını sayfadaki oyun verir."""
import re

import oyunlar as O
import scenes

PICK = [("element", r"element\w* (av\w*|oyun\w*|sorusu|bil\w*)|periyodik (tablo )?oyun\w*|kimya oyun\w*"), ("dizi", r"sayı dizi\w*|sayı oyun\w*|rakam\w* (oyun|dizi)\w*|hafıza oyun\w*|dizi oyun\w*"), ("eslestir", r"eşleştir\w*|eşleme\w*|kart oyun\w*|çift\w* bul"),
        ("hesap", r"hızlı hesap\w*|hesap oyun\w*|matematik oyun\w*|işlem oyun\w*"), ("simon", r"renk dizi\w*|renk oyun\w*|simon\w*|ışık oyun\w*")]


def oyunlar(text: str, st: dict):
    t = scenes.norm(text)
    if re.search(r"\b(yardım|neler var|hangi oyunlar|oyunlar neler|komutlar)\b", t):
        return {"say": "Beş oyun var: sayı dizisi, eşleştirme, hızlı hesap, renk dizisi ve element avı. Birinin adını söyleyin, sonra başla deyin. "
                       "Sayı dizisinde, hızlı hesapta ve element avında cevabı sesle de söyleyebilirsiniz. Rekorlarım diyerek en iyi skorlarınızı duyabilirsiniz."}
    for g, pat in PICK:
        if re.search(pat, t):
            st["game"] = g
            return {"do": {"game": g, "start": bool(re.search(r"\b(başla|başlat|oyna)\w*", t))}, "say": f"{O.GAMES[g]} efendim. Hazır olunca başla deyin."}
    if re.search(r"\b(rekor\w*|en iyi skor\w*|skorlarım|puanlarım)\b", t):
        v = O.view()
        parts = [f"{g['name']} {g['best']} {g['unit']}" for g in v["games"] if g["best"]]
        return {"say": ("Rekorlarınız: " + ", ".join(parts) + "." if parts else "Henüz rekorunuz yok efendim, bir oyun oynayalım.") + f" Bugün {v['today']} oyun oynadınız."}
    if re.search(r"\b(menü|ana menü|oyun seç|başka oyun|geri dön)\b", t):
        st.pop("game", None)
        return {"do": {"menu": True}, "say": "Oyun menüsü efendim."}
    if re.search(r"^(başla|başlat|hadi başla|tekrar|yeniden|yeniden başla|bir daha|tekrar oyna|oyna)$", t):
        return {"do": {"start": True}, "say": ""}
    if re.search(r"^(dur|durdur|bitir|duraklat)$", t):
        return {"do": {"stop": True}, "say": ""}
    # oyun içi cevap: sayfa değerlendirir (sesli söylemeye gerek yok, sonuç ekranda ve sesle bildirilir)
    return {"do": {"answer": str(text)[:120]}, "say": ""}


def ws(d: dict, st: dict):
    t = str(d.get("type", ""))[8:]
    if t == "score":
        g = str(d.get("game", ""))
        r = O.add_score(g, d.get("score"))
        if not r:
            return {}
        name, unit, sc = O.GAMES[g], O.UNIT[g], int(d.get("score") or 0)
        if r["record"]:
            say = f"Yeni rekor efendim! {name}: {sc} {unit}, önceki rekorunuz {r['prev']} idi."
        elif r["first"]:
            say = f"İlk skorunuz kaydedildi: {sc} {unit}."
        else:
            say = f"{sc} {unit}. Rekorunuz {r['best']}."
        return {"do": {"saved": g}, "say": say, "speak": True}
    if t == "say":                                   # sayı dizisinin sesli modu: rakamları Jarvis okur
        txt = str(d.get("text", ""))[:200]
        return {"do": {"quiet": True}, "say": txt, "speak": True} if txt else {}
    return {}


def init_payload():
    return O.view()
