"""Quiz modu (ders çalışma) sunucu tarafı: sayfadan gelen istekleri doğrular, içerik üretimini başlatır, tahta çözümünü sesle birlikte adım adım yayınlar.
Sayfa yalnızca kendi ders/ünite/konu metnini ve ilerlemesini gönderir; dosya yolu, komut ya da ağ adresi kabul edilmez."""
import re
import threading

import ders_ai
import ders_data

_narr_lock = threading.Lock()
_narr = {"id": 0, "stop": threading.Event()}
HOOKS = {"emit": None, "speak": None, "stop_speech": None}
_META = {}                                              # key -> meta (açık konular)

SPEECH = [("²", " kare "), ("³", " küp "), ("√", " kök "), ("≤", " küçük eşittir "), ("≥", " büyük eşittir "), ("≠", " eşit değildir "), ("≈", " yaklaşık "),
          ("·", " çarpı "), ("×", " çarpı "), ("÷", " bölü "), ("→", " "), ("⇒", " dolayısıyla "), ("∈", " elemanıdır "), ("∪", " birleşim "), ("∩", " kesişim "),
          ("ℝ", " gerçek sayılar "), ("ℤ", " tam sayılar "), ("ℕ", " doğal sayılar "), ("ℚ", " rasyonel sayılar "), ("π", " pi "), ("°", " derece "),
          ("=", " eşittir "), ("+", " artı "), ("%", " yüzde "), ("|", " mutlak değer "), ("^", " üssü "), ("*", " çarpı ")]


def speakable(text: str) -> str:
    t = str(text)
    t = re.sub(r"\|([^|]{1,40})\|", lambda mo: " mutlak değer " + mo.group(1) + " ", t)                    # |x - 2| -> mutlak değer x - 2
    t = re.sub(r"(?<![\w)])-(?=[a-zA-Z0-9(])", " eksi ", t)                       # -a, -5
    t = re.sub(r"(?<=\d)\s*-\s*(?=\d|[a-zA-Z(])", " eksi ", t)
    t = re.sub(r"\s-\s", " eksi ", t)
    for a, b in SPEECH:
        t = t.replace(a, b)
    t = re.sub(r"[(){}\[\]_`~]", " ", t)
    return " ".join(t.split())[:600]


def emit(do: dict):
    if HOOKS["emit"]:
        HOOKS["emit"](do)


def _opened(key: str):
    return _META.get(key)


def content_payload(key: str) -> dict:
    c = ders_data.cache_load(key)
    return {"key": key, "kaynaklar": c.get("kaynaklar", []), "kaynak_hata": c.get("kaynaklar_hata", ""), "lesson": c.get("lesson"), "ozet": c.get("ozet"), "etkinlik": c.get("etkinlik"), "quiz": c.get("quiz", []), "deneme": c.get("deneme", []),
            "status": ders_ai.status(key)}


def on_notify(key: str, ev: dict):
    """Arka plan üretimi bir parça bitirince sayfaya haber verir (yalnızca açık konu için)."""
    if key not in _META:
        return
    out = {"progress": {"key": key, "status": ev.get("status") or ders_ai.status(key)}}
    part = ev.get("part")
    if part:
        c = ders_data.cache_load(key)
        out["progress"]["part"] = part
        out["progress"]["data"] = c.get(part) if part in ("lesson", "ozet", "etkinlik") else c.get(part, [])
        if part == "kaynaklar":
            out["progress"]["hata"] = c.get("kaynaklar_hata", "")
    emit(out)


ders_ai.NOTIFY = on_notify


def _guess_nicel(ders_ad: str) -> bool:
    return bool(re.search(r"mat|fizik|kimya|geometri|sayısal|istatistik", ders_ad.lower()))


def open_topic(d: dict) -> dict:
    """Konuyu açar: anahtarı üretir, arka plan üretimini başlatır, önbellekteki içeriği döndürür."""
    ders_id = ders_data._s(d.get("ders"), 20)
    ders_ad = ders_data._s(d.get("dersAd"), 40)
    unite = ders_data._s(d.get("unite"), 100) or "Serbest ünite"
    konu = ders_data._s(d.get("konu"), 120)
    if not konu:
        return {"msg": "Konu adı gerekli."}
    base = ders_data.BY_ID.get(ders_id)
    if base:
        ders_ad = base["ad"]
        known = any(u["ad"] == unite and any(k["ad"] == konu for k in u["konular"]) for u in base["uniteler"])
        nicel = base["nicel"]
        if not known:
            ders_data.add_custom(base["ad"], unite, konu)
    else:
        if not ders_ad:
            return {"msg": "Ders adı gerekli."}
        ders_id = "ozel"
        nicel = _guess_nicel(ders_ad)
        ders_data.add_custom(ders_ad, unite, konu)
    key = ders_data.key_of(ders_id if base else ders_ad, unite, konu)
    meta = {"ders": ders_id, "dersAd": ders_ad, "unite": unite, "konu": konu, "nicel": nicel}
    _META.clear()
    try:
        import mebi
        extra = mebi.outcomes(ders_ad, unite, konu)           # MEBİ'den gelen konuysa kazanımlar soru üretimine girer (sayfaya gönderilmez)
    except Exception:
        extra = {}
    _META[key] = {**meta, **extra}
    st = ders_data.settings()
    ders_ai.prefetch(key, _META[key], st["quiz_n"], st["deneme_n"])
    stage = d.get("stage") if d.get("stage") in ("anlatim", "ozet", "etkinlik", "quiz", "deneme") else ""
    return {"opened": {"key": key, "meta": meta, "stage": stage}, "content": content_payload(key), "view": ders_data.view()}


# ------------------------------------------------------------------ anlatım (ses + ekranda vurgu)
def _start_narration(items):
    """items: [(konuşulacak_metin, sayfaya_giden_olay)]. Önceki anlatım varsa keser. Tek iş parçacığı."""
    stop_narration()
    with _narr_lock:
        _narr["id"] += 1
        my = _narr["id"]
        _narr["stop"] = threading.Event()
        ev = _narr["stop"]

    def run():
        for text, event in items:
            if ev.is_set() or _narr["id"] != my:
                break
            if event:
                emit(event)
            if text and HOOKS["speak"]:
                if HOOKS["speak"](text):                 # "Hey Jarvis" ya da durdur ile sözü kesildi: anlatımı bırak
                    break
        if _narr["id"] == my and not ev.is_set():
            emit({"narrEnd": True})
    threading.Thread(target=run, daemon=True).start()


def stop_narration():
    _narr["stop"].set()
    _narr["id"] += 1
    if HOOKS["stop_speech"]:
        try:
            HOOKS["stop_speech"]()
        except Exception:
            pass


def narrate(key: str, section: str):
    meta = _opened(key)
    c = ders_data.cache_load(key) if meta else {}
    items = []
    if section == "anlatim" and c.get("lesson"):
        for i, b in enumerate(c["lesson"]["bolumler"]):
            items.append((speakable(b["baslik"] + ". " + b["metin"]), {"narr": {"section": "anlatim", "i": i}}))
    elif section == "ozet" and c.get("ozet"):
        for i, t in enumerate(c["ozet"]["maddeler"]):
            items.append((speakable(t), {"narr": {"section": "ozet", "i": i}}))
    elif section == "etkinlik" and c.get("etkinlik"):
        e = c["etkinlik"]
        items.append((speakable(e["baslik"] + ". " + e["yonerge"]), {"narr": {"section": "etkinlik", "i": -1}}))
    if not items:
        emit({"msg": "Bu bölüm henüz hazır değil efendim, birkaç saniye bekleyin."})
        return
    _start_narration(items)


# ------------------------------------------------------------------ tahta çözümü
def help_question(d: dict):
    key = str(d.get("key") or "")
    qid = str(d.get("qid") or "")[:12]
    secili = str(d.get("secili") or "")[:1]
    meta = _opened(key)
    if not meta:
        return
    c = ders_data.cache_load(key)
    q = next((x for x in c.get("quiz", []) + c.get("deneme", []) if x.get("id") == qid), None)
    if not q:
        emit({"msg": "Soru bulunamadı."})
        return
    stop_narration()
    board = q.get("tahta")
    if not board:
        emit({"boardLoading": {"qid": qid}, "msg": "Çözümü hazırlıyorum efendim, birkaç saniye sürebilir."})
        ders_ai.urgent(True)
        try:
            board = ders_ai.make_board(meta, q, secili)
            if not board:
                board = ders_ai.make_board(meta, q, secili)
        finally:
            ders_ai.urgent(False)
        if not board:
            emit({"boardLoading": None, "msg": "Çözümü üretemedim efendim. Yazılı çözüm adımlarını gösteriyorum."})
            board = {"adimlar": [{"baslik": f"Adım {i + 1}", "islem": [s], "anlat": s} for i, s in enumerate(q["cozum_adimlari"])],
                     "sonuc": f"Doğru cevap {q['dogru']}) {q['siklar'][q['dogru']]}", "grafik": ""}
        else:
            c = ders_data.cache_load(key)
            for x in c.get("quiz", []) + c.get("deneme", []):
                if x.get("id") == qid:
                    x["tahta"] = board
            ders_data.cache_save(key, c)
    pts = ders_ai.graph_points(board["grafik"]) if board.get("grafik") else None
    items = [(None, {"boardStart": {"qid": qid, "n": len(board["adimlar"]), "grafik": pts, "grafikIfade": board.get("grafik", "")}})]
    for i, a in enumerate(board["adimlar"]):
        items.append((speakable(a["anlat"]), {"boardStep": {"i": i, "baslik": a["baslik"], "islem": a["islem"], "anlat": a["anlat"]}}))
    items.append((speakable(board["sonuc"]), {"boardEnd": {"sonuc": board["sonuc"]}}))
    _start_narration(items)


def flag_question(d: dict):
    key = str(d.get("key") or "")
    qid = str(d.get("qid") or "")[:12]
    if key not in _META:
        return
    c = ders_data.cache_load(key)
    n0 = len(c.get("quiz", [])) + len(c.get("deneme", []))
    for kind in ("quiz", "deneme"):
        c[kind] = [x for x in c.get(kind, []) if x.get("id") != qid]
    if len(c.get("quiz", [])) + len(c.get("deneme", [])) != n0:
        ders_data.cache_save(key, c)
        st = ders_data.settings()
        ders_ai.prefetch(key, _META[key], st["quiz_n"], st["deneme_n"])       # eksilen soru yeniden üretilsin
        emit({"flagged": qid, "msg": "Soru bankadan çıkarıldı, yerine yenisi üretilecek."})


def handle(d: dict):
    ty = d.get("type")
    if ty == "ders_open":
        emit(open_topic(d))
    elif ty == "ders_content":
        k = str(d.get("key") or "")
        if k in _META:
            emit({"content": content_payload(k)})
    elif ty == "ders_progress":
        ders_data.save_progress(str(d.get("key") or ""), d.get("progress") if isinstance(d.get("progress"), dict) else {})
    elif ty == "ders_settings":
        st = ders_data.set_setting(str(d.get("name") or ""), d.get("value"))
        emit({"settings": st})
        k = str(d.get("key") or "")
        if k in _META and str(d.get("name") or "") in ("quiz_n", "deneme_n"):
            ders_ai.prefetch(k, _META[k], st["quiz_n"], st["deneme_n"])       # hedef büyüdüyse üretim sürsün
    elif ty == "ders_help":
        help_question(d)
    elif ty == "ders_narrate":
        narrate(str(d.get("key") or ""), str(d.get("section") or ""))
    elif ty == "ders_regen":
        k = str(d.get("key") or "")
        if k in _META:
            ders_ai.stop()
            c = ders_data.cache_load(k)
            for part in ("lesson", "ozet", "etkinlik", "kaynaklar", "kaynaklar_hata", "kaynaklar_denendi"):
                c.pop(part, None)
            ders_data.cache_save(k, c)
            st = ders_data.settings()
            ders_ai.prefetch(k, _META[k], st["quiz_n"], st["deneme_n"])
            emit({"content": content_payload(k), "msg": "Anlatım, özet ve etkinlik internet kaynaklarıyla yeniden üretiliyor."})
    elif ty == "ders_stop":
        stop_narration()
        emit({"narrEnd": True})
    elif ty == "ders_flag":
        flag_question(d)
    elif ty == "ders_custom":
        r = ders_data.add_custom(str(d.get("ders") or ""), str(d.get("unite") or ""), str(d.get("konu") or ""))
        emit({"view": ders_data.view(), "msg": "Konu eklendi." if r else "Ders ve konu adı gerekli."})
    elif ty == "ders_reset":
        ders_data.reset_progress(str(d.get("key") or ""))
        emit({"view": ders_data.view()})


def shutdown():
    """Mod kapanırken: anlatımı keser, arka plan üretimini durdurur (GPU serbest kalır)."""
    stop_narration()
    ders_ai.stop()
    _META.clear()


AUTO = {"topic": None}            # main.mebi_cmd: ders modu açılınca sayfanın hemen açacağı konu (MEBİ'den)


def init_payload():
    t, AUTO["topic"] = AUTO["topic"], None
    return {"view": ders_data.view(), "auto": t}
