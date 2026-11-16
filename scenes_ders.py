"""Quiz modu (ders çalışma) komut işleyicisi (sesle/yazıyla). Çıktı: {'do': sayfaya giden komut, 'say': konuşulacak metin}.
Soru, ilerleme ve ekran durumu sayfada tutulur; burada cümle -> eylem dönüşümü yapılır."""
import re

import ders_data
import ders_srv
import scenes

DERS_WORDS = {"matematik": "matematik", "fizik": "fizik", "kimya": "kimya", "biyoloji": "biyoloji", "edebiyat": "edebiyat", "türk dili": "edebiyat", "tarih": "tarih", "coğrafya": "cografya"}
LETTERS = {"a": "A", "b": "B", "be": "B", "bi": "B", "c": "C", "ce": "C", "se": "C", "d": "D", "de": "D", "e": "E", "ee": "E"}
STAGES = {"anlatım": "anlatim", "konu anlatımı": "anlatim", "özet": "ozet", "etkinlik": "etkinlik", "quiz": "quiz", "kısa sınav": "quiz", "deneme": "deneme"}
ORD = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10}


def ders(text: str, st: dict):
    t = scenes.norm(text)
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Ders adını söyleyin, örneğin matematik. Ünite iki, konu üç, konuyu anlat, özet, etkinlik, quiz başlat, deneme başlat, devam et, soru sayısı 25, "
                       "B şıkkı, çözemedim, sonraki, önceki, kontrol et, sınavı bitir ve durdur diyebilirsiniz."}
    if re.search(r"^(durdur|dur|sus|sessiz ol|yeter)$|\b(anlatmayı|okumayı|anlatımı) (durdur|kes|bırak)\b", t):
        ders_srv.stop_narration()
        return {"do": {"stopNarr": True}}
    # ---- çözüm / tahta
    if re.search(r"\b(çözemedim|çözümü göster|çözümü anlat|tahtada (anlat|göster|çöz)|bu soruyu anlat|nasıl çözülür|yardım et)\b", t):
        return {"do": {"help": True}, "say": "Tamam efendim, çözümü tahtaya yazıp anlatıyorum."}
    # ---- cevap işaretleme
    m = re.match(r"^(?:şık |cevap |seçenek |işaretle |cevabım )?([a-e]|be|bi|ce|se|de|ee)(?: şıkkı| şık| şıkkını| seçeneği)?(?: işaretle| olsun)?$", t)
    if m:
        return {"do": {"answer": LETTERS[m.group(1)]}}
    if re.search(r"^(kontrol et|cevabı kontrol et|doğru mu|cevabı göster)$", t):
        return {"do": {"check": True}}
    if re.search(r"^(sonraki|ileri|sonraki soru|geç|bir sonraki)$", t):
        return {"do": {"next": True}}
    if re.search(r"^(önceki|geri|önceki soru)$", t):
        return {"do": {"prev": True}}
    if re.search(r"\b(sınavı bitir|testi bitir|bitir|sonuçları göster|sonuçları değerlendir|değerlendir)\b", t):
        return {"do": {"finish": True}, "say": "Sınavı bitiriyorum efendim."}
    if re.search(r"\b(bu soru|soru) (hatalı|yanlış|bozuk)\b|\bhatalı soru\b", t):
        return {"do": {"flag": True}, "say": "Soruyu hatalı olarak işaretliyorum efendim."}
    # ---- ayarlar
    m = re.search(r"\b(quiz|kısa sınav|deneme)\b.*?(\d{1,3})\s*soru|soru sayısı\s*(\d{1,3})", t)
    if m:
        n = int(m.group(2) or m.group(3))
        which = "deneme_n" if re.search(r"deneme", t) else "quiz_n"
        lo, hi = ders_data.LIMITS[which]
        n = max(lo, min(hi, n))
        return {"do": {"setting": {"name": which, "value": n}}, "say": f"{'Deneme' if which == 'deneme_n' else 'Quiz'} soru sayısı {n} oldu efendim."}
    if re.search(r"\binternet(ten)? kaynak\w* (aç|kullan)\b|\bkaynakları aç\b", t):
        return {"do": {"setting": {"name": "internet_kaynak", "value": True}}, "say": "İnternetten kaynak kullanımı açıldı efendim."}
    if re.search(r"\binternet(ten)? kaynak\w* (kapat|kullanma)\b|\bkaynakları kapat\b", t):
        return {"do": {"setting": {"name": "internet_kaynak", "value": False}}, "say": "İnternetten kaynak kullanımı kapatıldı efendim."}
    if re.search(r"\b(anında|her soruda|tek tek) kontrol\b|\bkontrol (anında|tek tek)\b", t):
        return {"do": {"setting": {"name": "anlik_kontrol", "value": True}}, "say": "Her soruda anında kontrol açıldı efendim."}
    if re.search(r"\b(sonda|sınav sonunda|en sonda) kontrol\b|\bkontrol (sonda|sonunda)\b", t):
        return {"do": {"setting": {"name": "anlik_kontrol", "value": False}}, "say": "Kontrol sınav sonunda yapılacak efendim."}
    # ---- gezinme
    if re.search(r"\b(devam et|kaldığım yerden|kaldığımız yerden)\b", t):
        return {"do": {"resume": True}, "say": "Kaldığınız yerden devam ediyoruz efendim."}
    if re.search(r"\b(ana ekran|ders seç|dersleri göster|başa dön|ders listesi)\b", t):
        return {"do": {"home": True}}
    m = re.search(r"\bünite (\d+|" + "|".join(ORD) + r")\b", t)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else ORD[m.group(1)]
        return {"do": {"pickUnite": n}}
    m = re.search(r"\bkonu (\d+|" + "|".join(ORD) + r")\b", t)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else ORD[m.group(1)]
        return {"do": {"pickKonu": n}}
    if re.search(r"\b(konuyu|anlatımı|dersi) (anlat|oku)|^anlat$|^oku$|\bkonu anlatımını (oku|anlat)\b", t):
        return {"do": {"narrate": "cur"}}
    if re.search(r"\bözeti (oku|anlat|göster)\b", t):
        return {"do": {"narrate": "ozet"}}
    for w, sid in sorted(STAGES.items(), key=lambda kv: -len(kv[0])):
        if re.search(r"\b" + w + r"\w*\b", t) and re.search(r"\b(başlat|başla|aç|geç|göster|git|hazırla)\b|^" + w + r"$", t):
            return {"do": {"stage": sid}, "say": f"{w.capitalize()} bölümüne geçiyorum efendim."}
    for w, did in DERS_WORDS.items():
        if re.search(r"\b" + w + r"\w*", t):
            return {"do": {"ders": did}, "say": f"{w.capitalize()} dersi, ünite ve konu seçebilirsiniz efendim."}
    return {"say": "Anlayamadım efendim. Ders adını söyleyebilir, ya da ekrandan seçebilirsiniz. Komutlar için yardım deyin."}


def init_payload():
    return ders_srv.init_payload()
