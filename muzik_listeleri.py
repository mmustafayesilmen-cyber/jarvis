"""Müzik listeleri: adlı çalma listeleri (muzik_listeleri.json, yalnızca bu bilgisayarda). Şarkı bir ad ya da YouTube bağlantısıyla eklenir; ad aranınca
bulunan ilk sonuç eklenir ve kayda gerçek adı/sanatçısı/süresi yazılır. Çalma Jarvis'in kendi oynatıcısında (study_music: yt-dlp + ffplay, tarayıcı gerekmez) yapılır.
Sayfadan gelen her değer burada doğrulanır ve sınırlanır. Zaman alan işler (arama) çağıran tarafından arka planda çalıştırılmalıdır."""
import json
import os
import re
import secrets
import threading
import time

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "muzik_listeleri.json")
MAX_LISTS, MAX_SONGS, MAX_NAME = 50, 500, 40
_lock = threading.RLock()
S = {"sel": None, "busy": "", "playing": None}          # sel: seçili liste kimliği; busy: ekranda gösterilen iş metni; playing: çalan liste kimliği
_VID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _name(v, n=MAX_NAME) -> str:
    return " ".join("".join(ch for ch in str(v or "") if ch.isprintable()).split())[:n]


def _load() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            raise ValueError
    except (OSError, ValueError):
        d = {}
    L = []
    for x in d.get("lists", []) if isinstance(d.get("lists"), list) else []:
        if isinstance(x, dict) and re.fullmatch(r"l[0-9a-f]{8}", str(x.get("id", ""))):
            songs = [{"id": s["id"], "title": _name(s.get("title"), 200) or s["id"], "artist": _name(s.get("artist"), 100), "dur": int(s.get("dur") or 0)}
                     for s in x.get("songs", []) if isinstance(s, dict) and _VID.match(str(s.get("id", "")))][:MAX_SONGS]
            L.append({"id": x["id"], "name": _name(x.get("name")) or "Liste", "songs": songs})
    return {"lists": L[:MAX_LISTS]}


def _save(d: dict) -> None:
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PATH)


def _get(d: dict, lid):
    return next((x for x in d["lists"] if x["id"] == lid), None)


def find(d: dict, text: str):
    """Ad ya da kimlikle liste bul: tam eşleşme, sonra 'içerir' (Türkçe büyük/küçük harf duyarsız). Birden çok eşleşmede None."""
    q = _name(text).replace("İ", "i").replace("I", "ı").lower()
    q = re.sub(r"\s*(listesi|listem|listemi|listeyi|liste)$", "", q).strip()
    if not q:
        return None
    low = lambda s: s.replace("İ", "i").replace("I", "ı").lower()
    ex = [x for x in d["lists"] if low(x["name"]) == q or x["id"] == text]
    if len(ex) == 1:
        return ex[0]
    part = [x for x in d["lists"] if q in low(x["name"])]
    return part[0] if len(part) == 1 else None


# ------------------------------------------------------------------ listeler
def create(name: str) -> dict:
    name = _name(name)
    if not name:
        return {}
    with _lock:
        d = _load()
        low = name.replace("İ", "i").replace("I", "ı").lower()
        ex = next((x for x in d["lists"] if x["name"].replace("İ", "i").replace("I", "ı").lower() == low), None)
        if ex:
            S["sel"] = ex["id"]
            return {**ex, "existed": True}
        if len(d["lists"]) >= MAX_LISTS:
            return {}
        x = {"id": "l" + secrets.token_hex(4), "name": name, "songs": []}
        d["lists"].append(x)
        _save(d)
        S["sel"] = x["id"]
        return x


def rename(lid: str, name: str) -> bool:
    name = _name(name)
    with _lock:
        d = _load()
        x = _get(d, lid)
        if not x or not name:
            return False
        x["name"] = name
        _save(d)
        return True


def delete(lid: str) -> int:
    """Listeyi siler; içindeki şarkı sayısını döner (-1: yok)."""
    with _lock:
        d = _load()
        x = _get(d, lid)
        if not x:
            return -1
        d["lists"] = [y for y in d["lists"] if y["id"] != lid]
        _save(d)
        if S["sel"] == lid:
            S["sel"] = d["lists"][0]["id"] if d["lists"] else None
        return len(x["songs"])


def select(lid) -> bool:
    with _lock:
        d = _load()
        if lid is None or _get(d, lid):
            S["sel"] = lid
            return True
        return False


# ------------------------------------------------------------------ şarkılar
def add_item(lid: str, item: dict):
    """Çözülmüş şarkıyı ekler: 'added' | 'dup' | 'full' | None (liste yok)."""
    if not isinstance(item, dict) or not _VID.match(str(item.get("id", ""))):
        return None
    with _lock:
        d = _load()
        x = _get(d, lid)
        if not x:
            return None
        if any(s["id"] == item["id"] for s in x["songs"]):
            return "dup"
        if len(x["songs"]) >= MAX_SONGS:
            return "full"
        x["songs"].append({"id": item["id"], "title": _name(item.get("title"), 200) or item["id"], "artist": _name(item.get("artist"), 100), "dur": int(item.get("dur") or 0)})
        _save(d)
        return "added"


def add_many(lid: str, items: list) -> int:
    n = 0
    for it in items:
        if add_item(lid, it) == "added":
            n += 1
    return n


def resolve(text: str):
    """Kullanıcının yazdığı ad ya da bağlantı -> şarkı ({'id','title','artist','dur'}), çalma listesi ({'playlist': (ad, [şarkılar])}) ya da None.
    Ağ işi: birkaç saniye sürer, arka planda çağırın. Bağlantıysa yalnızca youtube.com / youtu.be kabul edilir."""
    import study_music
    t = " ".join(str(text).split())[:300]
    if not t:
        return None
    if re.match(r"^https?://", t, re.I):
        pl = study_music.resolve_playlist(t) if "list=" in t and "v=" not in t else None
        if pl:
            return {"playlist": pl}
        return study_music.resolve_url(t)
    return study_music.resolve(t)


def remove_song(lid: str, ref):
    """ref: 1'den başlayan sıra numarası (int) ya da YouTube kimliği (str). Silinen şarkıyı döner (yoksa None)."""
    with _lock:
        d = _load()
        x = _get(d, lid)
        if not x:
            return None
        i = None
        if isinstance(ref, int) and 1 <= ref <= len(x["songs"]):
            i = ref - 1
        elif isinstance(ref, str):
            i = next((k for k, s in enumerate(x["songs"]) if s["id"] == ref), None)
        if i is None:
            return None
        s = x["songs"].pop(i)
        _save(d)
        return s


def move_song(lid: str, i: int, j: int) -> bool:
    """Şarkıyı i. sıradan j. sıraya taşır (0'dan başlayan indisler)."""
    with _lock:
        d = _load()
        x = _get(d, lid)
        n = len(x["songs"]) if x else 0
        if not x or not (0 <= i < n and 0 <= j < n):
            return False
        x["songs"].insert(j, x["songs"].pop(i))
        _save(d)
        return True


def find_song(x: dict, text: str):
    """Listede addan şarkı bul (içerir, harf duyarsız). Tek eşleşme yoksa None."""
    low = lambda s: s.replace("İ", "i").replace("I", "ı").lower()
    q = low(_name(text))
    if not q:
        return None
    hits = [s for s in x["songs"] if q in low(s["title"]) or q in low(s["artist"])]
    return hits[0] if len(hits) == 1 else None


# ------------------------------------------------------------------ çalma
def play(lid: str, start: int = 0, shuffle: bool = False, loop: bool = True) -> int:
    """Listeyi Jarvis'in oynatıcısında çalar. Dönen: çalınan şarkı sayısı (0: liste yok ya da boş)."""
    import study_music
    with _lock:
        d = _load()
        x = _get(d, lid)
        if not x or not x["songs"]:
            return 0
        S["sel"], S["playing"] = lid, lid
    return study_music.play_items(x["songs"], loop=loop, start=start, shuffle=shuffle)


def stats_of(x: dict) -> dict:
    return {"songs": len(x["songs"]), "dur": sum(s["dur"] for s in x["songs"])}


def view(np=None) -> dict:
    with _lock:
        d = _load()
        if S["sel"] is None or not _get(d, S["sel"]):
            S["sel"] = d["lists"][0]["id"] if d["lists"] else None
        return {"lists": [{"id": x["id"], "name": x["name"], **stats_of(x)} for x in d["lists"]], "sel": S["sel"],
                "songs": next((x["songs"] for x in d["lists"] if x["id"] == S["sel"]), []), "playing": S["playing"], "busy": S["busy"]}
