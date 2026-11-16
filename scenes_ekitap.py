"""E-kitap modu (kind "ekitap"): kitap adını söylersiniz, kamu malı (telifi bitmiş) eserlerin tam metnini internetten bulur, sayfalara böler ve
sayfa çevirme animasyonlu bir kitap olarak gösterir. Kaynaklar: Project Gutenberg (gutendex.com arama ucu) ve Türkçe Vikikaynak (tr.wikisource.org).
Telif hakkı süren kitaplar ARANMAZ/ÇEKİLMEZ; bulunamazsa bunu açıkça söyler. İstek yalnızca GET'tir ve yalnızca kitap adını taşır (kişisel veri yok).
Metin ekitap_cache/ içinde önbelleğe alınır, kitaplık ve okuma yeri ekitap_data.json'dadır (ikisi de gitignored). Sayfa 1000 karakterdir; yazı boyutunu sayfa verir."""
import hashlib
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request

import scenes
from scenes import norm

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "ekitap_cache")
FILE = os.path.join(HERE, "ekitap_data.json")
NOTIFY = None          # main bağlar: NOTIFY(kind, do)
UA = "JarvisEbook/1.0 (kamu mali eser okuyucu)"
PAGE_CH = 1000
CAP = 4_000_000        # karakter üst sınırı
_lk = threading.Lock()
B = {"id": None, "title": "", "author": "", "src": "", "pages": [], "pos": 0}
CAND = []              # son arama adayları
LASTQ = {"q": ""}
BUSY = {"on": False}


def _load():
    try:
        with open(FILE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


D = _load()
D.setdefault("lib", {})


def _save():
    with _lk:
        try:
            with open(FILE + ".tmp", "w", encoding="utf-8") as f:
                json.dump(D, f, ensure_ascii=False, indent=1)
            os.replace(FILE + ".tmp", FILE)
        except OSError:
            pass


def _push(do):
    if NOTIFY:
        try:
            NOTIFY("ekitap", do)
        except Exception:
            pass


def _get(url, timeout=25, maxb=12_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "tr,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(maxb)


# ---------------------------------------------------------------- kaynaklar
def _gutenberg_site(q):
    """gutenberg.org'un kendi arama sayfası (Gutendex bazı sorgularda zaman aşımına düşüyor; bu hızlı ve kararlı)."""
    out = []
    try:
        h = _get("https://www.gutenberg.org/ebooks/search/?" + urllib.parse.urlencode({"query": q, "submit_search": "Go!"}), 12).decode("utf-8", "replace")
    except Exception:
        return out
    for m in re.finditer(r'<li class="booklink">\s*<a class="link" href="/ebooks/(\d+)".*?<span class="title">(.*?)</span>(?:\s*<span class="subtitle">(.*?)</span>)?', h, re.S):
        title = re.sub(r"<.*?>|&amp;", lambda x: "&" if x.group() == "&amp;" else "", m.group(2)).strip()
        out.append({"src": "gutenberg", "id": "pg" + m.group(1), "title": title[:120], "author": (m.group(3) or "").strip()[:80],
                    "url": f"https://www.gutenberg.org/ebooks/{m.group(1)}.txt.utf-8", "lang": ""})
        if len(out) >= 8:
            break
    return out


def _gutenberg(q):
    out = _gutenberg_site(q)
    if out:
        return out
    try:
        j = json.loads(_get("https://gutendex.com/books/?" + urllib.parse.urlencode({"search": q}), 7).decode("utf-8", "replace"))
    except Exception:
        return out
    for b in j.get("results", [])[:8]:
        fm = b.get("formats", {})
        url = next((v for k, v in fm.items() if k.startswith("text/plain") and not v.endswith(".zip")), None)
        if not url:
            continue
        au = ", ".join(a.get("name", "") for a in b.get("authors", [])[:2])
        out.append({"src": "gutenberg", "id": "pg%d" % b["id"], "title": b.get("title", "?")[:120], "author": au, "url": url,
                    "lang": ",".join(b.get("languages", []))})
    return out


def _gutenberg_multi(q):
    """Tam adla ve her uzun sözcükle AYNI ANDA arar (Gutendex tüm sözcükleri ister; Türkçe eklerle tam ad tutmayabilir), başlık eşleşmesine göre sıralar."""
    words = [w for w in q.split() if len(w) >= 4][:4]
    res = {}

    def run(k, qq):
        res[k] = _gutenberg(qq)
    th = [threading.Thread(target=run, args=(i, qq), daemon=True) for i, qq in enumerate([q] + words)]
    for x in th:
        x.start()
    for x in th:
        x.join(9)
    seen, out = set(), []
    for k in sorted(res):
        for c in res[k]:
            if c["id"] not in seen:
                seen.add(c["id"])
                out.append(c)
    stems = [w[:5] for w in words]
    out.sort(key=lambda c: -sum(1 for st in stems if st in norm(c["title"])))
    return out


def _wikisource(q):
    out = []
    try:
        u = "https://tr.wikisource.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": q, "srlimit": 5, "format": "json"})
        j = json.loads(_get(u).decode("utf-8", "replace"))
    except Exception:
        return out
    for h in j.get("query", {}).get("search", []):
        t = h.get("title", "")
        if "/" in t or ":" in t:
            continue
        out.append({"src": "wikisource", "id": "ws" + hashlib.md5(t.encode()).hexdigest()[:10], "title": t, "author": "Vikikaynak", "url": t, "lang": "tr"})
    return out


def _ws_text(title):
    def ext(t):
        u = "https://tr.wikisource.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "prop": "extracts", "explaintext": 1, "titles": t, "format": "json", "redirects": 1})
        j = json.loads(_get(u).decode("utf-8", "replace"))
        for p in j.get("query", {}).get("pages", {}).values():
            return p.get("extract", "") or ""
        return ""
    main = ext(title)
    parts = [main]
    try:
        u = "https://tr.wikisource.org/w/api.php?" + urllib.parse.urlencode({"action": "query", "list": "allpages", "apprefix": title + "/", "aplimit": 60, "format": "json"})
        subs = [p["title"] for p in json.loads(_get(u).decode("utf-8", "replace")).get("query", {}).get("allpages", [])]
        for s in subs:
            parts.append("\n\n" + s.split("/")[-1].upper() + "\n\n" + ext(s))
            if sum(len(x) for x in parts) > CAP:
                break
    except Exception:
        pass
    return "\n\n".join(x for x in parts if x.strip())


def _clean_pg(txt):
    txt = txt.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    m = re.search(r"\*\*\* ?START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", txt, re.S | re.I)
    if m:
        txt = txt[m.end():]
    m = re.search(r"\*\*\* ?END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", txt, re.I)
    if m:
        txt = txt[:m.start()]
    return txt.strip()


def _paginate(txt):
    paras = [re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n\s*\n", txt.replace("\r", ""))]
    paras = [p for p in paras if p]
    pages, cur = [], ""
    for p in paras:
        while len(p) > PAGE_CH:
            room = PAGE_CH - len(cur) - 2
            if room < 200:
                pages.append(cur)
                cur, room = "", PAGE_CH
            cut = p.rfind(" ", 0, room)
            cut = cut if cut > room * .5 else room
            cur = (cur + "\n\n" if cur else "") + p[:cut]
            p = p[cut:].lstrip()
            pages.append(cur)
            cur = ""
        if len(cur) + len(p) + 2 > PAGE_CH and cur:
            pages.append(cur)
            cur = ""
        cur = (cur + "\n\n" if cur else "") + p
    if cur:
        pages.append(cur)
    return pages


def _fetch_text(c):
    os.makedirs(CACHE, exist_ok=True)
    cp = os.path.join(CACHE, c["id"] + ".txt")
    if os.path.exists(cp):
        with open(cp, encoding="utf-8") as f:
            return f.read()
    if c["src"] == "gutenberg":
        raw = _get(c["url"], 60)
        try:
            txt = raw.decode("utf-8")
        except UnicodeDecodeError:
            txt = raw.decode("latin-1")
        txt = _clean_pg(txt)
    else:
        txt = _ws_text(c["url"])
    txt = txt[:CAP]
    if len(txt) > 2000:
        with open(cp, "w", encoding="utf-8") as f:
            f.write(txt)
    return txt


# ---------------------------------------------------------------- Türkçeye çeviri (yerel Ollama, sayfa sayfa, okunan yerden ileri doğru)
TR = {"on": True, "gen": 0}
SYS_TR = ("Sen deneyimli bir edebiyat çevirmenisin. Verilen metni akıcı, doğal ve edebi bir Türkçeye çevir. Anlamı ve üslubu koru, hiçbir şey ekleme ya da çıkarma. "
          "Paragrafları aynen koru (boş satırla ayrılmış kalsın). Yalnızca çeviriyi yaz; açıklama, not ya da başlık ekleme.")


def _needs_tr():
    return bool(B["pages"]) and B.get("lang", "") != "tr"


def _tr_path(bid):
    return os.path.join(CACHE, bid + ".tr.json")


def _tr_load(bid):
    try:
        with open(_tr_path(bid), encoding="utf-8") as f:
            d = json.load(f)
        return {int(k): v for k, v in d.items()}
    except (OSError, ValueError):
        return {}


def _tr_save():
    try:
        os.makedirs(CACHE, exist_ok=True)
        with open(_tr_path(B["id"]) + ".tmp", "w", encoding="utf-8") as f:
            json.dump(B["tr"], f, ensure_ascii=False)
        os.replace(_tr_path(B["id"]) + ".tmp", _tr_path(B["id"]))
    except OSError:
        pass


def _tr_worker(gen, bid):
    TR["run"] = gen
    try:
        _tr_loop(gen, bid)
    finally:
        if TR.get("run") == gen:
            TR["run"] = None


def _tr_loop(gen, bid):
    fails = 0
    done = 0
    while TR["gen"] == gen and B["id"] == bid and TR["on"]:
        if time.time() - B.get("hb", 0) > 120:             # mod kapandı (sayfa nabız yollamıyor): modeli boşuna meşgul etme
            _tr_save()
            return
        n = len(B["pages"])
        i = next((k for k in range(B["pos"], n) if k not in B["tr"]), None)
        if i is None:
            i = next((k for k in range(0, B["pos"]) if k not in B["tr"]), None)
        if i is None:
            _tr_save()
            _push({"trdone": True, "msg": "Çeviri tamamlandı efendim."})
            return
        try:
            import scenes_yeni
            out = scenes_yeni._ask_llm("Şu metni Türkçeye çevir:\n\n" + B["pages"][i], SYS_TR)
        except Exception:
            out = ""
        out = re.sub(r"(?is)<think>.*?</think>", "", out or "").strip()
        if len(out) < 20:
            fails += 1
            if fails >= 3:
                _push({"msg": "Çeviri için yerel model yanıt vermiyor efendim; orijinal metni gösteriyorum.", "trfail": True})
                return
            time.sleep(4)
            continue
        fails = 0
        B["tr"][i] = out
        done += 1
        if done % 5 == 0:
            _tr_save()
        _push({"tr": {"i": i, "t": out}})


def _tr_start():
    TR["gen"] += 1
    if TR["on"] and _needs_tr():
        threading.Thread(target=_tr_worker, args=(TR["gen"], B["id"]), daemon=True).start()


def _lib_rows():
    rows = []
    for k, v in sorted(D["lib"].items(), key=lambda kv: -kv[1].get("t", 0)):
        rows.append({"id": k, "title": v["title"], "author": v.get("author", ""), "pos": v.get("pos", 0), "n": v.get("n", 0)})
    return rows[:20]


def _send_book():
    pages = B["pages"]
    _push({"book": {"id": B["id"], "title": B["title"], "author": B["author"], "src": B["src"], "n": len(pages), "pos": B["pos"], "trneed": _needs_tr()},
           "lib": _lib_rows(), "trmode": TR["on"]})
    for i in range(0, len(pages), 120):
        _push({"chunk": {"from": i, "pages": pages[i:i + 120]}})
        time.sleep(0.03)
    ks = sorted(B["tr"])
    for i in range(0, len(ks), 60):
        _push({"trbulk": {str(k): B["tr"][k] for k in ks[i:i + 60]}})
        time.sleep(0.03)


def _open(c):
    try:
        txt = _fetch_text(c)
    except Exception as e:
        _push({"msg": "Metin indirilemedi efendim: " + type(e).__name__, "busy": False})
        BUSY["on"] = False
        return
    if len(txt) < 1500:
        _push({"msg": "Bu kaynakta okunabilir metin bulamadım efendim.", "busy": False})
        BUSY["on"] = False
        return
    pages = _paginate(txt)
    lang = "tr" if (c.get("src") == "wikisource" or re.fullmatch(r"tr", c.get("lang", "") or "")) else (c.get("lang", "") or "en")
    B["hb"] = time.time()
    B.update(id=c["id"], title=c["title"], author=c["author"], src=c["src"], pages=pages, pos=D["lib"].get(c["id"], {}).get("pos", 0), lang=lang, tr=_tr_load(c["id"]))
    D["lib"][c["id"]] = {"title": c["title"], "author": c["author"], "src": c["src"], "pos": B["pos"], "n": len(pages), "t": time.time(), "url": c.get("url", ""), "lang": c.get("lang", "")}
    _save()
    BUSY["on"] = False
    _push({"busy": False, "msg": f"{c['title']} hazır, {len(pages)} sayfa." + (" Türkçeye çeviriyorum, ilk sayfalar birkaç saniyede gelir." if TR["on"] and _needs_tr() else "")})
    _send_book()
    _tr_start()


def _search(q):
    LASTQ["q"] = q
    cands = []
    try:
        import ekitap_adlar
        hit = ekitap_adlar.lookup(q)                # "savaş ve barış" -> "war and peace" (Gutendex Türkçe adı tanımaz)
    except Exception:
        hit = None
    if hit:
        cands = _gutenberg(hit[0])
        if hit[1] == "yazar":
            _push({"msg": f"Yazarın kamu malı eserlerini listeliyorum."})
    cands = cands or (_gutenberg_multi(q) + _wikisource(q))
    if not cands:                                # Türkçe ad İngilizce özgün adla aranır (yerel model varsa)
        try:
            import scenes_yeni
            en = (scenes_yeni._ask_llm(f"Şu kitabın İngilizce özgün adını ve yazarını yaz, yalnızca 'Ad Yazar' biçiminde, başka hiçbir şey yazma: {q}") or "").strip().split("\n")[0][:80]
        except Exception:
            en = ""
        if en and norm(en) != norm(q):
            cands = _gutenberg_multi(en)
    CAND[:] = cands[:6]
    if not cands:
        BUSY["on"] = False
        _push({"busy": False, "none": q, "msg": "Kamu malı kaynaklarda bulamadım efendim. Telifi süren kitapların metnini getiremem."})
        return
    _push({"cands": [{"i": i, "title": c["title"], "author": c["author"], "src": c["src"], "lang": c["lang"]} for i, c in enumerate(CAND)], "msg": f"{len(CAND)} aday buldum."})
    _open(CAND[0])


def _sayfa_metni():
    p = B["pages"]
    i = B["pos"]
    if p and TR["on"] and i in B.get("tr", {}):
        return B["tr"][i].replace("\n\n", " ")
    return " ".join(x.replace("\n\n", " ") for x in p[i:i + 1]) if p else ""


def ekitap(text, st):
    t = norm(text)
    raw = text.strip()
    if raw.startswith("§"):
        pr = raw[1:].split("|")
        B["hb"] = time.time()
        if pr[0] == "pos" and len(pr) > 2 and pr[1] == B["id"]:
            try:
                B["pos"] = max(0, min(len(B["pages"]) - 1, int(pr[2])))
                if B["id"] in D["lib"]:
                    D["lib"][B["id"]]["pos"] = B["pos"]
                    D["lib"][B["id"]]["t"] = time.time()
                    _save()
            except ValueError:
                pass
        elif pr[0] == "hb":
            if _needs_tr() and TR["on"] and TR.get("run") != TR["gen"]:
                _tr_start()
        elif pr[0] == "tr" and len(pr) > 1:
            return _set_tr(pr[1] == "1")
        elif pr[0] == "kit" and len(pr) > 1:
            return _pick(int(pr[1]) if pr[1].isdigit() else pr[1])
        return {"say": ""}
    if re.search(r"\b(türkçe\w*|çeviriyi aç\w*)", t) and not re.search(r"\bkitab\w*|\bsayfa\w*", t.replace("türkçe", "")):
        return _set_tr(True)
    if re.search(r"\b(orijinal\w*|ingilizce\w*|çeviriyi kapat\w*)", t):
        return _set_tr(False)
    if re.search(r"kitaptik", t):                        # Türkçe çeviri kamu malı kaynaklarda yoksa: sitenin kendi arama sayfası tarayıcıda açılır (metin çekilmez)
        import webbrowser
        q = LASTQ.get("q") or re.sub(r"kitaptik\w*|ara\w*|aç\w*|bul\w*", " ", t).strip()
        if not q:
            return {"say": "Neyi aramamı istersiniz efendim?"}
        webbrowser.open("https://kitaptik.com/ara?" + urllib.parse.urlencode({"q": q}))
        return {"say": f"{q} için Kitaptik arama sayfasını tarayıcıda açtım efendim. Orada okuma koşulları kitaba göre değişir."}
    if re.search(r"\b(yardım|komutlar|neler yapabilirsin)\b", t):
        return {"say": "Bir kitap adı söyleyin, örneğin Sefiller ya da Alice Harikalar Diyarında. Sonraki sayfa, önceki sayfa, elli ikinci sayfaya git, yüzde seksene git, sayfayı oku, kitaplığım ve ikinci adayı aç diyebilirsiniz. Yalnızca telifi bitmiş eserleri bulabilirim."}
    if re.search(r"\bkitaplı\w*|\bkütüphan\w*|\bkaldığım yer\w*", t):
        return {"say": f"Kitaplığınızda {len(D['lib'])} kitap var efendim.", "do": {"lib": _lib_rows(), "showlib": True}}
    if re.search(r"\b(sonraki|ileri|çevir|devam)\b", t) and B["pages"]:
        return {"say": "", "do": {"nav": "next"}}
    if re.search(r"\b(önceki|geri)\b", t) and B["pages"]:
        return {"say": "", "do": {"nav": "prev"}}
    m = re.search(r"(\d+)\s*\.?\s*sayfa\w*\s*(git|aç|geç)?|sayfa\s*(\d+)", t)
    if m and B["pages"]:
        n = int(m.group(1) or m.group(3))
        return {"say": "", "do": {"nav": "goto", "n": max(1, min(len(B["pages"]), n))}}
    m = re.search(r"(?:yüzde|%)\s*(\d+)|(\d+)\s*(?:yüzde|%)", t)
    if m and B["pages"]:
        pc = max(0, min(100, int(m.group(1) or m.group(2))))
        return {"say": "", "do": {"nav": "goto", "n": max(1, round(pc / 100 * len(B["pages"])))}}
    if re.search(r"\b(başa dön|ilk sayfa|baştan)\w*", t) and B["pages"]:
        return {"say": "", "do": {"nav": "goto", "n": 1}}
    if re.search(r"\b(sayfayı oku|sesli oku|bana oku|şunu oku)\b|\boku\b$", t) and B["pages"]:
        s = _sayfa_metni()
        return {"say": s[:1200] if s else "Okunacak sayfa yok."}
    if re.search(r"\b(sepya|koyu|gece|açık|kağıt) (tema|mod|renk)\w*|\btema\w* (sepya|koyu|gece|açık)", t):
        th = "koyu" if re.search(r"koyu|gece", t) else "sepya" if "sepya" in t else "acik"
        return {"say": "", "do": {"theme": th}}
    if re.search(r"\byazı\w* (büyüt|küçült)\w*|\b(yazıyı|fontu) (büyüt|küçült)\w*", t):
        return {"say": "", "do": {"font": "+" if "büyüt" in t else "-"}}
    mm = re.search(r"\b(birinci|ilk|ikinci|üçüncü|dördüncü|beşinci|altıncı|\d+\.?)\s*(aday|seçenek|sonuç)\w*", t)
    if mm and CAND:
        idx = {"birinci": 0, "ilk": 0, "ikinci": 1, "üçüncü": 2, "dördüncü": 3, "beşinci": 4, "altıncı": 5}.get(mm.group(1))
        idx = idx if idx is not None else int(re.sub(r"\D", "", mm.group(1))) - 1
        return _pick(idx)
    q = re.sub(r"\b(kitab\w*|romanı\w*|eserini\w*|aç\w*|bul\w*|getir\w*|ver\w*|oku\w*|internetten|ara\w*|istiyorum|okumak|okuyalım|başlat\w*|e kitap|lütfen)\b", " ", t)
    q = " ".join(q.split())
    if len(q) < 2:
        return {"say": "Hangi kitabı okumak istersiniz efendim?"}
    for k, v in D["lib"].items():                  # kitaplıktaki bir kitapsa yeniden aramadan aç
        if norm(v["title"]) == q or (len(q) > 4 and q in norm(v["title"])):
            return _pick(k)
    if BUSY["on"]:
        return {"say": "Bir kitabı hazırlıyorum efendim, birkaç saniye."}
    BUSY["on"] = True
    _push({"busy": True, "msg": f"{q} aranıyor…"})
    threading.Thread(target=_search, args=(q,), daemon=True).start()
    return {"say": f"{q.title()} için kamu malı kaynaklarda arıyorum efendim."}


def _set_tr(on):
    TR["on"] = bool(on)
    if on and _needs_tr():
        _tr_start()
        return {"say": "Türkçe çeviri açık efendim; okuduğunuz yerden başlayarak sayfaları çeviriyorum.", "do": {"trmode": True}}
    TR["gen"] += 1
    return {"say": "Orijinal metin gösteriliyor efendim." if not on else "Bu kitap zaten Türkçe efendim.", "do": {"trmode": bool(on and not _needs_tr())}}


def _pick(x):
    if BUSY["on"]:
        return {"say": "Bir kitabı hazırlıyorum efendim."}
    if isinstance(x, int):
        if not 0 <= x < len(CAND):
            return {"say": "Böyle bir aday yok efendim."}
        c = CAND[x]
    else:
        v = D["lib"].get(x)
        if not v:
            return {"say": "Kitap kitaplıkta yok efendim."}
        c = {"id": x, "src": v["src"], "title": v["title"], "author": v.get("author", ""), "url": v.get("url", ""), "lang": v.get("lang", "")}
    BUSY["on"] = True
    _push({"busy": True, "msg": c["title"] + " hazırlanıyor…"})
    threading.Thread(target=_open, args=(c,), daemon=True).start()
    return {"say": c["title"] + " hazırlanıyor efendim."}


def init_payload():
    BUSY["on"] = False
    B["hb"] = time.time()
    out = {"lib": _lib_rows(), "trmode": TR["on"], "kaynak": "Project Gutenberg ve Vikikaynak (yalnızca telifi bitmiş eserler)"}
    if B["pages"]:
        threading.Timer(0.6, lambda: (_send_book(), _tr_start())).start()
        out["resume"] = B["title"]
    return out


def register():
    scenes.HANDLERS["ekitap"] = ekitap
    scenes.INITS["ekitap"] = init_payload
    scenes.TITLES["ekitap"] = "JARVIS E-KİTAP"
    scenes.EXIT_SAY["ekitap"] = "E-kitap kapandı efendim, kaldığınız sayfa kayıtlı."
