"""Sistem analizi modu için gerçek ölçümler. Hiçbir değer uydurulmaz: ölçülemeyen şey (CPU / SSD sıcaklığı gibi) None döner ve arayüzde "ölçülemiyor" yazar.
Kaynaklar: psutil (CPU/RAM/disk/ağ/süreç), Windows PDH sayaçları (İngilizce adlarla, dilden bağımsız: etkin CPU frekansı, disk meşguliyeti ve gecikmesi,
işlemci kuyruğu, sayfa hatası), nvidia-smi (GPU), WMI/PowerShell (yalnızca bir kez, donanım bilgisi). Her şey bu bilgisayarda kalır; ağa hiçbir istek gitmez."""
import collections
import ctypes
import json
import os
import platform
import subprocess
import threading
import time

import psutil

NO_WINDOW = 0x08000000
_lock = threading.Lock()


# ------------------------------------------------------------------ Windows PDH sayaçları
class _Val(ctypes.Structure):
    _fields_ = [("CStatus", ctypes.c_ulong), ("doubleValue", ctypes.c_double)]


class _Pdh:
    PATHS = {
        "perf": r"\Processor Information(_Total)\% Processor Performance",
        "disk_busy": r"\PhysicalDisk(_Total)\% Disk Time",
        "disk_lat": r"\PhysicalDisk(_Total)\Avg. Disk sec/Transfer",
        "disk_q": r"\PhysicalDisk(_Total)\Current Disk Queue Length",
        "cpu_q": r"\System\Processor Queue Length",
        "pages": r"\Memory\Pages/sec",
    }

    def __init__(self):
        self.q = ctypes.c_void_p()
        self.h = {}
        self.ok = False
        try:
            self.d = ctypes.WinDLL("pdh")
            if self.d.PdhOpenQueryW(None, 0, ctypes.byref(self.q)) != 0:
                return
            for k, p in self.PATHS.items():
                c = ctypes.c_void_p()
                if self.d.PdhAddEnglishCounterW(self.q, p, 0, ctypes.byref(c)) == 0:
                    self.h[k] = c
            self.ok = bool(self.h)
            self.d.PdhCollectQueryData(self.q)
        except Exception:
            self.ok = False

    def read(self) -> dict:
        out = {}
        if not self.ok:
            return out
        try:
            self.d.PdhCollectQueryData(self.q)
            for k, c in self.h.items():
                v = _Val()
                if self.d.PdhGetFormattedCounterValue(c, 0x200, None, ctypes.byref(v)) == 0 and v.CStatus in (0, 1):
                    out[k] = v.doubleValue
        except Exception:
            pass
        return out

    def close(self):
        try:
            if self.ok:
                self.d.PdhCloseQuery(self.q)
        except Exception:
            pass
        self.ok = False


# ------------------------------------------------------------------ nvidia-smi akışı
GPU_FIELDS = ("temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,power.limit,clocks.sm,clocks.max.sm,clocks.mem,"
              "clocks.max.mem,fan.speed,pstate,utilization.encoder,utilization.decoder,clocks_throttle_reasons.active")
THROTTLE = [(0x04, "güç sınırı"), (0x08, "donanım yavaşlatması"), (0x20, "ısı yavaşlatması"), (0x40, "donanım ısı yavaşlatması"), (0x80, "güç freni")]


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


class _Gpu:
    """nvidia-smi'yi saniyede bir kısa süreli çalıştırır (sürekli çalışan alt süreç bırakmaz; Jarvis aniden kapansa bile artık süreç kalmaz)."""

    def __init__(self):
        self.data = None
        self.t = 0.0
        self.alive = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self.alive:
            t0 = time.time()
            try:
                r = subprocess.run(["nvidia-smi", f"--query-gpu={GPU_FIELDS}", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=4,
                                   creationflags=NO_WINDOW)
                f = [x.strip() for x in r.stdout.strip().splitlines()[0].split(",")] if r.returncode == 0 and r.stdout.strip() else []
                if len(f) >= 16:
                    reasons = []
                    try:
                        mask = int(f[15], 16)
                        reasons = [name for bit, name in THROTTLE if mask & bit]
                    except ValueError:
                        pass
                    self.data = {"temp": _num(f[0]), "util": _num(f[1]), "mem_util": _num(f[2]), "vram_used": _num(f[3]), "vram_total": _num(f[4]), "power": _num(f[5]),
                                 "power_limit": _num(f[6]), "clock": _num(f[7]), "clock_max": _num(f[8]), "mem_clock": _num(f[9]), "mem_clock_max": _num(f[10]),
                                 "fan": _num(f[11]), "pstate": f[12], "enc": _num(f[13]), "dec": _num(f[14]), "throttle": reasons}
                    self.t = time.time()
            except Exception:
                pass
            time.sleep(max(0.2, 1.0 - (time.time() - t0)))

    def get(self):
        return self.data if self.data and time.time() - self.t < 5 else None

    def close(self):
        self.alive = False


# ------------------------------------------------------------------ donanım bilgisi (bir kez)
_STATIC = None
_STATIC_LOCK = threading.Lock()
PS_INFO = r"""
$ErrorActionPreference='SilentlyContinue'
$c=Get-CimInstance Win32_Processor | Select-Object -First 1
$g=Get-CimInstance Win32_VideoController | Where-Object {$_.Name -notmatch 'Basic|Remote'} | Select-Object -First 1
$o=Get-CimInstance Win32_OperatingSystem
$b=Get-CimInstance Win32_BaseBoard
$bi=Get-CimInstance Win32_BIOS
$m=@(Get-CimInstance Win32_PhysicalMemory | ForEach-Object { @{gb=[math]::Round($_.Capacity/1GB); mhz=$_.Speed; maker=$_.Manufacturer} })
$d=@(Get-PhysicalDisk | ForEach-Object { @{name=$_.FriendlyName; type=[string]$_.MediaType; health=[string]$_.HealthStatus; gb=[math]::Round($_.Size/1GB)} })
@{cpu=$c.Name.Trim(); cores=$c.NumberOfCores; threads=$c.NumberOfLogicalProcessors; base_mhz=$c.MaxClockSpeed; gpu=$g.Name; gpu_driver=$g.DriverVersion;
  res="$($g.CurrentHorizontalResolution)x$($g.CurrentVerticalResolution)@$($g.CurrentRefreshRate)Hz"; os=$o.Caption; build=$o.BuildNumber; board="$($b.Manufacturer) $($b.Product)";
  bios=$bi.SMBIOSBIOSVersion; ram=$m; disks=$d} | ConvertTo-Json -Depth 4 -Compress
"""


def static_info() -> dict:
    global _STATIC
    with _STATIC_LOCK:
        if _STATIC is not None:
            return _STATIC
        info = {"cpu": platform.processor(), "cores": psutil.cpu_count(logical=False), "threads": psutil.cpu_count(), "os": platform.platform()}
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", PS_INFO], capture_output=True, text=True, timeout=25,
                               creationflags=NO_WINDOW, encoding="utf-8", errors="replace")
            d = json.loads(r.stdout.strip() or "{}")
            for k, v in d.items():
                if v not in (None, "", []):
                    info[k] = v
        except Exception:
            pass
        for k in ("ram", "disks"):                         # tek öğeli listeler PowerShell'de nesneye dönüşebilir
            if isinstance(info.get(k), dict):
                info[k] = [info[k]]
        _STATIC = info
        return info


# ------------------------------------------------------------------ örnekleyici
class Sampler:
    def __init__(self):
        self.pdh = None
        self.gpu = None
        self.hist = collections.deque(maxlen=90)
        self.running = False
        self._net = None
        self._dio = None
        self._procs = {}
        self._top = {"cpu": [], "ram": [], "jarvis": None, "t": 0.0}
        self.ncpu = psutil.cpu_count() or 1

    def start(self):
        with _lock:
            if self.running:
                return
            self.running = True
            self.pdh = _Pdh()
            self.gpu = _Gpu()
            self._net = None
            self._dio = None
            self.hist.clear()
            psutil.cpu_percent(percpu=True)
        threading.Thread(target=static_info, daemon=True).start()

    def stop(self):
        with _lock:
            self.running = False
            if self.pdh:
                self.pdh.close()
            if self.gpu:
                self.gpu.close()
            self.pdh = self.gpu = None
            self._procs.clear()

    # -- süreçler (2 sn'de bir): ada göre toplanır, CPU yüzdesi mantıksal çekirdek sayısına bölünür (Görev Yöneticisi gibi)
    def _processes(self):
        now = time.time()
        if now - self._top["t"] < 2.0:
            return self._top
        cpu, ram, jc, jr = {}, {}, 0.0, 0
        seen = set()
        here = os.path.normcase(os.path.dirname(os.path.abspath(__file__)))
        for p in psutil.process_iter(["pid", "name"]):
            try:
                pid = p.info["pid"]
                pr = self._procs.get(pid)
                if pr is None or pr.pid != pid:
                    pr = self._procs[pid] = p
                seen.add(pid)
                name = (p.info["name"] or "?")
                if name.lower().endswith(".exe"):
                    name = name[:-4]
                c = pr.cpu_percent(None) / self.ncpu
                rss = pr.memory_info().rss
                cpu[name] = cpu.get(name, 0.0) + c
                ram[name] = ram.get(name, 0) + rss
                if name.lower() in ("python", "pythonw"):          # Jarvis'in ana işlemi: main.py çalıştıran ve çalışma klasörü Jarvis klasörü olan python
                    try:
                        if any(a.lower().endswith("main.py") for a in pr.cmdline()) and os.path.normcase(pr.cwd()) == here:
                            jc += c
                            jr += rss
                    except (psutil.Error, OSError):
                        pass
            except (psutil.Error, OSError):
                continue
        for pid in list(self._procs):
            if pid not in seen:
                self._procs.pop(pid, None)
        skip = {"System Idle Process", "Idle"}
        self._top = {"cpu": sorted(((n, round(v, 1)) for n, v in cpu.items() if n not in skip), key=lambda x: -x[1])[:7],
                     "ram": sorted(((n, round(v / 2 ** 20)) for n, v in ram.items()), key=lambda x: -x[1])[:7],
                     "jarvis": {"cpu": round(jc, 1), "ram_mb": round(jr / 2 ** 20)}, "t": now}
        return self._top

    def snapshot(self) -> dict:
        now = time.time()
        st = static_info() if _STATIC is not None else {}
        per = psutil.cpu_percent(percpu=True)
        total = round(sum(per) / len(per), 1) if per else 0.0
        pd = self.pdh.read() if self.pdh else {}
        base = float(st.get("base_mhz") or 0)
        freq = round(base * pd["perf"] / 100) if base and "perf" in pd else None
        vm, sw = psutil.virtual_memory(), psutil.swap_memory()
        # disk
        du = psutil.disk_usage("C:/")
        dio = psutil.disk_io_counters()
        rd = wr = None
        if dio and self._dio:
            dt = max(0.2, now - self._dio[0])
            rd, wr = (dio.read_bytes - self._dio[1]) / dt / 2 ** 20, (dio.write_bytes - self._dio[2]) / dt / 2 ** 20
        self._dio = (now, dio.read_bytes, dio.write_bytes) if dio else None
        # ağ: en çok veri geçen arayüz
        nic = psutil.net_io_counters(pernic=True)
        up = down = None
        best = None
        if self._net:
            dt = max(0.2, now - self._net[0])
            for name, c in nic.items():
                o = self._net[1].get(name)
                if not o:
                    continue
                d, u = (c.bytes_recv - o.bytes_recv) / dt, (c.bytes_sent - o.bytes_sent) / dt
                if best is None or d + u > best[1] + best[2]:
                    best = (name, d, u)
        self._net = (now, nic)
        net = {"nic": None, "up_mbps": None, "down_mbps": None, "link_mbps": None, "ip": None}
        if best:
            net.update(nic=best[0], down_mbps=round(best[1] * 8 / 1e6, 2), up_mbps=round(best[2] * 8 / 1e6, 2))
        else:
            for name, s in psutil.net_if_stats().items():
                if s.isup and s.speed and "loopback" not in name.lower():
                    net["nic"] = name
                    break
        if net["nic"]:
            try:
                net["link_mbps"] = psutil.net_if_stats()[net["nic"]].speed or None
                net["ip"] = next((a.address for a in psutil.net_if_addrs().get(net["nic"], []) if a.family == 2), None)
                c = nic.get(net["nic"])
                net["total_gb_down"], net["total_gb_up"] = (round(c.bytes_recv / 2 ** 30, 2), round(c.bytes_sent / 2 ** 30, 2)) if c else (None, None)
            except Exception:
                pass
        top = self._processes()
        g = self.gpu.get() if self.gpu else None
        snap = {
            "t": now,
            "cpu": {"total": total, "per": [round(x) for x in per], "freq_mhz": freq, "base_mhz": base or None, "queue": pd.get("cpu_q"),
                    "procs": len(psutil.pids()), "temp": None},
            "ram": {"total_gb": round(vm.total / 2 ** 30, 1), "used_gb": round(vm.used / 2 ** 30, 2), "avail_gb": round(vm.available / 2 ** 30, 2), "percent": vm.percent,
                    "swap_used_gb": round(sw.used / 2 ** 30, 2), "swap_total_gb": round(sw.total / 2 ** 30, 1), "swap_percent": sw.percent, "pages_sec": pd.get("pages")},
            "gpu": g,
            "disk": {"total_gb": round(du.total / 2 ** 30), "used_gb": round(du.used / 2 ** 30), "free_gb": round(du.free / 2 ** 30), "percent": du.percent,
                     "read_mbs": None if rd is None else round(rd, 1), "write_mbs": None if wr is None else round(wr, 1), "busy": None if "disk_busy" not in pd else round(min(100, pd["disk_busy"]), 1),
                     "latency_ms": None if "disk_lat" not in pd else round(pd["disk_lat"] * 1000, 2), "queue": pd.get("disk_q"), "temp": None},
            "net": net,
            "top_cpu": top["cpu"], "top_ram": top["ram"], "jarvis": top["jarvis"],
            "uptime_s": int(now - psutil.boot_time()),
        }
        snap["alerts"] = alerts(snap)
        self.hist.append(snap)
        return snap


def alerts(s: dict) -> list:
    """Eşikler: yalnızca gerçekten dikkat gerektiren durumlar."""
    out = []
    if s["cpu"]["total"] >= 90:
        out.append(f"İşlemci yüzde {s['cpu']['total']:.0f} dolu")
    if s["ram"]["percent"] >= 85:
        out.append(f"RAM yüzde {s['ram']['percent']:.0f} dolu")
    if s["ram"]["swap_total_gb"] and s["ram"]["swap_percent"] >= 60:
        out.append(f"Sayfa dosyası yüzde {s['ram']['swap_percent']:.0f} dolu")
    if s["ram"].get("pages_sec") and s["ram"]["pages_sec"] > 1500:
        out.append("Bellek yetersizliği belirtisi: yoğun sayfa okuma")
    g = s["gpu"]
    if g:
        if g["temp"] is not None and g["temp"] >= 83:
            out.append(f"Ekran kartı sıcaklığı {g['temp']:.0f} derece")
        if g["vram_total"] and g["vram_used"] / g["vram_total"] >= 0.92:
            out.append("Ekran kartı belleği neredeyse dolu")
        if g["throttle"]:
            out.append("Ekran kartı yavaşlatılıyor: " + ", ".join(g["throttle"]))
    d = s["disk"]
    if d["percent"] >= 90:
        out.append(f"C diski yüzde {d['percent']:.0f} dolu")
    if d["busy"] is not None and d["busy"] >= 90:
        out.append(f"Disk yüzde {d['busy']:.0f} meşgul")
    if d["latency_ms"] is not None and d["latency_ms"] >= 40:
        out.append(f"Disk gecikmesi yüksek: {d['latency_ms']:.0f} ms")
    return out


SAMPLER = Sampler()
