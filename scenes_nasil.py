"""'Nasıl Çalışır?' modu komutları: 'buzdolabı nasıl çalışır', 'başla', 'sonraki', 'önceki', 'tekrar', 'adım üç', 'benzetme', 'ilginç bilgi', 'soru sor', 'konular'.
Listede olmayan konu sorulunca nasil.generate yerel modelle anlatım hazırlar (sonuç NOTIFY ile gelir). Sayfa '@seç id' / '@adım n' gizli komutlarını yollar."""
import re

import nasil as N
import scenes

HELP = ("Bir şey sorun, örneğin buzdolabı nasıl çalışır ya da uçak nasıl uçar. Sonra başla, sonraki, önceki, tekrar, benzetme, ilginç bilgi ve soru sor diyebilirsiniz. "
        "Listede olmayan bir konuyu sorarsanız yapay zekâyla hazırlarım.")
_TRIM = r"\b(nasıl|çalışır|çalışıyor|çalışır mı|işler|işliyor|oluşur|olur|uçar|anlat\w*|açıkla\w*|nedir|ne demek|bana|hakkında|konusu\w*|göster|aç|mantığı\w*|yapar)\b"
_ORD = {"a": 0, "b": 1, "c": 2, "bir": 0, "birinci": 0, "ilk": 0, "iki": 1, "ikinci": 1, "üç": 2, "üçüncü": 2, "son": 2, "sonuncu": 2}


def _out(say: str, extra=None):
    do = {"snap": N.snapshot()}
    if extra:
        do.update(extra)
    return {"do": do, "say": say}


def _step_say(t, i):
    b, m = t["adim"][i]
    tail = " Bitti efendim. İsterseniz soru sor deyin." if i == len(t["adim"]) - 1 else ""
    return f"Adım {i + 1}, {b}. {m}{tail}"


def _ask(t):
    qs = t.get("soru") or []
    if not qs:
        return {"say": "Bu konu için hazır soru yok efendim."}
    N.S["q"] = (N.S["q"] + 1) % len(qs)
    q = qs[N.S["q"]]
    return _out(f"{q['q']} " + " ".join(f"{'ABC'[i]}: {s}." for i, s in enumerate(q["s"])))


def _answer(t, t_norm: str):
    q = (t.get("soru") or [])[N.S["q"]]
    pick = None
    w = t_norm.split()
    for x in w:
        if x in _ORD:
            pick = _ORD[x]
            break
    if pick is None:
        for i, s in enumerate(q["s"]):
            if scenes.norm(s) and scenes.norm(s) in t_norm:
                pick = i
    if pick is None:
        return None
    N.S["score"][1] += 1
    ok = pick == q["c"]
    N.S["score"][0] += ok
    res = _out(("Doğru efendim! " if ok else f"Maalesef, doğru cevap {'ABC'[q['c']]}: {q['s'][q['c']]}. ") + ("Sıradaki için soru sor deyin." if len(t["soru"]) > 1 else ""),
               {"answer": {"pick": pick, "ok": ok}})
    return res


def nasil_mode(text: str, st: dict):
    raw = text.strip()
    if raw.startswith("@"):
        p = raw[1:].split()
        if len(p) == 2 and p[0] == "seç" and N.get(p[1]):
            t = N.get(p[1])
            N.select(t)
            return _out(f"{t['ad']}. {t['ozet']} Başla derseniz adım adım anlatırım.")
        if len(p) == 2 and p[0] == "adım" and N.S["id"] and p[1].isdigit():
            t = N.get(N.S["id"])
            i = max(0, min(int(p[1]), len(t["adim"]) - 1))
            N.S["step"] = i
            return _out(_step_say(t, i))
        if len(p) == 2 and p[0] == "cevap" and N.S["id"] and N.S["q"] >= 0 and p[1] in ("0", "1", "2"):
            return _answer(N.get(N.S["id"]), "abc"[int(p[1])]) or _out("")
        return _out("")
    t = scenes.norm(text)
    if not t:
        return None
    cur = N.get(N.S["id"]) if N.S["id"] else None
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": HELP}
    if cur and N.S["q"] >= 0 and len(t.split()) <= 4:
        r = _answer(cur, t)
        if r:
            return r
    if re.search(r"\b(konular\w*|liste\w*|neler var|hangi konular)\b", t):
        return _out("Yerleşik konular: " + ", ".join(x["ad"] for x in N.TOPICS) + ". Başka bir şey de sorabilirsiniz.")
    if cur:
        if re.fullmatch(r"(başla|başlat|anlat|anlatmaya başla|baştan|baştan anlat|baştan başla)", t):
            N.S["step"] = 0
            return _out(_step_say(cur, 0))
        if re.fullmatch(r"(sonraki|devam|devam et|ileri|sıradaki|geç|sonraki adım)", t):
            i = N.S["step"] + 1
            if i >= len(cur["adim"]):
                return {"say": "Son adımdaydık efendim. Soru sor ya da baştan diyebilirsiniz."}
            N.S["step"] = i
            return _out(_step_say(cur, i))
        if re.fullmatch(r"(önceki|geri|geri dön|önceki adım)", t):
            i = max(0, N.S["step"] - 1)
            N.S["step"] = i
            return _out(_step_say(cur, i))
        if re.fullmatch(r"(tekrar|tekrarla|tekrar et|bir daha)", t):
            return _out(_step_say(cur, max(0, N.S["step"])))
        m = re.search(r"\badım\s+(\w+)", t)
        if m and (scenes.num_in(m.group(1)) or 0) >= 1:
            i = min(scenes.num_in(m.group(1)), len(cur["adim"])) - 1
            N.S["step"] = i
            return _out(_step_say(cur, i))
        if re.search(r"\b(benzetme\w*|basit\w*|kolay anlat|örnek ver)\b", t):
            return _out(cur["benzetme"], {"show": "benzetme"})
        if re.search(r"\b(ilginç|bilgi|biliyor muydun|şaşırt)\w*", t):
            return _out(cur.get("bilgi") or "Bu konu için ek bilgi yok efendim.", {"show": "bilgi"})
        if re.search(r"\b(soru|test|sına|quiz)\w*", t):
            return _ask(cur)
        if re.search(r"\b(özet\w*|kısaca)\b", t):
            return _out(cur["ozet"])
        if cur.get("ai") and re.search(r"\b(bu konuyu|konuyu)\s+(sil|unut|kaldır)\w*", t):
            N.forget(cur["id"])
            return _out("Bu konuyu sildim efendim.")
    hit = N.find(t)
    if hit:
        N.select(hit)
        return _out(f"{hit['ad']}. {hit['ozet']} Başla derseniz adım adım anlatırım.")
    konu = " ".join(re.sub(_TRIM, " ", t).split())
    if len(konu) < 3 or not re.search(r"\b(nasıl|anlat|açıkla|nedir)", t):
        return {"say": "Anlayamadım efendim. Örneğin buzdolabı nasıl çalışır, başla, sonraki ya da soru sor diyebilirsiniz."}
    if not N.generate(konu):
        return {"say": f"Şu an {N.S['busy']} konusunu hazırlıyorum efendim, biraz bekleyin."}
    return _out(f"{konu} listemde yok, yapay zekâyla hazırlıyorum efendim. Birkaç saniye sürebilir.")
