"""Ders modu içerik üreticisi: konu anlatımı, özet, etkinlik, sorular ve tahta çözümleri yerel dil modeliyle (Ollama) üretilir ve ders_cache/ klasöründe saklanır.
Kalite önlemleri: sayısal derslerde (matematik, fizik, kimya) sorular 'düşünme' modunda üretilir, ardından model soruyu bağımsız çözer; çözüm şıkla uyuşmazsa soru atılır.
Sözel derslerde bu doğrulama yoktur; içerik arayüzde 'yapay zekâ ile üretildi' diye işaretlenir. Hatalı soru işaretlenince bankadan silinir."""
import json
import random
import re
import threading
import time

import ders_data
import ders_web

try:
    from brain import MODEL, CTX
except Exception:                                  # test ortamı
    MODEL, CTX = "qwen3:8b", 4096

NOTIFY = None                                      # main.py: notify(key, olay_sözlüğü) -> sayfaya iletir
_llm_lock = threading.Lock()
_urgent = 0                                        # sıradaki kullanıcı isteği (çözüm anlatımı) varken arka plan üretimi bekler
_cancel = threading.Event()
_job = {"key": None, "thread": None, "status": {}}
_job_lock = threading.Lock()
SYMBOL_NOTE = "Matematiksel ifadeleri düz metin ve Unicode ile yaz (x², √2, ≤, ≥, ·, |x|, ℝ); LaTeX, dolar işareti ya da ters eğik çizgi kullanma."


# ------------------------------------------------------------------ model çağrısı
def _llm(prompt: str, think: bool = False, num_predict: int = 2200, temp: float = 0.4, urgent_call: bool = False):
    """Tek seferde bir çağrı; iptal edilirse ya da hata olursa None. Akışlı okunur ki mod kapanınca ya da kullanıcı bir çözüm isteyince hemen bırakılabilsin
    (acil olmayan arka plan çağrıları, acil bir çağrı gelince bırakılır ve sonra yeniden denenir)."""
    import ollama
    with _llm_lock:
        out = []
        try:
            stream = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}], stream=True, think=think, keep_alive="10m",
                                 options={"temperature": temp, "num_ctx": CTX, "num_predict": num_predict, "repeat_penalty": 1.05})
            for part in stream:
                if _cancel.is_set() or (_urgent > 0 and not urgent_call):
                    return None
                out.append(part.message.content or "")
        except Exception as e:
            print("DERS: model hatası:", type(e).__name__, flush=True)
            return None
    return "".join(out).strip()


def _json(text):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    s = m.group(0)
    for cand in (s, re.sub(r",\s*([}\]])", r"\1", s)):
        try:
            return json.loads(cand)
        except ValueError:
            continue
    return None


def _wait_turn():
    while _urgent > 0 and not _cancel.is_set():
        time.sleep(0.3)


def _t(v, n=1500) -> str:
    return " ".join(str(v if v is not None else "").replace("\x00", " ").split())[:n]


def _ctx_line(m: dict) -> str:
    return f"9. sınıf {m['dersAd']} dersi (Türkiye Yüzyılı Maarif Modeli), ünite/tema: {m['unite']}, konu: {m['konu']}."


# ------------------------------------------------------------------ içerik türleri
def make_lesson(m: dict):
    nicel = m.get("nicel")
    p = (f"{_ctx_line(m)}\nBir öğretmen gibi, 9. sınıf öğrencisine bu konuyu Türkçe anlatan ders notu hazırla. 5 ya da 6 bölüm yaz: tanım ve temel kavramlar, kurallar, "
         + ("çözümlü örnekler (adım adım), sık yapılan hatalar, " if nicel else "önemli örnekler, sık karıştırılanlar, ")
         + "günlük hayattan bağlantı. Her bölüm 70-130 kelime olsun. Doğru ve kesin bilgi ver; emin olmadığın bilgi, tarih ya da isim uydurma. "
         + _mebi_block(m)
         + ders_web.block(m.get("kaynaklar"), m["konu"], 2200)
         + SYMBOL_NOTE + "\nYalnızca şu JSON'u döndür:\n"
         '{"bolumler":[{"baslik":"...","metin":"..."}],"alt_basliklar":["soru sorulabilecek 8-10 alt beceri/başlık"],"formuller":["varsa temel formül ya da kural"]}')
    d = _json(_llm(p, think=False, num_predict=2400, temp=0.35))
    if not d or not isinstance(d.get("bolumler"), list):
        return None
    bol = [{"baslik": _t(b.get("baslik"), 80), "metin": _t(b.get("metin"), 1400)} for b in d["bolumler"] if isinstance(b, dict) and _t(b.get("metin"))][:8]
    if len(bol) < 3:
        return None
    return {"bolumler": bol, "alt_basliklar": [_t(x, 90) for x in (d.get("alt_basliklar") or []) if _t(x)][:12], "formuller": [_t(x, 120) for x in (d.get("formuller") or []) if _t(x)][:10]}


def make_summary(m: dict, lesson: dict):
    text = " ".join(f"{b['baslik']}: {b['metin']}" for b in lesson["bolumler"])[:3200]
    p = (f"{_ctx_line(m)}\nAşağıdaki ders notunu 8-10 kısa madde halinde özetle (her madde en çok 20 kelime) ve en önemli kural/formülleri ayrıca listele. "
         + SYMBOL_NOTE + f"\nDers notu: {text}\nYalnızca JSON:\n" '{"maddeler":["..."],"anahtar_kavramlar":["..."],"formuller":["..."]}')
    d = _json(_llm(p, think=False, num_predict=900, temp=0.2))
    if not d or not isinstance(d.get("maddeler"), list):
        return None
    return {"maddeler": [_t(x, 200) for x in d["maddeler"] if _t(x)][:12], "anahtar_kavramlar": [_t(x, 60) for x in (d.get("anahtar_kavramlar") or []) if _t(x)][:12],
            "formuller": [_t(x, 120) for x in (d.get("formuller") or lesson.get("formuller") or []) if _t(x)][:10]}


def make_activity(m: dict, lesson: dict):
    subs = ", ".join(lesson.get("alt_basliklar", [])[:6])
    p = (f"{_ctx_line(m)}\nBu konu için sınıfta ya da evde yapılabilecek kısa bir ETKİNLİK hazırla: öğrenciyi düşündüren, kitapsız yapılabilen bir çalışma (örneğin eşleştirme, doğru/yanlış sorgulama, "
         f"boşluk doldurma ya da küçük bir araştırma/deney). Odak: {subs}. " + SYMBOL_NOTE + ders_web.block(m.get("kaynaklar"), subs, 900) + "\nYalnızca JSON:\n"
         '{"baslik":"...","amac":"...","yonerge":"öğrencinin yapacakları (3-5 cümle)","maddeler":[{"soru":"...","cevap":"..."}]}\n"maddeler" 6 adet olsun, cevapları doğru ve kesin yaz.')
    d = _json(_llm(p, think=m.get("nicel", False), num_predict=2200 if m.get("nicel") else 1500, temp=0.35))
    if not d or not isinstance(d.get("maddeler"), list):
        return None
    items = [{"soru": _t(x.get("soru"), 300), "cevap": _t(x.get("cevap"), 300)} for x in d["maddeler"] if isinstance(x, dict) and _t(x.get("soru")) and _t(x.get("cevap"))][:8]
    if len(items) < 3:
        return None
    return {"baslik": _t(d.get("baslik"), 100) or "Etkinlik", "amac": _t(d.get("amac"), 300), "yonerge": _t(d.get("yonerge"), 700), "maddeler": items}


# ------------------------------------------------------------------ sorular
LEVELS = {"quiz": "kolay ve orta düzeyde, konunun temel becerilerini ölçen", "deneme": "orta ve zor düzeyde, yeni nesil (beceri temelli, yorum ve problem çözme gerektiren), TYT/okul sınavı tarzında"}
NO_SHUFFLE = re.compile(r"yukarıdaki|hepsi|hiçbiri|\b[A-E] ve [A-E]\b|\bI+ ve I+\b|\bI, II|hem de", re.I)


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def _valid_q(q: dict):
    if not isinstance(q, dict):
        return None
    soru = _t(q.get("soru"), 700)
    sik = q.get("siklar")
    if len(soru) < 15 or not isinstance(sik, dict):
        return None
    opts = {k: _t(sik.get(k), 220) for k in "ABCDE"}
    if any(not v for v in opts.values()) or len({_norm(v) for v in opts.values()}) < 5:
        return None
    dogru = str(q.get("dogru") or "").strip().upper()[:1]
    if dogru not in "ABCDE" or not dogru:
        return None
    steps = [_t(x, 400) for x in (q.get("cozum_adimlari") or []) if _t(x)][:8] if isinstance(q.get("cozum_adimlari"), list) else []
    if not steps:
        return None
    return {"soru": soru, "siklar": opts, "dogru": dogru, "cozum_adimlari": steps, "aciklama": _t(q.get("aciklama"), 400)}


NEEDS_FIGURE = re.compile(r"aşağıdaki (grafik|şekil|tablo|görsel)|yukarıdaki (grafik|şekil|tablo)|şekilde|grafikte|tabloda|görselde|haritada", re.I)


# Tek geçişte çevrilir (iki ayrı geçiş aynı harfi iki kez çevirirdi): "cevap C", "C şıkkı", "C)", "C'dir"
_LETTER_REF = re.compile(r"((?:şık|seçenek|cevap|yanıt)\w*\s+)([A-E])\b|(?<![A-Za-zÇĞİÖŞÜçğıöşü])([A-E])(?=\)|'?(?:dır|dir|dur|dür|tır|tir|tur|tür)\b|\s+(?:şık|seçenek))", re.I)


def _remap_letters(text: str, new_of: dict) -> str:
    """Açıklama ve çözüm adımlarındaki şık harfi göndermelerini, şıklar karıştırıldıktan sonraki harflere çevirir
    (model 'doğru cevap C'dir' yazar, şıklar sonra karışınca bu yanlış kalırdı)."""
    def sub(m):
        if m.group(2):
            return m.group(1) + new_of.get(m.group(2).upper(), m.group(2))
        return new_of.get(m.group(3).upper(), m.group(3))
    return _LETTER_REF.sub(sub, text)


def _shuffle(q: dict) -> dict:
    texts = " ".join(q["siklar"].values()) + " " + q["soru"]
    if NO_SHUFFLE.search(texts):
        return q
    letters = list("ABCDE")
    order = letters[:]
    random.shuffle(order)
    new = {letters[i]: q["siklar"][order[i]] for i in range(5)}
    new_of = {order[i]: letters[i] for i in range(5)}                 # eski harf -> yeni harf
    q["dogru"] = new_of[q["dogru"]]
    q["siklar"] = new
    q["aciklama"] = _remap_letters(q.get("aciklama", ""), new_of)
    q["cozum_adimlari"] = [_remap_letters(s, new_of) for s in q.get("cozum_adimlari", [])]
    return q


def verify_light(q: dict) -> bool:
    """Sözel dersler için: model soruyu cevap anahtarını görmeden yanıtlar; anahtarla uyuşmazsa soru belirsiz ya da hatalıdır, atılır.
    Düşünme modu kapalı olduğu için hızlıdır; yine de yapay zekâ doğrulamasıdır, kesin doğruluk garantisi vermez."""
    p = ("Aşağıdaki çoktan seçmeli soruda TEK doğru şık vardır. Soruyu dikkatle oku ve doğru şıkkı bul. Soru belirsizse ya da birden fazla şık doğru görünüyorsa "
         '"yok" yaz.\nSoru: ' + q["soru"] + "\n" + "\n".join(f"{k}) {v}" for k, v in q["siklar"].items()) + '\nYalnızca JSON döndür: {"cevap":"A"}')
    d = _json(_llm(p, think=False, num_predict=120, temp=0.1))
    return bool(d) and str(d.get("cevap", "")).strip().upper()[:1] == q["dogru"]


def _mebi_block(m: dict) -> str:
    """MEBİ'nin bu konudaki kazanımları (m['kazanimlar'], ders_srv.open_topic doldurur). Boşsa bir şey eklenmez."""
    kz = m.get("kazanimlar") or []
    if not kz:
        return ""
    s = "\nMEBİ (MEB Bireysel Öğrenme Platformu) bu konuda şu kazanımları işliyor:\n" + "\n".join(f"- {k['kod']}: {k['ad']}" for k in kz[:8])
    if m.get("etkinlikler"):
        s += "\nMEBİ'deki etkinlik başlıkları: " + "; ".join(m["etkinlikler"][:10]) + "."
    return s + "\nİçeriği MEBİ'nin işlediği kazanımlara ve etkinlik başlıklarına bağlı tut; bunların dışına çıkma.\n"


def verify(q: dict) -> bool:
    """Sayısal sorular için: soru ve şıklar verilip model bağımsız çözer; cevabı anahtarla uyuşmalı."""
    p = ("Aşağıdaki çoktan seçmeli soruyu kendin dikkatle çöz ve doğru şıkkı bul. " + SYMBOL_NOTE + f"\nSoru: {q['soru']}\n"
         + "\n".join(f"{k}) {v}" for k, v in q["siklar"].items()) + '\nYalnızca JSON döndür: {"cevap":"A"}')
    d = _json(_llm(p, think=True, num_predict=2500, temp=0.1))
    return bool(d) and str(d.get("cevap", "")).strip().upper()[:1] == q["dogru"]


def make_questions(m: dict, kind: str, count: int, existing: list, focus: str):
    nicel = m.get("nicel")
    prev = "; ".join(_t(e["soru"], 60) for e in existing[-10:])
    p = (f"{_ctx_line(m)}\nBu konudan {count} adet 5 şıklı (A, B, C, D, E) çoktan seçmeli soru yaz. Zorluk: {LEVELS[kind]}. Odaklanılacak beceri: {focus}. "
         "Her soru farklı bir beceriyi ölçsün. Doğru cevap TEK ve kesin olsun, çeldiriciler makul hatalardan türesin. Soru kökü açık olsun; "
         "Şekil, grafik, tablo ya da görsel gerektiren soru YAZMA; sorular yalnızca metinle çözülebilsin. "
         + ("Sayısal değerler içeren, hesaplama ve yorum gerektiren problemler yaz; salt tanım sorusu yazma. " if nicel else "Bilgi ezberinden çok yorum ve ilişkilendirme isteyen sorular yaz. ")
         + "İşlemleri kendin doğrula. " + SYMBOL_NOTE
         + " Soru türlerini çeşitlendir (kavram, durum yorumlama, neden-sonuç, karşılaştırma); hepsi aynı kalıpta olmasın. Açıklamada şık harfi yazma, şıkkı içeriğiyle an."
         + (f" Daha önce yazılanlara benzeme: {prev}." if prev else "")
         + _mebi_block(m)
         + ders_web.block(m.get("kaynaklar"), focus, 1100)
         + ('\nHer soru yukarıdaki kazanımlardan yalnızca birini ölçsün ve "kazanim" alanına o kodu yaz (örn. "BİY.9.1.2").' if m.get("kazanimlar") else "")
         + '\nYalnızca JSON:\n{"sorular":[{"soru":"...","siklar":{"A":"...","B":"...","C":"...","D":"...","E":"..."},"dogru":"C","cozum_adimlari":["kısa adım","..."],"aciklama":"kısa gerekçe","kazanim":"kod ya da boş"}]}')
    d = _json(_llm(p, think=nicel, num_predict=3200 if nicel else 2800, temp=0.5 if not nicel else 0.35))
    out = []
    if not d or not isinstance(d.get("sorular"), list):
        return out
    seen = {_norm(e["soru"]) for e in existing}
    for raw in d["sorular"]:
        q = _valid_q(raw)
        if not q or _norm(q["soru"]) in seen or NEEDS_FIGURE.search(q["soru"]):
            continue
        codes = {k["kod"] for k in (m.get("kazanimlar") or [])}
        kod = str(raw.get("kazanim") or "").strip() if isinstance(raw, dict) else ""
        if kod in codes:
            q["kazanim"] = kod                                    # yalnızca MEBİ'nin gerçek kazanım kodları kabul edilir
        if nicel:
            _wait_turn()
            if _cancel.is_set():
                return out
            ok = verify(q)
            if _cancel.is_set() or _urgent > 0:           # doğrulama yarıda kesildi: soruyu atma, sonra yeniden üretilecek
                return out
            if not ok:
                continue
            q["kontrol"] = "dogrulandi"
        else:
            _wait_turn()
            if _cancel.is_set():
                return out
            ok = verify_light(q)
            if _cancel.is_set() or _urgent > 0:
                return out
            if not ok:
                continue                                          # model kendi sorusunu anahtarsız çözemedi: belirsiz soru atılır
            q["kontrol"] = "tutarli"
        q = _shuffle(q)
        q["id"] = "q" + format(random.getrandbits(32), "08x")[:8]
        q["zorluk"] = kind
        seen.add(_norm(q["soru"]))
        out.append(q)
    return out


# ------------------------------------------------------------------ tahta çözümü (sesli anlatım + ekranda çizim)
def make_board(m: dict, q: dict, secili: str = ""):
    """Soru için adım adım çözüm: her adımda ekrana yazılacak işlemler ve sesle okunacak anlatım."""
    p = (f"{_ctx_line(m)}\nÖğrenci şu soruyu çözemedi. Çözümü tahtada öğretmen gibi adım adım göster.\nSoru: {q['soru']}\n"
         + "\n".join(f"{k}) {v}" for k, v in q["siklar"].items()) + f"\nDoğru şık: {q['dogru']}" + (f" (öğrenci {secili} şıkkını seçmişti)" if secili and secili != q["dogru"] else "")
         + f"\nYazılı çözüm taslağı: {' | '.join(q.get('cozum_adimlari', []))[:900]}\n" + SYMBOL_NOTE
         + "\nHer adımda: 'baslik' (kısa), 'islem' (tahtaya yazılacak 1-3 satır işlem/ifade, Unicode semboller serbest), 'anlat' (öğrencinin sesli dinleyeceği 1-2 kısa cümle; SEMBOL KULLANMA, "
           "sayıları ve işlemleri sözle yaz: 'x kare', 'kök iki', 'eşittir', 'artı'). 'sonuc' alanında doğru cevabı belirt. Çözüm 3-7 adım olsun."
           ' Fonksiyon grafiği çizmek anlamlıysa "grafik" alanına yalnızca x değişkenli bir ifade yaz (örn. abs(2*x-4)+3), değilse boş bırak.'
           '\nYalnızca JSON:\n{"adimlar":[{"baslik":"...","islem":["..."],"anlat":"..."}],"sonuc":"...","grafik":""}')
    d = _json(_llm(p, think=m.get("nicel", False), num_predict=3000, temp=0.2, urgent_call=True))
    if not d or not isinstance(d.get("adimlar"), list):
        return None
    steps = []
    for a in d["adimlar"][:9]:
        if not isinstance(a, dict):
            continue
        isl = [_t(x, 160) for x in (a.get("islem") if isinstance(a.get("islem"), list) else [a.get("islem")]) if _t(x)][:4]
        if _t(a.get("anlat")) or isl:
            steps.append({"baslik": _t(a.get("baslik"), 80), "islem": isl, "anlat": _t(a.get("anlat"), 400)})
    if not steps:
        return None
    graf = _t(d.get("grafik"), 80)
    if graf and not re.fullmatch(r"[0-9x+\-*/().,^ a-z]*", graf.lower()):
        graf = ""
    return {"adimlar": steps, "sonuc": _t(d.get("sonuc"), 200) or f"Doğru cevap {q['dogru']}) {q['siklar'][q['dogru']]}", "grafik": graf}


def graph_points(expr: str):
    """Tahtadaki grafik: ifade güvenli bir ayrıştırıcıyla (safemath) -8..8 aralığında örneklenir; hata olursa None."""
    try:
        import safemath
        pts = []
        for i in range(-80, 81):
            x = i / 10
            try:
                y = safemath.evaluate(expr, {"x": x})
            except Exception:                              # tanımsız nokta (örn. kök içi negatif): çizgi bölünür
                pts.append(None)
                continue
            if isinstance(y, complex) or abs(y) > 1e6:
                pts.append(None)
                continue
            pts.append([x, float(y)])
        return pts if sum(1 for p in pts if p) >= 20 else None
    except Exception:
        return None


# ------------------------------------------------------------------ arka plan üretimi
def _status(key: str) -> dict:
    return _job["status"] if _job["key"] == key else {}


def _emit(key: str, ev: dict):
    if NOTIFY:
        try:
            NOTIFY(key, ev)
        except Exception:
            pass


def _run(key: str, m: dict, nq: int, nd: int):
    st = _job["status"]
    cache = ders_data.cache_load(key)
    if ders_data.settings().get("internet_kaynak") and not cache.get("kaynaklar_denendi") and not _cancel.is_set():
        st["kaynak"] = "aranıyor"
        _emit(key, {"status": dict(st)})
        got = ders_web.gather(m)                           # yalnızca arama sorgusu dışarı gider; sayfalar güvenle okunur, kaydedilmez
        cache["kaynaklar"], cache["kaynaklar_hata"], cache["kaynaklar_denendi"] = got["kaynaklar"], got["hata"], True
        ders_data.cache_save(key, cache)
        _emit(key, {"part": "kaynaklar"})
    m["kaynaklar"] = cache.get("kaynaklar", [])
    st.update(lesson=bool(cache.get("lesson")), ozet=bool(cache.get("ozet")), etkinlik=bool(cache.get("etkinlik")),
              quiz=len(cache.get("quiz", [])), deneme=len(cache.get("deneme", [])), hata="")

    def save(part, value):
        cache[part] = value
        ders_data.cache_save(key, cache)
        _emit(key, {"part": part})

    def attempt(fn, *a):
        for _ in range(3):
            if _cancel.is_set():
                return None
            _wait_turn()
            r = fn(*a)
            if r:
                return r
        return None

    try:
        if not cache.get("lesson"):
            r = attempt(make_lesson, m)
            if not r:
                st["hata"] = "Konu anlatımı üretilemedi (model yanıt vermedi)."
                _emit(key, {"status": dict(st)})
                return
            save("lesson", r)
            st["lesson"] = True
            _emit(key, {"status": dict(st)})
        lesson = cache["lesson"]
        if not cache.get("ozet") and not _cancel.is_set():
            r = attempt(make_summary, m, lesson)
            if r:
                save("ozet", r)
                st["ozet"] = True
                _emit(key, {"status": dict(st)})
        if not cache.get("etkinlik") and not _cancel.is_set():
            r = attempt(make_activity, m, lesson)
            if r:
                save("etkinlik", r)
                st["etkinlik"] = True
                _emit(key, {"status": dict(st)})
        for kind in ("quiz", "deneme"):
            bank = cache.setdefault(kind, [])
            subs = lesson.get("alt_basliklar") or [m["konu"]]
            fails = 0
            while not _cancel.is_set() and fails < 4:
                target = ders_data.settings()["quiz_n" if kind == "quiz" else "deneme_n"]      # ayar sürerken değişebilir
                if len(bank) >= target:
                    break
                _wait_turn()
                need = min(4, target - len(bank))
                focus = subs[(len(bank) // 2 + (3 if kind == "deneme" else 0)) % len(subs)]
                new = make_questions(m, kind, need, bank + cache.get("quiz" if kind == "deneme" else "deneme", []), focus)
                if new:
                    bank.extend(new)
                    cache[kind] = bank
                    ders_data.cache_save(key, cache)
                    st[kind] = len(bank)
                    fails = 0
                    _emit(key, {"status": dict(st), "part": kind})
                else:
                    fails += 1
            if _cancel.is_set():
                return
        st["bitti"] = True
        _emit(key, {"status": dict(st)})
    except Exception as e:
        print("DERS üretim hatası:", type(e).__name__, e, flush=True)
        st["hata"] = "Üretim sırasında bir hata oluştu."
        _emit(key, {"status": dict(st)})


def prefetch(key: str, meta: dict, nq: int, nd: int) -> dict:
    """Seçilen konunun içeriğini arka planda üretmeye başlar (daha önce üretilenler önbellekten gelir)."""
    with _job_lock:
        if _job["key"] == key and _job["thread"] and _job["thread"].is_alive():
            return dict(_job["status"])
        stop()
        _cancel.clear()
        _job["key"], _job["status"] = key, {}
        t = threading.Thread(target=_run, args=(key, meta, nq, nd), daemon=True)
        _job["thread"] = t
        t.start()
    return {}


def stop():
    """Arka plan üretimini durdurur (mod kapanırken ya da başka konuya geçilirken); GPU serbest kalır."""
    _cancel.set()
    t = _job.get("thread")
    if t and t.is_alive() and t is not threading.current_thread():
        t.join(timeout=6)
    _job["thread"] = None


def status(key: str) -> dict:
    return dict(_status(key))


def urgent(on: bool):
    global _urgent
    _urgent = max(0, _urgent + (1 if on else -1))
