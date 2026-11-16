"""Ders modu: 9. sınıf müfredatı (Türkiye Yüzyılı Maarif Modeli), ilerleme kaydı ve ayarlar.
Ünite / tema adları MEB öğretim programı sayfalarından (tymm.meb.gov.tr, 9. sınıf) alınmıştır. Konu başlıkları: 'program' = MEB kazanım kodlarından,
'öneri' = ünite adına göre önerilen başlık (resmî programla karşılaştırılmalı). İstenen ders, ünite ve konu ayrıca elle de yazılabilir.
Veriler yalnızca bu bilgisayarda (ders.json, ders_cache/) durur."""
import hashlib
import json
import os
import re
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "ders.json")
CACHE = os.path.join(HERE, "ders_cache")
_lock = threading.RLock()

P, O = "program", "öneri"


def _k(ad, kaynak=O, kod=""):
    return {"ad": ad, "kaynak": kaynak, "kod": kod}


DERSLER = [
    {"id": "matematik", "ad": "Matematik", "ikon": "∑", "nicel": True, "uniteler": [
        {"ad": "1. Tema: Sayılar", "kaynak": P, "konular": [
            _k("Gerçek sayıların üslü ve köklü gösterimleriyle işlemler", P, "MAT.9.1.1"), _k("Gerçek sayı aralıkları ve küme sembolleri", P, "MAT.9.1.2"),
            _k("Sayı kümelerinin özellikleri (doğal, tam, rasyonel, gerçek)", P, "MAT.9.1.3"), _k("Gerçek sayılarda işlem özellikleri ve cebirsel ifadeler", P, "MAT.9.1.4")]},
        {"ad": "2. Tema: Nicelikler ve Değişimler", "kaynak": P, "konular": [
            _k("Doğrusal referans fonksiyon f(x) = x", P, "MAT.9.2.1"), _k("Mutlak değer fonksiyonları", P, "MAT.9.2.2"),
            _k("Doğrusal fonksiyonlarla denklem ve eşitsizlik problemleri", P, "MAT.9.2.3")]},
        {"ad": "3. Tema: Algoritma ve Bilişim", "kaynak": P, "konular": [
            _k("Algoritma temelli problem çözme", P, "MAT.9.3.1"), _k("Mantık bağlaçları ve niceleyiciler", P, "MAT.9.3.2")]},
        {"ad": "4. Tema: Geometrik Şekiller", "kaynak": P, "konular": [_k("Üçgende açı ve kenar ilişkileri", P, "MAT.9.4.1")]},
        {"ad": "5. Tema: Eşlik ve Benzerlik", "kaynak": P, "konular": [
            _k("Geometrik dönüşümler (öteleme, yansıma, dönme)", P, "MAT.9.5.1"), _k("Üçgenlerde eşlik koşulları", P, "MAT.9.5.2"), _k("Üçgenlerde benzerlik", P, "MAT.9.5.3"),
            _k("Tales, Öklid ve Pisagor teoremleri", P, "MAT.9.5.4"), _k("Eşlik ve benzerlik problemleri", P, "MAT.9.5.5")]},
        {"ad": "6. Tema: İstatistiksel Araştırma Süreci", "kaynak": P, "konular": [
            _k("Veri toplama ve düzenleme"), _k("Veri grafikleri ve merkezi eğilim ölçüleri")]},
        {"ad": "7. Tema: Veriden Olasılığa", "kaynak": P, "konular": [_k("Örnek uzay ve olaylar"), _k("Olasılık hesaplama")]}]},
    {"id": "fizik", "ad": "Fizik", "ikon": "⚛", "nicel": True, "uniteler": [
        {"ad": "1. Ünite: Fizik Bilimi ve Kariyer Keşfi", "kaynak": P, "konular": [
            _k("Fizik biliminin tanımı", P, "FİZ.9.1.1"), _k("Fiziğin alt dalları", P, "FİZ.9.1.2"), _k("Fizik bilimine katkıda bulunan bilim insanları", P, "FİZ.9.1.3"),
            _k("Fizik bilimi ve kariyer alanları", P, "FİZ.9.1.4")]},
        {"ad": "2. Ünite: Kuvvet ve Hareket", "kaynak": P, "konular": [
            _k("SI birim sistemi, temel ve türetilmiş nicelikler", P, "FİZ.9.2.1"), _k("Skaler ve vektörel nicelikler", P, "FİZ.9.2.2"),
            _k("Vektörlerin toplanması (aynı doğrultuda, uç uca ve paralel kenar)", P, "FİZ.9.2.3-4"), _k("Doğadaki temel kuvvetler", P, "FİZ.9.2.5"),
            _k("Hareketin temel kavramları (konum, yer değiştirme, hız)", P, "FİZ.9.2.6"), _k("Hareket türleri", P, "FİZ.9.2.7")]},
        {"ad": "3. Ünite: Akışkanlar", "kaynak": P, "konular": [
            _k("Basınç", P, "FİZ.9.3.1"), _k("Durgun sıvılarda basınç", P, "FİZ.9.3.2"), _k("Sıvı basıncının günlük hayattaki uygulamaları", P, "FİZ.9.3.3"),
            _k("Açık hava basıncı", P, "FİZ.9.3.4"), _k("Kaldırma kuvveti", P, "FİZ.9.3.5"), _k("Kaldırma kuvveti ve sıvı basıncı ilişkisi", P, "FİZ.9.3.6"),
            _k("Akışkanlarda hız ve basınç ilişkisi", P, "FİZ.9.3.7")]},
        {"ad": "4. Ünite: Enerji", "kaynak": P, "konular": [
            _k("İş, güç ve enerji"), _k("Kinetik ve potansiyel enerji"), _k("Mekanik enerjinin korunumu"), _k("Isı, sıcaklık ve ısı aktarımı"), _k("Enerji kaynakları ve verim")]}]},
    {"id": "kimya", "ad": "Kimya", "ikon": "⚗", "nicel": True, "uniteler": [
        {"ad": "1. Tema: Etkileşim", "kaynak": P, "konular": [
            _k("Kimya bilimi ve atomun yapısı"), _k("Periyodik sistem"), _k("Kimyasal türler arası etkileşimler (iyonik, kovalent, metalik bağ)"), _k("Zayıf etkileşimler")]},
        {"ad": "2. Tema: Çeşitlilik", "kaynak": P, "konular": [
            _k("Maddenin sınıflandırılması"), _k("Karışımlar ve ayırma yöntemleri"), _k("Bileşikler ve adlandırma")]},
        {"ad": "3. Tema: Sürdürülebilirlik", "kaynak": P, "konular": [_k("Kimya ve çevre"), _k("Geri dönüşüm ve yeşil kimya"), _k("Enerji ve kimya")]}]},
    {"id": "biyoloji", "ad": "Biyoloji", "ikon": "🧬", "nicel": False, "uniteler": [
        {"ad": "1. Tema: Yaşam", "kaynak": P, "konular": [
            _k("Biyoloji bilimi ve bilimsel yöntem"), _k("Canlıların ortak özellikleri"), _k("Canlıların yapısındaki moleküller (inorganik ve organik)")]},
        {"ad": "2. Tema: Organizasyon", "kaynak": P, "konular": [
            _k("Hücre ve organeller"), _k("Hücrede madde geçişleri"), _k("Canlılarda organizasyon düzeyleri"), _k("Canlıların sınıflandırılması")]}]},
    {"id": "edebiyat", "ad": "Türk Dili ve Edebiyatı", "ikon": "✎", "nicel": False, "uniteler": [
        {"ad": "1. Tema: Sözün İnceliği", "kaynak": P, "konular": [_k("Edebiyat, dil ve güzel sanatlar"), _k("Şiirin ögeleri ve şiir türleri"), _k("Söz sanatları")]},
        {"ad": "2. Tema: Anlam Arayışı", "kaynak": P, "konular": [_k("Hikâye (öyküleyici metinler)"), _k("Hikâyede olay, kişi, yer, zaman")]},
        {"ad": "3. Tema: Anlamın Yapı Taşları", "kaynak": P, "konular": [_k("Sözcükte anlam"), _k("Cümlede anlam"), _k("Paragrafta anlam ve anlatım")]},
        {"ad": "4. Tema: Dilin Zenginliği", "kaynak": P, "konular": [_k("Masal ve fabl"), _k("Tiyatro (oyun) metinleri"), _k("Atasözleri ve deyimler")]}]},
    {"id": "tarih", "ad": "Tarih", "ikon": "🏛", "nicel": False, "uniteler": [
        {"ad": "1. Ünite: Geçmişin İnşa Sürecinde Tarih", "kaynak": P, "konular": [_k("Tarih bilimi ve yöntemi"), _k("Tarihî kaynaklar ve zaman kavramı")]},
        {"ad": "2. Ünite: Eski Çağ Medeniyetleri", "kaynak": P, "konular": [
            _k("İlk insan toplulukları ve tarım devrimi"), _k("Mezopotamya ve Mısır medeniyetleri"), _k("Anadolu uygarlıkları"), _k("Yunan ve Roma medeniyetleri")]},
        {"ad": "3. Ünite: Orta Çağ Medeniyetleri", "kaynak": P, "konular": [
            _k("İslam öncesi Türk tarihi"), _k("İslam medeniyetinin doğuşu"), _k("Avrupa'da Orta Çağ")]}]},
    {"id": "cografya", "ad": "Coğrafya", "ikon": "🌍", "nicel": False, "uniteler": [
        {"ad": "1. Ünite: Coğrafyanın Doğası", "kaynak": P, "konular": [_k("Coğrafyanın konusu ve bölümleri"), _k("Doğa-insan etkileşimi")]},
        {"ad": "2. Ünite: Mekânsal Bilgi Teknolojileri", "kaynak": P, "konular": [_k("Harita bilgisi ve ölçek"), _k("Coğrafi Bilgi Sistemleri ve uzaktan algılama")]},
        {"ad": "3. Ünite: Doğal Sistemler ve Süreçler", "kaynak": P, "konular": [_k("Dünya'nın şekli ve hareketleri"), _k("İklim ve hava olayları"), _k("Yer şekilleri")]},
        {"ad": "4. Ünite: Beşerî Sistemler ve Süreçler", "kaynak": P, "konular": [_k("Nüfus"), _k("Yerleşme")]},
        {"ad": "5. Ünite: Ekonomik Faaliyetler ve Etkileri", "kaynak": P, "konular": [_k("Ekonomik faaliyetlerin sınıflandırılması"), _k("Doğal kaynaklar")]},
        {"ad": "6. Ünite: Afetler ve Sürdürülebilir Çevre", "kaynak": P, "konular": [_k("Doğal afetler"), _k("Sürdürülebilir çevre")]},
        {"ad": "7. Ünite: Bölgeler, Ülkeler ve Küresel Bağlantılar", "kaynak": P, "konular": [_k("Bölge kavramı"), _k("Küresel bağlantılar")]}]},
]
BY_ID = {d["id"]: d for d in DERSLER}

DEFAULT_SETTINGS = {"quiz_n": 20, "deneme_n": 40, "anlik_kontrol": False, "anlat_sesli": True, "internet_kaynak": True}
LIMITS = {"quiz_n": (5, 40), "deneme_n": (10, 80)}
STAGES = ["anlatim", "ozet", "etkinlik", "quiz", "deneme"]


def _s(v, n=120) -> str:
    return " ".join(str(v if v is not None else "").replace("\x00", " ").split())[:n]


def key_of(ders: str, unite: str, konu: str) -> str:
    return hashlib.sha1(f"{ders}|{unite}|{konu}".lower().encode("utf-8")).hexdigest()[:12]


def _load() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    st = {**DEFAULT_SETTINGS, **(d.get("settings") if isinstance(d.get("settings"), dict) else {})}
    for k, (lo, hi) in LIMITS.items():
        try:
            st[k] = max(lo, min(hi, int(st[k])))
        except (TypeError, ValueError):
            st[k] = DEFAULT_SETTINGS[k]
    st["anlik_kontrol"] = bool(st["anlik_kontrol"])
    st["anlat_sesli"] = bool(st["anlat_sesli"])
    st["internet_kaynak"] = bool(st["internet_kaynak"])
    prog = d.get("progress") if isinstance(d.get("progress"), dict) else {}
    return {"settings": st, "progress": prog, "last": _s(d.get("last"), 20), "custom": d.get("custom") if isinstance(d.get("custom"), list) else []}


def _save(d: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=HERE, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, PATH)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def view() -> dict:
    with _lock:
        d = _load()
    return {"dersler": DERSLER, "settings": d["settings"], "progress": d["progress"], "last": d["last"], "custom": d["custom"]}


def settings() -> dict:
    with _lock:
        return _load()["settings"]


def set_setting(name: str, value) -> dict:
    with _lock:
        d = _load()
        if name in LIMITS:
            lo, hi = LIMITS[name]
            try:
                d["settings"][name] = max(lo, min(hi, int(value)))
            except (TypeError, ValueError):
                return d["settings"]
        elif name in ("anlik_kontrol", "anlat_sesli", "internet_kaynak"):
            d["settings"][name] = bool(value)
        _save(d)
        return d["settings"]


# ------------------------------------------------------------------ ilerleme (kalınan yerden devam)
def _clean_exam(e) -> dict:
    if not isinstance(e, dict):
        return {}
    ans = e.get("answers") if isinstance(e.get("answers"), dict) else {}
    out = {"answers": {str(k)[:12]: str(v)[:1] for k, v in list(ans.items())[:120] if str(v)[:1] in "ABCDE" and str(v)[:1]},
           "idx": max(0, min(119, int(e.get("idx", 0) or 0))), "finished": bool(e.get("finished")), "n": max(0, min(120, int(e.get("n", 0) or 0))),
           "ids": [str(x)[:12] for x in (e.get("ids") if isinstance(e.get("ids"), list) else [])[:120]],
           "checked": [str(x)[:12] for x in (e.get("checked") if isinstance(e.get("checked"), list) else [])[:120]],
           "t0": int(e.get("t0", 0) or 0)}
    return out


def save_progress(key: str, p: dict) -> None:
    """Sayfadan gelen ilerlemeyi doğrulayıp saklar. Yalnızca bilinen alanlar, sınırlı boyut."""
    if not re.fullmatch(r"[0-9a-f]{12}", str(key)) or not isinstance(p, dict):
        return
    meta = p.get("meta") if isinstance(p.get("meta"), dict) else {}
    with _lock:
        d = _load()
        if key not in d["progress"] and len(d["progress"]) >= 400:
            return
        cur = {"stage": p.get("stage") if p.get("stage") in STAGES else "anlatim",
               "done": {s: bool((p.get("done") or {}).get(s)) for s in STAGES} if isinstance(p.get("done"), dict) else {s: False for s in STAGES},
               "quiz": _clean_exam(p.get("quiz")), "deneme": _clean_exam(p.get("deneme")), "t": int(time.time()),
               "meta": {"ders": _s(meta.get("ders"), 20), "dersAd": _s(meta.get("dersAd"), 40), "unite": _s(meta.get("unite"), 100), "konu": _s(meta.get("konu"), 120)}}
        d["progress"][key] = cur
        d["last"] = key
        _save(d)


def reset_progress(key: str) -> None:
    with _lock:
        d = _load()
        d["progress"].pop(key, None)
        if d["last"] == key:
            d["last"] = ""
        _save(d)


def add_custom(ders: str, unite: str, konu: str) -> dict:
    ders, unite, konu = _s(ders, 40), _s(unite, 100), _s(konu, 120)
    if not ders or not konu:
        return {}
    with _lock:
        d = _load()
        item = {"ders": ders, "unite": unite or "Serbest ünite", "konu": konu}
        if not any(c.get("ders") == ders and c.get("unite") == item["unite"] and c.get("konu") == konu for c in d["custom"]) and len(d["custom"]) < 200:
            d["custom"].append(item)
            _save(d)
    return {"ders": ders, "unite": unite or "Serbest ünite", "konu": konu, "key": key_of(ders, item["unite"], konu)}


# ------------------------------------------------------------------ içerik önbelleği
def cache_path(key: str) -> str:
    return os.path.join(CACHE, key + ".json")


def cache_load(key: str) -> dict:
    try:
        with open(cache_path(key), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def cache_save(key: str, d: dict) -> None:
    os.makedirs(CACHE, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=CACHE, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, cache_path(key))
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


# ---- ek konu önerileri (kaynak 'öneri': resmî programla karşılaştırılmalı); mevcut ünitelerin sonuna eklenir
_EK = {
    ("Kimya", "1. Tema: Etkileşim"): ["Atom modelleri ve elektron dizilimi", "Elementlerin periyodik özellikleri (yarıçap, iyonlaşma enerjisi)", "İyon ve izotop kavramları"],
    ("Kimya", "2. Tema: Çeşitlilik"): ["Çözelti, süspansiyon ve emülsiyon", "Yoğunluk ve hâl değişimleri", "Mol kavramına giriş"],
    ("Kimya", "3. Tema: Sürdürülebilirlik"): ["Asit, baz ve tuzlar (günlük hayat)", "Yakıtlar ve yanma", "Plastikler ve polimerler"],
    ("Biyoloji", "1. Tema: Yaşam"): ["Enzimler ve biyolojik katalizörler", "Vitaminler ve mineraller", "Suyun ve tuzların canlılar için önemi"],
    ("Biyoloji", "2. Tema: Organizasyon"): ["Hücre zarının yapısı (akışkan mozaik modeli)", "Prokaryot ve ökaryot hücre karşılaştırması", "Tür, popülasyon, komünite ve ekosistem", "Mitoz ve hücre döngüsüne giriş"],
}
for _d in DERSLER:
    for _u in _d.get("uniteler", []):
        for _ad in _EK.get((_d["ad"], _u["ad"]), []):
            if not any(k["ad"] == _ad for k in _u["konular"]):
                _u["konular"].append(_k(_ad))
