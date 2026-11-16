"""Elektronik Laboratuvarı çözümleme motoru: devre kontrolü, basit simülasyon, Arduino taslağı üretimi, malzeme listesi, devre anlatımı.
Tüm çözümleme KURAL TABANLIDIR ve yaklaşıktır (gerçek devre benzetimi değildir). Girdi: sayfanın gönderdiği kart nesnesi
{ad,w,h,renk,parcalar:[{i,p,x,z,r,deger,renk,etiket}],teller:[{a:[i,pin],b:[i,pin]}]}."""
import heapq
import re

from elektronik_data import PARTS, SEM, VF, SKIP_FLOAT, SABLONLAR, fmt_ohm, E12

BOS = (None, 0)


def num(s, default=None):
    m = re.search(r"\d+(?:[.,]\d+)?", str(s or ""))
    return float(m.group(0).replace(",", ".")) if m else default


def parse_ohm(s):
    m = re.match(r"\s*(\d+(?:[.,]\d+)?)\s*([kKmM])?", str(s or ""))
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    u = (m.group(2) or "").lower()
    return v * (1e3 if u == "k" else 1e6 if u == "m" else 1)


def e12_up(r):
    """r'den büyük ya da eşit en yakın E12 değeri (akım hedefi aşılmasın diye yukarı yuvarlanır)."""
    for v in E12:
        if v >= r * 0.999:
            return v
    return E12[-1]


def led_vf(it, pin=None):
    sem = it["sem"]
    if "vf" in sem and pin in sem["vf"]:
        return sem["vf"][pin]
    if "vf1" in sem:
        return sem["vf1"]
    if it["p"] == "yedi_segment":
        return 2.0
    return VF.get(it.get("renk") or "kirmizi", 2.0)


_LOAD_R = {"buzzer": 100.0, "motor": 20.0, "hoparlor": 8.0}


class Devre:
    """Kartı düğümlere (net) çözer: union-find ile teller birleştirilir; gerilimler, kaynaklar, yollar hesaplanır."""

    def __init__(self, kart):
        kart = kart if isinstance(kart, dict) else {}
        self.kart = kart
        self.insts = {}
        for pa in kart.get("parcalar") or []:
            if not isinstance(pa, dict):
                continue
            i, pid = pa.get("i"), pa.get("p")
            if not i or pid not in PARTS or i in self.insts:
                continue
            self.insts[i] = {"i": i, "p": pid, "part": PARTS[pid], "sem": SEM.get(pid, {}), "deger": pa.get("deger"), "renk": pa.get("renk"),
                             "et": pa.get("etiket") or i}
        self.par = {}
        self.pininfo = {}
        for i, it in self.insts.items():
            for pn in it["part"]["pinler"]:
                self.par[(i, pn["ad"])] = (i, pn["ad"])
                self.pininfo[(i, pn["ad"])] = pn
        self.conn = set()
        self.bad = 0
        for t in kart.get("teller") or []:
            try:
                a, b = tuple(t["a"]), tuple(t["b"])
            except (KeyError, TypeError):
                self.bad += 1
                continue
            if a not in self.par or b not in self.par:
                self.bad += 1
                continue
            self.par[self._f(a)] = self._f(b)
            self.conn.update((a, b))
        self.members = {}
        for k in self.par:
            self.members.setdefault(self._f(k), []).append(k)
        self.gnd = {self._f(k) for k, pn in self.pininfo.items() if pn["tip"] == "gnd"}
        self.mcus = [i for i, it in self.insts.items() if it["sem"].get("mcu")]
        self._build()

    # ---------------------------------------------------------------- temel
    def _f(self, k):
        r = k
        while self.par[r] != r:
            r = self.par[r]
        while self.par[k] != r:
            self.par[k], k = r, self.par[k]
        return r

    def net(self, i, pin):
        return self._f((i, pin))

    def label(self, i):
        return self.insts[i]["et"]

    def _deger_v(self, it):
        d = it.get("deger") or PARTS[it["p"]].get("varsayilan")
        return num(d, 0.0)

    def _src_value(self, it, spec, volt):
        if isinstance(spec, (int, float)):
            return float(spec)
        if spec[0] == "deger":
            return self._deger_v(it) or None
        if spec[0] == "dep":
            v_in = max(volt.get(self.net(it["i"], spec[2]), {0.0}))
            return spec[1] if v_in >= spec[3] else None
        if spec[0] == "depd":
            want = self._deger_v(it)
            v_in = max(volt.get(self.net(it["i"], spec[1]), {0.0}))
            return want if want and v_in >= want + spec[2] else None
        return None

    def _resist(self, it, factor=1.0):
        if it["p"] in ("direnc", "potansiyometre", "trimpot", "termistor"):
            v = parse_ohm(it.get("deger")) or parse_ohm(it["part"].get("varsayilan")) or 1000.0
        else:
            v = it["sem"].get("rdef", 1000.0)
        return v * factor

    def _build(self):
        # ---- gerilim kaynakları (bağımlı çıkışlar için 3 tur)
        volt = {}
        for _ in range(3):
            nv = {}
            for i, it in self.insts.items():
                for pin, spec in (it["sem"].get("src") or {}).items():
                    v = self._src_value(it, spec, volt)
                    if v:
                        nv.setdefault(self.net(i, pin), set()).add(v)
            volt = nv
        for i, it in self.insts.items():                 # zayıf kaynaklar: yalnızca hatta başka kaynak yoksa (ör. ESP32 VIN pini USB'den 5 V verir)
            for pin, v in (it["sem"].get("alt") or {}).items():
                r = self.net(i, pin)
                if r not in volt and r not in self.gnd:
                    volt[r] = {v}
        self.volt = volt
        self.const = {r: max(v) for r, v in volt.items() if r not in self.gnd}
        self.shorts = [r for r in volt if r in self.gnd]
        self.clash = [r for r, v in volt.items() if len(v) > 1 and r not in self.gnd]
        # ---- MCU GPIO'ları (çıkış olabilen, bağlı pinler)
        self.pinr = {}
        for i in self.mcus:
            it = self.insts[i]
            m = it["sem"]["mcu"]
            for pn in it["part"]["pinler"]:
                if pn["tip"] in ("gc", "analog") and pn["ad"] not in m.get("inonly", ()) and (i, pn["ad"]) in self.conn:
                    r = self.net(i, pn["ad"])
                    if r not in self.const and r not in self.gnd:
                        self.pinr.setdefault(r, (m["v"], i, pn["ad"]))
        # ---- kenarlar
        self.edges = []
        self.adj = {}
        for i, it in self.insts.items():
            sem = it["sem"]
            pins = {p["ad"] for p in it["part"]["pinler"]}

            def add(a, b, kind, R, **kw):
                if a not in pins or b not in pins:
                    return None
                e = {"id": len(self.edges), "u": self.net(i, a), "v": self.net(i, b), "kind": kind, "R": R, "own": i, "a": a, "b": b, "cond": None,
                     "on": True, "dyn": False, **kw}
                self.edges.append(e)
                return e
            for y in sem.get("y", ()):
                kind = y[2]
                add(y[0], y[1], kind, self._resist(it, y[3] if len(y) > 3 else 1.0) if kind == "r" else 0.0)
            for tur, a, b in sem.get("l", ()):
                if tur == "led":
                    add(a, b, "d", 0.0, load=tur)
                else:
                    add(a, b, "r", _LOAD_R.get(tur, 50.0), load=tur)
            for a, b, ctrl, when in sem.get("c", ()):
                e = add(a, b, "k", 0.0, cond=(ctrl, when))
                if e:
                    e["ctrl"] = self.net(i, ctrl) if when != "led" else None
                    e["on"] = False
        for e in self.edges:
            if e["u"] == e["v"]:
                continue
            self.adj.setdefault(e["u"], []).append((e["v"], e, 1))
            self.adj.setdefault(e["v"], []).append((e["u"], e, -1))
        self._fixpoint()

    # ---------------------------------------------------------------- yol arama
    def _walk(self, start, targets, dirn, excl=(), dyn=False, only_r=False, stop=()):
        best = {start: 0.0}
        h = [(0.0, 0, start)]
        n = 0
        while h:
            c, _, x = heapq.heappop(h)
            if c > best.get(x, 1e18):
                continue
            if x in targets:
                return c, x
            if x in stop and x != start:                    # kaynak (besleme) hattının ötesine geçilmez
                continue
            for y, e, d in self.adj.get(x, ()):
                if e["id"] in excl:
                    continue
                k = e["kind"]
                if only_r and (k == "d" or e["cond"] is not None):
                    continue
                if e["cond"] is not None and (not e["on"] or (e["dyn"] and not dyn)):
                    continue
                if k == "d" and not ((dirn == "up" and d == -1) or (dirn == "down" and d == 1)):
                    continue
                nc = c + e["R"]
                if nc < best.get(y, 1e18):
                    best[y] = nc
                    n += 1
                    heapq.heappush(h, (nc, n, y))
        return None

    def _srcs(self, mode):
        if mode == "c":
            return self.const
        d = {r: v for r, (v, _i, _p) in self.pinr.items()}
        d.update(self.const)
        return d

    def _grnd(self, mode):
        return self.gnd if mode == "c" else self.gnd | set(self.pinr)

    def hi(self, root, mode="p"):
        return self._walk(root, self._srcs(mode), "up", dyn=(mode == "p")) is not None

    def _fixpoint(self):
        self.lit = set()
        for _ in range(5):
            changed = False
            for e in self.edges:
                if e["cond"] is None:
                    continue
                when = e["cond"][1]
                if when == "led":
                    on, dyn = (e["own"] in self.lit), False
                else:
                    r = e["ctrl"]
                    if when == "hi":
                        pm, cm = self.hi(r, "p"), self.hi(r, "c")
                        on, dyn = pm, pm and not cm
                    elif when == "gnd":
                        pm = self._walk(r, self._grnd("p"), "down", dyn=True) is not None
                        cm = self._walk(r, self._grnd("c"), "down") is not None
                        on, dyn = pm, pm and not cm
                    else:                                  # "lo": ortak kontak kapalı (NC), kontrol yükselince açılır
                        pm, cm = self.hi(r, "p"), self.hi(r, "c")
                        on, dyn = (not cm), pm and not cm
                if (e["on"], e["dyn"]) != (on, dyn):
                    e["on"], e["dyn"] = on, dyn
                    changed = True
            for i, it in self.insts.items():              # sürücü çıkışları (555 OUT, 74HC595, L293D...)
                for out, ctrl in it["sem"].get("d", ()):
                    if (i, out) not in self.conn:
                        continue
                    r = self.net(i, out)
                    if r in self.const or r in self.gnd or r in self.pinr:
                        continue
                    if ctrl is None or self.hi(self.net(i, ctrl), "p"):
                        vcc = next(iter((it["sem"].get("vcc") or {"": 0})), "")
                        v = max(self.volt.get(self.net(i, vcc), {5.0})) if vcc else 5.0
                        self.pinr[r] = (v, i, out)
                        changed = True
            self.loads = self._eval_loads()
            lit = {l["i"] for l in self.loads if l["state"] and l["tur"] == "led"}
            if lit != self.lit:
                self.lit = lit
                changed = True
            if not changed:
                break

    def _state(self, ua, ub, excl):
        up = self._walk(ua, self._srcs("c"), "up", excl)
        dn = self._walk(ub, self.gnd, "down", excl)
        if up and dn:
            return "acik", up, dn
        up = self._walk(ua, self._srcs("p"), "up", excl, True)
        dn = self._walk(ub, self._grnd("p"), "down", excl, True)
        if up and dn and up[1] != dn[1]:
            return "yanip", up, dn
        return None, None, None

    def _eval_loads(self):
        out = []
        for e in self.edges:
            if "load" not in e:
                continue
            it = self.insts[e["own"]]
            st, up, dn = self._state(e["u"], e["v"], {e["id"]})
            d = {"i": e["own"], "tur": e["load"], "a": e["a"], "b": e["b"], "state": st, "R": None, "V": None, "I": None, "src": None, "rev": False, "same": e["u"] == e["v"], "eid": e["id"]}
            if st:
                d["R"] = up[0] + dn[0]
                r = up[1]
                d["V"] = self.const.get(r) if r in self.const and st == "acik" else (self.pinr[r][0] if r in self.pinr else self.const.get(r))
                d["src"] = self.pinr.get(r) if r in self.pinr and r not in self.const else None
                if e["load"] == "led" and d["V"] is not None:
                    vf = led_vf(it, e["a"])
                    d["I"] = (d["V"] - vf) / d["R"] * 1000 if d["R"] > 0.5 else None
                    d["Rup"], d["Rdn"] = up[0], dn[0]
            elif e["load"] == "led":
                rs, _, _ = self._state(e["v"], e["u"], {e["id"]})
                d["rev"] = bool(rs)
            out.append(d)
        groups = {}                                     # ortak dirençten beslenen paralel LED'ler akımı paylaşır
        for d in out:
            if d["tur"] == "led" and d["I"] is not None and d["I"] > 0:
                e = self.edges[d["eid"]]
                if d["Rup"] > 0:
                    groups.setdefault(("u", e["u"]), []).append(d)
                elif d["Rdn"] > 0:
                    groups.setdefault(("v", e["v"]), []).append(d)
        for g in groups.values():
            if len(g) > 1:
                tot = g[0]["I"]
                for n, d in enumerate(g):
                    d["I"], d["Ipin"] = tot / len(g), (tot if n == 0 else 0.0)
        return out

    # ---------------------------------------------------------------- ortak yardımcılar
    def V(self, root):
        if root in self.gnd:
            return 0.0
        if root in self.volt:
            return max(self.volt[root])
        return None

    def pin_v(self, i, pin):
        return self.V(self.net(i, pin))

    def mcu_pins_on(self, root):
        return [(i, p) for (i, p) in self.members.get(root, ()) if i in self.mcus and self.pininfo[(i, p)]["tip"] in ("gc", "analog")]

    def part_ids(self, pid):
        return [i for i, it in self.insts.items() if it["p"] == pid]

    def _kshorts(self):
        """Direnci olmayan (buton, anahtar, sigorta, bobin, tel) yoldan besleme artısı GND'ye ulaşıyorsa o yoldaki parçalar."""
        m = {r: r for r in self.members}

        def fm(x):
            while m[x] != x:
                m[x] = m[m[x]]
                x = m[x]
            return x
        kown = []
        for e in self.edges:
            if e["kind"] == "k" and (e["cond"] is None or (e["on"] and not e["dyn"])) and e["u"] != e["v"]:
                m[fm(e["u"])] = fm(e["v"])
                kown.append(e)
        comp = {}
        for r in self.members:
            comp.setdefault(fm(r), []).append(r)
        out = []
        for c, roots in comp.items():
            if any(r in self.const for r in roots) and any(r in self.gnd for r in roots) and len(roots) > 1:
                out.append(next((e["own"] for e in kown if fm(e["u"]) == c), None))
        return out

    # ---------------------------------------------------------------- KONTROL
    def kontrol(self):
        S = []

        def add(sev, msg, i=None):
            S.append({"sev": sev, "msg": msg, **({"i": i} if i else {})})
        L = self.label
        if not self.insts:
            return [{"sev": "bilgi", "msg": "Kartta henüz parça yok. Bir parça ekleyerek başlayın (ör. 'arduino uno ekle')."}], 100
        if self.bad:
            add("uyari", f"{self.bad} tel geçersiz parça ya da pine bağlı; silinmiş bir parçanın teli olabilir.")
        # --- kısa devre / kaynak çakışması
        for r in self.shorts:
            names = ", ".join(sorted({L(i) for i, p in self.members[r]})[:4])
            add("hata", f"Kısa devre: besleme artısı ile GND aynı hatta birleşmiş ({names}). Artı ile eksiyi bağlayan teli sök; araya yük (direnç, LED+direnç, motor) koy.",
                next((i for i, p in self.members[r] if (self.insts[i]["sem"].get("src") or {}).get(p)), None))
        for r in self.clash:
            vs = "/".join(f"{v:g}V" for v in sorted(self.volt[r]))
            add("hata", f"Farklı gerilim kaynakları aynı hatta birleşmiş ({vs}). Kaynaklar ancak bir regülatör ya da diyot üzerinden birleştirilir.", self.members[r][0][0])
        for own in self._kshorts():
            add("hata", f"Doğrudan kısa devre: {L(own) if own else 'bir bağlantı'} üzerinden besleme artısı GND'ye kısalıyor. Araya direnç veya yük ekle.", own)
        # --- yükler: LED akımı, dirençsiz LED, ters LED
        seen = set()
        for l in self.loads:
            it = self.insts[l["i"]]
            if (l["i"], l["tur"]) in seen:                  # 7 segmentin 8 LED'i gibi çok yüklü parça tek mesaj verir
                continue
            if l["same"]:
                seen.add((l["i"], l["tur"]))
                add("uyari", f"{L(l['i'])} bacaklarının ikisi de aynı hatta: parça kısa devre edilmiş, çalışmaz.", l["i"])
                continue
            if l["tur"] == "led":
                if l["state"] and l["R"] is not None and l["R"] < 1.0:
                    seen.add((l["i"], l["tur"]))
                    vs = l["V"] or 5.0
                    rr = e12_up(max((vs - led_vf(it, l["a"])) / 0.015, 100))
                    add("hata", f"{L(l['i'])} dirençsiz bağlı: LED (ya da pin) aşırı akımla yanar. Seri direnç ekle: {vs:g} V için yaklaşık {fmt_ohm(rr)}.", l["i"])
                elif l["state"] and l["I"] is not None:
                    if l["I"] > 25:
                        add("uyari", f"{L(l['i'])} akımı yaklaşık {l['I']:.0f} mA: LED için fazla. Direnç değerini büyüt (hedef 10-20 mA).", l["i"])
                    elif l["I"] <= 0.5:
                        add("uyari", f"{L(l['i'])} için gerilim yetersiz: LED ileri gerilimi ({led_vf(it, l['a']):g} V) kaynaktan yüksek, yanmayabilir.", l["i"])
                elif not l["state"] and l["rev"]:
                    add("uyari", f"{L(l['i'])} ters bağlı görünüyor: anot (+) artı tarafına, katot (-) GND tarafına gelmeli.", l["i"])
            elif l["tur"] in ("motor", "hoparlor"):
                for pin in (l["a"], l["b"]):
                    if self.mcu_pins_on(self.net(l["i"], pin)) and self.net(l["i"], pin) not in self.const:
                        ad = it["part"]["ad"]
                        add("hata", f"{L(l['i'])} ({ad}) doğrudan mikrodenetleyici pinine bağlı: pin bu akımı veremez. Transistör/MOSFET (taban için 1 kΩ) ya da L298N/ULN2003 sürücü kullan.", l["i"])
                        break
        # --- pin akımları
        cur = {}
        for l in self.loads:
            if l["src"] and l["I"] and l["I"] > 0 and "mcu" in self.insts[l["src"][1]]["sem"]:
                cur[l["src"][1:]] = cur.get(l["src"][1:], 0.0) + l.get("Ipin", l["I"])
        for (mi, pin), ma in cur.items():
            lim = self.insts[mi]["sem"]["mcu"]["imax"]
            if ma > lim[1]:
                add("hata", f"{L(mi)} {pin} pininden yaklaşık {ma:.0f} mA çekiliyor; mutlak sınır {lim[1]} mA. Yükü transistör/sürücü ile sür.", mi)
            elif ma > lim[0]:
                add("uyari", f"{L(mi)} {pin} pini yaklaşık {ma:.0f} mA veriyor; önerilen en çok {lim[0]} mA. Akımı düşür ya da transistör kullan.", mi)
        # --- parça bazlı kontroller
        gnet = {}
        for i, it in self.insts.items():
            pid, part, sem = it["p"], it["part"], it["sem"]
            is_mcu = i in self.mcus
            conn = [p for p in part["pinler"] if (i, p["ad"]) in self.conn]
            if not conn and pid not in SKIP_FLOAT:
                add("uyari", f"{L(i)} ({part['ad']}) hiçbir şeye bağlı değil.", i)
                continue
            opt = set(part.get("opt") or ())
            if not is_mcu and pid not in SKIP_FLOAT:
                for p in part["pinler"]:
                    if (i, p["ad"]) in self.conn or p["ad"] in opt or p["tip"] in ("cikis", "gc", "analog"):
                        continue
                    if p["tip"] in ("guc", "gnd"):
                        add("hata", f"{L(i)} {p['ad']} ({p['acik'] or 'güç'}) pini bağlı değil: parça çalışmaz.", i)
                    elif part["kat"] == "pasif" or pid in ("buton", "anahtar", "buzzer", "hoparlor", "dc_motor", "titresim_motoru", "led", "diyot", "zener", "schottky"):
                        add("uyari", f"{L(i)} parçasının {p['ad']} ucu boşta: devre bu uçtan tamamlanmıyor.", i)
                    elif p["tip"] == "giris":
                        add("uyari", f"{L(i)} {p['ad']} giriş pini boşta: rastgele okuma yapabilir, bir seviyeye bağla.", i)
                    else:
                        add("uyari", f"{L(i)} {p['ad']} pini bağlı değil.", i)
                outs = [p for p in part["pinler"] if p["tip"] in ("cikis", "analog", "veri") and p["ad"] not in opt]
                if outs and all((i, p["ad"]) not in self.conn for p in outs) and part["kat"] in ("sensor", "haberlesme"):
                    add("uyari", f"{L(i)} sensörün çıkış/veri pini hiçbir yere bağlı değil: ölçüm alınamaz.", i)
            # besleme aralığı
            for pin, (lo, hi) in (sem.get("vcc") or {}).items():
                if (i, pin) not in self.conn:
                    continue
                r = self.net(i, pin)
                v = self.V(r)
                if v is None and r in self.pinr:
                    v = self.pinr[r][0]
                    add("uyari", f"{L(i)} bir GPIO pininden besleniyor (en çok ~20 mA). Küçük sensör olabilir; güçlü parçaları 5V/3V3 hattından besle.", i)
                if not v:
                    add("hata", f"{L(i)} {pin} pinine besleme gelmiyor: bu hat bir güç kaynağına (5V, 3V3, pil +) bağlı değil.", i)
                elif v > hi * 1.001:
                    ek = "3V3 pininden besle ya da AMS1117-3.3 gibi bir regülatör kullan." if hi <= 3.7 else "Daha düşük gerilim ver ya da regülatör kullan."
                    add("hata", f"{L(i)} {pin} pinine {v:g} V geliyor, izin verilen en çok {hi:g} V: parça zarar görür. {ek}", i)
                elif v < lo * 0.999:
                    add("uyari", f"{L(i)} {pin} pinindeki {v:g} V, parça için düşük (en az {lo:g} V).", i)
            for pin, (lo, hi) in (sem.get("bidi") or {}).items():
                if (i, pin) in self.conn:
                    v = self.pin_v(i, pin)
                    if v and v > hi * 1.001:
                        add("hata", f"{L(i)} {pin} pinine {v:g} V geliyor, en çok {hi:g} V olmalı.", i)
            # kutup
            if sem.get("pol"):
                a, k = sem["pol"]
                va, vk = self.pin_v(i, a), self.pin_v(i, k)
                if va is None and vk and vk > 0 and self._walk(self.net(i, a), self.gnd, "down", only_r=True, stop=set(self.const)):
                    va = 0.0                                # artı bacak dirençle GND'ye gidiyor, eksi bacak artıda
                if va is not None and vk is not None and va < vk:
                    add("hata", f"{L(i)} ters kutuplu: {a} ucu {va:g} V, {k} ucu {vk:g} V. " + ("Elektrolitik kondansatör patlayabilir; uçları çevir." if pid == "kondansator_elektrolitik" else "Diyot akım geçirmez; kasıtlı değilse çevir."), i)
                elif va == 0 and vk is None and (i, a) in self.conn and pid == "kondansator_elektrolitik":
                    add("uyari", f"{L(i)} artı (+) bacağı GND'ye bağlı görünüyor; kutup ters olabilir.", i)
            # ds18b20 pull-up
            if sem.get("pullup"):
                a, b = sem["pullup"]
                if (i, a) in self.conn and (i, b) in self.conn:
                    r = self._walk(self.net(i, a), {self.net(i, b)}, "down", only_r=True)
                    if not r or r[0] < 1000:
                        add("uyari", f"{L(i)} {a} ile {b} arasında 4,7 kΩ pull-up direnç yok: 1-Wire sensör bulunamaz.", i)
            # transistör tabanı
            if pid in ("transistor_npn", "transistor_pnp") and (i, "B") in self.conn:
                w = self._walk(self.net(i, "B"), self._srcs("p") if pid == "transistor_npn" else self._grnd("p"), "up" if pid == "transistor_npn" else "down", dyn=True)
                if w and w[0] < 1.0:
                    add("uyari", f"{L(i)} tabanı dirençsiz sürülüyor: taban akımı sınırsız kalır. Taban hattına 1 kΩ direnç koy.", i)
            # 3,3 V / 5 V uyumu
            for p in part["pinler"]:
                if (i, p["ad"]) not in self.conn:
                    continue
                r = self.net(i, p["ad"])
                mc = self.mcu_pins_on(r)
                if p["ad"] in (sem.get("l33") or ()):
                    for mi, mp in mc:
                        if self.insts[mi]["sem"]["mcu"]["v"] > 4.0 and mi != i:
                            add("uyari", f"{L(i)} {p['ad']} pini 3,3 V mantıklı ama 5 V'luk {L(mi)} {mp} pinine bağlı: 1 kΩ + 2 kΩ gerilim bölücü ya da seviye dönüştürücü kullan.", i)
                            break
                if p["tip"] == "cikis" and not is_mcu and p["ad"] not in (sem.get("o33") or ()):
                    for mi, mp in mc:
                        if self.insts[mi]["sem"]["mcu"]["v"] < 3.5:
                            vp = max((self.pin_v(i, q) or 0) for q in (sem.get("vcc") or {"": 0}) if q) if sem.get("vcc") else 0
                            if vp >= 4.5:
                                add("uyari", f"{L(i)} {p['ad']} çıkışı 5 V seviyesinde, {L(mi)} {mp} pini 3,3 V'a dayanır. Gerilim bölücü (1 kΩ + 2 kΩ) ya da seviye dönüştürücü kullan.", i)
                            break
        # --- GPIO'ya doğrudan yüksek gerilim
        for r, mem in self.members.items():
            mc = self.mcu_pins_on(r)
            if mc and r in self.const:
                for mi, mp in mc:
                    if self.const[r] > self.insts[mi]["sem"]["mcu"]["v"] * 1.1:
                        add("hata", f"{L(mi)} {mp} pinine {self.const[r]:g} V kaynak bağlı; pin {self.insts[mi]['sem']['mcu']['v']:g} V'a dayanır.", mi)
            # çıkış çakışması
            drv = [(i, p) for i, p in mem if any(o == p for o, _c in self.insts[i]["sem"].get("d", ()))]
            sen = {i for i, p in mem if i not in self.mcus and self.pininfo[(i, p)]["tip"] == "cikis" and (i, p) not in drv}
            if len(mc) >= 2:
                add("uyari", f"{L(mc[0][0])} {mc[0][1]} ve {mc[1][1]} pinleri birbirine bağlı: iki çıkış çakışabilir.", mc[0][0])
            elif drv and (len(drv) >= 2 or mc):
                add("uyari", f"{L(drv[0][0])} {drv[0][1]} çıkışı başka bir çıkış pinine bağlı: aynı hatta iki çıkış olmamalı.", drv[0][0])
            elif len(sen) >= 2:
                add("uyari", f"Aynı hatta {len(sen)} farklı parçanın çıkışı var ({', '.join(L(i) for i in sorted(sen))}): çıkışlar çakışabilir.", sorted(sen)[0])
        # --- buton giriş kuralı
        for i in self.part_ids("buton"):
            r1, r2 = self.net(i, "1"), self.net(i, "2")
            for a, b in ((r1, r2), (r2, r1)):
                if a in self.pinr and a not in self.const:
                    if b in self.gnd:
                        add("bilgi", f"{L(i)}: GND'ye bağlı buton için kodda pinMode(..., INPUT_PULLUP) kullan; basınca LOW okunur.", i)
                    elif b in self.const:
                        ex = {e["id"] for e in self.edges if e["own"] == i}
                        if not self._walk(a, self.gnd, "down", ex, only_r=True):
                            add("uyari", f"{L(i)} artıya bağlı ama pull-down direnç yok: basılmayınca pin boşta kalır. Pin ile GND arasına 10 kΩ koy ya da butonu GND'ye bağla.", i)
        # --- I2C
        for i, it in self.insts.items():
            if i in self.mcus or not any(p["ad"] in ("SDA", "SCL") for p in it["part"]["pinler"]):
                continue
            for mi in self.mcus[:1]:
                sda, scl = self.insts[mi]["sem"]["mcu"].get("i2c", (None, None))
                done_i2c = False
                for p, want, other in (("SDA", sda, scl), ("SCL", scl, sda)):
                    if done_i2c:
                        break
                    if (i, p) not in self.conn:
                        continue
                    mc = [mp for (_m, mp) in self.mcu_pins_on(self.net(i, p)) if _m == mi]
                    if other in mc and want not in mc:
                        add("hata", f"{L(i)} parçasının SDA ve SCL uçları ters bağlanmış: {L(mi)} üzerinde SDA={sda}, SCL={scl}. İki teli değiştir.", i)
                        done_i2c = True
                    elif mc and want not in mc:
                        k = self.insts[mi]["sem"]["mcu"]["kind"]
                        if k == "avr":
                            add("uyari", f"{L(i)} {p} pini {mc[0]}'a bağlı; {L(mi)} donanımsal I2C pinleri {sda} (SDA) ve {scl} (SCL)'dir.", i)
                        else:
                            add("bilgi", f"{L(i)} {p} özel pine bağlı: kodda Wire.begin(SDA, SCL) ile pinleri belirtmelisin (varsayılan {sda}/{scl}).", i)
        # --- analog parçalar analog olmayan pine bağlı
        for i, it in self.insts.items():
            if i in self.mcus:
                continue
            for p in it["part"]["pinler"]:
                if p["tip"] == "analog" and (i, p["ad"]) in self.conn:
                    for mi, mp in self.mcu_pins_on(self.net(i, p["ad"])):
                        if self.pininfo[(mi, mp)]["tip"] != "analog":
                            add("uyari", f"{L(i)} {p['ad']} analog çıkışlı ama {L(mi)} {mp} pini analog giriş değil; A0-A5 gibi bir analog pin kullan.", i)
                            break
        # --- ortak toprak
        for mi in self.mcus[:1]:
            gr = {self.net(mi, p["ad"]) for p in self.insts[mi]["part"]["pinler"] if p["tip"] == "gnd"}
            if gr:
                for i, it in self.insts.items():
                    if i in self.mcus or it["p"] in SKIP_FLOAT:
                        continue
                    sig = [p for p in it["part"]["pinler"] if p["tip"] not in ("guc", "gnd", "pasif") and (i, p["ad"]) in self.conn and any(m_ == mi for m_, _ in self.mcu_pins_on(self.net(i, p["ad"])))]
                    gp = [self.net(i, p["ad"]) for p in it["part"]["pinler"] if p["tip"] == "gnd" and (i, p["ad"]) in self.conn]
                    if sig and gp and not any(g in gr for g in gp):
                        add("uyari", f"{L(i)} parçasının GND'si {L(mi)} ile ortak değil: ayrı beslemeli parçaların topraklarını birleştir (ortak GND), yoksa sinyal çalışmaz.", i)
        # --- tek parça ipuçları
        for i in self.part_ids("atmega328p"):
            if not self.part_ids("kristal"):
                add("bilgi", f"{L(i)} için 16 MHz kristal (+2×22 pF) eklenmedi: dahili 8 MHz osilatör için sigorta (fuse) ayarı gerekir; RESET'i de 10 kΩ ile artıya çek.", i)
        for i in self.part_ids("servo"):
            if (i, "VCC") in self.conn and any(self.insts[mi]["p"].startswith("arduino") for mi in self.mcus) and \
                    any(m_ in self.mcus and self.pininfo[(m_, p_)]["ad"] == "5V" for m_, p_ in self.members.get(self.net(i, "VCC"), ())):
                add("bilgi", f"{L(i)} servo 5V pininden besleniyor: hareket anında akım çeker ve kart resetlenebilir. Küçük SG90 için sorun olmaz; birden fazla servo için harici 5 V kullan.", i)
        for i in self.part_ids("lm2596"):
            if (i, "OUT+") in self.conn and self.pin_v(i, "OUT+") is None:
                add("bilgi", f"{L(i)} çıkışı için giriş gerilimi yeterli değil ya da bağlı değil.", i)
        h = sum(1 for s in S if s["sev"] == "hata")
        u = sum(1 for s in S if s["sev"] == "uyari")
        b = sum(1 for s in S if s["sev"] == "bilgi")
        if not S:
            S.append({"sev": "bilgi", "msg": "Hiçbir sorun bulunamadı: bağlantılar kurala uygun görünüyor."})
        return S, max(0, min(100, 100 - 20 * h - 6 * u - b))

    # ---------------------------------------------------------------- SİMÜLASYON
    def sim(self):
        acik, yanip, yanik, nots = set(), set(), set(), []
        L = self.label
        if not self.insts:
            return {"acik": [], "yanip": [], "yanik": [], "not": ["Kart boş: simüle edilecek parça yok."]}
        ks = self._kshorts()
        if self.shorts or self.clash or ks:
            yanik.update(i for i in ks if i)
            for r in self.shorts + self.clash:
                for i, p in self.members[r]:
                    if (self.insts[i]["sem"].get("src") or {}).get(p):
                        yanik.add(i)
            nots.append("Kısa devre var: kaynak zorlanıyor. Önce 'devreyi kontrol et' ile sorunu bul; simülasyon yapılmadı.")
            return {"acik": [], "yanip": [], "yanik": sorted(yanik), "not": nots}
        noted = set()
        for l in self.loads:
            i, it = l["i"], self.insts[l["i"]]
            ad = L(i)
            if l["same"] or ((i, l["a"]) not in self.conn and len(it["sem"].get("l", ())) > 1):
                continue
            if l["tur"] == "led" and l["state"] and l["R"] is not None and l["R"] < 1.0:
                if (i, "burn") in noted:
                    continue
                noted.add((i, "burn"))
            if l["tur"] == "led":
                if l["state"] and l["R"] is not None and l["R"] < 1.0:
                    yanik.add(i)
                    nots.append(f"{ad}: dirençsiz bağlı, aşırı akımla yanar.")
                elif l["state"] == "acik":
                    acik.add(i)
                    nots.append(f"{ad}: {l['V']:g} V kaynaktan {fmt_ohm(l['R'])} dirençle sürülüyor, sürekli yanar" + (f" (≈{l['I']:.0f} mA)." if l["I"] else "."))
                elif l["state"] == "yanip":
                    yanip.add(i)
                    nots.append(f"{ad}: mikrodenetleyici/sürücü çıkışıyla kontrol ediliyor; program çalışınca yanıp söner" + (f" (≈{l['I']:.0f} mA)." if l["I"] else "."))
                elif l["rev"]:
                    nots.append(f"{ad}: ters bağlı, yanmaz.")
                else:
                    nots.append(f"{ad}: akım yolu yok (artıdan GND'ye tamamlanmıyor), yanmaz.")
            elif l["state"]:
                (acik if l["state"] == "acik" else yanip).add(i)
                eylem = {"buzzer": "öter", "motor": "döner", "hoparlor": "ses verir"}.get(l["tur"], "çalışır")
                nots.append(f"{ad}: {'sürekli' if l['state'] == 'acik' else 'kontrollü (kod/sürücü ile)'} {eylem}.")
            elif l["tur"] in ("buzzer", "motor", "hoparlor"):
                nots.append(f"{ad}: akım yolu tamamlanmadığı için çalışmaz.")
        for i, it in self.insts.items():
            vcc = it["sem"].get("vcc")
            if not vcc or i in self.mcus:
                continue
            ok = False
            for pin, (lo, hi) in vcc.items():
                if (i, pin) not in self.conn:
                    continue
                v = self.pin_v(i, pin) or (self.pinr[self.net(i, pin)][0] if self.net(i, pin) in self.pinr else 0)
                if v > hi * 1.001:
                    yanik.add(i)
                    nots.append(f"{L(i)}: {pin} pinine {v:g} V geliyor, aşırı gerilimle bozulur.")
                    ok = False
                    break
                if v >= lo * 0.999:
                    ok = True
            gok = any((i, p["ad"]) in self.conn for p in it["part"]["pinler"] if p["tip"] == "gnd")
            if ok and gok and i not in yanik:
                ctl = it["sem"].get("ctl") or []
                drv = any((i, c) in self.conn and self._walk(self.net(i, c), self._srcs("p"), "up", dyn=True) is not None and
                          self._walk(self.net(i, c), self.const, "up") is None for c in ctl)
                (yanip if drv else acik).add(i)
                nots.append(f"{L(i)}: beslemesi tamam" + ("; kontrol girişi mikrodenetleyici ile sürülüyor." if drv else "."))
            elif not ok and i not in yanik and any((i, p) in self.conn for p in vcc):
                nots.append(f"{L(i)}: yeterli besleme/GND yok, çalışmaz.")
        if self.mcus:
            nots.append("Mikrodenetleyici kartının USB ile beslendiği varsayıldı. Sonuçlar basit kural tabanlı yaklaşıktır, gerçek devre benzetimi değildir.")
        else:
            nots.append("Sonuçlar basit kural tabanlı yaklaşıktır, gerçek devre benzetimi değildir.")
        return {"acik": sorted(acik - yanik), "yanip": sorted(yanip - yanik), "yanik": sorted(yanik), "not": nots}

    # ---------------------------------------------------------------- MALZEME LİSTESİ
    def bom(self):
        g = {}
        for i, it in self.insts.items():
            deger = it.get("deger") or ""
            renk = it.get("renk") or ""
            key = (it["p"], deger, renk)
            d = g.setdefault(key, {"ad": it["part"]["ad"] + (f" ({renk})" if renk else ""), "deger": deger, "adet": 0, "etiketler": []})
            d["adet"] += 1
            d["etiketler"].append(it["et"])
        return sorted(g.values(), key=lambda d: (d["etiketler"][0].rstrip("0123456789"), d["etiketler"][0]))

    # ---------------------------------------------------------------- MCU pin eşleştirmesi (kod üretimi + anlatım)
    def primary_mcu(self):
        for i in self.mcus:
            if self.insts[i]["part"]["kat"] == "kart":
                return i
        return self.mcus[0] if self.mcus else None

    def bindings(self, mi):
        """{parça: {parça pini: mcu pini}} ve sıralı satırlar [(mcu pini, [(parça, pin, aradaki parçalar)])]."""
        it = self.insts[mi]
        by, rows = {}, []
        for pn in it["part"]["pinler"]:
            if pn["tip"] not in ("gc", "analog") or (mi, pn["ad"]) not in self.conn:
                continue
            root = self.net(mi, pn["ad"])
            devs = self._devices(root, mi)
            if devs:
                rows.append((pn["ad"], devs))
            for i, p, via in devs:
                by.setdefault(i, {}).setdefault(p, pn["ad"])
        return by, rows

    def _devices(self, start, mi):
        seen, q, out = {start}, [(start, (), 0)], []
        while q:
            root, via, dep = q.pop(0)
            for (i, pin) in self.members.get(root, ()):
                if i == mi or i in self.mcus:
                    continue
                pid = self.insts[i]["p"]
                tip = self.pininfo[(i, pin)]["tip"]
                if tip in ("guc", "gnd") or pid in SKIP_FLOAT:
                    continue
                if pid == "direnc" and dep < 3:
                    o = "2" if pin == "1" else "1"
                    r2 = self.net(i, o)
                    if r2 not in seen and r2 not in self.gnd and r2 not in self.const:      # toprak/besleme hattına geçilmez (pull-up/pull-down/bölücü direnci başka parçaları pine bağlamasın)
                        seen.add(r2)
                        q.append((r2, via + (i,), dep + 1))
                    continue
                out.append((i, pin, via))
                if pid in ("transistor_npn", "transistor_pnp", "mosfet_n") and pin in ("B", "G") and dep < 3:
                    for o in ("C", "D"):
                        if (i, o) in self.pininfo:
                            r2 = self.net(i, o)
                            if r2 not in seen:
                                seen.add(r2)
                                q.append((r2, via + (i,), dep + 1))
        return out

    # ---------------------------------------------------------------- DEVREYİ ANLAT
    def anlat(self):
        if not self.insts:
            return "Kart boş efendim. Bir parça ekleyerek başlayabilirsiniz."
        L = self.label
        k = self.kart
        cnt = {}
        for it in self.insts.values():
            cnt[it["part"]["ad"]] = cnt.get(it["part"]["ad"], 0) + 1
        out = [f"{k.get('ad') or 'Kart'}: {len(self.insts)} parça ve {len(k.get('teller') or [])} bağlantı içeriyor. Parçalar: " + ", ".join(f"{n} adet {a}" if n > 1 else a for a, n in cnt.items()) + "."]
        if self.const:
            out.append("Güç hatları: " + ", ".join(sorted({f"{v:g} V" for v in self.const.values()})) + ".")
        else:
            out.append("Henüz bir güç kaynağı (pil, USB kartı, 5V) hatta bağlı değil.")
        mi = self.primary_mcu()
        if mi:
            by, rows = self.bindings(mi)
            for pin, devs in rows[:10]:
                dn = []
                for i, p, via in devs:
                    if self.insts[i]["p"].startswith("transistor") or self.insts[i]["p"] == "mosfet_n":
                        continue
                    dn.append(" → ".join([L(v) for v in via] + [f"{L(i)} {p}"]))
                if dn:
                    out.append(f"{L(mi)} {pin} pini: " + "; ".join(dn) + ".")
        for l in self.loads:
            if l["tur"] == "led" and l["state"] and l["R"] is not None and l["R"] >= 1 and l["I"]:
                out.append(f"{L(l['i'])} yaklaşık {l['I']:.0f} mA akımla {'sürekli yanar' if l['state'] == 'acik' else 'program/sürücü ile yanıp söner'}.")
        for i in self.part_ids("ne555"):
            f = self._f555(i)
            if f:
                out.append(f"{L(i)} astable modda: yaklaşık {f[0]:.2f} Hz frekans, %{f[1]:.0f} doluluk oranıyla kare dalga üretir; çıkıştaki LED saniyede yaklaşık {f[0]:.1f} kez yanıp söner.")
        if mi and self.part_ids("ne555") == []:
            out.append("Devre mikrodenetleyici ile çalışır: 'kodu üret' ile bir Arduino taslağı alabilirsiniz.")
        elif not mi and not self.part_ids("ne555") and self.loads:
            n = sum(1 for l in self.loads if l["state"])
            out.append(f"Devre mikrodenetleyicisizdir; yükler doğrudan güç hattı ve parçalar üzerinden çalışır ({n} yük etkin).")
        return " ".join(out)

    def _f555(self, i):
        try:
            vcc, dis, thr, gnd = (self.net(i, p) for p in ("VCC", "DIS", "THR", "GND"))
            r1 = self._walk(vcc, {dis}, "down", only_r=True)
            r2 = self._walk(dis, {thr}, "down", only_r=True)
            cs = [self.insts[c] for c in self.part_ids("kondansator_elektrolitik") + self.part_ids("kondansator_seramik")
                  if {self.net(c, "+" if self.insts[c]["p"] == "kondansator_elektrolitik" else "1"), self.net(c, "-" if self.insts[c]["p"] == "kondansator_elektrolitik" else "2")} == {thr, gnd}]
            if not (r1 and r2 and cs):
                return None
            c = parse_cap(cs[0].get("deger"))
            if not c or r1[0] + 2 * r2[0] <= 0:
                return None
            return 1.44 / ((r1[0] + 2 * r2[0]) * c), (r1[0] + r2[0]) / (r1[0] + 2 * r2[0]) * 100
        except (KeyError, StopIteration):
            return None


def parse_cap(s):
    m = re.match(r"\s*(\d+(?:[.,]\d+)?)\s*(p|n|µ|u|m)?F?", str(s or ""))
    if not m:
        return None
    return float(m.group(1).replace(",", ".")) * {"p": 1e-12, "n": 1e-9, "µ": 1e-6, "u": 1e-6, "m": 1e-3, None: 1.0}[m.group(2)]


# ====================================================================== ŞABLON KURUCU
def sablon_kart(sab):
    """Şablon açıklamasından sayfaya gidecek kart nesnesi (x/z verilmez: sayfa otomatik yerleştirir)."""
    ids, parcalar, say = {}, [], {}
    for n, (key, pid, ek) in enumerate(sab["p"], 1):
        part = PARTS[pid]
        ref = part["ref"]
        say[ref] = say.get(ref, 0) + 1
        ids[key] = f"p{n}"
        d = {"i": f"p{n}", "p": pid, "etiket": f"{ref}{say[ref]}"}
        if part.get("degerler"):
            d["deger"] = part["varsayilan"]
        if part.get("renkler"):
            d["renk"] = part["renkler"][0]
        d.update(ek)
        parcalar.append(d)
    teller = [{"a": [ids[a], pa], "b": [ids[b], pb], "tip": "kablo"} for a, pa, b, pb in sab["t"]]
    return {"ad": sab["ad"], "w": sab.get("w", 40), "h": sab.get("h", 28), "renk": "yesil", "parcalar": parcalar, "teller": teller}


# ====================================================================== KOD ÜRETİMİ
_ADC = {"avr": (1023, 5.0), "esp32": (4095, 3.3), "esp8266": (1023, 3.3), "pico": (1023, 3.3)}


class Kod:
    def __init__(self, A, mi):
        self.A, self.mi = A, mi
        self.m = A.insts[mi]
        self.mp = self.m["sem"]["mcu"]
        self.kind = self.mp["kind"]
        self.adcmax, self.vref = _ADC[self.kind]
        self.inc, self.glob, self.setup, self.loop, self.libs, self.defs = [], [], [], [], [], []
        self.vals, self.disp, self.cond = {}, [], []
        self.leds, self.btns = [], []
        self.baud = 9600 if self.kind == "avr" else 115200
        self.serial = False
        self.names = set()
        self.ipucu = None                           # blok kurucudan: {"esik", "olcu": temp|cm|hum, "yon": ">"|"<"}
        self.esik_cond = None

    def lit(self, pin):
        pid = self.m["p"]
        if pid in ("arduino_uno", "arduino_nano", "arduino_mega"):
            return pin[1:] if pin.startswith("D") else pin
        if pid == "esp32":
            return pin[1:] if pin.startswith("G") else pin
        if pid == "raspberry_pico":
            return pin[2:] if pin.startswith("GP") else pin
        if pid == "atmega328p":
            return {"B": lambda n: str(8 + n), "D": lambda n: str(n), "C": lambda n: f"A{n}"}[pin[1]](int(pin[2:])) if re.match(r"P[BCD]\d$", pin) else pin
        if pid == "attiny85":
            return pin[2:] if pin.startswith("PB") else pin
        return pin

    def vn(self, it, pre):
        return f"{pre}_" + re.sub(r"\W", "", it["et"]).lower()

    def is_adc(self, pin):
        return self.A.pininfo[(self.mi, pin)]["tip"] == "analog"

    def mac(self, it, role, pin):
        base = re.sub(r"\W", "", it["et"]).upper() or "P"
        name = f"{base}_{role}_PIN" if role else f"{base}_PIN"
        if name not in self.names:
            self.names.add(name)
            self.defs.append(f"#define {name} {self.lit(pin)}")
        return name

    def var(self, name, typ, init):
        if name not in self.names:
            self.names.add(name)
            self.glob.append(f"{typ} {name} = {init};")
        return name

    def lib(self, s):
        if s not in self.libs:
            self.libs.append(s)

    def pwm_ok(self, pin):
        pw = self.mp.get("pwm")
        return pw is None or pin in pw

    # ------------------------------------------------------------ parça üreticileri
    def gen(self, i, it, bd):
        pid = it["p"]
        f = getattr(self, "g_" + pid, None)
        if f:
            f(it, bd)
            return True
        return False

    def g_led(self, it, bd):
        if "A" in bd:
            self.leds.append((self.mac(it, "", bd["A"]), False))
        elif "K" in bd:
            self.leds.append((self.mac(it, "", bd["K"]), True))
        else:
            return
        self.setup.append(f"pinMode({self.leds[-1][0]}, OUTPUT);")

    g_ir_led = g_led

    def g_rgb_led(self, it, bd):
        pins = [(c, self.mac(it, c, bd[c])) for c in ("R", "G", "B") if c in bd]
        for _, m in pins:
            self.setup.append(f"pinMode({m}, OUTPUT);")
        if pins:
            self.var("rgbAdim", "int", "0")
            self.loop.append("// RGB LED: renkler sırayla değişir")
            self.loop.append("static unsigned long tRgb = 0;\n  if (millis() - tRgb >= 700) {\n    tRgb = millis();\n    rgbAdim = (rgbAdim + 1) % " + str(len(pins)) + ";")
            for n, (_, m) in enumerate(pins):
                self.loop.append(f"    digitalWrite({m}, rgbAdim == {n} ? HIGH : LOW);")
            self.loop.append("  }")

    def g_buton(self, it, bd):
        pin = bd.get("1") or bd.get("2")
        if not pin:
            return
        m = self.mac(it, "", pin)
        self.setup.append(f"pinMode({m}, INPUT_PULLUP);   // buton GND'ye bağlıysa; basılınca LOW")
        self.btns.append(m)

    def _analog(self, it, bd, pin, kind, label, unit=""):
        m = self.mac(it, "", pin)
        v = self.var(self.vn(it, "v"), "int", "0")
        if not self.is_adc(pin):
            self.loop.append(f"// DİKKAT: {pin} analog giriş değil; analog okunabilen bir pine (A0...) taşıyın")
        self.loop.append(f"{v} = analogRead({m});")
        self.vals.setdefault(kind, v)
        self.disp.append((label, v))
        return v

    def g_potansiyometre(self, it, bd):
        if "W" in bd:
            self._analog(it, bd, bd["W"], "pot", "Pot")

    g_trimpot = g_potansiyometre

    def g_ldr(self, it, bd):
        p = bd.get("1") or bd.get("2")
        if p:
            self._analog(it, bd, p, "ldr", "Isik")

    def g_termistor(self, it, bd):
        p = bd.get("1") or bd.get("2")
        if p:
            self._analog(it, bd, p, "ntc", "NTC(ham)")

    def g_lm35(self, it, bd):
        if "OUT" in bd:
            v = self._analog(it, bd, bd["OUT"], "lm35", "LM35 ham")
            t = self.var("sicaklikC", "float", "0")
            self.loop.append(f"{t} = {v} * ({self.vref} / {self.adcmax}.0) * 100.0;   // LM35: 10 mV / °C")
            self.vals["temp"] = t
            self.disp.append(("Sicaklik C", t))

    def g_toprak_nem(self, it, bd):
        if "AO" in bd:
            v = self._analog(it, bd, bd["AO"], "nem", "Nem(ham)")
            self.loop.append("// Kapasitif sensör: kuru toprakta değer yüksek, ıslakta düşüktür; eşiği kendi sensörünüze göre ayarlayın")

    def g_mq2(self, it, bd):
        if "AO" in bd:
            self._analog(it, bd, bd["AO"], "gaz", "Gaz")
        elif "DO" in bd:
            self._din(it, "DO", bd["DO"], "Gaz?")

    def g_mikrofon(self, it, bd):
        if "AO" in bd:
            self._analog(it, bd, bd["AO"], "ses", "Ses")
        elif "DO" in bd:
            self._din(it, "DO", bd["DO"], "Ses?")

    def _din(self, it, role, pin, label, pull=False):
        m = self.mac(it, role if role not in ("", None) else "", pin)
        self.setup.append(f"pinMode({m}, {'INPUT_PULLUP' if pull else 'INPUT'});")
        v = self.var(self.vn(it, "d"), "int", "0")
        self.loop.append(f"{v} = digitalRead({m});")
        self.disp.append((label, v))
        return v

    def g_hall(self, it, bd):
        if "OUT" in bd:
            self._din(it, "", bd["OUT"], "Hall", True)

    def g_ir_engel(self, it, bd):
        if "OUT" in bd:
            self._din(it, "", bd["OUT"], "Engel(LOW=var)", True)

    def g_pir(self, it, bd):
        if "OUT" in bd:
            v = self._din(it, "", bd["OUT"], "Hareket")
            self.vals["hareket"] = v
            self.cond.append(f"{v} == HIGH")

    def g_hcsr04(self, it, bd):
        if "TRIG" in bd and "ECHO" in bd:
            t, e = self.mac(it, "TRIG", bd["TRIG"]), self.mac(it, "ECHO", bd["ECHO"])
            self.setup += [f"pinMode({t}, OUTPUT);", f"pinMode({e}, INPUT);"]
            cm = self.var("mesafeCm", "float", "0")
            self.loop += [f"digitalWrite({t}, LOW);  delayMicroseconds(2);", f"digitalWrite({t}, HIGH); delayMicroseconds(10);", f"digitalWrite({t}, LOW);",
                          f"long sure = pulseIn({e}, HIGH, 30000);   // µs, 30 ms zaman aşımı", f"{cm} = sure * 0.0343 / 2.0;   // cm (0 = ölçüm yok)"]
            self.vals["cm"] = cm
            self.cond.append(f"({cm} > 0 && {cm} < 30)")
            self.disp.append(("Mesafe cm", cm))

    def _dht(self, it, bd, tur):
        if "DATA" not in bd:
            return
        m = self.mac(it, "", bd["DATA"])
        self.lib("DHT sensor library (Adafruit)")
        self.inc.append("#include <DHT.h>")
        self.glob.append(f"DHT dht({m}, {tur});")
        self.setup.append("dht.begin();")
        t, h = self.var("sicaklikC", "float", "0"), self.var("nemYuzde", "float", "0")
        self.loop += ["static unsigned long tDht = 0;", "if (millis() - tDht >= 2000) {   // DHT en fazla 2 sn'de bir okunur", "  tDht = millis();",
                      f"  {t} = dht.readTemperature();", f"  {h} = dht.readHumidity();", "}"]
        self.vals["temp"] = t
        self.vals["hum"] = h
        self.disp += [("Sicaklik C", t), ("Nem %", h)]

    def g_dht11(self, it, bd):
        self._dht(it, bd, "DHT11")

    def g_dht22(self, it, bd):
        self._dht(it, bd, "DHT22")

    def g_ds18b20(self, it, bd):
        if "DQ" in bd:
            m = self.mac(it, "", bd["DQ"])
            self.lib("OneWire, DallasTemperature")
            self.inc += ["#include <OneWire.h>", "#include <DallasTemperature.h>"]
            self.glob += [f"OneWire oneWire({m});", "DallasTemperature ds(&oneWire);"]
            self.setup.append("ds.begin();")
            t = self.var("sicaklikC", "float", "0")
            self.loop += ["ds.requestTemperatures();", f"{t} = ds.getTempCByIndex(0);"]
            self.vals["temp"] = t
            self.disp.append(("Sicaklik C", t))

    def g_joystick(self, it, bd):
        for ax in ("VRX", "VRY"):
            if ax in bd:
                m = self.mac(it, ax, bd[ax])
                v = self.var(f"v_{ax.lower()}", "int", "0")
                self.loop.append(f"{v} = analogRead({m});")
                self.disp.append((ax, v))
        if "SW" in bd:
            self._din(it, "SW", bd["SW"], "Joy buton", True)

    def g_enkoder(self, it, bd):
        if "CLK" in bd and "DT" in bd:
            c, d = self.mac(it, "CLK", bd["CLK"]), self.mac(it, "DT", bd["DT"])
            self.setup += [f"pinMode({c}, INPUT_PULLUP);", f"pinMode({d}, INPUT_PULLUP);"]
            self.var("enkSayac", "int", "0")
            self.var("enkSon", "int", "HIGH")
            self.loop += [f"int enkNow = digitalRead({c});", f"if (enkNow != enkSon && enkNow == LOW) {{   // CLK düşen kenar: yön DT'ye bakılarak bulunur", f"  enkSayac += (digitalRead({d}) != enkNow) ? 1 : -1;", "}", "enkSon = enkNow;"]
            self.disp.append(("Enkoder", "enkSayac"))
        if "SW" in bd:
            self._din(it, "SW", bd["SW"], "Enk buton", True)

    def g_ir_alici(self, it, bd):
        if "OUT" in bd:
            m = self.mac(it, "", bd["OUT"])
            self.lib("IRremote (v4)")
            self.inc.append("#include <IRremote.hpp>")
            self.setup.append(f"IrReceiver.begin({m}, ENABLE_LED_FEEDBACK);")
            self.loop += ["if (IrReceiver.decode()) {", "  Serial.println(IrReceiver.decodedIRData.decodedRawData, HEX);   // kumanda tuş kodu", "  IrReceiver.resume();", "}"]
            self.serial = True

    def g_buzzer(self, it, bd):
        pin = bd.get("+") or bd.get("-")
        if pin:
            m = self.mac(it, "", pin)
            self.setup.append(f"pinMode({m}, OUTPUT);")
            self.buz = m

    def g_servo(self, it, bd):
        if "SIG" in bd:
            m = self.mac(it, "", bd["SIG"])
            self.lib("ESP32Servo" if self.kind == "esp32" else "Servo (yerleşik)")
            self.inc.append("#include <ESP32Servo.h>" if self.kind == "esp32" else "#include <Servo.h>")
            n = "servo" + re.sub(r"\W", "", it["et"])
            self.glob.append(f"Servo {n};")
            self.setup.append(f"{n}.attach({m});")
            self.servos = getattr(self, "servos", []) + [n]

    def g_role(self, it, bd):
        if "IN" in bd:
            m = self.mac(it, "IN", bd["IN"])
            self.defs.append("// Çoğu röle modülü LOW ile çeker (aktif-düşük). Sizinki HIGH ile çekiyorsa değerleri değiştirin.")
            self.defs += ["#define ROLE_ON LOW", "#define ROLE_OFF HIGH"]
            self.setup += [f"pinMode({m}, OUTPUT);", f"digitalWrite({m}, ROLE_OFF);"]
            self.roles = getattr(self, "roles", []) + [m]

    def g_dc_motor(self, it, bd):
        pin = bd.get("+") or bd.get("-")
        if pin:
            m = self.mac(it, "", pin)
            self.setup.append(f"pinMode({m}, OUTPUT);")
            self.motors = getattr(self, "motors", []) + [(m, pin)]

    g_titresim_motoru = g_dc_motor

    def g_l298n(self, it, bd):
        pins = {k: self.mac(it, k, bd[k]) for k in ("ENA", "IN1", "IN2", "ENB", "IN3", "IN4") if k in bd}
        if "IN1" in pins and "IN2" in pins:
            for m in pins.values():
                self.setup.append(f"pinMode({m}, OUTPUT);")
            if "ENA" in pins:
                self.setup.append(f"digitalWrite({pins['ENA']}, HIGH);   // tam hız (PWM için analogWrite)")
            self.loop += ["// L298N: motor A 2 sn ileri, 1 sn dur, 2 sn geri", "static unsigned long tMot = 0;", "unsigned long gecen = (millis() - tMot) % 6000;",
                          f"digitalWrite({pins['IN1']}, gecen < 2000);", f"digitalWrite({pins['IN2']}, gecen >= 3000 && gecen < 5000);"]

    def g_step_motor(self, it, bd):
        if all(k in bd for k in ("IN1", "IN2", "IN3", "IN4")):
            m = [self.mac(it, k, bd[k]) for k in ("IN1", "IN2", "IN3", "IN4")]
            self.lib("Stepper (yerleşik)")
            self.inc.append("#include <Stepper.h>")
            self.glob.append(f"Stepper stepper(2048, {m[0]}, {m[2]}, {m[1]}, {m[3]});   // 28BYJ-48 için sıra IN1, IN3, IN2, IN4")
            self.setup.append("stepper.setSpeed(10);   // dev/dk")
            self.loop += ["stepper.step(512);   // çeyrek tur (bu sırada program bekler)", "delay(500);"]

    def g_a4988(self, it, bd):
        if "STEP" in bd and "DIR" in bd:
            s, d = self.mac(it, "STEP", bd["STEP"]), self.mac(it, "DIR", bd["DIR"])
            self.setup += [f"pinMode({s}, OUTPUT);", f"pinMode({d}, OUTPUT);", f"digitalWrite({d}, HIGH);"]
            self.loop += ["for (int i = 0; i < 200; i++) {   // 200 adım = 1 tur (tam adım)", f"  digitalWrite({s}, HIGH); delayMicroseconds(800);", f"  digitalWrite({s}, LOW);  delayMicroseconds(800);", "}", "delay(1000);"]

    def g_neopixel(self, it, bd):
        if "DIN" in bd:
            m = self.mac(it, "DIN", bd["DIN"])
            self.lib("Adafruit NeoPixel")
            self.inc.append("#include <Adafruit_NeoPixel.h>")
            self.glob += [f"Adafruit_NeoPixel strip(8, {m}, NEO_GRB + NEO_KHZ800);", "int npAdim = 0;"]
            self.setup += ["strip.begin();", "strip.setBrightness(40);   // akımı düşük tutar"]
            self.loop += ["static unsigned long tNp = 0;", "if (millis() - tNp >= 120) {", "  tNp = millis();", "  strip.clear();", "  strip.setPixelColor(npAdim, strip.Color(0, 80, 160));", "  strip.show();", "  npAdim = (npAdim + 1) % 8;", "}"]

    def g_lcd1602(self, it, bd):
        self.lib("LiquidCrystal_I2C")
        self.inc += ["#include <Wire.h>", "#include <LiquidCrystal_I2C.h>"]
        self.glob.append("LiquidCrystal_I2C lcd(0x27, 16, 2);   // adres 0x3F olabilir")
        self.setup += ["lcd.init();", "lcd.backlight();"]
        self.lcd = True

    def g_oled(self, it, bd):
        self.lib("Adafruit SSD1306 + Adafruit GFX")
        self.inc += ["#include <Wire.h>", "#include <Adafruit_GFX.h>", "#include <Adafruit_SSD1306.h>"]
        self.glob.append("Adafruit_SSD1306 oled(128, 64, &Wire, -1);")
        self.setup += ["oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);", "oled.setTextColor(SSD1306_WHITE);"]
        self.oled = True

    def g_mpu6050(self, it, bd):
        self.lib("Adafruit MPU6050")
        self.inc += ["#include <Wire.h>", "#include <Adafruit_MPU6050.h>", "#include <Adafruit_Sensor.h>"]
        self.glob.append("Adafruit_MPU6050 mpu;")
        self.setup.append("if (!mpu.begin()) { Serial.println(F(\"MPU6050 bulunamadi\")); }")
        self.loop += ["sensors_event_t a, g, temp;", "mpu.getEvent(&a, &g, &temp);", "Serial.print(\"ivme x/y/z: \"); Serial.print(a.acceleration.x); Serial.print(' '); Serial.print(a.acceleration.y); Serial.print(' '); Serial.println(a.acceleration.z);"]
        self.serial = True

    def g_bmp280(self, it, bd):
        self.lib("Adafruit BMP280")
        self.inc += ["#include <Wire.h>", "#include <Adafruit_BMP280.h>"]
        self.glob.append("Adafruit_BMP280 bmp;")
        self.setup.append("if (!bmp.begin(0x76)) { Serial.println(F(\"BMP280 bulunamadi (0x77 deneyin)\")); }")
        p = self.var("basincHpa", "float", "0")
        self.loop.append(f"{p} = bmp.readPressure() / 100.0;")
        self.vals.setdefault("temp", None)
        self.disp.append(("Basinc hPa", p))
        t = self.var("sicaklikC", "float", "0")
        self.loop.append(f"{t} = bmp.readTemperature();")
        self.vals["temp"] = t
        self.disp.append(("Sicaklik C", t))

    def g_rtc(self, it, bd):
        self.lib("RTClib (Adafruit)")
        self.inc += ["#include <Wire.h>", "#include <RTClib.h>"]
        self.glob.append("RTC_DS3231 rtc;")
        self.setup.append("rtc.begin();   // saati ilk seferde rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); ile ayarlayın")
        self.loop += ["DateTime now = rtc.now();", "Serial.print(now.hour()); Serial.print(':'); Serial.print(now.minute()); Serial.print(':'); Serial.println(now.second());"]
        self.serial = True

    def g_rfid(self, it, bd):
        self.lib("MFRC522")
        self.inc += ["#include <SPI.h>", "#include <MFRC522.h>"]
        ss = self.mac(it, "SS", bd["SDA"]) if "SDA" in bd else "SS_PIN"
        rs = self.mac(it, "RST", bd["RST"]) if "RST" in bd else "RST_PIN"
        self.glob.append(f"MFRC522 rfid({ss}, {rs});")
        self.setup += ["SPI.begin();", "rfid.PCD_Init();"]
        self.loop += ["if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {", "  for (byte i = 0; i < rfid.uid.size; i++) { Serial.print(rfid.uid.uidByte[i], HEX); Serial.print(' '); }", "  Serial.println();", "  rfid.PICC_HaltA();", "}"]
        self.serial = True

    def g_tm1637(self, it, bd):
        if "CLK" in bd and "DIO" in bd:
            c, d = self.mac(it, "CLK", bd["CLK"]), self.mac(it, "DIO", bd["DIO"])
            self.lib("TM1637Display")
            self.inc.append("#include <TM1637Display.h>")
            self.glob.append(f"TM1637Display display({c}, {d});")
            self.setup.append("display.setBrightness(5);")
            self.loop += ["display.showNumberDec((millis() / 1000) % 10000);   // saniye sayacı", "delay(200);"]

    def g_hc05(self, it, bd):
        if "TX" in bd and "RX" in bd:
            tx, rx = self.mac(it, "TX", bd["TX"]), self.mac(it, "RX", bd["RX"])
            self.lib("SoftwareSerial (yerleşik)")
            self.inc.append("#include <SoftwareSerial.h>")
            self.glob.append(f"SoftwareSerial bt({tx}, {rx});   // (modülün TX'i kartın RX'ine, modülün RX'i kartın TX'ine)")
            self.setup.append("bt.begin(9600);")
            self.loop += ["if (bt.available()) Serial.write(bt.read());", "if (Serial.available()) bt.write(Serial.read());"]
            self.serial = True

    def g_hc595(self, it, bd):
        if all(k in bd for k in ("DS", "SH_CP", "ST_CP")):
            d, s, l = (self.mac(it, k, bd[k]) for k in ("DS", "SH_CP", "ST_CP"))
            self.setup += [f"pinMode({d}, OUTPUT);", f"pinMode({s}, OUTPUT);", f"pinMode({l}, OUTPUT);"]
            self.var("ykSayi", "byte", "0")
            self.loop += [f"digitalWrite({l}, LOW);", f"shiftOut({d}, {s}, MSBFIRST, ykSayi);   // 8 çıkışa ikili sayı yazar", f"digitalWrite({l}, HIGH);", "ykSayi++;", "delay(250);"]

    def g_yedi_segment(self, it, bd):
        seg = {s: self.mac(it, s, bd[s]) for s in ("A", "B", "C", "D", "E", "F", "G") if s in bd}
        if len(seg) == 7:
            order = ", ".join(seg[s] for s in "ABCDEFG")
            self.glob.append(f"const int SEG_PIN[7] = {{{order}}};   // A..G\nconst byte RAKAM[10] = {{0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F}};   // ortak katot, bit0=A")
            self.setup.append("for (int i = 0; i < 7; i++) pinMode(SEG_PIN[i], OUTPUT);")
            self.loop += ["static unsigned long tSeg = 0; static int rakam = 0;", "if (millis() - tSeg >= 1000) {", "  tSeg = millis();", "  for (int i = 0; i < 7; i++) digitalWrite(SEG_PIN[i], (RAKAM[rakam] >> i) & 1);", "  rakam = (rakam + 1) % 10;", "}"]

    # ------------------------------------------------------------ birleştirme
    def build(self, ad):
        A = self.A
        by, rows = A.bindings(self.mi)
        done, todo = [], []
        order = {"sensor": 0, "baglanti": 0, "pasif": 0, "yariiletken": 1, "haberlesme": 2, "cikis": 3, "entegre": 2}
        for i, it in sorted(A.insts.items(), key=lambda kv: order.get(kv[1]["part"]["kat"], 4)):
            if i == self.mi or i in A.mcus:
                continue
            ok = self.gen(i, it, by.get(i, {}))
            if i in by and not ok and it["p"] not in ("direnc", "transistor_npn", "transistor_pnp", "mosfet_n", "kondansator_seramik", "kondansator_elektrolitik", "diyot", "zener", "schottky"):
                todo.append(f"// {it['et']} ({it['part']['ad']}): özel kütüphane/protokol gerekebilir; pinler: " + ", ".join(f"{p}->{m}" for p, m in by[i].items()))
            if ok:
                done.append(it["et"])
        for it in A.insts.values():                 # I2C parçaları pinsiz ama kodu olanlar
            pass
        # LED davranışı
        if self.leds:
            if self.btns:
                for n, (m, inv) in enumerate(self.leds):
                    b = self.btns[n % len(self.btns)]
                    self.loop.append(f"digitalWrite({m}, (digitalRead({b}) == LOW) {'!=' if inv else '=='} true);   // butona basılıyken yanar")
            elif len(self.leds) == 1:
                m, inv = self.leds[0]
                self.glob.append("unsigned long tLed = 0;\nbool ledDurum = false;")
                self.loop += ["if (millis() - tLed >= 500) {   // 500 ms'de bir durum değiştir (bekleme yok: diğer işler aksamaz)", "  tLed = millis();", "  ledDurum = !ledDurum;",
                              f"  digitalWrite({m}, {'!ledDurum' if inv else 'ledDurum'});", "}"]
            else:
                names = ", ".join(m for m, _ in self.leds)
                inv = [m for m, v in self.leds if v]
                self.glob.append(f"const int LED_PINLERI[{len(self.leds)}] = {{{names}}};\nint ledSira = 0;\nunsigned long tLed = 0;")
                self.loop += ["if (millis() - tLed >= 600) {   // LED'ler sırayla yanar (trafik lambası gibi)", "  tLed = millis();", f"  for (int i = 0; i < {len(self.leds)}; i++) digitalWrite(LED_PINLERI[i], i == ledSira);",
                              f"  ledSira = (ledSira + 1) % {len(self.leds)};", "}"]
                if inv:
                    self.loop.append("// Not: bazı LED'ler pine katottan bağlı (ters mantık); onlar için HIGH/LOW'u değiştirin.")
        # blok kurucudan gelen eşik ('30 derecede fan aç'): koşul buzzer, röle ve motor/fan için ortak kullanılır
        ip = self.ipucu if isinstance(self.ipucu, dict) else None
        if ip and isinstance(ip.get("esik"), (int, float)) and ip.get("olcu") in ("temp", "cm", "hum") and ip.get("yon") in (">", "<"):
            v = self.vals.get(ip["olcu"])
            sabit, birim = {"temp": ("ESIK_SICAKLIK", "°C"), "cm": ("ESIK_MESAFE", "cm"), "hum": ("ESIK_NEM", "%")}[ip["olcu"]]
            if v:
                self.defs.append(f"#define {sabit} {ip['esik']:g}   // eşik: {birim} ({'üstünde' if ip['yon'] == '>' else 'altında'} tetiklenir)")
                self.esik_cond = f"({v} > 0 && {v} {ip['yon']} {sabit})" if ip["olcu"] == "cm" else f"({v} {ip['yon']} {sabit})"
                self.cond.insert(0, self.esik_cond)
            else:
                self.defs.append(f"// Eşik ({ip['esik']:g} {birim}) için ölçüm sensörü bulunamadı; koşulu kendiniz yazın.")
        # buzzer
        if getattr(self, "buz", None):
            b = self.buz
            if self.cond:
                self.loop += [f"if ({' || '.join(self.cond)}) tone({b}, 1000);   // alarm koşulu", f"else noTone({b});"]
            else:
                self.loop += ["static unsigned long tBz = 0;", "if (millis() - tBz >= 2000) {", "  tBz = millis();", f"  tone({b}, 1000, 200);   // 2 sn'de bir kısa bip", "}"]
            if self.kind == "esp32":
                self.defs.append("// ESP32: tone() için çekirdek 3.x gerekir; eski çekirdekte ledcWriteTone kullanın.")
        if not getattr(self, "buz", None) and self.cond and self.leds is None:
            pass
        # servo
        for n in getattr(self, "servos", []):
            if "pot" in self.vals:
                self.loop.append(f"{n}.write(map({self.vals['pot']}, 0, {self.adcmax}, 0, 180));   // pot açıyı belirler")
            else:
                self.var("servoAci", "int", "0")
                self.var("servoYon", "int", "1")
                self.loop += ["static unsigned long tSv = 0;", "if (millis() - tSv >= 15) {", "  tSv = millis();", "  servoAci += servoYon;", "  if (servoAci >= 180 || servoAci <= 0) servoYon = -servoYon;", f"  {n}.write(servoAci);", "}"]
        # röle
        for m in getattr(self, "roles", []):
            if "nem" in self.vals:
                self.loop.append(f"digitalWrite({m}, {self.vals['nem']} > 600 ? ROLE_ON : ROLE_OFF);   // 600: kuruluk eşiği, sensörünüze göre ayarlayın")
            elif self.cond:
                self.loop.append(f"digitalWrite({m}, ({' || '.join(self.cond)}) ? ROLE_ON : ROLE_OFF);")
            else:
                self.loop += ["static unsigned long tRl = 0;", "if (millis() - tRl >= 5000) {", "  tRl = millis();", f"  digitalWrite({m}, !digitalRead({m}));   // 5 sn'de bir aç/kapat", "}"]
        # motor (transistör/MOSFET sürülü)
        for m, pin in getattr(self, "motors", []):
            if self.esik_cond:
                self.loop.append(f"{'analogWrite' if self.pwm_ok(pin) else 'digitalWrite'}({m}, {self.esik_cond} ? {'255' if self.pwm_ok(pin) else 'HIGH'} : 0);   // eşik koşulunda çalışır")
            elif self.pwm_ok(pin):
                self.loop += ["static unsigned long tM = 0;", "unsigned long mg = (millis() - tM) % 4000;", f"analogWrite({m}, mg < 2000 ? 200 : 0);   // 2 sn dönsün (PWM hız), 2 sn dursun"]
            else:
                self.loop += [f"digitalWrite({m}, (millis() / 2000) % 2);   // 2 sn aç, 2 sn kapa"]
        # ekranlar
        if getattr(self, "lcd", False):
            self.loop.append("static unsigned long tLcd = 0;\nif (millis() - tLcd >= 500) {\n  tLcd = millis();\n  lcd.clear();")
            items = self.disp[:2] or [("Merhaba", None)]
            for n, (lb, ex) in enumerate(items):
                self.loop += [f"  lcd.setCursor(0, {n});", f"  lcd.print(\"{lb}: \");" + (f" lcd.print({ex});" if ex else "")]
            self.loop.append("}")
        if getattr(self, "oled", False):
            self.loop.append("static unsigned long tOled = 0;\nif (millis() - tOled >= 250) {\n  tOled = millis();\n  oled.clearDisplay(); oled.setCursor(0, 0); oled.setTextSize(1);")
            for lb, ex in self.disp[:4] or [("Merhaba", None)]:
                self.loop.append(f"  oled.print(\"{lb}: \");" + (f" oled.println({ex});" if ex else " oled.println();"))
            self.loop.append("  oled.display();\n}")
        if self.disp and not getattr(self, "lcd", False) and not getattr(self, "oled", False) or self.serial:
            self.serial = True
            if self.disp:
                pr = ["static unsigned long tPr = 0;", "if (millis() - tPr >= 500) {   // 500 ms'de bir seri monitöre yaz", "  tPr = millis();"]
                for lb, ex in self.disp[:6]:
                    pr.append(f"  Serial.print(\"{lb}: \"); Serial.print({ex}); Serial.print(\"   \");")
                pr += ["  Serial.println();", "}"]
                self.loop += pr
        elif self.disp:
            self.serial = False
        mn = self.m["part"]["ad"]
        head = [f"// Jarvis Elektronik Laboratuvarı: {ad or 'kart'}", f"// Kart: {mn}", f"// Üretilen parçalar: {', '.join(done) if done else 'yok'}"]
        if self.libs:
            head.append("// Gerekli kütüphaneler (Arduino IDE > Kütüphane Yöneticisi): " + "; ".join(self.libs))
        if self.kind == "esp32":
            head.append("// ESP32: Araçlar > Kart > ESP32 Dev Module seçin. Pinler 3,3 V mantıklıdır.")
        if self.kind in ("pico",):
            head.append("// Raspberry Pi Pico: Earle Philhower 'arduino-pico' çekirdeği ile derlenir.")
        if self.m["p"] in ("atmega328p", "attiny85"):
            head.append("// Çıplak çip: önyükleyici/ISP ile yükleyin; dahili osilatör ayarını (fuse) unutmayın. Pin numaraları Arduino eşlemesidir.")
        head.append("// Bu bir taslaktır: kendi devrenize göre eşikleri ve süreleri ayarlayın.")
        out = head + [""] + sorted(set(self.inc), key=self.inc.index) + ([""] if self.inc else [])
        out += ["// Pin tanımları"] + [d for d in self.defs] + [""]
        out += self.glob + ([""] if self.glob else [])
        out += ["void setup() {"]
        if self.serial or self.disp:
            out.append(f"  Serial.begin({self.baud});")
        out += ["  " + s for s in self.setup]
        if not self.setup and not self.serial:
            out.append("  // bu devrede kodla başlatılacak bir çıkış bulunamadı")
        out += ["}", "", "void loop() {"]
        for ln in self.loop:
            out += ["  " + x if x else "" for x in ln.split("\n")]
        if not self.loop:
            out.append("  // pinlere bağlı bilinen bir parça yok: önce parçaları MCU pinlerine bağlayın")
        out.append("}")
        if todo:
            out += [""] + todo
        return "\n".join(out) + "\n"


def kod_uret(kart):
    """(kod | None, neden). MCU yoksa neden döner."""
    A = Devre(kart)
    if not A.insts:
        return None, "Kart boş: önce bir mikrodenetleyici (ör. Arduino Uno) ve parçalar ekleyin."
    mi = A.primary_mcu()
    if mi is None:
        return None, "Kartta mikrodenetleyici yok (Arduino, ESP32, Pico...). Kod, bir MCU'nun pinlerine bağlı parçalardan üretilir. Bu devre mikrodenetleyicisiz çalışıyor olabilir."
    if not any((mi, p["ad"]) in A.conn for p in A.insts[mi]["part"]["pinler"] if p["tip"] in ("gc", "analog")):
        return None, f"{A.label(mi)} pinlerine hiçbir parça bağlı değil: önce parçaları pinlere bağlayın."
    k = Kod(A, mi)
    k.ipucu = kart.get("ipucu")
    return k.build(kart.get("ad") or "kart"), ""
