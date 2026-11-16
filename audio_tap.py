"""Telefon tarayıcısı için bilgisayarın sesini telefona aktarma (WASAPI loopback): varsayılan hoparlöre giden karışım 22,05 kHz mono 16-bit PCM'e çevrilir ve abonelere (bağlı telefon) verilir.
Windows 10 bu sürümde yalnızca uygulama başına değil tüm karışımı yakalar: tarayıcının sesiyle birlikte Jarvis'in konuşması/müzik de gider. Ses kaydedilmez ya da saklanmaz, yalnızca anlık aktarılır;
yalnızca en az bir telefon 'SES'i açtıysa dinleme açıktır, son telefon ayrılınca kapanır. Sessiz parçalar gönderilmez (veri tasarrufu)."""
import math
import threading
import time

import numpy as np

OUT_RATE = 22050
_subs = []
_lock = threading.Lock()
_stop = threading.Event()
_thread = None


def _run(stop: threading.Event):
    import pyaudiowpatch as pa
    from scipy.signal import resample_poly
    while not stop.is_set():
        p = stream = None
        try:
            p = pa.PyAudio()
            dev = p.get_default_wasapi_loopback()
            rate = int(dev["defaultSampleRate"])
            ch = int(dev["maxInputChannels"]) or 2
            g = math.gcd(OUT_RATE, rate)
            up, down = OUT_RATE // g, rate // g
            n = 2048
            stream = p.open(format=pa.paInt16, channels=ch, rate=rate, input=True, input_device_index=dev["index"], frames_per_buffer=n)
            last, quiet, tick = dev["name"], 0, 0
            while not stop.is_set():
                data = stream.read(n, exception_on_overflow=False)
                x = np.frombuffer(data, dtype=np.int16).reshape(-1, ch).astype(np.float32).mean(axis=1)
                if np.abs(x).max() < 20:
                    quiet += 1
                    if quiet > 12:                                  # yaklaşık yarım saniyeden uzun sessizlik: gönderme
                        continue
                else:
                    quiet = 0
                y = resample_poly(x, up, down) if (up, down) != (1, 1) else x
                pcm = np.clip(y, -32768, 32767).astype("<i2").tobytes()
                with _lock:
                    subs = list(_subs)
                for cb in subs:
                    try:
                        cb(pcm)
                    except Exception:
                        pass
                tick += 1
                if tick % 120 == 0:
                    try:
                        if p.get_default_wasapi_loopback()["name"] != last:
                            break                                   # varsayılan hoparlör değişti: yeniden bağlan
                    except Exception:
                        break
        except Exception as e:
            print("ses aktarma hatası:", type(e).__name__, flush=True)
            stop.wait(2)
        finally:
            try:
                if stream is not None:
                    stream.stop_stream()
                    stream.close()
            except Exception:
                pass
            try:
                if p is not None:
                    p.terminate()
            except Exception:
                pass


def subscribe(cb) -> bool:
    """cb(bytes) çağrılır. İlk abone dinlemeyi başlatır. Kütüphane yoksa False."""
    global _thread, _stop
    try:
        import pyaudiowpatch  # noqa: F401
    except Exception:
        return False
    with _lock:
        _subs.append(cb)
        if _thread is None or not _thread.is_alive():
            _stop = threading.Event()
            _thread = threading.Thread(target=_run, args=(_stop,), daemon=True)
            _thread.start()
    return True


def unsubscribe(cb) -> None:
    with _lock:
        if cb in _subs:
            _subs.remove(cb)
        if not _subs:
            _stop.set()


def stop_all() -> None:
    with _lock:
        _subs.clear()
    _stop.set()
