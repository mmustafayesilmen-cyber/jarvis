"""Tarif modu verisi ve durumu (40 yerleşik tarif, kişi sayısına göre ölçekleme, alışveriş listesi). Tarifler yerleşiktir (internet gerekmez). Adım: (metin, sayaç dakikası ya da 0)."""
import json
import os
import re

R = [
 {"id": "menemen", "ad": "Menemen", "kat": "kahvaltı", "dk": 15, "kisi": 2, "mal": ["3 yumurta", "2 domates", "2 sivri biber", "1 yemek kaşığı tereyağı", "tuz, pul biber"],
  "adim": [("Biberleri küçük küçük doğrayın, domatesleri rendeleyin.", 0), ("Tavada tereyağını eritin, biberleri beş dakika kavurun.", 5), ("Domatesleri ekleyip suyunu çekene kadar pişirin.", 7),
           ("Yumurtaları kırın, tuz ve pul biberi ekleyin. Hafifçe karıştırın.", 3), ("Ocaktan alın, sıcak servis yapın.", 0)]},
 {"id": "omlet", "ad": "Peynirli omlet", "kat": "kahvaltı", "dk": 8, "kisi": 1, "mal": ["2 yumurta", "2 yemek kaşığı rendelenmiş kaşar", "1 tatlı kaşığı tereyağı", "tuz, karabiber"],
  "adim": [("Yumurtaları tuz ve karabiberle çırpın.", 0), ("Tavada tereyağını eritin, yumurtayı dökün.", 0), ("Alt tarafı tutunca üstüne kaşarı serpin.", 2), ("İkiye katlayıp bir dakika daha pişirin ve servis yapın.", 1)]},
 {"id": "pankek", "ad": "Pankek", "kat": "kahvaltı", "dk": 25, "kisi": 3, "mal": ["1 su bardağı un", "1 su bardağı süt", "1 yumurta", "1 yemek kaşığı şeker", "1 paket kabartma tozu", "1 tutam tuz"],
  "adim": [("Yumurta, süt ve şekeri çırpın.", 0), ("Un, kabartma tozu ve tuzu ekleyip topaksız bir hamur yapın.", 0), ("Hamuru on dakika dinlendirin.", 10), ("Yağlanmış tavada kepçeyle küçük daireler dökün, kabarcıklar çıkınca çevirin.", 2), ("Bal ya da meyveyle servis yapın.", 0)]},
 {"id": "mercimek", "ad": "Mercimek çorbası", "kat": "çorba", "dk": 40, "kisi": 4, "mal": ["1 su bardağı kırmızı mercimek", "1 soğan", "1 havuç", "1 patates", "6 su bardağı sıcak su", "2 yemek kaşığı sıvı yağ", "tuz, kimyon, limon"],
  "adim": [("Soğanı doğrayıp yağda kavurun.", 4), ("Havuç ve patatesi küp doğrayıp ekleyin, birkaç dakika çevirin.", 3), ("Yıkanmış mercimeği ve sıcak suyu ekleyin.", 0), ("Kaynayınca kısık ateşte sebzeler yumuşayana kadar pişirin.", 25), ("Blenderdan geçirin, tuz ve kimyonla tatlandırın.", 0), ("Limon sıkarak servis yapın.", 0)]},
 {"id": "pilav", "ad": "Tereyağlı pirinç pilavı", "kat": "ana yemek", "dk": 30, "kisi": 4, "mal": ["2 su bardağı pirinç", "2 yemek kaşığı tereyağı", "3 su bardağı sıcak su", "1 tatlı kaşığı tuz"],
  "adim": [("Pirinci ılık tuzlu suda yirmi dakika bekletip yıkayın.", 20), ("Tencerede tereyağını eritip pirinci beş dakika kavurun.", 5), ("Sıcak suyu ve tuzu ekleyin, kaynayınca kısın.", 0), ("Kapağını kapatıp su çekilene kadar pişirin.", 10), ("Altını kapatın, havlu sararak on dakika demlendirin.", 10)]},
 {"id": "makarna", "ad": "Domates soslu makarna", "kat": "ana yemek", "dk": 20, "kisi": 2, "mal": ["200 gram makarna", "3 domates ya da 1 kase salça sos", "2 diş sarımsak", "2 yemek kaşığı zeytinyağı", "tuz, fesleğen"],
  "adim": [("Bol tuzlu kaynar suda makarnayı paket süresince haşlayın.", 9), ("Sarımsağı zeytinyağında hafifçe kavurun.", 1), ("Rendelenmiş domatesi ekleyip koyulaşana kadar pişirin.", 8), ("Süzülmüş makarnayı sosa katıp karıştırın.", 0), ("Fesleğenle servis yapın.", 0)]},
 {"id": "kurufasulye", "ad": "Kuru fasulye", "kat": "ana yemek", "dk": 90, "kisi": 5, "mal": ["2 su bardağı kuru fasulye", "1 soğan", "2 yemek kaşığı salça", "2 yemek kaşığı sıvı yağ", "tuz, pul biber"],
  "adim": [("Fasulyeyi bir gece önceden suda bekletin, suyunu değiştirip haşlayın.", 20), ("Ayrı tencerede soğanı yağda kavurun, salçayı ekleyin.", 5), ("Haşlanmış fasulyeyi ve sıcak suyu ilave edin.", 0), ("Kısık ateşte fasulye yumuşayana kadar pişirin, tuzu sonda ekleyin.", 50), ("Pilavla sıcak servis yapın.", 0)]},
 {"id": "karniyarik", "ad": "Karnıyarık", "kat": "ana yemek", "dk": 60, "kisi": 4, "mal": ["4 patlıcan", "250 gram kıyma", "1 soğan", "2 domates", "2 sivri biber", "1 yemek kaşığı salça", "sıvı yağ, tuz, karabiber"],
  "adim": [("Patlıcanları alaca soyup tuzlu suda on beş dakika bekletin, kurulayıp kızartın.", 15), ("Soğanı kavurun, kıymayı ekleyip suyunu çekene kadar pişirin.", 10), ("Salça, doğranmış domates ve baharatı ekleyip harcı hazırlayın.", 5), ("Patlıcanları ortadan yarıp harçla doldurun, üstüne biber ve domates koyun.", 0), ("Tepsiye dizip az su ekleyerek 200 derece fırında pişirin.", 25)]},
 {"id": "tavuksote", "ad": "Tavuk sote", "kat": "ana yemek", "dk": 30, "kisi": 3, "mal": ["400 gram tavuk göğsü", "2 biber", "2 domates", "1 soğan", "2 yemek kaşığı sıvı yağ", "tuz, karabiber, kekik"],
  "adim": [("Tavuğu küp küp doğrayın.", 0), ("Yağda tavukları suyunu salıp çekene kadar kavurun.", 8), ("Soğan ve biberleri ekleyip beş dakika çevirin.", 5), ("Domatesleri ve baharatı ekleyin, kapağı kapalı pişirin.", 12), ("Sıcak servis yapın.", 0)]},
 {"id": "sutlac", "ad": "Fırın sütlaç", "kat": "tatlı", "dk": 60, "kisi": 6, "mal": ["1 litre süt", "½ su bardağı pirinç", "¾ su bardağı şeker", "1 yemek kaşığı nişasta", "1 paket vanilya"],
  "adim": [("Pirinci bir bardak suda yumuşayana kadar haşlayın.", 15), ("Sütü ve şekeri ekleyip karıştırarak pişirin.", 10), ("Nişastayı az sütle açıp tencereye ekleyin, bir taşım kaynatın.", 3), ("Vanilyayı katıp kaselere paylaştırın.", 0), ("Isıtılmış fırında üstü kızarana kadar pişirip soğutun.", 12)]},
 {"id": "kek", "ad": "Sade kek", "kat": "tatlı", "dk": 55, "kisi": 8, "mal": ["3 yumurta", "1 su bardağı şeker", "1 su bardağı süt", "½ su bardağı sıvı yağ", "2,5 su bardağı un", "1 paket kabartma tozu", "1 paket vanilya"],
  "adim": [("Fırını 175 dereceye ısıtın.", 0), ("Yumurta ve şekeri açılana kadar çırpın.", 3), ("Süt ve yağı ekleyin, sonra un, kabartma tozu ve vanilyayı katın.", 0), ("Yağlanmış kalıba dökün.", 0), ("Fırında kürdan temiz çıkana kadar pişirin.", 40), ("On dakika dinlendirip kalıptan çıkarın.", 10)]},
 {"id": "cacik", "ad": "Cacık", "kat": "atıştırmalık", "dk": 10, "kisi": 3, "mal": ["2 su bardağı yoğurt", "1 salatalık", "1 diş sarımsak", "1 yemek kaşığı zeytinyağı", "nane, tuz"],
  "adim": [("Salatalığı rendeleyin ya da ince doğrayın.", 0), ("Yoğurdu sarımsak ve tuzla çırpın, azıcık su ile açın.", 0), ("Salatalığı ekleyin, naneyle ve zeytinyağıyla süsleyin.", 0), ("Buzdolabında yarım saat dinlendirin.", 30)]},
]
from tarif_data2 import R2
from tarif_tm import R3, VARIANTS

R += R2 + R3
BY_ID = {r["id"]: r for r in R}
for _k, _v in VARIANTS.items():                    # mevcut tariflerin Thermomix sürümü (tarif_tm.py)
    BY_ID[_k]["tmv"] = _v
CATS = ["kahvaltı", "çorba", "ana yemek", "tatlı", "atıştırmalık", "salata", "içecek"]
S = {"id": None, "step": -1, "kisi": 0, "tm": False}   # tm: Thermomix sürümü gösterilsin mi (yalnızca Thermomix tariflerinde hep açık)
LIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tarif_alisveris.json")      # kişisel alışveriş listesi (gitignored)
_FR = {"½": 0.5, "¼": 0.25, "¾": 0.75}
_NUM = re.compile(r"^(\d+(?:[.,]\d+)?|[½¼¾])\s*(.*)$")


def _fmt_n(x: float) -> str:
    if abs(x - round(x)) < 0.05:
        return str(int(round(x)))
    h = {0.25: "¼", 0.5: "½", 0.75: "¾"}
    f = x - int(x)
    for k, v in h.items():
        if abs(f - k) < 0.07:
            return (str(int(x)) if int(x) else "") + v
    return f"{x:.1f}".replace(".", ",")


def scale(line: str, f: float) -> str:
    """'3 yumurta' -> f katı. Baştaki sayı yoksa ('tuz, karabiber') olduğu gibi kalır."""
    if abs(f - 1) < 1e-9:
        return line
    m = _NUM.match(line.strip())
    if not m:
        return line
    n = m.group(1)
    v = _FR.get(n) or float(n.replace(",", "."))
    return f"{_fmt_n(v * f)} {m.group(2)}"


def factor(r) -> float:
    return (S["kisi"] / r["kisi"]) if S["kisi"] and r["kisi"] else 1.0


def shopping() -> list:
    try:
        with open(LIST_FILE, encoding="utf-8") as f:
            d = json.load(f)
        return [str(x) for x in d][:200] if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def shopping_save(items: list) -> None:
    with open(LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(items[:200], f, ensure_ascii=False)


def shopping_add(r) -> int:
    f = factor(r)
    items = shopping()
    add = [scale(m, f) for m in r["mal"]]
    items += [x for x in add if x not in items]
    shopping_save(items)
    return len(add)


def has_tm(r) -> bool:
    return bool(r.get("tmv") or r.get("tmonly"))


def eff(r):
    """Gösterilecek sürüm: Thermomix açıksa ve tarifin Thermomix sürümü varsa onun kişi/süre/malzeme/adımları."""
    if r and S["tm"] and r.get("tmv"):
        return {**r, **r["tmv"]}
    return r


def cur():
    return eff(BY_ID.get(S["id"]))


def tm_on(r) -> bool:
    return bool(r and (r.get("tmonly") or (S["tm"] and r.get("tmv"))))


def _hiz(h: str) -> str:
    return {"kaşık": "kaşık hızı", "hamur": "hamur modu"}.get(h, "hız " + h.replace(".", ",").replace("-", " ile "))


def tm_text(tm) -> str:
    """Thermomix ayarını okunacak cümleye çevirir: '20 dakika, 100 derece, hız 1, ters dönüş'."""
    if not tm:
        return ""
    p = []
    s = tm.get("s") or 0
    if s:
        m, sn = divmod(int(s), 60)
        p.append(" ".join(x for x in ((f"{m} dakika" if m else ""), (f"{sn} saniye" if sn else "")) if x))
    c = tm.get("c")
    if c:
        p.append("Varoma sıcaklığı" if c == "varoma" else f"{c} derece")
    if tm.get("h"):
        p.append(_hiz(tm["h"]))
    if tm.get("r"):
        p.append("ters dönüş")
    if tm.get("a"):
        p.append({"kelebek": "kelebek takılı", "varoma": "Varoma takılı", "sepet": "pişirme sepeti takılı"}.get(tm["a"], tm["a"]))
    return ", ".join(p)


def card(r) -> dict:
    return {"id": r["id"], "ad": r["ad"], "kat": r["kat"], "dk": r["dk"], "kisi": r["kisi"], "n": len(r["adim"]), "tm": has_tm(r), "tmonly": bool(r.get("tmonly")), "web": r.get("web", "")}


# ------------------------------------------------------------------ internetten tarif (yerleşik listede olmayan yemek)
PENDING = []                                       # normal Jarvis'te 'X tarifi' denince: mod açılınca bu cümle çalışır (scenes_tarif.init_payload)
WEB = []                                         # bu oturumda internetten getirilen tarifler (bellekte; sayfada 'internet' kategorisi)
NOTIFY = None                                      # main.py: NOTIFY(do, say) -> tarif sayfasına iletir ve mod açıksa söyler
_wseq = [0]


def from_web(rec: dict) -> dict:
    """yemek.parse_recipe sonucunu tarif biçimine çevirir; kişi sayısı '4 kişilik' metninden okunur (yoksa ölçekleme kapalı)."""
    import yemek
    rid = "web_" + re.sub(r"[^a-z0-9]+", "", yemek.fold(rec["url"].rstrip("/").split("/")[-1]))[:40]
    m = re.search(r"\d+", rec.get("kisi") or "")
    r = {"id": rid, "ad": rec["ad"], "kat": "internet", "dk": rec.get("dk") or 0, "kisi": int(m.group(0)) if m and 0 < int(m.group(0)) <= 30 else 0,
         "mal": list(rec["mal"]), "adim": [(s, yemek.step_timer(s)) for s in rec["adim"]], "web": rec["url"], "site": rec.get("site", "")}
    if rid not in BY_ID:
        R.append(r)
        WEB.append(r)
    BY_ID[rid] = r
    return r


def web_search(query: str) -> None:
    """Yemek adını yemek.com'da arar, başlığı en çok benzeyen tarifi açar, diğer iki adayı 'internet' kategorisine ekler. Sonuç NOTIFY ile gelir."""
    import threading
    _wseq[0] += 1
    seq = _wseq[0]

    def run():
        import yemek
        from concurrent.futures import ThreadPoolExecutor
        try:
            from rapidfuzz import fuzz
            cand = []
            for start in (0, 3):
                for u, ttl in yemek.search_yemekcom(query, start):
                    if u not in [c[0] for c in cand]:
                        cand.append((u, ttl))
                if len(cand) >= 6:
                    break
            q = yemek.fold(query)
            cand.sort(key=lambda c: -fuzz.token_set_ratio(q, yemek.fold(re.sub(r"^[^:]{2,40}:\s*", "", c[1]))))   # 'Doyurucu Lezzet: X' -> 'X'
            with ThreadPoolExecutor(3) as ex:
                recs = [x for x in ex.map(yemek.fetch_recipe, [c[0] for c in cand[:3]]) if x]
            yemek._save()
            if seq != _wseq[0]:
                return
            if not recs:
                _web_done(None, f"{query} için internette tarif bulamadım efendim. Yemeğin adını farklı söyleyebilir misiniz?")
                return
            rs = [from_web(x) for x in recs]
            S.update(id=rs[0]["id"], step=-1, kisi=0, tm=False)
            r = rs[0]
            sure = f", yaklaşık {r['dk']} dakika" if r["dk"] else ""
            kisi = f", {r['kisi']} kişilik" if r["kisi"] else ""
            alt = f" İnternet kategorisinde {len(rs) - 1} benzer tarif daha var." if len(rs) > 1 else ""
            _web_done(r, f"İnternetten buldum efendim: {r['ad']}{sure}{kisi}, {len(r['adim'])} adım. Malzemeleri ve yapılışını ekranda gösteriyorum; başla derseniz adımları okurum.{alt}")
        except Exception as e:
            print("tarif internet hatası:", type(e).__name__, e, flush=True)
            if seq == _wseq[0]:
                _web_done(None, "İnternete ulaşamadım efendim, bağlantıyı kontrol edip tekrar deneyin.")
    threading.Thread(target=run, daemon=True).start()


def _web_done(r, say: str):
    if NOTIFY:
        try:
            NOTIFY({"data": view(), "busy": ""}, say)
        except Exception as e:
            print("tarif bildirim hatası:", e, flush=True)


def _extra(r) -> dict:
    """Püf noktası, saklama önerisi ve yaklaşık kalori (tarif_extra.py); internetten gelen tariflerde yoktur."""
    try:
        from tarif_extra import INFO
    except Exception:
        return {}
    i = INFO.get(r.get("id"))
    return {"kcal": i[0], "ip": i[1], "sakla": i[2]} if i else {}


def view() -> dict:
    c = cur()
    out = {"list": [card(r) for r in R], "cats": CATS + (["internet"] if WEB else []), "cur": None, "shop": shopping(), "tm": S["tm"]}
    if c:
        f = factor(c)
        out["cur"] = {**card(c), "kisi": S["kisi"] or c["kisi"], "mal": [scale(m, f) for m in c["mal"]], "step": S["step"], "tmon": tm_on(c), "site": c.get("site", ""),
                      "adim": [{"t": a[0], "dk": a[1], "tm": a[2] if len(a) > 2 else None, "tms": tm_text(a[2] if len(a) > 2 else None)} for a in c["adim"]],
                      **_extra(c)}
    return out


def init_payload() -> dict:
    S.update(id=None, step=-1, kisi=0, tm=False)
    return view()


_GENERIC = ("tereyagli", "domates", "peynirli", "corbasi", "çorbası", "pilavi", "pilavı", "salatasi", "salatası", "tatlisi", "tatlısı", "sosu", "hamuru", "kremali", "kremalı")


def find_exact(t: str):
    """Yalnızca tarifin tam adı (ya da kimliği) cümlede geçiyorsa; 'fırında patatesli tavuk tarifi' tavuk sote'ye gitmesin, internette aransın."""
    tt = t.replace("ı", "i")
    for r in sorted(R, key=lambda r: -len(r["ad"])):
        if r["ad"].lower().replace("ı", "i") in tt:
            return r
    words = re.findall(r"\w+", tt)
    for r in R:                                    # kimlik yalnızca cümledeki tek yemek sözcüğüyse ('pilav tarifi' evet, 'bulgur pilavı' hayır)
        if r["kat"] != "internet" and any(re.fullmatch(re.escape(r["id"]) + r"\w{0,4}", w) for w in words) \
                and len([w for w in words if w not in ("tarif", "tarifi", "tarifini", "göster", "aç", "nasil", "nasıl", "yapilir", "yapılır", "bana", "bir")]) <= 1:
            return r
    return None


def find(t: str):
    """Cümleden tarif bulur: tam ad > kimlik > ayırt edici kelime kökü ('ezogelin çorbası' mercimeğe gitmesin diye genel kelimeler az puan alır)."""
    tt = t.replace("ı", "i")
    best, bs = None, 0.0
    for r in R:
        ad = r["ad"].lower().replace("ı", "i")
        words = [w for w in ad.split() if len(w) > 3]
        sc = 10.0 if ad in tt else 5.0 if r["id"] in tt else sum(0.3 if w in _GENERIC else 1.0 for w in words if w[:6] in tt)
        if sc > bs:
            best, bs = r, sc
    return best if bs >= 1.0 else None


def by_ingredient(t: str):
    """Cümledeki malzemelere göre tarifleri sıralar (en çok malzeme eşleşen önce)."""
    toks = [w[:5] for w in t.replace("ı", "i").split() if len(w) > 3]
    sc = []
    for r in R:
        txt = " ".join(r["mal"]).lower().replace("ı", "i")
        n = sum(1 for tk in set(toks) if tk in txt)
        if n:
            sc.append((-n, r["dk"], r))
    return [x[2] for x in sorted(sc, key=lambda x: (x[0], x[1]))]
