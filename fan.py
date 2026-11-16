"""Arduino'ya bağlı fanı seri port üzerinden kontrol eder (arduino/fan/fan.ino)."""
import threading, time
import serial
from serial.tools import list_ports

BAUD = 9600
_lock = threading.Lock()
_ser = None
_speed = 0


def _find_port():
    """CH340 / Arduino görünen ilk portu bulur."""
    for p in list_ports.comports():
        d = f"{p.description} {p.manufacturer or ''}".lower()
        if any(k in d for k in ("ch340", "arduino", "usb-serial", "wch")):
            return p.device
    return None


def _open():
    global _ser
    if _ser and _ser.is_open:
        return _ser
    port = _find_port()
    if not port:
        raise RuntimeError("Arduino kartı bulunamadı")
    _ser = serial.Serial(port, BAUD, timeout=1, write_timeout=1)
    time.sleep(2.0)                      # port açılınca kart resetlenir, açılmasını bekle
    _ser.reset_input_buffer()
    return _ser


def _send(cmd: str) -> str:
    global _ser
    with _lock:
        try:
            s = _open()
            s.write((cmd + "\n").encode("ascii"))
            return s.readline().decode("ascii", "ignore").strip()
        except (serial.SerialException, OSError, RuntimeError):
            try:
                if _ser:
                    _ser.close()
            except Exception:
                pass
            _ser = None
            raise


def set_speed(pct: int) -> int:
    """Fan hızını 0-100 yüzde olarak ayarlar; ayarlanan hızı döndürür."""
    global _speed
    pct = max(0, min(100, int(pct)))
    reply = _send(f"S{pct}")
    if not reply.startswith("OK"):
        raise RuntimeError("Kart cevap vermedi")
    _speed = pct
    return pct


def speed() -> int:
    return _speed


def stop_quietly():
    """Jarvis kapanırken fanı durdurmayı dener."""
    try:
        if _ser and _ser.is_open:
            set_speed(0)
    except Exception:
        pass
