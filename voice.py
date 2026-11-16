"""Uyandırma ("Jarvis" / "Hey Jarvis"), konuşma tanıma (faster-whisper) ve seslendirme (Piper yerel / edge-tts).

- Uyandırma: openWakeWord "hey jarvis" modeli + kısa konuşmaları Whisper ile kontrol ederek tek başına "Jarvis".
  "Jarvis, YouTube aç" gibi tek nefeste söylenen komut da yakalanır (self.wake_command).
- Seslendirme konuşurken mikrofon dinlenir: "Hey Jarvis" denirse ya da stop_event gelirse Jarvis susar.
"""
import asyncio, collections, io, json, os, re, tempfile, threading, time, queue, wave
import numpy as np
import sounddevice as sd
import settings
from scipy.signal import butter, sosfilt, iirnotch, tf2sos

HERE = os.path.dirname(os.path.abspath(__file__))
DIAG_DIR = os.path.join(HERE, "diag")        # son tanıma ses parçaları (yalnızca bu bilgisayarda, en fazla 40 dosya)
DIAG_KEEP = 40


def _add_cuda_dlls():
    """pip ile kurulan cublas/cudnn DLL'lerini bulunabilir yap."""
    import site
    for base in site.getsitepackages():
        for sub in ("cublas", "cudnn"):
            p = os.path.join(base, "nvidia", sub, "bin")
            if os.path.isdir(p):
                os.add_dll_directory(p)
                os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")


_add_cuda_dlls()
SR = 16000
CHUNK = 1280  # 80 ms
EDGE_VOICES = {"tr": "tr-TR-AhmetNeural", "en": "en-GB-RyanNeural"}     # İngilizcede filmdeki gibi İngiliz aksanı
# Filmdeki JARVIS: sakin, biraz yavaş ve kalın
EDGE_TUNE = {"tr": ("-4%", "-6Hz"), "en": ("-3%", "-4Hz")}
PERSONA = {"name": None}          # main.py: kişilik modu açıkken adı ("ultron"); sesi Jarvis'ten ayırır
# Kişilik sesleri: büyük SSML perde kaydırmaları (ör. -32Hz) sesi yapay/robotik yapıyordu. Artık sentez doğal perdeye yakın yapılır,
# kalınlık/incelik PERSONA_SHAPE'teki "speed" ile verilir (ses biraz yavaş/hızlı çalınır: perde ve tını birlikte kayar, başka bir insan
# sesi gibi duyulur). "fx" Jarvis'in metalik efektinin ne kadarının uygulanacağıdır (0 = hiç; kadın seslerde efekt yapay duruyordu).
PERSONA_TUNE = {"ultron": {"tr": ("-3%", "-3Hz"), "en": ("-2%", "-3Hz")},
                "friday": {"tr": ("+2%", "+0Hz"), "en": ("+1%", "+0Hz")},
                "luna": {"tr": ("-9%", "+0Hz"), "en": ("-8%", "+0Hz")}}
PERSONA_SHAPE = {"ultron": {"speed": 0.89, "fx": 0.4},      # ~2 yarım ton kalın, %11 yavaş, hafif metal
                 "friday": {"speed": 1.0, "fx": 0.0},       # olduğu gibi, canlı
                 "luna": {"speed": 1.035, "fx": 0.0}}       # bir tık ince; hız "-9%" ile dengelenir, sakin kalır
PERSONA_VOICE = {"friday": {"tr": "tr-TR-EmelNeural", "en": "en-IE-EmilyNeural"},   # kadın ses (Friday'in İrlandalı aksanı); Ultron Jarvis'in erkek sesini kalınlaştırır
                 "luna": {"tr": "tr-TR-EmelNeural", "en": "en-GB-SoniaNeural"}}     # kadın ses, Friday'den farklı aksan/ton (PERSONA_TUNE ile)


ELEVEN_VOICE = "onwK4e9ZLuTAKqWW03F9"     # "Daniel": ElevenLabs hazır kütüphanesinden sakin, derin İngiliz erkek sesi
ELEVEN_MODEL = "eleven_multilingual_v2"   # Türkçe ve İngilizceyi aynı sesle okur


def _elevenlabs(text, api_key, voice_id) -> bytes:
    """ElevenLabs REST (SDK gerekmez). Hata olursa istisna fırlatır; çağıran sıradaki motora geçer."""
    import urllib.request
    body = json.dumps({"text": text, "model_id": ELEVEN_MODEL,
                       "voice_settings": {"stability": 0.55, "similarity_boost": 0.8, "style": 0.15, "use_speaker_boost": True}}).encode()
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128", data=body,
                                 headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


def jarvis_fx(x, sr, amt=1.0):
    """Filmdeki gibi hafif 'yapay zekâ' tınısı: kısa metalik oda yankısı + çok hafif koro (abartısız)."""
    rng = np.random.default_rng(7)
    n = int(sr * 0.09)
    ir = rng.normal(0, 1, n) * np.exp(-np.linspace(0, 7, n))
    ir[0] = 0
    wet = np.convolve(x, ir)[:len(x)]
    wet /= np.abs(wet).max() + 1e-9
    d = int(sr * 0.012)
    chorus = np.concatenate([np.zeros(d), x[:-d]])
    y = x + amt * (0.10 * wet * np.abs(x).max() + 0.18 * chorus)
    return y / (np.abs(y).max() + 1e-9) * 0.9


def _mp3_to_wav_fx(mp3: bytes, speed: float = 1.0, fx: float = 1.0) -> bytes:
    """MP3 -> 24 kHz WAV. speed != 1: ses 24000/speed Hz'e örneklenip 24 kHz diye yazılır (speed<1 = daha kalın ve yavaş). fx: efekt miktarı."""
    import av
    c = av.open(io.BytesIO(mp3))
    res = av.AudioResampler(format="flt", layout="mono", rate=int(round(24000 / speed)))
    x = np.concatenate([f.to_ndarray().ravel() for fr in c.decode(audio=0) for f in res.resample(fr)])
    if fx > 0:
        x = jarvis_fx(x, 24000, fx)
    else:
        x = x / (np.abs(x).max() + 1e-9) * 0.9
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm.tobytes())
    return buf.getvalue()
def _piper_like_edge(wav: bytes) -> bytes:
    """Yerel (Piper) sesi, internet (Edge) 'JARVIS' sesine olabildiğince yaklaştırır: biraz daha kalın ve yavaş (örnekleme hızı %5 düşürülerek)
    ve aynı JARVIS efekti. İki ses farklı modeller olduğu için birebir aynı olamaz; ama tını ve tempo yakınlaşır."""
    if not wave_cfg_fx():
        return wav
    with wave.open(io.BytesIO(wav), "rb") as r:
        sr, ch, sw = r.getframerate(), r.getnchannels(), r.getsampwidth()
        raw = r.readframes(r.getnframes())
    if sw != 2:
        return wav
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    pcm = (np.clip(jarvis_fx(x, sr), -1, 1) * 32767).astype(np.int16)
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(sr * 0.95)); w.writeframes(pcm.tobytes())
    return out.getvalue()


def wave_cfg_fx() -> bool:
    return bool(settings.get("jarvis_fx"))


PIPER_VOICES = {"tr": "tr_TR-dfki-medium", "en": "en_GB-alan-medium"}
# Whisper sessizlik/gürültüde eğitim verisinden bu cümleleri uydurur
HALLUCINATION = re.compile(r"(altyazı|alt yazı|m\.?\s?k\.?$|izlediğiniz için|abone ol|izlediğin için|bir sonraki videoda|"
                           r"sesli betimleme|amara\.org|subtitles|thanks for watching|beğenmeyi unutmay)", re.I)
PROMPT = ("Jarvis, YouTube aç. Spotify aç. Müzik çal. Sezen Aksu çal. WhatsApp mesajlarını oku. "
          "Wi-Fi adı ne? Chrome kapat. Saat kaç? Ses yüzde elli yap. İnternette araştır.")
PROMPT_EN = "Jarvis, open YouTube. Play some music. What time is it? Read my WhatsApp messages. Search the web."
# Konuşmanın BAŞINDA söylenen "Jarvis" (Whisper'ın olası yazımlarıyla); geri kalanı komut olarak alınır
WAKE_RE = re.compile(r"^\W*(?:hey|hay|hei|he)?\W*(?:[jcçg]ar?[vbw][iıy][sz]|[jc]erv[iı]s|javis|jarves)\b\W*(.*)$",
                     re.I | re.S)


def speech_text(text: str, lang: str = "tr") -> str:
    """Seslendirmeden önce metni düzelt: işaretleri ve sesli okunuşta tuhaf duran kalıpları temizle."""
    text = re.sub(r"[*_`#>]|\[.*?\]\(.*?\)|https?://\S+", "", text)
    text = re.sub(r"[\"“”]", "", text)
    text = re.sub("[🌀-🫿☀-➿️]", "", text)      # emoji okunmasın
    if lang == "tr":
        text = re.sub(r"%\s?(\d+)", r"yüzde \1", text)
        text = re.sub(r"(\d+)\s?%", r"yüzde \1", text)
        text = re.sub(r"\bMiB\b|\bMB\b", "megabayt", text)
        text = re.sub(r"\bGB\b", "gigabayt", text)
        text = re.sub(r"(\d+)\s?°C?", r"\1 derece", text)
    else:
        text = re.sub(r"%\s?(\d+)", r"\1 percent", text)
    return re.sub(r"\s+", " ", text).strip()


class Voice:
    last_lang = "tr"

    def __init__(self, on_level=None):
        from faster_whisper import WhisperModel
        import openwakeword
        from openwakeword.model import Model
        openwakeword.utils.download_models(["hey_jarvis"])
        self.ww = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        try:
            self.stt = WhisperModel("large-v3-turbo", device="cuda", compute_type="int8_float16")   # daha az VRAM: LLM ile birlikte sığsın
            # transcribe tembeldir; gerçekten çalıştığını görmek için sonucu tüket
            list(self.stt.transcribe(np.random.randn(SR * 2).astype(np.float32) * 0.1, language="tr")[0])
        except Exception:
            self.stt = WhisperModel("small", device="cpu", compute_type="int8")
        self.q = queue.Queue()
        self.tap = None
        self.on_level = on_level
        self.wake_command = None
        self.speaking = False
        self.interrupted = False
        self.stop_event = threading.Event()
        self._speak_lock = threading.Lock()
        self._piper = {}
        self.unclear = False
        self._sos = np.vstack([tf2sos(*iirnotch(f0, 25, fs=SR)) for f0 in (60, 120, 180)] +
                              [butter(2, 50, btype="highpass", fs=SR, output="sos")])   # şebeke uğultusu + rumble
        self._zi = np.zeros((self._sos.shape[0], 2))
        self._floor = None
        self._hist = collections.deque(maxlen=150)
        self._last_chunk = time.time()
        self.stream = None
        self.waiting = False         # yalnızca "Hey Jarvis" beklenirken True (pencere kapalı/gizli)
        self.restore_muted = False   # kapalı mikrofonla "Hey Jarvis" ile açılan oturum bitince yeniden kapanır
        self._open_mic()
        threading.Thread(target=self._mic_watchdog, daemon=True).start()
        try:
            self._piper_voice("tr")          # ilk konuşma gecikmesin diye önceden yükle
        except Exception:
            pass

    def _on_audio(self, data, *_):
        self._last_chunk = time.time()
        if getattr(self, "muted", False):
            # mikrofon "kapalı": ses yalnızca pencere kapalıyken "Hey Jarvis" uyandırma modeline gider. Pencere açıkken hiçbir ses işlenmez,
            # kuyruğa bile girmez (konuşma tanıma, kayıt ve görselleştirici de çalışmaz).
            if self.waiting:
                self.q.put(np.clip(data[:, 0], -32768, 32767).astype(np.int16))
            return
        x = data[:, 0].astype(np.float32)
        tp = getattr(self, "tap", None)
        if tp:
            try:
                tp(x)               # müzik görselleştirici: yalnızca frekans sayıları çıkarılır, ses saklanmaz
            except Exception:
                pass
        y, self._zi = sosfilt(self._sos, x, zi=self._zi)       # düşük frekanslı uğultuyu süz
        rms = float(np.sqrt(np.mean(y ** 2)))
        self._hist.append(rms)
        self._floor = float(np.percentile(self._hist, 30))   # son ~12 sn'nin alt yüzdeliği: sessiz odada gürültü, müzik varken müziğin seviyesi
        self.q.put(np.clip(y, -32768, 32767).astype(np.int16))

    def _open_mic(self):
        if self.stream is not None:
            try:
                self.stream.close()
            except Exception:
                pass
        sd._terminate()                      # cihaz listesini tazele (USB kulaklık yeniden takılmış olabilir)
        sd._initialize()
        self.stream = sd.InputStream(samplerate=SR, channels=1, dtype="int16", blocksize=CHUNK, callback=self._on_audio)
        self.stream.start()
        self._last_chunk = time.time()
        print("Mikrofon açıldı:", sd.query_devices(kind="input")["name"], flush=True)

    def _mic_watchdog(self):
        """Mikrofondan 3 sn ses parçası gelmezse akış ölmüştür (USB koptu vb.): yeniden aç."""
        while True:
            time.sleep(2)
            if time.time() - self._last_chunk > 3:
                try:
                    self._open_mic()
                except Exception as e:
                    print("Mikrofon açılamadı, tekrar denenecek:", e, flush=True)

    def _flush(self):
        while not self.q.empty():
            self.q.get_nowait()

    # ------------------------------------------------------------------ uyandırma
    def wait_wake(self, poll=None) -> bool:
        """'Jarvis' / 'Hey Jarvis' bekler. poll() True dönerse (yazılı/telefon komutu geldi) False ile çıkar.
        'Jarvis, YouTube aç' gibi tek nefeste söylenen komut self.wake_command'a yazılır."""
        self._flush()
        self.waiting = True
        try:
            return self._wait_wake(poll)
        finally:
            self.waiting = False
            self._flush()

    def _wait_wake(self, poll=None) -> bool:
        self._flush()
        self.ww.reset()
        self.wake_command = None
        seg, pre, silent, floor = [], [], 0, None
        while True:
            if poll and poll():
                return False
            try:
                chunk = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            if self.speaking:                       # hatırlatma vb. konuşurken kendi sesini duymasın
                seg, pre = [], []
                continue
            if max(self.ww.predict(chunk).values()) > 0.5:
                return True
            if getattr(self, "muted", False):
                continue                            # kapalı modda konuşma metne çevrilmez; yalnızca uyandırma modeli bakar
            rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
            floor = self._floor if self._floor is not None else rms
            if rms > max(45, floor * 4):
                if not seg:
                    seg = pre[-3:]                  # kelimenin başı kesilmesin
                seg.append(chunk)
                silent = 0
            elif seg:
                seg.append(chunk)
                silent += 1
                if silent >= 7:                     # ~0,5 sn sessizlik: konuşma bitti
                    n = len(seg)
                    audio, seg = seg, []
                    if 4 <= n <= 90 and self._is_wake(audio):   # 0,3–7 sn arası konuşmalar
                        return True
            pre = (pre + [chunk])[-5:]
            if len(seg) > 90:                       # çok uzun (müzik/TV): kontrol etme
                seg = []

    def _has_speech(self, audio) -> bool:
        """Silero VAD (CPU): gerçekten insan konuşması var mı? Müzik, TV, tıkırtı ve gürültü GPU'daki Whisper'a hiç gitmesin."""
        try:
            from faster_whisper.vad import get_speech_timestamps, VadOptions
            ts = get_speech_timestamps(audio.astype(np.float32), VadOptions(min_speech_duration_ms=250, min_silence_duration_ms=300))
            return sum(t["end"] - t["start"] for t in ts) >= 0.3 * SR
        except Exception:
            return True                      # dedektör çalışmazsa eskisi gibi davran

    @staticmethod
    def _prep(audio):
        """Kısık sesi (tepe < %60) tepe %80'e yükselt; üst sınır 80 kat (mikrofon çok kısık kayıt yapabiliyor)."""
        peak = float(np.abs(audio).max()) if len(audio) else 0.0
        if 0 < peak < 0.6:
            audio = audio * min(80.0, 0.8 / peak)
        return audio

    def _diag(self, raw, text, lang, conf, note=""):
        """Tanıma sonucunu günlüğe yaz ve ses parçasını yerel 'diag' klasörüne kaydet (en son 40).
        Gizli mod (rapor modu açıkken): ne söylenen metin günlüğe yazılır ne de ses parçası kaydedilir."""
        priv = getattr(self, "is_private", None)
        if priv and priv():
            print(f"TANI: {len(raw)/SR:.1f}sn [gizli mod: metin ve ses kaydedilmedi]", flush=True)
            return
        a = raw
        rms = float(np.sqrt(np.mean((a * 32768) ** 2))) if len(a) else 0.0
        print(f"TANI: {len(a)/SR:.1f}sn tepe={int(float(np.abs(a).max())*32768) if len(a) else 0} rms={rms:.0f} dil={lang} "
              f"güven={conf:.2f} {note} metin={text!r}", flush=True)
        if not settings.get("save_clips"):
            return
        try:
            os.makedirs(DIAG_DIR, exist_ok=True)
            name = time.strftime("%m%d_%H%M%S") + ("_bos" if not text else "") + ".wav"
            with wave.open(os.path.join(DIAG_DIR, name), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
                w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
            old = sorted(f for f in os.listdir(DIAG_DIR) if f.endswith(".wav"))
            for f in old[:-DIAG_KEEP]:
                os.remove(os.path.join(DIAG_DIR, f))
        except OSError:
            pass

    def _is_wake(self, frames) -> bool:
        audio = self._prep(np.concatenate(frames).astype(np.float32) / 32768.0)
        if not self._has_speech(audio):
            return False
        try:
            segs, _ = self.stt.transcribe(audio, language="tr", beam_size=1, vad_filter=True,
                                          condition_on_previous_text=False, no_speech_threshold=0.6)
            text = " ".join(s.text for s in segs if s.no_speech_prob < 0.6 and s.avg_logprob > -1.0).strip()
        except Exception:
            return False
        m = WAKE_RE.match(text)
        if not m:
            return False
        rest = m.group(1).strip(" .,!?")
        if len(rest) > 2:
            full = self.transcribe(audio) or ""          # dili algılayarak komutu doğru yaz
            fm = WAKE_RE.match(full)
            cmd = (fm.group(1) if fm else full).strip(" .,!?")
            self.wake_command = cmd or None
        return True

    # ------------------------------------------------------------------ dinleme
    def listen(self, no_speech_timeout=7.0, max_len=20.0, stop=None):
        """Kullanıcı konuşup susana kadar kaydeder, metne çevirir. Konuşma yoksa None. Mikrofon kapalıysa hiçbir şey dinlenmez."""
        if getattr(self, "muted", False):
            time.sleep(0.25)
            return None
        self._flush()
        frames, started, silent, t0 = [], False, 0, time.time()
        self.unclear = False
        floor, pre = None, []
        while time.time() - t0 < max_len:
            if stop and stop() and not started:      # yazılı/telefon komutu geldi ya da pencere kapatıldı
                return None
            if self.speaking:                        # Jarvis konuşurken (örn. ders anlatımı) kendi sesini komut sanmasın
                self._flush()
                frames, started, silent, pre = [], False, 0, []
                time.sleep(0.1)
                continue
            try:
                chunk = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
            floor = self._floor if self._floor is not None else rms     # oda gürültüsü akıştan sürekli izleniyor
            loud = rms > max(45, floor * 4)
            if self.on_level:
                self.on_level(min(1.0, rms / 6000))
            if loud:
                if not started:
                    frames = pre[-3:]               # kelimenin başı kesilmesin
                started, silent = True, 0
            elif started:
                silent += 1
            pre = (pre + [chunk])[-4:]
            if started:
                frames.append(chunk)
                if silent > 12:  # ~1 sn sessizlik
                    break
            elif time.time() - t0 > no_speech_timeout:
                return None
        if not frames:
            return None
        audio = np.concatenate(frames).astype(np.float32) / 32768.0
        if len(frames) < 5:            # 0.4 sn'den kısa ses: tıklama/gürültü
            return None
        return self.transcribe(audio)

    def transcribe(self, audio):
        """Konuşmayı metne çevirir; Türkçe mi İngilizce mi olduğunu algılar (self.last_lang).
        Konuşma var ama güvenilir anlaşılamadıysa None döner ve self.unclear=True olur."""
        raw = audio
        audio = self._prep(audio)                      # alçak sesli konuşmayı yükselt
        self.unclear = False
        if not self._has_speech(audio):                # konuşma yok (müzik/gürültü): GPU'yu hiç çalıştırma
            self._diag(raw, "", "tr", 0.0, "(konuşma yok, atlandı)")
            return None
        try:
            det, prob, _ = self.stt.detect_language(audio)
        except Exception:
            det, prob = "tr", 0.0
        text, conf, lang = self._decode(audio, "tr"), None, "tr"
        text, conf = text
        # Kısık Türkçe cümleler sık sık İngilizce sanılıyor ve uydurma İngilizce çıkıyor: İngilizceye yalnızca güçlü kanıtla geç
        if (det == "en" and prob > 0.6) or conf < -0.7:
            t2, c2 = self._decode(audio, "en")
            if det == "en" and prob > 0.6 and c2 > conf + 0.15 and len(t2) >= 2:
                text, conf, lang = t2, c2, "en"
        if HALLUCINATION.search(text) or len(text) < 2:
            self._diag(raw, "", lang, conf, f"(uydurma/boş: {text!r})")
            return None
        if conf < -0.8:                                # yanlış duyulmuş olabilir: tahmin yürütme, sor
            self.unclear = True
            self._diag(raw, text, lang, conf, "(belirsiz)")
            return None
        self.last_lang = lang
        self._diag(raw, text, lang, conf, f"(dil algısı {det} {prob:.2f})")
        return text

    def _decode(self, audio, lang):
        """(metin, ortalama güven) döndürür."""
        segs, _ = self.stt.transcribe(audio, language=lang, vad_filter=True, beam_size=5,
                                      condition_on_previous_text=False,
                                      initial_prompt=PROMPT_EN if lang == "en" else PROMPT,
                                      no_speech_threshold=0.5)
        segs = [s for s in segs if s.no_speech_prob < 0.5]
        text = " ".join(s.text.strip() for s in segs if s.avg_logprob > -1.0).strip()
        conf = sum(s.avg_logprob * len(s.text) for s in segs) / max(1, sum(len(s.text) for s in segs)) if segs else -9.0
        return text, conf

    def transcribe_bytes(self, data: bytes):
        """Telefondan gelen kayıt (webm/ogg/mp4) -> metin."""
        from faster_whisper import decode_audio
        audio = decode_audio(io.BytesIO(data), sampling_rate=SR)
        if len(audio) < SR * 0.4:
            return None
        return self.transcribe(audio)

    # ------------------------------------------------------------------ seslendirme
    def _piper_voice(self, lang):
        if lang not in self._piper:
            from piper import PiperVoice
            self._piper[lang] = PiperVoice.load(os.path.join(HERE, "voices", PIPER_VOICES[lang] + ".onnx"))
        return self._piper[lang]

    def _synth(self, text, lang):
        """(ses baytları, mime) döndürür. Seçili motor çalışmazsa diğerine geçer."""
        # Ses motoru config.json'daki "tts" ayarından seçilir: "edge" (varsayılan, filmdeki JARVIS tınısı; internet gerekir) → olmazsa yerel Piper;
        # "piper" → yalnızca yerel; "elevenlabs" → anahtar girilmişse ElevenLabs, olmazsa Edge, sonra Piper.
        # (2026-10-24: bu satır bir ara 'daima Piper' olarak sabitlenmişti, ayar yok sayılıyor ve ses eskisinden farklı çıkıyordu.)
        pref = settings.get("tts")
        engines = {"edge": ["edge", "piper"], "elevenlabs": ["elevenlabs", "edge", "piper"]}.get(pref, ["piper", "edge"])
        for eng in engines:
            try:
                if eng == "piper":
                    buf = io.BytesIO()
                    with wave.open(buf, "wb") as w:
                        self._piper_voice(lang).synthesize_wav(text, w)
                    return _piper_like_edge(buf.getvalue()), "audio/wav"
                elif eng == "elevenlabs":
                    api_key = os.environ.get("ELEVENLABS_API_KEY") or settings.get("elevenlabs_api_key")
                    if not api_key or "YOUR_API_KEY" in str(api_key):
                        continue
                    audio = _elevenlabs(text, api_key, settings.get("elevenlabs_voice_id") or ELEVEN_VOICE)
                    if audio:
                        # ElevenLabs returns MP3; optionally apply FX if enabled
                        if settings.get("jarvis_fx"):
                            return _mp3_to_wav_fx(audio), "audio/wav"
                        return audio, "audio/mpeg"
                else:  # edge TTS
                    persona = PERSONA["name"]
                    vname = (PERSONA_VOICE.get(persona) or {}).get(lang) or EDGE_VOICES.get(lang, EDGE_VOICES["tr"])
                    dk = f"{lang}/{persona}" if persona in PERSONA_VOICE else lang      # kişiliğin sesi bozulursa yalnızca o sesin yedeği devreye girer
                    if time.time() < self._edge_down.get(dk, 0):
                        continue                          # bu dilin Edge sesi az önce ses vermedi: sıradaki motora hemen geç (her cümlede bekleme olmasın)
                    import edge_tts
                    tune = PERSONA_TUNE.get(PERSONA["name"]) or EDGE_TUNE
                    rate, pitch = tune.get(lang, tune["tr"])
                    async def one():
                        out = b""
                        try:
                            async for ch in edge_tts.Communicate(text, vname, rate=rate, pitch=pitch).stream():
                                if ch["type"] == "audio":
                                    out += ch["data"]
                        except edge_tts.exceptions.NoAudioReceived:
                            return None                    # sunucu 'bu sesten ses yok' dedi (geçici ağ hatasından farklı)
                        return out
                    async def hedged():
                        """Edge may fail transiently; retry with hedging."""
                        tasks, no_audio = [], 0
                        try:
                            for k in range(4):
                                tasks.append(asyncio.ensure_future(one()))
                                done, _ = await asyncio.wait(tasks, timeout=1.6 if k < 3 else 10, return_when=asyncio.FIRST_COMPLETED)
                                for d in done:
                                    if not d.cancelled() and d.exception() is None and d.result():
                                        return d.result()
                                    if not d.cancelled() and d.exception() is None and d.result() is None:
                                        no_audio += 1
                                if no_audio >= 2:
                                    return b""             # iki kez 'ses yok': bu ses şu an çalışmıyor, boşuna bekleme
                                tasks = [t for t in tasks if t not in done]
                            return b""
                        finally:
                            for t in tasks:
                                t.cancel()
                    data = asyncio.run(hedged())
                    if data:
                        self._edge_down.pop(dk, None)
                        shape = PERSONA_SHAPE.get(persona)
                        if shape:                          # kişilik sesi: doğal sentez + hafif biçimlendirme (bkz. PERSONA_SHAPE)
                            fx = shape["fx"] if settings.get("jarvis_fx") else 0.0
                            if fx > 0 or shape["speed"] != 1.0:
                                return _mp3_to_wav_fx(data, shape["speed"], fx), "audio/wav"
                            return data, "audio/mpeg"
                        if settings.get("jarvis_fx"):
                            return _mp3_to_wav_fx(data), "audio/wav"
                        return data, "audio/mpeg"
                    self._edge_down[dk] = time.time() + self.EDGE_RETRY_S      # ses gelmedi (ör. Microsoft'ta Ahmet sesi bozuk): 10 dk sonra tekrar dene
                    print(f"SES: Edge sesi ({vname}) ses vermedi, {self.EDGE_RETRY_S // 60} dakika yerel Piper sesi kullanılacak", flush=True)
            except Exception:
                import traceback
                traceback.print_exc()
                if eng == "edge":
                    self._edge_down[locals().get("dk", lang)] = time.time() + self.EDGE_RETRY_S
        return None, None

    EDGE_RETRY_S = 600
    _edge_down: dict = {}                                  # dil -> Edge'in yeniden deneneceği zaman

    # Sentez önbelleği: aynı cümle tekrar istenince ağa gitmeden anında çalınır. Yalnızca bellekte tutulur (diske yazılmaz).
    _cache: dict = {}
    _CACHE_MAX = 120

    def clear_cache(self):
        self._cache.clear()

    def prepare(self, text: str, lang: str = "tr"):
        """Metni seslendirmeye hazırlar: (ses baytları, mime) ya da None. Çalmadan önce, başka iş sürerken yapılabilir."""
        text = speech_text(text, lang)
        if not text:
            return None
        key = (text, lang, settings.get("tts"), bool(settings.get("jarvis_fx")), PERSONA["name"])
        hit = self._cache.get(key)
        if hit:
            return hit
        data, mime = self._synth(text, lang)
        if not data:
            return None
        if len(self._cache) >= self._CACHE_MAX:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = (data, mime)
        return data, mime

    def play(self, data: bytes, mime: str, on_audio=None) -> bool:
        """Hazır sesi çalar. Konuşurken 'Hey Jarvis' denirse ya da stop_event gelirse susar; susturulduysa True döner."""
        with self._speak_lock:
            if on_audio:
                on_audio(data, mime)          # telefona da gönderilsin
            import pygame, uuid
            path = os.path.join(tempfile.gettempdir(), "jarvis_tts_" + uuid.uuid4().hex[:8] + (".wav" if mime == "audio/wav" else ".mp3"))
            with open(path, "wb") as f:
                f.write(data)
            self.stop_event.clear()
            self.interrupted = False
            self.speaking = True
            self._flush()
            self.ww.reset()
            try:
                if not pygame.mixer.get_init():          # çıkış cihazı yalnızca konuşurken açılır; boşta açık akış bazı kulaklıklarda cızırtı yapar
                    pygame.mixer.init()
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
                t0 = time.time()
                while pygame.mixer.music.get_busy():
                    if self.stop_event.is_set():
                        self.interrupted = True
                    elif not getattr(self, "muted", False):
                        try:
                            chunk = self.q.get(timeout=0.05)
                            # ilk yarım saniye kendi sesinin başlangıcı; eşik yüksek, kendi 'Jarvis' deyişine kanmasın
                            if time.time() - t0 > 0.5 and max(self.ww.predict(chunk).values()) > 0.7:
                                self.interrupted = True
                        except queue.Empty:
                            pass
                    else:
                        time.sleep(0.05)
                    if self.interrupted:
                        pygame.mixer.music.stop()
                        break
                pygame.mixer.music.unload()
                pygame.mixer.quit()
                time.sleep(0.2)                     # odadaki yankı sönsün, kendi sesini komut sanmasın
            finally:
                self.speaking = False
                self._flush()
                try:
                    os.remove(path)
                except OSError:
                    pass
            return self.interrupted

    def speak(self, text: str, lang: str = "tr", on_audio=None) -> bool:
        """Metni seslendirir (hazırla + çal). Susturulduysa True döner."""
        prep = self.prepare(text, lang)
        if not prep:
            return False
        return self.play(prep[0], prep[1], on_audio)
