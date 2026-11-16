"""Yuvam modu: ev eşyalarının odası / mobilyası / çekmecesi kaydedilir ve bulunur (telefon uygulaması Yuvam ile aynı veri modeli).
Her şey yalnızca bu bilgisayarda (yuvam.json) tutulur. Sayfadan ya da sesle gelen her değer burada doğrulanır, uzunluğu sınırlanır;
fotoğraflar yalnızca küçük JPEG data-URL olarak kabul edilir. Yuvam uygulamasının yedeği (version 1) içe aktarılabilir."""
import json
import os
import re
import secrets
import tempfile
import threading
import time

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yuvam.json")
BACKUP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yuvam_yedek.json")
_lock = threading.RLock()
MAX_ITEMS, MAX_ROOMS, MAX_LOCS, MAX_HISTORY, MAX_CATS = 3000, 60, 1500, 6000, 40
MAX_IMG = 220_000                        # bir fotoğraf için en fazla ~220 KB (sayfa 720 px'e küçültüp gönderir)
_IMG = re.compile(r"^data:image/jpeg;base64,[A-Za-z0-9+/]+={0,2}$")
_ID = re.compile(r"^[A-Za-z0-9]{4,24}$")

DEFAULT_CATEGORIES = [("Elektronik", "headphones"), ("Mutfak", "silverware-fork-knife"), ("Kıyafet", "tshirt-crew"), ("Kitap", "book-open-variant"),
                      ("Belgeler", "file-document-outline"), ("Mobilya", "sofa-outline"), ("Oyuncak", "teddy-bear"), ("Alet", "hammer-wrench"),
                      ("Kişisel", "account-outline"), ("Diğer", "shape-outline")]
SUGGESTED_ROOMS = ["Salon", "Mutfak", "Yatak Odası", "Çalışma Odası", "Banyo", "Depo", "Garaj"]


# ------------------------------------------------------------------ yardımcılar
def normalize(s: str) -> str:
    """'Çekmece' -> 'cekmece' (Yuvam'daki text.ts ile aynı)."""
    s = str(s).replace("İ", "i").replace("I", "ı").lower()
    for a, b in (("ı", "i"), ("ş", "s"), ("ğ", "g"), ("ü", "u"), ("ö", "o"), ("ç", "c")):
        s = s.replace(a, b)
    return s.strip()


def _uid() -> str:
    return "y" + secrets.token_hex(6)


def _now() -> int:
    return int(time.time() * 1000)


def _s(v, n=200) -> str:
    return " ".join(str(v if v is not None else "").replace("\x00", " ").split())[:n]


def _text(v, n=1500) -> str:
    """Satır sonlarını koruyan metin (nasıl bulunur adımları için)."""
    lines = [" ".join(l.split()) for l in str(v if v is not None else "").replace("\x00", " ").replace("\r", "").split("\n")]
    return "\n".join(l for l in lines if l)[:n]


def _id(v, allow_empty=True) -> str:
    v = str(v or "")
    return v if _ID.match(v) else ""


def _img(v) -> str:
    v = str(v or "")
    return v if len(v) <= MAX_IMG and _IMG.match(v) else ""


def _num(v, lo, hi, default=0.0) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return min(hi, max(lo, x)) if x == x else default


def _pin(v):
    if isinstance(v, dict) and "x" in v and "y" in v:
        return {"x": round(_num(v["x"], 0, 1), 4), "y": round(_num(v["y"], 0, 1), 4)}
    return None


def _initial() -> dict:
    return {"version": 1, "onboarded": True, "user": {"id": _uid(), "name": "Misafir", "email": ""}, "rooms": [],
            "categories": [{"id": _uid(), "name": n, "icon": i} for n, i in DEFAULT_CATEGORIES], "locations": [], "items": [], "history": []}


def _load() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and d.get("version") == 1 and isinstance(d.get("items"), list):
            return _clean(d)
    except (OSError, ValueError):
        pass
    return _initial()


def _save(d: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(PATH), suffix=".tmp")
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


def _clean(d: dict) -> dict:
    """Dosyadan ya da yedekten gelen veriyi alan alan doğrular; tanımsız alanları atar."""
    def lst(k, mx):
        v = d.get(k)
        return [x for x in v if isinstance(x, dict)][:mx] if isinstance(v, list) else []
    out = _initial()
    u = d.get("user") if isinstance(d.get("user"), dict) else {}
    out["user"] = {"id": _id(u.get("id")) or _uid(), "name": _s(u.get("name"), 40) or "Misafir", "email": _s(u.get("email"), 80)}
    out["rooms"] = [{"id": _id(r.get("id")) or _uid(), "name": _s(r.get("name"), 40) or "Oda", "image": _img(r.get("image")) or None,
                     "createdAt": int(_num(r.get("createdAt"), 0, 4e12, _now()))} for r in lst("rooms", MAX_ROOMS)]
    cats = [{"id": _id(c.get("id")) or _uid(), "name": _s(c.get("name"), 30) or "Diğer", "icon": re.sub(r"[^a-z\-]", "", str(c.get("icon", ""))[:30]) or "tag-outline"}
            for c in lst("categories", MAX_CATS)]
    if cats:
        out["categories"] = cats
    rooms = {r["id"] for r in out["rooms"]}
    out["locations"] = [{"id": _id(l.get("id")) or _uid(), "roomId": _id(l.get("roomId")), "name": _s(l.get("name"), 40) or "Konum",
                         "parentId": _id(l.get("parentId")) or None} for l in lst("locations", MAX_LOCS) if _id(l.get("roomId")) in rooms]
    locs = {l["id"] for l in out["locations"]}
    cat_ids = {c["id"] for c in out["categories"]}
    items = []
    for i in lst("items", MAX_ITEMS):
        rid = _id(i.get("roomId"))
        if rid not in rooms:
            continue
        lid = _id(i.get("locationId"))
        cid = _id(i.get("categoryId"))
        items.append({"id": _id(i.get("id")) or _uid(), "name": _s(i.get("name"), 80) or "Eşya", "image": _img(i.get("image")) or None,
                      "categoryId": cid if cid in cat_ids else None, "roomId": rid, "locationId": lid if lid in locs else None,
                      "description": _text(i.get("description"), 600), "howToFind": _text(i.get("howToFind"), 800),
                      "tags": [_s(t, 20) for t in (i.get("tags") if isinstance(i.get("tags"), list) else [])][:10],
                      "isFavorite": bool(i.get("isFavorite")), "pin": _pin(i.get("pin")),
                      "lastViewedAt": int(_num(i.get("lastViewedAt"), 0, 4e12)) or None, "viewCount": int(_num(i.get("viewCount"), 0, 1e6)),
                      "createdAt": int(_num(i.get("createdAt"), 0, 4e12, _now())), "updatedAt": int(_num(i.get("updatedAt"), 0, 4e12, _now()))})
    out["items"] = items
    ids = {i["id"] for i in items}
    out["history"] = [{"id": _id(h.get("id")) or _uid(), "itemId": _id(h.get("itemId")), "previousLocation": _s(h.get("previousLocation"), 200),
                       "newLocation": _s(h.get("newLocation"), 200), "changedAt": int(_num(h.get("changedAt"), 0, 4e12, _now()))}
                      for h in lst("history", MAX_HISTORY) if _id(h.get("itemId")) in ids]
    return out


# ------------------------------------------------------------------ konum zinciri (location.ts)
def chain(d: dict, loc_id):
    out, seen, cur = [], set(), next((l for l in d["locations"] if l["id"] == loc_id), None) if loc_id else None
    while cur and cur["id"] not in seen:
        seen.add(cur["id"])
        out.insert(0, cur)
        pid = cur["parentId"]
        cur = next((l for l in d["locations"] if l["id"] == pid), None) if pid else None
    return out


def path_names(d: dict, item: dict) -> list:
    room = next((r for r in d["rooms"] if r["id"] == item["roomId"]), None)
    return [room["name"] if room else "Bilinmeyen oda"] + [l["name"] for l in chain(d, item["locationId"])]


def path_label(names, sep=" → ") -> str:
    return sep.join(names)


def resolve_path(d: dict, room_id: str, segments) -> str:
    """Konum adlarını bulur ya da oluşturur; yaprak konumun id'sini döndürür."""
    parent = None
    for raw in segments[:6]:
        name = _s(raw, 40)
        if not name:
            continue
        f = next((l for l in d["locations"] if l["roomId"] == room_id and l["parentId"] == parent and normalize(l["name"]) == normalize(name)), None)
        if f is None:
            if len(d["locations"]) >= MAX_LOCS:
                break
            f = {"id": _uid(), "roomId": room_id, "name": name, "parentId": parent}
            d["locations"].append(f)
        parent = f["id"]
    return parent


def _with_history(d: dict, before_label: str, item: dict):
    after = path_label(path_names(d, item))
    if before_label != after:
        d["history"].append({"id": _uid(), "itemId": item["id"], "previousLocation": before_label, "newLocation": after, "changedAt": _now()})
        del d["history"][:-MAX_HISTORY]


# ------------------------------------------------------------------ arama (search.ts)
def _stem_hit(text: str, t: str) -> bool:
    if t in text:
        return True
    if len(t) < 6:
        return False
    for n in range(len(t) - 1, max(5, len(t) - 4) - 1, -1):
        if t[:n] in text:
            return True
    return False


def search(d: dict, query: str) -> list:
    tokens = normalize(query).split()
    if not tokens:
        return []
    scored = []
    for it in d["items"]:
        cat = next((c["name"] for c in d["categories"] if c["id"] == it["categoryId"]), "")
        name = normalize(it["name"])
        rest = normalize(" ".join([cat, *path_names(d, it), it["description"], it["howToFind"], *it["tags"]]))
        score, ok = 0.0, True
        for t in tokens:
            if t in name:
                score += 3 if name.startswith(t) else 2
            elif t in rest:
                score += 1
            elif _stem_hit(name, t):
                score += 1.5
            elif _stem_hit(rest, t):
                score += 0.5
            else:
                ok = False
                break
        if ok:
            scored.append((score, it))
    scored.sort(key=lambda s: (-s[0], -s[1]["updatedAt"]))
    return [s[1] for s in scored]


# ------------------------------------------------------------------ sayfaya giden görünüm
def view() -> dict:
    with _lock:
        d = _load()
    return {"data": d, "rooms_suggest": SUGGESTED_ROOMS}


def init_payload():
    return view()


def stats() -> dict:
    d = _load()
    return {"items": len(d["items"]), "rooms": len(d["rooms"]), "favorites": sum(1 for i in d["items"] if i["isFavorite"])}


# ------------------------------------------------------------------ işlemler (AppContext.tsx)
def _find_room(d, name):
    n = normalize(name)
    r = next((r for r in d["rooms"] if normalize(r["name"]) == n), None)
    if r is None and len(n) >= 3:   # "salonda" -> Salon
        r = next((r for r in d["rooms"] if normalize(r["name"]).split()[0][:max(3, len(normalize(r["name"]).split()[0]) - 1)] == n[:max(3, len(normalize(r["name"]).split()[0]) - 1)]), None)
    return r


def add_room(name: str, image: str = "") -> dict:
    name = _s(name, 40)
    if not name:
        return {}
    with _lock:
        d = _load()
        ex = next((r for r in d["rooms"] if normalize(r["name"]) == normalize(name)), None)
        if ex:
            return ex
        if len(d["rooms"]) >= MAX_ROOMS:
            return {}
        r = {"id": _uid(), "name": name, "image": _img(image) or None, "createdAt": _now()}
        d["rooms"].append(r)
        _save(d)
    return r


def update_room(room_id: str, name=None, image=None) -> bool:
    with _lock:
        d = _load()
        r = next((r for r in d["rooms"] if r["id"] == room_id), None)
        if not r:
            return False
        if name is not None and _s(name, 40):
            r["name"] = _s(name, 40)
        if image is not None:
            r["image"] = _img(image) or None
        _save(d)
    return True


def delete_room(room_id: str) -> bool:
    """Odayı yalnızca içinde eşya yoksa siler (Yuvam'da da oda silme yok; bu ek güvenlik)."""
    with _lock:
        d = _load()
        if any(i["roomId"] == room_id for i in d["items"]) or not any(r["id"] == room_id for r in d["rooms"]):
            return False
        d["rooms"] = [r for r in d["rooms"] if r["id"] != room_id]
        d["locations"] = [l for l in d["locations"] if l["roomId"] != room_id]
        _save(d)
    return True


def add_category(name: str) -> dict:
    name = _s(name, 30)
    if not name:
        return {}
    with _lock:
        d = _load()
        ex = next((c for c in d["categories"] if normalize(c["name"]) == normalize(name)), None)
        if ex or len(d["categories"]) >= MAX_CATS:
            return ex or {}
        c = {"id": _uid(), "name": name, "icon": "tag-outline"}
        d["categories"].append(c)
        _save(d)
    return c


def _item_from(d: dict, inp: dict, base=None):
    rid = _id(inp.get("roomId"))
    if not any(r["id"] == rid for r in d["rooms"]):
        return None
    cid = _id(inp.get("categoryId"))
    seg = [_s(x, 40) for x in (inp.get("locationPath") or []) if isinstance(x, str)][:6] if isinstance(inp.get("locationPath"), list) else []
    now = _now()
    it = dict(base) if base else {"id": _uid(), "tags": [], "viewCount": 0, "lastViewedAt": None, "createdAt": now}
    it.update(name=_s(inp.get("name"), 80), image=_img(inp.get("image")) or None, categoryId=cid if any(c["id"] == cid for c in d["categories"]) else None,
              roomId=rid, locationId=resolve_path(d, rid, seg), description=_text(inp.get("description"), 600), howToFind=_text(inp.get("howToFind"), 800),
              isFavorite=bool(inp.get("isFavorite")), pin=_pin(inp.get("pin")), updatedAt=now)
    return it if it["name"] else None


def add_item(inp: dict):
    with _lock:
        d = _load()
        if len(d["items"]) >= MAX_ITEMS:
            return None
        it = _item_from(d, inp)
        if not it:
            return None
        d["items"].insert(0, it)
        _save(d)
    return it


def update_item(item_id: str, inp: dict):
    with _lock:
        d = _load()
        old = next((i for i in d["items"] if i["id"] == item_id), None)
        if not old:
            return None
        before = path_label(path_names(d, old))
        it = _item_from(d, inp, old)
        if not it:
            return None
        d["items"] = [it if i["id"] == item_id else i for i in d["items"]]
        _with_history(d, before, it)
        _save(d)
    return it


def move_item(item_id: str, room_id: str, path, pin=None):
    with _lock:
        d = _load()
        it = next((i for i in d["items"] if i["id"] == item_id), None)
        if not it or not any(r["id"] == room_id for r in d["rooms"]):
            return None
        before = path_label(path_names(d, it))
        it["roomId"] = room_id
        it["locationId"] = resolve_path(d, room_id, [_s(x, 40) for x in path][:6])
        it["pin"] = _pin(pin)
        it["updatedAt"] = _now()
        _with_history(d, before, it)
        _save(d)
    return it


def mark_viewed(item_id: str) -> None:
    with _lock:
        d = _load()
        it = next((i for i in d["items"] if i["id"] == item_id), None)
        if it:
            it["lastViewedAt"] = _now()
            it["viewCount"] = (it.get("viewCount") or 0) + 1
            _save(d)


def toggle_favorite(item_id: str):
    with _lock:
        d = _load()
        it = next((i for i in d["items"] if i["id"] == item_id), None)
        if not it:
            return None
        it["isFavorite"] = not it["isFavorite"]
        _save(d)
    return it["isFavorite"]


def delete_item(item_id: str) -> bool:
    with _lock:
        d = _load()
        keep = [i for i in d["items"] if i["id"] != item_id]
        if len(keep) == len(d["items"]):
            return False
        d["items"] = keep
        d["history"] = [h for h in d["history"] if h["itemId"] != item_id]
        _save(d)
    return True


def set_user(name: str) -> None:
    with _lock:
        d = _load()
        d["user"]["name"] = _s(name, 40) or d["user"]["name"]
        _save(d)


def reset_all() -> None:
    with _lock:
        _save(_initial())


def export_backup() -> str:
    """Yuvam uygulamasının yedek biçimiyle aynı; jarvis klasörüne yuvam_yedek.json olarak yazılır."""
    with _lock:
        d = _load()
        with open(BACKUP, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    return BACKUP


def import_backup(text: str) -> int:
    """Yuvam uygulamasından alınan yedek metnini (JSON) doğrulayıp mevcut verinin yerine koyar; eşya sayısını döndürür, geçersizse -1."""
    try:
        d = json.loads(text)
    except ValueError:
        return -1
    if not isinstance(d, dict) or d.get("version") != 1 or not isinstance(d.get("items"), list) or not isinstance(d.get("rooms"), list):
        return -1
    with _lock:
        out = _clean(d)
        _save(out)
    return len(out["items"])


def import_backup_file() -> int:
    """jarvis klasöründeki yuvam_yedek.json dosyasını içe aktarır (-2: dosya yok)."""
    try:
        with open(BACKUP, encoding="utf-8") as f:
            return import_backup(f.read(3_000_000))
    except OSError:
        return -2
