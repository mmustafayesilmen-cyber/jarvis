"""On yaratıcı mod: Rüya günlüğü (ruya), Nefes rehberi (nefes), Ritim stüdyosu (ritim), Müzik kutusu (nota), Mors atölyesi (mors),
Renk atölyesi (renk), Zen kum bahçesi (kum), Simya atölyesi (simya), Zaman kapsülü (kapsul), Hikâye zarları (hikaye).
Hepsi yereldir (internet gerekmez; yalnızca rüya yorumu ve hikâye yazımı yerel Ollama'yı kullanır, o da yoksa atlanır). Ses WebAudio ile sayfada üretilir.
Kalıcı veri repo kökündeki yaratici_data.json içindedir (gitignored). Her işlev (text, state) -> {"say", "do"} döner; sayfalar ui/scene_<kind>.html.
Çıkış yalnızca açık ifadelerle (scenes.handle içindeki ortak dal). Uzaktan whitelist'te DEĞİL."""
import colorsys
import datetime
import json
import os
import random
import re
import threading

import scenes
from scenes import norm

HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(HERE, "yaratici_data.json")
_lk = threading.Lock()
NOTIFY = None          # main bağlar: NOTIFY(kind, do)
SAY = None             # main bağlar: SAY(metin, kind)
KINDS = ("ruya", "nefes", "ritim", "nota", "mors", "renk", "kum", "simya", "kapsul", "hikaye")


def _load():
    try:
        with open(FILE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


D = _load()


def _save():
    with _lk:
        try:
            with open(FILE + ".tmp", "w", encoding="utf-8") as f:
                json.dump(D, f, ensure_ascii=False, indent=1)
            os.replace(FILE + ".tmp", FILE)
        except OSError:
            pass


def _after_colon(raw: str) -> str:
    return raw.split(":", 1)[1].strip() if ":" in raw else ""


def _ask_llm(prompt: str, system: str = "") -> str:
    try:
        import scenes_yeni
        return scenes_yeni._ask_llm(prompt, system) or ""
    except Exception:
        return ""


def _bg(kind, fn):
    threading.Thread(target=fn, daemon=True).start()


def _push(kind, do):
    if NOTIFY:
        try:
            NOTIFY(kind, do)
        except Exception:
            pass


NUM_W = {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10}


def _num(t, default=None):
    m = re.search(r"\d+", t)
    if m:
        return int(m.group())
    for w, n in NUM_W.items():
        if re.search(rf"\b{w}\b", t):
            return n
    return default


# ======================================================================= RÜYA GÜNLÜĞÜ
STOP = set("ve ile ama fakat çünkü gibi için daha çok pek biraz sonra önce ben benim bana beni sen bir bu şu o ki mi mı mu mü de da ne neden niye hep hiç "
           "olarak olan oldu olduğunu vardı yoktu gördüm gördüm sanki sonra sonrasında içinde üzerinde yanında rüya rüyamda rüyam rüyada var yok "
           "kendimi kendim bazen aniden birden tam sadece bile artık yine hâlâ hala ise ya yada veya ancak ayrıca bunu şunu onu bunlar onlar bütün tüm her hiçbir "
           "başka gibi kadar doğru diye derken ederken görüyordum gidiyordum oluyordu yapıyordum vardı olmuştu".split())


def _words(txt):
    out = []
    for w in re.findall(r"[a-zçğıöşüâîû]{4,}", norm(txt)):
        base = re.sub(r"(ları|leri|lar|ler|ında|inde|unda|ünde|dan|den|tan|ten|nda|nde|da|de|ta|te)$", "", w) if len(w) > 5 else w
        if base not in STOP and w not in STOP and len(base) >= 4:
            out.append(base)
    return list(dict.fromkeys(out))[:14]


def _ruya_snap():
    dr = D.setdefault("ruya", [])
    cnt = {}
    for r in dr:
        for w in r.get("w", []):
            cnt[w] = cnt.get(w, 0) + 1
    top = sorted(cnt.items(), key=lambda x: -x[1])[:28]
    keep = {w for w, _ in top}
    edges = {}
    for r in dr:
        ws = [w for w in r.get("w", []) if w in keep]
        for i in range(len(ws)):
            for j in range(i + 1, len(ws)):
                k = tuple(sorted((ws[i], ws[j])))
                edges[k] = edges.get(k, 0) + 1
    return {"rows": [{"i": i, "d": r["d"], "t": r["t"], "w": r.get("w", []), "y": r.get("y", "")} for i, r in enumerate(dr)][-40:][::-1],
            "stars": [{"w": w, "n": n} for w, n in top], "edges": [{"a": a, "b": b, "n": n} for (a, b), n in edges.items()], "total": len(dr)}


def ruya(text, st):
    t = norm(text)
    raw = text.strip()
    dr = D.setdefault("ruya", [])
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Rüya ekle iki nokta ve rüyanızı anlatın deyin. Son rüyayı oku, tekrar eden temalar, rüyamı yorumla ve son rüyayı sil de diyebilirsiniz. Her rüya anahtar kelimelerle yıldız haritasına eklenir."}
    if re.search(r"\b(tekrar eden|tema\w*|yıldız haritası|harita\w*)\b", t):
        s = _ruya_snap()["stars"][:5]
        if not s:
            return {"say": "Henüz rüya kaydı yok efendim."}
        return {"say": "En sık geçenler: " + ", ".join(f"{x['w']} {x['n']} kez" for x in s) + ".", "do": {"snap": _ruya_snap()}}
    if re.search(r"\bson rüya\w* (sil|kaldır)\w*|\brüya\w* sil\w*", t):
        if not dr:
            return {"say": "Silinecek rüya yok efendim."}
        dr.pop()
        _save()
        return {"say": "Son rüya silindi efendim.", "do": {"snap": _ruya_snap()}}
    if re.search(r"\b(yorumla|yorum\w*|anlamı ne|ne anlama)\b", t):
        if not dr:
            return {"say": "Önce bir rüya ekleyin efendim."}
        r = dr[-1]
        idx = len(dr) - 1

        def work():
            y = _ask_llm("Aşağıdaki rüyayı 3-4 cümleyle, eğlence amaçlı ve sakin bir dille psikolojik sembolizm açısından yorumla. Kesin hüküm verme, kehanet söyleme. Türkçe yaz.\n\nRüya: " + r["t"])
            if not y:
                _push("ruya", {"msg": "Yorum için yerel model açık değil efendim."})
                return
            if idx < len(dr) and dr[idx]["t"] == r["t"]:
                dr[idx]["y"] = y.strip()
                _save()
            _push("ruya", {"snap": _ruya_snap(), "msg": "Yorum hazır."})
        _bg("ruya", work)
        return {"say": "Yorumluyorum efendim, bu yalnızca eğlence amaçlı bir okuma olacak."}
    if re.search(r"\bson rüya\w* (oku|göster|anlat)\w*|\brüyam\w* (oku|neydi)\b", t):
        if not dr:
            return {"say": "Henüz rüya kaydı yok efendim."}
        return {"say": "Son rüyanız: " + dr[-1]["t"][:400], "do": {"snap": _ruya_snap()}}
    body = _after_colon(raw)
    if re.search(r"\b(ekle|kaydet|yaz)\w*|\brüya\w*", t) and (body or len(raw) > 40):
        body = body or re.sub(r"(?i)^(jarvis\W+)?(rüyam|rüya ekle|rüya)\W*", "", raw).strip()
        if len(body) < 8:
            return {"say": "Rüyayı biraz daha ayrıntılı anlatın efendim."}
        dr.append({"d": datetime.date.today().strftime("%d.%m.%Y"), "t": body[:1500], "w": _words(body)})
        del dr[:-200]
        _save()
        return {"say": f"Rüya kaydedildi efendim, {len(dr[-1]['w'])} anahtar kelime yıldız haritasına eklendi.", "do": {"snap": _ruya_snap()}}
    return {"say": "Rüya ekle iki nokta diyerek rüyanızı anlatın efendim."}


# ======================================================================= NEFES REHBERİ
PAT = {
    "kutu": ("Kutu nefesi", [["Nefes al", 4], ["Tut", 4], ["Ver", 4], ["Tut", 4]], "Odaklanma ve sakinlik"),
    "478": ("4-7-8", [["Nefes al", 4], ["Tut", 7], ["Ver", 8]], "Uykuya geçiş, gerginlik"),
    "sakin": ("Sakin nefes", [["Nefes al", 5], ["Ver", 5]], "Günlük gevşeme"),
    "enerji": ("Enerji nefesi", [["Nefes al", 2], ["Ver", 2]], "Uyanıklık, hızlı toparlanma"),
    "uzun": ("Uzun verme", [["Nefes al", 4], ["Ver", 8]], "Kalp ritmini yavaşlatma"),
}
N = {"pat": "kutu", "on": False, "cycles": 6}


def _nefes_do(extra=None):
    ad, steps, ne = PAT[N["pat"]]
    return {"pat": {"id": N["pat"], "ad": ad, "steps": steps, "ne": ne}, "cycles": N["cycles"], "pats": [{"id": k, "ad": v[0], "ne": v[2]} for k, v in PAT.items()], **(extra or {})}


def nefes(text, st):
    t = norm(text)
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Başlat, durdur, kutu nefesi, dört yedi sekiz, sakin nefes, enerji nefesi, uzun verme ve on tur yap diyebilirsiniz."}
    if re.search(r"\b4 7 8\b|\b478\b|\bdört yedi sekiz|\buyku nefes\w*|\buyuyamıyorum", t):
        N["pat"] = "478"
    elif re.search(r"\bkutu\b|\bodak nefes\w*|\bdört dört\b", t):
        N["pat"] = "kutu"
    elif re.search(r"\benerji\w*|\buyanık\w*|\bkendime gel\w*", t):
        N["pat"] = "enerji"
    elif re.search(r"\buzun\b|\bkalp\w*|\byavaşla\w*", t):
        N["pat"] = "uzun"
    elif re.search(r"\bsakin\w*|\bgevşe\w*|\brahatla\w*|\bstres\w*", t):
        N["pat"] = "sakin"
    m = re.search(r"(\d+|bir|iki|üç|dört|beş|altı|yedi|sekiz|dokuz|on|yirmi)\s*(tur|döngü|nefes)", t)
    if m:
        N["cycles"] = max(1, min(30, int(m.group(1)) if m.group(1).isdigit() else {**NUM_W, "yirmi": 20}[m.group(1)]))
    if re.search(r"\b(dur\w*|bitir|bırak|ara ver)\b", t):
        N["on"] = False
        return {"say": "Nefes egzersizi durdu efendim.", "do": _nefes_do({"run": False})}
    if re.search(r"\b(başlat|başla|başlayalım|çalıştır|hadi)\w*|\bnefes al\w*", t):
        N["on"] = True
        return {"say": f"{PAT[N['pat']][0]} başlıyor efendim, {N['cycles']} tur. Omuzlarınızı gevşetin.", "do": _nefes_do({"run": True})}
    return {"say": f"{PAT[N['pat']][0]} seçildi efendim. Başlat derseniz başlarım.", "do": _nefes_do({"run": N["on"]})}


# ======================================================================= RİTİM STÜDYOSU
INS = ("kick", "snare", "hat", "clap", "tom")
PRESETS = {
    "house": (122, {"kick": [1, 5, 9, 13], "clap": [5, 13], "hat": [3, 7, 11, 15]}),
    "hiphop": (90, {"kick": [1, 4, 11], "snare": [5, 13], "hat": [1, 3, 5, 7, 9, 11, 13, 15]}),
    "trap": (140, {"kick": [1, 8, 11], "snare": [9], "hat": list(range(1, 17)), "clap": [9]}),
    "rock": (118, {"kick": [1, 9, 11], "snare": [5, 13], "hat": [1, 3, 5, 7, 9, 11, 13, 15]}),
    "disko": (118, {"kick": [1, 5, 9, 13], "snare": [5, 13], "hat": [3, 7, 11, 15, 16]}),
    "reggae": (76, {"kick": [9], "snare": [9], "hat": [3, 7, 11, 15], "tom": [5, 13]}),
    "halay": (128, {"kick": [1, 5, 9, 13], "tom": [3, 7, 11, 15], "snare": [8, 16], "hat": [1, 2, 5, 6, 9, 10, 13, 14]}),
}


def _steps_from(d):
    return {k: [1 if (i + 1) in d.get(k, []) else 0 for i in range(16)] for k in INS}


R = D.setdefault("ritim", {})
if "steps" not in R:
    R.update(bpm=PRESETS["house"][0], steps=_steps_from(PRESETS["house"][1]), swing=0, saved={})
R.setdefault("saved", {})
R["play"] = False


def _r_snap():
    return {"bpm": R["bpm"], "steps": R["steps"], "swing": R.get("swing", 0), "play": R["play"], "saved": sorted(R["saved"]), "presets": list(PRESETS)}


def ritim(text, st):
    t = norm(text)
    raw = text.strip()
    if raw.startswith("§"):                                   # sayfadan sessiz eşitleme: §step|araç|adım|0-1, §bpm|n
        try:
            p = raw[1:].split("|")
            if p[0] == "step" and p[1] in INS:
                R["steps"][p[1]][int(p[2])] = 1 if p[3] == "1" else 0
            elif p[0] == "bpm":
                R["bpm"] = max(50, min(220, int(p[1])))
        except (ValueError, IndexError):
            pass
        return {"say": ""}
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Çal, durdur, tempo yüz yirmi, hızlandır, yavaşlat, house, hiphop, trap, rock, disko, reggae ya da halay ritmi, kick ekle bir beş dokuz, snare çıkar beş, rastgele ritim, ritmi kaydet adı ve yükle adı diyebilirsiniz."}
    for k in sorted(R["saved"], key=len, reverse=True):
        if re.search(r"\b(yükle|aç|getir)\w*", t) and norm(k) in t:
            R["bpm"], R["steps"] = R["saved"][k]["bpm"], R["saved"][k]["steps"]
            return {"say": f"{k} ritmi yüklendi efendim.", "do": {"snap": _r_snap()}}
    for k, (bpm, d) in PRESETS.items():
        if k in t or (k == "hiphop" and re.search(r"hip hop", t)):
            R["bpm"], R["steps"] = bpm, _steps_from(d)
            R["play"] = True
            return {"say": f"{k.capitalize()} ritmi, tempo {bpm}.", "do": {"snap": _r_snap(), "play": True}}
    if re.search(r"\brastgele\b", t):
        R["steps"] = {k: [1 if random.random() < p else 0 for _ in range(16)] for k, p in zip(INS, (.22, .15, .5, .12, .1))}
        for i in (0, 8):
            R["steps"]["kick"][i] = 1
        R["bpm"] = random.randint(80, 150)
        R["play"] = True
        return {"say": f"Rastgele ritim hazır, tempo {R['bpm']}.", "do": {"snap": _r_snap(), "play": True}}
    if re.search(r"\b(kaydet)\w*", t):
        name = (_after_colon(raw) or re.sub(r"(?i).*kaydet\w*\s*", "", raw)).strip()[:24] or f"ritim {len(R['saved']) + 1}"
        R["saved"][name] = {"bpm": R["bpm"], "steps": R["steps"]}
        _save()
        return {"say": f"{name} adıyla kaydedildi efendim.", "do": {"snap": _r_snap()}}
    if re.search(r"\btemizle\w*|\bsıfırla\w*|\bhepsini sil\w*", t):
        R["steps"] = {k: [0] * 16 for k in INS}
        return {"say": "Ritim temizlendi efendim.", "do": {"snap": _r_snap()}}
    m = re.search(r"\b(kick|bas|davul|snare|trampet|hat|hi hat|clap|alkış|tom)\w*\s+(ekle|çıkar|sil|kaldır)\w*\s*([\d\s,ve]*)", t)
    if m:
        name = {"bas": "kick", "davul": "kick", "trampet": "snare", "hi": "hat", "alkış": "clap"}.get(m.group(1), m.group(1))
        ns = [int(x) for x in re.findall(r"\d+", m.group(3)) if 1 <= int(x) <= 16]
        if name in INS and ns:
            for n in ns:
                R["steps"][name][n - 1] = 1 if m.group(2) == "ekle" else 0
            return {"say": f"{name} {'eklendi' if m.group(2) == 'ekle' else 'çıkarıldı'}.", "do": {"snap": _r_snap()}}
        return {"say": "Hangi adımları, bir ile on altı arasında söyleyin efendim."}
    if re.search(r"\btempo\b|\bbpm\b", t) and _num(t):
        R["bpm"] = max(50, min(220, _num(t)))
        return {"say": f"Tempo {R['bpm']}.", "do": {"snap": _r_snap()}}
    if re.search(r"\bhızlan\w*|\bhızlandır\w*|\bdaha hızlı\b", t):
        R["bpm"] = min(220, R["bpm"] + 10)
        return {"say": f"Tempo {R['bpm']}.", "do": {"snap": _r_snap()}}
    if re.search(r"\byavaşla\w*|\bdaha yavaş\b", t):
        R["bpm"] = max(50, R["bpm"] - 10)
        return {"say": f"Tempo {R['bpm']}.", "do": {"snap": _r_snap()}}
    if re.search(r"\bswing\w*|\bsalla\w*", t):
        R["swing"] = 0 if R.get("swing") else 0.35
        return {"say": "Swing " + ("açık." if R["swing"] else "kapalı."), "do": {"snap": _r_snap()}}
    if re.search(r"\b(dur\w*|bitir|sustur|kes)\b", t):
        R["play"] = False
        return {"say": "Ritim durdu efendim.", "do": {"snap": _r_snap(), "play": False}}
    if re.search(r"\b(çal|başlat|başla|oynat|devam)\w*", t):
        R["play"] = True
        return {"say": "", "do": {"snap": _r_snap(), "play": True}}
    return {"say": "Ritim komutunu anlayamadım efendim, yardım deyin."}


# ======================================================================= MÜZİK KUTUSU
NOTE_ST = {"do": 0, "re": 2, "mi": 4, "fa": 5, "sol": 7, "la": 9, "si": 11}
SCALES = {"majör": [0, 2, 4, 5, 7, 9, 11, 12], "minör": [0, 2, 3, 5, 7, 8, 10, 12], "pentatonik": [0, 2, 4, 7, 9, 12], "blues": [0, 3, 5, 6, 7, 10, 12]}
CHORDS = {"majör": [0, 4, 7], "minör": [0, 3, 7], "7": [0, 4, 7, 10], "azaltılmış": [0, 3, 6], "sus": [0, 5, 7]}
NT = {"inst": "piyano"}
INSTR = ("piyano", "org", "çan", "synth", "gitar")


def _note_tokens(t):
    out = []
    for m in re.finditer(r"\b(do|re|mi|fa|sol|la|si)\b(?:\s+(diyez|bemol))?", t):
        n = 60 + NOTE_ST[m.group(1)] + (1 if m.group(2) == "diyez" else -1 if m.group(2) == "bemol" else 0)
        out.append(n)
    return out


def nota(text, st):
    t = norm(text)
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Do re mi fa sol çal, do majör gam çal, la minör akor çal, enstrümanı org yap, çan, synth, gitar ya da piyano diyebilirsiniz. Klavyeden A S D F G H J tuşlarıyla da çalabilirsiniz."}
    for k in INSTR:
        if k in t and re.search(r"\b(yap|seç|geç|çal|olsun|enstrüman\w*)\b", t) and not _note_tokens(t):
            NT["inst"] = k
            return {"say": f"{k.capitalize()} sesi seçildi.", "do": {"inst": k}}
    root = re.search(r"\b(do|re|mi|fa|sol|la|si)\b(?:\s+(diyez|bemol))?\s+(majör|minör|pentatonik|blues|7|azaltılmış|sus)\b", t)
    if root and re.search(r"\bgam\b|\bakor\b|\bçal\b", t):
        base = 60 + NOTE_ST[root.group(1)] + (1 if root.group(2) == "diyez" else -1 if root.group(2) == "bemol" else 0)
        typ = root.group(3)
        if re.search(r"\bakor\b", t) and typ in CHORDS:
            ns = [base + i for i in CHORDS[typ]]
            return {"say": f"{root.group(1).capitalize()} {typ} akoru.", "do": {"chord": ns, "inst": NT["inst"]}}
        if typ in SCALES:
            return {"say": f"{root.group(1).capitalize()} {typ} gam.", "do": {"seq": [base + i for i in SCALES[typ]], "step": 0.28, "inst": NT["inst"]}}
    ns = _note_tokens(t)
    if ns and re.search(r"\b(çal|çalsana|oyna|söyle)\w*", t):
        return {"say": "", "do": {"seq": ns[:48], "step": 0.34, "inst": NT["inst"]}}
    if re.search(r"\bşarkı\w*|\bmelodi\w*", t):
        tune = {"ode": [64, 64, 65, 67, 67, 65, 64, 62, 60, 60, 62, 64, 64, 62, 62],
                "mary": [64, 62, 60, 62, 64, 64, 64, 62, 62, 62, 64, 67, 67]}
        k = "ode" if re.search(r"neşeye|ode|beethoven", t) else "mary"
        return {"say": "Bir melodi çalıyorum.", "do": {"seq": tune[k], "step": 0.4, "inst": NT["inst"]}}
    return {"say": "Notaları söyleyin efendim, örneğin do re mi çal.", "do": {"inst": NT["inst"]}}


# ======================================================================= MORS ATÖLYESİ
MORS = {"a": ".-", "b": "-...", "c": "-.-.", "ç": "-.-..", "d": "-..", "e": ".", "f": "..-.", "g": "--.", "ğ": "--.-.", "h": "....", "ı": "..", "i": ".-..-", "j": ".---",
        "k": "-.-", "l": ".-..", "m": "--", "n": "-.", "o": "---", "ö": "---.", "p": ".--.", "r": ".-.", "s": "...", "ş": ".--..", "t": "-", "u": "..-", "ü": "..--", "v": "...-",
        "y": "-.--", "z": "--..", "q": "--.-", "w": ".--", "x": "-..-",
        "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----."}
MORS["i"] = ".."          # Türk alfabesinde i = .. (ı = ..-..)
MORS["ı"] = "..-.."
REV = {v: k for k, v in MORS.items()}
M = {"wpm": 12, "q": None, "score": [0, 0]}


def _enc(s):
    s = s.replace("İ", "i").replace("I", "ı").lower()
    return " ".join("/" if c == " " else MORS[c] for c in s if c == " " or c in MORS)


def mors(text, st):
    t = norm(text)
    raw = text.strip()
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Mors yaz iki nokta merhaba, mors çöz iki nokta nokta çizgi, hız on beş, alfabeyi göster, harf sor ve cevap k diyebilirsiniz."}
    m = re.search(r"\bhız\w*\s*(\d+)|\b(\d+)\s*(wpm|kelime)", t)
    if m:
        M["wpm"] = max(5, min(30, int(m.group(1) or m.group(2))))
        return {"say": f"Hız dakikada {M['wpm']} kelime.", "do": {"wpm": M["wpm"]}}
    if re.search(r"\balfabe\w*|\btablo\w*", t):
        return {"say": "Alfabe ekranda efendim.", "do": {"table": True}}
    if re.search(r"\bçöz\w*", t):
        body = _after_colon(raw) or re.sub(r"(?i).*çöz\w*\s*", "", raw)
        codes = re.findall(r"[.\-·–—_]+|/", body)
        out = "".join(" " if c == "/" else REV.get(c.replace("·", ".").replace("–", "-").replace("—", "-").replace("_", "-"), "?") for c in codes)
        return {"say": f"Çözüm: {out}" if out.strip() else "Çözülecek kod bulamadım efendim.", "do": {"decoded": out}}
    if re.search(r"\bharf sor\w*|\btest\w*|\bsınav\w*|\bsoru\w*", t) and not _after_colon(raw):
        c = random.choice([x for x in MORS if x.isalpha()])
        M["q"] = c
        return {"say": "Dinleyin ve hangi harf olduğunu söyleyin efendim.", "do": {"quiz": {"code": MORS[c]}, "score": M["score"]}}
    m = re.search(r"\bcevap\w*\s+(\w)\b", t) or (re.fullmatch(r"(\w)", t) if M["q"] else None)
    if m and M["q"]:
        guess = m.group(1)
        ok = guess == M["q"]
        M["score"][0 if ok else 1] += 1
        ans = M["q"]
        M["q"] = None
        return {"say": ("Doğru efendim." if ok else f"Yanlış, cevap {ans.upper()} idi."), "do": {"reveal": ans, "ok": ok, "score": M["score"]}}
    body = _after_colon(raw) or re.sub(r"(?i)^(jarvis\W+)?(mors|yaz|çal|gönder)\w*\s*", "", raw)
    code = _enc(body)
    if not code:
        return {"say": "Morsa çevirecek bir metin söyleyin efendim. Mors yaz iki nokta merhaba."}
    return {"say": "", "do": {"text": body[:80], "code": code, "wpm": M["wpm"], "play": True}}


# ======================================================================= RENK ATÖLYESİ
MOODS = {
    "sakin": (200, 0.35, .62, 40), "huzur": (200, .35, .62, 40), "okyanus": (200, .6, .5, 35), "deniz": (195, .6, .5, 35), "orman": (130, .45, .38, 40),
    "doğa": (110, .4, .45, 45), "gün batımı": (18, .8, .58, 40), "enerjik": (15, .9, .55, 140), "neon": (300, 1, .55, 220), "pastel": (330, .55, .84, 60),
    "toprak": (28, .45, .42, 30), "gece": (250, .55, .25, 40), "romantik": (345, .6, .6, 30), "retro": (35, .7, .6, 140), "kış": (205, .25, .75, 30),
    "sonbahar": (25, .65, .45, 28), "yaz": (48, .85, .58, 90), "kahve": (25, .45, .28, 20), "uzay": (265, .6, .3, 100), "lavanta": (270, .4, .7, 25),
}


def _hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, max(0, min(1, l)), max(0, min(1, s)))
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def _pal_mood(key):
    h, s, l, spread = MOODS[key]
    out = []
    for i in range(5):
        out.append(_hex(h + random.uniform(-spread, spread) + i * 6, s + random.uniform(-.15, .15), l + (i - 2) * .09 + random.uniform(-.05, .05)))
    return out


def _harm(hexc, kind):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    h *= 360
    offs = {"tamamlayıcı": [0, 180], "üçlü": [0, 120, 240], "dörtlü": [0, 90, 180, 270], "benzer": [-30, 0, 30], "bölünmüş": [0, 150, 210]}[kind]
    out = [_hex(h + o, s, l) for o in offs]
    out += [_hex(h, s, min(.92, l + .25)), _hex(h, s, max(.1, l - .25))]
    return out[:6]


RN = D.setdefault("renk", {"saved": [], "cur": None})
RN.setdefault("saved", [])


def _renk_snap():
    return {"saved": RN["saved"][-12:][::-1], "cur": RN.get("cur"), "moods": list(MOODS)}


COLORS = {"kırmızı": "#e53935", "turuncu": "#fb8c00", "sarı": "#fdd835", "yeşil": "#43a047", "mavi": "#1e88e5", "mor": "#8e24aa", "pembe": "#ec407a", "turkuaz": "#26c6da",
          "lacivert": "#1a237e", "kahverengi": "#6d4c41", "siyah": "#212121", "beyaz": "#fafafa", "gri": "#9e9e9e"}


def renk(text, st):
    t = norm(text)
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Sakin palet, gün batımı paleti, neon, pastel, okyanus, orman gibi bir ruh hali söyleyin. Kırmızı için üçlü uyum, mavi için tamamlayıcı renkler, rastgele palet, paleti kaydet de diyebilirsiniz."}
    if re.search(r"\bkaydet\w*", t) and RN.get("cur"):
        RN["saved"].append(RN["cur"])
        del RN["saved"][:-40]
        _save()
        return {"say": "Palet kaydedildi efendim.", "do": {"snap": _renk_snap()}}
    hm = re.search(r"#?([0-9a-f]{6})\b", text.lower())
    base = ("#" + hm.group(1)) if hm and re.search(r"[0-9]", hm.group(1)) else next((v for k, v in COLORS.items() if k in t), None)
    kind = next((k for k in ("tamamlayıcı", "üçlü", "dörtlü", "benzer", "bölünmüş") if k in t), None) or ("tamamlayıcı" if re.search(r"\bzıt\b|\bkarşıt\b", t) else None)
    if base and (kind or re.search(r"\buyum\w*|\bpalet\w*|\brenk\w*", t)):
        kind = kind or "benzer"
        cols = _harm(base, kind)
        RN["cur"] = {"ad": f"{kind.capitalize()} uyum", "c": cols}
        return {"say": f"{kind.capitalize()} uyum paleti hazır.", "do": {"pal": RN["cur"], "snap": _renk_snap()}}
    for k in sorted(MOODS, key=len, reverse=True):
        if k in t:
            RN["cur"] = {"ad": k.capitalize(), "c": _pal_mood(k)}
            return {"say": f"{k.capitalize()} paleti hazır.", "do": {"pal": RN["cur"], "snap": _renk_snap()}}
    k = random.choice(list(MOODS))
    RN["cur"] = {"ad": k.capitalize() + " (rastgele)", "c": _pal_mood(k)}
    return {"say": "Rastgele bir palet.", "do": {"pal": RN["cur"], "snap": _renk_snap()}}


# ======================================================================= ZEN KUM BAHÇESİ
KM = {"rake": "düz", "stones": 3}


def kum(text, st):
    t = norm(text)
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Fareyle kumu tırmıklayın. Taş ekle, taşları azalt, tırmığı dalga yap, daire yap, çift çizgi, temizle ya da yeni bahçe diyebilirsiniz."}
    if re.search(r"\btemizle\w*|\bsıfırla\w*|\bdüzle\w*", t):
        return {"say": "Kum düzlendi efendim.", "do": {"clear": True}}
    if re.search(r"\byeni bahçe\w*|\brastgele\b", t):
        KM["stones"] = random.randint(2, 5)
        return {"say": "Yeni bir bahçe.", "do": {"clear": True, "stones": KM["stones"], "reroll": True}}
    if re.search(r"\btaş\w*", t) and re.search(r"\b(ekle|koy|fazla|artır)\w*", t):
        KM["stones"] = min(9, KM["stones"] + 1)
        return {"say": "", "do": {"stones": KM["stones"], "reroll": False}}
    if re.search(r"\btaş\w*", t) and re.search(r"\b(azalt|çıkar|kaldır|sil)\w*", t):
        KM["stones"] = max(0, KM["stones"] - 1)
        return {"say": "", "do": {"stones": KM["stones"], "reroll": False}}
    for k in ("düz", "dalga", "daire", "çift"):
        if k in t:
            KM["rake"] = k
            return {"say": f"Tırmık: {k}.", "do": {"rake": k}}
    return {"say": "Sakin olun efendim; fareyle kuma çizin.", "do": {"rake": KM["rake"]}}


# ======================================================================= SİMYA ATÖLYESİ
EL = {"ateş": "🔥", "su": "💧", "toprak": "🌍", "hava": "💨", "buhar": "♨️", "çamur": "🟤", "lav": "🌋", "duman": "🌫️", "toz": "✨", "bulut": "☁️", "yağmur": "🌧️",
      "rüzgar": "🌬️", "göl": "🏞️", "dağ": "⛰️", "yangın": "🚒", "deniz": "🌊", "okyanus": "🐋", "kum": "🏖️", "çöl": "🏜️", "cam": "🔍", "taş": "🪨", "metal": "⚙️",
      "kılıç": "🗡️", "tuğla": "🧱", "ev": "🏠", "köy": "🏘️", "şehir": "🏙️", "bitki": "🌱", "ağaç": "🌳", "orman": "🌲", "odun": "🪵", "kömür": "⚫", "elmas": "💎",
      "kağıt": "📄", "kitap": "📖", "çiçek": "🌸", "arı": "🐝", "bal": "🍯", "enerji": "🔋", "şimşek": "⚡", "elektrik": "💡", "ampul": "🔆", "hayat": "🧬", "balık": "🐟",
      "kuş": "🐦", "hayvan": "🦊", "insan": "🧑", "çiftlik": "🚜", "tekerlek": "🛞", "araba": "🚗", "gemi": "🚢", "uçak": "✈️", "roket": "🚀", "gökyüzü": "🌌", "güneş": "☀️",
      "gökkuşağı": "🌈", "buz": "🧊", "kar": "❄️", "kardan adam": "⛄", "müzik": "🎵", "gitar": "🎸", "şarkı": "🎤", "bilgisayar": "💻", "internet": "🌐",
      "yapay zeka": "🤖", "jarvis": "🦾", "uzay": "🪐", "ay": "🌙", "yıldız": "⭐", "gezegen": "🪐", "robot": "🤖", "fener": "🏮", "ışık": "💫", "ekmek": "🍞", "un": "🌾", "buğday": "🌾"}
COMBO = [("su", "ateş", "buhar"), ("su", "toprak", "çamur"), ("ateş", "toprak", "lav"), ("ateş", "hava", "duman"), ("toprak", "hava", "toz"), ("buhar", "hava", "bulut"),
         ("bulut", "su", "yağmur"), ("hava", "hava", "rüzgar"), ("su", "su", "göl"), ("toprak", "toprak", "dağ"), ("ateş", "ateş", "yangın"), ("göl", "su", "deniz"),
         ("deniz", "deniz", "okyanus"), ("toprak", "rüzgar", "kum"), ("kum", "kum", "çöl"), ("kum", "ateş", "cam"), ("lav", "su", "taş"), ("taş", "ateş", "metal"),
         ("metal", "taş", "kılıç"), ("çamur", "ateş", "tuğla"), ("tuğla", "tuğla", "ev"), ("ev", "ev", "köy"), ("köy", "köy", "şehir"), ("toprak", "yağmur", "bitki"),
         ("bitki", "bitki", "ağaç"), ("ağaç", "ağaç", "orman"), ("ağaç", "kılıç", "odun"), ("odun", "ateş", "kömür"), ("kömür", "dağ", "elmas"), ("odun", "su", "kağıt"),
         ("kağıt", "kağıt", "kitap"), ("bitki", "güneş", "çiçek"), ("çiçek", "hava", "arı"), ("arı", "ağaç", "bal"), ("ateş", "rüzgar", "enerji"), ("bulut", "enerji", "şimşek"),
         ("şimşek", "metal", "elektrik"), ("elektrik", "cam", "ampul"), ("çamur", "şimşek", "hayat"), ("hayat", "göl", "balık"), ("hayat", "hava", "kuş"), ("hayat", "orman", "hayvan"),
         ("hayvan", "ateş", "insan"), ("insan", "bitki", "çiftlik"), ("odun", "taş", "tekerlek"), ("tekerlek", "metal", "araba"), ("odun", "deniz", "gemi"), ("metal", "kuş", "uçak"),
         ("uçak", "ateş", "roket"), ("hava", "bulut", "gökyüzü"), ("ateş", "gökyüzü", "güneş"), ("yağmur", "güneş", "gökkuşağı"), ("su", "rüzgar", "buz"), ("bulut", "buz", "kar"),
         ("kar", "insan", "kardan adam"), ("insan", "rüzgar", "müzik"), ("odun", "müzik", "gitar"), ("insan", "müzik", "şarkı"), ("elektrik", "insan", "bilgisayar"),
         ("bilgisayar", "bilgisayar", "internet"), ("bilgisayar", "hayat", "yapay zeka"), ("yapay zeka", "insan", "jarvis"), ("roket", "gökyüzü", "uzay"), ("taş", "gökyüzü", "ay"),
         ("uzay", "ateş", "yıldız"), ("toprak", "uzay", "gezegen"), ("elektrik", "insan", "robot"), ("ampul", "ateş", "fener"), ("güneş", "cam", "ışık"), ("bitki", "kum", "buğday"),
         ("buğday", "taş", "un"), ("un", "ateş", "ekmek")]
LOOK = {}
for _a, _b, _r in COMBO:
    LOOK[frozenset((_a, _b))] = _r
SY = D.setdefault("simya", {"found": ["ateş", "su", "toprak", "hava"]})


def _sy_snap():
    return {"found": [{"ad": k, "e": EL.get(k, "◆")} for k in SY["found"]], "total": len(set(LOOK.values())) + 4, "n": len(SY["found"])}


def _find_names(t):
    names = sorted(EL, key=len, reverse=True)
    out = []
    rest = t
    for n in names:
        stem = n if len(n) <= 3 else n[:-1] if len(n) > 4 else n
        for m in re.finditer(rf"(?:^|\s){re.escape(stem)}\w*", rest):
            out.append((m.start(), n))
        rest = re.sub(rf"(?:^|\s){re.escape(stem)}\w*", lambda m: " " * len(m.group()), rest)
    return [n for _, n in sorted(out)]


def simya(text, st):
    t = norm(text)
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "İki öğeyi sayfada tıklayın ya da ateş ile suyu birleştir deyin. İpucu ver, keşfettiklerim ve sıfırla da var. Hedef: hepsini keşfetmek."}
    if re.search(r"\bsıfırla\w*|\bbaştan\b", t):
        SY["found"] = ["ateş", "su", "toprak", "hava"]
        _save()
        return {"say": "Simya defteri sıfırlandı efendim.", "do": {"snap": _sy_snap()}}
    if re.search(r"\bipucu\w*|\bnasıl\b|\bnapayım", t):
        opts = [(a, b, r) for a, b, r in COMBO if r not in SY["found"] and a in SY["found"] and b in SY["found"]]
        if not opts:
            return {"say": "Elinizdeki öğelerle yeni bir şey göremiyorum, belki aynı öğeyi ikiye katlamayı deneyin."}
        a, b, r = random.choice(opts)
        return {"say": f"{a.capitalize()} ile {b} birleştirmeyi deneyin.", "do": {"hint": [a, b]}}
    if re.search(r"\bkeşfet\w*|\bneler var|\bkaç\b|\bdefter\w*", t) and not re.search(r"\bbirleştir|\bkarıştır", t):
        s = _sy_snap()
        return {"say": f"{s['n']} öğeden {s['total']} tanesini keşfettiniz efendim.", "do": {"snap": s}}
    ns = _find_names(t)
    if len(ns) == 1 and re.search(r"\b(ikiye|kendisiyle|iki kez|katla)\w*", t):
        ns = ns * 2
    if len(ns) >= 2:
        a, b = ns[0], ns[1]
        if a not in SY["found"] or b not in SY["found"]:
            return {"say": f"{(a if a not in SY['found'] else b).capitalize()} henüz keşfedilmedi efendim."}
        r = LOOK.get(frozenset((a, b)))
        if not r:
            return {"say": f"{a.capitalize()} ile {b} bir şey oluşturmadı.", "do": {"fail": [a, b]}}
        new = r not in SY["found"]
        if new:
            SY["found"].append(r)
            _save()
        return {"say": (f"Yeni keşif: {r}!" if new else f"{r.capitalize()} zaten elinizde."), "do": {"made": {"ad": r, "e": EL.get(r, "◆"), "new": new}, "snap": _sy_snap()}}
    return {"say": "İki öğe söyleyin efendim, örneğin ateş ile suyu birleştir."}


# ======================================================================= ZAMAN KAPSÜLÜ
KS = D.setdefault("kapsul", [])
UNIT = {"gün": 1, "hafta": 7, "ay": 30, "yıl": 365, "sene": 365}


def _ks_when(t):
    m = re.search(r"(\d+|bir|iki|üç|dört|beş|altı|yedi|sekiz|dokuz|on|yirmi)?\s*(gün|hafta|ay|yıl|sene)\w*\s+sonra", t) or re.search(r"\b(yarın|haftaya|seneye|gelecek yıl)\b", t)
    today = datetime.date.today()
    if m and m.re.pattern.startswith("(\\d"):
        n = m.group(1)
        n = int(n) if n and n.isdigit() else ({**NUM_W, "yirmi": 20}.get(n, 1) if n else 1)
        u = m.group(2)
        if u == "ay":
            mo = today.month - 1 + n
            return datetime.date(today.year + mo // 12, mo % 12 + 1, min(today.day, 28))
        if u in ("yıl", "sene"):
            return datetime.date(today.year + n, today.month, min(today.day, 28))
        return today + datetime.timedelta(days=n * UNIT[u])
    if m:
        w = m.group(1)
        return today + datetime.timedelta(days={"yarın": 1, "haftaya": 7}.get(w, 365))
    m = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", t)
    if m:
        try:
            return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


def _ks_snap():
    today = datetime.date.today()
    rows = []
    for i, k in enumerate(KS):
        dd = datetime.date.fromisoformat(k["open"])
        due = dd <= today
        rows.append({"i": i, "from": k["from"], "open": dd.strftime("%d.%m.%Y"), "days": (dd - today).days, "due": due, "read": bool(k.get("read")),
                     "text": k["text"] if due else None})
    return {"rows": rows}


def kapsul(text, st):
    t = norm(text)
    raw = text.strip()
    today = datetime.date.today()
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Geleceğe mesaj iki nokta bir yıl sonra bunu okuyacaksın diyerek yazın; tarih için gün, hafta, ay ya da yıl sonra söyleyin. Açılan kapsülleri okumak için kapsülleri aç deyin. Metinler vakti gelene kadar ekranda gizli kalır."}
    if re.search(r"\b(kapsüll\w*|kapsülü) (aç|oku|göster)\w*|\baçılan\w*|\bvakti gelen\w*", t):
        due = [k for k in KS if datetime.date.fromisoformat(k["open"]) <= today]
        if not due:
            return {"say": "Vakti gelmiş bir kapsül yok efendim.", "do": {"snap": _ks_snap()}}
        for k in due:
            k["read"] = True
        _save()
        k = due[0]
        return {"say": f"{k['from']} tarihli kapsül: {k['text'][:300]}", "do": {"snap": _ks_snap(), "confetti": True}}
    m = re.search(r"\b(\d+)\. kapsül\w*\s*(sil)\w*|\bkapsül\w* sil\w*", t)
    if m:
        if not KS:
            return {"say": "Silinecek kapsül yok efendim."}
        n = int(m.group(1)) - 1 if m.group(1) else len(KS) - 1
        if not 0 <= n < len(KS):
            return {"say": "Böyle bir kapsül yok efendim."}
        if datetime.date.fromisoformat(KS[n]["open"]) > today and "onay" not in t:
            return {"say": "Mühürlü bir kapsülü silmek için kapsülü sil onay diyin efendim, geri dönüşü yok."}
        KS.pop(n)
        _save()
        return {"say": "Kapsül silindi efendim.", "do": {"snap": _ks_snap()}}
    body = _after_colon(raw)
    mt = re.search(r"[,;.]?\s*((?:\d+|bir|iki|üç|dört|beş|altı|yedi|sekiz|dokuz|on|yirmi)?\s*(?:gün|hafta|ay|yıl|sene)\w*\s+sonra|yarın|haftaya|seneye|gelecek yıl|\d{1,2}[./]\d{1,2}[./]\d{4})\W*$", body, re.I)
    if mt:                                       # tarih ifadesi mesajın SONUNDAKİ kısımdır; mesaj metni içindeki "5 gün sonra" yanlış okunmasın
        when = _ks_when(norm(mt.group(1)))
        body = body[:mt.start()].strip()
    else:
        when = _ks_when(t)
    if re.search(r"\b(geleceğe|gelecekteki|kapsül\w*|mühürle|mesaj)\w*", t) and body:
        if not when or when <= today:
            return {"say": "Ne zaman açılsın efendim? Örneğin bir yıl sonra ya da altı ay sonra deyin."}
        KS.append({"from": today.strftime("%d.%m.%Y"), "open": when.isoformat(), "text": body[:2000]})
        _save()
        return {"say": f"Kapsül mühürlendi, {when.strftime('%d.%m.%Y')} tarihinde açılacak efendim.", "do": {"snap": _ks_snap(), "seal": True}}
    return {"say": "Geleceğe mesaj iki nokta, mesajınız, bir yıl sonra diyerek mühürleyin efendim.", "do": {"snap": _ks_snap()}}


# ======================================================================= HİKÂYE ZARLARI
DICE = {
    "karakter": ["yaşlı bir deniz feneri bekçisi", "konuşan bir kedi", "emekli bir hırsız", "yolunu kaybetmiş bir robot", "gezgin bir aşçı", "uykusuz bir saatçi", "çocuk bir kaşif",
                 "unutkan bir büyücü", "gece vardiyası şoförü", "son kitapçı", "gölge avcısı", "mahcup bir ejderha"],
    "mekan": ["terk edilmiş bir tren istasyonu", "bulutların üstünde bir pazar", "dipsiz bir kütüphane", "yağmurda kalmış bir liman kasabası", "ay ışığında bir çöl", "yeraltı çay bahçesi",
              "dönen bir gökdelen", "sisli bir orman", "kayıp bir adada bir radyo istasyonu", "sonsuz bir asansör"],
    "nesne": ["paslı bir anahtar", "yarım kalmış bir harita", "tik tak eden bir kutu", "cebinde bir mektup", "ışıldayan bir taş", "çalmayan bir telefon", "tek ayakkabı", "solmayan bir gül",
              "yanlış saat gösteren bir saat", "mühürlü bir şişe"],
    "sorun": ["herkes bir şeyi unutmuş", "bir gece boyunca saat durmuş", "kapı hiçbir yere açılmıyor", "biri yanlış kişiyle karıştırılmış", "ses tamamen kaybolmuş", "bir söz tutulmamış",
              "harita sürekli değişiyor", "sır açığa çıkmak üzere"],
    "tur": ["gizem", "fantastik", "bilim kurgu", "komedi", "masal", "gerilim", "dramatik", "tatlı bir macera"],
}
HK = D.setdefault("hikaye", {"dice": {}, "story": "", "log": []})
LOCK = set()


def _roll(which=None):
    dd = HK["dice"]
    for k in DICE:
        if (which is None or k in which) and k not in LOCK:
            dd[k] = random.choice(DICE[k])
        elif k not in dd:
            dd[k] = random.choice(DICE[k])


def _hk_snap():
    return {"dice": HK["dice"], "story": HK.get("story", ""), "lock": sorted(LOCK), "saved": len(HK.get("log", []))}


def _llm_story(kind, prompt, cont):
    def work():
        s = _ask_llm(prompt, "Sen yaratıcı bir Türkçe hikâye yazarısın. Kısa, görsel ve akıcı yaz. Başlık ve açıklama ekleme.")
        if not s:
            _push("hikaye", {"msg": "Hikâye için yerel model açık değil efendim; zarlar yine de ilham verir."})
            return
        HK["story"] = (HK.get("story", "") + "\n\n" + s.strip()) if cont and HK.get("story") else s.strip()
        HK["log"] = (HK.get("log", []) + [HK["story"][:1500]])[-12:]
        _save()
        _push("hikaye", {"snap": _hk_snap(), "msg": "Hikâye hazır."})
        if SAY:
            try:
                SAY("Hikâye hazır efendim. İsterseniz devam et deyin.", "hikaye")
            except Exception:
                pass
    _bg(kind, work)


def hikaye(text, st):
    t = norm(text).replace("â", "a")
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Zar at, karakteri değiştir, mekanı kilitle, bu zarlarla hikâye yaz, devam et ve hikâyeyi sıfırla diyebilirsiniz."}
    if not HK["dice"]:
        _roll()
    names = {"karakter": "karakter", "mekan": "mekan", "mekân": "mekan", "nesne": "nesne", "sorun": "sorun", "tür": "tur", "tur": "tur"}
    hit = [v for k, v in names.items() if re.search(rf"\b{k}\w*", t)]
    if re.search(r"\bkilit\w* (aç|kaldır)\w*", t):
        LOCK.clear()
        return {"say": "Kilitler açıldı.", "do": {"snap": _hk_snap()}}
    if re.search(r"\bkilitle\w*|\bsabitle\w*", t) and hit:
        LOCK.update(hit)
        return {"say": f"{hit[0].capitalize()} kilitlendi.", "do": {"snap": _hk_snap()}}
    if re.search(r"\bsıfırla\w*|\byeni hikaye\w*|\bhikayeyi sil\w*", t) and "zar" not in t:
        HK["story"] = ""
        return {"say": "Hikâye temizlendi.", "do": {"snap": _hk_snap()}}
    if re.search(r"\bdevam\w*|\bsonra ne\w*", t) and HK.get("story"):
        _llm_story("hikaye", "Şu hikâyeye devam et, 1-2 paragraf yaz, sonu açık bırak:\n\n" + HK["story"][-1800:], True)
        return {"say": "Devam ediyorum efendim."}
    if re.search(r"\bhikaye\w*|\bmasal\w*|\byaz\b", t):
        d = HK["dice"]
        p = (f"Şu unsurlarla {d['tur']} türünde kısa bir hikâye yaz (3 paragraf): karakter: {d['karakter']}; mekân: {d['mekan']}; nesne: {d['nesne']}; sorun: {d['sorun']}.")
        HK["story"] = ""
        _llm_story("hikaye", p, False)
        return {"say": "Hikâyeyi yazıyorum efendim, birkaç saniye sürer."}
    _roll(hit or None)
    d = HK["dice"]
    return {"say": f"{d['karakter'].capitalize()}, {d['mekan']}, {d['nesne']}.", "do": {"snap": _hk_snap(), "roll": True}}


# ======================================================================= ORTAK
HANDLERS = {"ruya": ruya, "nefes": nefes, "ritim": ritim, "nota": nota, "mors": mors, "renk": renk, "kum": kum, "simya": simya, "kapsul": kapsul, "hikaye": hikaye}
TITLES = {"ruya": "JARVIS RÜYA GÜNLÜĞÜ", "nefes": "JARVIS NEFES REHBERİ", "ritim": "JARVIS RİTİM STÜDYOSU", "nota": "JARVIS MÜZİK KUTUSU", "mors": "JARVIS MORS ATÖLYESİ",
          "renk": "JARVIS RENK ATÖLYESİ", "kum": "JARVIS ZEN BAHÇESİ", "simya": "JARVIS SİMYA ATÖLYESİ", "kapsul": "JARVIS ZAMAN KAPSÜLÜ", "hikaye": "JARVIS HİKÂYE ZARLARI"}
EXIT = {"ruya": "Rüya günlüğü kapandı efendim, kayıtlarınız duruyor.", "nefes": "Nefes rehberi kapandı efendim.", "ritim": "Ritim stüdyosu kapandı efendim.",
        "nota": "Müzik kutusu kapandı efendim.", "mors": "Mors atölyesi kapandı efendim.", "renk": "Renk atölyesi kapandı efendim.", "kum": "Zen bahçesi kapandı efendim.",
        "simya": "Simya atölyesi kapandı efendim, keşifleriniz kayıtlı.", "kapsul": "Zaman kapsülü kapandı efendim, mühürler yerinde.", "hikaye": "Hikâye zarları kapandı efendim."}


def init_payload(kind):
    if kind == "ruya":
        return {"snap": _ruya_snap()}
    if kind == "nefes":
        N["on"] = False
        return _nefes_do()
    if kind == "ritim":
        R["play"] = False
        return {"snap": _r_snap()}
    if kind == "nota":
        return {"inst": NT["inst"]}
    if kind == "mors":
        M["q"] = None
        return {"wpm": M["wpm"], "table": {k: v for k, v in MORS.items()}, "score": M["score"]}
    if kind == "renk":
        if not RN.get("cur"):
            RN["cur"] = {"ad": "Okyanus", "c": _pal_mood("okyanus")}
        return {"snap": _renk_snap(), "pal": RN["cur"]}
    if kind == "kum":
        return {"rake": KM["rake"], "stones": KM["stones"]}
    if kind == "simya":
        return {"snap": _sy_snap(), "emoji": EL}
    if kind == "kapsul":
        return {"snap": _ks_snap()}
    if kind == "hikaye":
        _roll()
        return {"snap": _hk_snap()}
    return {}


def register():
    """scenes.py sonundan çağrılır: sahne sözlüklerine kaydeder."""
    for k in KINDS:
        scenes.HANDLERS[k] = HANDLERS[k]
        scenes.INITS[k] = (lambda kk=k: init_payload(kk))
        scenes.TITLES[k] = TITLES[k]
        scenes.EXIT_SAY[k] = EXIT[k]
