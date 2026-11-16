"""Hologram modu komut işleyicisi (sesle/yazıyla). Çıktı: {'do': sayfaya giden komut, 'say': konuşulacak metin}.
İnsan hologramı sayfada çizilir (ui/scene_hologram.html); burada yalnızca cümle -> eklem açısı / renk / animasyon / görünüm dönüşümü yapılır.
Hiçbir şey diske yazılmaz, kamera ya da ağ kullanılmaz."""
import re

import scenes
from scenes_notes import COLORS

PARTS = {  # söz -> sayfadaki renk parçası
    "kafa": "head", "baş": "head", "yüz": "head", "boyun": "neck", "gövde": "torso", "göğüs": "torso", "karın": "torso", "vücut": "torso", "beden": "torso",
    "kol": "arms", "kollar": "arms", "el": "hands", "eller": "hands", "bacak": "legs", "bacaklar": "legs", "ayak": "feet", "ayaklar": "feet",
}
JOINT_WORDS = {"omuz": "shoulder", "dirsek": "elbow", "bilek": "wrist", "kalça": "hip", "diz": "knee", "ayak bileği": "ankle", "boyun": "neck", "kafa": "head", "baş": "head",
               "bel": "chest", "göğüs": "chest", "gövde": "chest"}
EXTRA_COLORS = {"neon yeşil": "#39ff14", "neon mavi": "#1f51ff", "cyan": "#00e5ff", "camgöbeği": "#00e5ff", "buz mavisi": "#9fe8ff", "altın": "#ffc83d", "bordo": "#800020",
                "gümüş": "#cfd8dc", "kızıl": "#ff3b30", "limon": "#e6ff3d", "lila": "#c39bff"}
PRESETS = {"t pozu": "tpose", "t duruşu": "tpose", "normal": "normal", "dik dur": "normal", "hazır ol": "normal", "ayakta": "normal", "otur": "sit", "oturma": "sit",
           "zafer": "victory", "yıldız": "star", "çömel": "squat", "eğil": "bow", "kahraman": "hero", "süper kahraman": "hero", "iron man": "ironman",
           "uçuş": "fly", "uç": "fly", "savaş duruşu": "fight", "dövüş": "fight", "boks": "fight"}
ANIMS = [(r"el salla\w*|selam\w* (ver|salla)|merhaba de", "wave", "El sallıyorum efendim."), (r"yürü\w*", "walk", "Yürüyüş animasyonu efendim."),
         (r"koş\w*", "run", "Koşu animasyonu efendim."), (r"dans\w*|oyna\w*", "dance", "Dans ediyorum efendim, göz kamaştırıcı olacak."),
         (r"nefes\w*", "breathe", "Nefes alıp veriyor efendim."), (r"zıpla\w*", "jump", "Zıplıyorum efendim.")]
STYLES = {"tel kafes": "wire", "tel": "wire", "kafes": "wire", "dolu": "solid", "katı": "solid", "iskelet": "skeleton", "çubuk": "skeleton", "nokta": "points", "noktalar": "points",
          "röntgen": "xray", "x ray": "xray"}


def _color_in(t: str):
    for k in sorted(list(EXTRA_COLORS) + list(COLORS), key=len, reverse=True):
        if re.search(r"\b" + k + r"\b", t):
            return EXTRA_COLORS.get(k) or COLORS[k]
    m = re.search(r"#[0-9a-f]{6}\b", t)
    return m.group(0) if m else None


def _side(t: str):
    if re.search(r"\bsağ\w*", t):
        return "R"
    if re.search(r"\bsol\w*", t):
        return "L"
    return "B"


def _deg(t: str, default: int) -> int:
    n = scenes.num_in(re.sub(r"\b(her )?iki\b|\bbir\b", " ", t))
    return max(0, min(180, n)) if n is not None else default


def hologram(text: str, st: dict):
    t = scenes.norm(text)
    for a, b in (("ayağ", "ayak"), ("dirseğ", "dirsek"), ("bileğ", "bilek"), ("bacağ", "bacak"), ("kolları", "kollar"), ("eklemleri", "eklemler")):
        t = t.replace(a, b)             # ünsüz yumuşaması: dirseği -> dirsek
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar|ne yapabilirsin)\b", t):
        return {"say": "Eklem seçip sağ kolu yana kaldır, dirseği doksan derece bük, kafayı sola çevir diyebilirsiniz. Renk için kafayı kırmızı yap, kolları mavi yap, eklemleri sarı yap, gökkuşağı. "
                       "Duruş için T pozu, otur, zafer, yıldız. Animasyon için yürü, koş, dans et, el salla. Görünüm için tel kafes, dolu, iskelet, röntgen, tara, yakınlaş, öne dön, yan dön."}
    # ---------------------------------------------------------------- sıfırla / tara / gökkuşağı
    if re.search(r"\b(renkler\w* sıfırla|rengi sıfırla|renk sıfırla|renkleri eski)\w*", t):
        return {"do": {"colorReset": True}, "say": "Renkleri sıfırladım efendim."}
    if re.search(r"\b(sıfırla|baştan başla|her şeyi sıfırla|ilk haline)\b", t):
        return {"do": {"reset": True}, "say": "Hologramı ilk haline getirdim efendim."}
    if re.search(r"\b(tara|tarama|tarayalım|analiz et|incele)\w*\b", t) and not re.search(r"\b(kapat|durdur)\b", t):
        return {"do": {"scan": True}, "say": "Tarama başlıyor efendim. Vücut yapısı ve eklem hareketleri analiz ediliyor."}
    if re.search(r"gökkuşağı|rainbow|renk renk|rengarenk", t):
        return {"do": {"rainbow": not re.search(r"\b(kapat|durdur|bitir)\b", t)}, "say": "Gökkuşağı modu efendim." if not re.search(r"\b(kapat|durdur|bitir)\b", t) else "Gökkuşağı modunu kapattım efendim."}
    # ---------------------------------------------------------------- görünüm / kamera
    m = re.search(r"\b(ön|öne|arka|arkaya|yan|yana|üst|üstten|sağdan|soldan|ön taraf|arka taraf)\b.*\b(dön|bak|çevir|göster|görünüm)\w*|\b(ön|arka|yan|üst)\w* (görünüm|görüş)\w*", t)
    if m and not re.search(r"\b(kol|bacak|kafa|baş|boyun|bel|gövde|diz|dirsek|omuz|kalça)\w*", t):
        w = m.group(0)
        view = "back" if "arka" in w else "side" if re.search(r"yan|sağdan|soldan", w) else "top" if "üst" in w else "front"
        return {"do": {"view": view}, "say": {"front": "Önden görünüm efendim.", "back": "Arkadan görünüm efendim.", "side": "Yandan görünüm efendim.", "top": "Üstten görünüm efendim."}[view]}
    if re.search(r"\b(dönmeyi|dönmesini|dönüşü|dönme)\b.*\b(durdur|kapat|dur|kes)\b|\b(durdur|dur)\b.*\b(dön\w*)\b|\bdönme\b$", t):
        return {"do": {"spin": 0}, "say": "Dönmeyi durdurdum efendim."}
    if re.search(r"\b(dön|dönmeye devam|döndür|dönmeyi başlat)\b", t) and not re.search(r"\b(kafa|baş|boyun|bel|gövde)\w*", t):
        sp = 0.2 if re.search(r"yavaş", t) else 1.6 if re.search(r"hızlı", t) else 0.6
        return {"do": {"spin": sp}, "say": "Hologram dönüyor efendim."}
    if re.search(r"\b(yakınlaş|büyüt|yaklaş)\w*", t):
        return {"do": {"zoom": 1.25}, "say": "Yakınlaştım efendim."}
    if re.search(r"\b(uzaklaş|küçült)\w*", t):
        return {"do": {"zoom": 0.8}, "say": "Uzaklaştım efendim."}
    for k, v in STYLES.items():
        if re.search(r"\b" + k + r"\b", t) and re.search(r"\b(yap|göster|aç|geç|modu|stili|görünüm)\b|^" + k + r"$", t):
            return {"do": {"style": v}, "say": f"{k.capitalize()} görünümü efendim."}
    for key, label in (("joints", "eklemleri"), ("labels", "etiketleri"), ("grid", "ızgarayı"), ("hud", "bilgi panelini")):
        word = {"joints": r"eklem\w*", "labels": r"etiket\w*|isim\w*", "grid": r"ızgara\w*|zemin", "hud": r"panel\w*|bilgi\w*|veri\w*"}[key]
        if re.search(r"\b(" + word + r")\b", t) and re.search(r"\b(göster|aç|ekle|görünsün)\b", t) and not re.search(r"\b(renk|yap)\b", t):
            return {"do": {"toggle": {key: True}}, "say": f"{label.capitalize()} gösteriyorum efendim."}
        if re.search(r"\b(" + word + r")\b", t) and re.search(r"\b(gizle|kapat|kaldır|sakla)\b", t):
            return {"do": {"toggle": {key: False}}, "say": f"{label.capitalize()} gizledim efendim."}
    # ---------------------------------------------------------------- renk
    color = _color_in(t)
    if color and re.search(r"\b(yap|boya|olsun|renk|rengi|çevir|dönüştür)\w*", t) or (color and len(t.split()) <= 3):
        tt = t
        if re.search(r"\b(tüm|bütün|her|hepsi\w*|hologram\w*|vücud\w*|vücut\w*|beden\w*|her şey\w*)\b", tt) and not re.search(r"\b(eklem|kol|bacak|kafa|baş|gövde|el|ayak)", tt):
            return {"do": {"color": {"target": "all", "hex": color}}, "say": "Tüm hologramın rengini değiştirdim efendim."}
        if re.search(r"\beklem\w*", tt) and not any(re.search(r"\b" + w + r"\w*", tt) for w in ("dirsek", "diz", "omuz", "bilek", "kalça")):
            return {"do": {"color": {"target": "joints", "hex": color}}, "say": "Eklemlerin rengini değiştirdim efendim."}
        for w, j in JOINT_WORDS.items():
            if re.search(r"\b" + w + r"\w*", tt) and w not in ("kafa", "baş", "boyun", "gövde", "göğüs", "bel"):
                return {"do": {"color": {"target": "joint:" + j, "side": _side(tt), "hex": color}}, "say": f"{w.capitalize()} rengini değiştirdim efendim."}
        for w, part in PARTS.items():
            if re.search(r"\b" + w + r"\w*", tt):
                return {"do": {"color": {"target": part, "side": _side(tt), "hex": color}}, "say": f"{w.capitalize()} rengini değiştirdim efendim."}
        return {"do": {"color": {"target": "all", "hex": color}}, "say": "Hologramın rengini değiştirdim efendim."}
    # ---------------------------------------------------------------- animasyonlar
    if re.search(r"\b(animasyon\w*|hareket\w*)\b.*\b(durdur|kapat|bitir|dur)\b|^(dur|durdur|sabit|hareketsiz)$", t):
        return {"do": {"anim": None}, "say": "Animasyonu durdurdum efendim."}
    for pat, name, say in ANIMS:
        if re.search(r"\b(" + pat + r")", t):
            return {"do": {"anim": name}, "say": say}
    # ---------------------------------------------------------------- eklem hareketi
    side = _side(t)
    d = _deg(t, 0)
    sides = ("R", "L") if side == "B" else (side,)
    if re.search(r"\bdirsek\w*", t):
        if re.search(r"\b(düzelt|aç|indir|uzat|sıfırla)\b", t):
            return {"do": {"joint": [{"j": "elbow", "s": s, "rx": 0, "ry": 0, "rz": 0} for s in sides]}, "say": "Dirseği düzelttim efendim."}
        a = d or 90
        return {"do": {"joint": [{"j": "elbow", "s": s, "rx": -a} for s in sides]}, "say": f"Dirseği {a} derece büktüm efendim."}
    if re.search(r"\bdiz\w*", t):
        if re.search(r"\b(düzelt|aç|indir|uzat|sıfırla)\b", t):
            return {"do": {"joint": [{"j": "knee", "s": s, "rx": 0} for s in sides]}, "say": "Dizi düzelttim efendim."}
        a = d or 90
        return {"do": {"joint": [{"j": "knee", "s": s, "rx": a} for s in sides]}, "say": f"Dizi {a} derece büktüm efendim."}
    if re.search(r"\bbilek\w*", t):
        a = d or 45
        return {"do": {"joint": [{"j": "wrist", "s": s, "rx": -a} for s in sides]}, "say": f"Bileği {a} derece büktüm efendim."}
    if re.search(r"\b(kol|kolu|kolları|kolumu|omuz\w*)\b", t):
        if re.search(r"\b(indir|düzelt|sıfırla|aşağı|salla bırak)\b", t):
            return {"do": {"joint": [{"j": "shoulder", "s": s, "rx": 0, "rz": 0} for s in sides]}, "say": "Kolu indirdim efendim."}
        a = d or (170 if re.search(r"yukarı|tamamen|havaya", t) else 90)
        if re.search(r"\b(öne|ileri|ön)\w*", t):
            return {"do": {"joint": [{"j": "shoulder", "s": s, "rx": -a, "rz": 0} for s in sides]}, "say": f"Kolu öne {a} derece kaldırdım efendim."}
        return {"do": {"joint": [{"j": "shoulder", "s": s, "rz": (-a if s == "R" else a), "rx": 0} for s in sides]}, "say": f"Kolu yana {a} derece kaldırdım efendim."}
    if re.search(r"\b(bacak\w*|kalça\w*)\b", t):
        if re.search(r"\b(indir|düzelt|sıfırla)\b", t):
            return {"do": {"joint": [{"j": "hip", "s": s, "rx": 0, "rz": 0} for s in sides]}, "say": "Bacağı indirdim efendim."}
        a = d or 60
        if re.search(r"\b(yana|aç)\b", t):
            return {"do": {"joint": [{"j": "hip", "s": s, "rz": (-a if s == "R" else a), "rx": 0} for s in sides]}, "say": f"Bacağı yana {a} derece açtım efendim."}
        return {"do": {"joint": [{"j": "hip", "s": s, "rx": -a, "rz": 0} for s in sides]}, "say": f"Bacağı öne {a} derece kaldırdım efendim."}
    if re.search(r"\b(kafa\w*|baş\w*|boyun\w*)\b", t):
        a = d or 40
        if re.search(r"\b(düzelt|sıfırla|ortala|dik)\b", t):
            return {"do": {"joint": [{"j": "neck", "rx": 0, "ry": 0, "rz": 0}]}, "say": "Kafayı düzelttim efendim."}
        if re.search(r"\bsol\w*", t):
            return {"do": {"joint": [{"j": "neck", "ry": a}]}, "say": f"Kafayı sola {a} derece çevirdim efendim."}
        if re.search(r"\bsağ\w*", t):
            return {"do": {"joint": [{"j": "neck", "ry": -a}]}, "say": f"Kafayı sağa {a} derece çevirdim efendim."}
        if re.search(r"\b(öne|aşağı|eğ)\w*", t):
            return {"do": {"joint": [{"j": "neck", "rx": a}]}, "say": f"Kafayı {a} derece öne eğdim efendim."}
        if re.search(r"\b(arkaya|yukarı|geri)\w*", t):
            return {"do": {"joint": [{"j": "neck", "rx": -a}]}, "say": "Kafayı geriye attım efendim."}
    if re.search(r"\b(bel|gövde|göğüs|omurga)\w*", t):
        a = d or 30
        if re.search(r"\b(düzelt|sıfırla|dik)\b", t):
            return {"do": {"joint": [{"j": "chest", "rx": 0, "ry": 0, "rz": 0}]}, "say": "Gövdeyi düzelttim efendim."}
        if re.search(r"\bsol\w*", t):
            return {"do": {"joint": [{"j": "chest", "ry": a}]}, "say": f"Gövdeyi sola {a} derece çevirdim efendim."}
        if re.search(r"\bsağ\w*", t):
            return {"do": {"joint": [{"j": "chest", "ry": -a}]}, "say": f"Gövdeyi sağa {a} derece çevirdim efendim."}
        return {"do": {"joint": [{"j": "chest", "rx": a}]}, "say": f"Gövdeyi {a} derece öne eğdim efendim."}
    # ---------------------------------------------------------------- hazır duruşlar
    for k, v in sorted(PRESETS.items(), key=lambda kv: -len(kv[0])):
        if re.search(r"\b" + k + r"\b", t):
            return {"do": {"preset": v}, "say": f"{k.capitalize()} duruşu efendim."}
    return {"say": "Anlayamadım efendim. Sağ kolu yana kaldır, dirseği bük, kafayı sola çevir, kafayı kırmızı yap, T pozu, yürü, tel kafes ya da tara diyebilirsiniz. Tüm komutlar için yardım deyin."}


def init_payload():
    return {"colors": {"cyan": "#00e5ff"}}
