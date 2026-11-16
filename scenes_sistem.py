"""Sistem analizi modu komut işleyicisi (sesle/yazıyla). Tüm cevaplar sysmon.py'nin gerçek ölçümlerinden üretilir; ölçülemeyen değer için açıkça "ölçemiyorum" denir.
Bu modda 'sistemi kapat' gibi güç komutları çalışmaz."""
import re

import scenes
import sysmon


def _snap():
    s = sysmon.SAMPLER
    if s.running and s.hist:
        return s.hist[-1]
    return s.snapshot()


def _avg(vals):
    v = [x for x in vals if x is not None]
    return sum(v) / len(v) if v else None


def _p(x, d=0):
    return f"{x:.{d}f}".replace(".", ",")


def _dur(sec: int) -> str:
    d, r = divmod(sec, 86400)
    h, r = divmod(r, 3600)
    m = r // 60
    return (f"{d} gün " if d else "") + (f"{h} saat " if h else "") + f"{m} dakika"


def say_cpu(s) -> str:
    c = s["cpu"]
    out = f"İşlemci şu an yüzde {_p(c['total'])} dolu"
    if c["freq_mhz"]:
        out += f", etkin frekans {_p(c['freq_mhz'] / 1000, 2)} gigahertz"
    out += f". {c['procs']} işlem çalışıyor"
    if s["top_cpu"]:
        out += f", en çok kullanan {s['top_cpu'][0][0]}, yüzde {_p(s['top_cpu'][0][1])}"
    return out + "."


def say_cpu_temp(s) -> str:
    g = s["gpu"]
    out = "İşlemci sıcaklığını ölçemiyorum efendim. Windows bu bilgisayarda sıcaklık sensörünü uygulamalara açmıyor, ölçmek için ayrıca bir sürücü yüklemek gerekirdi."
    if g and g["temp"] is not None:
        out += f" Ekran kartının sıcaklığını söyleyebilirim: {_p(g['temp'])} derece."
    return out


def say_ram(s) -> str:
    r = s["ram"]
    out = f"Bellek yüzde {_p(r['percent'])} dolu: {_p(r['used_gb'], 1)} gigabayt kullanımda, {_p(r['avail_gb'], 1)} gigabayt boş, toplam {_p(r['total_gb'], 0)}."
    if r["swap_total_gb"]:
        out += f" Sayfa dosyası yüzde {_p(r['swap_percent'])} dolu."
    if s["top_ram"]:
        out += f" En çok belleği {s['top_ram'][0][0]} kullanıyor, {s['top_ram'][0][1]} megabayt."
    return out


def say_gpu(s) -> str:
    g = s["gpu"]
    name = (sysmon._STATIC or {}).get("gpu") or "Ekran kartı"
    if not g:
        return "Ekran kartı verisini şu an okuyamıyorum efendim."
    out = (f"{name}: yüzde {_p(g['util'])} yükte, sıcaklık {_p(g['temp'])} derece, video belleği {_p(g['vram_used'] / 1024, 1)} / {_p(g['vram_total'] / 1024, 0)} gigabayt, "
           f"güç {_p(g['power'], 0)} watt, saat hızı {_p(g['clock'], 0)} megahertz.")
    if g["throttle"]:
        out += " Dikkat: " + ", ".join(g["throttle"]) + " nedeniyle yavaşlatılıyor."
    return out


def say_disk(s) -> str:
    d = s["disk"]
    out = f"C diski yüzde {_p(d['percent'])} dolu, {d['free_gb']} gigabayt boş."
    if d["read_mbs"] is not None:
        out += f" Şu an okuma {_p(d['read_mbs'], 1)}, yazma {_p(d['write_mbs'], 1)} megabayt saniye."
    if d["busy"] is not None:
        out += f" Disk yüzde {_p(d['busy'])} meşgul, gecikme {_p(d['latency_ms'], 1)} milisaniye."
    h = ((sysmon._STATIC or {}).get("disks") or [{}])[0]
    if h.get("health"):
        out += f" Sağlık durumu {h['health']} görünüyor."
    return out + " Diskin sıcaklığı ve aşınma bilgisi yönetici izni gerektirdiği için ölçülmedi."


def say_net(s) -> str:
    n = s["net"]
    if not n["nic"]:
        return "Etkin bir ağ bağlantısı bulamadım efendim."
    out = f"{n['nic']} bağlantısı"
    if n["link_mbps"]:
        out += f", bağlantı hızı {n['link_mbps']} megabit"
    if n["down_mbps"] is not None:
        out += f". Şu an indirme {_p(n['down_mbps'], 1)}, yükleme {_p(n['up_mbps'], 1)} megabit saniye"
    return out + ". Bu bağlantı hızıdır, internet hızı testi değildir."


def say_top(s) -> str:
    c = ", ".join(f"{n} yüzde {_p(v)}" for n, v in s["top_cpu"][:3])
    r = ", ".join(f"{n} {m} megabayt" for n, m in s["top_ram"][:3])
    return f"İşlemciyi en çok kullananlar: {c}. Belleği en çok kullananlar: {r}."


def say_info() -> str:
    i = sysmon.static_info()
    ram = i.get("ram") or []
    ram_s = ""
    if ram:
        ram_s = f"{sum(x.get('gb', 0) for x in ram)} gigabayt bellek ({len(ram)} modül, {ram[0].get('mhz')} megahertz). "
    disks = ", ".join(f"{d.get('name')} {d.get('gb')} gigabayt" for d in (i.get("disks") or []))
    return (f"İşlemci {i.get('cpu', '?')}, {i.get('cores')} çekirdek {i.get('threads')} iş parçacığı. Ekran kartı {i.get('gpu', '?')}. {ram_s}"
            f"Depolama: {disks or 'bilinmiyor'}. Anakart {i.get('board', '?')}. {i.get('os', '')}, derleme {i.get('build', '')}.")


def diagnose(s) -> str:
    """'Bilgisayar neden yavaş': gerçek ölçümlerden en olası darboğaz."""
    h = list(sysmon.SAMPLER.hist)[-15:] or [s]
    cpu = _avg(x["cpu"]["total"] for x in h)
    ram = s["ram"]["percent"]
    busy = _avg(x["disk"]["busy"] for x in h)
    lat = _avg(x["disk"]["latency_ms"] for x in h)
    why = []
    if cpu >= 80:
        why.append(f"işlemci yüzde {_p(cpu)} yükte, en çok kullanan {s['top_cpu'][0][0] if s['top_cpu'] else 'bilinmiyor'}")
    if ram >= 85:
        why.append(f"bellek yüzde {_p(ram)} dolu, en çok kullanan {s['top_ram'][0][0] if s['top_ram'] else 'bilinmiyor'}")
    if busy is not None and busy >= 80:
        why.append(f"disk yüzde {_p(busy)} meşgul")
    if lat is not None and lat >= 30:
        why.append(f"disk gecikmesi {_p(lat)} milisaniye")
    g = s["gpu"]
    if g and g["throttle"]:
        why.append("ekran kartı " + ", ".join(g["throttle"]) + " nedeniyle yavaşlatılıyor")
    if g and g["temp"] is not None and g["temp"] >= 83:
        why.append(f"ekran kartı {_p(g['temp'])} derece")
    if s["disk"]["percent"] >= 92:
        why.append(f"C diski neredeyse dolu, yüzde {_p(s['disk']['percent'])}")
    if why:
        return "Yavaşlığın olası nedeni: " + "; ".join(why) + "."
    return (f"Anormal bir şey görmüyorum efendim. İşlemci ortalama yüzde {_p(cpu)}, bellek yüzde {_p(ram)}, disk gecikmesi normal. "
            "Yavaşlık başka bir uygulamadan ya da ağdan gelebilir, işlemcide ve bellekte darboğaz yok. İşlemci sıcaklığını ölçemediğim için ısı kaynaklı yavaşlamayı göremem.")


def scan_summary(s) -> str:
    h = list(sysmon.SAMPLER.hist)[-20:] or [s]
    parts = []
    parts.append(f"İşlemci ortalama yüzde {_p(_avg(x['cpu']['total'] for x in h))}, en yüksek {_p(max(x['cpu']['total'] for x in h))}")
    parts.append(f"bellek yüzde {_p(s['ram']['percent'])}")
    g = s["gpu"]
    if g:
        parts.append(f"ekran kartı yüzde {_p(g['util'])} yükte {_p(g['temp'])} derece")
    parts.append(f"C diski yüzde {_p(s['disk']['percent'])} dolu")
    msg = "Tarama tamamlandı: " + ", ".join(parts) + "."
    msg += (" Dikkat edilecekler: " + "; ".join(s["alerts"]) + ".") if s["alerts"] else " Dikkat gerektiren bir durum yok."
    return msg + " İşlemci ve disk sıcaklığı ölçülemedi."


def sistem(text: str, st: dict):
    t = scenes.norm(text)
    if re.search(r"\b(sistemi|bilgisayarı|bilgisayarımı|pc'yi|pc yi)\b.*\b(kapat|yeniden başlat|uyut|kilitle)\w*|\b(kapat|yeniden başlat)\b.*\b(sistemi|bilgisayarı)\b", t):
        return {"say": "Güç komutları bu modda çalışmaz efendim. Önce çık deyip normal Jarvis'e dönün."}
    s = _snap()
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Sistemi tara, işlemci, ram, ekran kartı, disk, ağ, en çok kaynak kullanan, bilgisayar neden yavaş, sistem bilgisi, çalışma süresi ve Jarvis ne kadar kaynak kullanıyor diyebilirsiniz."}
    if re.search(r"\b(tara|tarama|analiz|incele|genel durum|özet|rapor ver)\w*", t):
        return {"do": {"scan": True}, "say": scan_summary(s)}
    if re.search(r"\b(neden|niye)\b.*\b(yavaş|donuyor|takılıyor|kasıyor)\w*|\b(yavaşladı|yavaşlık|donma|kasma|takılma)\w*", t):
        return {"do": {"scan": True}, "say": diagnose(s)}
    if "jarvis" in text.lower() and re.search(r"\b(kaynak|ram|bellek|işlemci)\w*", t):      # scenes.norm 'jarvis' sözcüğünü attığı için ham metne bakılır
        j = s["jarvis"] or {}
        return {"say": f"Jarvis ana işlemi {j.get('ram_mb', 0)} megabayt bellek ve yüzde {_p(j.get('cpu', 0), 1)} işlemci kullanıyor. Ses tanıma ve dil modeli ekran kartı belleğini ayrıca kullanıyor."}
    if re.search(r"\b(sıcaklık|derece|ısı|sıcak)\w*", t):
        if re.search(r"\b(ekran kartı|gpu|grafik|kart)\b", t):
            return {"say": say_gpu(s)}
        if re.search(r"\b(disk|ssd|depolama)\b", t):
            return {"say": "Diskin sıcaklığını ölçemiyorum efendim, bu bilgi yönetici izni gerektiriyor ve sizin onayınız olmadan izin yükseltmem."}
        return {"say": say_cpu_temp(s)}
    if re.search(r"\b(işlemci|cpu|çekirdek)\w*", t):
        return {"say": say_cpu(s)}
    if re.search(r"\b(ekran kartı|gpu|grafik|vram|video belleği)\w*", t):
        return {"say": say_gpu(s)}
    if re.search(r"\b(en çok|hangi (uygulama|program)|kaynak kullan)\w*", t):
        return {"say": say_top(s)}
    if re.search(r"\b(ram|bellek|hafıza|sayfa dosyası)\b", t):
        return {"say": say_ram(s)}
    if re.search(r"\b(disk|ssd|depolama|c sürücü)\w*", t):
        return {"say": say_disk(s)}
    if re.search(r"\b(ağ|internet|wifi|ethernet|bağlantı|hız)\w*", t):
        return {"say": say_net(s)}
    if re.search(r"\b(sistem bilgisi|donanım|özellik|bilgisayarım ne|anakart|hangi işlemci)\w*", t):
        return {"say": say_info()}
    if re.search(r"\b(açık kal|çalışma süresi|ne kadar süredir|uptime)\w*|\bne zamandır\b", t):
        return {"say": f"Bilgisayar {_dur(s['uptime_s'])} önce açıldı."}
    return {"say": "Anlayamadım efendim. Sistemi tara, işlemci, ram, ekran kartı, disk, ağ, en çok kaynak kullanan, bilgisayar neden yavaş ya da sistem bilgisi diyebilirsiniz."}


def init_payload():
    return {"static": sysmon._STATIC or {}}
