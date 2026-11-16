"""Jarvis'in kendi müzik oynatıcısı: şarkı kuyruğu (yt-dlp ile ses akışı + ffplay, tarayıcı gerekmez). Ders müziği de buradan çalar.
Özellikler: 'X çal' (kuyruğu değiştirir), sıraya ekleme, sonraki / önceki, duraklat / devam, ders listesi döngüsü, çalan şarkı bilgisi."""
import random, re, shutil, subprocess, sys, threading, time

IDS = ["sdkXjrS14Jg", "rBR1nwYIFck", "Gj3AjW682Ew", "NMRhx71bGo4", "o96Do5VDwEU"]

_lock = threading.Lock()          # süreç başlatma kilidi
_qlock = threading.Lock()         # kuyruk kilidi
_stop = threading.Event()
_thread = None
_proc = None
_q: list = []                     # [{'id','title','artist','dur'}]
_i = 0
_loop_all = False
_jump = None
_repeat = False
_np = {"item": None, "t0": 0.0, "paused_at": None, "paused_total": 0.0}


def _py():
    return sys.executable.replace("pythonw", "python")


def resolve(query: str):
    """Arama sorgusu -> {'id','title','artist','dur'} ya da None (yt-dlp kütüphanesi, indirme yok)."""
    import yt_dlp
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True}) as y:
        info = y.extract_info(f"ytsearch1:{query}", download=False)
    entries = info.get("entries") or []
    if not entries:
        return None
    e = entries[0]
    return {"id": e["id"], "title": e.get("title") or query, "artist": e.get("channel") or e.get("uploader") or "", "dur": e.get("duration") or 0}


def _play_one(item: dict, stop: threading.Event) -> None:
    """Tek bir şarkıyı yt-dlp -> ffplay ile bir kez çalar (diske yazılmaz). Bitince ya da öldürülünce döner."""
    global _proc
    ffplay = shutil.which("ffplay") or "ffplay"
    with _lock:
        if stop.is_set():
            return
        dl = subprocess.Popen([_py(), "-m", "yt_dlp", "-q", "--no-warnings", "-f", "bestaudio", "-o", "-", f"https://music.youtube.com/watch?v={item['id']}"],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=0x08000000)
        p = _proc = subprocess.Popen([ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet", "-i", "-"], stdin=dl.stdout, creationflags=0x08000000)
        dl.stdout.close()
        _np.update(item=item, t0=time.time(), paused_at=None, paused_total=0.0)
    p.wait()
    dl.kill()


def _worker(stop: threading.Event) -> None:
    global _i, _jump
    fails = 0
    while not stop.is_set():
        with _qlock:
            if _i >= len(_q):
                if _loop_all and _q:
                    _i = 0
                else:
                    break
            item = _q[_i]
        t0 = time.time()
        try:
            _play_one(item, stop)
        except Exception as e:
            print("şarkı çalma hatası:", e, flush=True)
        if stop.is_set():
            return
        with _qlock:
            jumped = _jump is not None
            if jumped:
                _i, _jump = _jump, None
            elif not _repeat:
                _i += 1
        fails = 0 if time.time() - t0 > 20 or jumped else fails + 1
        if fails > max(4, len(_q) * 2):               # internet yoksa boşuna dönüp durma
            break
        if fails:
            stop.wait(2)
    if not stop.is_set():
        _np.update(item=None)


def set_repeat(on: bool) -> None:
    """Çalan şarkıyı tekrar tekrar çalar (ders listesi döngüsünden bağımsız)."""
    global _repeat
    _repeat = bool(on)


def repeat_on() -> bool:
    return _repeat


def _launch(items: list, loop: bool, start: int = 0) -> None:
    global _thread, _stop, _q, _i, _loop_all, _jump
    stop()
    _stop = threading.Event()
    with _qlock:
        _q, _i, _loop_all, _jump = list(items), max(0, min(int(start), max(0, len(items) - 1))), loop, None
    _thread = threading.Thread(target=_worker, args=(_stop,), daemon=True)
    _thread.start()


_VID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def play_items(items: list, loop: bool = True, start: int = 0, shuffle: bool = False) -> int:
    """Hazır (çözülmüş) şarkı listesini çalar: [{'id': 11 karakterlik YouTube kimliği, 'title', 'artist', 'dur'}]. Geçersiz kimlikler atlanır.
    shuffle: karıştırır (start yok sayılır). Dönen: çalınacak şarkı sayısı."""
    its = [{"id": i["id"], "title": str(i.get("title", ""))[:200], "artist": str(i.get("artist", ""))[:100], "dur": int(i.get("dur") or 0)}
           for i in items if isinstance(i, dict) and _VID.match(str(i.get("id", "")))]
    if not its:
        return 0
    if shuffle:
        random.shuffle(its)
        start = 0
    _launch(its, loop, start)
    return len(its)


def current_item():
    """Şu an çalan şarkı ({'id','title','artist','dur'}) ya da None."""
    it = _np["item"]
    return dict(it) if it and active() else None


def resolve_url(url: str):
    """YouTube video bağlantısı -> {'id','title','artist','dur'} ya da None (yalnızca youtube.com / youtu.be / music.youtube.com kimliği alınır)."""
    m = re.match(r"^https?://(?:www\.|m\.|music\.)?(?:youtube\.com/(?:watch\?(?:[^#]*&)?v=|shorts/|embed/)|youtu\.be/)([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])", str(url).strip())
    if not m:
        return None
    import yt_dlp
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as y:
        info = y.extract_info("https://www.youtube.com/watch?v=" + m.group(1), download=False)
    if not info or info.get("_type") == "playlist" or info.get("is_live"):
        return None
    return {"id": m.group(1), "title": info.get("track") or info.get("title") or m.group(1), "artist": info.get("artist") or info.get("channel") or info.get("uploader") or "",
            "dur": int(info.get("duration") or 0)}


def resolve_playlist(url: str, limit: int = 100):
    """YouTube çalma listesi bağlantısı -> (liste adı, [{'id','title','artist','dur'}]) ya da None. En fazla 'limit' şarkı."""
    m = re.match(r"^https?://(?:www\.|m\.|music\.)?youtube\.com/(?:playlist|watch)\?(?:[^#]*&)?list=([A-Za-z0-9_-]{10,64})", str(url).strip())
    if not m:
        return None
    import yt_dlp
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True, "playlistend": int(limit)}) as y:
        info = y.extract_info("https://www.youtube.com/playlist?list=" + m.group(1), download=False)
    out = []
    for e in (info or {}).get("entries") or []:
        if e and _VID.match(str(e.get("id", ""))) and e.get("duration") is not False:
            out.append({"id": e["id"], "title": e.get("title") or e["id"], "artist": e.get("channel") or e.get("uploader") or "", "dur": int(e.get("duration") or 0)})
    return ((info or {}).get("title") or "YouTube listesi", out[:int(limit)]) if out else None


def start() -> None:
    """Ders şarkı listesi: sırayla ve sonsuz döngüde."""
    _launch([{"id": v, "title": f"Ders şarkısı {n}", "artist": "", "dur": 0} for n, v in enumerate(IDS, 1)], True)


def start_custom(queries: list) -> int:
    """Kullanıcının şarkı listesi: ilk bulunan şarkı hemen çalmaya başlar, kalanlar arka planda aranıp kuyruğa eklenir; liste döngüde çalar.
    Dönen: ilk şarkının bulunup bulunmadığına göre listenin uzunluğu (0 = hiçbiri bulunamadı)."""
    first = None
    for k, q in enumerate(queries):
        try:
            it = resolve(q)
        except Exception as e:
            print("şarkı arama hatası:", e, flush=True)
            it = None
        if it:
            first = (k, it)
            break
    if not first:
        return 0
    _launch([first[1]], True)
    ev = _stop
    rest = queries[first[0] + 1:]

    def fill():
        for q in rest:
            if ev.is_set():
                return
            try:
                it = resolve(q)
            except Exception:
                continue
            if it:
                with _qlock:
                    if ev.is_set():
                        return
                    _q.append(it)
    threading.Thread(target=fill, daemon=True).start()
    return len(queries)


def _kill():
    with _lock:
        if _proc and _proc.poll() is None:
            resume()
            _proc.kill()


def stop() -> bool:
    running = bool(_thread and _thread.is_alive())
    _stop.set()
    _kill()
    _np.update(item=None)
    return running


def active() -> bool:
    return bool(_thread and _thread.is_alive() and not _stop.is_set())


def skip() -> bool:
    """Sonraki şarkı (kuyruğun sonundaysa çalma biter)."""
    global _jump
    if not active():
        return False
    with _qlock:
        _jump = _i + 1
        if _jump >= len(_q):
            _jump = 0 if _loop_all else len(_q)
    _kill()
    return True


def prev() -> bool:
    """İlk 5 saniyeden sonra baştan başlatır, değilse önceki şarkıya döner."""
    global _jump
    if not active():
        return False
    s = status()
    with _qlock:
        _jump = _i if (s and s["pos"] > 5) else max(0, _i - 1)
    _kill()
    return True


def pause() -> bool:
    if not active() or _np["paused_at"] is not None or not _proc or _proc.poll() is not None:
        return False
    try:
        import psutil
        psutil.Process(_proc.pid).suspend()
    except Exception:
        return False
    _np["paused_at"] = time.time()
    return True


def resume() -> bool:
    if _np["paused_at"] is None or not _proc:
        return False
    try:
        import psutil
        psutil.Process(_proc.pid).resume()
    except Exception:
        pass
    _np["paused_total"] += time.time() - _np["paused_at"]
    _np["paused_at"] = None
    return True


def status():
    """Çalan şarkı: {'title','artist','dur','pos','playing','index','total'} ya da None."""
    it = _np["item"]
    if not it or not active():
        return None
    end = _np["paused_at"] or time.time()
    return {"id": it.get("id", ""), "title": it.get("title", ""), "artist": it.get("artist", ""), "dur": it.get("dur", 0), "pos": max(0.0, end - _np["t0"] - _np["paused_total"]),
            "playing": _np["paused_at"] is None, "index": _i + 1, "total": len(_q), "repeat": _repeat}


def queue_titles() -> list:
    with _qlock:
        return [(("▶ " if n == _i else "") + (x.get("title") or "?")) for n, x in enumerate(_q)]


def play_query(query: str) -> str:
    """'X çal': şarkıyı arayıp kuyruğu değiştirir ve çalar. Dönen: bulunan şarkının adı ('' = bulunamadı)."""
    try:
        it = resolve(query)
    except Exception as e:
        print("şarkı arama hatası:", e, flush=True)
        return ""
    if not it:
        return ""
    _launch([it], False)
    return it["title"]


def enqueue(query: str) -> str:
    """Şarkıyı kuyruğun sonuna ekler; hiçbir şey çalmıyorsa çalmaya başlar. Dönen: şarkı adı ('' = bulunamadı)."""
    try:
        it = resolve(query)
    except Exception as e:
        print("şarkı arama hatası:", e, flush=True)
        return ""
    if not it:
        return ""
    if not active():
        _launch([it], False)
        return it["title"]
    with _qlock:
        _q.append(it)
    return it["title"]
