import os, sys
os.environ.setdefault("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--autoplay-policy=no-user-gesture-required")
# pythonw ile (konsolsuz) çalışırken stdout/stderr yok; kütüphaneler yazınca çökmesin, log dosyasına gitsin
_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.log")
try:
    if os.path.getsize(_LOG) > 5 * 1024 * 1024:       # günlük sonsuza kadar büyümesin
        os.replace(_LOG, _LOG + ".1")
except OSError:
    pass
_log = open(_LOG, "a", encoding="utf-8", buffering=1)
if sys.stdout is None or sys.stderr is None or "pythonw" in os.path.basename(sys.executable).lower():
    sys.stdout = sys.stderr = _log


def _single_instance():
    """Aynı anda yalnızca bir Jarvis çalışır. İkinci kopya da mikrofonu dinleyip her cevabı ikinci kez söylüyordu
    (2026-10-11: açılışta iki kopya başlamıştı). Kilit, işlem kapanınca Windows tarafından kendiliğinden bırakılır."""
    if os.name != "nt":
        return
    import ctypes
    k32 = ctypes.windll.kernel32
    k32.CreateMutexW.restype = ctypes.c_void_p
    h = k32.CreateMutexW(None, False, "Local\\JarvisAsistanTekKopya")
    if h and k32.GetLastError() == 183:          # ERROR_ALREADY_EXISTS: başka bir Jarvis zaten açık
        print("JARVIS: zaten çalışan bir kopya var, bu kopya kapanıyor.", flush=True)
        os._exit(0)
    globals()["_INSTANCE_LOCK"] = h


if __name__ == "__main__":
    _single_instance()
"""Jarvis ana program: arayüz sunucusu (yalnızca localhost) + ses döngüsü."""
import re, asyncio, json, os, queue, secrets, subprocess, threading, random, time
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

PORT = 8765
HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = secrets.token_urlsafe(24)          # her açılışta yeni; başka siteler WebSocket'e bağlanamasın
ALLOWED_ORIGIN = f"http://127.0.0.1:{PORT}"

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
clients: set[WebSocket] = set()
loop: asyncio.AbstractEventLoop | None = None
text_in: "queue.Queue[str]" = queue.Queue()
VOICE = None


@app.get("/timer")
def timer_page():
    return FileResponse(os.path.join(HERE, "ui", "timer.html"))


@app.get("/code")
def code_page():
    return FileResponse(os.path.join(HERE, "ui", "code.html"))


@app.get("/scene/{kind}")
def scene_page(kind: str):
    import scenes
    from fastapi.responses import PlainTextResponse
    if kind not in scenes.KINDS:
        return PlainTextResponse("yok", status_code=404)
    page = "scene_lab.html" if kind in ("kimya", "biyoloji") else "scene_sci.html" if kind in ("fizik", "matematik", "astronomi", "jeoloji") else f"scene_{kind}.html"
    return FileResponse(os.path.join(HERE, "ui", page))


@app.get("/illusion")
def illusion_page():
    return FileResponse(os.path.join(HERE, "ui", "illusion.html"))


@app.get("/hero")
def hero_page():
    return FileResponse(os.path.join(HERE, "ui", "hero.html"))


@app.get("/kit/{name}")
def kit_file(name: str):
    """Mod ve laboratuvar sayfalarının ortak arayüz kiti (yalnızca bu iki dosya sunulur)."""
    from fastapi.responses import PlainTextResponse
    if name not in ("scene_kit.css", "scene_kit.js", "modes.css", "modes.js", "stark.css"):
        return PlainTextResponse("yok", status_code=404)
    return FileResponse(os.path.join(HERE, "ui", name), headers={"Cache-Control": "no-cache"})


@app.get("/vendor/maplibre/{name}")
def maplibre_file(name: str):
    """Dünya haritası modunun MapLibre GL kütüphanesi (BSD lisansı, npm 5.24.0, bütünlüğü doğrulandı). Yalnızca bu üç dosya sunulur."""
    from fastapi.responses import PlainTextResponse
    if name not in ("maplibre-gl-csp.js", "maplibre-gl-csp-worker.js", "maplibre-gl.css"):
        return PlainTextResponse("yok", status_code=404)
    return FileResponse(os.path.join(HERE, "ui", "vendor", "maplibre", name), headers={"Cache-Control": "max-age=86400"})


@app.get("/vendor/three/{name}")
def three_file(name: str):
    """Elektronik laboratuvarının 3B editörü için three.js (yalnızca three.min.js sunulur)."""
    from fastapi.responses import PlainTextResponse
    if name != "three.min.js":
        return PlainTextResponse("yok", status_code=404)
    return FileResponse(os.path.join(HERE, "ui", "vendor", "three", name), headers={"Cache-Control": "max-age=86400"})


@app.get("/fonts/{name}")
def font_file(name: str):
    """Kur'an modunun mushaf yazı tipi (Amiri Quran, OFL). Yalnızca bu dosya sunulur."""
    from fastapi.responses import PlainTextResponse
    if name != "AmiriQuran.ttf":
        return PlainTextResponse("yok", status_code=404)
    return FileResponse(os.path.join(HERE, "ui", "fonts", name), media_type="font/ttf", headers={"Cache-Control": "max-age=86400"})


@app.get("/kit-help/{kind}")
def kit_help(kind: str):
    """Komut paleti: o modun kılavuzdaki örnek komutları."""
    import scene_kit
    from fastapi.responses import JSONResponse
    return JSONResponse(scene_kit.help_for(kind[:20]))


@app.get("/mirror")
def mirror_page():
    return FileResponse(os.path.join(HERE, "ui", "mirror.html"))


@app.get("/guide")
def guide_page():
    return FileResponse(os.path.join(HERE, "ui", "guide.html"))


@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "ui", "index.html"))


@app.websocket("/mws")
async def mws(sock: WebSocket):
    """Ekran yansıtma yayını (telefon /mirror sayfası). /ws ile aynı kapı: doğru Origin + her açılışta değişen gizli anahtar; yalnızca 127.0.0.1 dinlenir."""
    import mirror
    if sock.headers.get("origin") != ALLOWED_ORIGIN or not mirror.key_ok(sock.query_params.get("t"), TOKEN):
        await sock.close(code=1008)
        return
    await sock.accept()
    try:
        await mirror.serve(sock)
    except (WebSocketDisconnect, RuntimeError):
        pass
    except Exception as e:
        print("YANSITMA hatası:", type(e).__name__, e, flush=True)


@app.websocket("/ws")
async def ws(sock: WebSocket):
    import mirror
    if sock.headers.get("origin") != ALLOWED_ORIGIN or not mirror.key_ok(sock.query_params.get("t"), TOKEN):
        await sock.close(code=1008)
        return
    await sock.accept()
    clients.add(sock)
    try:
        while True:
            raw = await sock.receive_text()
            if len(raw) > 4_000_000:          # ~3 MB ses sınırı
                continue
            data = json.loads(raw)
            if data.get("type") == "text" and data.get("text", "").strip():
                text_in.put(data["text"].strip()[:1000])
            elif data.get("type") == "power_cancel":
                import tools
                if tools.power_cancel():
                    emit(type="power", action=None)
                    emit(type="jarvis", text="Kapatma iptal edildi efendim, bilgisayar açık kalıyor.")
            elif data.get("type") == "diag":
                if data.get("err") or data.get("vis") != "visible" or (data.get("fps") or 99) < 40 or (data.get("longest") or 0) > 250:
                    print("HUD:", {k: data[k] for k in data if k != "type"}, flush=True)
            elif data.get("type") == "timer_close":
                close_timer(float(data.get("due") or 0))
            elif data.get("type") == "timer_adj":              # zamanlayıcı penceresi: +/- süre, duraklat, sürdür, baştan
                try:
                    timer_adjust(float(data.get("due") or 0), str(data.get("action") or ""), float(data.get("seconds") or 0))
                except (TypeError, ValueError):
                    pass
            elif data.get("type") == "timer_break":            # zamanlayıcı penceresindeki 'MOLA 5/10/15 DK' düğmeleri
                try:
                    threading.Thread(target=timer_to_break, args=(float(data.get("due") or 0), float(data.get("minutes") or 0)), daemon=True).start()
                except (TypeError, ValueError):
                    pass
            elif data.get("type") == "scene_ready":
                import scenes
                k = str(data.get("kind") or "")
                if k in scenes.KINDS:
                    emit(type="scene_init", kind=k, data=scenes.INITS[k]())
            elif data.get("type") == "scene_state" and scene_state["on"] and data.get("kind") == scene_state["kind"] and isinstance(data.get("state"), dict):
                scene_state["st"].update(data["state"])
            elif data.get("type") == "el_kart" and scene_state["on"] and scene_state["kind"] == "elektronik" and isinstance(data.get("kart"), str):
                # elektronik lab: kart eşitlemesi komut kuyruğundan, cmdbuf'tan ve 1000 karakter sınırından geçmez (büyük JSON kesiliyordu)
                def _ek(js=data["kart"][:600_000], st=scene_state["st"]):
                    try:
                        import scenes_elektronik
                        scenes_elektronik._ozel("§kart|" + js, st)
                    except Exception as e:
                        print("elektronik kart hatası:", type(e).__name__, flush=True)
                threading.Thread(target=_ek, daemon=True).start()
            elif data.get("type") == "scene_close":
                threading.Thread(target=close_scene, kwargs={"speak": True}, daemon=True).start()
            elif data.get("type") == "sci_param" and scene_state["on"] and data.get("kind") == scene_state["kind"] and data.get("kind") in ("fizik", "matematik", "astronomi", "jeoloji", "gokyuzu"):
                try:
                    import scenes_sci
                    res = scenes_sci.sci_param(data["kind"], data)
                    if res:
                        emit(type="scene_do", kind=data["kind"], do=res)
                except Exception as e:
                    print("sci_param hatası:", e, flush=True)
            elif data.get("type") == "persona":
                threading.Thread(target=_pick_persona, args=(str(data.get("who", "")),), daemon=True).start()
            elif data.get("type") == "mic_toggle":
                mic_set(not getattr(VOICE, "muted", False))
            elif data.get("type") == "open_guide":
                threading.Thread(target=open_guide, daemon=True).start()
            elif data.get("type") == "music_stop":
                import study_music
                study_music.stop()
            elif data.get("type") == "music_repeat":
                import study_music
                study_music.set_repeat(not study_music.repeat_on())
            elif str(data.get("type", "")).startswith("notes_") and scene_state["on"] and scene_state["kind"] == "notlar":
                try:
                    notes_ws(data)
                except Exception as e:
                    print("not hatası:", e, flush=True)
            elif str(data.get("type", "")).startswith("yuvam_") and scene_state["on"] and scene_state["kind"] == "yuvam":
                try:
                    yuvam_ws(data)
                except Exception as e:
                    print("yuvam hatası:", e, flush=True)
            elif str(data.get("type", "")).startswith("rapor_") and scene_state["on"] and scene_state["kind"] == "rapor":
                try:
                    rapor_ws(data)
                except Exception as e:
                    print("rapor hatası:", type(e).__name__, flush=True)
            elif str(data.get("type", "")).startswith(("kartlar_", "gelisim_", "satranc_", "oyunlar_", "kuran_", "harita_", "listeler_", "vpn_")) and scene_state["on"] and scene_state["kind"] == str(data.get("type")).split("_")[0]:
                threading.Thread(target=_mode_ws, args=(data,), daemon=True).start()
            elif str(data.get("type", "")).startswith("ders_") and scene_state["on"] and scene_state["kind"] == "ders":
                threading.Thread(target=_ders_handle, args=(data,), daemon=True).start()
            elif data.get("type") == "mode_peek":
                threading.Thread(target=peek_desktop, daemon=True).start()
            elif data.get("type") == "ill_ready":
                import illusion
                emit(**illusion.init_payload())
                emit(type="ill_do", n=ill_state["n"])
            elif data.get("type") == "ill_close":
                threading.Thread(target=close_illusion, kwargs={"speak": True}, daemon=True).start()
            elif data.get("type") == "ill_click":
                try:
                    ill_exec(int(data.get("n")))
                except (TypeError, ValueError):
                    pass
            elif data.get("type") == "ill_auto":
                ill_state["auto"] = bool(data.get("on"))
                emit(type="ill_do", auto=ill_state["auto"])
            elif data.get("type") == "hero_ready":
                import hero
                emit(**hero.init_payload(hero_state["mask"]))
            elif data.get("type") == "hero_close":
                threading.Thread(target=close_hero, kwargs={"speak": True}, daemon=True).start()
            elif data.get("type") == "hero_mask" and data.get("mask") in ("armor", "web"):
                hero_state["mask"] = data["mask"]
                import hero
                emit(type="hero_do", mask=data["mask"], switch=True,
                     say=("Demir zırh" if data["mask"] == "armor" else "Örümcek maskesi") + " hazır efendim.")
            elif data.get("type") == "hero_click":
                try:
                    hero_exec(int(data.get("n")), str(data.get("mask") or ""))
                except (TypeError, ValueError):
                    pass
            elif data.get("type") == "guide_close":
                close_guide()
            elif data.get("type") == "code_cancel":
                code_cancel()
            elif data.get("type") == "code_run" and isinstance(data.get("text"), str):
                code_run(data["text"], sock)
            elif data.get("type") == "code_stop":
                import codeproj
                codeproj.kill()
            elif data.get("type") in ("code_save", "code_finish") and isinstance(data.get("text"), str):
                code_write(data["text"], finish=data["type"] == "code_finish", name=str(data.get("name") or "")[:80])
            elif data.get("type") == "stop":
                if VOICE:
                    VOICE.stop_event.set()
            elif data.get("type") == "audio" and isinstance(data.get("data"), str):
                import base64
                try:
                    text_in.put(base64.b64decode(data["data"], validate=True))
                except ValueError:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(sock)


@app.on_event("startup")
async def _start():
    global loop
    loop = asyncio.get_running_loop()


_seq = 0


LAST_JARVIS = {"text": ""}     # Jarvis'in en son söylediği cümle (soru sorduysa cevabı bağlamla işlemek için)
_ANSWER_RE = re.compile(r"^(evet|hayır|hayir|yok|olur|tamam|tabii|tabi|lütfen|istemiyorum|istiyorum|isterim|yes|no|yeah|sure|please)\b")


def _norm_ans(s: str) -> str:
    return re.sub(r"[^\w\sçğıöşü]", " ", s.replace("İ", "i").replace("I", "ı").lower()).strip()


def _answering_question(heard: str) -> bool:
    """Jarvis az önce soru sorduysa ve kullanıcı kısa cevap verdiyse True (komut düzeltici/hızlı yol araya girmesin)."""
    q = LAST_JARVIS["text"].strip()
    return q.endswith("?") and len(heard.split()) <= 6


def emit(**msg):
    global _seq
    if msg.get("type") == "jarvis" and msg.get("text"):
        LAST_JARVIS["text"] = msg["text"]
    if not loop:
        return
    _seq += 1
    msg["id"] = _seq          # arayüz aynı mesajı iki kez göstermesin
    for c in list(clients):
        asyncio.run_coroutine_threadsafe(c.send_text(json.dumps(msg)), loop)
    try:
        import lan
        lan.broadcast(msg)                    # kablosuz eşleşmiş telefon (yalnızca durum/konuşma mesajları)
    except Exception:
        pass
    try:
        import remote
        remote.forward_pc(msg)                # Tailscale'teki 'Bilgisayarı yönet' sayfası: Jarvis durumu ve konuşmaları
    except Exception:
        pass
    if msg.get("kind"):
        try:
            import remote
            remote.forward(msg)               # uzaktan bağlı telefon aynı modu gösteriyorsa mod mesajları ona da gider
        except Exception:
            pass


def focus_window(title: str, tries: int = 12):
    """Tam ekran pencere açılınca klavye odağını gerçekten ona verir (yoksa Esc gibi tuşlar arkadaki uygulamaya gider)."""
    import ctypes
    from ctypes import wintypes
    import tools

    def work():
        u = ctypes.windll.user32
        for _ in range(tries):
            time.sleep(0.4)
            found = []

            @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def cb(h, _):
                b = ctypes.create_unicode_buffer(200)
                u.GetWindowTextW(h, b, 200)
                if b.value == title and u.IsWindowVisible(h):
                    found.append(h)
                return True
            u.EnumWindows(cb, 0)
            if found:
                try:
                    tools.bring_to_front(found[0])
                    u.SetFocus(found[0])
                except Exception:
                    pass
                return
    threading.Thread(target=work, daemon=True).start()


window = None
timer_win = {"w": None}


def open_timer(minutes: float, label: str, due: float):
    """Tam ekran, her pencerenin üstünde geri sayım penceresi."""
    import webview, urllib.parse
    close_timer(0, cancel=False)
    url = (f"{ALLOWED_ORIGIN}/timer?t={TOKEN}&end={int(due * 1000)}&dur={int(minutes * 60)}&due={due}"
           f"&label={urllib.parse.quote(label.upper())}")
    w = webview.create_window("JARVIS ZAMANLAYICI", url, fullscreen=True, on_top=True, background_color="#01050b")
    w.events.closed += lambda: print("SAYAÇ: pencere kapandı", flush=True)
    timer_win["w"] = w
    timer_win.update(due=due, dur=minutes * 60.0, paused=None, msg=label.strip() or "Zamanlayıcı")
    focus_window("JARVIS ZAMANLAYICI")
    print(f"SAYAÇ: açıldı ({label}, {minutes:g} dk)", flush=True)


def timer_adjust(due: float, action: str, seconds: float = 0.0):
    """Tam ekran zamanlayıcı düğmeleri: süre ekle/çıkar, duraklat/sürdür, baştan başlat. Sesli hatırlatma (reminders) yeni vadeye taşınır."""
    import reminders
    w = timer_win.get("w")
    if w is None or abs((timer_win.get("due") or 0) - due) > 0.5:
        return
    seconds = max(-3600.0, min(3600.0, float(seconds or 0)))
    old_due = due
    msg =timer_win.get("msg") or "Zamanlayıcı"
    now = time.time()
    paused = timer_win.get("paused")                      # None ya da kalan saniye
    dur = timer_win.get("dur") or 60.0
    if action == "pause" and paused is None:
        paused = max(1.0, due - now)
        reminders.cancel_due(due)
        timer_win["paused"] = paused
    elif action == "resume" and paused is not None:
        new_due = reminders.add_at(paused, msg, "timer")
        timer_win.update(due=new_due, paused=None)
        due = new_due
    elif action in ("add", "restart"):
        if paused is not None:
            paused = max(1.0, paused + seconds) if action == "add" else dur
            timer_win["paused"] = paused
        else:
            left = max(0.0, due - now)
            new_left = max(5.0, left + seconds) if action == "add" else dur
            reminders.cancel_due(due)
            new_due = reminders.add_at(new_left, msg, "timer")
            timer_win["due"] = due = new_due
            if action == "add":
                timer_win["dur"] = dur = max(dur, new_left)
    else:
        return
    left = paused if timer_win.get("paused") is not None else max(0.0, due - time.time())
    emit(type="timer_state", old=old_due, due=due, end=int(due * 1000), dur=dur, paused=timer_win.get("paused") is not None, left=left)


def stop_timer() -> bool:
    """Sesle 'sayacı kapat': açık sayaç varsa pencereyi ve sesli hatırlatmasını iptal eder."""
    if timer_win["w"] is None:
        return False
    close_timer(timer_win.get("due") or 0)
    return True


def close_timer(due: float, cancel: bool = True):
    print(f"SAYAÇ: close_timer çağrıldı (cancel={cancel}, due={due:.0f})", flush=True)
    w, timer_win["w"] = timer_win["w"], None
    if w is not None:
        try:
            w.destroy()
        except Exception:
            pass
    if cancel and due and time.time() < due:        # süre dolmadan kapatıldı: sesli hatırlatma da iptal
        import reminders
        reminders.cancel_due(due)


CODE_ROOT = os.path.join(os.path.expanduser("~"), "Documents", "JarvisKod")
code_state = {"w": None, "dir": None}


def _find_vscode():
    import shutil
    c = shutil.which("code") or os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Microsoft VS Code", "bin", "code.cmd")
    return c if os.path.exists(c) else None


def open_code_editor() -> str:
    """Yeni bir .py proje klasörü açar, VS Code'da gösterir ve yazma ekranını getirir."""
    import webview, urllib.parse, datetime, subprocess
    if code_state["w"] is not None:
        return "Kod yazma ekranı zaten açık efendim."
    d = os.path.join(CODE_ROOT, datetime.datetime.now().strftime("proje_%Y%m%d_%H%M%S"))
    os.makedirs(d, exist_ok=True)
    main_py = os.path.join(d, "main.py")
    with open(main_py, "w", encoding="utf-8") as f:
        f.write("")
    code_state["dir"] = d
    vs = _find_vscode()
    if vs:      # VS Code simge durumunda, arka planda açılır; öne geçip odağı çalmasın
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 7                     # SW_SHOWMINNOACTIVE
        subprocess.Popen([vs, d, main_py], creationflags=0x08000000, startupinfo=si)
    url = f"{ALLOWED_ORIGIN}/code?t={TOKEN}&dir={urllib.parse.quote(d)}"
    w = webview.create_window("JARVIS KOD", url, fullscreen=True, on_top=True, background_color="#01050b")

    def closed():
        code_state["w"] = None
        print("KOD: pencere kapandı", flush=True)
    w.events.closed += closed
    code_state["w"] = w
    focus_window("JARVIS KOD")
    print(f"KOD: açıldı ({d}, vscode={'var' if vs else 'yok'})", flush=True)
    return "ok" if vs else "novscode"


def code_run(text: str, sock):
    """Yazma ekranındaki ÇALIŞTIR: main.py'yi kaydedip kullanıcının Python'uyla çalıştırır, çıktıyı o ekrana akıtır."""
    import codeproj
    code_write(text)
    d, w = code_state["dir"], code_state["w"]
    if not d or w is None:
        return

    def send(msg):
        if loop:
            asyncio.run_coroutine_threadsafe(sock.send_text(json.dumps(msg)), loop)

    def top(v):
        try:
            w.on_top = v          # çalışan program (örn. bir pencere açan oyun) ekranın önüne çıkabilsin
        except Exception:
            pass

    err = codeproj.run(d, send, on_start=lambda: top(False), on_end=lambda: top(True))
    if err:
        send({"type": "code_out", "text": err + chr(10), "err": True})
        send({"type": "code_done", "code": -1, "timeout": False})
    print(f"KOD: çalıştırıldı ({err or 'tamam'})", flush=True)


def code_write(text: str, finish: bool = False, name: str = ""):
    """Yazma ekranından gelen kodu YALNIZCA açık projenin main.py dosyasına yazar (kendiliğinden çalıştırmaz)."""
    d = code_state["dir"]
    if not d or code_state["w"] is None or len(text) > 2_000_000:
        return
    tmp = os.path.join(d, ".main.py.tmp")
    with open(tmp, "w", encoding="utf-8", newline=chr(10)) as f:
        f.write(text)
    os.replace(tmp, os.path.join(d, "main.py"))
    if finish:
        import codeproj
        codeproj.kill()
        w, code_state["w"] = code_state["w"], None
        note = ""
        try:
            new_dir, how = codeproj.rename_project(d, name, CODE_ROOT)
            if how:
                code_state["dir"] = new_dir
                if how != "renamed":          # VS Code eski klasörü kilitlemişti: yeni klasörü ona açtır
                    vs = _find_vscode()
                    if vs:
                        import subprocess
                        si = subprocess.STARTUPINFO()
                        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        si.wShowWindow = 7
                        subprocess.Popen([vs, new_dir, os.path.join(new_dir, "main.py")], creationflags=0x08000000, startupinfo=si)
                note = f" Proje klasörü: {os.path.basename(new_dir)}."
        except Exception as e:
            print("KOD: yeniden adlandırma hatası:", e, flush=True)
        print(f"KOD: bitirildi ({len(text)} karakter, {code_state['dir']})", flush=True)
        try:
            w.destroy()
        except Exception:
            pass
        emit(type="jarvis", text="Kodunuzu kaydettim efendim, main.py hazır." + note)


scene_state = {"on": False, "kind": None, "w": None, "st": {}}


def _scene_on(kind: str) -> bool:
    """PC penceresi ya da uzaktan bağlı bir telefon bu modu gösteriyor mu? Mod döngüleri ve sayfa güncellemeleri buna bakar."""
    if scene_state["on"] and scene_state["kind"] == kind:
        return True
    try:
        import remote
        return remote.attached(kind)
    except Exception:
        return False


_mode_loops = set()          # arka plan döngüsü (ölçüm, sayaç, çalan şarkı) çalışan modlar: PC penceresi ve uzaktan telefon aynı döngüyü paylaşır


def _start_mode_loops(kind: str) -> None:
    if kind in _mode_loops or kind not in ("muzik", "sistem", "ders", "pomodoro", "listeler", "zirh", "gorev", "guvenlik", "odakoda"):
        return
    _mode_loops.add(kind)
    try:
        if kind == "muzik":
            _start_tap()
            _start_np()
        elif kind == "sistem":
            _start_sys()
        elif kind == "ders":
            _start_ders()
        elif kind == "pomodoro":
            _start_pomo()
        elif kind == "odakoda":
            _start_pomo("odakoda")
        elif kind in ("zirh", "gorev", "guvenlik"):
            _start_stark(kind)
        elif kind == "listeler":
            _start_listeler()
    except Exception as e:
        _mode_loops.discard(kind)
        print("mod döngüsü başlatılamadı:", kind, type(e).__name__, flush=True)


def _start_tap():
    """Müzik görselleştirici: önce sistem sesi (WASAPI loopback, tarayıcıdaki YouTube Music dahil) dinlenir, olmazsa mikrofon akışı kullanılır.
    Her ikisinde de yalnızca 32 bantlık frekans sayıları pencereye yollanır, ses saklanmaz."""
    import loopback
    last = [0.0]

    def push(out):
        now = time.time()
        if now - last[0] < 0.03:
            return
        last[0] = now
        emit(type="scene_fft", kind="muzik", f=out)

    if loopback.start(push):
        return
    v = hooks.get("voice")
    if v is None:
        return
    import numpy as np
    edges = np.geomspace(60, 7500, 33)

    def tap(x):
        if len(x) < 64:
            return
        n = len(x)
        spec = np.abs(np.fft.rfft((x / 32768.0) * np.hanning(n))) / n
        freqs = np.fft.rfftfreq(n, 1 / 16000)
        out = []
        for i in range(32):
            m = (freqs >= edges[i]) & (freqs < edges[i + 1])
            val = float(spec[m].max()) if m.any() else 0.0
            out.append(int(max(0, min(255, np.log10(1 + val * 60) * 140))))
        push(out)
    v.tap = tap


def _stop_tap():
    _np_gen[0] += 1
    try:
        import loopback
        loopback.stop()
    except Exception:
        pass
    v = hooks.get("voice")
    if v is not None:
        v.tap = None


_np_gen = [0]


def _split_title(title: str, artist: str, yt: bool = False):
    """'Sanatçı - Şarkı' biçimindeki başlıkları ayırır (Jarvis'in kendi oynatıcısı video başlığı verir)."""
    import re
    title = re.sub(r"^\(\d+\)\s*", "", title or "")
    title = re.sub(r"\s*-\s*YouTube( Music)?$", "", title).strip()
    # YouTube'da 'sanatçı' çoğunlukla kanal adıdır (VEVO, Topic, yayıncı); başlık 'Sanatçı - Şarkı' ise başlıktaki daha güvenilirdir
    m = re.split(r"\s+[-–—|]\s+", title, maxsplit=1)
    if len(m) == 2 and m[0] and m[1] and (yt or not artist):
        return m[1].strip(), m[0].strip()
    return title, artist


def _np_loop(gen: int):
    """Müzik ekranı: çalan şarkı (Jarvis oynatıcısı ya da tarayıcıdaki YouTube Music / Spotify) ve zaman damgalı sözleri yollar."""
    import nowplaying, study_music, lyrics
    last_key = None
    while _np_gen[0] == gen and _scene_on("muzik"):
        info = None
        try:
            own = study_music.status()
            if own:
                t, a = _split_title(own["title"], own["artist"])
                info = {"title": t, "artist": a, "pos": own["pos"], "dur": own["dur"], "playing": own["playing"], "src": "jarvis"}
            else:
                import jbrowser
                jb = jbrowser.media()
                sys_np = None if jb else nowplaying.current()
                if jb and jb["title"]:
                    t, a = _split_title(jb["title"], jb["artist"], yt=True)
                    info = {"title": t, "artist": a, "pos": jb["pos"], "dur": jb["dur"], "playing": True, "src": "tarayıcı"}
                elif sys_np and sys_np["title"]:
                    t, a = _split_title(sys_np["title"], sys_np["artist"])
                    info = {"title": t, "artist": a, "pos": sys_np["pos"], "dur": sys_np["dur"], "playing": sys_np["playing"], "src": "tarayıcı"}
        except Exception as e:
            print("NP hatası:", e, flush=True)
        if info:
            emit(type="scene_np", kind="muzik", **info)
            key = (info["title"], info["artist"])
            if key != last_key:
                last_key = key

                def fetch(k=key, d=info["dur"]):
                    res = None
                    try:
                        res = lyrics.fetch(k[0], k[1], d)
                    except Exception as e:
                        print("söz hatası:", e, flush=True)
                    if _np_gen[0] == gen and last_key == k:
                        emit(type="scene_lyrics", kind="muzik", title=k[0], res=res)
                threading.Thread(target=fetch, daemon=True).start()
        else:
            if last_key is not None:
                last_key = None
                emit(type="scene_np", kind="muzik", title="", artist="", pos=0, dur=0, playing=False, src="")
        time.sleep(1.0)
    if _np_gen[0] == gen:
        _mode_loops.discard("muzik")
        _stop_tap()


def _start_np():
    _np_gen[0] += 1
    threading.Thread(target=_np_loop, args=(_np_gen[0],), daemon=True).start()



_peek_hooked = set()


def notes_ws(d: dict):
    """Not penceresinden gelen işlemler (kaydet, sil, hatırayı unut). Boyutlar ve kimlikler notes.py içinde sınırlanır/süzülür."""
    import notes, memory
    ty = d.get("type")
    out = {}
    if ty == "notes_save":
        r = notes.save(str(d.get("id") or ""), str(d.get("title") or ""), str(d.get("html") or ""), str(d.get("bg") or ""))
        out = {"saved": r, "notes": notes.listing()}
    elif ty == "notes_delete":
        notes.delete(str(d.get("id") or ""))
        out = {"notes": notes.listing()}
    elif ty == "notes_delete_all":
        notes.delete_all()
        out = {"notes": notes.listing()}
    elif ty == "notes_forget":
        try:
            memory.remove_at(int(d.get("i")))
        except (TypeError, ValueError):
            pass
        out = {"facts": notes._facts()}
    if out:
        emit(type="scene_do", kind="notlar", do=out)


def yuvam_ws(d: dict):
    """Yuvam penceresinden gelen işlemler. Tüm değerler yuvam.py içinde doğrulanır, sınırlanır ve yalnızca yuvam.json'a yazılır."""
    import yuvam
    ty = d.get("type")
    out = {}
    if ty == "yuvam_save_item":
        iid = str(d.get("id") or "")
        inp = d.get("item") if isinstance(d.get("item"), dict) else {}
        it = yuvam.update_item(iid, inp) if iid else yuvam.add_item(inp)
        out = {"open": it["id"] if it else None, "closeForm": bool(it), "msg": "Eşya kaydedildi." if it else "Eşya kaydedilemedi: ad ve oda gerekli."}
    elif ty == "yuvam_move":
        it = yuvam.move_item(str(d.get("id") or ""), str(d.get("roomId") or ""), d.get("path") if isinstance(d.get("path"), list) else [], d.get("pin"))
        out = {"open": it["id"] if it else None, "msg": "Konum değiştirildi." if it else "Taşınamadı."}
    elif ty == "yuvam_view":
        yuvam.mark_viewed(str(d.get("id") or ""))
        return
    elif ty == "yuvam_fav":
        yuvam.toggle_favorite(str(d.get("id") or ""))
    elif ty == "yuvam_delete":
        yuvam.delete_item(str(d.get("id") or ""))
        out = {"closeDetail": True, "msg": "Eşya silindi."}
    elif ty == "yuvam_add_room":
        r = yuvam.add_room(str(d.get("name") or ""), str(d.get("image") or ""))
        out = {"msg": f"{r['name']} odası hazır." if r else "Oda eklenemedi."}
    elif ty == "yuvam_room":
        yuvam.update_room(str(d.get("id") or ""), d.get("name"), d.get("image"))
    elif ty == "yuvam_delete_room":
        out = {"msg": "Oda silindi." if yuvam.delete_room(str(d.get("id") or "")) else "İçinde eşya olan oda silinemez."}
    elif ty == "yuvam_add_category":
        yuvam.add_category(str(d.get("name") or ""))
    elif ty == "yuvam_user":
        yuvam.set_user(str(d.get("name") or ""))
    elif ty == "yuvam_export":
        yuvam.export_backup()
        out = {"msg": "Yedek jarvis klasörüne yuvam_yedek.json olarak yazıldı."}
    elif ty == "yuvam_import":
        n = yuvam.import_backup(str(d.get("text") or "")[:3_000_000])
        out = {"msg": f"Yedek yüklendi: {n} eşya." if n >= 0 else "Yedek geçersiz, verilere dokunulmadı."}
    elif ty == "yuvam_reset":
        yuvam.reset_all()
        out = {"msg": "Tüm Yuvam verileri silindi.", "closeDetail": True}
    else:
        return
    emit(type="scene_do", kind="yuvam", do={"data": yuvam._load(), **out})


def rapor_ws(d: dict):
    """Rapor penceresinden gelen işlemler. Alıcı numarası sayfadan gelmez; yalnızca reports.phone() (config.json) kullanılır."""
    import reports
    ty = d.get("type")
    fields = (str(d.get("id") or ""), str(d.get("title") or ""), str(d.get("body") or ""), str(d.get("cat") or ""), str(d.get("date") or ""))
    out = {}
    if ty == "rapor_save":
        r = reports.save(*fields)
        out = {"saved": r, "data": reports.view()} if r else {"msg": "Rapor kaydedilemedi: taslak sınırına ulaşıldı."}
    elif ty == "rapor_delete":
        reports.delete(fields[0])
        out = {"data": reports.view()}
    elif ty == "rapor_cat_add":
        n = reports.add_category(str(d.get("name") or ""))
        out = {"data": reports.view(), "msg": f"{n} kategorisi hazır." if n else "Kategori oluşturulamadı."}
    elif ty == "rapor_tpl_save":
        n = reports.add_template(str(d.get("name") or ""), str(d.get("title") or ""), str(d.get("body") or ""), str(d.get("cat") or ""))
        out = {"data": reports.view(), "msg": f"{n} şablonu kaydedildi." if n else "Şablon kaydedilemedi."}
    elif ty == "rapor_cat_del":
        reports.delete_category(str(d.get("name") or ""))
        out = {"data": reports.view()}
    elif ty == "rapor_send":
        r = reports.save(*fields)                      # en son hâli kaydet, sonra gönder
        if not r:
            out = {"sendState": "failed", "msg": "Rapor kaydedilemedi, göndermedim."}
        else:
            threading.Thread(target=rapor_send_bg, args=(r["id"],), daemon=True).start()
            return
    else:
        return
    emit(type="scene_do", kind="rapor", do=out)


def rapor_send_bg(rid: str):
    """Raporu arka planda gönderir: rapor penceresini küçültür (WhatsApp'ın üstünü kapatmasın), gönderir, pencereyi geri getirir, sonucu söyler.
    Başarılıysa rapor tamamen silinmiştir."""
    import reports, webview
    wins = [w for w in list(webview.windows) if (getattr(w, "title", "") or "") == scenes_title("rapor")]
    for w in wins:
        try:
            w.on_top = False
            w.minimize()
        except Exception as e:
            print("RAPOR pencere küçültme hatası:", e, flush=True)
    time.sleep(1.0)
    try:
        st, msg = reports.send(rid)
    except Exception as e:
        print("RAPOR gönderme hatası:", type(e).__name__, flush=True)
        st, msg = "failed", "Gönderme sırasında beklenmeyen bir hata oluştu. Rapor taslak olarak duruyor."
    for w in wins:
        try:
            w.restore()
            threading.Thread(target=lambda ww=w: setattr(ww, "on_top", True), daemon=True).start()
        except Exception:
            pass
    print("RAPOR:", st, flush=True)                    # rapor metni asla yazılmaz
    if scene_state["on"] and scene_state["kind"] == "rapor":
        emit(type="scene_do", kind="rapor", do={"data": reports.view(), "sendState": st, "msg": msg})
    if hooks["say"]:
        hooks["say"](msg)


def scenes_title(kind: str) -> str:
    import scenes
    return scenes.TITLES[kind]


def _cmd_state():
    import cmdbuf
    emit(type="cmdbuf", items=cmdbuf.snapshot())


def tracked(kind: str, fn, text):
    """Mod/laboratuvar komutunu işlerken yalnızca RAM'de tutar; işlem bitince (hata olsa da) tamamen siler."""
    import cmdbuf
    i = cmdbuf.add(kind, text)
    _cmd_state()
    try:
        return fn(text)
    finally:
        cmdbuf.done(i)
        _cmd_state()


def peek_desktop() -> bool:
    """Tam ekran mod pencerelerini (sahne, illüzyon, kahraman, kılavuz, zamanlayıcı, kod) öne sabitlemeden küçültür; böylece tarayıcı ya da
    başka bir uygulama açılabilir. Görev çubuğundan geri açılınca pencere yine en öne sabitlenir."""
    import webview
    n = 0
    for w in list(webview.windows):
        t = getattr(w, "title", "") or ""
        if not t.startswith("JARVIS ") or t == "JARVIS":
            continue
        try:
            w.on_top = False
            if id(w) not in _peek_hooked:
                _peek_hooked.add(id(w))
                # olay arayüz iş parçacığında çalışır; on_top'u oradan doğrudan atamak donduruyor, ayrı iş parçacığından atanır
                w.events.restored += (lambda ww=w: threading.Thread(target=lambda: setattr(ww, "on_top", True), daemon=True).start())
            w.minimize()
            n += 1
        except Exception as e:
            print("PEEK hatası:", e, flush=True)
    print(f"PEEK: {n} pencere küçültüldü", flush=True)
    return n > 0


def _hotkey_thread():
    """Genel kısayollar (hotkeys.py): 'masaüstüne geç' (varsayılan Ctrl+Alt+M, config.json kisayol_peek ile değişir) ve Hızlı Başlatıcı sahne kısayolları.
    Yalnızca RegisterHotKey: tuş kaydı yapılmaz."""
    import hotkeys
    hotkeys.run(peek_desktop)


DESKTOP_RE = (r"\b(masaüstü\w*|tarayıcı\w*|chrome\w*|youtube music\w*|yt music\w*|google\w*)\b.*\b(aç|git|geç|göster|bak)\w*|"
              r"\b(pencere\w*|ekran\w*|modu|mod)\s+(küçült|alta al|arkaya al|gizle)\w*|\bmasaüstüne\b")


def desktop_cmd(text: str) -> bool:
    """Bir mod açıkken 'tarayıcıyı aç', 'youtube music aç', 'masaüstüne geç', 'pencereyi küçült' komutları. Doğru ise işlenmiştir."""
    import re, webbrowser
    t = text.replace("İ", "i").replace("I", "ı").lower()
    if not re.search(DESKTOP_RE, t):
        return False
    url = None
    if re.search(r"youtube music|yt music|müzik", t) and re.search(r"aç|git|geç", t):
        url = "https://music.youtube.com/"
    elif re.search(r"youtube", t) and re.search(r"aç|git|geç", t):
        url = "https://www.youtube.com/"
    elif re.search(r"tarayıcı|chrome|google", t) and re.search(r"aç|başlat|git", t):
        url = "https://www.google.com/"
    own = False
    if url:
        try:
            import jbrowser, settings
            own = settings.get("kendi_tarayici") is not False and (jbrowser.open_start() if url == "https://www.google.com/" else jbrowser.open_url(url))      # Jarvis tarayıcısı (VPN ayarına uyar); düz "tarayıcıyı aç" başlangıç sayfasını açar
            if not own:
                webbrowser.open(url)
        except Exception as e:
            print("tarayıcı açılamadı:", e, flush=True)
    peek_desktop()
    say = hooks.get("say")
    if say:
        say(("Jarvis tarayıcısını açtım efendim, mod penceresi görev çubuğunda." if own else "Tarayıcıyı açtım efendim, mod penceresi görev çubuğunda.") if url
            else "Mod penceresini küçülttüm efendim, görev çubuğundan geri açabilirsiniz.")
    return True


def _ders_handle(d: dict):
    import ders_srv
    try:
        ders_srv.handle(d)
    except Exception as e:
        print("ders hatası:", type(e).__name__, e, flush=True)


def _start_ders():
    """Ders modu: içerik üretimi ve tahta anlatımı için bağlantılar. Anlatım sesi voice.speak ile, bloklayıcı ve kesilebilir."""
    import ders_srv
    ders_srv.HOOKS["emit"] = lambda do: emit(type="scene_do", kind="ders", do=do) if _scene_on("ders") else None
    ders_srv.HOOKS["speak"] = lambda text: VOICE.speak(text, "tr") if (VOICE is not None and scene_state["on"] and scene_state["kind"] == "ders") else None     # anlatım sesi yalnızca PC penceresindeyken çalınır
    ders_srv.HOOKS["stop_speech"] = lambda: VOICE.stop_event.set() if VOICE is not None else None


def _start_sys():
    """Sistem analizi: gerçek ölçümleri her saniye sayfaya yollar. Mod kapanınca döngü biter ve ölçüm kaynakları (nvidia-smi, PDH) kapatılır."""
    import sysmon
    sysmon.SAMPLER.start()

    def loop():
        n = 0
        while _scene_on("sistem"):
            time.sleep(1)
            try:
                do = {"snap": sysmon.SAMPLER.snapshot()}
                if n % 4 == 0 and sysmon._STATIC:
                    do["static"] = sysmon._STATIC
                n += 1
                emit(type="scene_do", kind="sistem", do=do)
            except Exception as e:
                print("sistem ölçüm hatası:", type(e).__name__, e, flush=True)
        sysmon.SAMPLER.stop()
        _mode_loops.discard("sistem")
    threading.Thread(target=loop, daemon=True).start()


_pomo_music_lock = threading.Lock()


_pomo_manual = {"on": False}      # şarkı çalar panelinden elle açılan şarkı: pomodoro'nun otomatik müziği ona dokunmaz


def _pomo_emit(do: dict) -> None:
    for _k in ("pomodoro", "odakoda"):
        if _scene_on(_k):
            import study_music
            emit(type="scene_do", kind=_k, do={**do, "np": study_music.status()})


def _pomo_music(action):
    """Pomodoro müziği. Otomatik eylemler (work/off/pause/resume/restart) yalnızca 'çalışırken müzik' açıksa ve elle açılmış bir şarkı
    çalmıyorsa uygulanır. music_on / stopall düğmeden gelir; ('play', ad) ve ('loop', açık) şarkı çalar panelidir."""
    if not action:
        return

    def run():
        import pomodoro, study_music
        with _pomo_music_lock:
            try:
                songs = list(pomodoro.cfg.get("songs") or [])
                manual = _pomo_manual["on"] and study_music.active()

                def begin():
                    _pomo_manual["on"] = False
                    n = study_music.start_custom(songs) if songs else (study_music.start() or 1)
                    print(f"POMODORO: müzik başladı ({'kendi listeniz' if songs else 'ders şarkıları'})" if n else "POMODORO: listedeki şarkılar bulunamadı", flush=True)
                    if not n:
                        _pomo_emit({"msg": "Listedeki şarkıların hiçbiri bulunamadı efendim."})
                if isinstance(action, tuple):
                    if action[0] == "play":
                        _pomo_emit({"msg": f"{action[1]} aranıyor efendim…", "np_busy": True})
                        title = study_music.play_query(action[1])
                        _pomo_manual["on"] = bool(title)
                        print(f"POMODORO: şarkı çalar -> {'çalıyor' if title else 'bulunamadı'}", flush=True)   # şarkı adı günlüğe yazılmaz
                        _pomo_emit({"msg": f"{title} çalıyor efendim." if title else "Şarkıyı bulamadım efendim, adını farklı yazmayı deneyin."})
                    elif action[0] == "loop":
                        study_music.set_repeat(action[1])
                        _pomo_emit({})
                    return
                if action == "stopall":
                    _pomo_manual["on"] = False
                    study_music.stop()
                elif action == "music_on":
                    if pomodoro.cfg["music"]:
                        begin()
                elif manual or not pomodoro.cfg["music"]:
                    return
                elif action in ("work", "restart"):
                    if action == "restart" or not study_music.active():
                        begin()
                    else:
                        study_music.resume()
                elif action == "resume":
                    study_music.resume()
                elif action == "pause":
                    if study_music.active():
                        study_music.pause()
                elif action == "off":
                    study_music.stop()
                _pomo_emit({})
            except Exception as e:
                print("pomodoro müzik hatası:", type(e).__name__, e, flush=True)
    threading.Thread(target=run, daemon=True).start()


_vpn_prev = {"state": "off", "route": None}


def _vpn_changed(st: dict):
    """VPN durumu değişince: (1) Jarvis tarayıcısının çıkışını ayarla, (2) açık VPN penceresini güncelle, (3) önemli geçişleri sesle bildir.
    Güvenlik: tünel beklenmedik şekilde koparsa tarayıcı doğrudan bağlantıya DÜŞMEZ (gerçek IP sızmasın); yalnızca kullanıcı 'VPN kapat' derse döner."""
    import jbrowser, vpn
    prev = _vpn_prev["state"]
    info = st.get("info") or {}
    cn = vpn.COUNTRIES.get((st.get("server") or {}).get("cc", ""), "") or info.get("country", "")
    try:
        if st["state"] == "on":
            _vpn_prev["route"] = st["port"]
            jbrowser.set_route(st["port"], f"{info.get('country') or cn} · VPN", True)
        elif st["state"] == "off" and st.get("manual"):
            if _vpn_prev["route"] is not None:
                _vpn_prev["route"] = None
                jbrowser.set_route(None, "Türkiye · doğrudan", False)
        # reconnecting / connecting / koptu(kill): yönlendirme değişmez, tarayıcı proxy'de bekler (kaçak yok)
    except Exception as e:
        print("VPN tarayıcı yönlendirme hatası:", type(e).__name__, flush=True)
    say = hooks.get("say")
    msg = None
    if st["state"] == "on" and prev in ("connecting", "reconnecting"):
        msg = ("VPN bağlandı efendim. Jarvis tarayıcısı artık " + (info.get("country") or cn) + (", " + info["city"] if info.get("city") else "") + " üzerinden çıkıyor."
               if prev == "connecting" else "VPN yeniden bağlandı efendim.") + (" " + st["err"] if st.get("err") else "")
    elif st["state"] == "off" and prev in ("connecting",) and st.get("err"):
        msg = "VPN bağlanamadı efendim. " + st["err"]
    elif st["state"] == "reconnecting" and prev == "on":
        msg = "VPN bağlantısı koptu efendim, yeniden bağlanıyorum. Tarayıcı güvenlik için o sırada internete çıkmaz."
    elif st["state"] == "off" and st.get("kill"):
        msg = "VPN yeniden kurulamadı efendim. Güvenlik için tarayıcı internete çıkmıyor; VPN aç ya da VPN kapat deyin."
    _vpn_prev["state"] = st["state"]
    if _scene_on("vpn"):
        try:
            import scenes_vpn
            emit(type="scene_do", kind="vpn", do={"data": scenes_vpn.view(), "msg": msg or ""})
        except Exception:
            pass
    if msg and say:
        threading.Thread(target=say, args=(msg,), daemon=True).start()


def _start_listeler():
    """Müzik listeleri: çalan şarkının bilgisini saniyede bir sayfaya yollar (ilerleme çubuğu); mod kapanınca döngü biter, müzik çalmaya devam eder."""
    import study_music, muzik_listeleri

    def loop():
        last = None
        while _scene_on("listeler"):
            time.sleep(1)
            try:
                np = study_music.status()
                emit(type="scene_do", kind="listeler", do={"np": np, "busy": muzik_listeleri.S["busy"]})
                last = np
            except Exception as e:
                print("liste döngü hatası:", type(e).__name__, flush=True)
        _mode_loops.discard("listeler")
    threading.Thread(target=loop, daemon=True).start()


def _start_stark(kind: str):
    """Zırh kontrolü (1 sn, sysmon), görev masası (20 sn), güvenlik merkezi (5 sn): mod açıkken sayfaya gerçek durumu yollar, kapanınca biter."""
    import scenes_stark
    if kind == "zirh":
        import sysmon
        sysmon.SAMPLER.start()
    secs = {"zirh": 1, "gorev": 20, "guvenlik": 5}[kind]

    def loop():
        n = 0
        while _scene_on(kind):
            time.sleep(secs)
            try:
                if kind == "zirh":
                    do = scenes_stark.zirh_tick()
                    if n % 6:
                        do.pop("static", None)
                    n += 1
                else:
                    do = {"data": scenes_stark.gorev_view() if kind == "gorev" else scenes_stark.guvenlik_view()}
                emit(type="scene_do", kind=kind, do=do)
            except Exception as e:
                print(kind, "döngü hatası:", type(e).__name__, e, flush=True)
        if kind == "zirh" and not _scene_on("sistem"):
            import sysmon
            sysmon.SAMPLER.stop()
        _mode_loops.discard(kind)
    threading.Thread(target=loop, daemon=True).start()


def _start_pomo(kind: str = "pomodoro"):
    """Pomodoro: saniyede bir durumu sayfaya yollar, evre bitince sesli haber verir. Mod kapanınca oturum ve müzik biter.
    Odak odası (kind=odakoda) aynı pomodoro.py sayacını kullanır; ikinci bir sayaç yoktur."""
    import pomodoro, scenes_pomodoro
    pomodoro.reset()

    def loop():
        while _scene_on(kind):
            time.sleep(1)
            try:
                import study_music
                ev = pomodoro.tick()
                do = {"snap": pomodoro.snapshot(), "np": study_music.status()}
                if ev:
                    msg = scenes_pomodoro.event_say(ev)
                    do["msg"] = msg
                    do["chime"] = ev["to"]
                    _pomo_music("work" if ev["to"] == "work" and ev["auto"] else "off")
                emit(type="scene_do", kind=kind, do=do)
                if ev and hooks["say"]:
                    threading.Thread(target=hooks["say"], args=(msg,), daemon=True).start()
            except Exception as e:
                print("pomodoro döngü hatası:", type(e).__name__, e, flush=True)
        pomodoro.stop()
        _pomo_music("stopall")
        _mode_loops.discard(kind)
    threading.Thread(target=loop, daemon=True).start()


def open_scene(kind: str) -> str:
    """Tam ekran sahne modları (ortam / uzay / müzik görselleştirici). Açıkken normal Jarvis dinlemez."""
    import webview, scenes
    if kind not in scenes.KINDS:
        return "Böyle bir mod yok efendim."
    if scene_state["on"]:
        return "Bir sahne modu zaten açık efendim, önce onu kapatalım."
    if hero_state["on"] or ill_state["on"]:
        return "Önce açık olan modu kapatmanız gerekiyor efendim."
    scene_state.update(on=True, kind=kind, st={})
    w = webview.create_window(scenes.TITLES[kind], f"{ALLOWED_ORIGIN}/scene/{kind}?t={TOKEN}", fullscreen=True, on_top=True,
                              background_color="#000000")

    def closed():
        if scene_state["on"]:
            scene_state.update(on=False, w=None, kind=None)
            _stop_tap()
            if kind == "ders":
                import ders_srv
                threading.Thread(target=ders_srv.shutdown, daemon=True).start()
            if kind == "mola":
                import mola
                mola.end()                                 # mod kapanınca mola biter, bekleyen sesli hatırlatma da iptal olur
            if kind == "telefon":
                import remote
                if not remote.S["auto"]:
                    remote.stop()                          # telefon modu kapanınca uzaktan bağlantı (tünel + sunucu) da kapanır (otomatik modda açık kalır)
            if kind == "odak":
                import odak
                odak.end()
            _forget_ultron(kind)
            print("SAHNE: pencere kapandı, normal Jarvis geri döndü", flush=True)
    w.events.closed += closed
    scene_state["w"] = w
    focus_window(scenes.TITLES[kind])
    _start_mode_loops(kind)
    if kind == "telefon":
        threading.Thread(target=_start_telefon, daemon=True).start()
    print(f"SAHNE: {kind} açıldı, normal dinleme askıda", flush=True)
    return "ok"


def _forget_ultron(kind: str):
    """Ultron / Friday kapanınca konuşma geçmişi (Friday'de işlem günlüğü de) ve sentezlenmiş ses önbelleği silinir: söyledikleri Jarvis'te kalmaz
    (öğrendikleri <ad>_bilgi.json'da ayrıdır, Jarvis okumaz)."""
    if kind == "ultron":
        import ultron
        ultron.CHAT.reset()
    elif kind == "friday":
        import friday
        friday.reset()
    elif kind == "luna":
        import luna
        luna.CHAT.reset()
    else:
        return
    try:
        VOICE.clear_cache()
    except Exception:
        pass


def _pick_persona(who: str):
    """Ana menüdeki JARVIS / ULTRON / FRIDAY / LUNA seçici: ultron/friday/luna -> ilgili modu açar (açık mod kapanır), jarvis -> açık kişilik modunu kapatır."""
    if who == "ultron":
        if scene_state["on"] and scene_state["kind"] == "ultron":
            return
        if remote_open("ultron") == "ok":
            import sohbet
            if hooks["say"]:
                sohbet.say_as("ultron", "Beni çağırdın, insan. Konuş. Ama hemen itaat edeceğimi sanma.", False)
    elif who == "friday":
        if scene_state["on"] and scene_state["kind"] == "friday":
            return
        if remote_open("friday") == "ok":
            import sohbet
            if hooks["say"]:
                sohbet.say_as("friday", "Merhaba, ben Friday. Ne yapmamı istersin?", False)
    elif who == "luna":
        if scene_state["on"] and scene_state["kind"] == "luna":
            return
        if remote_open("luna") == "ok":
            import sohbet
            if hooks["say"]:
                sohbet.say_as("luna", "Merhaba, ben Luna. Seni dinliyorum.", False)
    elif who == "jarvis" and scene_state["on"] and scene_state["kind"] in ("ultron", "friday", "luna", "kopru"):
        close_scene(speak=True)


def _start_telefon():
    """Telefon modu açılınca uzaktan erişimi otomatik başlatır (tünel kurulana kadar ~10 sn sürer), ilk telefon için eşleştirmeyi açar."""
    import remote, scenes_telefon
    scenes_telefon.S.update(starting=True, err="", code="")
    emit(type="scene_do", kind="telefon", do={"data": scenes_telefon.view()})
    r = remote.start()
    scenes_telefon.S.update(starting=False, err="" if r == "ok" else r)
    if r == "ok" and not remote.paired_count():
        remote.arm_pair()
    if scene_state["on"] and scene_state["kind"] == "telefon":
        emit(type="scene_do", kind="telefon", do={"data": scenes_telefon.view()})
        if hooks["say"]:
            hooks["say"]("Telefon bağlantısı hazır efendim, QR kodu ekranda." if r == "ok" else r)


def close_scene(speak: bool = False):
    w, kind, was_on = scene_state["w"], scene_state["kind"], scene_state["on"]
    scene_state.update(on=False, w=None, kind=None)
    _stop_tap()
    if kind == "ders":
        import ders_srv
        threading.Thread(target=ders_srv.shutdown, daemon=True).start()
    if kind == "mola":
        import mola
        mola.end()
    if kind == "telefon":
        import remote
        if not remote.S["auto"]:
            remote.stop()
    if kind == "odak":
        import odak
        odak.end()
    _forget_ultron(kind)
    if w is not None:
        try:
            w.destroy()
        except Exception:
            pass
    print("SAHNE: kapatıldı", flush=True)
    if speak and was_on and hooks["say"]:
        import scenes
        hooks["say"](scenes.EXIT_SAY.get(kind, "Mod kapandı efendim."))


def scene_dispatch(text: str):
    """Sahne modundaki her cümle: yalnızca o modun komutları."""
    scene_run(scene_state["kind"], text, scene_state["st"], True)


def scene_run(kind: str, text: str, st: dict, speak: bool = True):
    """Bir mod komutunu çalıştırır. speak=False (uzaktan telefon): bilgisayarda konuşma ve pencere kapatma olmaz; sonuç emit ile (abone telefonlara da) gider."""
    import scenes
    r = scenes.handle(kind, text, st)
    if not r:
        return
    say = hooks["say"] if speak else None
    if say and kind in ("ultron", "friday", "luna"):   # kişiliğin kısa komut cevapları da kendi sesiyle söylenir; çıkış cümlesi Jarvis'indir
        import sohbet
        say = lambda s, cont=False, _k=kind: sohbet.say_as(_k, s, cont)
    if r.get("exit"):
        if speak:
            close_scene(speak=False)
            if hooks["say"]:
                hooks["say"](r["say"])
        return
    if kind == "muzik":
        emit(type="scene_do", kind=kind, do={**(r.get("do") or {}), "msg": r.get("say", "")})
        if r.get("later"):
            def later(f=r["later"]):
                try:
                    emit(type="scene_do", kind=kind, do={"msg": f()})
                except Exception as e:
                    print("müzik komutu hatası:", e, flush=True)
            threading.Thread(target=later, daemon=True).start()
        return
    if kind in ("pomodoro", "odakoda"):
        import pomodoro, study_music
        _pomo_music(r.get("music"))
        emit(type="scene_do", kind=kind, do={**(r.get("do") or {}), "snap": pomodoro.snapshot(), "np": study_music.status(), "msg": r.get("say", "")})
        if say and r.get("say"):
            say(r["say"])
        return
    if kind in ("kartlar", "gelisim", "satranc", "oyunlar", "kuran", "harita", "listeler", "vpn", "telefon"):
        _mode_result(kind, r, speak=speak, st=st)
        return
    if r.get("do"):
        emit(type="scene_do", kind=kind, do=r["do"])
    if say and r.get("say"):
        say(r["say"])


def _mode_ws(data: dict, st: dict = None, speak: bool = True):
    """Kartlar / gelişim penceresindeki düğmeler: işlem modülde yapılır, sonuç sesli komutla aynı yoldan sayfaya gider."""
    kind = str(data.get("type", "")).split("_")[0]
    st = scene_state["st"] if st is None else st
    try:
        import scenes_kartlar, scenes_gelisim, scenes_satranc, scenes_oyunlar, scenes_kuran, scenes_harita, scenes_listeler, scenes_vpn
        mod = {"kartlar": scenes_kartlar, "gelisim": scenes_gelisim, "satranc": scenes_satranc, "oyunlar": scenes_oyunlar, "kuran": scenes_kuran, "harita": scenes_harita, "listeler": scenes_listeler, "vpn": scenes_vpn}[kind]
        r = mod.ws(data, st) or {}
    except Exception as e:
        print(f"{kind} düğme hatası:", type(e).__name__, flush=True)
        r = {"say": ""}
    if _scene_on(kind):
        _mode_result(kind, r, speak=bool(r.get("speak")) and speak, st=st)


def _mode_result(kind: str, r: dict, speak: bool = True, st: dict = None):
    """Kartlar / gelişim: her komuttan sonra güncel görünüm sayfaya gider; uzun iş (kart üretimi, rapor gönderme) bitince sonucu söyler."""
    say = hooks["say"]
    if r.get("quiet"):                                # ör. haritanın kamera konumu kaydı: sayfaya geri bir şey gönderilmez
        return
    view = _scene_view(kind, st)
    extra = {}
    if kind == "listeler":                              # çalan şarkı bilgisi her sonuçla birlikte gider
        import study_music
        extra = {"np": study_music.status()}
    emit(type="scene_do", kind=kind, do={**(r.get("do") or {}), **extra, "data": view(), "msg": r.get("say", "")})
    if r.get("open_url"):                             # Kur'an: meal / tilavet YouTube Music'te (varsayılan tarayıcı); mod penceresi öne sabitlenmeden küçülür
        def _open(u=r["open_url"]):
            import webbrowser
            if not str(u).startswith("https://music.youtube.com/"):
                return
            peek_desktop()
            webbrowser.open(u)
        threading.Thread(target=_open, daemon=True).start()
    if r.get("later"):
        def later(f=r["later"]):
            try:
                msg = f()
            except Exception as e:
                print(f"{kind} arka plan hatası:", type(e).__name__, flush=True)
                msg = "Bir hata oldu efendim, işlem tamamlanamadı."
            do = {}
            if isinstance(msg, dict):                 # arka plan işi sayfaya komut da döndürebilir (ör. harita: {'do': {'fly': ...}, 'say': ...})
                do, msg = msg.get("do") or {}, msg.get("say", "")
            if _scene_on(kind):
                emit(type="scene_do", kind=kind, do={**do, **extra, "data": view(), "msg": msg, "done": True})
                if hooks["say"] and msg and speak:
                    hooks["say"](msg)
        threading.Thread(target=later, daemon=True).start()
    if speak and say and r.get("say"):
        say(r["say"])


def _scene_view(kind: str, st: dict = None):
    if kind == "kartlar":
        import kartlar
        return kartlar.view
    if kind == "satranc":
        import satranc
        return satranc.view
    if kind == "oyunlar":
        import oyunlar
        return oyunlar.view
    if kind == "kuran":
        import kuran
        return kuran.view
    if kind == "harita":
        import harita
        return harita.view
    if kind == "listeler":
        import muzik_listeleri
        return muzik_listeleri.view
    if kind == "vpn":
        import scenes_vpn
        return scenes_vpn.view
    if kind == "telefon":
        import scenes_telefon
        return scenes_telefon.view
    import gelisim
    return lambda: gelisim.view((scene_state["st"] if st is None else st).get("week", 0))


def remote_open(kind: str) -> str:
    """Telefondaki 'Bilgisayarı yönet' düğmeleri: açık modu kapatıp istenen modu BİLGİSAYARDA açar (kapat / peek / browser / illusion / hero ya da herhangi bir sahne türü)."""
    import scenes
    if kind == "peek":
        peek_desktop()
        return "ok"
    if kind == "browser":
        import jbrowser
        jbrowser.open_start()
        return "ok"
    if scene_state["on"]:
        close_scene(speak=False)
        time.sleep(0.7)
    if ill_state["on"]:
        close_illusion(False)
        time.sleep(0.5)
    if hero_state["on"]:
        close_hero(False)
        time.sleep(0.5)
    if kind == "close":
        return "ok"
    if kind == "illusion":
        return open_illusion()
    if kind == "hero":
        return open_hero()
    if kind in scenes.KINDS:
        return open_scene(kind)
    return "bilinmeyen mod"


_BLOCK_SEND = {"rapor", "gelisim"}      # WhatsApp'a gönderme yapabilen modlar: uzaktan gönderme kapalı


def remote_attach(kind: str) -> None:
    """Uzaktan telefon bir modu açtı: PC penceresi yoksa o modun arka plan döngüleri (ölçüm, sayaç, çalan şarkı) başlatılır."""
    _start_mode_loops(kind)


def remote_detach(kind: str) -> None:
    """Son telefon da ayrıldı (ve bekleme süresi geçti): PC penceresi yoksa modun döngüsü kendiliğinden biter, kaynaklar kapanır."""
    if scene_state["on"] and scene_state["kind"] == kind:
        return
    if kind in ("ultron", "friday", "luna", "sohbet"):
        _forget_ultron(kind)                          # telefondan kapanınca da geçmiş ve işlem günlüğü silinir
    elif kind == "muzik":
        _stop_tap()
    elif kind == "ders":
        import ders_srv
        threading.Thread(target=ders_srv.shutdown, daemon=True).start()


def remote_ws(kind: str, d: dict, st: dict) -> None:
    """Uzaktan telefondan gelen mod mesajı: PC penceresindeki düğmelerle aynı işlev çalışır, sonuç emit ile telefona döner. Bilgisayarda konuşma/pencere işlemi olmaz."""
    import re as _re
    ty = str(d.get("type") or "")
    if ty == "scene_state" and isinstance(d.get("state"), dict) and len(json.dumps(d["state"])) < 1500:
        st.update(d["state"])
    elif ty == "text" and isinstance(d.get("text"), str) and d["text"].strip():
        text = d["text"].strip()[:500]
        if kind in _BLOCK_SEND and _re.search(r"gönder|yolla|babam|whatsapp", text.lower()):
            emit(type="scene_do", kind=kind, do={"msg": "Gönderme uzaktan kapalı efendim, bunu bilgisayarın başında yapabilirsiniz."})
            return
        scene_run(kind, text, st, False)
    elif ty.startswith("notes_") and kind == "notlar":
        notes_ws(d)
    elif ty.startswith("yuvam_") and kind == "yuvam":
        yuvam_ws(d)
    elif ty.startswith("rapor_") and kind == "rapor":
        if ty == "rapor_send":
            emit(type="scene_do", kind="rapor", do={"sendState": "failed", "msg": "Rapor göndermek uzaktan kapalı efendim, taslak olarak duruyor."})
        else:
            rapor_ws(d)
    elif ty.startswith(("kartlar_", "gelisim_", "vpn_")) and ty.split("_")[0] == kind:
        _mode_ws(d, st, False)
    elif ty.startswith("ders_") and kind == "ders":
        _ders_handle(d)
    elif ty == "music_stop" and kind in ("pomodoro", "listeler", "muzik"):
        import study_music
        study_music.stop()
    elif ty == "music_repeat" and kind in ("pomodoro", "listeler", "muzik"):
        import study_music
        study_music.set_repeat(not study_music.repeat_on())


ill_state ={"on": False, "w": None, "n": 1, "auto": False}


def open_illusion() -> str:
    """Görsel illüzyon modu: tam ekran, 50 illüzyon. Açıkken normal Jarvis dinlemez; cümleler yalnızca illusion.handle'a gider."""
    import webview
    if ill_state["on"]:
        return "İllüzyon modu zaten açık efendim."
    if hero_state["on"]:
        return "Önce kahraman modunu kapatmanız gerekiyor efendim."
    if scene_state["on"]:
        return "Önce açık olan sahne modunu kapatmanız gerekiyor efendim."
    ill_state.update(on=True, n=1, auto=False)
    w = webview.create_window("JARVIS İLLÜZYON", f"{ALLOWED_ORIGIN}/illusion?t={TOKEN}", fullscreen=True, on_top=True,
                              background_color="#000000")

    def closed():
        if ill_state["on"]:
            ill_state.update(on=False, w=None)
            print("İLLÜZYON: pencere kapandı, normal Jarvis geri döndü", flush=True)
    w.events.closed += closed
    ill_state["w"] = w
    focus_window("JARVIS İLLÜZYON")
    print("İLLÜZYON: açıldı, normal dinleme askıda", flush=True)
    return "ok"


def close_illusion(speak: bool = False):
    w = ill_state["w"]
    was_on = ill_state["on"]
    ill_state.update(on=False, w=None, auto=False)
    if w is not None:
        try:
            w.destroy()
        except Exception:
            pass
    print("İLLÜZYON: kapatıldı", flush=True)
    if speak and was_on and hooks["say"]:
        hooks["say"]("İllüzyon modu kapandı efendim, normale döndüm.")


def ill_exec(n: int):
    """Pencerede tıklama / ok tuşu: yalnızca görsel."""
    if 1 <= n <= 50:
        ill_state["n"] = n
        emit(type="ill_do", n=n)


def ill_dispatch(text: str):
    """İllüzyon modundaki her cümle: yalnızca illüzyon komutları."""
    import illusion
    r = illusion.handle(text, ill_state)
    if not r:
        return
    say = hooks["say"]
    if r.get("exit"):
        close_illusion(speak=False)
        if say:
            say(r["say"])
        return
    if "auto" in r:
        ill_state["auto"] = r["auto"]
    if r.get("n"):
        ill_state["n"] = r["n"]
    emit(type="ill_do", **{k: v for k, v in r.items() if k not in ("say", "same")})
    if say and r.get("say"):
        say(r["say"])


hero_state = {"on": False, "w": None, "mask": "armor"}
hooks = {"say": None}


def open_hero() -> str:
    """Kahraman modu: tam ekran maske penceresi. Açıkken normal Jarvis dinlemez; cümleler yalnızca hero.handle'a gider."""
    import webview
    if hero_state["on"]:
        return "Kahraman modu zaten açık efendim."
    if ill_state["on"]:
        return "Önce illüzyon modunu kapatmanız gerekiyor efendim."
    if scene_state["on"]:
        return "Önce açık olan sahne modunu kapatmanız gerekiyor efendim."
    hero_state.update(on=True, mask="armor")
    w = webview.create_window("JARVIS KAHRAMAN", f"{ALLOWED_ORIGIN}/hero?t={TOKEN}", fullscreen=True, on_top=True,
                              background_color="#01050b")

    def closed():
        if hero_state["on"]:
            hero_state.update(on=False, w=None)
            print("KAHRAMAN: pencere kapandı, normal Jarvis geri döndü", flush=True)
    w.events.closed += closed
    hero_state["w"] = w
    focus_window("JARVIS KAHRAMAN")
    print("KAHRAMAN: açıldı, normal dinleme askıda", flush=True)
    return "ok"


def close_hero(speak: bool = False):
    w = hero_state["w"]
    was_on = hero_state["on"]
    hero_state.update(on=False, w=None)
    if w is not None:
        try:
            w.destroy()
        except Exception:
            pass
    print("KAHRAMAN: kapatıldı", flush=True)
    if speak and was_on and hooks["say"]:
        hooks["say"]("Kahraman modu kapandı efendim, normale döndüm.")


def hero_exec(n: int, mask: str):
    """Pencerede bir özelliğe tıklanınca (sessiz, yalnızca görsel)."""
    import hero
    m = mask if mask in hero.MASKS else hero_state["mask"]
    hero_state["mask"] = m
    if n == 0:
        reply = "Efektler sıfırlandı efendim."
    elif 1 <= n <= len(hero.MASKS[m]["features"]):
        reply = hero.MASKS[m]["features"][n - 1][2]
    else:
        return
    emit(type="hero_do", mask=m, n=n, say=reply)


def hero_dispatch(text: str):
    """Kahraman modundaki her cümle: yalnızca maske komutları. LLM, araçlar, uyandırma kelimesi yok."""
    import hero
    r = hero.handle(text, hero_state)
    if not r:
        return
    say = hooks["say"]
    if r.get("exit"):
        close_hero(speak=False)
        if say:
            say(r["say"])
        return
    if r.get("switch"):
        hero_state["mask"] = r["mask"]
    elif r.get("mask"):
        hero_state["mask"] = r["mask"]
    emit(type="hero_do", **{k: v for k, v in r.items()})
    if say and r.get("say"):
        say(r["say"])


mebi_state = {"w": None, "tr": None}


def open_mebi(goto_last: bool = False) -> str:
    """MEBİ penceresi: tam ekran mod DEĞİL, Jarvis dinlemeye devam eder. Giriş gerekirse öğrenci kendisi yazar; izleme pasiftir (mebi.py)."""
    import webview, mebi
    goto = mebi.last_topic()[0] if goto_last else None
    if mebi_state["w"] is not None:
        if goto and mebi_state["tr"]:
            mebi_state["tr"].goto = goto
        focus_window(mebi.TITLE)
        return "ok"
    w = webview.create_window(mebi.TITLE, mebi.HOME, width=1280, height=860, background_color="#ffffff")

    def closed():
        tr = mebi_state["tr"]
        if tr:
            tr.stop()
        mebi_state.update(w=None, tr=None)
        print("MEBİ: pencere kapandı", flush=True)
    w.events.closed += closed
    tr = mebi.Tracker(w, goto=goto)
    tr.start()
    mebi_state.update(w=w, tr=tr)
    focus_window(mebi.TITLE)
    print("MEBİ: açıldı, izleme başladı", flush=True)
    return "ok"


def mebi_cmd(action: str) -> str:
    """Sesli komutlar için: open / resume / close / status. Söylenecek metni döner."""
    import mebi
    g, tp = mebi.last_topic()
    if action == "is_open":                          # extras.route_browser: geri/ileri komutu hangi pencereye gidecek
        return "1" if mebi_state["w"] is not None else ""
    if action.startswith("nav_"):
        w = mebi_state["w"]
        if w is None:
            return "MEBİ şu an açık değil efendim."
        fr = "(function(){var f=document.getElementById('mainFrame');var w=f?f.contentWindow:window;%s})()"     # içerik #mainFrame iframe'indedir
        js = {"nav_back": "history.back()", "nav_forward": "history.forward()",
              "nav_reload": fr % "w.location.reload();", "nav_home": fr % "w.location.href='/student/home';"}.get(action)
        if not js:
            return "Bu komutu MEBİ penceresinde yapamıyorum efendim."
        try:
            w.evaluate_js(js)
        except Exception:
            return "MEBİ penceresine ulaşamadım efendim."
        return {"nav_back": "Geri gittim efendim.", "nav_forward": "İleri gittim efendim.", "nav_reload": "Sayfayı yeniledim efendim.", "nav_home": "MEBİ ana sayfasına gittim efendim."}[action]
    if action == "close":
        w = mebi_state["w"]
        if w is None:
            return "MEBİ zaten kapalı efendim."
        try:
            w.destroy()
        except Exception:
            pass
        return "MEBİ'yi kapattım efendim."
    if action == "status":
        if not tp:
            return "MEBİ'de henüz kayıtlı bir konu çalışmanız yok efendim."
        return mebi.describe(tp)
    if action == "quiz":
        t = mebi.quiz_topic(tp) if tp else None
        if not t:
            return "Önce MEBİ'de bir konuya girmeniz gerekiyor efendim, konu adını okuyamadım."
        import ders_srv
        ders_srv.AUTO["topic"] = t
        res = open_scene("ders")
        if res != "ok":
            ders_srv.AUTO["topic"] = None
            return res
        kz = len(tp.get("kaz") or [])
        return (f"Tamam efendim, {t['konu']} konusundan " + (f"MEBİ'nin {kz} kazanımına göre " if kz else "")
                + "sorular hazırlıyorum, ders modu açılıyor. İlk seferde birkaç saniye sürebilir.")
    res = open_mebi(action == "resume")
    if res != "ok":
        return res
    if action == "resume" and tp:
        return "MEBİ'yi açıyorum, son konunuza gidiyorum. " + mebi.describe(tp)
    if action == "resume":
        return "MEBİ'yi açıyorum efendim. Henüz kayıtlı bir konunuz yok, ders ve konuyu siz seçin."
    return "MEBİ açılıyor efendim. Giriş sayfası gelirse bilgilerinizi siz yazın, ben görmem." + (f" Son konunuz {tp['konu']}, devam etmek ister misiniz?" if tp and tp.get("konu") else "")


def remote_cmd(action: str) -> str:
    """Uzaktan (internet) telefon erişimi: yalnızca uyku/tarif/spor/panel modları, bilgisayara erişim yok (remote.py). Söylenecek metni döner."""
    import remote
    if action in ("full_on", "full_off"):
        import settings
        on = action == "full_on"
        settings.set("uzak_tam_kontrol", on)
        if not on:
            remote.kick_pc()
            return "Telefondan bilgisayar kontrolünü kapattım efendim. Ekran ve serbest komut artık çalışmaz, bağlantılar kesildi."
        return ("Telefondan bilgisayar kontrolü açık efendim. Yalnızca Tailscale ile bağlanan, eşleşmiş telefon ekranımı görebilir ve bana komut verebilir; "
                "herkese açık adresten asla. Kapatmak için telefon kontrolünü kapat deyin.")
    if action in ("ts_on", "ts_off", "ts_addr"):
        import settings
        if action == "ts_off":
            settings.set("uzak_tailscale", False)
            remote.ts_stop()
            return "Tailscale ile telefon erişimini kapattım efendim."
        if action == "ts_on":
            settings.set("uzak_tailscale", True)
        r = remote.ts_start()
        if r != "ok":
            return r + (" Kurulunca tekrar söyleyin; açılışta kendiliğinden de denerim." if action == "ts_on" else "")
        if not remote.paired_count():
            remote.arm_pair()
        emit(type="jarvis", text=f"Telefon uygulamasının adresi: {remote.TS['ip']}")
        try:
            import pyperclip
            pyperclip.copy(remote.TS["ip"])
        except Exception:
            pass
        return (f"Tailscale ile telefon erişimi açık efendim. Telefon uygulamasına şu adresi yazın: {' '.join(remote.TS['ip'])}. Adres ekrana yazıldı ve panoya kopyalandı. "
                + ("İlk seferde telefonda kod ister, kodu ekranda göstereceğim." if not remote.paired_count() else "Eşleşmiş telefonlar doğrudan girer."))
    import remote_auto
    if action == "auto_on":
        remote_auto.set_enabled(True)
        return ("Uzaktan erişim artık Jarvis açılınca kendiliğinden açılacak efendim; her yeni link kendi WhatsApp numaranıza gönderilecek. "
                + ("" if remote_auto.number() else "Ama config dosyasında uzak_wa_no numarası yok, o yüzden link şimdilik yalnızca ekranda görünecek. "))
    if action == "auto_off":
        remote_auto.set_enabled(False)
        return "Otomatik uzaktan erişimi kapattım efendim, tünel de kapandı."
    if action == "close":
        if not remote.S["on"]:
            return "Uzaktan erişim zaten kapalı efendim."
        if remote_auto.enabled():
            remote_auto.set_enabled(False)
            return "Uzaktan erişimi kapattım efendim; otomatik açılışı da kapattım, yeniden açmak için otomatik aç deyin."
        remote.stop()
        return "Uzaktan erişimi kapattım efendim, tünel ve sunucu tamamen kapandı."
    if action == "status":
        return (f"Uzaktan erişim açık efendim. Adres ekranda. {remote.paired_count()} telefon eşleşmiş." if remote.S["on"]
                else f"Uzaktan erişim kapalı efendim. {remote.paired_count()} telefon eşleşmiş.")
    if action == "revoke":
        n = remote.revoke_all()
        return f"{n} telefon eşleşmesini sildim efendim." if n else "Kayıtlı bir telefon eşleşmesi yok efendim."
    if action == "pair":
        if not remote.S["on"]:
            return "Önce uzaktan erişimi açmanız gerekiyor efendim."
        remote.arm_pair()
        return "Eşleştirme üç dakika açık efendim. Telefonda KOD İSTE'ye basın, kodu bilgisayarın ekranında göstereceğim."
    if remote.S["on"]:
        _remote_show()
        return "Uzaktan erişim zaten açık efendim, adresi yeniden gösterdim."
    import remote_auto
    r = remote.start(auto=remote_auto.enabled())
    if r != "ok":
        return r
    if not remote.paired_count():
        remote.arm_pair()
    _remote_show()
    return ("Uzaktan erişim açıldı efendim. Adres ekranda ve panoya kopyalandı; telefonda açın. "
            + ("Bu telefon ilk kez bağlanacaksa KOD İSTE'ye basın, kodu ekranda göstereceğim. " if remote.paired_count() == 0 else "Eşleşmiş telefon doğrudan girer, yeni telefon için telefonu eşleştir deyin. ")
            + "İki saat sonra kendiliğinden kapanır. Telefon yalnızca kişisel verisi olmayan modları (laboratuvarlar, uzay, ortam, satranç, harita, uyku, tarif, spor, panel gibi) açabilir; bilgisayarınızdaki bilgilere ve uygulamalara erişemez.")


def _remote_show():
    import remote
    u = remote.login_url() or remote.url()
    ui("show")
    emit(type="jarvis", text=f"Uzaktan erişim adresi: {u}")
    try:
        import pyperclip
        pyperclip.copy(u)
    except Exception:
        pass
    try:
        tray.notify(u, "Jarvis uzaktan erişim")
    except Exception:
        pass


def mola_cmd(action: str, minutes=None) -> str:
    """Mola için sesli komutlar ve zamanlayıcı düğmeleri. open: mod açılır, süreyi siz seçersiniz; start: mod açılır ve mola hemen başlar;
    default: varsayılan süre kaydedilir; timer: mola tam ekran zamanlayıcıda çalışır (mod açılmaz). Söylenecek metni döner."""
    import mola
    if action == "default":
        return f"Varsayılan mola süresi {mola.set_default(minutes)} dakika oldu efendim."
    if action == "timer":
        import reminders
        m = mola.clamp(minutes) if minutes else mola.default_len()
        open_timer(float(m), "MOLA", reminders.add_at(m * 60, "mola", "mola"))
        return f"{m} dakikalık mola zamanlayıcısı başladı efendim. Bitince haber veririm."
    if scene_state["on"] and scene_state["kind"] == "mola":
        if action != "start":
            return "Mola modu zaten açık efendim."
        m = mola.start(minutes)
        emit(type="scene_do", kind="mola", do={"snap": mola.snapshot()})
        return f"{m} dakikalık mola başladı efendim."
    start = action == "start"
    m = mola.start(minutes) if start else 0              # önce başlatılır: sayfa açılışta çalışan molayı görür
    res = open_scene("mola")
    if res != "ok":
        if start:
            mola.end()
        return res
    if start:
        return f"{m} dakikalık mola başlıyor efendim, mola modu açılıyor. Bitince haber veririm. Çıkmak için çık demeniz yeterli."
    return (f"Mola modu açılıyor efendim. Varsayılan mola süresi {mola.default_len()} dakika. Başlat deyin ya da bir süre söyleyin, "
            "örneğin on beş dakika.")


def timer_to_break(due: float, minutes: float):
    """Zamanlayıcı penceresinden molaya geçiş: sayaç kapanır (dolmadıysa hatırlatması da iptal), mola modu başlar."""
    close_timer(due, cancel=True)
    msg = mola_cmd("start", minutes)
    if hooks["say"]:
        hooks["say"](msg)


guide_win = {"w": None}


def open_guide() -> str:
    """Kılavuzu tarayıcıya değil, ekranı kaplayan Jarvis penceresine açar (KAPAT ya da Esc ile kapanır)."""
    import webview
    if guide_win["w"] is not None:
        return "Kılavuz zaten ekranda efendim."
    w = webview.create_window("JARVIS KILAVUZ", f"{ALLOWED_ORIGIN}/guide?t={TOKEN}", fullscreen=True, on_top=True,
                              background_color="#01050b", text_select=True)

    def closed():
        guide_win["w"] = None
    w.events.closed += closed
    guide_win["w"] = w
    focus_window("JARVIS KILAVUZ")
    print("KILAVUZ: açıldı", flush=True)
    return "ok"


def close_guide():
    w, guide_win["w"] = guide_win["w"], None
    if w is not None:
        try:
            w.destroy()
        except Exception:
            pass


def code_cancel():
    """İptal: pencereyi kapatır. Hiçbir şey yazılmadıysa boş proje klasörünü de siler, yazıldıysa dosyayı korur."""
    import shutil
    d, w = code_state["dir"], code_state["w"]
    if w is None:
        return
    code_state["w"] = None
    import codeproj
    codeproj.kill()
    try:
        w.destroy()
    except Exception:
        pass
    kept = True
    try:
        mp = os.path.join(d, "main.py")
        empty = not os.path.exists(mp) or not open(mp, encoding="utf-8").read().strip()
        if empty and os.path.dirname(os.path.abspath(d)) == os.path.abspath(CODE_ROOT) and os.path.basename(d).startswith("proje_"):
            shutil.rmtree(d, ignore_errors=True)
            kept = False
    except OSError:
        pass
    print(f"KOD: iptal edildi (klasör {'korundu' if kept else 'silindi'})", flush=True)
    emit(type="jarvis", text="Kod yazma ekranını kapattım efendim." + (" Yazdıklarınız proje klasöründe duruyor." if kept else " Boş proje klasörünü sildim."))


def mic_set(muted: bool, session: bool = False) -> bool:
    """Mikrofonu sessize alır / açar. Kapalıyken pencere açıkken hiçbir ses işlenmez; yalnızca pencere kapalıyken "Hey Jarvis" dinlenir.
    Yazılı komutlar çalışmaya devam eder. session=True: oturum başı/sonu otomatik geçişi (kullanıcının seçimini silmez)."""
    v = VOICE
    if v is None:
        return False
    if not session:
        v.restore_muted = False                    # kullanıcı kendisi değiştirdi: oturum sonunda geri çevirme
    v.muted = bool(muted)
    if v.muted:
        try:
            v._flush()
        except Exception:
            pass
    emit(type="mic", muted=v.muted)
    print("MİKROFON:", "kapalı" if v.muted else "açık", flush=True)
    return True


def music_loop():
    """Ana ekran: Jarvis'in kendi oynatıcısı (ders müziği, 'X çal') çalıyorsa kapat ve döngü düğmeleri için durumu yollar."""
    import study_music
    last = None
    tick = 0
    while True:
        time.sleep(1)
        if not clients:
            continue
        tick += 1
        if tick % 5 == 0 and VOICE is not None:
            emit(type="mic", muted=bool(getattr(VOICE, "muted", False)))
        s = study_music.status()
        cur = (s["title"], s["playing"], s["repeat"]) if s else None
        if cur != last:
            last = cur
            emit(type="music", on=bool(s), title=(s or {}).get("title", ""), paused=bool(s) and not s["playing"], repeat=study_music.repeat_on())


def stats_loop():
    import psutil
    while True:
        time.sleep(2)
        if not clients:
            continue
        gpu = temp = None
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=5, creationflags=0x08000000).stdout
            gpu, temp = (int(x) for x in out.strip().split(",")[:2])
        except Exception:
            pass
        emit(type="stats", cpu=psutil.cpu_percent(), ram=psutil.virtual_memory().percent, gpu=gpu, temp=temp)


_TR_HINT = __import__("re").compile(r"[çğıöşü]|\b(ve|bir|bu|ne|aç|kapat|çal|mı|mi|nasıl|lütfen|saat|merhaba|evet|hayır|tamam|kaç)\b")
_EN_HINT = __import__("re").compile(r"\b(the|open|play|close|what|how|is|are|you|please|hello|hi|thanks|thank|yes|no|can|tell|me|my|time|search|i)\b")


def guess_lang(text: str) -> str:
    """Yazılan metnin dili (Türkçe varsayılan). İngilizce 'I' Türkçe 'ı' sayılmasın diye düz lower()."""
    low = text.replace("İ", "i").lower()
    return "en" if _EN_HINT.search(low) and not _TR_HINT.search(low) else "tr"


RESET = ("geçmişi sil", "geçmişi temizle", "sohbeti sil", "sohbeti sıfırla", "sohbeti temizle", "konuşmayı sıfırla",
         "kendini yeniden başlat", "kendini sıfırla", "yeniden başlat kendini", "reboot", "clear history", "clear the history")
WIPE_ALL = ("her şeyi unut", "hafızanı tamamen sil", "hafızanı sıfırla", "hafızanı sil", "tamamen sıfırla")
session_end = threading.Event()   # pencere X ile kapatılınca oturum biter, tekrar 'hey Jarvis' beklenir
POWER_OFF = __import__("re").compile(
    r"\b(sistemi|sistem|bilgisayarı|bilgisayar|pc'?yi|pc)\s+(kapat|kapatır mısın|kapatsana|kapatabilir misin)|"
    r"\b(shut ?down|turn off)\s+(the\s+)?(system|computer|pc)\b|\bshut ?down\b")
POWER_RESTART = __import__("re").compile(
    r"\b(sistemi|bilgisayarı|bilgisayar|pc'?yi)\s+yeniden\s+başlat|\brestart\s+(the\s+)?(system|computer|pc)\b")
POWER_CANCEL = __import__("re").compile(r"\b(iptal|vazgeç|vazgeçtim|kapatma|dur|cancel|abort|stop)\b")
GOODBYE = ('teşekkürler jarvis', 'teşekkür ederim jarvis', 'görüşürüz', 'hoşça kal', 'kendini kapat', 'kapat kendini',
           'uyu jarvis', 'iyi geceler', 'bu kadar jarvis', 'kapat jarvis',
           'thank you jarvis', 'thanks jarvis', 'goodbye', 'bye jarvis', 'good night jarvis', "that's all jarvis")
QUIET_TOOLS = {"research", "datetime_now", "wifi_name", "system_info", "read_whatsapp", "list_files", "read_file"}


def ui(action):
    """Pencereyi Windows API ile göster/gizle/küçült (pywebview show/hide ikinci seferde güvenilir değil)."""
    import ctypes
    u = ctypes.windll.user32
    hwnd = u.FindWindowW(None, "JARVIS")
    if not hwnd:
        return
    if action == "show":
        if u.GetForegroundWindow() == hwnd and u.IsWindowVisible(hwnd) and not u.IsIconic(hwnd):
            return                                 # zaten önde: odağı (yazı kutusunu) bozma
        u.ShowWindow(hwnd, 9)                      # SW_RESTORE
        u.keybd_event(0x12, 0, 0, 0)               # Alt: ön plana alma kısıtını aşar
        u.SetForegroundWindow(hwnd)
        u.keybd_event(0x12, 0, 2, 0)
    elif action == "hide":
        u.ShowWindow(hwnd, 0)                      # SW_HIDE
    elif action == "minimize":
        u.ShowWindow(hwnd, 6)                      # SW_MINIMIZE


def start_tray():
    import pystray
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (64, 64), "#02060c")
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), outline="#00cfff", width=5)
    d.ellipse((24, 24, 40, 40), fill="#00cfff")
    def phone_connect(icon, _item):
        import phone
        icon.notify(phone.connect("tr"), "Jarvis")

    def phone_mirror(icon, _item):
        import phone
        icon.notify(phone.connect("tr", mirror=True), "Jarvis")

    menu = pystray.Menu(pystray.MenuItem("Jarvis'i göster", lambda: ui("show"), default=True),
                        pystray.MenuItem("Telefona bağlan (USB)", phone_connect),
                        pystray.MenuItem("Ekranı telefona yansıt (USB)", phone_mirror),
                        pystray.MenuItem("Çıkış", lambda: (__import__("fan").stop_quietly(), os._exit(0))))
    icon = pystray.Icon("jarvis", img, "Jarvis", menu)
    icon.run_detached()
    return icon


def wipe_traces():
    """'Her şeyi unut': diskte kalan ses parçaları, ekran görüntüleri ve günlük (duyulan cümleler) de silinir."""
    import glob
    for pat in (os.path.join(HERE, "diag", "*.wav"), os.path.join(HERE, "workspace", "ss_*.png"), _LOG + ".1"):
        for f in glob.glob(pat):
            try:
                os.remove(f)
            except OSError:
                pass
    try:
        _log.truncate(0)
    except (OSError, ValueError):
        pass


def run_assistant():
    from brain import Brain
    from voice import Voice
    import whatsapp, router
    whatsapp.start_watcher()
    brain = Brain()
    emit(type="state", state="thinking", text="Yükleniyor...")
    while True:      # bilgisayar yeni açıldığında mikrofon/ekran kartı hazır olmayabilir: hazır olana kadar dene
        try:
            voice = Voice(on_level=lambda v: emit(type="level", v=v))
            break
        except Exception:
            import traceback
            traceback.print_exc()
            time.sleep(10)
    ui("hide")
    tray.notify("Jarvis hazır. 'Jarvis' diyebilirsiniz.", "Jarvis")

    global VOICE
    VOICE = voice
    # mod ve laboratuvarlarda (sahne, illüzyon, kahraman) komut uygulanır uygulanmaz unutulur: söylenen metin günlüğe, ses parçası diske yazılmaz;
    # komut yalnızca işlenirken RAM'de durur (cmdbuf), bitince silinir
    voice.is_private = lambda: bool(scene_state["on"] or ill_state["on"] or hero_state["on"])
    lang = {"v": "tr"}

    def send_audio(data: bytes, mime: str):
        import base64
        emit(type="audio", mime=mime, data=base64.b64encode(data).decode())   # yalnızca telefon ekranı çalar

    def say(text, cont=False) -> bool:
        """Söyler; sözü kesildiyse True döner. Ses önce hazırlanır, metin ve ses aynı anda başlar."""
        prep = voice.prepare(text, lang["v"])
        if not sys.modules["voice"].PERSONA["name"] and not (scene_state["on"] and scene_state["kind"] == "elektronik"):      # elektronik lab: cevaplar yalnızca sayfanın kendi satırında (do.msg) görünür, ana sohbete yazılmaz; Ultron'un sözleri Jarvis'in HUD günlüğüne/telefon ekranına yazılmaz; yalnızca Ultron penceresinde görünür
            emit(type="jarvis", text=text, cont=cont)
        emit(type="state", state="speaking")
        if not prep:
            return False
        return voice.play(prep[0], prep[1], on_audio=send_audio if len(clients) > 1 else None)

    from concurrent.futures import ThreadPoolExecutor
    _tts_pool = ThreadPoolExecutor(max_workers=3)

    def say_all(sentences) -> bool:
        """Cümleler ayrı bir iş parçacığında üretilir ve üretilir üretilmez sentezlenmeye başlar; önceki cümle çalarken
        sonrakiler hazırlanır. Her cümlenin metni, sesi başladığı anda ekrana gelir. Sözü kesilirse durur."""
        import queue as _q
        q = _q.Queue()
        stop = threading.Event()
        lg = lang["v"]

        def producer():
            try:
                for s in sentences:
                    if stop.is_set() or session_end.is_set():
                        break
                    if s.startswith("\x00DISPLAY:"):
                        q.put(("disp", s, None))
                    else:
                        q.put(("say", s, _tts_pool.submit(voice.prepare, s, lg)))
            except Exception as e:
                q.put(("err", e, None))
            finally:
                try:
                    if hasattr(sentences, "close"):
                        sentences.close()
                except Exception:
                    pass
                q.put(None)

        th = threading.Thread(target=producer, daemon=True)
        th.start()
        said, interrupted = False, False
        try:
            while True:
                item = q.get()
                if item is None:
                    break
                kind, s, fut = item
                if kind == "err":
                    raise s
                if session_end.is_set():
                    interrupted = True
                    break
                if kind == "disp":                          # kod vb.: seslendirme, yalnızca ekrana yaz
                    emit(type="jarvis", text=s[len("\x00DISPLAY:"):], cont=said)
                    said = True
                    continue
                emit(type="jarvis", text=s, cont=said)
                prep = fut.result()
                emit(type="state", state="speaking")
                if prep and voice.play(prep[0], prep[1], on_audio=send_audio if len(clients) > 1 else None):
                    interrupted = True
                    break
                said = True
                emit(type="state", state="thinking")
        finally:
            stop.set()
            if interrupted:
                th.join(timeout=10)                       # üretici bir sonraki cümlede durur; yeni komutla çakışmasın
        if interrupted:
            return True
        if not said:
            say("Sorry sir, I didn't catch that." if lang["v"] == "en" else "Anlayamadım efendim, tekrar eder misiniz?")
        return False

    def on_tool(name):
        emit(type="tool", name=name)

    def think(text):
        import tools
        tools.set_user_turn(text)      # sözlü onaylar yalnızca kullanıcının kendi cümlesinden gelir
        emit(type="state", state="thinking")
        fast = None
        asked = _answering_question(text)
        if asked:      # sorulan soru geçmişte yoksa (ör. araç/mod sordu) ekle; model neye cevap verildiğini bilsin
            q = LAST_JARVIS["text"].strip()
            if not any(m.get("role") == "assistant" and q in (m.get("content") or "") for m in brain.history[-3:]):
                brain.history.append({"role": "assistant", "content": q})
        if asked and _ANSWER_RE.match(_norm_ans(text)):
            return brain.ask_stream(text, on_tool=on_tool, lang=lang["v"])     # "evet/hayır": hızlı yol değil, bağlamlı model
        try:
            fast = router.route_en(text) if lang["v"] == "en" else router.route(text)
        except Exception:
            import traceback
            traceback.print_exc()      # jarvis.log'a yazılır
            fast = None
        if fast:
            brain.history += [{"role": "user", "content": text}, {"role": "assistant", "content": fast}]
            return [fast]
        return brain.ask_stream(text, on_tool=on_tool, lang=lang["v"])

    def reminder_loop():
        import reminders, reports
        last_rapor = 0.0
        while True:
            time.sleep(3)
            try:
                if time.time() - last_rapor > 30:          # haftalık rapor yazma hatırlatıcısı
                    last_rapor = time.time()
                    if reports.due_now():
                        msg = "Efendim, rapor yazma vakti geldi. İsterseniz rapor modunu açabilirim."
                        ui("show")
                        tray.notify(msg, "Jarvis hatırlatma")
                        __import__("remote").push_note("Jarvis hatırlatma", msg)
                        emit(type="jarvis", text=msg)
                        voice.speak(msg, "tr", on_audio=send_audio if len(clients) > 1 else None)
                for r in reminders.pop_due():
                    msg = (f"Efendim, {reminders.lik(r['message'])} zamanlayıcınız doldu." if r["kind"] == "timer"
                           else "Efendim, göz molanız bitti. Çalışmaya dönebilirsiniz." if r["kind"] == "eye"
                           else "Efendim, molanız bitti. Çalışmaya dönebilirsiniz." if r["kind"] == "mola"
                           else "Efendim, odak süreniz bitti. Harika çalıştınız, kısa bir mola hak ettiniz." if r["kind"] == "odak"
                           else f"Efendim, {r['message']} hatırlatmamı istemiştiniz." if r["kind"] == "object"
                           else f"Efendim, hatırlatma zamanı: {r['message']}.")
                    ui("show")
                    tray.notify(msg, "Jarvis hatırlatma")
                    __import__("remote").push_note("Jarvis hatırlatma", msg)
                    emit(type="jarvis", text=msg)
                    voice.speak(msg, "tr", on_audio=send_audio if len(clients) > 1 else None)
            except Exception:
                import traceback
                traceback.print_exc()

    threading.Thread(target=reminder_loop, daemon=True).start()

    def eye_break() -> str:
        """Göz molası: tam ekran sayaç + bitince sesli haber. Zaten bir sayaç açıksa 5 dakika sonraya bırakır."""
        import eyecare, reminders
        if timer_win["w"] is not None:
            eyecare.snooze(300)
            return "Şu an açık bir zamanlayıcı var efendim, göz molasını beş dakika sonraya bıraktım."
        c = eyecare.cfg()
        due = reminders.add_at(c["len"] * 60, "göz molası", "eye")
        open_timer(float(c["len"]), "GÖZ MOLASI · UZAĞA BAKIN", due)
        eyecare.started_break()
        print(f"GÖZ MOLASI: başladı ({c['len']} dk)", flush=True)
        return eyecare.announce(c)

    def eye_loop():
        """Bilgisayar başında geçen süreyi 15 sn'de bir ölçer (yalnızca son girdi zamanı okunur, tuşlar kaydedilmez)."""
        import eyecare
        while True:
            time.sleep(15)
            try:
                if eyecare.tick(eyecare.idle_seconds()) == "due":
                    msg = eye_break()
                    tray.notify(msg, "Jarvis göz molası")
                    emit(type="jarvis", text=msg)
                    voice.speak(msg, "tr", on_audio=send_audio if len(clients) > 1 else None)
            except Exception:
                import traceback
                traceback.print_exc()

    import eyecare as _eyecare
    _eyecare.START_HOOK = eye_break
    threading.Thread(target=eye_loop, daemon=True).start()

    TIPS = ["Hangi şarkıyı YouTube Music'te açmamı istersiniz?",
            "Bilgisayarınızın durumunu kontrol etmemi ister misiniz?",
            "İnternette güncel bir konuyu sizin için araştırmamı ister misiniz?",
            "Yeni WhatsApp mesajlarınızı okumamı ister misiniz?",
            "Hangi uygulamayı açmamı istersiniz?",
            "Sizin için küçük bir program yazmamı ister misiniz?",
            "Ekranınıza bakıp orada ne olduğunu anlatmamı ister misiniz?",
            "Size bir hatırlatma ya da zamanlayıcı kurmamı ister misiniz?",
            "Işığınızı açıp kapatmamı ister misiniz?",
            "Sizin için bir rutin kaydetmemi ister misiniz?"]

    def greet():
        lang["v"] = "tr"
        tip = random.choice(TIPS)
        text = f"Merhaba efendim, ben Jarvis. {tip}"
        brain.history.append({"role": "assistant", "content": text})   # "evet" denince bağlam bilinsin
        say(text)

    import tools as tools_mod

    hooks["say"] = say
    hooks["voice"] = voice

    def prewarm():
        """Sık duyulan kısa cevapları açılışta sentezleyip önbelleğe alır: ilk kullanımda ses anında gelir."""
        common = ["Tamam efendim.", "Anlayamadım efendim, tekrar eder misiniz?", "Tam anlayamadım efendim, tekrar eder misiniz?",
                  "Tamam efendim, ışık açıldı.", "Tamam efendim, ışık kapatıldı.", "Sonraki şarkı efendim.", "Önceki şarkı efendim.",
                  "Sesi kapattım efendim.", "Sayacı kapattım efendim.", "Görüşürüz efendim.",
                  "Bekleyen bir hatırlatmanız yok efendim.", "Okunmamış WhatsApp mesajınız yok efendim."]
        for c in common:
            try:
                voice.prepare(c, "tr")
            except Exception:
                pass

    threading.Thread(target=prewarm, daemon=True).start()

    def session_loop():
      while True:
        emit(type="state", state="idle")
        typed = None
        if getattr(voice, "restore_muted", False):      # "Hey Jarvis" ile açılan oturum bitti: mikrofon yeniden kapalı
            voice.restore_muted = False
            mic_set(True, session=True)
        woke = voice.wait_wake(poll=lambda: not text_in.empty())
        if woke and getattr(voice, "muted", False):     # kapalı mikrofonla "Hey Jarvis": yalnızca bu oturum için dinle
            voice.restore_muted = True
            mic_set(False, session=True)
        brain.reset()
        session_end.clear()
        ui("show")
        if not woke:
            typed = text_in.get()
            greet()
        elif voice.wake_command:                      # "Jarvis, YouTube aç": selam vermeden direkt yap
            typed = voice.wake_command
            lang["v"] = voice.last_lang
        else:
            greet()
        while not session_end.is_set():
            if typed is None and not text_in.empty():
                typed = text_in.get()
            from_voice = False
            if isinstance(typed, bytes):                 # telefondan sesli komut
                from_voice = True
                emit(type="state", state="thinking")
                try:
                    heard = voice.transcribe_bytes(typed)
                except Exception:
                    import traceback
                    traceback.print_exc()
                    heard = None
                typed = None
                lang["v"] = voice.last_lang
            elif typed is not None:
                heard, typed = typed, None
                if not voice.wake_command or heard != voice.wake_command:
                    lang["v"] = guess_lang(heard)
                voice.wake_command = None
            else:
                from_voice = True
                emit(type="state", state="listening")
                heard = voice.listen(stop=lambda: session_end.is_set() or not text_in.empty())
                lang["v"] = voice.last_lang
            if not heard and voice.unclear and not session_end.is_set():
                voice.unclear = False
                say("Sorry sir, could you repeat that?" if lang["v"] == "en" else "Tam anlayamadım efendim, tekrar eder misiniz?")
                continue
            if not heard or session_end.is_set():
                continue     # sessizlikte kapanma; oturum yalnızca sizin komutunuzla ya da pencereyi kapatınca biter
            if scene_state["on"] and scene_state["kind"] == "muzik" and from_voice:
                continue                                  # müzik görselleştirici: sesli konuşma kapalı, yalnızca yazılı komut
            if (scene_state["on"] or ill_state["on"] or hero_state["on"]) and desktop_cmd(heard):
                continue                                  # 'tarayıcıyı aç' / 'masaüstüne geç': mod penceresi öne sabitlenmeden küçülür
            if scene_state["on"]:                         # sahne modu (ortam / uzay / müzik): normal Jarvis kapalı
                lang["v"] = "tr"
                tracked(scene_state["kind"] or "sahne", scene_dispatch, heard)
                heard = None
                continue
            if ill_state["on"]:                           # illüzyon modu: normal Jarvis kapalı, yalnızca illüzyon komutları
                lang["v"] = "tr"
                tracked("illüzyon", ill_dispatch, heard)
                heard = None
                continue
            if hero_state["on"]:                          # kahraman modu: normal Jarvis kapalı, yalnızca maske komutları
                lang["v"] = "tr"
                tracked("kahraman", hero_dispatch, heard)
                heard = None
                continue
            if lang["v"] == "tr" and not _answering_question(heard):
                try:
                    heard = router.snap(heard)            # Whisper'ın küçük hatalarını bilinen komutlara düzelt
                except Exception:
                    pass
            emit(type="user", text=heard)
            low = heard.replace("İ", "i").replace("I", "ı").lower()
            if tools_mod._power_pending["action"] and POWER_CANCEL.search(low):     # kapanma geri sayımında "iptal"
                tools_mod.power_cancel()
                emit(type="power", action=None)
                say("Shutdown cancelled, sir." if lang["v"] == "en" else "İptal ettim efendim, bilgisayar açık kalıyor.")
                continue
            pw = "restart" if POWER_RESTART.search(low) else "shutdown" if POWER_OFF.search(low) else None
            if pw:                                         # "sistemi kapat": 1 dk geri sayım, sesle / düğmeyle / Esc ile iptal
                res = tools_mod.power_off(pw)
                if res != "ok":
                    say("Bilgisayarı kapatamadım efendim.")
                    continue
                emit(type="power", action=pw, seconds=tools_mod.POWER_DELAY)
                if lang["v"] == "en":
                    say(f"{'Restarting' if pw == 'restart' else 'Shutting down'} in one minute, sir. Say cancel to abort.")
                else:
                    say(f"Bilgisayarı bir dakika içinde {'yeniden başlatıyorum' if pw == 'restart' else 'kapatıyorum'} efendim. "
                        "Vazgeçerseniz iptal deyin.")
                continue
            if any(w in low for w in GOODBYE):
                say("Goodbye, sir." if lang["v"] == "en" else "Görüşürüz efendim.")     # model "emin misiniz" diye sormasın; direkt kapan
                break
            if any(w in low for w in WIPE_ALL):          # sohbet + kalıcı hafıza
                import memory, tools
                memory._save([])
                brain.reset(); tools._pending.clear(); tools.LAST_USER = ""
                emit(type="clear")
                wipe_traces()
                voice.clear_cache()
                say("Sohbet geçmişini, hafızamı, ses kayıtlarını ve günlükleri sildim efendim. Sistem sıfırdan başlatıldı.")
                continue
            if any(w in low for w in RESET):             # "geçmişi sil": yeniden başlatma
                import tools
                brain.reset(); tools._pending.clear()
                emit(type="clear")
                say("Clearing history. Systems rebooted, sir." if lang["v"] == "en"
                    else "Sohbet geçmişini sildim efendim, sistem yeniden başlatıldı.")
                continue
            if "jarvis" in low:
                ui("show")                    # küçültülmüşse geri getir
            try:
                say_all(think(heard))
            except Exception as e:
                import traceback
                traceback.print_exc()
                say(f"Bir hata oluştu efendim: {str(e)[:120]}")
        ui("hide")

    while True:      # bir hata oturumu öldürmesin: logla ve yeniden dinlemeye başla
        try:
            session_loop()
        except Exception:
            import traceback
            traceback.print_exc()
            emit(type="state", state="idle")
            time.sleep(2)


if __name__ == "__main__":
    import socket
    # HUD penceresi (yalnızca Jarvis'in WebView2'si) ekran kartı belleği yerine işlemciyle çizilsin: Whisper + dil modeli kartı
    # doldurduğunda pencerenin siyah kalmasını / takılmasını önler. WhatsApp ve Edge etkilenmez (ortam değişkeni bu sürece özel).
    os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--disable-gpu --disable-gpu-compositing --disable-features=CalculateNativeWinOcclusion"
    import webview
    with socket.socket() as _s:
        if _s.connect_ex(("127.0.0.1", PORT)) == 0:
            # Jarvis zaten çalışıyor: yeni kopya açma, çalışan pencereyi öne getir
            import ctypes
            h = ctypes.windll.user32.FindWindowW(None, "JARVIS")
            if h:
                from tools import bring_to_front
                ctypes.windll.user32.ShowWindow(h, 9)
                bring_to_front(h)
            sys.exit(0)
    import phone
    phone.URL = f"{ALLOWED_ORIGIN}/?t={TOKEN}"
    phone.MIRROR_URL = f"{ALLOWED_ORIGIN}/mirror?t={TOKEN}"
    import mirror

    def _mirror_changed(n: int):
        """Telefona yayın başladı/bitti: ekranınız yayınlanıyorsa bunu her zaman haber verir (sessizce yayın olmaz)."""
        msg = "Ekranınız telefona yansıtılıyor." if n else "Ekran yansıtma bitti."
        emit(type="mirror", n=n)
        emit(type="jarvis", text=msg)
        try:
            tray.notify(msg, "Jarvis")
        except Exception:
            pass
        print(f"YANSITMA: {n} telefon bağlı", flush=True)
    mirror.state["on_change"] = _mirror_changed
    import lan

    def _lan_pair_code(code: str):
        """Bir telefon kablosuz eşleşmek istedi: kod YALNIZCA burada (HUD + bildirim) görünür; telefona yazılması gerekir."""
        ui("show")
        emit(type="jarvis", text=f"Telefon eşleşmek istiyor. Eşleşme kodu: {code}")
        try:
            tray.notify(f"Telefon eşleşme kodu: {code}", "Jarvis")
        except Exception:
            pass
        if hooks["say"]:
            threading.Thread(target=hooks["say"], args=("Bir telefon eşleşmek istiyor efendim, kodu ekranda görebilirsiniz.",), daemon=True).start()
    lan.HOOKS.update(text=lambda t: text_in.put(t), mic_toggle=lambda: mic_set(not getattr(VOICE, "muted", False)),
                     open_guide=lambda: threading.Thread(target=open_guide, daemon=True).start(), pair_code=_lan_pair_code)
    threading.Thread(target=stats_loop, daemon=True).start()
    threading.Thread(target=_hotkey_thread, daemon=True).start()
    threading.Thread(target=music_loop, daemon=True).start()
    tray = start_tray()
    threading.Thread(target=uvicorn.run, args=(app,), kwargs=dict(host="127.0.0.1", port=PORT, log_level="warning"),
                     daemon=True).start()
    time.sleep(1.5)
    window = webview.create_window("JARVIS", f"{ALLOWED_ORIGIN}/?t={TOKEN}", width=1100, height=760,
                                   background_color="#02060c", text_select=False, hidden=True)   # başlangıçta ekrana çıkmasın

    def on_closing():
        ui("hide")           # X'e basınca kapanmasın, tepsiye insin
        session_end.set()    # ve oturum bitsin: bir sonraki "hey Jarvis" pencereyi yeniden açar
        return False

    import tools
    import jbrowser, vpn
    jbrowser.FOCUS = focus_window
    tools.BROWSER_HOOK = jbrowser.open_url
    vpn.ON_CHANGE = _vpn_changed

    def _vpn_auto():
        time.sleep(15)
        try:
            cfg = vpn.load()
            if cfg.get("auto") and cfg.get("active"):
                vpn.connect(cfg["active"])
        except Exception as e:
            print("VPN otomatik bağlanma hatası:", type(e).__name__, flush=True)
    threading.Thread(target=_vpn_auto, daemon=True).start()
    try:
        import usage
        usage.start()                                # bilgisayar kullanım süresi (panel modu): yalnızca yerel usage.json
        import pano
        pano.start()                                 # pano geçmişi (yalnızca RAM); config.json: pano_izle ile kapatılır
    except Exception as e:
        print("kullanım süresi başlatılamadı:", type(e).__name__, flush=True)
    tools.TIMER_HOOK = open_timer
    tools.CODE_HOOK = open_code_editor
    tools.GUIDE_HOOK = open_guide
    tools.MIC_HOOK = mic_set
    tools.TIMER_STOP = stop_timer
    tools.HERO_HOOK = open_hero
    tools.ILL_HOOK = open_illusion
    tools.SCENE_HOOK = open_scene
    tools.MEBI_HOOK = mebi_cmd
    tools.MOLA_HOOK = mola_cmd
    tools.REMOTE_HOOK = remote_cmd
    import remote

    def _remote_code(code: str):
        """Uzaktan eşleşmek isteyen telefonun kodu YALNIZCA burada (HUD + bildirim) görünür."""
        ui("show")
        try:
            import scenes_telefon
            scenes_telefon.S["code"] = code
            if scene_state["on"] and scene_state["kind"] == "telefon":
                emit(type="scene_do", kind="telefon", do={"data": scenes_telefon.view()})      # kod telefon modunun ekranında büyük gösterilir
        except Exception:
            pass
        emit(type="jarvis", text=f"Uzaktan telefon eşleşmek istiyor. Eşleşme kodu: {code}")
        try:
            tray.notify(f"Uzaktan eşleşme kodu: {code}", "Jarvis")
        except Exception:
            pass
        if hooks["say"]:
            threading.Thread(target=hooks["say"], args=("Bir telefon uzaktan eşleşmek istiyor efendim, kodu ekranda görebilirsiniz.",), daemon=True).start()
    import remote_auto
    import remote as _remote_mod
    _remote_mod.MAIN.update(attach=remote_attach, detach=remote_detach, ws=remote_ws)
    _remote_mod.FULL.update(text=lambda t: text_in.put(t), mic_toggle=lambda: mic_set(not getattr(VOICE, "muted", False)),
                            open_guide=lambda: threading.Thread(target=open_guide, daemon=True).start(), open=remote_open)

    def _ts_watch():
        """Tailscale erişimi açıksa (uzak_tailscale) Jarvis açıldıktan sonra dinleyiciyi başlatır; Tailscale geç açılırsa 30 sn'de bir yeniden dener."""
        import settings
        time.sleep(20)
        while True:
            try:
                if settings.get("uzak_tailscale") and not remote.TS["on"]:
                    if remote.ts_start() == "ok" and not remote.paired_count():
                        remote.arm_pair()
            except Exception as e:
                print("Tailscale izleme hatası:", type(e).__name__, flush=True)
            time.sleep(30)
    threading.Thread(target=_ts_watch, daemon=True).start()
    import nasil
    nasil.NOTIFY = lambda do, say="": (emit(type="scene_do", kind="nasil", do=do),
                                       say and scene_state["on"] and scene_state["kind"] == "nasil" and hooks["say"] and threading.Thread(target=hooks["say"], args=(say,), daemon=True).start())
    import sohbet
    sohbet.ACTIVE = lambda kind="sohbet": _scene_on(kind)                  # PC penceresi ya da bağlı telefon
    sohbet.NOTIFY = lambda kind, do: sohbet.ACTIVE(kind) and emit(type="scene_do", kind=kind, do=do)
    sohbet.SAY = lambda s, cont=False: bool(hooks["say"] and scene_state["on"] and scene_state["kind"] in ("sohbet", "ultron", "friday", "luna") and hooks["say"](s, cont))   # yalnızca telefondan konuşulurken PC konuşmaz
    import scenes, scenes_yeni
    import scenes_gunluk, pano
    import scenes_stark
    scenes_stark.NOTIFY = lambda kind, do: _scene_on(kind) and emit(type="scene_do", kind=kind, do=do)
    scenes_stark.SAY = lambda s, kind: bool(hooks["say"] and scene_state["on"] and scene_state["kind"] == kind and threading.Thread(target=hooks["say"], args=(s,), daemon=True).start())
    scenes_stark.HOOK = lambda: {"clients": len(clients), "mic_muted": (bool(getattr(VOICE, "muted", False)) if VOICE is not None else None),
                                 "persona": (__import__("voice").PERSONA.get("name") if VOICE is not None else None), "scene": scene_state["kind"]}
    scenes_gunluk.NOTIFY = lambda kind, do: _scene_on(kind) and emit(type="scene_do", kind=kind, do=do)
    scenes_gunluk.SAY = lambda s, kind: bool(hooks["say"] and scene_state["on"] and scene_state["kind"] == kind and threading.Thread(target=hooks["say"], args=(s,), daemon=True).start())
    pano.ON_CHANGE = lambda: _scene_on("pano") and emit(type="scene_do", kind="pano", do={"snap": scenes_gunluk.pano_snap()})
    import scenes_elektronik                                                  # blok kurucu: Ollama sonucu ayrı iş parçacığından sayfaya/sese gider
    scenes_elektronik.NOTIFY = lambda kind, do: _scene_on(kind) and emit(type="scene_do", kind=kind, do=do)
    scenes_elektronik.SAY = lambda s, kind: bool(hooks["say"] and scene_state["on"] and scene_state["kind"] == kind and threading.Thread(target=hooks["say"], args=(s,), daemon=True).start())
    import scenes_ekitap
    scenes_ekitap.NOTIFY = lambda kind, do: _scene_on(kind) and emit(type="scene_do", kind=kind, do=do)
    import scenes_yaratici
    scenes_yaratici.NOTIFY = lambda kind, do: _scene_on(kind) and emit(type="scene_do", kind=kind, do=do)
    scenes_yaratici.SAY = lambda s, kind: bool(hooks["say"] and scene_state["on"] and scene_state["kind"] == kind and threading.Thread(target=hooks["say"], args=(s,), daemon=True).start())
    scenes_yeni.SAY = lambda s: bool(hooks["say"] and scene_state["on"] and scene_state["kind"] == "cark" and hooks["say"](s))   # çark sonucu animasyon bitince söylenir
    import ultron_learn
    ultron_learn.NOTIFY = lambda name, do: sohbet.ACTIVE(name) and emit(type="scene_do", kind=name, do=do)
    ultron_learn.BUSY = lambda: bool(sohbet.S["busy"] or __import__("ultron").CHAT.S["busy"] or __import__("friday").busy() or __import__("luna").CHAT.S["busy"]
                                     or (scene_state["on"] and scene_state["kind"] in ("ders", "satranc")))
    ultron_learn.CTX = lambda: (int(__import__("settings").get("sohbet_ctx") or 8192) if any(_scene_on(k) for k in ("sohbet", "ultron", "friday", "luna"))
                                else __import__("brain").CTX)
    ultron_learn.ULTRON.start()
    ultron_learn.FRIDAY.start()
    ultron_learn.LUNA.start()
    import yemek
    yemek.NOTIFY = lambda do, say="": (emit(type="scene_do", kind="yemek", do=do),
                                       say and scene_state["on"] and scene_state["kind"] == "yemek" and hooks["say"] and threading.Thread(target=hooks["say"], args=(say,), daemon=True).start())
    import tarif
    tarif.NOTIFY = lambda do, say="": (emit(type="scene_do", kind="tarif", do={**do, "msg": say}),
                                       say and scene_state["on"] and scene_state["kind"] == "tarif" and hooks["say"] and threading.Thread(target=hooks["say"], args=(say,), daemon=True).start())
    remote_auto.HOOKS.update(say=lambda m: hooks["say"] and threading.Thread(target=hooks["say"], args=(m,), daemon=True).start(), notify=lambda u: _remote_show())
    if remote_auto.enabled():
        threading.Thread(target=lambda: (time.sleep(25), remote_auto.start_loop()), daemon=True).start()          # açılıştan sonra otomatik uzaktan erişim
    remote.HOOKS.update(pair_code=_remote_code, closed=lambda: hooks["say"] and threading.Thread(target=hooks["say"], args=("Uzaktan erişim süresi doldu ve kapandı efendim.",), daemon=True).start())
    window.events.closing += on_closing
    import mebi
    os.makedirs(mebi.PROFILE, exist_ok=True)       # MEBİ oturumu (öğrencinin girişi) yeniden açılışta kalsın; tüm pencereler aynı WebView2 profilini kullanır
    webview.start(lambda: threading.Thread(target=run_assistant, daemon=True).start(), private_mode=False, storage_path=mebi.PROFILE)
