"""Friday modu komutları. Serbest cümleler friday.ask'e (araç döngüsü, arka planda) gider; burada yalnızca kısa komutlar var:
yardım, sus/iptal, yeni konuşma, öğrenmeyi durdur/başlat, 'X'i öğren' / 'şimdi öğren' (arka plan bilgi kuyruğu), 'öğrendiklerini sil' (iki adımlı onay).
'Araştır' bilerek buraya alınmadı: Friday için araştırma bir iştir (research aracıyla yapılır ve cevap verilir). Çıkış scenes.handle içinde."""
import re

import friday
import scenes
from ultron_learn import FRIDAY as L


def init_payload():
    return friday.init_payload()


def friday_mode(text: str, st: dict):
    raw = text.strip()
    t = scenes.norm(text)
    if not t:
        return None
    if st.pop("forget", False):                                   # bir önceki cümle 'öğrendiklerini sil' idi
        if re.fullmatch(r"(evet|sil|onaylıyorum|tamam|sil gitsin|unut)", t):
            L.forget_all()
            return {"do": {"learn": {"phase": "note", "snap": L.snapshot()}}, "say": "Tamam, öğrendiğim notların hepsini sildim."}
        return {"say": "Peki, silmedim."}
    if re.fullmatch(r"(yardım|neler yapabilirsin|komutlar)", t):
        return {"say": friday.HELP}
    if re.fullmatch(r"(sus|dur|yeter|kes|iptal|tamam yeter|sustur|sessiz ol)", t):
        friday.cancel()
        return {"do": {"stop": True, "busy": False}, "say": ""}
    if len(t.split()) <= 4 and re.search(r"\b(yeni (konuşma|sohbet)|sohbeti (sıfırla|temizle)\w*|geçmişi (sil|temizle)\w*|baştan başlayalım)\b", t):
        friday.reset()
        return {"do": {"reset": True, "snap": friday.snapshot()}, "say": "Konuşmayı ve işlem günlüğünü temizledim. Öğrendiklerim duruyor."}
    if re.search(r"\böğren\w* (durdur|kapat|bırak|kes|dur)\w*|\böğrenme\w* (durdur|kapat|bırak|kes)\w*|\bartık öğrenme\b", t):
        L.set_enabled(False)
        return {"do": {"learn": {"phase": "kapalı", "snap": L.snapshot()}}, "say": "Tamam, arka plandaki öğrenmeyi durdurdum."}
    if re.search(r"\böğren\w* (başlat|aç|sürdür|devam)\w*|\böğrenmeye (başla|devam)\w*", t):
        L.set_enabled(True)
        return {"do": {"learn": {"phase": "boşta", "snap": L.snapshot()}}, "say": "Öğrenmeye devam ediyorum."}
    if re.search(r"\b(öğrendik\w*|notlar\w*|bildiklerin\w*)\w* (sil|unut|temizle)\w*|\b(hepsini|her şeyi) unut\b", t):
        st["forget"] = True
        return {"say": "Öğrendiğim her şeyi silmemi istiyorsun, emin misin? Evet dersen hepsi gider."}
    m = re.match(r"^(.+?)\s+(?:hakkında\s+|ile ilgili\s+)?(?:internette\s+)?öğren\w*$", t)
    if (m and len(m.group(1)) >= 3 and not re.search(r"\b(ne|neler|neyi|nasıl|niye|neden)\b", m.group(1))) or re.fullmatch(r"(hemen )?(bir şey öğren|bir şeyler öğren|öğren)", t):
        topic = L.clean(m.group(1), 80).strip(" .,!?") if m else ""
        if m and len(topic) < 3:
            return {"say": "Bunu konu olarak anlayamadım, biraz daha açık söyler misin?"}
        if not L.learn_now(topic or None):
            return {"say": "Şu an zaten bir şey öğreniyorum, bitince bakarım."}
        return {"do": {"learn": {"phase": "konu seçti", "topic": topic, "snap": L.snapshot()}},
                "say": (f"Tamam, {topic} konusunu arka planda öğreniyorum." if topic else "Tamam, merak ettiğim bir şeye bakıyorum.")}
    return friday.ask(raw)
