"""Not modu: notlar yalnızca bu bilgisayarda (notes.json) tutulur. Biçimli (süslü) notlar HTML olarak saklanır, ama her kaydetmede ve her gösterimde
beyaz liste süzgecinden geçer: betik, olay işleyici, bağlantı, resim, iframe vb. hiçbir zaman saklanmaz ya da gösterilmez."""
import datetime
import html as _html
import json
import os
import re
import secrets
import tempfile
import threading
from html.parser import HTMLParser

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.json")
MAX_NOTES = 500
MAX_HTML = 120_000
_lock = threading.Lock()

TAGS = {"p", "div", "span", "br", "b", "strong", "i", "em", "u", "s", "strike", "del", "h1", "h2", "h3", "ul", "ol", "li", "blockquote", "hr", "sub", "sup"}
VOID = {"br", "hr"}
DROP_WITH_CONTENT = {"script", "style", "iframe", "object", "embed", "template", "noscript", "svg", "math", "textarea", "select", "button", "form", "title", "head"}
FONTS = {"segoe ui": "Segoe UI", "georgia": "Georgia", "times new roman": "Times New Roman", "courier new": "Courier New", "consolas": "Consolas", "comic sans ms": "Comic Sans MS",
         "trebuchet ms": "Trebuchet MS", "impact": "Impact", "palatino linotype": "Palatino Linotype", "lucida handwriting": "Lucida Handwriting", "brush script mt": "Brush Script MT",
         "verdana": "Verdana", "arial": "Arial", "bahnschrift": "Bahnschrift", "candara": "Candara", "constantia": "Constantia", "ink free": "Ink Free", "segoe script": "Segoe Script"}
_COLOR = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\(\s*\d{1,3}\s*(,\s*\d{1,3}\s*){2}(,\s*(0|1|0?\.\d+)\s*)?\)|[a-zA-Z]{3,20}|transparent)$")
_SIZE = re.compile(r"^(\d{1,2}(\.\d)?)px$")
_KEYSIZE = {"xx-small", "x-small", "small", "medium", "large", "x-large", "xx-large", "xxx-large"}
_BORDER = re.compile(r"^\d{1,2}px (solid|dashed|dotted|double) (#[0-9a-fA-F]{3,8}|rgba?\([\d\s,.]+\)|[a-zA-Z]{3,20})$")
_PX = re.compile(r"^-?\d{1,3}(\.\d)?px$")


def _style_ok(name: str, val: str):
    name, val = name.strip().lower(), val.strip()
    if not val or len(val) > 90 or any(c in val for c in "\\;{}<>@") or "url(" in val.lower() or "expression" in val.lower():
        return None
    if name in ("color", "background-color", "border-color"):
        return val if _COLOR.match(val) else None
    if name == "font-family":
        first = val.split(",")[0].strip().strip("'\"").lower()
        return f"'{FONTS[first]}'" if first in FONTS else None
    if name == "font-size":
        m = _SIZE.match(val)
        if m:
            return val if 8 <= float(m.group(1)) <= 96 else None
        return val if val in _KEYSIZE else None
    if name == "font-weight":
        return val if val in ("bold", "normal", "bolder", "lighter") or re.fullmatch(r"[1-9]00", val) else None
    if name == "font-style":
        return val if val in ("italic", "normal", "oblique") else None
    if name == "text-decoration" or name == "text-decoration-line":
        return val if re.fullmatch(r"(underline|line-through|none|overline)( (underline|line-through|overline))*", val) else None
    if name == "text-align":
        return val if val in ("left", "right", "center", "justify") else None
    if name in ("border", "border-left", "border-right", "border-top", "border-bottom"):
        return val if _BORDER.match(val) else None
    if name == "border-radius":
        m = _PX.match(val)
        return val if m and 0 <= float(val[:-2]) <= 60 else None
    if name in ("padding", "padding-left", "padding-right", "padding-top", "padding-bottom", "margin", "margin-left", "margin-top", "margin-bottom", "margin-right"):
        return val if _PX.match(val) and -20 <= float(val[:-2]) <= 80 else None
    if name == "line-height":
        return val if re.fullmatch(r"\d(\.\d{1,2})?", val) else None
    if name == "letter-spacing":
        return val if _PX.match(val) and abs(float(val[:-2])) <= 12 else None
    return None


def clean_style(style: str) -> str:
    out = []
    for decl in style.split(";"):
        if ":" not in decl:
            continue
        n, v = decl.split(":", 1)
        ok = _style_ok(n, v)
        if ok is not None:
            out.append(f"{n.strip().lower()}: {ok}")
    return "; ".join(out)


class _Clean(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0
        self.stack = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.skip:
            if tag in DROP_WITH_CONTENT:
                self.skip += 1
            return
        if tag in DROP_WITH_CONTENT:
            self.skip = 1
            return
        if tag == "font":                 # eski biçimleme: renk/boyutu stile çevir
            d = dict(attrs)
            st = []
            if d.get("color"):
                st.append(f"color: {d['color']}")
            if d.get("face"):
                st.append(f"font-family: {d['face']}")
            tag, attrs = "span", [("style", "; ".join(st))]
        if tag not in TAGS:
            return
        style = ""
        for k, v in attrs:
            if k.lower() == "style" and v:
                style = clean_style(v)
        self.out.append(f"<{tag}" + (f' style="{_html.escape(style, quote=True)}"' if style else "") + ">")
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.skip:
            if tag in DROP_WITH_CONTENT:
                self.skip -= 1
            return
        if tag == "font":
            tag = "span"
        if tag in TAGS and tag not in VOID and tag in self.stack:
            while self.stack:
                t = self.stack.pop()
                self.out.append(f"</{t}>")
                if t == tag:
                    break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(_html.escape(data, quote=False))

    def result(self):
        while self.stack:
            self.out.append(f"</{self.stack.pop()}>")
        return "".join(self.out)


def sanitize(raw: str) -> str:
    """Biçimli not HTML'ini beyaz listeye göre temizler (uzunluk sınırlı)."""
    raw = (raw or "")[:MAX_HTML * 2]
    p = _Clean()
    try:
        p.feed(raw)
        p.close()
    except Exception:
        return _html.escape(re.sub(r"<[^>]*>", " ", raw))[:MAX_HTML]
    return p.result()[:MAX_HTML]


def plain(html_: str) -> str:
    t = re.sub(r"<(br|/p|/div|/li|/h[1-3])[^>]*>", "\n", html_ or "")
    t = re.sub(r"<[^>]+>", "", t)
    return " ".join(_html.unescape(t).split())


def _color(c: str) -> str:
    c = (c or "").strip()
    return c if re.fullmatch(r"#[0-9a-fA-F]{3,8}", c) else ""


def _load() -> list:
    try:
        with open(PATH, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _save(items: list) -> None:
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(PATH), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(items[-MAX_NOTES:], f, ensure_ascii=False, indent=1)
        os.replace(tmp, PATH)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def listing() -> list:
    """Sayfaya gidecek liste (yeniden süzülmüş), en yeni en üstte."""
    out = []
    for n in _load():
        out.append({"id": n.get("id", ""), "title": str(n.get("title", ""))[:120], "html": sanitize(n.get("html", "")), "bg": _color(n.get("bg", "")),
                    "ts": n.get("ts", ""), "mod": n.get("mod", ""), "src": n.get("src", "kullanıcı")})
    out.sort(key=lambda x: x["mod"] or x["ts"], reverse=True)
    return out


def save(note_id: str, title: str, html_: str, bg: str = "", src: str = "kullanıcı") -> dict:
    """Notu oluşturur ya da günceller; kaydedilen notu döndürür."""
    html_ = sanitize(html_)
    title = " ".join(str(title or "").split())[:120] or (plain(html_)[:40] or "Başlıksız not")
    with _lock:
        items = _load()
        cur = next((n for n in items if n.get("id") == note_id), None) if note_id and re.fullmatch(r"n[0-9a-f]{8}", note_id) else None
        if cur is None:
            cur = {"id": "n" + secrets.token_hex(4), "ts": _now(), "src": src if src in ("kullanıcı", "jarvis") else "kullanıcı"}
            items.append(cur)
        cur.update(title=title, html=html_, bg=_color(bg), mod=_now())
        _save(items)
    return {"id": cur["id"], "title": title}


def add_text(text: str, src: str = "jarvis") -> dict:
    """Düz metinden hızlı not (örn. 'not al: yarın sınav var')."""
    text = " ".join(str(text or "").split())[:2000]
    if not text:
        return {}
    return save("", text[:40], "<p>" + _html.escape(text, quote=False) + "</p>", "", src)


def append_html(note_id: str, fragment: str) -> bool:
    with _lock:
        items = _load()
        cur = next((n for n in items if n.get("id") == note_id), None)
        if not cur:
            return False
        cur["html"] = sanitize(cur.get("html", "") + sanitize(fragment))
        cur["mod"] = _now()
        _save(items)
    return True


def delete(note_id: str) -> bool:
    with _lock:
        items = _load()
        keep = [n for n in items if n.get("id") != note_id]
        if len(keep) == len(items):
            return False
        _save(keep)
    return True


def delete_all() -> int:
    with _lock:
        n = len(_load())
        _save([])
    return n


def find(query: str):
    """Başlığı ya da içeriği sorguyla eşleşen ilk not (en yeniden başlayarak)."""
    q = " ".join((query or "").lower().split())
    if not q:
        return None
    for n in listing():
        if q in n["title"].lower() or q in plain(n["html"]).lower():
            return n
    return None


def init_payload():
    import memory
    return {"notes": listing(), "facts": _facts(), "fonts": sorted(set(FONTS.values()))}


def _facts():
    import memory
    return [{"i": i, "fact": x.get("fact", ""), "date": x.get("date", "")} for i, x in enumerate(memory._load())]
