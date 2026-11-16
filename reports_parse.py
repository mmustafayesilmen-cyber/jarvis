"""Rapor hatırlatıcısı için cümle çözümleyici. Hem normal Jarvis'te ('cuma 17.00'de rapor yazmayı hatırlat') hem rapor modunda kullanılır."""
import re

import reports

DAY_WORDS = [("pazartesi", 0), ("salı", 1), ("çarşamba", 2), ("perşembe", 3), ("cuma(?!rtesi)", 4), ("cumartesi", 5), ("pazar(?!tesi)", 6)]


def _norm(text: str) -> str:
    t = text.replace("İ", "i").replace("I", "ı").lower()
    t = re.sub(r"['’]\w*", "", t)
    t = re.sub(r"[^\w\sçğıöşü:.]", " ", t)
    return " ".join(t.split())


def parse(text: str):
    """None = rapor hatırlatıcısıyla ilgili değil. Aksi hâlde ('set', günler, 'SS:DD') | ('clear',) | ('show',) | ('need', eksik_açıklama)."""
    t = _norm(text)
    if not re.search(r"\brapor\w*", t) or not re.search(r"\bhatırlat\w*", t):
        return None
    if re.search(r"\b(iptal|kapat|sil|kaldır|durdur|gerek yok)\w*", t):
        return ("clear",)
    if re.search(r"\b(ne zaman|göster|kurulu mu|var mı|söyle|hangi)\b", t):
        return ("show",)
    days = set()
    if re.search(r"\bhafta içi\b", t):
        days = {0, 1, 2, 3, 4}
    elif re.search(r"\bhafta sonu\b", t):
        days = {5, 6}
    elif re.search(r"\bher gün\b|\bgünlük\b|\bhergün\b", t):
        days = set(range(7))
    else:
        for w, i in DAY_WORDS:
            if re.search(r"\b" + w + r"\w*", t):
                days.add(i)
    m = re.search(r"\b(\d{1,2})[:.](\d{2})\b", t) or re.search(r"\bsaat (\d{1,2})\b", t)
    hh = mm = None
    if m:
        hh, mm = int(m.group(1)), int(m.group(2)) if m.lastindex == 2 else 0
    if not days:
        return ("need", "Hangi gün olacak efendim? Örneğin her cuma saat 17.00 diyebilirsiniz.")
    if hh is None or not (0 <= hh <= 23 and 0 <= mm <= 59):
        return ("need", "Saat kaçta hatırlatayım efendim? Örneğin saat 17.00.")
    return ("set", sorted(days), f"{hh:02d}:{mm:02d}")


def handle(text: str):
    """parse sonucunu uygular; (konuşma metni) ya da None döndürür."""
    r = parse(text)
    if r is None:
        return None
    if r[0] == "need":
        return r[1]
    if r[0] == "clear":
        return "Rapor hatırlatıcısını kapattım efendim." if reports.clear_reminder() else "Zaten kurulu bir rapor hatırlatıcısı yok efendim."
    if r[0] == "show":
        lab = reports.reminder_label()
        return f"Rapor hatırlatıcınız: {lab}." if lab else "Kurulu bir rapor hatırlatıcısı yok efendim."
    lab = reports.set_reminder(r[1], r[2])
    return f"Tamam efendim, {lab} rapor yazma vakti geldiğini hatırlatacağım." if lab else "Hatırlatıcıyı kuramadım efendim."
