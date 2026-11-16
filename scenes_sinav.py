"""Sınav modu komutları: 'matematik sınavı 15 kasım', 'fizik sınavı 3 gün sonra konu elektrik', 'sınavlarım', 'sıradaki sınav', 'matematik sınavını sil', 'bugün ne çalışayım', 'yarın hangi dersler var'.
Tarih ayrıştırma agenda.parse_when ile yapılır; ders programı schedule.py'den okunur (değiştirilmez). Kişisel veri: yalnızca yerel, uzaktan erişime kapalı."""
import datetime
import re

import agenda
import scenes
import schedule
import sinav as X


def _res(say: str):
    return {"do": {"data": X.view()}, "say": say}


def _fmt(e) -> str:
    n = e["kalan"]
    return f"{e['ders']} {'bugün' if n == 0 else 'yarın' if n == 1 else str(n) + ' gün sonra'}"


def sinav(text: str, st: dict):
    t = scenes.norm(text)
    if not t:
        return None
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Matematik sınavı on beş kasım diyerek sınav ekleyebilir, konu elektrik diye konu belirtebilirsiniz. Sınavlarım, sıradaki sınav, bugün ne çalışayım, yarın hangi dersler var ve matematik sınavını sil de var."}
    if re.search(r"\b(sil|kaldır|iptal)\w*", t) and re.search(r"sınav", t):
        m = re.search(r"([a-zçğıöşü ]+?)\s+sınav\w*", t)
        name = re.sub(r"\b(şu|bu|benim|sınav\w*)\b", "", m.group(1)).strip() if m else ""
        n = X.remove(name) if name else 0
        return _res(f"{name} sınavını sildim efendim." if n else "Silinecek bir sınav bulamadım efendim.")
    if re.search(r"\b(bugün|şimdi)\b.*\b(ne çalış\w*|çalışayım|çalışmam|hedef)\b|\bne çalış\w*\b", t):
        a = X.advice()
        return _res(a[0] if a else "Kayıtlı bir sınavınız yok efendim. Matematik sınavı on beş kasım diyerek ekleyebilirsiniz.")
    if re.search(r"\b(yarın|yarınki)\b.*\b(ders\w*|program\w*)\b", t):
        v = X.view()
        return _res(f"Yarın {v['yarin_gun']}: " + ", ".join(v["yarin"]) + "." if v["yarin"] else "Yarın ders yok efendim.")
    if re.search(r"\b(sıradaki|en yakın|ilk)\b.*sınav|\bsınav\w* ne zaman\b", t):
        ex = X.upcoming()
        return _res(f"Sıradaki sınav: {_fmt(ex[0])}." + (f" Konu: {ex[0]['konu']}." if ex[0].get("konu") else "") if ex else "Kayıtlı sınav yok efendim.")
    if re.search(r"\b(sınavlarım|sınavlar|kaç sınav|sınav listesi|sınavları)\b", t) and not re.search(r"\d", t):
        ex = X.upcoming()
        return _res(("Sınavlarınız: " + "; ".join(_fmt(e) for e in ex[:6]) + ".") if ex else "Kayıtlı sınavınız yok efendim.")
    m = re.search(r"([a-zçğıöşü ]+?)\s+sınav\w*", t)
    if m:
        pw = agenda.parse_when(t)
        if not pw:
            return {"say": "Sınav tarihini anlayamadım efendim. Örneğin matematik sınavı on beş kasım ya da fizik sınavı üç gün sonra deyin."}
        when = pw[0].date()
        if when < datetime.date.today():
            return {"say": "Bu tarih geçmişte kalmış efendim."}
        ders = re.sub(r"\b(benim|yeni|bir|şu|bu|ekle\w*|var|olacak|için|tarihi|kaydet\w*)\b", "", m.group(1)).strip()
        ders = ders.split(" ")[-2:] if len(ders.split()) > 2 else ders.split()
        ders = schedule.cap(" ".join(ders)) if ders else ""
        if not ders:
            return {"say": "Hangi dersin sınavı efendim?"}
        km = re.search(r"\bkonu\w*\s+(.+)$", t)
        konu = km.group(1).strip() if km else ""
        e = X.add(ders, when, konu)
        n = (when - datetime.date.today()).days
        return _res(f"{ders} sınavını {when.day} {agenda_month(when.month)} için kaydettim efendim, {n} gün var.")
    return {"do": {"data": X.view()}, "say": ""}


def agenda_month(m: int) -> str:
    return ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"][m]


def init_payload():
    return X.init_payload()
