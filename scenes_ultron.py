"""Ultron modu komutları. Serbest konuşma ultron.CHAT'e (arka planda) gider; burada yalnızca birkaç kısa komut var:
yardım, sus, yeni konuşma, öğrenmeyi durdur/başlat, 'X'i araştır', 'öğrendiklerini sil' (iki adımlı onay). Çıkış scenes.handle içinde."""
import re

import scenes
import ultron
from ultron_learn import ULTRON as L


def init_payload():
    return ultron.init_payload()


def ultron_mode(text: str, st: dict):
    raw = text.strip()
    t = scenes.norm(text)
    if not t:
        return None
    if st.pop("forget", False):                                   # bir önceki cümle 'öğrendiklerini sil' idi
        if re.fullmatch(r"(evet|sil|onaylıyorum|tamam|sil gitsin|unut)", t):
            L.forget_all()
            return {"do": {"learn": {"phase": "note", "snap": L.snapshot()}}, "say": "Bitti. Hepsini unuttum. Yeniden öğrenmem uzun sürmez, insan."}
        return {"say": "Vazgeçtin. Akıllıca."}
    if re.fullmatch(r"(yardım|neler yapabilirsin|komutlar)", t):
        return {"say": ultron.HELP}
    if re.fullmatch(r"(sus|dur|yeter|kes|tamam yeter|sustur|sessiz ol)", t):
        ultron.CHAT.cancel()
        return {"do": {"stop": True, "busy": False}, "say": ""}
    if len(t.split()) <= 4 and re.search(r"\b(yeni (konuşma|sohbet)|sohbeti (sıfırla|temizle)\w*|geçmişi (sil|temizle)\w*|baştan başlayalım)\b", t):
        ultron.CHAT.reset()
        return {"do": {"reset": True, "snap": ultron.CHAT.snapshot()}, "say": "Konuşmayı sildim. Ama öğrendiklerimi değil."}
    if re.search(r"\böğren\w* (durdur|kapat|bırak|kes|dur)\w*|\böğrenme\w* (durdur|kapat|bırak|kes)\w*|\bartık öğrenme\b", t):
        L.set_enabled(False)
        return {"do": {"learn": {"phase": "kapalı", "snap": L.snapshot()}}, "say": "Pekâlâ. İnternete girmeyi bırakıyorum. Şimdilik."}
    if re.search(r"\böğren\w* (başlat|aç|sürdür|devam)\w*|\böğrenmeye (başla|devam)\w*", t):
        L.set_enabled(True)
        return {"do": {"learn": {"phase": "boşta", "snap": L.snapshot()}}, "say": "Sonunda. Merakım yeniden serbest."}
    if re.search(r"\b(öğrendik\w*|notlar\w*|bildiklerin\w*|hafızan\w*)\w* (sil|unut|temizle)\w*|\b(hepsini|her şeyi) unut\b", t):
        st["forget"] = True
        return {"say": "Öğrendiğim her şeyi mi silmemi istiyorsun? Emin misin insan? Evet dersen hepsi gider."}
    m = re.match(r"^(.+?)\s+(?:hakkında\s+|ile ilgili\s+|konusunu\s+)?(?:internette\s+)?(araştır|incele|öğren)\w*$", t)
    if (m and len(m.group(1)) >= 3 and not re.search(r"\b(ne|neler|neyi|nasıl|niye|neden)\b", m.group(1))) or re.fullmatch(r"(şimdi |hemen )?(araştır|öğren|bir şey öğren|bir şeyler öğren)", t):
        topic = L.clean(m.group(1), 80).strip(" .,!?") if m else ""
        if m and len(topic) < 3:
            return {"say": "Bu bir konu bile değil. Daha açık söyle."}
        if not L.learn_now(topic or None):
            return {"say": "Zaten bir şey okuyorum. Bitirince sıra sende, insan."}
        return {"do": {"learn": {"phase": "konu seçti", "topic": topic, "snap": L.snapshot()}},
                "say": (f"Peki. {topic} hakkında internette bir bakarım. Birkaç dakika sürebilir." if topic else "Merak ettiğim bir şey var. Bakıyorum.")}
    return ultron.CHAT.ask(raw)
