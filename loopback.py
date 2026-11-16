"""Müzik görselleştirici için sistem sesi dinleyicisi (WASAPI loopback): tarayıcıda (YouTube Music vb.) çalan her ses 32 frekans bandına
çevrilip callback'e verilir. Ses kaydedilmez, saklanmaz, yalnızca anlık band değerleri geçer. Hoparlör değişirse kendini yeniler."""
import threading, time

import numpy as np

BANDS = 32
_stop = threading.Event()
_thread = None
status = {"ok": False}


def _run(cb, stop: threading.Event):
    import pyaudiowpatch as pa
    edges = np.geomspace(50, 12000, BANDS + 1)
    while not stop.is_set():
        p = None
        stream = None
        try:
            p = pa.PyAudio()
            dev = p.get_default_wasapi_loopback()
            rate = int(dev["defaultSampleRate"])
            ch = int(dev["maxInputChannels"]) or 2
            n = 2048
            win = np.hanning(n)
            freqs = np.fft.rfftfreq(n, 1 / rate)
            masks = [(freqs >= edges[i]) & (freqs < edges[i + 1]) for i in range(BANDS)]
            stream = p.open(format=pa.paInt16, channels=ch, rate=rate, input=True, input_device_index=dev["index"], frames_per_buffer=n)
            status["ok"] = True
            last_name = dev["name"]
            tick = 0
            while not stop.is_set():
                data = stream.read(n, exception_on_overflow=False)
                x = np.frombuffer(data, dtype=np.int16).reshape(-1, ch).mean(axis=1) / 32768.0
                if len(x) < n:
                    continue
                spec = np.abs(np.fft.rfft(x * win)) / n
                out = []
                for m in masks:
                    val = float(spec[m].max()) if m.any() else 0.0
                    out.append(int(max(0, min(255, np.log10(1 + val * 120) * 150))))
                cb(out)
                tick += 1
                if tick % 120 == 0:                    # ~5 sn'de bir: varsayılan hoparlör değiştiyse yeniden bağlan
                    try:
                        if p.get_default_wasapi_loopback()["name"] != last_name:
                            break
                    except Exception:
                        break
        except Exception as e:
            status["ok"] = False
            print("loopback hatası:", e, flush=True)
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
    status["ok"] = False


def start(cb) -> bool:
    """Dinlemeyi başlatır; kütüphane/aygıt yoksa False döner."""
    global _thread, _stop
    stop()
    try:
        import pyaudiowpatch  # noqa: F401
    except Exception as e:
        print("loopback yok:", e, flush=True)
        return False
    _stop = threading.Event()
    _thread = threading.Thread(target=_run, args=(cb, _stop), daemon=True)
    _thread.start()
    return True


def stop() -> None:
    _stop.set()
