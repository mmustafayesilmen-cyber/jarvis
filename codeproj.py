"""Kod yazma ekranının yardımcıları: projeyi çalıştırma/durdurma ve proje klasörünü yeniden adlandırma."""
import os, re, shutil, subprocess, sys, threading, time

RUN_TIMEOUT = 120          # sn; süre dolunca program durdurulur
MAX_OUT = 200_000          # karakter; fazlası kesilir
_state = {"p": None}
_lock = threading.Lock()


def find_python():
    """Kullanıcının kendi Python'u (Jarvis'in venv'i değil: orada kullanıcının paketleri yok)."""
    cands = [shutil.which("python"), os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python312", "python.exe")]
    for c in cands:
        if c and os.path.exists(c) and ".venv" not in c.lower() and "jarvis" not in c.lower():
            return c
    return None


def is_running() -> bool:
    p = _state["p"]
    return p is not None and p.poll() is None


def run(project_dir: str, send, on_start=None, on_end=None) -> str:
    """main.py'yi çalıştırır. send(dict) çıktıyı ekrana iter. Dönen metin boşsa başladı, doluysa hata."""
    with _lock:
        if is_running():
            return "Program zaten çalışıyor."
        py = find_python()
        if not py:
            return "Python bulunamadı."
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        p = subprocess.Popen([py, "-u", "main.py"], cwd=project_dir, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, env=env, creationflags=0x08000000)
        _state["p"] = p
    if on_start:
        on_start()
    timed_out = {"v": False}

    def watchdog():
        t0 = time.time()
        while p.poll() is None:
            if time.time() - t0 > RUN_TIMEOUT:
                timed_out["v"] = True
                kill()
                return
            time.sleep(0.5)

    def pump():
        sent = 0
        try:
            for raw in iter(p.stdout.readline, b""):
                txt = raw.decode("utf-8", errors="replace")
                sent += len(txt)
                if sent <= MAX_OUT:
                    send({"type": "code_out", "text": txt})
                elif sent - len(txt) <= MAX_OUT:
                    send({"type": "code_out", "text": "… çıktı çok uzun, kesildi …" + chr(10), "err": True})
        finally:
            code = p.wait()
            if on_end:
                on_end()
            send({"type": "code_done", "code": code, "timeout": timed_out["v"]})

    threading.Thread(target=watchdog, daemon=True).start()
    threading.Thread(target=pump, daemon=True).start()
    return ""


def kill() -> bool:
    p = _state["p"]
    if p is None or p.poll() is not None:
        return False
    subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True, creationflags=0x08000000)
    return True


def clean_name(name: str) -> str:
    n = re.sub(r"[^\w\- ]", "", (name or "").strip(), flags=re.UNICODE)
    n = re.sub(r"\s+", "_", n).strip("_-")[:40]
    return n


def rename_project(d: str, name: str, root: str):
    """(yeni_klasör, not). Önce yeniden adlandırmayı dener; VS Code klasörü kilitliyorsa kopyalayıp eskisini silmeye çalışır."""
    n = clean_name(name)
    if not n:
        return d, ""
    new = os.path.join(root, n)
    k = 2
    while os.path.exists(new):
        new = os.path.join(root, f"{n}_{k}")
        k += 1
    if os.path.abspath(os.path.dirname(d)) != os.path.abspath(root):
        return d, ""
    try:
        os.rename(d, new)
        return new, "renamed"
    except OSError:
        shutil.copytree(d, new)
        shutil.rmtree(d, ignore_errors=True)
        return new, "copied" if not os.path.exists(d) else "copied_old_kept"
