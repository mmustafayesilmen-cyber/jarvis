"""Gelişim paneli komutları: bu hafta / geçen hafta, ne kadar çalıştım, en zayıf dersim, kartlar, raporu gönder (onaylı), taslak kaydet.
Rapor gönderimi dışarıya (WhatsApp) mesaj attığı için sesle istendiğinde önce 'evet' onayı beklenir; penceredeki düğme kendi onay kutusunu gösterir."""
import re
import time

import gelisim as G
import scenes


def _summary(v) -> str:
    T, Q = v["totals"], v["quiz"]
    if not (T["focus"] or T["cards"] or Q["week_n"]):
        return f"{v['label']} haftasında kayıtlı çalışma yok efendim." + (" Pomodoro geçmişi yeni tutulmaya başladı, önceki günlerin kaydı yok." if v["days"][0]["date"] < v["first"] else "")
    s = f"{v['label']}: {T['focus']} dakika odaklandınız, {T['rounds']} pomodoro turu, {T['active']} gün çalıştınız."
    if T["prev_focus"]:
        d = T["focus"] - T["prev_focus"]
        s += f" Geçen haftadan {abs(d)} dakika {'fazla' if d >= 0 else 'az'}."
    if T["cards"]:
        s += f" {T['cards']} kart tekrar ettiniz, yüzde {T['cards_pct']} doğru."
    if Q["week_n"]:
        s += f" {Q['week_n']} soru çözdünüz, yüzde {Q['week_pct']} doğru."
    if T["streak"] > 1 and v["offset"] == 0:
        s += f" {T['streak']} gündür kesintisiz çalışıyorsunuz."
    return s


def _send_now() -> str:
    import reports
    title, body = G.report_text(G.view(0 if _OFF[0] is None else _OFF[0]))
    r = reports.save("", title, body, cat="Haftalık")
    if not r:
        return "Rapor taslağı oluşturulamadı efendim, taslak sınırı dolmuş olabilir."
    st, msg = reports.send(r["id"])
    return msg


_OFF = [None]


def _start_send(st) -> dict:
    _OFF[0] = st.get("week", 0)
    st.pop("confirm", None)
    return {"do": {"sending": True}, "say": "Raporu Babam'a gönderiyorum efendim.", "later": _send_now}


def gelisim(text: str, st: dict):
    t = scenes.norm(text)
    v = G.view(st.get("week", 0))
    pending = time.time() - st.get("confirm", 0) < 60
    if pending and re.search(r"\b(evet|gönder|onaylıyorum|tamam|olur)\b", t) and not re.search(r"\b(hayır|iptal|vazgeç|gönderme)\b", t):
        return _start_send(st)
    if pending and re.search(r"\b(hayır|iptal|vazgeç|gönderme|dur)\b", t):
        st.pop("confirm", None)
        return {"do": {"confirm": False}, "say": "Tamam efendim, göndermedim."}
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Bu hafta, geçen hafta, ne kadar çalıştım, en zayıf dersim, kartlar nasıl gidiyor, raporu taslak olarak kaydet ve raporu babama gönder diyebilirsiniz."}
    if re.search(r"\b(rapor\w*)\b", t) and re.search(r"\b(gönder|ilet|yolla|at)\w*", t):
        st["confirm"] = time.time()
        return {"do": {"confirm": True}, "say": f"{v['label']} haftasının raporunu Babam'a WhatsApp'tan göndereyim mi? Evet ya da hayır deyin."}
    if re.search(r"\b(rapor\w*|taslak)\b", t) and re.search(r"\b(kaydet|hazırla|oluştur|taslak)\w*", t):
        import reports
        title, body = G.report_text(v)
        r = reports.save("", title, body, cat="Haftalık")
        return {"say": "Raporu rapor modunda taslak olarak kaydettim efendim, göndermedim." if r else "Taslak kaydedilemedi efendim."}
    if re.search(r"\b(geçen|önceki)\s+hafta\w*", t):
        st["week"] = max(-52, st.get("week", 0) - 1)
        return {"do": {"week": st["week"]}, "say": _summary(G.view(st["week"]))}
    if re.search(r"\b(sonraki)\s+hafta\w*", t):
        st["week"] = min(0, st.get("week", 0) + 1)
        return {"do": {"week": st["week"]}, "say": _summary(G.view(st["week"]))}
    if re.search(r"\bbu\s+hafta\w*", t) and not re.search(r"(ne kadar|kaç)", t):
        st["week"] = 0
        return {"do": {"week": 0}, "say": _summary(G.view(0))}
    if re.search(r"\b(zayıf|kötü|eksik|en düşük|çalışmam gereken|hangi ders)\w*", t):
        w = v["weakest"]
        if not w:
            rated = [b for b in v["quiz"]["by_ders"] if b["pct"] is not None and b["n"] >= 3]
            if len(rated) == 1:
                return {"say": f"Şimdilik yalnızca {rated[0]['ders']} dersinde soru çözdünüz, yüzde {rated[0]['pct']} doğru. Karşılaştırma için başka derslerden de Quiz çözün efendim."}
            return {"say": "Zayıf dersi söyleyebilmem için en az iki derste üçer soru çözülmüş olmalı efendim. Quiz modunda soru çözdükçe burada görünecek."}
        best = next((b for b in reversed(v["quiz"]["by_ders"]) if b["pct"] is not None and b["n"] >= 3), None)
        s = f"En zayıf dersiniz {w['ders']}, yüzde {w['pct']} doğru, {w['n']} soru."
        if best and best["ders"] != w["ders"]:
            s += f" En iyisi {best['ders']}, yüzde {best['pct']}."
        return {"say": s}
    if re.search(r"\b(kart\w*|ezber\w*)\b", t):
        T = v["totals"]
        return {"say": f"Bu hafta {T['cards']} kart tekrar ettiniz" + (f", yüzde {T['cards_pct']} doğru." if T["cards"] else ". Ezber kartları modunda çalıştıkça burada görünecek.")}
    if re.search(r"\b(seri|kaç gündür|üst üste)\b", t):
        s = v["totals"]["streak"]
        return {"say": f"{s} gündür kesintisiz çalışıyorsunuz efendim." if s else "Şu an devam eden bir çalışma seriniz yok efendim, bugün başlayabilirsiniz."}
    if re.search(r"\b(ne kadar|kaç dakika|özet|durum|nasıl gidiyor|çalıştım)\w*", t):
        return {"say": _summary(v)}
    return {"say": "Anlayamadım efendim. Bu hafta, geçen hafta, ne kadar çalıştım, en zayıf dersim ya da raporu gönder diyebilirsiniz."}


def ws(d: dict, st: dict):
    t = str(d.get("type", ""))[8:]
    if t == "week":
        try:
            st["week"] = max(-52, min(0, int(d.get("offset", 0))))
        except (TypeError, ValueError):
            st["week"] = 0
        return {}
    if t == "send":                         # penceredeki onay kutusunda 'Gönder'e basıldı
        return _start_send(st)
    if t == "draft":
        import reports
        title, body = G.report_text(G.view(st.get("week", 0)))
        return {"say": "Taslak rapor modunda kaydedildi, gönderilmedi." if reports.save("", title, body, cat="Haftalık") else "Taslak kaydedilemedi."}
    if t == "preview":
        title, body = G.report_text(G.view(st.get("week", 0)))
        return {"do": {"preview": {"title": title, "body": body}}}
    return {}


def init_payload():
    return G.view(0)
