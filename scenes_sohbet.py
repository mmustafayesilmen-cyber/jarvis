"""Sohbet modu komutları. Her cümle (çıkış ve birkaç kısa komut dışında) sohbete gider: cevabı sohbet.ask arka planda üretir,
bu işlev hemen döner (konuşma döngüsü beklemez). Komutlar: yardım, sus/yeter, yeni sohbet, derin düşün / hızlı cevap ver / otomatik düşün,
'... bunu hatırla' (kalıcı hafızaya yazar)."""
import re

import scenes
import sohbet as S

_REM_END = re.compile(r"^(.*?)[,.\s]*\b(bunu|bunları|şunu)\s+(hatırla|aklında tut|kaydet)\w*$")
_REM_START = re.compile(r"^(hatırla|aklında tut|şunu hatırla|bunu hatırla)\s*[:,]?\s+(.+)$")


def init_payload():
    return S.init_payload()


def sohbet_mode(text: str, st: dict):
    raw = text.strip()
    t = scenes.norm(text)
    if not t:
        return None
    n = len(t.split())
    if re.fullmatch(r"(yardım|neler yapabilirsin|komutlar)", t):
        return {"say": S.HELP}
    if re.fullmatch(r"(sus|dur|yeter|kes|tamam yeter|sustur|sessiz ol)", t):
        S.cancel()
        return {"do": {"stop": True, "busy": False}, "say": ""}
    if n <= 4 and re.search(r"\b(yeni sohbet|sohbeti (sıfırla|temizle)\w*|geçmişi (sil|temizle)\w*|baştan başlayalım)\b", t):
        S.reset()
        return {"do": {"reset": True, "snap": S.snapshot()}, "say": "Yeni bir sohbete başlıyoruz efendim."}
    if n <= 5:
        if re.search(r"\b(derin düşün\w*|çok düşün\w*|hep düşün\w*|düşünmeyi aç\w*)", t):
            S.set_mode("hep")
            return {"do": {"think": "hep"}, "say": "Her cevapta önce düşüneceğim efendim. Cevaplar biraz geç gelebilir."}
        if re.search(r"\b(hızlı (cevap|yanıt|konuş)\w*|düşünmeyi kapat\w*|düşünme)\b", t):
            S.set_mode("hic")
            return {"do": {"think": "hic"}, "say": "Düşünmeden hızlı cevap vereceğim efendim."}
        if re.search(r"\botomatik düşün\w*|\bnormal düşün\w*", t):
            S.set_mode("auto")
            return {"do": {"think": "auto"}, "say": "Zor sorularda düşünüp basit sohbette hızlı cevap vereceğim efendim."}
    low = raw.replace("İ", "i").replace("I", "ı").lower()
    m = _REM_END.match(low) or _REM_START.match(low)
    if m and n <= 25:
        fact = (m.group(1) if m.re is _REM_END else m.group(2)).strip(" ,.")
        if len(fact) >= 3:
            import memory
            return {"say": memory.remember(fact.capitalize()).replace("Hatırlayacağım:", "Hatırlayacağım efendim:")}
    return S.ask(raw)
