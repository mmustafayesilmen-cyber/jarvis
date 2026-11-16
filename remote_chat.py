"""Uzaktan sohbet: telefondan Jarvis ile yazışma. Bilgisayara erişim YOK:
- Yerel LLM (Ollama) araçsız ve hafızasız çalışır: brain.SYSTEM (araç listesi) ve memory.json (kişisel hafıza) bu sohbete HİÇ verilmez.
- Yazılı komut olarak yalnızca güvenli, bilgisayardan bağımsız olanlar çalışır: hava durumu, kur/birim dönüştürme, hesap makinesi, saat/tarih ve 'X modunu aç' (telefonda o sayfayı açar).
  Ses, ışık, güç, kilit, mesaj gönderme, uygulama/dosya, hatırlatıcı/zamanlayıcı gibi her şey reddedilir.
- Geçmiş yalnızca bağlantının RAM'indedir; diske yazılmaz."""
import datetime
import re

import ollama

import brain
import extras
import scenes

SYSTEM = ("Sen JARVIS'sin, kullanıcının kişisel asistanısın. Kullanıcıya 'efendim' diye hitap et, Türkçe ve kısa cevap ver (en çok üç dört cümle). "
          "Bu, telefondan uzaktan açılmış bir sohbet: bilgisayarda hiçbir işlem yapamazsın (uygulama açmak, ses, ışık, kilit, mesaj, dosya, ekran). "
          "Böyle bir istek gelirse bunu yalnızca bilgisayarın başındayken yapabileceğini söyle. Kullanıcının kişisel bilgilerini bilmezsin, uydurma. "
          "Bilmediğin şeyi bilmediğini söyle.")
MAX_TURNS = 10
_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
_MONTHS = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
_OPEN = re.compile(r"\b(aç|açar mısın|göster|git|başlat|getir|gir)\w*")


def safe_command(text: str, names: dict):
    """(yanıt, açılacak_mod) ya da (None, None). Yalnızca güvenli komutlar."""
    t = scenes.norm(text)
    if not t:
        return None, None
    if re.fullmatch(r"(saat kaç|saat kaçtı|şu an saat kaç|saati söyle|saat ne)", t):
        return f"Saat {datetime.datetime.now().strftime('%H:%M')} efendim.", None
    if re.fullmatch(r"(tarih ne|bugünün tarihi ne|bugün ayın kaçı|bugün günlerden ne|bugün hangi gün|hangi gündeyiz|günlerden ne)", t):
        d = datetime.date.today()
        return f"Bugün {d.day} {_MONTHS[d.month]} {d.year} {_DAYS[d.weekday()]} efendim.", None
    for fn in (extras.route_weather, extras.route_convert, extras.route_calc):
        try:
            r = fn(t)
        except Exception:
            r = None
        if r:
            return str(r), None
    if _OPEN.search(t):
        for kind, name in names.items():
            words = {kind, "internet" if kind == "browser" else kind, scenes.norm(name).replace(" lab", " laboratuvar")} | {w for w in scenes.norm(name).split() if len(w) > 3}
            if any(w in t for w in words):
                return f"{name} açılıyor efendim.", kind
    return None, None


def stream(history: list, text: str):
    """Yerel LLM'den parça parça yanıt üretir (araçsız, hafızasız). history güncellenir."""
    history.append({"role": "user", "content": text[:500]})
    del history[:-MAX_TURNS * 2]
    msgs = [{"role": "system", "content": SYSTEM}] + history
    out = ""
    for ch in ollama.chat(model=brain.MODEL, messages=msgs, keep_alive="5m", stream=True, **brain._extra(),
                          options={"temperature": 0.4, "num_ctx": brain.CTX, "repeat_penalty": 1.1}):
        piece = ch.message.content or ""
        if piece:
            out += piece
            yield piece
    history.append({"role": "assistant", "content": out.strip()[:1500]})
