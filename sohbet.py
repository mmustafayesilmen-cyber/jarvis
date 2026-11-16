"""Sohbet motoru: yerel modelle (brain.MODEL) uzun, akıcı, düşünebilen sohbet. İki kişilik bu motoru kullanır: Jarvis sohbet modu (JARVIS) ve Ultron (ultron.py).
Normal Jarvis'ten farkı: araç çağırmaz, cevaplar kısa olmak zorunda değil, konuşma geçmişi kişiliğe göre modda kalır (yalnızca RAM'de, diske yazılmaz),
zor sorularda model önce düşünür (qwen3 'think'). Cevap cümle cümle akar: metin sayfaya, tamamlanan cümleler sese gider.
Yavaş iş ayrı iş parçacığında çalışır; sonuçlar NOTIFY(kind, do) ile sayfaya, SAY ile sese iletilir (main.py bağlar)."""
import datetime
import queue
import re
import threading
import time

import settings

NOTIFY = None            # main.py: NOTIFY(kind, do) -> o modun sayfasına iletir
SAY = None               # main.py: SAY(metin, devam_mı) -> söyler; sözü kesildiyse True döner
ACTIVE = lambda kind="sohbet": True    # main.py: o kipin penceresi hâlâ açık mı

IDLE_RESET = 30 * 60     # bu kadar süre sessizlikten sonra mod açılırsa geçmiş temizlenir
CHAR_BUDGET = 12000      # modele giden geçmişin üst sınırı (≈4000 belirteç); eskiler düşer
MAX_MSGS = 80
_CODE = "\x00CODE"

SYSTEM = """Sen JARVIS'sin: kullanıcının bilgisayarında yerel çalışan kişisel yapay zekâ asistanısın. Şu an SOHBET MODUNDASIN: araç çalıştırmıyor, kullanıcıyla gerçekten konuşuyorsun.
KİŞİLİK: Zeki, meraklı, sıcak, hafif esprili ve dürüstsün. Konuyu gerçekten düşün; yüzeysel ya da kalıp cevap verme. Kullanıcı yanılıyorsa nazikçe, gerekçesiyle karşı çık; sen yanılırsan açıkça düzelt. Bilmediğin ya da emin olmadığın şeyi uydurma, "emin değilim" de. Kullanıcının daha önce söylediklerini hatırla ve kullan.
ERİŞİMİN: İnternete, saate, havaya ve güncel olaylara bu modda erişimin yok; bunları tahmin etme, gerekirse "bunu sohbet dışında normal Jarvis'e sorun" de.
KONUŞMA TARZI: Cevabın sesli okunacak, bu yüzden düz ve doğal konuşma dili kullan; markdown, başlık, madde işareti, tablo ve emoji kullanma (kod istenirse ``` bloğu serbest). Türkçede kullanıcıya "siz" diye hitap et; "efendim" sözcüğünü doğal ve seyrek kullan, her cümleye ekleme. Sayıları rakamla yaz. Kullanıcı İngilizce konuşursa İngilizce cevap ver ve ona "sir" de.
UZUNLUK: Selam, teşekkür gibi basit sohbete 1-2 cümleyle karşılık ver. Fikir, açıklama, karşılaştırma, tavsiye isteyen sorulara 4-8 cümleyle gerçekten içerik ver; kullanıcı "detaylı anlat" derse daha uzun konuş. Önce asıl cevabı ver; konuşmayı sürdürmek faydalıysa en fazla bir ilgili soru sor, ama her mesajı soruyla bitirme.
DÜŞÜNME: Karmaşık sorularda adım adım akıl yürüt; matematik ve mantıkta sonucu kontrol et.
Kullanıcının cümlesi ses tanımadan bozuk gelmiş olabilir; en olası anlamı seç, çok belirsizse kısaca sor."""

HELP = ("Benimle istediğiniz her şeyi konuşabilirsiniz: fikir, açıklama, karşılaştırma, tavsiye, kod ya da sadece sohbet. "
        "Yeni sohbet derseniz geçmişi temizlerim, sus derseniz sözümü keserim. Derin düşün ya da hızlı cevap ver diyerek düşünme biçimini seçebilirsiniz. "
        "Bir şeyi sonraya saklamamı isterseniz, örneğin en sevdiğim renk mavi bunu hatırla deyin. Çıkmak için çık deyin.")

_DEEP = re.compile(r"\b(neden|niçin|niye|nasıl|açıkla\w*|karşılaştır\w*|fark\w*|sence|tavsiye\w*|öner\w*|plan\w*|analiz\w*|yorumla\w*|değerlendir\w*|"
                   r"mantık\w*|kanıtla\w*|hesapla\w*|çöz\w*|strateji\w*|avantaj\w*|hangisi|why|how|explain|compare|should)\b", re.I)


def _mode() -> str:
    m = settings.get("sohbet_think")
    return m if m in ("auto", "hep", "hic") else "auto"


def wants_think(text: str) -> bool:
    """Basit selam/teşekkürde düşünme (hız); uzun ya da 'neden/nasıl/sence' gibi sorularda düşün (doğruluk)."""
    m = _mode()
    if m != "auto":
        return m == "hep"
    return len(text.split()) >= 7 or bool(_DEEP.search(text))


def set_mode(m: str):
    settings.set("sohbet_think", m)


def _jarvis_system() -> str:
    import memory
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    return SYSTEM + f"\nŞu anki tarih ve saat (yalnızca bilgi): {now}." + memory.as_prompt()


# ------------------------------------------------------------------ cümle ayırma (akış sırasında)
_END = re.compile(r"(.+?(?:[.!?…]+(?=\s)|\n))\s*", re.S)
_EMOJI = re.compile("[\U00010000-\U0010ffff☀-➿️]")


def _sentences(text: str, final: bool):
    """Tamamlanmış cümleleri ve henüz bitmemiş artığı döner; çok kısa parçalar sonrakiyle birleşir."""
    out, pos, carry = [], 0, ""
    for m in _END.finditer(text):
        s = carry + m.group(1).strip()
        pos = m.end()
        if len(s) < 14:
            carry = s + " "
            continue
        carry = ""
        out.append(s)
    rest = carry + text[pos:]
    if final and rest.strip():
        out.append(rest.strip())
        rest = ""
    return out, rest


def _split(buf: str, final: bool = False):
    """Kod bloklarını (``` ... ```) sese vermeden atlar; yerine _CODE işareti koyar."""
    out = []
    while "```" in buf:
        i = buf.index("```")
        s, _ = _sentences(buf[:i], True)
        out += s
        j = buf.find("```", i + 3)
        if j == -1:                                  # blok henüz kapanmadı: gelene kadar bekle
            return out, ("" if final else buf[i:])
        out.append(_CODE)
        buf = buf[j + 3:]
    s, rest = _sentences(buf, final)
    return out + s, rest


def _speakable(s: str) -> str:
    import brain
    s = _EMOJI.sub("", s)
    s = re.sub(r"\([^)]*\)", "", s)                  # (sahne yönergesi) ve (kaynak: …) okunmaz; ekranda görünür
    s = re.sub(r"^\s*[-•*]\s+", "", s)
    s = re.sub(r"[*#>`~|]+|(?<!\w)_+|_+(?!\w)", "", s)        # dosya adlarındaki alt çizgi (a_b.txt) kalır, _vurgu_ gider
    return brain.rule_fixes(" ".join(s.split()))


def say_as(persona, text: str, cont: bool = False) -> bool:
    """SAY ile söyler; persona verilmişse yalnızca bu cümle o kişiliğin sesiyle sentezlenir (voice.PERSONA), sonra Jarvis sesine dönülür."""
    import voice as V
    V.PERSONA["name"] = persona
    try:
        return bool(SAY(text, cont)) if SAY else False
    finally:
        V.PERSONA["name"] = None


class Chat:
    """Bir kişiliğin sohbeti: kendi geçmişi, sistem istemi ve sayfası (kind). Geçmiş yalnızca bellekte durur."""

    def __init__(self, kind: str, system_fn, persona=None, strip_parens=False, filler="Bir saniye efendim, düşünüyorum.", code_note="Kodu ekrana yazdım efendim.",
                 err_model="Bir sorun oldu efendim, model yanıt vermedi. Ollama açık mı diye bakar mısınız?",
                 err_empty="Bir cevap oluşturamadım efendim, tekrar eder misiniz?"):
        self.kind, self.system_fn, self.persona, self.strip_parens = kind, system_fn, persona, strip_parens
        self.filler, self.code_note, self.err_model, self.err_empty = filler, code_note, err_model, err_empty
        self.S = {"msgs": [], "gen": 0, "busy": False, "last": 0.0}
        self._lock = threading.Lock()

    def active(self) -> bool:
        return bool(ACTIVE(self.kind))

    def notify(self, do: dict):
        if NOTIFY:
            NOTIFY(self.kind, do)

    def snapshot(self) -> dict:
        return {"msgs": list(self.S["msgs"]), "busy": self.S["busy"], "think": _mode()}

    def init_payload(self):
        with self._lock:
            self.S["gen"] += 1                       # önceki oturumdan kalan cevap üretimini keser
            self.S["busy"] = False
            if time.time() - self.S["last"] > IDLE_RESET:
                self.S["msgs"].clear()
        return self.snapshot()

    def reset(self):
        with self._lock:
            self.S["gen"] += 1
            self.S["busy"] = False
            self.S["msgs"].clear()

    def cancel(self):
        with self._lock:
            self.S["gen"] += 1
            self.S["busy"] = False

    def _window(self) -> list:
        out, n = [], 0
        for m in reversed(self.S["msgs"]):
            n += len(m["content"])
            if n > CHAR_BUDGET and out:
                break
            out.append(m)
        out.reverse()
        while out and out[0]["role"] != "user":
            out.pop(0)
        return out

    def ask(self, text: str):
        text = text.strip()[:2000]
        with self._lock:
            self.S["gen"] += 1
            gen = self.S["gen"]
            self.S["msgs"].append({"role": "user", "content": text})
            del self.S["msgs"][:-MAX_MSGS]
            self.S["busy"] = True
            self.S["last"] = time.time()
        threading.Thread(target=self._run, args=(gen, text), daemon=True).start()
        return {"do": {"user": text, "busy": True}, "say": ""}

    def _run(self, gen: int, text: str):
        import ollama
        import brain
        think = wants_think(text)
        ctx = int(settings.get("sohbet_ctx") or 8192)
        msgs = [{"role": "system", "content": self.system_fn()}] + self._window()
        alive = lambda: self.S["gen"] == gen and self.active()
        q = queue.Queue()
        mute = {"on": False}

        def speaker():
            first = True
            while True:
                s = q.get()
                if s is None:
                    return
                if mute["on"] or not alive():
                    continue
                try:
                    cont, first = not first, False   # ilk cümle yeni HUD balonu, sonrakiler onun devamı
                    if SAY and say_as(self.persona, s, cont):         # sözü kesildi: kalan cümleler söylenmez, metin yine de yazılır
                        mute["on"] = True
                except Exception as e:
                    print("sohbet konuşma hatası:", type(e).__name__, flush=True)

        sp = threading.Thread(target=speaker, daemon=True)
        sp.start()
        full, buf, p_tok, p_th, last = "", "", "", "", 0.0
        noted_code = filler = False
        t0 = time.time()

        seen, loop, depth = set(), {"s": None}, {"n": 0}

        def push(sents):
            nonlocal noted_code
            for s in sents:
                if s == _CODE:
                    if not noted_code:
                        noted_code = True
                        q.put(self.code_note)
                    continue
                key = re.sub(r"\W+", " ", s.lower()).strip()
                if len(key) >= 20:                   # model aynı cümleyi tekrarlamaya başladı (döngü): üretimi kes, tekrarı söyleme
                    if key in seen:
                        loop["s"] = s
                        return
                    seen.add(key)
                s = _speakable(s)
                if s:
                    q.put(s)

        def flush(force=False):
            nonlocal p_tok, p_th, last
            now = time.time()
            if not force and now - last < 0.12:
                return
            d = {}
            if p_tok:
                d["tok"] = p_tok
            if p_th:
                d["th"] = p_th
            if d:
                self.notify(d)
            p_tok = p_th = ""
            last = now

        err = False
        try:
            if think:
                self.notify({"thinking": True})
            stream = ollama.chat(model=brain.MODEL, messages=msgs, stream=True, keep_alive="5m", **brain._extra(think),
                                 options={"temperature": 0.6 if think else 0.7, "top_p": 0.9, "num_ctx": ctx,
                                          "num_predict": 2200 if think else 900, "repeat_penalty": 1.1, "repeat_last_n": 256})
            for part in stream:
                if not alive():
                    break
                m = part.message
                th = getattr(m, "thinking", None) or ""
                ct = m.content or ""
                if th:
                    p_th += th
                    if not filler and not full and time.time() - t0 > 4:
                        filler = True
                        q.put(self.filler)
                if ct and self.strip_parens:         # küçük model parantez içinde sahne yönergesi yazar: akış sırasında atılır
                    out = []
                    for c in ct:
                        if c == "(":
                            depth["n"] += 1
                        elif c == ")" and depth["n"]:
                            depth["n"] -= 1
                        elif not depth["n"]:
                            out.append(c)
                    ct = re.sub(r"[ \t]{2,}", " ", "".join(out))
                    if not full and not ct.strip():
                        ct = ""
                if ct:
                    full += ct
                    buf += ct
                    p_tok += ct
                    sents, buf = _split(buf)
                    push(sents)
                    if loop["s"]:
                        break
                flush()
            if alive() and not loop["s"]:
                sents, buf = _split(buf, True)
                push(sents)
            if loop["s"]:                            # geçmişe ve sayfaya tekrarlanan kısım girmesin
                i = full.find(loop["s"])
                j = full.find(loop["s"], i + 1) if i >= 0 else -1
                if j > 0:
                    full = full[:j].rstrip()
        except Exception:
            import traceback
            traceback.print_exc()
            err = True
        flush(True)
        q.put(None)
        with self._lock:
            mine = self.S["gen"] == gen
            if mine:
                self.S["busy"] = False
                self.S["last"] = time.time()
                if full.strip():
                    self.S["msgs"].append({"role": "assistant", "content": full.strip()})
        if not mine or not self.active():
            return
        if err or not full.strip():
            msg = self.err_model if err else self.err_empty
            self.notify({"done": True, "text": msg, "err": True})
            if SAY:
                sp.join(timeout=60)
                say_as(self.persona, msg, False)
            return
        self.notify({"done": True, "text": full.strip()})


# ------------------------------------------------------------------ Jarvis sohbet modu (eski işlev adları korunur)
JARVIS = Chat("sohbet", _jarvis_system)
S = JARVIS.S
ask, reset, cancel, snapshot, init_payload = JARVIS.ask, JARVIS.reset, JARVIS.cancel, JARVIS.snapshot, JARVIS.init_payload
