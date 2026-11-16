"""Elektronik Laboratuvarı: BLOK TABANLI KART KURUCU. Kullanıcı özelliği söyler ("Uno ile sıcaklığı ölçüp ekranda gösteren, 30 derecede fanı açan kart");
yerel LLM (ya da kural tabanlı yedek) YALNIZCA hangi blokların gerektiğini ve parametrelerini seçer, kablolamayı asla çizmez. Kablolama, pin ataması,
dirençler, güç hattı ve kod ipuçları bu modüldeki önceden doğrulanmış blok kurallarıyla, deterministik olarak yapılır.
Sözleşme: kur(plan, mcu) -> {"kart", "notlar", "mcu"}; sec(tarif) -> {"mcu", "bloklar", "soru", "notlar", "ipucu", "kaynak"}; katalog() sayfaya gider.
Yeni blok eklemek: aşağıdaki gibi `@_blok(...)` ile bir uret(ctx, p) işlevi yazın (parça kimlikleri elektronik_data.PARTS'tan, pin adları o parçanın
pinlerinden okunur); `python -c "import elektronik_bloklar as b; print(b.dogrula())"` boş liste vermelidir."""
import json
import re

import elektronik_analiz as an
from elektronik_data import PARTS, VF, fmt_ohm

try:
    from rapidfuzz import fuzz
except ImportError:                                # rapidfuzz yoksa difflib
    import difflib

    class fuzz:                                    # noqa: N801
        @staticmethod
        def ratio(a, b):
            return difflib.SequenceMatcher(None, a, b).ratio() * 100

_TR = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"})
_NUM = {"bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5, "alti": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10}
KATLAR = [("giris", "Giriş"), ("cikis", "Çıkış"), ("guc", "Güç")]
RENK_AD = {"kirmizi": "kırmızı", "yesil": "yeşil", "mavi": "mavi", "sari": "sarı", "beyaz": "beyaz", "turuncu": "turuncu"}


class BlokHata(Exception):
    """Kullanıcıya olduğu gibi söylenebilen kurulum hatası (pin tükendi, bilinmeyen blok...)."""


def fold(text):
    t = str(text).replace("İ", "i").replace("I", "ı").lower().translate(_TR)
    t = re.sub(r"['’`]\w*", "", t)
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)
    t = re.sub(r"[^a-z0-9.+\s]", " ", t)
    t = re.sub(r"(?<![0-9])\.|\.(?![0-9])", " ", t)
    return " ".join(t.split())


# ====================================================================== MİKRODENETLEYİCİLER
def _mcu(ad, part, v, v5, gnd, pool, pwm, adc, intr, i2c, spi=None, risky=(), inonly=(), ek_giris=(), lim5=450, lim33=50, ima=20, usb=""):
    return {"ad": ad, "part": part, "v": v, "v5": v5, "v33": "3V3", "gnd": list(gnd), "pool": list(pool), "pwm": set(pwm), "adc": list(adc), "intr": set(intr),
            "i2c": tuple(i2c), "spi": spi or {}, "risky": set(risky), "inonly": set(inonly), "ek_giris": list(ek_giris), "lim5": lim5, "lim33": lim33, "ima": ima, "usb": usb}


_UNO_POOL = [f"D{n}" for n in range(2, 14)] + [f"A{n}" for n in range(0, 6)]
MCULAR = {
    "uno": _mcu("Arduino Uno", "arduino_uno", 5.0, "5V", ["GND", "GND2", "GND3"], _UNO_POOL, ["D3", "D5", "D6", "D9", "D10", "D11"], [f"A{n}" for n in range(0, 6)],
                ["D2", "D3"], ("A4", "A5"), {"MOSI": "D11", "SCK": "D13"}),
    "nano": _mcu("Arduino Nano", "arduino_nano", 5.0, "5V", ["GND", "GND2"], _UNO_POOL, ["D3", "D5", "D6", "D9", "D10", "D11"], [f"A{n}" for n in (6, 7, 0, 1, 2, 3, 4, 5)],
                 ["D2", "D3"], ("A4", "A5"), {"MOSI": "D11", "SCK": "D13"}),
    "mega": _mcu("Arduino Mega 2560", "arduino_mega", 5.0, "5V", ["GND", "GND2"], [f"D{n}" for n in range(2, 20)] + [f"A{n}" for n in range(0, 10)] + ["D20", "D21"],
                 [f"D{n}" for n in range(2, 14)], [f"A{n}" for n in range(0, 10)], ["D2", "D3", "D18", "D19", "D20", "D21"], ("D20", "D21")),
    "esp32": _mcu("ESP32 DevKit", "esp32", 3.3, "VIN", ["GND", "GND2"], ["G13", "G14", "G25", "G26", "G27", "G32", "G33", "G4", "G16", "G17", "G18", "G19", "G23", "G5", "G21", "G22", "G2", "G15", "G12"],
                  ["G13", "G14", "G25", "G26", "G27", "G32", "G33", "G4", "G16", "G17", "G18", "G19", "G23", "G5", "G21", "G22", "G2", "G15", "G12"],
                  ["G36", "G39", "G34", "G35", "G32", "G33"],
                  ["G13", "G14", "G25", "G26", "G27", "G32", "G33", "G4", "G16", "G17", "G18", "G19", "G23", "G5", "G21", "G22"], ("G21", "G22"), {"MOSI": "G23", "SCK": "G18"},
                  risky=("G2", "G15", "G12"), inonly=("G34", "G35", "G36", "G39"), ek_giris=("G34", "G35", "G36", "G39"), lim33=300, ima=12, usb="VIN pini USB 5 V'unu verir; kart USB ile beslenmelidir"),
    "nodemcu": _mcu("NodeMCU (ESP8266)", "nodemcu", 3.3, "VIN", ["GND", "GND2"], ["D5", "D6", "D7", "D1", "D2", "D3", "D4", "D0", "D8"], ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"], ["A0"],
                    ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"], ("D2", "D1"), {"MOSI": "D7", "SCK": "D5"}, risky=("D3", "D4", "D8", "D0"), lim33=300, ima=12, usb="VIN pini USB 5 V'unu verir; kart USB ile beslenmelidir"),
    "pico": _mcu("Raspberry Pi Pico", "raspberry_pico", 3.3, "VBUS", ["GND", "GND2", "GND3", "GND4", "GND5", "GND6", "GND7", "GND8"],
                 ["GP2", "GP3", "GP6", "GP7", "GP8", "GP9", "GP10", "GP11", "GP12", "GP13", "GP14", "GP15", "GP16", "GP17", "GP18", "GP19", "GP20", "GP21", "GP22", "GP26", "GP27", "GP28", "GP4", "GP5", "GP0", "GP1"],
                 ["GP2", "GP3", "GP6", "GP7", "GP8", "GP9", "GP10", "GP11", "GP12", "GP13", "GP14", "GP15", "GP16", "GP17", "GP18", "GP19", "GP20", "GP21", "GP22", "GP26", "GP27", "GP28", "GP4", "GP5"],
                 ["GP26", "GP27", "GP28"], ["GP2", "GP3", "GP6", "GP7", "GP8", "GP9", "GP10", "GP11", "GP12", "GP13", "GP14", "GP15", "GP16", "GP17", "GP18", "GP19", "GP20", "GP21", "GP22"], ("GP4", "GP5"),
                 {"MOSI": "GP19", "SCK": "GP18"}, risky=("GP0", "GP1"), lim33=250, ima=12, usb="VBUS pini USB 5 V'unu verir; kart USB ile beslenmelidir"),
}
MCU_ADLAR = [{"id": k, "ad": v["ad"]} for k, v in MCULAR.items()]


# ====================================================================== KURUCU BAĞLAMI
def _vs(v):
    return f"{v:g}".replace(".", ",")


def _nat(p):
    m = re.match(r"([A-Za-z]+)(\d+)", p)
    return (m.group(1), int(m.group(2))) if m else (p, 0)


class Ctx:
    """Bir kartın kurulumu: parça/tel listesi, MCU pin ayırıcı, güç hatları, akım bütçesi, notlar."""

    def __init__(self, mcu):
        self.key = mcu
        self.m = MCULAR[mcu]
        self.parcalar, self.teller = [], []
        self.say = {}
        self.used, self.rez = set(), set()
        self.harita = {}
        self.notlar = []
        self.akim_l = []
        self.gi = 0
        self.pil_d = {}
        self.bridge = None
        self.i2c_say = {}
        self.mid = self.add(self.m["part"])

    # ---------------------------------------------------------------- parça / tel
    def add(self, pid, etiket=None, **ek):
        part = PARTS[pid]
        ref = part["ref"]
        if etiket is None:
            self.say[ref] = self.say.get(ref, 0) + 1
            etiket = f"{ref}{self.say[ref]}"
        i = f"p{len(self.parcalar) + 1}"
        d = {"i": i, "p": pid, "etiket": etiket}
        if part.get("degerler"):
            d["deger"] = part["varsayilan"]
        if part.get("renkler"):
            d["renk"] = part["renkler"][0]
        d.update({k: v for k, v in ek.items() if v is not None})
        self.parcalar.append(d)
        return i

    def etiket(self, i):
        return next(p["etiket"] for p in self.parcalar if p["i"] == i)

    def tel(self, a, pa, b, pb, tip="iz"):
        for i, pn in ((a, pa), (b, pb)):
            part = PARTS[next(p["p"] for p in self.parcalar if p["i"] == i)]
            if pn not in {x["ad"] for x in part["pinler"]}:
                raise BlokHata(f"Dahili hata: {part['ad']} parçasında '{pn}' pini yok.")
        self.teller.append({"a": [a, pa], "b": [b, pb], "tip": tip})

    def not_(self, s):
        if s not in self.notlar:
            self.notlar.append(s)

    # ---------------------------------------------------------------- güç hatları
    @property
    def mantik5(self):
        return self.m["v"] >= 4.5

    def hat5(self, i, pin, tip="iz"):
        """Parça pinini 5 V hattına bağlar (3,3 V kartlarda VIN/VBUS = USB 5 V)."""
        self.tel(i, pin, self.mid, self.m["v5"], tip)
        if not self.mantik5:
            self.not_(f"5 V hattı bu kartta {self.m['v5']} pininden gelir: {self.m['usb']}.")

    def hat33(self, i, pin, tip="iz"):
        self.tel(i, pin, self.mid, self.m["v33"], tip)

    def hat(self, i, pin, hat="mantik"):
        if hat == "5v" or (hat == "mantik" and self.mantik5):
            self.hat5(i, pin)
        else:
            self.hat33(i, pin)

    def gnd(self, i, pin, tip="iz"):
        g = self.m["gnd"]
        self.gi += 1
        self.tel(i, pin, self.mid, g[(self.gi - 1) // 3 % len(g)], tip)

    def pil(self, tur):
        """Ortak harici pil paketi (tur 'mot' = 6 V motor, 'mnt' = 4,5 V mantık); eksisi MCU toprağına bağlanır."""
        if tur not in self.pil_d:
            deger = "6V (4 pil)" if tur == "mot" else "4.5V (3 pil)"
            i = self.add("pil_aa", deger=deger)
            self.gnd(i, "-", "kablo")
            self.pil_d[tur] = i
            self.not_(f"Harici pil ({deger}): eksi ucu MCU GND'sine bağlı (ortak toprak). Artı ucu yalnızca ilgili yüke gider, MCU'ya bağlamayın.")
        return self.pil_d[tur]

    def guc(self, istenen, ma):
        """'oto' ise 5 V hattında yer varsa 5v, yoksa pil."""
        if istenen == "oto":
            return "5v" if self.toplam("5v") + ma <= 350 else "pil"
        return istenen

    def akim(self, ad, ma, hat="5v"):
        """hat: 5v | 3v3 | mantik | pil."""
        if hat == "mantik":
            hat = "5v" if self.mantik5 else "3v3"
        if hat == "5v" and not self.mantik5:
            hat = "5v"
        self.akim_l.append((ad, ma, hat))

    def toplam(self, hat):
        return sum(ma for _, ma, h in self.akim_l if h == hat)

    # ---------------------------------------------------------------- pin ayırıcı
    def _flex(self, p):
        m = self.m
        return (p in m["pwm"]) + (p in m["adc"]) + (p in m["intr"]) + (p in m["i2c"]) + (p in m["spi"].values())

    def rezerve(self, pinler):
        self.rez |= set(pinler)

    def pin(self, tur, ne):
        """tur: dijital | giris | pwm | analog | kesme. En az yetenekli boş pin önce verilir (esnek pinler sonraki bloklara kalır)."""
        m = self.m
        dolu = self.used | self.rez
        sira = {p: n for n, p in enumerate(m["pool"] + m["ek_giris"] + m["adc"])}
        if tur == "analog":
            cand = [p for p in m["adc"] if p not in dolu]
            yalniz = set(m["inonly"]) | {a for a in m["adc"] if a not in m["pool"]}             # yalnızca analog okunabilen pinler önce kullanılır
            key = lambda p: (p not in yalniz, self._flex(p), sira.get(p, 99))                       # noqa: E731
        elif tur == "pwm":
            cand = [p for p in m["pool"] if p in m["pwm"] and p not in dolu and p not in m["inonly"]]
            key = lambda p: (p in m["risky"], self._flex(p), sira[p])                                        # noqa: E731
        elif tur == "kesme":
            cand = [p for p in m["pool"] if p in m["intr"] and p not in dolu and p not in m["inonly"]]
            key = lambda p: (p in m["risky"], self._flex(p), sira[p])                                        # noqa: E731
            if not cand:
                self.not_("Kesme destekli boş pin kalmadı; sinyal yoklama (polling) ile okunur.")
                return self.pin("dijital", ne)
        else:
            cand = [p for p in m["pool"] if p not in dolu and p not in m["inonly"]]
            if tur == "giris":
                cand += [p for p in m["ek_giris"] if p not in dolu]
            key = lambda p: (p in m["risky"], p not in m["inonly"], self._flex(p), sira[p])                  # noqa: E731
        if not cand:
            oneri = {"uno": "Arduino Mega ya da ESP32", "nano": "Arduino Mega ya da ESP32", "nodemcu": "ESP32 ya da Arduino Mega", "pico": "ESP32 ya da Arduino Mega"}.get(self.key)
            raise BlokHata(f"{ne} için boş {tur} pini kalmadı ({m['ad']})." + (f" Daha çok pini olan {oneri} seçin ya da bazı blokları çıkarın." if oneri else " Bazı blokları çıkarın."))
        p = sorted(cand, key=key)[0]
        self.used.add(p)
        self.harita[p] = ne
        return p

    def sabit(self, pinler, ne):
        for p in pinler:
            self.used.add(p)
            self.harita[p] = ne

    # ---------------------------------------------------------------- I2C hattı
    def i2c_oku(self):
        sda, scl = self.m["i2c"]
        return sda, scl

    def i2c(self, i, ihtiyac="her", ad=""):
        """Parçanın SDA/SCL pinlerini ortak I2C hattına bağlar. ihtiyac: her | 5v | 3v3; mantık gerilimi uyuşmazsa seviye dönüştürücü eklenir."""
        sda, scl = self.m["i2c"]
        self.sabit([sda, scl], "I2C hattı (SDA/SCL, ortak)")
        uyusmaz = (ihtiyac == "5v" and not self.mantik5) or (ihtiyac == "3v3" and self.mantik5)
        if not uyusmaz:
            self.tel(i, "SDA", self.mid, sda)
            self.tel(i, "SCL", self.mid, scl)
        else:
            if self.bridge is None:
                b = self.add("seviye_donusturucu")
                self.hat33(b, "LV")
                self.hat5(b, "HV")
                self.gnd(b, "GND")
                self.tel(b, "LV1" if not self.mantik5 else "HV1", self.mid, sda)
                self.tel(b, "LV2" if not self.mantik5 else "HV2", self.mid, scl)
                self.bridge = b
                self.not_(f"I2C seviye dönüştürücü ({self.etiket(b)}) eklendi: {self.m['ad']} {_vs(self.m['v'])} V, bağlı modül {'5 V' if ihtiyac == '5v' else '3,3 V'} gerektiriyor.")
            b = self.bridge
            yan = ("HV1", "HV2") if not self.mantik5 else ("LV1", "LV2")
            self.tel(i, "SDA", b, yan[0])
            self.tel(i, "SCL", b, yan[1])
        self.i2c_say[ad] = self.i2c_say.get(ad, 0) + 1
        if ad and ad != "MPU6050" and self.i2c_say[ad] == 2:
            self.not_(f"Uyarı: iki {ad} aynı I2C adresini kullanır; ikincisi için adres seçici (jumper) ya da farklı model gerekir.")


# ====================================================================== BLOK TANIMI
BLOKLAR = {}


def _sayi(ad, etiket, v, mn, mx):
    return {"ad": ad, "tip": "sayi", "etiket": etiket, "varsayilan": v, "min": mn, "max": mx}


def _sec(ad, etiket, v, secenekler):
    return {"ad": ad, "tip": "secim", "etiket": etiket, "varsayilan": v, "secenekler": list(secenekler)}


_GUC = _sec("guc", "Besleme", "oto", ["oto", "5v", "pil"])


def _blok(id, ad, kat, acik, parcalar, pinler, param=(), kw="", kisa=None):
    def dec(fn):
        BLOKLAR[id] = {"id": id, "ad": ad, "kat": kat, "acik": acik, "param": list(param), "parcalar": list(parcalar), "pinler": dict(pinler), "uret": fn,
                       "kw": re.compile(kw) if kw else None, "kisa": kisa or ad}
        return fn
    return dec


def param_dogrula(b, p):
    """Sayfadan/LLM'den gelen parametreleri doğrular: bilinmeyenleri atar, sınırlar, geçersizi varsayılana çeker."""
    p = p if isinstance(p, dict) else {}
    out = {}
    for sp in b["param"]:
        v = p.get(sp["ad"], sp["varsayilan"])
        if sp["tip"] == "sayi":
            try:
                v = int(round(float(str(v).replace(",", "."))))
            except (TypeError, ValueError):
                v = sp["varsayilan"]
            v = max(sp["min"], min(sp["max"], v))
        elif sp["tip"] == "secim":
            fv = fold(v)
            eslesen = next((s for s in sp["secenekler"] if fold(s) == fv), None)
            v = eslesen if eslesen is not None else sp["varsayilan"]
        else:
            v = str(v)[:40]
        out[sp["ad"]] = v
    return out


def _ozet(b, p):
    parts = []
    for sp in b["param"]:
        v = p.get(sp["ad"])
        if v in (None, ""):
            continue
        if sp["ad"] == "adet":
            parts.append(f"{v} adet")
        elif sp["tip"] == "secim" and v == sp["varsayilan"] and sp["ad"] not in ("renk", "tur"):
            continue                                    # varsayılan seçimler (oto besleme gibi) özette gösterilmez
        else:
            parts.append(RENK_AD.get(v, str(v)))
    return b["ad"] + (" — " + ", ".join(parts) if parts else "")


def _r_led(c, renk, ma=None):
    V = c.m["v"]
    I = 0.015 if V >= 4.5 else 0.010
    r = max((V - VF.get(renk, 2.0)) / I, 100.0)
    return fmt_ohm(an.e12_up(r))


# ====================================================================== GİRİŞ BLOKLARI
@_blok("buton", "Buton", "giris", "Basınca pine LOW verir (INPUT_PULLUP, harici direnç gerekmez).", ["buton"], {"dijital": 1}, [_sayi("adet", "Adet", 1, 1, 4)],
       r"\b(buton\w*|dugme\w*|dugmeli|tus)\b", "Buton")
def _u_buton(c, p):
    for n in range(p["adet"]):
        b = c.add("buton")
        pin = c.pin("dijital", f"{c.etiket(b)} (buton, INPUT_PULLUP)")
        c.tel(b, "1", c.mid, pin)
        c.gnd(b, "2")
    c.not_("Buton: kodda pinMode(..., INPUT_PULLUP) kullanılır; basılınca LOW okunur.")


@_blok("potansiyometre", "Potansiyometre", "giris", "Döndürülünce 0-1023 arası analog değer verir (ayar düğmesi).", ["potansiyometre"], {"analog": 1}, [_sayi("adet", "Adet", 1, 1, 3)],
       r"potansiyometre\w*|\bpot\w*\b|\bknob\b|ayarlanabilir", "Pot")
def _u_pot(c, p):
    for n in range(p["adet"]):
        r = c.add("potansiyometre")
        c.hat(r, "1", "mantik")
        pin = c.pin("analog", f"{c.etiket(r)} orta uç (analog)")
        c.tel(r, "W", c.mid, pin)
        c.gnd(r, "2")


@_blok("ldr", "LDR ışık ölçümü", "giris", "Ortam ışığını ölçer (LDR + 10 kΩ gerilim bölücü, analog giriş).", ["ldr", "direnc"], {"analog": 1}, [],
       r"\bldr\b|isik (sensor|olc|seviye|algila|siddet)\w*|isigi (olc|algila)\w*|karanlik|aydinlik|gece lambasi|gunes isigi|\blux\b|isik algila\w*", "Işık")
def _u_ldr(c, p):
    l = c.add("ldr")
    r = c.add("direnc", deger="10kΩ")
    c.hat(l, "1", "mantik")
    pin = c.pin("analog", f"{c.etiket(l)} bölücü ortası (analog)")
    c.tel(l, "2", r, "1")
    c.tel(l, "2", c.mid, pin)
    c.gnd(r, "2")
    c.akim("LDR", 1, "mantik")


@_blok("dht", "Sıcaklık-nem (DHT)", "giris", "Sıcaklık ve nemi tek telle ölçer; DHT11 ucuz, DHT22 daha hassas.", ["dht11", "dht22"], {"dijital": 1}, [_sec("tur", "Model", "dht22", ["dht22", "dht11"])],
       r"\bdht\s?(11|22)?\b|sicak\w*|derece\w*|termometre|\bisi(yi)?\b|\bnem(i|li|ler|ini)?\b|hava durumu|hava istasyon\w*", "Sıcaklık")
def _u_dht(c, p):
    d = c.add(p["tur"])
    c.hat(d, "VCC", "mantik")
    c.gnd(d, "GND")
    pin = c.pin("dijital", f"{c.etiket(d)} DATA (sıcaklık-nem)")
    c.tel(d, "DATA", c.mid, pin)
    c.akim(p["tur"].upper(), 2, "mantik")
    c.not_("DHT: Adafruit DHT kütüphanesi gerekir; DHT22 en fazla 2 sn'de bir okunur.")


@_blok("lm35", "LM35 sıcaklık", "giris", "Sıcaklığı 10 mV/°C gerilimle verir (analog, 4-30 V besleme).", ["lm35"], {"analog": 1}, [], r"\blm\s?35\b", "LM35")
def _u_lm35(c, p):
    s = c.add("lm35")
    c.hat5(s, "VCC")
    c.gnd(s, "GND")
    pin = c.pin("analog", f"{c.etiket(s)} OUT (analog)")
    c.tel(s, "OUT", c.mid, pin)
    c.akim("LM35", 1, "5v")
    if not c.mantik5:
        c.not_("LM35 3,3 V ADC ile 0-330 °C ölçebilir ama çözünürlük düşüktür; ADC referansı 3,3 V alınır.")


@_blok("ds18b20", "DS18B20 sıcaklık", "giris", "Tek telli dijital, suya dayanıklı versiyonu olan sıcaklık sensörü (4,7 kΩ pull-up'lı).", ["ds18b20", "direnc"], {"dijital": 1}, [],
       r"\bds\s?18b20\b|\bds18\w*|su sicakli\w*|suya dayanikli|havuz|akvaryum|sivi sicakli\w*", "DS18B20")
def _u_ds(c, p):
    s = c.add("ds18b20")
    r = c.add("direnc", deger="4.7kΩ")
    c.hat(s, "VDD", "mantik")
    c.gnd(s, "GND")
    pin = c.pin("dijital", f"{c.etiket(s)} DQ (1-Wire)")
    c.tel(r, "1", s, "VDD")
    c.tel(r, "2", s, "DQ")
    c.tel(s, "DQ", c.mid, pin)
    c.akim("DS18B20", 1, "mantik")


@_blok("hcsr04", "HC-SR04 mesafe", "giris", "Ultrasonik mesafe ölçer (2-400 cm). 3,3 V kartlarda ECHO gerilim bölücüyle indirilir.", ["hcsr04", "direnc"], {"dijital": 1, "giris": 1}, [],
       r"hc\s?sr\s?04|\bsr04\b|ultrasonik|mesafe\w*|uzaklik\w*|park (sensor|et)\w*|engel (algila|sensor)\w*|\d+\s?(cm|santim\w*)\b", "Mesafe")
def _u_hc(c, p):
    s = c.add("hcsr04")
    c.hat5(s, "VCC")
    c.gnd(s, "GND")
    t = c.pin("dijital", f"{c.etiket(s)} TRIG")
    c.tel(s, "TRIG", c.mid, t)
    e = c.pin("giris", f"{c.etiket(s)} ECHO")
    if c.mantik5:
        c.tel(s, "ECHO", c.mid, e)
    else:
        r1, r2 = c.add("direnc", deger="1kΩ"), c.add("direnc", deger="1.8kΩ")
        c.tel(s, "ECHO", r1, "1")
        c.tel(r1, "2", r2, "1")
        c.tel(r1, "2", c.mid, e)
        c.gnd(r2, "2")
        c.not_(f"HC-SR04 ECHO çıkışı 5 V'tur: {c.etiket(r1)} (1 kΩ) + {c.etiket(r2)} (1,8 kΩ) gerilim bölücü ile ≈3,2 V'a indirildi.")
    c.akim("HC-SR04", 15, "5v")


@_blok("pir", "PIR hareket", "giris", "İnsan hareketini algılar; hareket varken çıkış HIGH olur (ilk dakika ısınır).", ["pir"], {"giris": 1}, [],
       r"\bpir\b|hareket\w*|hirsiz\w*|birisi (girince|gecince|yaklasinca)|insan (algila|var)\w*|presence", "Hareket")
def _u_pir(c, p):
    s = c.add("pir")
    c.hat5(s, "VCC")
    c.gnd(s, "GND")
    pin = c.pin("giris", f"{c.etiket(s)} OUT (hareket)")
    c.tel(s, "OUT", c.mid, pin)
    c.akim("PIR", 1, "5v")


@_blok("toprak_nem", "Toprak nemi", "giris", "Toprağın ıslaklığını analog okur (kuru: yüksek değer, ıslak: düşük).", ["toprak_nem"], {"analog": 1}, [],
       r"toprak\w*|bitki\w*|saksi\w*|cicek\w*|sulama\w*", "Toprak nemi")
def _u_toprak(c, p):
    s = c.add("toprak_nem")
    c.hat(s, "VCC", "mantik")
    c.gnd(s, "GND")
    pin = c.pin("analog", f"{c.etiket(s)} AO (nem)")
    c.tel(s, "AO", c.mid, pin)
    c.akim("Toprak nemi", 5, "mantik")


@_blok("mq2", "MQ-2 gaz/duman", "giris", "Duman, LPG ve metan algılar (analog, ısınma ~20 sn, ~150 mA).", ["mq2", "direnc"], {"analog": 1}, [],
       r"\bmq\s?-?2\b|\bgaz\w*|duman\w*|yangin\w*|\blpg\b|metan|kacak", "Gaz")
def _u_mq2(c, p):
    s = c.add("mq2")
    c.hat5(s, "VCC")
    c.gnd(s, "GND")
    pin = c.pin("analog", f"{c.etiket(s)} AO (gaz)")
    if c.mantik5:
        c.tel(s, "AO", c.mid, pin)
    else:
        r1, r2 = c.add("direnc", deger="12kΩ"), c.add("direnc", deger="22kΩ")
        c.tel(s, "AO", r1, "1")
        c.tel(r1, "2", r2, "1")
        c.tel(r1, "2", c.mid, pin)
        c.gnd(r2, "2")
        c.not_(f"MQ-2 AO çıkışı 5 V'a çıkabilir: {c.etiket(r1)} (12 kΩ) + {c.etiket(r2)} (22 kΩ) bölücü ile ≈3,2 V'a indirildi.")
    c.akim("MQ-2", 150, "5v")
    c.not_("MQ-2 ısınırken (~20 sn) değerler kararsızdır; eşiği kendi ortamınıza göre ayarlayın.")


@_blok("joystick", "Joystick", "giris", "İki eksen analog + basma düğmesi.", ["joystick"], {"analog": 2, "dijital": 1}, [],
       r"joy\s?stick\w*|analog kol|oyun kolu", "Joystick")
def _u_joy(c, p):
    j = c.add("joystick")
    c.hat(j, "VCC", "mantik")
    c.gnd(j, "GND")
    for ax in ("VRX", "VRY"):
        pin = c.pin("analog", f"{c.etiket(j)} {ax}")
        c.tel(j, ax, c.mid, pin)
    pin = c.pin("dijital", f"{c.etiket(j)} SW (buton, INPUT_PULLUP)")
    c.tel(j, "SW", c.mid, pin)
    c.akim("Joystick", 3, "mantik")


@_blok("enkoder", "Döner enkoder", "giris", "Sonsuz dönen düğme + basma tuşu (KY-040).", ["enkoder"], {"kesme": 1, "dijital": 2}, [],
       r"enkoder\w*|encoder\w*|rotary|doner (dugme|anahtar|kodlayici)\w*", "Enkoder")
def _u_enk(c, p):
    e = c.add("enkoder")
    c.hat(e, "VCC", "mantik")
    c.gnd(e, "GND")
    pin = c.pin("kesme", f"{c.etiket(e)} CLK")
    c.tel(e, "CLK", c.mid, pin)
    pin = c.pin("dijital", f"{c.etiket(e)} DT")
    c.tel(e, "DT", c.mid, pin)
    pin = c.pin("dijital", f"{c.etiket(e)} SW (INPUT_PULLUP)")
    c.tel(e, "SW", c.mid, pin)
    c.akim("Enkoder", 2, "mantik")


@_blok("ir_alici", "IR alıcı (kumanda)", "giris", "Uzaktan kumanda sinyalini okur (VS1838).", ["ir_alici"], {"giris": 1}, [],
       r"kumanda\w*|\bir alici\w*|kizilotesi|infrared", "IR")
def _u_ir(c, p):
    s = c.add("ir_alici")
    c.hat(s, "VCC", "mantik")
    c.gnd(s, "GND")
    pin = c.pin("giris", f"{c.etiket(s)} OUT (IR)")
    c.tel(s, "OUT", c.mid, pin)
    c.akim("IR alıcı", 3, "mantik")
    c.not_("IR alıcı: IRremote kütüphanesi gerekir.")


@_blok("ses", "Ses sensörü (mikrofon)", "giris", "Ses şiddetini ölçer/algılar (KY-038). Analog ya da eşikli dijital çıkış seçilir.", ["mikrofon"], {"analog": 1}, [_sec("cikis", "Çıkış", "analog", ["analog", "dijital"])],
       r"mikrofon\w*|alkis\w*|gurultu\w*|bagir\w*|ses (sensor|seviye|siddet|algila|olc|duy)\w*|sesi (algila|olc|duy|dinle)\w*|sese tepki|sesle", "Ses")
def _u_ses(c, p):
    s = c.add("mikrofon")
    c.hat(s, "VCC", "mantik")
    c.gnd(s, "GND")
    if p["cikis"] == "analog":
        pin = c.pin("analog", f"{c.etiket(s)} AO (ses)")
        c.tel(s, "AO", c.mid, pin)
    else:
        pin = c.pin("giris", f"{c.etiket(s)} DO (ses eşiği)")
        c.tel(s, "DO", c.mid, pin)
    c.akim("Mikrofon", 4, "mantik")


@_blok("mpu6050", "MPU6050 ivme/jiroskop", "giris", "3 eksen ivme + 3 eksen dönüş ölçer (I2C).", ["mpu6050"], {"i2c": 1}, [],
       r"mpu\s?-?6050|ivme\w*|jiroskop\w*|gyro\w*|egim\w*|sallan\w*|denge\w*", "İvme")
def _u_mpu(c, p):
    m = c.add("mpu6050")
    c.hat(m, "VCC", "mantik")
    c.gnd(m, "GND")
    c.i2c(m, "her", "MPU6050")
    if c.i2c_say.get("MPU6050", 0) == 2:
        c.hat33(m, "AD0")
        c.not_(f"İkinci MPU6050 ({c.etiket(m)}): AD0 pini 3V3'e bağlandı, adresi 0x69 oldu.")
    c.akim("MPU6050", 4, "mantik")
    c.not_("MPU6050: Adafruit MPU6050 kütüphanesi gerekir.")


@_blok("bmp280", "BMP280 basınç", "giris", "Basınç ve sıcaklık ölçer (I2C, YALNIZCA 3,3 V).", ["bmp280"], {"i2c": 1}, [],
       r"bmp\s?-?280|basinc\w*|barometre|yukseklik\w*|rakim|irtifa", "Basınç")
def _u_bmp(c, p):
    b = c.add("bmp280")
    c.hat33(b, "VCC")
    c.gnd(b, "GND")
    c.i2c(b, "3v3", "BMP280")
    c.akim("BMP280", 1, "3v3")
    c.not_("BMP280 yalnızca 3,3 V'tur: VCC 3V3 pinine bağlandı" + (" ve I2C hattı seviye dönüştürücüden geçti." if c.mantik5 else "."))


# ====================================================================== ÇIKIŞ BLOKLARI
_RENK_SEC = ["kirmizi", "yesil", "mavi", "sari", "beyaz", "turuncu"]


@_blok("led", "LED + ön direnç", "cikis", "LED'ler pine ön dirençle bağlanır (direnç renge ve kart gerilimine göre hesaplanır).", ["led", "direnc"], {"dijital": 1},
       [_sayi("adet", "Adet", 1, 1, 6), _sec("renk", "Renk", "kirmizi", _RENK_SEC)], r"\bled\w*|lamba\w*|isik yak\w*|isiklar yan\w*|aydinlat\w*|ikaz\w*", "LED")
def _u_led(c, p):
    rv = _r_led(c, p["renk"])
    for n in range(p["adet"]):
        l = c.add("led", renk=p["renk"])
        r = c.add("direnc", deger=rv)
        pin = c.pin("dijital", f"{c.etiket(l)} ({RENK_AD[p['renk']]}, {rv} direnç)")
        c.tel(c.mid, pin, r, "1")
        c.tel(r, "2", l, "A")
        c.gnd(l, "K")
        c.akim("LED", 10, "pin")
    if not c.mantik5 and p["renk"] in ("mavi", "beyaz"):
        c.not_(f"Uyarı: mavi/beyaz LED'in ileri gerilimi (≈3,2 V) {_vs(c.m['v'])} V'a çok yakın; sönük yanar. Kırmızı/yeşil/sarı seçmeniz önerilir.")


@_blok("rgb_led", "RGB LED", "cikis", "Ortak katotlu RGB LED: 3 PWM pini + 3 ön direnç ile her renk karışımı.", ["rgb_led", "direnc"], {"pwm": 3}, [],
       r"\brgb\b(\s+(led|lamba|isik)\w*)?|renkli led\w*|renk degistir\w*(\s+(lamba|led)\w*)?|renk gecis\w*(\s+(lamba|led)\w*)?", "RGB")
def _u_rgb(c, p):
    l = c.add("rgb_led")
    vf = {"R": 2.0, "G": 3.0, "B": 3.2}
    V = c.m["v"]
    I = 0.015 if V >= 4.5 else 0.010
    for ch in ("R", "G", "B"):
        rv = fmt_ohm(an.e12_up(max((V - vf[ch]) / I, 100.0)))
        r = c.add("direnc", deger=rv)
        pin = c.pin("pwm", f"{c.etiket(l)} {ch} ({rv} direnç, PWM)")
        c.tel(c.mid, pin, r, "1")
        c.tel(r, "2", l, ch)
        c.akim("RGB kanal", 10, "pin")
    c.gnd(l, "K")


@_blok("trafik", "Trafik lambası", "cikis", "Kırmızı, sarı ve yeşil LED sırayla yanar (3 LED + 3 direnç).", ["led", "direnc"], {"dijital": 3}, [],
       r"trafik\w*(\s+(lamba|isik)\w*)?", "Trafik")
def _u_trafik(c, p):
    for renk in ("kirmizi", "sari", "yesil"):
        rv = _r_led(c, renk)
        l = c.add("led", renk=renk)
        r = c.add("direnc", deger=rv)
        pin = c.pin("dijital", f"{c.etiket(l)} ({RENK_AD[renk]}, trafik lambası)")
        c.tel(c.mid, pin, r, "1")
        c.tel(r, "2", l, "A")
        c.gnd(l, "K")
        c.akim("LED", 10, "pin")


@_blok("buzzer", "Buzzer", "cikis", "Alarm/bip sesi çıkarır. Aktif buzzer sabit tonda öter, pasif buzzer tone() ile melodi çalar.", ["buzzer"], {"dijital": 1},
       [_sec("tur", "Tür", "pasif", ["pasif", "aktif"])], r"buzzer\w*|alarm\w*|\bbip\w*|siren\w*|korna\w*|uyari ses\w*|sesli (uyari|alarm)\w*|ses cikar\w*|calsin|melodi\w*|\bzil\b|\bot(er|sun)\b|muzik cal\w*", "Buzzer")
def _u_buzzer(c, p):
    z = c.add("buzzer")
    pin = c.pin("dijital", f"{c.etiket(z)} ({p['tur']} buzzer)")
    c.tel(z, "+", c.mid, pin)
    c.gnd(z, "-")
    c.akim("Buzzer", 15, "pin")
    if p["tur"] == "aktif":
        c.not_("Aktif buzzer pini HIGH yapınca öter (tone() yerine digitalWrite de kullanılabilir).")


def _surucu_motor(c, yuk, hat, tur, ne):
    """Düşük taraf anahtarlı motor/fan sürücüsü: pin → (direnç) → MOSFET/transistör; geri tepme diyotu; yük gerilimi 5V hattından ya da harici pilden."""
    if tur == "mosfet":
        q = c.add("mosfet_n")
        pin = c.pin("pwm", f"{ne} sürücü kapısı (PWM, {c.etiket(q)})")
        rg = c.add("direnc", deger="220Ω")
        rp = c.add("direnc", deger="10kΩ")
        c.tel(c.mid, pin, rg, "1")
        c.tel(rg, "2", q, "G")
        c.tel(q, "G", rp, "1")
        c.gnd(rp, "2")
        c.gnd(q, "S")
        d_pin, s_pin = "D", "S"
    else:
        q = c.add("transistor_npn")
        pin = c.pin("pwm", f"{ne} sürücü tabanı (PWM, {c.etiket(q)})")
        rb = c.add("direnc", deger="1kΩ")
        c.tel(c.mid, pin, rb, "1")
        c.tel(rb, "2", q, "B")
        c.gnd(q, "E")
        d_pin = "C"
    d = c.add("diyot")
    c.tel(yuk, "-", q, d_pin)
    c.tel(d, "A", q, d_pin)
    if hat == "pil":
        pil = c.pil("mot")
        c.tel(yuk, "+", pil, "+", "kablo")
        c.tel(d, "K", pil, "+", "kablo")
    else:
        c.hat5(yuk, "+")
        c.hat5(d, "K")
    return q


@_blok("dc_motor", "DC motor", "cikis", "DC motoru MOSFET/transistörle (geri tepme diyotlu) sürer; PWM ile hız. Ayrı pil ya da 5 V hattı.", ["dc_motor", "mosfet_n", "transistor_npn", "diyot", "direnc", "pil_aa"], {"pwm": 1},
       [_GUC, _sec("surucu", "Sürücü", "mosfet", ["mosfet", "transistor"])], r"\bmotor\w*|pervane\w*|tekerlek\w*", "Motor")
def _u_motor(c, p):
    m = c.add("dc_motor")
    hat = c.guc(p["guc"] if p["guc"] != "oto" else "pil", 250)
    _surucu_motor(c, m, hat, p["surucu"], c.etiket(m))
    c.akim("DC motor", 250, "5v" if hat == "5v" else "pil")
    c.not_("DC motor: Arduino pininden doğrudan değil, " + ("MOSFET (IRLZ44N)" if p["surucu"] == "mosfet" else "BC547 (≤100 mA)") + " üzerinden sürülür; diyot geri tepmeyi engeller."
           + (" 5 V pininden beslenen motor kartı resetleyebilir; sorun olursa guc=pil seçin." if hat == "5v" else ""))


@_blok("fan", "Fan", "cikis", "5 V küçük fan, MOSFET ile PWM'li sürülür (ısıtıcı/soğutucu uygulamaları).", ["dc_motor", "mosfet_n", "diyot", "direnc", "pil_aa"], {"pwm": 1},
       [_GUC], r"\bfan\w*|vantilator\w*|sogutucu\w*|sogutma\w*|havalandirma\w*", "Fan")
def _u_fan(c, p):
    m = c.add("dc_motor", etiket=f"FAN{sum(1 for x in c.parcalar if x['etiket'].startswith('FAN')) + 1}")
    hat = c.guc("5v" if p["guc"] == "oto" else p["guc"], 150)
    _surucu_motor(c, m, hat, "mosfet", c.etiket(m))
    c.akim("Fan", 150, "5v" if hat == "5v" else "pil")
    if hat == "pil":
        c.not_("Fan harici pilden beslenir (5 V hattı yetmiyor ya da seçildi); fanın gerilimi pile uygun olmalı (6 V pil için 5-6 V fan).")


@_blok("servo", "Servo motor", "cikis", "0-180° dönen servo (SG90). Sinyal PWM pininden, güç 5 V hattından ya da ayrı pilden.", ["servo", "pil_aa"], {"pwm": 1},
       [_sayi("adet", "Adet", 1, 1, 3), _GUC], r"servo\w*|kapi (ac|kilit)\w*|\bkilit\w*", "Servo")
def _u_servo(c, p):
    ist = p["guc"] if p["guc"] != "oto" else ("5v" if p["adet"] == 1 else "pil")
    hat = c.guc(ist, 150 * p["adet"])
    for n in range(p["adet"]):
        s = c.add("servo")
        c.gnd(s, "GND")
        if hat == "pil":
            c.tel(s, "VCC", c.pil("mot"), "+", "kablo")
        else:
            c.hat5(s, "VCC")
        pin = c.pin("pwm", f"{c.etiket(s)} SIG (servo)")
        c.tel(s, "SIG", c.mid, pin)
        c.akim("Servo", 150, "5v" if hat == "5v" else "pil")
    if hat == "pil":
        c.not_("Servo harici pilden (6 V, 4×AA) beslenir; SG90 için 4,8-6 V uygundur.")


@_blok("step_motor", "Step motor", "cikis", "28BYJ-48 step motor + ULN2003 sürücü kartı (4 yön pini).", ["step_motor", "pil_aa"], {"dijital": 4}, [_GUC],
       r"step\s?motor\w*|adim\w* motor\w*|stepper\w*|28byj|adimli motor", "Step motor")
def _u_step(c, p):
    hat = c.guc("5v" if p["guc"] == "oto" else p["guc"], 240)
    s = c.add("step_motor")
    c.gnd(s, "GND")
    if hat == "pil":
        c.tel(s, "VCC", c.pil("mot"), "+", "kablo")
    else:
        c.hat5(s, "VCC")
    for n in range(1, 5):
        pin = c.pin("dijital", f"{c.etiket(s)} IN{n}")
        c.tel(s, f"IN{n}", c.mid, pin)
    c.akim("Step motor", 240, "5v" if hat == "5v" else "pil")
    c.not_("Step motor: Stepper kütüphanesi ile (IN1, IN3, IN2, IN4 sırası) sürülür; ~240 mA çeker.")


@_blok("titresim", "Titreşim motoru", "cikis", "Telefon gibi titreşim; BC547 transistör + geri tepme diyotu ile sürülür.", ["titresim_motoru", "transistor_npn", "diyot", "direnc"], {"pwm": 1}, [],
       r"titresim\w*|vibrasyon\w*|vibrator\w*", "Titreşim")
def _u_titresim(c, p):
    m = c.add("titresim_motoru")
    _surucu_motor(c, m, "5v", "transistor", c.etiket(m))
    c.akim("Titreşim motoru", 85, "5v")
    c.not_("Titreşim motoru 5 V hattından beslenir; 3 V'luk motor ise PWM ile kısın ya da 3V3 hattına alın.")


@_blok("role", "Röle modülü", "cikis", "Küçük sinyalle başka devreyi açıp kapatır (pompa, lamba). Yük klemense bağlanır: COM-NO.", ["role", "klemens"], {"dijital": 1}, [],
       r"\brole\w*|pompa\w*|selenoid\w*|solenoid\w*|valf\w*|\bvana\b|230 ?v|sebeke\w*|\bpriz\w*|cihaz\w* (ac|kapat)\w*|elektrikli alet", "Röle")
def _u_role(c, p):
    r = c.add("role")
    k = c.add("klemens")
    c.hat5(r, "VCC")
    c.gnd(r, "GND")
    pin = c.pin("dijital", f"{c.etiket(r)} IN (röle)")
    c.tel(r, "IN", c.mid, pin)
    c.tel(r, "COM", k, "1")
    c.tel(r, "NO", k, "2")
    c.akim("Röle", 75, "5v")
    c.not_(f"Röle yükü {c.etiket(k)} klemensindedir (COM-NO). Şebeke gerilimini (230 V) bu modelle denemeyin; yalnızca düşük gerilim.")


@_blok("yedi_segment", "7 segment gösterge", "cikis", "Tek haneli rakam göstergesi (ortak katot); 7 segment için 7 pin + 7 direnç.", ["yedi_segment", "direnc"], {"dijital": 7}, [],
       r"7 ?segment\w*|yedi segment\w*|segment\w*|rakam gost\w*", "7 segment")
def _u_seg(c, p):
    d = c.add("yedi_segment")
    rv = fmt_ohm(an.e12_up(max((c.m["v"] - 2.0) / (0.010), 100.0)))
    for s in "ABCDEFG":
        r = c.add("direnc", deger=rv)
        pin = c.pin("dijital", f"{c.etiket(d)} segment {s} ({rv} direnç)")
        c.tel(c.mid, pin, r, "1")
        c.tel(r, "2", d, s)
        c.akim("Segment", 10, "pin")
    c.gnd(d, "COM")
    c.not_("7 segment 7 dijital pin harcar; pin sıkıntısı varsa 74HC595 ya da TM1637 kullanın.")


@_blok("lcd1602", "LCD 16x2 (I2C)", "cikis", "2 satır 16 karakter yazı ekranı (I2C arka kart, 5 V).", ["lcd1602", "seviye_donusturucu"], {"i2c": 1}, [],
       r"\blcd\w*|16 ?x ?2|1602", "LCD")
def _u_lcd(c, p):
    l = c.add("lcd1602")
    c.hat5(l, "VCC")
    c.gnd(l, "GND")
    c.i2c(l, "5v", "LCD1602")
    c.akim("LCD1602", 25, "5v")
    c.not_("LCD1602: LiquidCrystal_I2C kütüphanesi; adres 0x27 (olmazsa 0x3F).")


@_blok("oled", "OLED ekran (I2C)", "cikis", "0,96\" 128x64 küçük ekran (SSD1306, I2C, 3,3-5 V).", ["oled"], {"i2c": 1}, [],
       r"\boled\w*|ssd1306|ekran\w*|display\w*|gosterge\w*|\bgoster\w*|yazdir\w*", "Ekran")
def _u_oled(c, p):
    o = c.add("oled")
    c.hat(o, "VCC", "mantik")
    c.gnd(o, "GND")
    c.i2c(o, "her", "OLED")
    c.akim("OLED", 10, "mantik")
    c.not_("OLED: Adafruit SSD1306 + GFX kütüphaneleri; adres 0x3C.")


@_blok("neopixel", "NeoPixel şerit", "cikis", "WS2812B adreslenebilir renkli LED şerit (tek veri pini).", ["neopixel", "direnc", "kondansator_elektrolitik", "pil_aa"], {"dijital": 1},
       [_sayi("adet", "LED sayısı", 8, 1, 60), _GUC], r"neo\s?pixel\w*(\s+serit\w*)?(\s+\d+\s*(adet\s*)?led\w*)?|ws2812\w*|serit led\w*|led serit\w*|\d+\s*(adet\s*)?ledli serit\w*|adreslenebilir|piksel\w*", "NeoPixel")
def _u_neo(c, p):
    ma = p["adet"] * 15
    hat = c.guc(p["guc"] if p["guc"] != "oto" else ("oto" if ma <= 350 else "pil"), ma)
    n = c.add("neopixel")
    r = c.add("direnc", deger="330Ω")
    k = c.add("kondansator_elektrolitik", deger="1000µF")
    c.gnd(n, "GND")
    c.gnd(k, "-")
    if hat == "pil":
        pil = c.pil("mnt")
        c.tel(n, "VCC", pil, "+", "kablo")
        c.tel(k, "+", pil, "+", "kablo")
    else:
        c.hat5(n, "VCC")
        c.hat5(k, "+")
    pin = c.pin("dijital", f"{c.etiket(n)} DIN ({p['adet']} LED)")
    c.tel(c.mid, pin, r, "1")
    c.tel(r, "2", n, "DIN")
    c.akim("NeoPixel", ma, "5v" if hat == "5v" else "pil")
    c.not_(f"NeoPixel veri hattında {c.etiket(r)} (330 Ω), besleme hattında {c.etiket(k)} (1000 µF) var. Tahmini akım ≈{ma} mA (parlaklık düşük); tam beyazda LED başına 60 mA'e çıkar.")
    if not c.mantik5:
        c.not_("Uyarı: 3,3 V veri sinyali 5 V NeoPixel için sınırdadır; sorun olursa 74HCT125 gibi seviye dönüştürücü ekleyin.")


@_blok("led_matris", "LED matris 8x8", "cikis", "MAX7219 ile 8x8 LED matris (3 pin: DIN, CS, CLK; mümkünse donanım SPI pinleri).", ["led_matris"], {"spi": 1, "dijital": 1}, [],
       r"(led\w*\s+)?matris\w*|(led\w*\s+)?matrix\w*|8 ?x ?8|max7219", "LED matris")
def _u_matris(c, p):
    m = c.add("led_matris")
    c.hat5(m, "VCC")
    c.gnd(m, "GND")
    sp = c.m["spi"]
    if sp:
        c.sabit([sp["MOSI"], sp["SCK"]], f"{c.etiket(m)} SPI (DIN/CLK)")
        c.tel(m, "DIN", c.mid, sp["MOSI"])
        c.tel(m, "CLK", c.mid, sp["SCK"])
    else:
        for ad in ("DIN", "CLK"):
            pin = c.pin("dijital", f"{c.etiket(m)} {ad}")
            c.tel(m, ad, c.mid, pin)
    pin = c.pin("dijital", f"{c.etiket(m)} CS")
    c.tel(m, "CS", c.mid, pin)
    c.akim("LED matris", 80, "5v")
    c.not_("LED matris: LedControl ya da MD_MAX72xx kütüphanesi gerekir.")
    if not c.mantik5:
        c.not_("MAX7219 5 V ile çalışır; 3,3 V veri hattı çoğu modülde yeterlidir, olmazsa seviye dönüştürücü ekleyin.")


# ====================================================================== GÜÇ BLOKLARI
@_blok("usb", "USB-C besleme", "guc", "Kartı harici USB-C 5 V modülüyle besler (bilgisayar USB'si yerine adaptör/powerbank).", ["usb_c"], {}, [],
       r"usb\s?-?c|usb (ile )?(besle|guc)\w*|usb besleme", "USB")
def _u_usb(c, p):
    u = c.add("usb_c")
    c.gnd(u, "GND", "kablo")
    hedef = {"nodemcu": "VIN", "esp32": "VIN", "pico": "VSYS"}.get(c.key, "5V")
    c.tel(u, "VBUS", c.mid, hedef, "kablo")
    c.not_(f"USB-C modülü {hedef} pinine bağlandı. Kartın kendi USB'si de takılıyken ikisini aynı anda KULLANMAYIN (iki 5 V kaynağı birleşir).")


@_blok("pil_reg", "Pil/adaptör + regülatör", "guc", "9 V pil ya da 12 V adaptör, LM2596 buck ya da 7805 ile 5 V'a düşürülüp karta verilir.", ["pil_9v", "dc_jak", "lm2596", "regulator_7805"], {},
       [_sec("kaynak", "Kaynak", "9v pil", ["9v pil", "12v adaptor"]), _sec("regulator", "Regülatör", "lm2596", ["lm2596", "7805"])],
       r"pil\w* (ile )?(calis|beslen|besle)\w*|pilli|bataryali|batarya ile|tasinabilir|adaptor\w*|\b12 ?v\b|\b9 ?v\b", "Pil")
def _u_pilreg(c, p):
    reg = p["regulator"]
    if p["kaynak"] == "9v pil":
        k = c.add("pil_9v")
        kp, km = "+", "-"
    else:
        k = c.add("dc_jak", deger="12V")
        kp, km = "+", "-"
    hedef = {"nodemcu": "VIN", "esp32": "VIN", "pico": "VSYS"}.get(c.key, "5V")
    if reg == "lm2596":
        u = c.add("lm2596", deger="5V")
        c.tel(k, kp, u, "IN+", "kablo")
        c.tel(k, km, u, "IN-", "kablo")
        c.tel(u, "OUT-", c.mid, c.m["gnd"][0], "kablo")
        c.tel(u, "IN-", u, "OUT-")
        c.tel(u, "OUT+", c.mid, hedef, "kablo")
    else:
        u = c.add("regulator_7805")
        c.tel(k, kp, u, "IN", "kablo")
        c.tel(k, km, u, "GND", "kablo")
        c.tel(u, "GND", c.mid, c.m["gnd"][0], "kablo")
        c.tel(u, "OUT", c.mid, hedef, "kablo")
    c.not_(f"Güç yolu: {p['kaynak']} → {PARTS['lm2596' if reg == 'lm2596' else 'regulator_7805']['ad']} → MCU {hedef} (5 V). USB takılıyken bu beslemeyi bağlamayın.")
    if reg == "lm2596":
        c.not_("LM2596 çıkışını 5,0 V'a ayarlamayı unutmayın (trimpot).")


@_blok("ortak_toprak", "Ortak toprak klemensi", "guc", "Harici pil/besleme eksilerini MCU toprağıyla birleştiren GND klemensi (ortak toprak).", ["klemens"], {}, [],
       r"ortak (toprak|gnd)\w*", "Ortak GND")
def _u_ortak(c, p):
    k = c.add("klemens", etiket="GND-K1")
    c.gnd(k, "1", "kablo")
    c.gnd(k, "2", "kablo")
    c.not_(f"{c.etiket(k)} klemensi MCU GND'sine bağlıdır: ayrı beslemeli parçaların (pil, motor sürücü) eksi uçlarını buraya bağlayın.")


def katalog():
    """Sayfaya giden blok listesi."""
    return [{"id": b["id"], "ad": b["ad"], "kat": b["kat"], "acik": b["acik"], "param": [dict(sp) for sp in b["param"]],
             "parcalar": [PARTS[x]["ad"] for x in b["parcalar"]]} for b in BLOKLAR.values()]


def dogrula():
    """Kurulumda blok tanımlarındaki hataları (olmayan parça id'si) listeler; boş liste = tamam."""
    hata = []
    for b in BLOKLAR.values():
        for x in b["parcalar"]:
            if x not in PARTS:
                hata.append(f"{b['id']}: katalogda olmayan parça {x}")
        if b["kat"] not in dict(KATLAR):
            hata.append(f"{b['id']}: geçersiz kategori")
    return hata


# ====================================================================== KURULUM
_YEDEK = {"uno": "mega", "nano": "mega", "nodemcu": "esp32", "pico": "esp32"}
_ONCELIK = {"analog": 0, "kesme": 1, "pwm": 2, "spi": 3, "giris": 4, "dijital": 5, "i2c": 6}


def plan_coz(plan):
    """[(blok_id, param)] listesini doğrular ve pin kısıtına göre kurulum sırasına dizer. Bilinmeyen blokta BlokHata."""
    out = []
    for n, it in enumerate(plan):
        bid = it.get("id") if isinstance(it, dict) else it[0]
        prm = it.get("param") if isinstance(it, dict) else it[1]
        b = BLOKLAR.get(bid)
        if not b:
            raise BlokHata(f"'{bid}' adında bir blok yok.")
        out.append((n, b, param_dogrula(b, prm)))
    out.sort(key=lambda x: (min((_ONCELIK.get(k, 5) for k in x[1]["pinler"]), default=9), x[0]))
    return out


def _kart_adi(plan):
    ad = [b["kisa"] for _, b, _ in sorted(plan, key=lambda x: x[0]) if b["kat"] != "guc"]
    s = " + ".join(dict.fromkeys(ad[:3])) + " kartı"
    return s[:40]


def _kur_tek(plan, mcu, ipucu, ad):
    c = Ctx(mcu)
    m = c.m
    for _, b, _p in plan:                                      # sabit pinler önce ayrılır
        if "i2c" in b["pinler"]:
            c.rez |= set(m["i2c"])
        if "spi" in b["pinler"] and m["spi"]:
            c.rez |= set(m["spi"].values())
    for _, b, p in plan:
        b["uret"](c, p)
    # --- güç bütçesi
    t5, t33, tp = c.toplam("5v"), c.toplam("3v3"), c.toplam("pil")
    notl = [f"Kart: {m['ad']} ({_vs(m['v'])} V mantık)."]
    if c.harita:
        notl.append("Pin atamaları: " + "; ".join(f"{p} → {ne}" for p, ne in sorted(c.harita.items(), key=lambda kv: _nat(kv[0]))) + ".")
    g = []
    if t5:
        g.append(f"5 V hattı ≈{t5} mA (sınır ≈{m['lim5']} mA)")
    if t33:
        g.append(f"3,3 V hattı ≈{t33} mA (sınır ≈{m['lim33']} mA)")
    if tp:
        g.append(f"harici pil ≈{tp} mA")
    if g:
        notl.append("Akım tahmini: " + ", ".join(g) + ".")
    if t5 > m["lim5"]:
        notl.append(f"Uyarı: 5 V hattı yükü ({t5} mA) USB sınırını aşabilir; motor/servo/NeoPixel bloklarında besleme = pil seçin.")
    if t33 > m["lim33"]:
        notl.append(f"Uyarı: 3,3 V hattı yükü ({t33} mA) kartın 3,3 V çıkışı için fazla.")
    notl += c.notlar
    n = len(c.parcalar)
    kart = {"ad": ad or _kart_adi(plan), "w": min(80, max(40, 28 + 4 * n)), "h": min(80, max(28, 20 + 2 * n)), "renk": "yesil", "parcalar": c.parcalar, "teller": c.teller}
    if ipucu:
        kart["ipucu"] = dict(ipucu)
        notl.append(f"Eşik: {ipucu['esik']:g} {'°C' if ipucu['olcu'] == 'temp' else ('cm' if ipucu['olcu'] == 'cm' else '%')} ({'üstünde' if ipucu['yon'] == '>' else 'altında'}) — kodda ESIK sabiti olarak yer alır.")
    sor, _puan = an.Devre(kart).kontrol()
    for s in sor:
        if s["sev"] == "hata":
            notl.append("HATA (kontrol): " + s["msg"])
        elif s["sev"] == "uyari":
            notl.append("Uyarı (kontrol): " + s["msg"])
    return {"kart": kart, "notlar": notl, "mcu": mcu}


def kur(plan, mcu="uno", ad=None, ipucu=None, esnek=True):
    """plan: [{"id","param"}...]. esnek=True ise MCU kullanıcı seçimi değilse pin yetmediğinde bir üst kart denenir (Uno/Nano→Mega, NodeMCU/Pico→ESP32). Dönüş: {"kart","notlar","mcu"}; hata: BlokHata."""
    if not plan:
        raise BlokHata("Plan boş: önce blok ekleyin.")
    if mcu not in MCULAR:
        mcu = "uno"
    cp = plan_coz(plan)
    deneme = [mcu] + ([_YEDEK[mcu]] if esnek and mcu in _YEDEK else [])
    son = None
    for k in deneme:
        try:
            r = _kur_tek(cp, k, ipucu, ad)
            if k != mcu:
                r["notlar"].insert(0, f"{MCULAR[mcu]['ad']} üzerinde pin yetmedi; {MCULAR[k]['ad']} seçildi.")
            return r
        except BlokHata as e:
            son = e
    raise son


# ====================================================================== SEÇİM: KURAL TABANLI
_MCU_KW = [("mega", r"\bmega\b"), ("nano", r"\bnano\b"), ("uno", r"\buno\b|atmega ?328"), ("esp32", r"esp ?32\b"), ("nodemcu", r"nodemcu|esp ?8266"),
           ("pico", r"\bpico\b|rp2040")]
_YOK = [(r"\bgps\b|konum bul\w*|uydu\w*", "GPS", None),
        (r"\bwifi\b|wi fi|\binternet\w*|bluetooth\w*|kablosuz\w*|\bbulut\w*|\bmqtt\b|telefon uygulama\w*|\biot\b", "Wi-Fi/Bluetooth haberleşmesi", "mcu:esp32"),
        (r"kamera\w*|goruntu isle\w*", "kamera", None),
        (r"parmak izi|\brfid\b|\bnfc\b|kart okuyucu", "RFID/NFC/parmak izi okuyucu", None),
        (r"\bsd kart\w*|veri kaydet\w*|\blogger\b|veri tut\w*", "SD kart ile veri kaydı", "oled"),
        (r"(?<![0-9] )\bsaat(i|in|e)?\b|\brtc\b|takvim\w*|gercek zamanli", "gerçek zamanlı saat (RTC)", "oled"),
        (r"dokunmatik\w*|dokunma sens\w*", "dokunmatik sensör", "buton"),
        (r"nabiz\w*|kalp atis\w*|oksijen sens\w*", "nabız sensörü", None),
        (r"agirlik\w*|terazi\w*|load cell", "ağırlık (yük hücresi) sensörü", "potansiyometre"),
        (r"akim sens\w*|guc olc\w*|voltaj olc\w*|gerilim olc\w*|watt\w*", "akım/gerilim ölçümü", "potansiyometre"),
        (r"renk sens\w*|renk algila\w*", "renk sensörü", "ldr"),
        (r"hoparlor\w*|\bmp3\b|ses kayd\w*|konus\w*", "hoparlör/MP3", "buzzer"),
        (r"lazer\w*", "lazer", "led"),
        (r"klavye\w*|tus takimi|keypad", "tuş takımı", "buton"),
        (r"\bhall\b|miknatis\w*", "hall sensörü", "buton"),
        (r"\bnem sensoru? yok", "x", None)]
_ESIK_SOZ = {"temp": "sıcaklık", "cm": "mesafe", "hum": "nem"}


_BIRIM = ("derece", "cm", "santim", "saniye", "sn", "dakika", "dk", "volt", "v", "ohm", "yuzde", "c", "saat", "mm", "hz", "kilo", "k")


def _kural_param(bid, t):
    """Tarif metninden bloğun parametrelerini çıkarır (adet, renk, model...)."""
    b = BLOKLAR[bid]
    p = {}
    kw = b["kw"]
    toks = t.split()
    if bid == "neopixel":
        m = re.search(r"(\d+)\s*(?:adet\s*|tane\s*)?(?:led|piksel|pixel)", t)
        if m:
            p["adet"] = int(m.group(1))
    elif any(s["ad"] == "adet" for s in b["param"]) and kw:
        for n, tk in enumerate(toks):
            if kw.match(tk):
                for j in range(n - 1, max(-1, n - 3), -1):
                    v = toks[j]
                    nxt = toks[j + 1] if j + 1 < len(toks) else ""
                    if v.isdigit() and not nxt.startswith(_BIRIM):
                        p["adet"] = int(v)
                        break
                    if v in _NUM:
                        p["adet"] = _NUM[v]
                        break
                if "adet" in p:
                    break
    if bid == "dht":
        p["tur"] = "dht11" if re.search(r"dht\s?11", t) else "dht22"
    if bid == "led":
        renkler = [r for r in _RENK_SEC if re.search(r"\b" + r + r"\w*\s+(led|lamba|isik)", t)]
        if renkler:
            p["renk"] = renkler[0]
    if bid == "buzzer" and re.search(r"\baktif\b", t):
        p["tur"] = "aktif"
    if bid in ("dc_motor", "fan", "servo", "step_motor", "neopixel") and re.search(r"ayri (bir )?pil|harici (pil|besleme)|dis besleme|ayri besleme|bagimsiz besleme|ayri guc", t):
        p["guc"] = "pil"
    if bid == "ses" and re.search(r"dijital|esik", t):
        p["cikis"] = "dijital"
    if bid == "pil_reg":
        if re.search(r"adaptor|12 ?v\b", t):
            p["kaynak"] = "12v adaptor"
        if re.search(r"7805", t):
            p["regulator"] = "7805"
    return p


def _esik(raw):
    """Tarifteki sayısal koşul: '30 derecede' -> {'esik': 30, 'olcu': 'temp', 'yon': '>'}."""
    s = str(raw).replace("İ", "i").replace("I", "ı").lower().translate(_TR)
    yon_alt = bool(re.search(r"alt(ina|inda|ini)|dusunce|dusen|azalinca|altinda kal|inince|dustugunde", s))
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:°|derece\w*|santigrat\w*|c\b)", s)
    if m:
        return {"esik": float(m.group(1).replace(",", ".")), "olcu": "temp", "yon": "<" if yon_alt else ">"}
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:cm\b|santim\w*)", s)
    if m:
        uzak = bool(re.search(r"uzaklas\w*|uzakta|ustunde|fazla|ustune|asinca", s))
        return {"esik": float(m.group(1).replace(",", ".")), "olcu": "cm", "yon": ">" if uzak else "<"}
    if re.search(r"\bnem", s):
        m = re.search(r"(?:%|yuzde)\s*(\d+)|(\d+)\s*(?:%|yuzde)", s)
        if m:
            return {"esik": float(m.group(1) or m.group(2)), "olcu": "hum", "yon": "<" if yon_alt else ">"}
    return None


def _mcu_sec(t):
    for k, rx in _MCU_KW:
        if re.search(rx, t):
            return k
    return None


def sec_kural(tarif):
    """Anahtar sözcük eşleştirmeyle blok seçimi (Ollama'sız çalışır). Dönüş: {"mcu","mcu_acik","bloklar","soru","notlar","ipucu","kaynak"}."""
    raw = str(tarif or "")
    t = fold(raw)
    notlar = []
    mcu = _mcu_sec(t)
    acik = mcu is not None
    if re.search(r"\battiny\w*", t):
        notlar.append("ATtiny için bloğum yok (çıplak çip); en yakın: Arduino Nano ile kurdum.")
        mcu, acik = mcu or "nano", True
    # katalogda olmayanlar: metinden çıkarılır, kullanıcıya söylenir (uydurma yok)
    for rx, ad, yakin in _YOK:
        mm = re.search(rx, t)
        if not mm or ad == "x":
            continue
        t = (t[:mm.start()] + " " + t[mm.end():]).strip()
        if yakin and yakin.startswith("mcu:"):
            if mcu is None:
                mcu = yakin[4:]
            notlar.append(f"{ad} için ağ kodu üretemem; en yakın: {MCULAR[yakin[4:]]['ad']} seçtim, bağlantıyı kendiniz kodlamalısınız.")
        elif yakin:
            notlar.append(f"{ad} için bloğum yok, en yakın: {BLOKLAR[yakin]['ad']}.")
        else:
            notlar.append(f"{ad} için bloğum yok; bu özelliği karta ekleyemedim.")
    t = re.sub(r"ayar\w* dugme\w*", " pot ", t)
    toprak = bool(re.search(r"toprak|bitki|saksi|cicek|sulama", t))
    t_dht = re.sub(r"\bnem\w*", " ", t) if toprak else t
    lm = bool(re.search(r"\blm\s?35\b", t))
    ds = bool(BLOKLAR["ds18b20"]["kw"].search(t))
    sicak = bool(re.search(r"sicak\w*|derece\w*|termometre|\bisi\b|\bisiyi\b|\bnem\w*|\bdht", t_dht))
    maskeli = t
    for bid in ("rgb_led", "neopixel", "led_matris", "yedi_segment", "trafik"):
        maskeli = BLOKLAR[bid]["kw"].sub(" ", maskeli)
    t_m = re.sub(r"(?:servo|step|adim|titresim|vibrasyon|fan)\w*\s+motor\w*|motor\w*\s+(?:servo|step|fan)\w*", " ", t)      # özel motorlar DC motor sayılmaz
    lcd_var = bool(re.search(r"\blcd\w*|16 ?x ?2|1602", t))
    seg_var = bool(BLOKLAR["yedi_segment"]["kw"].search(t))
    secilen = []
    for bid, b in BLOKLAR.items():
        kw = b["kw"]
        if kw is None:
            continue
        if bid == "dht":
            hit = sicak and not lm and not ds
        elif bid == "led":
            hit = bool(kw.search(maskeli))
        elif bid == "oled":
            hit = (bool(kw.search(maskeli)) and not lcd_var and not seg_var) or bool(re.search(r"\boled\w*|ssd1306|\bekran\w*", t) and not lcd_var) or bool(re.search(r"\boled\w*|ssd1306", t))
        elif bid == "dc_motor":
            hit = bool(kw.search(t_m))
        else:
            hit = bool(kw.search(t))
        if hit:
            secilen.append(bid)
    es = _esik(raw)
    if es:
        gerek = {"temp": ("dht", "lm35", "ds18b20", "bmp280"), "cm": ("hcsr04",), "hum": ("dht",)}[es["olcu"]]
        if not any(x in secilen for x in gerek):
            ek = {"temp": "dht", "cm": "hcsr04", "hum": "dht"}[es["olcu"]]
            secilen.insert(0, ek)
            notlar.append(f"{_ESIK_SOZ[es['olcu']].capitalize()} koşulu için {BLOKLAR[ek]['ad']} bloğunu ekledim.")
    if "pil_reg" in secilen and re.search(r"ayri (bir )?pil|harici pil", t) and any(x in secilen for x in ("dc_motor", "fan", "servo", "step_motor", "neopixel")):
        secilen.remove("pil_reg")                       # 'ayrı pil ile çalışan motor': pil motorun besleme seçeneğidir, kartın güç yolu değil
    plan = []
    for bid in secilen:
        prm = _kural_param(bid, t)
        if bid == "led":
            renkler = [r for r in _RENK_SEC if re.search(r"\b" + r + r"\w*\s+(led|lamba|isik)", t)]
            if len(renkler) > 1:
                for r in renkler:
                    plan.append({"id": "led", "param": {"adet": 1, "renk": r}})
                continue
        plan.append({"id": bid, "param": prm})
    if mcu is None and plan:
        mcu = "nano" if re.search(r"kucuk|mini|kompakt|\bcep\b|breadboard", t) else "uno"
    soru = None
    if not plan and notlar:
        soru = "Bu isteği karşılayan bir bloğum yok efendim; yine de en yakın bloklarla kurmamı ister misiniz, yoksa başka bir özellik mi söyleyeceksiniz?"
    elif not plan:
        soru = "Ne yapmasını istediğinizi tam anlayamadım efendim. Örneğin: sıcaklığı ölçüp ekranda gösteren, 30 derecede fanı açan bir kart."
    return {"mcu": mcu or "uno", "mcu_acik": acik, "bloklar": plan, "soru": soru, "notlar": notlar, "ipucu": es, "kaynak": "kural"}


# ====================================================================== SEÇİM: YEREL LLM
def _katalog_metni():
    sat = []
    for b in BLOKLAR.values():
        ps = []
        for sp in b["param"]:
            if sp["tip"] == "sayi":
                ps.append(f"{sp['ad']} {sp['min']}-{sp['max']}")
            elif sp["tip"] == "secim":
                ps.append(f"{sp['ad']}: " + "|".join(sp["secenekler"]))
        sat.append(f"- {b['id']}: {b['ad']} — {b['acik'].split('.')[0][:70]}" + (f" [{'; '.join(ps)}]" if ps else ""))
    return "\n".join(sat)


_SISTEM = ("Sen bir elektronik kart kurucusunun BLOK SEÇİCİSİSİN. Kullanıcının isteğini karşılayan blokları aşağıdaki katalogdan seç. "
           "Kablolama, pin, direnç ve kod senin işin DEĞİL; yalnızca blok id'lerini ve parametrelerini seç. Katalogda olmayan id UYDURMA; "
           "karşılığı olmayan bir istek varsa onu bloklara ekleme. Mikrodenetleyici: uno, nano, mega, esp32, nodemcu, pico (kullanıcı söylemediyse null). "
           "Sensör koşulu (ör. 30 derecede fan) için hem sensör hem eyleyici bloğunu seç. Yalnızca şu biçimde TEK JSON yaz, başka metin yazma: "
           '{"mcu": "uno", "bloklar": [{"id": "...", "param": {}}], "soru": null}. İstek anlaşılmazsa bloklar boş ve soru bir Türkçe cümle olsun.\n\nKATALOG:\n')


def _json_cikar(s):
    s = re.sub(r"<think>.*?</think>", "", str(s), flags=re.S).strip()
    try:
        return json.loads(s)
    except ValueError:
        m = re.search(r"\{.*\}", s, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except ValueError:
                return None
    return None


def llm_temizle(d):
    """LLM çıktısını doğrular: katalogda olmayan blok atılır, parametre geçersizse varsayılan. Geçersiz yapı -> None."""
    if not isinstance(d, dict) or not isinstance(d.get("bloklar", []), list):
        return None
    plan, atilan = [], []
    for it in d.get("bloklar") or []:
        if not isinstance(it, dict):
            continue
        bid = str(it.get("id") or "").strip()
        if bid not in BLOKLAR:
            atilan.append(bid)
            continue
        plan.append({"id": bid, "param": param_dogrula(BLOKLAR[bid], it.get("param"))})
        if len(plan) >= 24:
            break
    mcu = str(d.get("mcu") or "").strip().lower()
    soru = d.get("soru")
    return {"mcu": mcu if mcu in MCULAR else None, "bloklar": plan, "soru": (str(soru)[:200] if soru else None), "atilan": atilan}


def sec_llm(tarif):
    """Ollama (brain.MODEL) ile seçim; olmazsa/geçersizse None (çağıran kural tabanlıya düşer). Bir kez yeniden dener."""
    try:
        import brain
        import ollama
    except Exception:                               # noqa: BLE001
        return None
    msgs = [{"role": "system", "content": _SISTEM + _katalog_metni()}, {"role": "user", "content": "İstek: " + str(tarif)[:500]}]
    for _ in range(2):
        try:
            out = ollama.chat(model=brain.MODEL, messages=msgs, format="json", keep_alive="5m", **brain._extra(False),
                              options={"temperature": 0, "num_ctx": brain.CTX, "num_predict": 600}).message.content
        except Exception as e:                      # noqa: BLE001
            print("elektronik blok LLM hatası:", type(e).__name__, flush=True)
            return None
        r = llm_temizle(_json_cikar(out))
        if r is not None and (r["bloklar"] or r["soru"]):
            return r
        msgs = msgs + [{"role": "assistant", "content": str(out)[:400]}, {"role": "user", "content": "Geçersiz çıktı. Yalnızca katalogdaki id'lerle geçerli JSON yaz."}]
    return None


def sec(tarif, llm=True):
    """LLM (varsa) + kural tabanlı doğrulama. Modelin seçtiği blok, tarifte karşılığı yoksa atılır (uydurma engeli); kuralın bulduğu ama modelin atladığı
    bloklar eklenir; parametrelerde tarifte açıkça yazılanlar (kural) modelin değerinin önüne geçer. Eşik ve 'bloğum yok' notları her zaman kuraldan gelir."""
    kural = sec_kural(tarif)
    if not llm:
        return kural
    r = sec_llm(tarif)
    if not r:
        kural["notlar"].insert(0, "Yerel model kullanılamadı; anahtar sözcüklerle seçtim.")
        return kural
    t = fold(tarif)
    kural_p = {}
    for it in kural["bloklar"]:
        kural_p.setdefault(it["id"], []).append(it["param"])
    plan, atilan = [], list(r["atilan"])
    for it in r["bloklar"]:
        b = BLOKLAR[it["id"]]
        if it["id"] not in kural_p and not (b["kw"] and b["kw"].search(t)):
            atilan.append(it["id"])
            continue
        ham = (kural_p.get(it["id"]) or [{}])[0]
        plan.append({"id": it["id"], "param": param_dogrula(b, {**it["param"], **ham})})
    for it in kural["bloklar"]:                              # kuralın bulduğu ama modelin atladığı bloklar
        if not any(x["id"] == it["id"] for x in plan):
            plan.append({"id": it["id"], "param": param_dogrula(BLOKLAR[it["id"]], it["param"])})
    acik = bool(kural["mcu_acik"])
    out = {"mcu": kural["mcu"] if acik else (r["mcu"] or kural["mcu"]), "mcu_acik": acik, "bloklar": plan, "soru": None, "notlar": list(kural["notlar"]),
           "ipucu": kural["ipucu"], "kaynak": "llm"}
    if atilan:
        out["notlar"].append("Modelin önerdiği, tarifte karşılığı olmayan blok(lar) atıldı: " + ", ".join(a or "?" for a in atilan) + ".")
    if not plan:
        out["soru"] = r["soru"] or kural["soru"]
        out["kaynak"] = "llm" if r["soru"] else "kural"
    return out


def blok_bul(metin):
    """Sesli 'plana LED bloğu ekle' için: metinden ilk blok (id, param) ya da None."""
    r = sec_kural(metin)
    return r["bloklar"][0] if r["bloklar"] else None


def plan_satirlari(plan):
    out = []
    for n, it in enumerate(plan):
        b = BLOKLAR[it["id"]]
        out.append({"i": n, "id": b["id"], "ad": b["ad"], "ozet": _ozet(b, it["param"])})
    return out
