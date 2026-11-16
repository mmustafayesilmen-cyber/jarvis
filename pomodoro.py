"""Pomodoro modu çekirdeği: çalışma / kısa mola / uzun mola döngüsü. Süreler ayarlanabilir (pomodoro.json'da saklanır).
Durum yalnızca bellekte tutulur (mod kapanınca sıfırlanır); kalıcı olan yalnızca ayarlar ve günlük tamamlanan tur sayısı.
Zaman kaynağı now() testlerde değiştirilebilir; gerçek ses/ışık/müzik burada yok, onları main.py ve scenes_pomodoro.py yönetir."""
import json
import os
import threading
import time

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro.json")
DEFAULTS = {"work": 25, "short": 5, "long": 15, "rounds": 4, "auto": True, "music": False, "songs": []}
MAX_SONGS = 30
LIMITS = {"work": (1, 600), "short": (1, 240), "long": (1, 480), "rounds": (2, 20)}
NAMES = {"work": "Çalışma", "short": "Kısa mola", "long": "Uzun mola"}

now = time.time          # testlerde değiştirilir
_lock = threading.RLock()
cfg = dict(DEFAULTS)
S = {}


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.localtime(now()))


def _load_file() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


HIST_DAYS = 400
HIST = {}                # {"YYYY-MM-DD": {"done": tur, "work_s": saniye}} — gelişim paneli okur


def _save() -> None:
    if S["done_today"] or S["work_s_today"]:
        HIST[S["day"]] = {"done": S["done_today"], "work_s": int(S["work_s_today"])}
    for k in sorted(HIST)[:-HIST_DAYS]:
        HIST.pop(k, None)
    data = {"settings": cfg, "stats": {"day": S["day"], "done": S["done_today"], "work_s": int(S["work_s_today"])}, "history": HIST}
    tmp = PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, PATH)
    except OSError:
        pass


def reset() -> None:
    """Oturumu sıfırlar, ayarları ve bugünün sayacını dosyadan yükler."""
    global cfg
    with _lock:
        d = _load_file()
        cfg = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULTS.items()}
        for k, v in (d.get("settings") or {}).items():
            if k in DEFAULTS and type(v) is type(DEFAULTS[k]):
                if k in LIMITS:
                    v = max(LIMITS[k][0], min(LIMITS[k][1], v))
                cfg[k] = v
        st = d.get("stats") or {}
        same = st.get("day") == _today()
        HIST.clear()
        for k, v in (d.get("history") or {}).items():
            if isinstance(k, str) and len(k) == 10 and isinstance(v, dict):
                HIST[k] = {"done": int(v.get("done", 0) or 0), "work_s": int(v.get("work_s", 0) or 0)}
        if st.get("day") and (st.get("done") or st.get("work_s")) and st["day"] not in HIST:      # geçmiş kaydından önceki son gün
            HIST[st["day"]] = {"done": int(st.get("done", 0)), "work_s": int(st.get("work_s", 0))}
        S.clear()
        S.update(phase="idle", paused=False, end=0.0, left=0.0, total=0.0, round=1, session_done=0, started=0.0,
                 day=_today(), done_today=int(st.get("done", 0)) if same else 0, work_s_today=float(st.get("work_s", 0)) if same else 0.0)


reset()


def set_cfg(key: str, value):
    """Ayarı sınırlar içinde kaydeder. (kaydedilen değer, sınıra takıldı mı) döner."""
    with _lock:
        clipped = False
        if key in LIMITS:
            lo, hi = LIMITS[key]
            nv = max(lo, min(hi, int(value)))
            clipped = nv != int(value)
            value = nv
        cfg[key] = value
        # çalışan evrenin süresine dokunulmaz; yeni süre bir sonraki evreden itibaren geçerlidir. Beklemedeki (başlamamış) evre güncellenir.
        if S["phase"] in ("work", "short", "long") and S["paused"] and S["left"] == S["total"] and key in ("work", "short", "long") and key == S["phase"]:
            S["left"] = S["total"] = cfg[key] * 60.0
        _save()
        return value, clipped


def _clean_song(q: str) -> str:
    return " ".join("".join(ch for ch in str(q) if ch.isprintable()).split())[:80]


def add_song(q: str) -> bool:
    """Çalışma müziği listesine şarkı adı (YouTube araması için) ekler. Boş ya da tekrar eden eklenmez."""
    q = _clean_song(q)
    with _lock:
        if not q or q.lower() in (x.lower() for x in cfg["songs"]) or len(cfg["songs"]) >= MAX_SONGS:
            return False
        cfg["songs"].append(q)
        _save()
        return True


def remove_song(i: int):
    """1'den başlayan sıra numarasıyla şarkıyı listeden çıkarır; çıkarılanın adını döner."""
    with _lock:
        if not 1 <= i <= len(cfg["songs"]):
            return None
        name = cfg["songs"].pop(i - 1)
        _save()
        return name


def clear_songs() -> int:
    with _lock:
        n = len(cfg["songs"])
        cfg["songs"].clear()
        _save()
        return n


def _enter(phase: str, run: bool) -> None:
    secs = cfg[phase] * 60.0
    S.update(phase=phase, total=secs, left=secs, paused=not run, end=now() + secs if run else 0.0, started=now())


def start() -> str:
    """Boştaysa çalışma evresini başlatır; duraklatılmışsa sürdürür. Döner: 'started' | 'resumed' | 'running'."""
    with _lock:
        if S["phase"] == "idle":
            S["round"] = 1
            _enter("work", True)
            return "started"
        if S["paused"]:
            S["paused"] = False
            S["end"] = now() + S["left"]
            return "resumed"
        return "running"


def pause() -> bool:
    with _lock:
        if S["phase"] == "idle" or S["paused"]:
            return False
        S["left"] = max(0.0, S["end"] - now())
        S["paused"] = True
        return True


def stop() -> bool:
    """Oturumu bitirir (ayarlar ve günlük sayaç kalır)."""
    with _lock:
        was = S["phase"] != "idle"
        S.update(phase="idle", paused=False, end=0.0, left=0.0, total=0.0, round=1, session_done=0)
        return was


def extend(minutes: int) -> bool:
    """Geçerli evreye dakika ekler (negatifse çıkarır; en az 1 dakika kalır)."""
    with _lock:
        if S["phase"] == "idle":
            return False
        left = (S["left"] if S["paused"] else max(0.0, S["end"] - now())) + minutes * 60.0
        left = max(60.0, left)
        S["left"] = left
        S["total"] = max(S["total"], left)
        if not S["paused"]:
            S["end"] = now() + left
        return True


def _next_phase(counted: bool) -> str:
    if S["phase"] == "work":
        return "long" if counted and S["session_done"] % cfg["rounds"] == 0 else "short"
    return "work"


def skip() -> dict:
    """Geçerli evreyi atlar: çalışma atlanırsa tur sayılmaz, mola atlanırsa doğrudan çalışmaya geçilir."""
    with _lock:
        if S["phase"] == "idle":
            return {}
        return _finish(counted=False)


def _finish(counted: bool) -> dict:
    prev = S["phase"]
    if S["day"] != _today():                         # gece yarısını geçen oturum: yeni günün sayacı sıfırdan başlar
        S.update(day=_today(), done_today=0, work_s_today=0.0)
    if prev == "work":
        if counted:
            S["session_done"] += 1
            S["done_today"] += 1
            S["work_s_today"] += S["total"]
        else:                                        # atlanan çalışmada geçen süre kadarı sayılır
            S["work_s_today"] += max(0.0, S["total"] - (S["left"] if S["paused"] else max(0.0, S["end"] - now())))
        nxt = _next_phase(counted)
    else:
        nxt = "work"
        if prev == "long":
            S["round"] = 1
        else:
            S["round"] = min(S["round"] + 1, cfg["rounds"])
    run = cfg["auto"] if counted else True
    _enter(nxt, run)
    _save()
    return {"from": prev, "to": nxt, "counted": counted, "auto": run, "done_today": S["done_today"], "session_done": S["session_done"]}


def tick():
    """Saniyede bir çağrılır. Evre bittiyse geçiş olayını döner, yoksa None."""
    with _lock:
        if S["phase"] == "idle" or S["paused"]:
            return None
        if S["end"] - now() <= 0:
            return _finish(counted=True)
        return None


def snapshot() -> dict:
    with _lock:
        left = S["left"] if S["paused"] or S["phase"] == "idle" else max(0.0, S["end"] - now())
        waiting = S["phase"] != "idle" and S["paused"] and S["left"] == S["total"]
        return {"phase": S["phase"], "name": NAMES.get(S["phase"], "Hazır"), "paused": S["paused"], "waiting": waiting, "left": int(round(left)),
                "total": int(S["total"]), "round": S["round"], "rounds": cfg["rounds"], "session_done": S["session_done"],
                "done_today": S["done_today"], "work_min_today": int(S["work_s_today"] // 60), "cfg": dict(cfg)}


def mmss(sec: int) -> str:
    m, s = divmod(max(0, int(sec)), 60)
    return f"{m} dakika {s} saniye" if m else f"{s} saniye"
