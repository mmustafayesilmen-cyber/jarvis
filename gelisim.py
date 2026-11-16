"""Haftalık gelişim paneli: yalnızca bu bilgisayarda kayıtlı gerçek verilerden hesaplar, hiçbir değer uydurulmaz.
Kaynaklar: pomodoro.json (günlük odak dakikası ve tur; geçmiş kaydı 2026-10-11'de başladı), kartlar.json (günlük kart tekrarı),
ders.json + ders_cache/ (Quiz/deneme cevapları ve doğru şıklar). Kaydı olmayan gün 0 değil 'veri yok' sayılır."""
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P_POMO, P_KART, P_DERS, D_CACHE = (os.path.join(HERE, x) for x in ("pomodoro.json", "kartlar.json", "ders.json", "ders_cache"))
DAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
today = datetime.date.today      # testlerde değiştirilir


def _read(p) -> dict:
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def pomo_days() -> dict:
    d = _read(P_POMO)
    out = {k: v for k, v in (d.get("history") or {}).items() if isinstance(v, dict)}
    st = d.get("stats") or {}
    if st.get("day"):
        out[st["day"]] = {"done": st.get("done", 0), "work_s": st.get("work_s", 0)}
    return out


def kart_days() -> dict:
    return {k: v for k, v in (_read(P_KART).get("log") or {}).items() if isinstance(v, dict)}


def game_days() -> dict:
    """{gün: {'mind': zihin oyunu sayısı, 'chess': satranç oyunu sayısı}} — oyunlar.json ve satranc.json'dan."""
    out = {}
    for k, v in (_read(os.path.join(HERE, "oyunlar.json")).get("log") or {}).items():
        if isinstance(v, dict):
            out.setdefault(k, {"mind": 0, "chess": 0})["mind"] = int(v.get("plays", 0))
    for k, v in (_read(os.path.join(HERE, "satranc.json")).get("log") or {}).items():
        if isinstance(v, dict):
            out.setdefault(k, {"mind": 0, "chess": 0})["chess"] = int(v.get("games", 0))
    return out


def quiz_topics() -> list:
    """Her çalışılmış konu için quiz/deneme doğru sayıları (yalnızca işaretlenmiş ya da bitmiş sınavlardaki cevaplar sayılır)."""
    out = []
    for key, p in (_read(P_DERS).get("progress") or {}).items():
        if not isinstance(p, dict):
            continue
        cache = _read(os.path.join(D_CACHE, f"{key}.json")) if all(c in "0123456789abcdef" for c in str(key)) else {}
        right = {q.get("id"): q.get("dogru") for kind in ("quiz", "deneme") for q in (cache.get(kind) or []) if isinstance(q, dict)}
        res = {}
        for kind in ("quiz", "deneme"):
            ex = p.get(kind) or {}
            ans = ex.get("answers") or {}
            counted = set(ans) if ex.get("finished") else set(ex.get("checked") or []) & set(ans)
            n = ok = 0
            for qid in counted:
                if qid in right and right[qid]:
                    n += 1
                    ok += 1 if ans.get(qid) == right[qid] else 0
            res[kind] = {"n": n, "ok": ok}
        m = p.get("meta") or {}
        out.append({"key": key, "ders": m.get("dersAd") or m.get("ders") or "?", "unite": m.get("unite", ""), "konu": m.get("konu", ""),
                    "stage": p.get("stage", ""), "t": int(p.get("t") or 0), "quiz": res["quiz"], "deneme": res["deneme"],
                    "n": res["quiz"]["n"] + res["deneme"]["n"], "ok": res["quiz"]["ok"] + res["deneme"]["ok"]})
    out.sort(key=lambda x: x["t"], reverse=True)
    return out


def _pct(ok, n):
    return round(100 * ok / n) if n else None


def _range(offset: int):
    t = today()
    start = t - datetime.timedelta(days=t.weekday()) + datetime.timedelta(weeks=offset)
    return start, start + datetime.timedelta(days=6)


def label(start, end) -> str:
    if start.month == end.month:
        return f"{start.day}-{end.day} {MONTHS[end.month - 1]} {end.year}"
    return f"{start.day} {MONTHS[start.month - 1]} - {end.day} {MONTHS[end.month - 1]} {end.year}"


def view(offset: int = 0) -> dict:
    offset = max(-52, min(0, int(offset)))
    start, end = _range(offset)
    pd, kd, gd = pomo_days(), kart_days(), game_days()
    first = min(list(pd) + list(kd) or [today().isoformat()])
    days = []
    for i in range(7):
        dt = start + datetime.timedelta(days=i)
        k = dt.isoformat()
        p, c = pd.get(k), kd.get(k)
        days.append({"date": k, "label": DAYS[i], "day": dt.day, "future": dt > today(), "today": dt == today(),
                     "nodata": k < first, "focus": round((p or {}).get("work_s", 0) / 60), "rounds": (p or {}).get("done", 0),
                     "cards": (c or {}).get("rev", 0), "cards_ok": (c or {}).get("ok", 0),
                     "mind": (gd.get(k) or {}).get("mind", 0), "chess": (gd.get(k) or {}).get("chess", 0)})
    focus = sum(d["focus"] for d in days)
    rounds = sum(d["rounds"] for d in days)
    cards = sum(d["cards"] for d in days)
    cards_ok = sum(d["cards_ok"] for d in days)
    active = sum(1 for d in days if d["focus"] or d["cards"])
    ps, pe = _range(offset - 1)
    prev_focus = round(sum(v.get("work_s", 0) for k, v in pd.items() if ps.isoformat() <= k <= pe.isoformat()) / 60)
    # seri: bugünden geriye kesintisiz çalışılan gün
    streak, dt = 0, today()
    if not ((pd.get(dt.isoformat()) or {}).get("work_s") or (kd.get(dt.isoformat()) or {}).get("rev")):
        dt -= datetime.timedelta(days=1)                 # bugün henüz çalışılmadıysa seri dünden sayılır
    while (pd.get(dt.isoformat()) or {}).get("work_s") or (kd.get(dt.isoformat()) or {}).get("rev"):
        streak += 1
        dt -= datetime.timedelta(days=1)
    # quiz
    topics = quiz_topics()
    s_ts = int(datetime.datetime.combine(start, datetime.time()).timestamp())
    e_ts = int(datetime.datetime.combine(end + datetime.timedelta(days=1), datetime.time()).timestamp())
    week_topics = [x for x in topics if s_ts <= x["t"] < e_ts]
    by = {}
    for x in topics:
        b = by.setdefault(x["ders"], {"ders": x["ders"], "n": 0, "ok": 0, "konu": 0})
        b["n"] += x["n"]
        b["ok"] += x["ok"]
        b["konu"] += 1
    by_ders = sorted(({**b, "pct": _pct(b["ok"], b["n"])} for b in by.values()), key=lambda b: (b["pct"] is None, b["pct"] if b["pct"] is not None else 0))
    qn, qok = sum(x["n"] for x in topics), sum(x["ok"] for x in topics)
    wn, wok = sum(x["n"] for x in week_topics), sum(x["ok"] for x in week_topics)
    rated = [b for b in by_ders if b["pct"] is not None and b["n"] >= 3]
    weakest = rated[0] if len(rated) >= 2 and rated[0]["pct"] < rated[-1]["pct"] else None     # karşılaştırma için en az iki ders gerekir
    return {"offset": offset, "label": label(start, end), "days": days, "first": first,
            "totals": {"focus": focus, "rounds": rounds, "cards": cards, "cards_pct": _pct(cards_ok, cards), "active": active, "streak": streak,
                       "mind": sum(d["mind"] for d in days), "chess": sum(d["chess"] for d in days),
                       "prev_focus": prev_focus, "best": max(days, key=lambda d: d["focus"])["label"] if focus else None},
            "quiz": {"pct": _pct(qok, qn), "n": qn, "week_pct": _pct(wok, wn), "week_n": wn, "by_ders": by_ders,
                     "topics": [{**x, "pct": _pct(x["ok"], x["n"])} for x in (week_topics or topics)[:12]], "week_only": bool(week_topics)},
            "weakest": weakest}


def report_text(v: dict):
    """(başlık, gövde) — rapor modu biçimine uygun düz metin."""
    T, Q = v["totals"], v["quiz"]
    lines = [f"Odaklanma: {T['focus']} dakika ({T['rounds']} pomodoro turu), {T['active']} gün çalışıldı."]
    if T["prev_focus"]:
        diff = T["focus"] - T["prev_focus"]
        lines.append(f"Geçen haftaya göre: {'+' if diff >= 0 else ''}{diff} dakika.")
    if T["streak"] and v["offset"] == 0:
        lines.append(f"Kesintisiz çalışma serisi: {T['streak']} gün.")
    if T["cards"]:
        lines.append(f"Ezber kartları: {T['cards']} tekrar, doğru oranı %{T['cards_pct']}.")
    if T["mind"] or T["chess"]:
        lines.append("Oyunlar: " + ", ".join(x for x in (f"{T['mind']} zihin oyunu" if T["mind"] else "", f"{T['chess']} satranç oyunu" if T["chess"] else "") if x) + ".")
    if Q["week_n"]:
        lines.append(f"Bu hafta çözülen sorular: {Q['week_n']} soru, doğru oranı %{Q['week_pct']}.")
    elif Q["n"]:
        lines.append(f"Quiz genel doğru oranı: %{Q['pct']} ({Q['n']} soru).")
    if Q["topics"] and Q["week_only"]:
        lines.append("Çalışılan konular: " + "; ".join(f"{x['ders']} - {x['konu']}" for x in Q["topics"][:6]) + ".")
    if v["weakest"] and v["weakest"]["pct"] < 85:
        lines.append(f"Daha çok çalışılması gereken ders: {v['weakest']['ders']} (%{v['weakest']['pct']}).")
    lines.append("(Jarvis tarafından bu bilgisayardaki kayıtlardan hazırlandı.)")
    return f"Haftalık çalışma raporu ({v['label']})", "\n".join(lines)
