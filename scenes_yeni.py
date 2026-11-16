"""Sekiz yeni mod: Sınav simülatörü (optik), Beyin fırtınası tahtası, Dijital masa, Hızlı okuma, Kelime kutusu, Bütçe, Karar çarkı, Hızlı başlatıcı.
Hepsi yereldir (internet gerekmez; yalnızca tahta kategorileri ve okuma metni üretimi yerel Ollama'yı kullanır). Veriler repo kökünde düz JSON dosyalarındadır
(optik_deneme, board_notes, desk_state, reading_stats, vocabulary, pocket_budget, decision_wheels, system_presets; hepsi gitignored).
Her işlev (text, state) -> {"say", "do"} döner; sayfalar ui/scene_<kind>.html. Çıkış yalnızca açık ifadelerle (scenes.handle)."""
import datetime
import json
import os
import random
import re
import threading
import time

import scenes
from scenes import norm, num_in

HERE = os.path.dirname(os.path.abspath(__file__))
_lk = threading.Lock()


def _load(name, default):
    try:
        with open(os.path.join(HERE, name), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, type(default)) else default
    except (OSError, ValueError):
        return default


def _save(name, data):
    p = os.path.join(HERE, name)
    with _lk:
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(p + ".tmp", p)


def _ask_llm(prompt: str, system: str = "") -> str:
    """Yerel model (brain.MODEL, brain.CTX: model yeniden yüklenmesin) ile tek seferlik cevap; hata olursa ''."""
    try:
        import ollama
        import brain
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        return ollama.chat(model=brain.MODEL, messages=msgs, keep_alive="5m", **brain._extra(),
                           options={"temperature": 0.3, "num_ctx": brain.CTX}).message.content.strip()
    except Exception as e:
        print("yeni mod model hatası:", type(e).__name__, flush=True)
        return ""


def _raw_after_colon(raw: str) -> str:
    return raw.split(":", 1)[1].strip() if ":" in raw else ""


def _words(t, *keys):
    return any(re.search(k, t) for k in keys)


# ================================================================== 1) SINAV SİMÜLATÖRÜ (optik form)
OP_FILE = "optik_deneme.json"
# ad: (soru sayısı, dakika) — süre, gerçek sınavın soru başına süresine göre ayarlanmıştır (TYT 120 soru/165 dk, AYT 160 soru/180 dk, YDT 80 soru/120 dk)
OP_PRE = {"tyt türkçe": (40, 55), "tyt sosyal": (20, 27), "tyt matematik": (40, 55), "tyt fen": (20, 27), "tyt": (120, 165),
          "ayt matematik": (40, 45), "ayt fen": (40, 45), "ayt edebiyat": (40, 45), "ayt sosyal": (40, 45), "ayt": (160, 180), "ydt": (80, 120)}
O = {"on": False, "fin": False, "name": "", "n": 0, "dur": 0, "end": 0.0, "ans": {}, "flag": [], "key": "", "res": None}
_LET = {"a": "A", "b": "B", "be": "B", "c": "C", "ce": "C", "d": "D", "de": "D", "e": "E"}


def _opt_snap():
    left = max(0.0, O["end"] - time.time()) if O["on"] else 0.0
    h = _load(OP_FILE, {"history": []}).get("history", [])[-6:]
    return {"on": O["on"], "fin": O["fin"], "name": O["name"], "n": O["n"], "dur": O["dur"], "ans": O["ans"], "flag": O["flag"], "key": O["key"],
            "res": O["res"], "left": round(left, 1), "history": h, "presets": [{"k": k, "n": v[0], "d": v[1]} for k, v in OP_PRE.items()]}


def _opt_score():
    ans, key, n = O["ans"], O["key"], O["n"]
    d = y = 0
    marks = {}
    for q in range(1, n + 1):
        a = ans.get(q)
        if not a:
            marks[q] = "b"
        elif key and q <= len(key):
            ok = key[q - 1] == a
            d += ok
            y += (not ok)
            marks[q] = "d" if ok else "y"
        else:
            marks[q] = "?"
    blank = sum(1 for v in marks.values() if v == "b")
    if key:
        O["res"] = {"keyed": True, "d": d, "y": y, "b": blank + sum(1 for v in marks.values() if v == "?"), "net": round(d - y / 4, 2), "marks": marks}
    else:
        O["res"] = {"keyed": False, "marked": len(ans), "b": n - len(ans), "marks": marks}
    return O["res"]


def _opt_finish():
    O.update(on=False, fin=True)
    r = _opt_score()
    data = _load(OP_FILE, {"history": []})
    data.setdefault("history", []).append({"ts": datetime.datetime.now().strftime("%d.%m %H:%M"), "ad": O["name"], "n": O["n"],
                                           "d": r.get("d"), "y": r.get("y"), "b": r["b"], "net": r.get("net"), "ans": "".join(O["ans"].get(i, "-") for i in range(1, O["n"] + 1))})
    data["history"] = data["history"][-60:]
    _save(OP_FILE, data)


def _opt_set_key(rest: str):
    letters = []
    for tok in rest.split():
        if tok in _LET:
            letters.append(_LET[tok])
        elif re.fullmatch(r"[a-e]{2,}", tok):
            letters += list(tok.upper())
    return "".join(letters)


def optik(text, st):
    t = norm(text)
    if O["on"] and time.time() > O["end"] + 1:
        _opt_finish()

    def res(say):
        return {"do": {"snap": _opt_snap()}, "say": say}
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "TYT Türkçe denemesi başlat de. İşaretlemek için on beş C ya da on beş C şıkkı deyin; on beşi boş bırak, on beşi işaretle diyerek turlayın. "
                       "Kalan süreyi söyle, cevap anahtarı A B C D diyerek net hesaplatın, sınavı teslim et diyerek bitirin."}
    m = re.search(r"(\d{1,3})\s*soruluk.*?(\d{1,3})\s*(?:dakika|dk)", t) or re.search(r"(\d{1,3})\s*soru\w*.*?(\d{1,3})\s*(?:dakika|dk)", t)
    pre = max((k for k in OP_PRE if k in t), key=len, default=None)
    if re.search(r"\b(başlat|başla|başlayalım|çözelim|çözeceğim)\w*", t) and (pre or m or re.search(r"\b(deneme|sınav)\w*", t)):
        if m:
            n, dur, name = max(1, min(200, int(m.group(1)))), max(1, min(300, int(m.group(2)))), f"{m.group(1)} soruluk deneme"
        elif pre:
            (n, dur), name = OP_PRE[pre], pre.upper()
        else:
            return {"say": "Hangi deneme efendim? Örneğin TYT Türkçe, AYT matematik ya da kırk soruluk elli dakikalık deneme."}
        O.update(on=True, fin=False, name=name, n=n, dur=dur, end=time.time() + dur * 60, ans={}, flag=[], key="", res=None)
        return res(f"{name} denemesi başladı efendim. {n} soru, {dur} dakika. Başarılar.")
    if re.search(r"\b(kalan|ne kadar (kaldı|var)|kaç dakika)\b", t):
        if not O["on"]:
            return {"say": "Çalışan bir deneme yok efendim."}
        left = int(max(0, O["end"] - time.time()) // 60)
        return {"say": f"{left} dakika kaldı efendim." if left else "Son dakikadasınız efendim."}
    if re.search(r"\bcevap anahtar\w*", t):
        letters = _opt_set_key(re.split(r"\bcevap anahtar\w*", t, 1)[1])
        if not O["n"]:
            return {"say": "Önce bir deneme başlatmanız gerekiyor efendim."}
        if not letters:
            return {"say": "Cevap anahtarını harflerle söyleyin ya da yazın, örneğin cevap anahtarı A B C D A."}
        O["key"] = letters
        if O["fin"]:
            _opt_score()
            r = O["res"]
            d = _load(OP_FILE, {"history": []})
            if d.get("history"):
                d["history"][-1].update(d=r["d"], y=r["y"], b=r["b"], net=r["net"])
                _save(OP_FILE, d)
            return res(f"{r['d']} doğru, {r['y']} yanlış, {r['b']} boş. Netiniz {r['net']} efendim.")
        return res(f"Cevap anahtarı kaydedildi, {len(letters)} soru. Teslimde neti hesaplarım." + ("" if len(letters) == O["n"] else f" Dikkat: denemede {O['n']} soru var."))
    if re.search(r"\b(teslim|sınavı bitir|denemeyi bitir|sınavı sonlandır|denemeyi sonlandır)\w*", t):
        if not O["on"]:
            return {"say": "Çalışan bir deneme yok efendim."}
        _opt_finish()
        r = O["res"]
        if r["keyed"]:
            return res(f"{r['d']} doğru, {r['y']} yanlış, {r['b']} boş. Netiniz {r['net']} efendim.")
        return res(f"Deneme teslim edildi. {r['marked']} soru işaretlediniz, {r['b']} boş. Net için cevap anahtarı söyleyin.")
    if re.search(r"\b(geçmiş|önceki|eski) (deneme|sonuç)\w*|\bdeneme geçmiş\w*", t):
        h = _load(OP_FILE, {"history": []}).get("history", [])[-3:]
        nets = [x for x in h if x.get("net") is not None]
        return {"say": ("Son denemeleriniz: " + "; ".join(f"{x['ad']} net {x['net']}" for x in nets) + ".") if nets else "Netli kayıtlı denemeniz yok efendim."}
    if re.search(r"\biptal\b", t) and O["on"]:
        O.update(on=False, fin=False, ans={}, flag=[], res=None)
        return res("Deneme iptal edildi efendim.")
    mf = re.search(r"(\d{1,3})\s*(?:numaralı|\.)?\s*(?:soru\w*)?\s*(işaretle|turla|bayrak\w*)", t)
    if mf and O["n"]:
        q = int(mf.group(1))
        if 1 <= q <= O["n"]:
            O["flag"] = [x for x in O["flag"] if x != q] if q in O["flag"] else O["flag"] + [q]
            return res(f"{q}. soru {'turlamak için işaretlendi' if q in O['flag'] else 'işareti kaldırıldı'}.")
    mb = re.search(r"(\d{1,3})\s*(?:numaralı|\.)?\s*(?:soru\w*)?\s*(boş|sil\w*|temizle\w*|kaldır\w*|iptal)", t)
    if mb and O["n"] and not O["fin"]:
        q = int(mb.group(1))
        O["ans"].pop(q, None)
        return res(f"{q}. soru boş bırakıldı.")
    hits = re.findall(r"(\d{1,3})\s*(?:numaralı|\.)?\s*(?:soru\w*)?\s*(?:cevab\w*|şık\w*)?\s*\b(a|b|be|c|ce|d|de|e)\b", t)
    if hits:
        if not O["on"]:
            return {"say": "Önce bir deneme başlatmanız gerekiyor efendim. Örneğin TYT Türkçe denemesi başlat."}
        done = []
        for q, l in hits:
            q = int(q)
            if 1 <= q <= O["n"]:
                O["ans"][q] = _LET[l]
                done.append(f"{q} {_LET[l]}")
        return res(", ".join(done) + " işaretlendi." if done else f"Soru numarası 1 ile {O['n']} arasında olmalı efendim.")
    return {"say": "Anlayamadım efendim. On beş C gibi cevap söyleyin ya da yardım deyin."}


# ================================================================== 2) BEYİN FIRTINASI TAHTASI
TH_FILE = "board_notes.json"
TH_COL = {"sarı": "sari", "pembe": "pembe", "mavi": "mavi", "yeşil": "yesil", "turuncu": "turuncu", "mor": "mor"}


def _th():
    d = _load(TH_FILE, {})
    d.setdefault("notes", [])
    d.setdefault("links", [])
    d.setdefault("next", 1)
    return d


def _th_snap(d):
    return {"notes": d["notes"], "links": d["links"]}


def _th_place(i):
    return round(0.07 + (i % 5) * 0.18 + random.uniform(-.015, .015), 3), round(0.10 + ((i // 5) % 5) * 0.17 + random.uniform(-.015, .015), 3)


def _th_group(d):
    """Notları yerel modelle kategorilere ayırır; model cevap vermezse renge göre gruplar. Sütunlara dizer."""
    notes = d["notes"]
    groups = {}
    out = _ask_llm("Aşağıdaki numaralı notları anlamca 2-5 kısa kategoriye ayır. Her not tam bir kategoriye girsin. Yalnızca şu JSON'u döndür: "
                   '{"kategoriler": {"Kategori adı": [1, 2]}}\n' + "\n".join(f"{n['id']}: {n['text']}" for n in notes),
                   "Yalnızca geçerli JSON döndürürsün. Kategori adları Türkçe ve en fazla 3 sözcük olsun.")
    try:
        m = re.search(r"\{.*\}", out, re.S)
        cats = json.loads(m.group(0))["kategoriler"] if m else {}
        for name, ids in cats.items():
            for i in ids:
                groups[int(i)] = str(name)[:30]
    except (ValueError, KeyError, TypeError, AttributeError):
        groups = {}
    if len(groups) < len(notes) / 2:                       # model işe yaramadı: renge göre
        names = {"sari": "Sarı", "pembe": "Pembe", "mavi": "Mavi", "yesil": "Yeşil", "turuncu": "Turuncu", "mor": "Mor"}
        groups = {n["id"]: names.get(n["c"], "Diğer") for n in notes}
    order = []
    for n in notes:
        n["g"] = groups.get(n["id"], "Diğer")
        if n["g"] not in order:
            order.append(n["g"])
    rows = {g: 0 for g in order}
    for n in notes:
        gi = order.index(n["g"])
        n["x"] = round(0.05 + (gi + 0) * (0.90 / max(1, len(order))), 3)
        n["y"] = round(0.16 + rows[n["g"]] * 0.15, 3)
        rows[n["g"]] += 1
    return order


def tahta(text, st):
    t = norm(text)
    raw = text.strip()
    if raw.startswith("§tasi|"):
        try:
            _, i, x, y = raw.split("|")
            d = _th()
            for n in d["notes"]:
                if n["id"] == int(i):
                    n["x"], n["y"] = round(max(0, min(.95, float(x))), 3), round(max(0, min(.9, float(y))), 3)
            _save(TH_FILE, d)
        except ValueError:
            pass
        return {"say": ""}
    d = _th()

    def res(say, d=d):
        _save(TH_FILE, d)
        return {"do": {"snap": _th_snap(d)}, "say": say}
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Tahtaya ekle iki nokta ve fikrinizi söyleyin; sarı nota yaz diyerek renk seçin. Bir ile üçü bağla, fikirleri kategorilere ayır, "
                       "üç numaralı notu sil, tahtayı temizle diyebilirsiniz. Notları fareyle sürükleyebilirsiniz."}
    if re.search(r"\bbağlantı\w*.*\b(sil|kaldır|temizle)\w*", t):
        d["links"] = []
        return res("Bağlantıları kaldırdım efendim.")
    if re.search(r"\b(tahta\w*|pano\w*|hepsini|tümünü|her şeyi)\b.*\b(temizle|sil|boşalt)\w*|\b(temizle|boşalt)\b", t) and not re.search(r"\b(ekle|yaz)\b", t):
        d.update(notes=[], links=[], next=1)
        return res("Tahtayı temizledim efendim.")
    if re.search(r"\b(kategori\w*|grupla\w*|grupland\w*|ayır\w*|topla\w*)\b", t) and not re.search(r"\b(ekle|yaz)\b", t):
        if len(d["notes"]) < 2:
            return {"say": "Gruplamak için en az iki not gerekiyor efendim."}
        order = _th_group(d)
        return res(f"{len(d['notes'])} fikri {len(order)} kategoriye ayırdım: " + ", ".join(order) + ".")
    if re.search(r"\b(dağıt|gruplamayı kaldır|kategorileri kaldır)\w*", t):
        for i, n in enumerate(d["notes"]):
            n["g"] = ""
            n["x"], n["y"] = _th_place(i)
        return res("Notları tahtaya dağıttım efendim.")
    ids = [int(x) for x in re.findall(r"\d+", t)]
    if re.search(r"\b(bağla|birleştir)\w*", t) and len(ids) >= 2:
        have = {n["id"] for n in d["notes"]}
        a, b = ids[0], ids[1]
        if a in have and b in have and a != b:
            if [a, b] not in d["links"] and [b, a] not in d["links"]:
                d["links"].append([a, b])
            return res(f"{a} ile {b} bağlandı efendim.")
        return {"say": "Bu numaralı notları bulamadım efendim."}
    if re.search(r"\b(sil|kaldır|çıkar)\w*", t) and not re.search(r"\b(ekle|yaz)\w*", t):
        if re.search(r"\bson\b", t) and d["notes"]:
            ids = [d["notes"][-1]["id"]]
        if not ids:
            return {"say": "Hangi notu silmemi istersiniz efendim? Numarasını söyleyin."}
        n0 = len(d["notes"])
        d["notes"] = [n for n in d["notes"] if n["id"] not in ids]
        d["links"] = [l for l in d["links"] if l[0] not in ids and l[1] not in ids]
        return res("Notu sildim efendim." if len(d["notes"]) < n0 else "Bu numaralı not yok efendim.")
    m = re.search(r"(\d+)\s*(?:numaralı|\.)?\s*not\w*\s*(?:değiştir|düzenle|güncelle)\w*", t)
    if m and ":" in raw:
        for n in d["notes"]:
            if n["id"] == int(m.group(1)):
                n["text"] = _raw_after_colon(raw)[:300]
                return res("Notu güncelledim efendim.")
    if re.search(r"\b(ekle|yaz|not al|fikir)\w*", t):
        body = _raw_after_colon(raw)
        if not body:
            mm = re.search(r"\b(?:ekle|yaz|ekler misin)\w*\s+(.+)$", raw, re.I)
            body = mm.group(1).strip() if mm else ""
        if not body:
            return {"say": "Ne yazayım efendim? Örneğin tahtaya ekle iki nokta ve fikrinizi söyleyin."}
        col = next((v for k, v in TH_COL.items() if re.search(rf"\b{k}\w*", t.split("ekle")[0] + " " + t.split("yaz")[0])), random.choice(list(TH_COL.values())))
        i = d["next"]
        d["next"] += 1
        x, y = _th_place(len(d["notes"]))
        d["notes"].append({"id": i, "text": body[:300], "c": col, "x": x, "y": y, "g": ""})
        return res(f"{i} numaralı not tahtaya eklendi efendim.")
    return {"say": "Anlayamadım efendim. Tahtaya ekle iki nokta ve fikrinizi söyleyin ya da yardım deyin."}


# ================================================================== 3) DİJİTAL MASA
MA_FILE = "desk_state.json"
MA_DEF = {"lamp": True, "night": True, "rain": 0, "cafe": 0, "wind": 0, "window": False, "book": True, "plant": 0, "coffee": 5}


def _ma():
    d = {**MA_DEF, **_load(MA_FILE, {})}
    return d


def masa(text, st):
    t = norm(text)
    d = _ma()

    def res(say):
        _save(MA_FILE, d)
        return {"do": {"snap": d}, "say": say}
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Masadaki lambayı yak ya da söndür, yağmur sesini seviye üç yap, kafe sesi, rüzgar sesi, gece yap, gündüz yap, pencereyi aç, kitabı kapat, "
                       "çiçeği sula ve kahve fincanına dokun diyebilirsiniz. Objelere tıklayarak da kullanabilirsiniz."}
    if re.search(r"\b(sıfırla|baştan|varsayılan)\b", t):
        d.update(MA_DEF)
        return res("Masayı ilk haline getirdim efendim.")
    if re.search(r"\blamba\w*|\bişık\b|\babajur\w*", t):
        if re.search(r"\b(yak|aç|açık)\w*", t):
            d["lamp"] = True
        elif re.search(r"\b(söndür|kapat|kapa|kapalı)\w*", t):
            d["lamp"] = False
        else:
            d["lamp"] = not d["lamp"]
        return res("Lamba yandı efendim." if d["lamp"] else "Lamba söndü efendim.")
    for key, pat, name in (("rain", r"yağmur\w*", "Yağmur"), ("cafe", r"kafe\w*|cafe|kahvehane", "Kafe"), ("wind", r"rüzgar\w*|rüzgâr\w*", "Rüzgar")):
        if re.search(pat, t) and re.search(r"\bses\w*|\bseviye\w*|\bkapat|\bkıs|\bartır|\bsöndür|\baç\b|\byap\b|\bkapa\b", t):
            n = num_in(t)
            if re.search(r"\b(kapat|kapa|söndür|sustur|kapalı|sıfır)\w*", t) and n is None:
                d[key] = 0
            elif n is not None:
                d[key] = max(0, min(5, n))
            elif re.search(r"\b(artır|yükselt|aç|daha)\w*", t):
                d[key] = min(5, d[key] + 1) if d[key] else 3
            elif re.search(r"\b(kıs|azalt|düşür)\w*", t):
                d[key] = max(0, d[key] - 1)
            else:
                d[key] = 3
            return res(f"{name} sesi {'kapandı' if not d[key] else 'seviye ' + str(d[key])} efendim.")
    if re.search(r"\bgece\b", t):
        d["night"] = True
        return res("Gece oldu efendim.")
    if re.search(r"\bgündüz\b|\bsabah\b|\bgün ışığ\w*", t):
        d["night"] = False
        return res("Gündüz oldu efendim.")
    if re.search(r"\bpencere\w*", t):
        d["window"] = not re.search(r"\b(kapat|kapa)\w*", t)
        return res("Pencere açıldı, hava giriyor efendim." if d["window"] else "Pencere kapandı efendim.")
    if re.search(r"\bkitab\w*|\bdefter\w*", t):
        d["book"] = not re.search(r"\b(kapat|kapa)\w*", t)
        return res("Kitap açıldı efendim, iyi okumalar." if d["book"] else "Kitabı kapattım efendim.")
    if re.search(r"\b(çiçek\w*|bitki\w*|saksı\w*)", t):
        d["plant"] = min(9, d["plant"] + 1)
        return res("Çiçeği suladım efendim, çok mutlu." if d["plant"] < 9 else "Çiçek zaten fazla sulandı efendim, boğmayalım.")
    if re.search(r"\bkahve\w*|\bfincan\w*|\bçay\w*", t):
        d["coffee"] = 5
        return res(random.choice(["Kahveniz tazelendi efendim, buharı tüteri.", "Fincanı doldurdum, afiyet olsun efendim.", "Sıcak kahve hazır efendim."]))
    return {"say": "Anlayamadım efendim. Lambayı yak, yağmur sesini seviye üç yap ya da kahve fincanına dokun diyebilirsiniz."}


# ================================================================== 4) HIZLI OKUMA ANTRENÖRÜ
OK_FILE = "reading_stats.json"
OK_TR = [
    "Dünya'nın en derin noktası olan Mariana Çukuru, yaklaşık on bir kilometre derinliğindedir. Buraya ışık hiç ulaşmaz ve basınç deniz seviyesindekinin bin katından fazladır. "
    "Buna rağmen çukurun dibinde yaşayan küçük canlılar bulunmuştur. Bilim insanları bu canlıların aşırı koşullara nasıl uyum sağladığını inceleyerek hem yaşamın sınırlarını hem de yeni ilaçların kaynaklarını araştırmaktadır.",
    "Uyku, yalnızca dinlenmek değildir. Gece boyunca beyin gün içinde öğrenilen bilgileri düzenler, önemli olanları uzun süreli belleğe aktarır ve gereksiz ayrıntıları temizler. "
    "Yeterince uyumayan öğrencilerin sınavda daha çok yanlış yaptığı ve dikkatini daha zor topladığı birçok araştırmada gösterilmiştir. Bu nedenle sınavdan önceki gece çalışmak yerine uyumak çoğu zaman daha doğru bir tercihtir.",
    "Anadolu'daki Göbeklitepe, tarihin bilinen en eski tapınak alanıdır ve yaklaşık on iki bin yıl öncesine uzanır. Dikilitaşlardaki hayvan kabartmaları, insanların tarım yapmadan önce bile büyük topluluk yapıları kurabildiğini göstermiştir. "
    "Bu keşif, medeniyetin tarımla başladığı düşüncesini sorgulatmış ve tarih kitaplarının yeniden yazılmasına neden olmuştur.",
    "Dil öğrenmenin en etkili yollarından biri aralıklı tekrardır. Bir kelimeyi bir kez ezberlemek yerine artan aralıklarla yeniden görmek, bilginin uzun süreli belleğe yerleşmesini sağlar. "
    "Her tekrarda hatırlamak biraz zorlaşmalı, çünkü zorlanarak hatırlanan bilgi daha kalıcı olur. Günde yirmi dakikalık düzenli çalışma, haftada bir saatlik yoğun çalışmadan genellikle daha verimlidir.",
]
OK_EN = [
    "Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are more than three thousand years old and still perfectly edible. "
    "Honey contains very little water and is naturally acidic, so bacteria cannot grow in it. Bees also add an enzyme that produces a small amount of hydrogen peroxide, which protects it even further.",
    "The human brain uses about twenty percent of the body's energy, even though it makes up only two percent of its weight. Scientists believe this is because billions of neurons constantly send tiny electrical signals to each other. "
    "Even when we are resting, large parts of the brain stay active, which is why a short walk or a good night's sleep can improve concentration so much.",
    "Cities around the world are trying to become greener. Many of them are planting trees on rooftops, building more bicycle lanes, and replacing diesel buses with electric ones. "
    "Experts say that these changes not only reduce pollution but also make people healthier and happier, because they spend more time outdoors and breathe cleaner air.",
]
R = {"wpm": 250, "cur": None, "lang": "tr", "words": 0}


def _ok_stats():
    d = _load(OK_FILE, {})
    d.setdefault("hist", [])
    if d.get("wpm"):
        R["wpm"] = int(d["wpm"])
    return d


def _ok_snap():
    d = _ok_stats()
    return {"wpm": R["wpm"], "hist": d["hist"][-12:], "cur": R["cur"]}


def okuma(text, st):
    t = norm(text)
    raw = text.strip()
    d = _ok_stats()

    def res(say, do=None):
        return {"do": {"snap": _ok_snap(), **(do or {})}, "say": say}
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Okuma hızını üç yüz kelimeye çıkar, paragraf antrenmanını başlat, İngilizce paragraf, metni durdur, devam, baştan, hızlandır ve yavaşlat diyebilirsiniz. "
                       "Okuma bitince kavrama dört diyerek anlama puanınızı kaydedin. Kendi metniniz için kendi metnim iki nokta ve metni yazın."}
    m = re.search(r"(\d{2,4})\s*kelime", t)
    if m and re.search(r"\b(çıkar|yap|ayarla|olsun|artır|düşür|hız\w*)\b", t):
        R["wpm"] = max(80, min(1000, int(m.group(1))))
        d["wpm"] = R["wpm"]
        _save(OK_FILE, d)
        return res(f"Okuma hızı dakikada {R['wpm']} kelime oldu efendim.", {"wpm": R["wpm"]})
    if re.search(r"\bhızlan\w*|\bhızlandır\w*|\bdaha hızlı\b", t):
        R["wpm"] = min(1000, R["wpm"] + 25)
        d["wpm"] = R["wpm"]
        _save(OK_FILE, d)
        return res(f"Dakikada {R['wpm']} kelime efendim.", {"wpm": R["wpm"]})
    if re.search(r"\byavaşla\w*|\bdaha yavaş\b", t):
        R["wpm"] = max(80, R["wpm"] - 25)
        d["wpm"] = R["wpm"]
        _save(OK_FILE, d)
        return res(f"Dakikada {R['wpm']} kelime efendim.", {"wpm": R["wpm"]})
    if re.search(r"\b(durdur|duraklat|dur|bekle)\b", t):
        return res("Durdurdum efendim.", {"pause": True})
    if re.search(r"\b(devam|sürdür)\w*", t):
        return res("Devam ediyorum efendim.", {"pause": False})
    if re.search(r"\bbaştan\b|\btekrar oku\b", t) and R["cur"]:
        return res("Baştan başlıyorum efendim.", {"start": R["cur"]})
    mk = re.search(r"\bkavrama\s*(?:puanı\s*)?(\d{1,3})", t)
    if mk and R["words"]:
        v = int(mk.group(1))
        kav = v if v > 5 else v * 20
        d["hist"].append({"ts": datetime.datetime.now().strftime("%d.%m %H:%M"), "wpm": R["wpm"], "words": R["words"], "lang": R["lang"], "kav": min(100, kav)})
        d["hist"] = d["hist"][-200:]
        _save(OK_FILE, d)
        R["words"] = 0
        return res(f"Kaydedildi: dakikada {R['wpm']} kelime, kavrama yüzde {min(100, kav)}.")
    if re.search(r"\b(istatistik\w*|ilerleme\w*|geçmiş\w*|ortalama\w*)\b", t):
        h = d["hist"]
        if not h:
            return {"say": "Henüz kayıtlı okumanız yok efendim."}
        avg = sum(x["wpm"] for x in h[-10:]) // len(h[-10:])
        kv = [x["kav"] for x in h[-10:] if x.get("kav") is not None]
        return {"say": f"Son okumalarınızın ortalaması dakikada {avg} kelime" + (f", ortalama kavrama yüzde {sum(kv) // len(kv)}." if kv else ".")}
    body = _raw_after_colon(raw)
    if re.search(r"\bkendi metn\w*|\bmetn\w* yapıştır", t) and body:
        txt = body
        lang = "en" if re.search(r"\b(the|and|of|to|is)\b", body.lower()) else "tr"
    elif re.search(r"\b(üret|yaz)\w*", t) and re.search(r"\b(paragraf|metin)\w*", t):
        topic = body or "ilginç bir bilim konusu"
        en = bool(re.search(r"ingilizce", t))
        txt = _ask_llm(f"{'İngilizce' if en else 'Türkçe'}, lise düzeyinde, {topic} hakkında 90 kelimelik tek paragraf yaz. Başlık, liste veya açıklama ekleme; yalnızca paragraf.")
        txt = re.sub(r"\s+", " ", txt.replace("<think>", "").split("</think>")[-1]).strip()
        if len(txt.split()) < 20:
            return {"say": "Şu an metin üretemedim efendim. Hazır paragraflardan başlayabilirsiniz."}
        lang = "en" if en else "tr"
    elif re.search(r"\b(başlat|başla|paragraf|antrenman\w*|oku\w*|başlayalım|sıradaki|yeni|başka)\b", t):
        lang = "en" if re.search(r"ingiliz\w*|english", t) else "tr"
        pool = OK_EN if lang == "en" else OK_TR
        txt = random.choice([p for p in pool if p != R["cur"]] or pool)
    else:
        return {"say": "Anlayamadım efendim. Paragraf antrenmanını başlat ya da okuma hızını üç yüz kelimeye çıkar diyebilirsiniz."}
    R.update(cur=txt, lang=lang, words=len(txt.split()))
    return res(f"{R['words']} kelimelik paragraf, dakikada {R['wpm']} kelime. Başlıyorum.", {"start": txt, "lang": lang})


# ================================================================== 5) KELİME KUTUSU
VO_FILE = "vocabulary.json"
_SEED = """substantial|önemli, hatırı sayılır|considerable|The company made a substantial profit this year.
reluctant|isteksiz|unwilling|She was reluctant to share her results.
abundant|bol, çok miktarda|plentiful|Fresh water is abundant in this region.
inevitable|kaçınılmaz|unavoidable|Change is inevitable in any growing society.
conclude|sonuca varmak, bitirmek|deduce|The study concluded that sleep improves memory.
essential|temel, şart|vital|Water is essential for life.
estimate|tahmin etmek|approximate|Experts estimate that the population will double.
obtain|elde etmek|acquire|You must obtain permission before entering.
frequent|sık, sık olan|regular|Frequent exercise keeps the heart healthy.
reduce|azaltmak|decrease|We need to reduce energy consumption.
ancient|antik, çok eski|archaic|Ancient civilizations built great cities.
benefit|fayda, yarar|advantage|Reading has many benefits for the brain.
challenge|zorluk, meydan okumak|obstacle|Learning a language is a real challenge.
consequence|sonuç, netice|outcome|Every action has a consequence.
contribute|katkıda bulunmak|donate|Many people contributed to the project.
demand|talep, istemek|request|The demand for electric cars is rising.
enhance|artırmak, geliştirmek|improve|Good lighting can enhance your mood.
evidence|kanıt|proof|There is no evidence for this theory.
flexible|esnek|adaptable|A flexible schedule helps students.
generate|üretmek|produce|Wind turbines generate electricity.
hesitate|tereddüt etmek|pause|Don't hesitate to ask questions.
impact|etki|effect|Technology has a huge impact on education.
indicate|göstermek, işaret etmek|suggest|Results indicate a clear trend.
maintain|sürdürmek, korumak|preserve|It is hard to maintain a healthy diet.
neglect|ihmal etmek|ignore|Do not neglect your homework.
obvious|açık, bariz|evident|The answer was obvious to everyone.
prevent|önlemek|avoid|Vaccines prevent many diseases.
rare|nadir|scarce|Snow is rare in this city.
severe|şiddetli, ciddi|harsh|The region suffered a severe drought.
tend|eğilimi olmak|incline|Teenagers tend to sleep late.
reveal|ortaya çıkarmak|disclose|The test revealed an error.
urgent|acil|pressing|This is an urgent matter.
vast|geniş, uçsuz bucaksız|enormous|A vast desert lies to the south.
accurate|doğru, kesin|precise|The map is not accurate.
ambitious|hırslı|determined|She is an ambitious student.
adapt|uyum sağlamak|adjust|Animals adapt to their environment.
appropriate|uygun|suitable|Wear appropriate clothes for the interview.
reliable|güvenilir|dependable|He is a reliable friend.
ability|yetenek|skill|She has the ability to learn quickly.
increase|artmak, artırmak|rise|Prices continue to increase."""
_SEED_DE = """das Haus|ev|das Gebäude|Das Haus ist sehr groß.
die Schule|okul||Ich gehe jeden Tag zur Schule.
der Freund|arkadaş|der Kamerad|Mein Freund heißt Max.
lernen|öğrenmek|studieren|Ich lerne jeden Tag Deutsch.
das Wasser|su||Ich trinke viel Wasser.
das Buch|kitap||Das Buch liegt auf dem Tisch.
arbeiten|çalışmak||Er arbeitet im Büro.
schnell|hızlı|rasch|Der Zug ist sehr schnell.
die Zeit|zaman||Ich habe keine Zeit.
schön|güzel|hübsch|Das Wetter ist heute schön."""
BOX_DAYS = [0, 1, 2, 4, 8, 16]
V = {"ids": [], "i": 0, "show": False, "await": None}


def _vo():
    d = _load(VO_FILE, {})
    if not d.get("words"):
        words = []
        for lang, blob in (("en", _SEED), ("de", _SEED_DE)):
            for ln in blob.split("\n"):
                w, tr, syn, ex = ln.split("|")
                words.append({"w": w, "tr": tr, "syn": syn, "ex": ex, "lang": lang, "box": 0, "due": "", "seen": 0, "ok": 0})
        d["words"] = words
        _save(VO_FILE, d)
    return d


def _vo_snap(d):
    cur = None
    if V["ids"] and V["i"] < len(V["ids"]):
        w = d["words"][V["ids"][V["i"]]]
        cur = {**w, "show": V["show"]}
    boxes = [sum(1 for w in d["words"] if w["box"] == b) for b in range(6)]
    return {"cur": cur, "i": V["i"], "n": len(V["ids"]), "boxes": boxes, "total": len(d["words"]),
            "done": bool(V["ids"]) and V["i"] >= len(V["ids"]), "await": V["await"]}


def _vo_session(d, n):
    today = datetime.date.today().isoformat()
    due = [i for i, w in enumerate(d["words"]) if w["seen"] and (w["due"] or "") <= today]
    new = [i for i, w in enumerate(d["words"]) if not w["seen"]]
    random.shuffle(new)
    V.update(ids=(due + new)[:n], i=0, show=False, await_=None)
    V["await"] = None


def kelime(text, st):
    t = norm(text)
    raw = text.strip()
    d = _vo()

    def res(say):
        _save(VO_FILE, d)
        return {"do": {"snap": _vo_snap(d)}, "say": say}
    cur_w = d["words"][V["ids"][V["i"]]] if V["ids"] and V["i"] < len(V["ids"]) else None
    if V["await"] and cur_w:                                       # önceki komut bir cümle ya da telaffuz bekliyordu
        mode, V["await"] = V["await"], None
        word = cur_w["w"].split()[-1].lower()
        if mode == "pron":
            from rapidfuzz import fuzz
            sc = max(fuzz.ratio(word, x) for x in t.split()) if t.split() else 0
            return res(f"Şunu duydum: {t}. Benzerlik yüzde {int(sc)}. " + ("Çok iyi efendim." if sc >= 80 else "Biraz daha net söyleyebilirsiniz. Not: Türkçe tanıma kullandığım için yaklaşıktır."))
        ok = word[:max(4, len(word) - 2)] in t and len(t.split()) >= 4
        return res("Güzel bir cümle efendim, kelimeyi doğru kullandınız." if ok else f"Cümlede {cur_w['w']} kelimesini kullanmanız ve en az dört sözcük söylemeniz gerekiyor efendim.")
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Bugünkü on kelimemi getir de. Sonra göster, bildim, bilmedim ya da zor deyin; bilmediklerinizi daha sık sorarım. Cümle kur, telaffuzumu kontrol et, "
                       "kelime ekle iki nokta apple eşittir elma ve kelime istatistiği de var."}
    m = re.search(r"(\d{1,2})\s*kelime", t)
    if re.search(r"\b(getir|başlat|başla|çalışalım|kelime çalış\w*|yeni kelime\w*)\b", t) and re.search(r"\bkelime\w*", t):
        n = int(m.group(1)) if m else (num_in(t) or 10)
        _vo_session(d, max(1, min(40, n)))
        return res(f"{len(V['ids'])} kelime hazır efendim. Anlamı için göster deyin.")
    if re.search(r"\bkelime ekle\b", t):
        body = _raw_after_colon(raw) or re.sub(r"(?i).*kelime ekle\w*\s*", "", raw)
        mm = re.match(r"\s*(.+?)\s*(?:=|eşittir|eşit)\s*(.+)$", body) or re.match(r"\s*(\S+)\s+(.+)$", body)
        if not mm:
            return {"say": "Kelime ekle iki nokta apple eşittir elma biçiminde söyleyin efendim."}
        d["words"].append({"w": mm.group(1).strip(), "tr": mm.group(2).strip(), "syn": "", "ex": "", "lang": "en", "box": 0, "due": "", "seen": 0, "ok": 0})
        return res(f"{mm.group(1).strip()} kelimesini kutuya ekledim efendim.")
    if re.search(r"\bistatistik\w*|\bkaç kelime\b", t):
        s = _vo_snap(d)
        return {"say": f"Kutuda {s['total']} kelime var. Ezberlenmiş (son kutu) {s['boxes'][5]}, öğrenilen toplam {sum(s['boxes'][1:])}."}
    if not cur_w and not d.get("words"):
        return {"say": "Kelime yok efendim."}
    if re.search(r"\bcümle kur\b|\bcümle\b", t):
        mw = re.search(r"cümle kur\w*\s*(?:[:：]\s*)?(\S+)?", raw, re.I)
        if mw and mw.group(1):
            for i, w in enumerate(d["words"]):
                if w["w"].lower().split()[-1] == mw.group(1).lower():
                    V.update(ids=[i], i=0, show=True)
                    break
        cur_w = d["words"][V["ids"][V["i"]]] if V["ids"] and V["i"] < len(V["ids"]) else None
        if not cur_w:
            return {"say": "Önce bir kelime getirin efendim."}
        V["await"] = "sent"
        return res(f"{cur_w['w']} ile bir cümle kurun, ben dinliyorum.")
    if re.search(r"\btelaffuz\w*", t) and cur_w:
        V["await"] = "pron"
        return res(f"{cur_w['w']} kelimesini söyleyin, dinliyorum.")
    if not V["ids"]:
        return {"say": "Önce bugünkü kelimelerinizi getirin efendim."}
    if V["i"] >= len(V["ids"]):
        return {"say": "Bugünkü kelimeler bitti efendim, tebrikler. Yeniden için kelimelerimi getir deyin."}
    w = d["words"][V["ids"][V["i"]]]
    if re.search(r"\b(göster|anlam\w*|çevir\w*|ne demek|türkçesi)\b", t):
        V["show"] = True
        return res(f"{w['w']}: {w['tr']}.")
    verdict = None
    if re.search(r"\b(bilmedim|yanlış|hatırlamadım|bilemedim)\b", t):
        verdict = "no"
    elif re.search(r"\b(zor|zorlandım|emin değilim)\b", t):
        verdict = "hard"
    elif re.search(r"\b(bildim|doğru|kolay|biliyorum|hatırladım)\b", t):
        verdict = "yes"
    if verdict:
        w["seen"] += 1
        if verdict == "yes":
            w["box"] = min(5, w["box"] + 1)
            w["ok"] += 1
        elif verdict == "no":
            w["box"] = 1
        w["due"] = (datetime.date.today() + datetime.timedelta(days=BOX_DAYS[w["box"]] if verdict != "no" else 0)).isoformat()
        V["i"] += 1
        V["show"] = False
        nxt = "Bugünkü kelimeler bitti efendim, tebrikler." if V["i"] >= len(V["ids"]) else f"Sıradaki: {d['words'][V['ids'][V['i']]]['w']}."
        return res(("Harika. " if verdict == "yes" else "Tekrar edeceğiz. ") + nxt)
    if re.search(r"\b(sonraki|geç|atla|ileri)\b", t):
        V["i"] += 1
        V["show"] = False
        return res("Geçtim efendim.")
    return {"say": "Anlayamadım efendim. Göster, bildim, bilmedim ya da zor deyin."}


# ================================================================== 6) BÜTÇE & HARÇLIK
BU_FILE = "pocket_budget.json"
BU_CATS = [("Kırtasiye", r"kitap|kalem|defter|silgi|fotokopi|kırtasiye|dosya|çanta|test"), ("Ulaşım", r"otobüs|metro|taksi|dolmuş|servis|benzin|akbil|ulaşım|bilet|tramvay|minibüs"),
           ("Eğlence", r"sinema|oyun|netflix|spotify|konser|eğlence|bowling|müzik|abonelik|steam"), ("Yemek", r"yemek|döner|kafe|kahve|çay|pizza|burger|hamburger|tost|simit|börek|cips|çikolata|dondurma|kantin|market|su |içecek|tatlı"),
           ("Giyim", r"tişört|pantolon|ayakkabı|mont|kıyafet|elbise|kazak|çorap")]


def _bu():
    d = _load(BU_FILE, {})
    d.setdefault("allow", 0)
    d.setdefault("tx", [])
    d.setdefault("goals", [])
    return d


def _money(raw: str):
    s = raw.replace("₺", " ")
    m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+(?:[.,]\d+)?)\s*(bin\b)?", s)
    if not m:
        return None
    v = m.group(1)
    v = v.replace(".", "") if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", v) else v.replace(",", ".")
    x = float(v) * (1000 if m.group(2) else 1)
    return x if x > 0 else None


def _cat(t):
    for name, pat in BU_CATS:
        if re.search(pat, t + " "):
            return name
    return "Diğer"


def _bu_month(d):
    ym = datetime.date.today().strftime("%Y-%m")
    tx = [x for x in d["tx"] if x["ts"].startswith(ym)]
    spent = sum(x["amt"] for x in tx if x["kind"] == "gider")
    income = sum(x["amt"] for x in tx if x["kind"] == "gelir")
    cats = {}
    for x in tx:
        if x["kind"] == "gider":
            cats[x["cat"]] = cats.get(x["cat"], 0) + x["amt"]
    return spent, income, cats


def _bu_snap(d):
    spent, income, cats = _bu_month(d)
    return {"allow": d["allow"], "spent": round(spent, 2), "income": round(income, 2), "left": round(d["allow"] + income - spent, 2), "cats": cats,
            "tx": d["tx"][-12:][::-1], "goals": d["goals"]}


def _tl(x):
    return f"{int(x)}" if float(x).is_integer() else f"{x:.2f}"


def butce(text, st):
    t = norm(text)
    raw = text.strip()
    d = _bu()

    def res(say):
        _save(BU_FILE, d)
        return {"do": {"snap": _bu_snap(d)}, "say": say}
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Harcama ekle iki nokta kitap yüz elli lira, gelir ekle harçlık beş yüz, bu ay ne kadar harcadım, kalan harçlığım, harçlığım iki bin olsun, "
                       "birikim hedefi telefon sekiz bin, birikim hedefine beş yüz lira ekle ve son harcamayı sil diyebilirsiniz."}
    if re.search(r"\bson (harcama|gider|işlem)\w*.*\b(sil|kaldır|iptal)\w*|\b(sil|iptal)\b.*\bson (harcama|işlem)", t):
        if d["tx"]:
            x = d["tx"].pop()
            return res(f"{x['note'] or x['cat']} kaydını ({_tl(x['amt'])} TL) sildim efendim.")
        return {"say": "Silinecek kayıt yok efendim."}
    if re.search(r"\bhedef\w*", t) and re.search(r"\b(sil|kaldır)\w*", t) and d["goals"]:
        g = d["goals"].pop()
        return res(f"{g['name']} hedefini sildim efendim.")
    if re.search(r"\bharçlığ\w*", t) and re.search(r"\b(olsun|yap|ayarla|belirle|kaydet|güncelle)\b", t):
        a = _money(raw)
        if a:
            d["allow"] = a
            return res(f"Aylık harçlığınız {_tl(a)} TL olarak ayarlandı efendim.")
    if re.search(r"\bbirikim\w*|\bhedef\w*", t) and not re.search(r"\b(harcama|harcadım)\b|\b(ne kadar|kaç)\b", t):
        a = _money(raw)
        dative = re.search(r"\bhedef(ine|e|ime)\b|\bbirikim(ime|e)\b", t)
        m = re.search(r"hedef\w*\s*[:：]?\s*(.*?)\s*\d", raw, re.I)
        name = re.sub(r"(?i)\b(ekle|koy|yeni|oluştur|için)\b", " ", m.group(1) if m else "").strip(" :.-")
        name = " ".join(name.split())
        if not a:
            return {"say": "Tutarı anlayamadım efendim. Örneğin birikim hedefi telefon sekiz bin lira."}
        if not dative and name:
            d["goals"].append({"name": name[:40].capitalize(), "target": a, "saved": 0})
            return res(f"{d['goals'][-1]['name']} hedefi eklendi: {_tl(a)} TL.")
        if d["goals"]:
            g = d["goals"][-1]
            for x in d["goals"]:
                if norm(x["name"]) in t:
                    g = x
            g["saved"] = min(g["target"] * 10, g["saved"] + a)
            pct = int(g["saved"] / g["target"] * 100) if g["target"] else 0
            return res(f"{g['name']} hedefine {_tl(a)} TL ekledim. Şu an {_tl(g['saved'])} TL, yüzde {pct}.")
        return {"say": "Önce bir hedef oluşturun efendim, örneğin birikim hedefi telefon sekiz bin lira."}
    if re.search(r"\b(ne kadar|kaç)\b.*\b(harca\w*|gider)\b|\bharcamalarım\b|\bbu ay\b.*\b(harca\w*)\b", t):
        spent, income, cats = _bu_month(d)
        top = max(cats, key=cats.get) if cats else ""
        return {"say": f"Bu ay {_tl(spent)} TL harcadınız" + (f"; en çok {top} ({_tl(cats[top])} TL)." if top else ".")}
    if re.search(r"\bkalan\b|\bne kadar (param|harçlığım)\b|\bharçlığım ne kadar\b", t):
        s = _bu_snap(d)
        return {"say": f"Bu ay kalan harçlığınız {_tl(s['left'])} TL efendim." if d["allow"] or d["tx"] else "Önce aylık harçlığınızı söyleyin efendim, örneğin harçlığım iki bin lira olsun."}
    kind = "gelir" if re.search(r"\b(gelir|harçlık aldım|harçlık ekle\w*|kazandım|maaş)\b", t) and not re.search(r"\b(harcadım|harcama)\b", t) else "gider"
    if re.search(r"\b(ekle|harcadım|harcama|ödedim|aldım|gelir|kazandım)\b", t):
        a = _money(raw)
        if not a:
            return {"say": "Tutarı anlayamadım efendim. Örneğin harcama ekle kitap yüz elli lira."}
        note = re.sub(r"(?i)\b(harcama|gelir|ekle|için|harcadım|ödedim|aldım|kazandım|bugün)\b|[:：]|[\d.,]+\s*(bin)?\s*(tl|lira|₺)?", " ", raw)
        note = " ".join(note.split())[:40]
        cat = _cat(t) if kind == "gider" else "Gelir"
        d["tx"].append({"ts": now, "amt": round(a, 2), "cat": cat, "note": note.capitalize(), "kind": kind})
        s = _bu_snap(d)
        return res(f"{'Gelir' if kind == 'gelir' else cat + ' harcaması'} olarak {_tl(a)} TL kaydedildi." + (f" Kalan harçlık {_tl(s['left'])} TL." if d["allow"] else ""))
    return {"say": "Anlayamadım efendim. Harcama ekle kitap yüz elli lira diyebilirsiniz."}


# ================================================================== 7) KARAR ÇARKI
CA_FILE = "decision_wheels.json"
CA_DEF = {"ders çalışma": ["Matematik", "Fizik", "Kimya", "Biyoloji", "Türkçe", "Tarih", "Coğrafya"],
          "yemek": ["Tavuk döner", "Makarna", "Pizza", "Mercimek çorbası", "Omlet", "Köfte"], "ne yapsam": ["Kitap oku", "Yürüyüşe çık", "Film izle", "Ders çalış", "Müzik dinle", "Arkadaşını ara"]}


def _ca():
    d = _load(CA_FILE, {})
    if not d.get("wheels"):
        d = {"wheels": {k: list(v) for k, v in CA_DEF.items()}, "cur": "ders çalışma"}
        _save(CA_FILE, d)
    if d.get("cur") not in d["wheels"]:
        d["cur"] = next(iter(d["wheels"]))
    return d


def _ca_snap(d):
    return {"wheels": d["wheels"], "cur": d["cur"]}


SAY = None            # main.py: konuşma işlevi (yalnızca çark sonucu, animasyon bitince söylenir)


def _after_spin(msg: str) -> str:
    """Çark animasyonu ~4,5 sn sürer: sonuç önceden söylenip sürpriz bozulmasın diye animasyon bitince konuşulur; şimdilik sessiz."""
    if SAY:
        threading.Timer(4.8, lambda: SAY(msg)).start()
        return ""
    return msg


def cark(text, st):
    t = norm(text)
    raw = text.strip()
    d = _ca()

    def res(say, do=None):
        _save(CA_FILE, d)
        return {"do": {"snap": _ca_snap(d), **(do or {})}, "say": say}
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Ders çalışma çarkını çevir, çarka seçenek ekle iki nokta Biyoloji ödevi, çarktan sil, yeni çark yemek iki nokta pizza virgül kebap, "
                       "rastgele sayı seç bir ile elli arası, yazı tura ve zar at diyebilirsiniz."}
    m = re.search(r"(\d+)\s*(?:ile|ve|-)\s*(\d+)\s*(?:arası|arasında|arasi)", t) or re.search(r"rastgele sayı.*?(\d+)\D+(\d+)", t)
    if m and re.search(r"\bsayı\w*", t):
        a, b = sorted((int(m.group(1)), int(m.group(2))))
        n = random.randint(a, b)
        return res(f"{a} ile {b} arasında {n} çıktı efendim.", {"num": {"a": a, "b": b, "n": n}})
    if re.search(r"\byazı tura\b|\bpara at\w*", t):
        r = random.choice(["Yazı", "Tura"])
        return res(f"{r} geldi efendim.", {"num": {"txt": r}})
    if re.search(r"\bzar\b", t):
        n = random.randint(1, 6)
        return res(f"{n} geldi efendim.", {"num": {"txt": f"⚀⚁⚂⚃⚄⚅"[n - 1] + f" {n}"}})
    name = next((k for k in sorted(d["wheels"], key=len, reverse=True) if norm(k) in t), None)
    if re.search(r"\byeni (çark|kura)\w*|\bçark (oluştur|yap)\w*|\bkura çek", t):
        body = _raw_after_colon(raw)
        if not body:
            return {"say": "Seçenekleri iki nokta üst üste sonrası virgülle söyleyin efendim. Örneğin yeni çark yemek iki nokta pizza virgül kebap."}
        head = re.sub(r"(?i)(yeni|çark\w*|kura|çek|oluştur|yap)", " ", raw.split(":", 1)[0]).strip() or "kura"
        opts = [x.strip().capitalize() for x in re.split(r"[,;]| ve ", body) if x.strip()][:24]
        if len(opts) < 2:
            return {"say": "En az iki seçenek gerekiyor efendim."}
        if re.search(r"kura çek", t):                         # kalıcı olmayan hızlı kura
            pick = random.randrange(len(opts))
            d["wheels"]["kura"], d["cur"] = opts, "kura"
            return res(_after_spin(f"{opts[pick]} çıktı efendim."), {"spin": {"idx": pick, "label": opts[pick]}})
        d["wheels"][head.lower()] = opts
        d["cur"] = head.lower()
        return res(f"{head} çarkı {len(opts)} seçenekle hazır efendim.")
    if re.search(r"\b(seçenek|seçeneği)\b.*\b(ekle)\w*|\bçarka\b.*\bekle\w*", t):
        body = _raw_after_colon(raw) or re.sub(r"(?i).*ekle\w*\s*", "", raw)
        opts = [x.strip().capitalize() for x in re.split(r"[,;]", body) if x.strip()]
        if not opts:
            return {"say": "Eklenecek seçeneği söyleyin efendim."}
        k = name or d["cur"]
        d["wheels"][k] = (d["wheels"][k] + opts)[:24]
        d["cur"] = k
        return res(f"{', '.join(opts)} {k} çarkına eklendi efendim.")
    if re.search(r"\b(sil|çıkar|kaldır)\w*", t):
        k = name or d["cur"]
        if re.search(r"\bçark\w* (sil|kaldır)\w*|\bçarkı (sil|kaldır)", t) and len(d["wheels"]) > 1:
            d["wheels"].pop(k)
            return res(f"{k} çarkı silindi efendim.")
        body = _raw_after_colon(raw) or re.sub(r"(?i).*\b(çarktan|çarkdan|çarkı)\b\s*", "", raw)
        body = re.sub(r"(?i)\b(sil\w*|çıkar\w*|kaldır\w*)\b", "", body).strip(" :,")
        before = len(d["wheels"][k])
        d["wheels"][k] = [x for x in d["wheels"][k] if norm(x) != norm(body)]
        return res("Seçeneği çıkardım efendim." if len(d["wheels"][k]) < before else "Böyle bir seçenek bulamadım efendim.")
    if re.search(r"\b(çevir|döndür|çek|seç|başlat)\w*", t) or name:
        k = name or d["cur"]
        d["cur"] = k
        if len(d["wheels"][k]) < 2:
            return {"say": "Çarkta en az iki seçenek olmalı efendim."}
        idx = random.randrange(len(d["wheels"][k]))
        return res(_after_spin(f"{d['wheels'][k][idx]} çıktı efendim."), {"spin": {"idx": idx, "label": d["wheels"][k][idx]}})
    return {"say": "Anlayamadım efendim. Ders çalışma çarkını çevir diyebilirsiniz."}


# ================================================================== 8) HIZLI BAŞLATICI (makro sahneleri + kısayollar)
SP_FILE = "system_presets.json"
SP_DEF = {"scenes": [
    {"name": "yazılım ortamı", "items": [{"t": "app", "v": "visual studio code"}, {"t": "url", "v": "https://github.com"}, {"t": "app", "v": "spotify"}], "hotkey": ""},
    {"name": "ders çalışma", "items": [{"t": "app", "v": "not defteri"}, {"t": "url", "v": "https://mebi.eba.gov.tr"}], "hotkey": ""}], "peek": "ctrl+alt+m"}
TYPES = {"app": "Uygulama", "url": "Site", "folder": "Klasör", "file": "Dosya"}


def _sp():
    d = _load(SP_FILE, {})
    if not d.get("scenes") and "scenes" not in d:
        d = json.loads(json.dumps(SP_DEF))
        _save(SP_FILE, d)
    d.setdefault("scenes", [])
    import settings
    pk = settings.get("kisayol_peek")
    d["peek"] = "ctrl+alt+m" if pk is None else pk
    return d


def hotkey_scenes():
    """[(kısayol, sahne adı)] — hotkeys.py kaydeder."""
    return [(s["hotkey"], s["name"]) for s in _sp()["scenes"] if s.get("hotkey")]


def _find(d, t):
    t = norm(t)
    best = None
    for s in d["scenes"]:
        n = norm(s["name"])
        if n and n in t and (best is None or len(n) > len(norm(best["name"]))):
            best = s
    return best


def _run_item(it):
    import tools
    k, v = it.get("t"), str(it.get("v") or "")
    if k == "app":
        tools.open_app(v)
    elif k == "url":
        import webbrowser
        if re.match(r"^https?://[^\s]+$", v):
            webbrowser.open(v)
    elif k in ("folder", "file"):
        p = os.path.expandvars(os.path.expanduser(v))
        if os.path.exists(p):
            os.startfile(p)


def launcher_run(name: str) -> str:
    """Sahnedeki her öğeyi sırayla açar (arka planda; öğeler arasında kısa bekleme). Yalnızca uygulama adı, http(s) adresi, var olan klasör/dosya: komut çalıştırılmaz."""
    d = _sp()
    sc = next((s for s in d["scenes"] if s["name"].lower() == str(name).lower()), None)
    if not sc or not sc["items"]:
        return "Bu sahne boş ya da yok efendim."

    def go():
        for it in sc["items"]:
            try:
                _run_item(it)
            except Exception as e:
                print("sahne öğesi açılamadı:", type(e).__name__, flush=True)
            time.sleep(0.8)
    threading.Thread(target=go, daemon=True).start()
    return f"{sc['name'].capitalize()} sahnesi başlatılıyor efendim, {len(sc['items'])} öğe açılacak."


def voice_launch(t: str):
    """Mod dışında da çalışır: '<sahne adı> sahnesini/ortamını başlat'. Eşleşme yoksa None (diğer komutlara dokunmaz)."""
    if not re.search(r"\b(sahne\w*|ortam\w*)\b", t) or not re.search(r"\b(başlat|aç|çalıştır|kur)\w*", t):
        return None
    d = _sp()
    sc = _find(d, t)
    if not sc or re.search(r"\b(sil|kaldır|ekle|kısayol)\w*", t):
        return None
    return launcher_run(sc["name"])


def _reload_keys():
    try:
        import hotkeys
        hotkeys.RELOAD.set()
    except Exception:
        pass


_NUMW = {"bir": "1", "iki": "2", "üç": "3", "dört": "4", "beş": "5", "altı": "6", "yedi": "7", "sekiz": "8", "dokuz": "9", "sıfır": "0"}


def _combo_from_words(text):
    """'ctrl alt 1' / 'kontrol alt bir' / 'alt m' konuşmasından kısayol (norm 'bir' sözcüğünü atar, bu yüzden ham metinden okunur)."""
    import hotkeys
    s = text.replace("İ", "i").replace("I", "ı").lower()
    toks = [_NUMW.get(x, x) for x in re.findall(r"[\wçğıöşü]+", s)]
    toks = [x for x in toks if x in hotkeys.MODS or x in hotkeys.NAMED or (len(x) == 1 and x.isalnum()) or re.fullmatch(r"f\d{1,2}", x)]
    return hotkeys.canon("+".join(toks))


def baslat(text, st):
    t = norm(text)
    raw = text.strip()
    d = _sp()

    def res(say):
        _save(SP_FILE, {"scenes": d["scenes"]})
        _reload_keys()
        return {"do": {"snap": _sp_snap()}, "say": say}
    if raw.startswith("§"):                                           # sayfadaki düğmeler: §komut|alan|alan...
        parts = raw[1:].split("|")
        c = parts[0]
        try:
            if c == "ekle":
                sc = next(s for s in d["scenes"] if s["name"] == parts[1])
                ty, v = parts[2], "|".join(parts[3:]).strip()
                if ty in TYPES and v:
                    if ty == "url" and not re.match(r"^https?://", v):
                        v = "https://" + v
                    sc["items"].append({"t": ty, "v": v[:300]})
                    return res("Öğe eklendi efendim.")
            elif c == "sil":
                sc = next(s for s in d["scenes"] if s["name"] == parts[1])
                sc["items"].pop(int(parts[2]))
                return res("Öğe kaldırıldı efendim.")
            elif c == "yeni":
                nm = parts[1].strip().lower()[:30]
                if nm and not any(s["name"] == nm for s in d["scenes"]):
                    d["scenes"].append({"name": nm, "items": [], "hotkey": ""})
                    return res(f"{nm} sahnesi oluşturuldu efendim.")
            elif c == "sahnesil":
                d["scenes"] = [s for s in d["scenes"] if s["name"] != parts[1]]
                return res("Sahne silindi efendim.")
            elif c == "kisayol":
                sc = next(s for s in d["scenes"] if s["name"] == parts[1])
                combo = scenes_hotkey_canon(parts[2])
                if parts[2].strip() and not combo:
                    return {"do": {"snap": _sp_snap()}, "say": "Kısayol geçersiz efendim: en az Ctrl, Alt ya da Win ile bir tuş gerekir."}
                if combo and (combo == d["peek"] or any(s is not sc and s.get("hotkey") == combo for s in d["scenes"])):
                    return {"do": {"snap": _sp_snap()}, "say": "Bu kısayol başka bir yerde kullanılıyor efendim."}
                sc["hotkey"] = combo
                return res(f"Kısayol {combo or 'kaldırıldı'} efendim.")
            elif c == "peek":
                combo = scenes_hotkey_canon(parts[1])
                if parts[1].strip() and not combo:
                    return {"do": {"snap": _sp_snap()}, "say": "Kısayol geçersiz efendim: en az Ctrl, Alt ya da Win ile bir tuş gerekir."}
                if combo and any(s.get("hotkey") == combo for s in d["scenes"]):
                    return {"do": {"snap": _sp_snap()}, "say": "Bu kısayol bir sahnede kullanılıyor efendim."}
                import settings
                settings.set("kisayol_peek", combo)
                d["peek"] = combo
                return res(f"Masaüstüne geç kısayolu {combo or 'kapatıldı'} efendim.")
            elif c == "calistir":
                return {"say": launcher_run(parts[1])}
        except (StopIteration, IndexError, ValueError):
            pass
        return {"say": ""}
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Yazılım ortamını aç diyerek sahneyi başlatın. Yeni sahne ders çalışma, ders çalışma sahnesine uygulama ekle spotify, siteye ekle youtube nokta com, "
                       "sahneyi sil ve kısayol ata ctrl alt 1 diyebilirsiniz. Kısayolları sayfadan da istediğiniz tuşlarla ayarlayabilirsiniz."}
    if re.search(r"\bmasaüstü\w*.*\bkısayol\w*|\bkısayol\w*.*\bmasaüstü\w*", t):
        combo = _combo_from_words(re.sub(r"(?i)masa\w*", " ", raw))
        import settings
        if re.search(r"\b(kaldır|sil|kapat)\w*", t):
            settings.set("kisayol_peek", "")
            return res("Masaüstüne geç kısayolunu kapattım efendim.")
        if combo:
            settings.set("kisayol_peek", combo)
            return res(f"Masaüstüne geç kısayolu {combo} oldu efendim.")
    if re.search(r"\b(yeni|oluştur|ekle)\w*\s+sahne\w*|\bsahne\w*\s+(oluştur|ekle)\w*", t):
        nm = re.sub(r"\b(yeni|oluştur\w*|ekle\w*|sahne\w*)\b", " ", t).strip()
        if not nm:
            return {"say": "Sahneye ne ad vereyim efendim? Örneğin yeni sahne ders çalışma."}
        if any(s["name"] == nm for s in d["scenes"]):
            return {"say": "Bu adda bir sahne zaten var efendim."}
        d["scenes"].append({"name": nm[:30], "items": [], "hotkey": ""})
        return res(f"{nm} sahnesi oluşturuldu efendim. Uygulama, site ya da klasör ekleyebilirsiniz.")
    sc = _find(d, t)
    if sc and re.search(r"\bkısayol\w*", t):
        if re.search(r"\b(kaldır|sil|kapat)\w*", t):
            sc["hotkey"] = ""
            return res("Kısayolu kaldırdım efendim.")
        combo = _combo_from_words(re.sub(re.escape(sc["name"]), " ", raw, flags=re.I))
        if not combo:
            return {"say": "Kısayolu anlayamadım efendim. Örneğin kontrol alt 1 deyin."}
        if combo == d["peek"] or any(s is not sc and s.get("hotkey") == combo for s in d["scenes"]):
            return {"say": "Bu kısayol başka bir yerde kullanılıyor efendim."}
        sc["hotkey"] = combo
        return res(f"{sc['name']} sahnesinin kısayolu {combo} oldu efendim.")
    if sc and re.search(r"\b(sil|kaldır)\w*", t):
        if re.search(r"\bsahne(yi|sini|si)?\s+(sil|kaldır)\w*|\b(sil|kaldır)\w*\s+sahne", t):
            d["scenes"] = [s for s in d["scenes"] if s is not sc]
            return res(f"{sc['name']} sahnesini sildim efendim.")
        rest = [w for w in re.sub(r"\b(sahne\w*|sil\w*|kaldır\w*|uygulama\w*|site\w*|klasör\w*|dosya\w*|den|dan)\b", " ", t.replace(norm(sc["name"]), " ")).split() if len(w) > 1]
        for i, it in enumerate(sc["items"]):
            if any(w in it["v"].lower() for w in rest):
                sc["items"].pop(i)
                return res(f"{it['v']} sahneden kaldırıldı efendim.")
        return {"say": "Hangi öğeyi kaldıracağımı anlayamadım efendim."}
    if sc and re.search(r"\bekle\w*", t):
        body = re.sub(r"(?i).*\bekle\w*\s*[:：]?\s*", "", raw).strip()
        ty = "app" if re.search(r"\buygulama\w*|\bprogram\w*", t) else "url" if re.search(r"\bsite\w*|\badres\w*|\blink\w*", t) else "folder" if re.search(r"\bklasör\w*", t) else "file" if re.search(r"\bdosya\w*", t) else ""
        body = re.sub(r"(?i)^(uygulaması|uygulama|program|site|siteyi|klasör|klasörü|dosya|dosyayı|adres|link)\s*", "", body).strip()
        if not ty or not body:
            return {"say": "Neyi ekleyeyim efendim? Örneğin ders çalışma sahnesine uygulama ekle spotify."}
        if ty == "url":
            body = body.replace(" nokta ", ".").replace(" ", "")
            body = body if body.startswith("http") else "https://" + body
        sc["items"].append({"t": ty, "v": body[:300]})
        return res(f"{body} {sc['name']} sahnesine eklendi efendim.")
    if sc:
        return {"say": launcher_run(sc["name"])}
    if re.search(r"\b(başlat|aç|çalıştır)\w*", t):
        return {"say": "Bu adda bir sahne bulamadım efendim. Sahnelerinizi ekranda görebilirsiniz."}
    return {"say": "Anlayamadım efendim. Yazılım ortamını aç gibi bir sahne adı ya da yardım deyin."}


def scenes_hotkey_canon(s):
    import hotkeys
    return hotkeys.canon(s)


def _sp_snap():
    d = _sp()
    try:
        import hotkeys
        st = dict(hotkeys.STATUS)
    except Exception:
        st = {}
    return {"scenes": d["scenes"], "peek": d["peek"], "status": st, "types": TYPES}


# ================================================================== kayıt
INIT = {"optik": _opt_snap, "tahta": lambda: _th_snap(_th()), "masa": _ma, "okuma": _ok_snap, "kelime": lambda: (_vo_session_reset(), _vo_snap(_vo()))[1],
        "butce": lambda: _bu_snap(_bu()), "cark": lambda: _ca_snap(_ca()), "baslatici": _sp_snap}


def _vo_session_reset():
    V.update(ids=[], i=0, show=False)
    V["await"] = None


PENDING: dict = {}          # extras: mod açılırken söylenen komut ('TYT Türkçe denemesi başlat') mod açılınca çalışır


def init_payload(kind):
    if kind == "optik" and not O["on"]:
        O.update(fin=False, n=0, name="", ans={}, flag=[], key="", res=None)
    pend = PENDING.pop(kind, None)
    if pend and kind == "optik":
        norm_t = norm(pend)
        if re.search(r"\b(başlat|başla|çöz)\w*", norm_t) and (any(k in norm_t for k in OP_PRE) or re.search(r"soruluk", norm_t)):
            optik(pend, {})
    return {"snap": INIT[kind]()}
