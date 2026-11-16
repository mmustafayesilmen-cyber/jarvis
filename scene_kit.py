"""Ortak mod/laboratuvar arayüz kiti için komut yardımı: kılavuzdaki (ui/guide.html) örnek komutları ilgili moda göre döner.
Yalnızca okuma yapar; kılavuz değişince bir sonraki istekte yeniden okunur."""
import json
import os
import re

GUIDE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "guide.html")
# sahne türü -> kılavuz bölümü (bölüm içinde başlığında bu sözcük geçen maddeler öne alınır)
SECTION = {"ortam": ("sahneler", "ortam"), "uzay": ("sahneler", "uzay"), "muzik": ("sahneler", "müzik"),
           "fizik": ("fizikmat", "fizik"), "matematik": ("fizikmat", "matematik"),
           "astronomi": ("gokastro", "astronomi"), "jeoloji": ("gokastro", "jeoloji"), "gokyuzu": ("gokastro", "gökyüzü"),
           "kimya": ("kimyalab", ""), "biyoloji": ("biyolab", ""), "notlar": ("notlar", ""), "yuvam": ("yuvam", ""),
           "hologram": ("hologram", ""), "rapor": ("rapor", ""), "sistem": ("sistem", ""), "ders": ("ders", ""),
           "pomodoro": ("pomodoro", ""), "mola": ("mola", ""), "kartlar": ("kartlar", ""), "gelisim": ("gelisim", ""), "satranc": ("satranc", ""), "oyunlar": ("oyunlar", ""), "kuran": ("kuran", ""), "harita": ("harita", ""), "listeler": ("listeler", ""), "vpn": ("vpn", ""), "uyku": ("uyku", ""), "tarif": ("tarif", ""), "spor": ("spor", ""), "panel": ("panel", ""), "telefon": ("telefon", ""), "sinav": ("sinav", ""), "odak": ("odak", ""), "planlama": ("planlama", ""), "nasil": ("nasil", ""), "yemek": ("yemek", ""), "sohbet": ("sohbet", ""),"ultron": ("ultron", ""), "friday": ("friday", ""), "luna": ("luna", ""),"illusion": ("illuzyon", ""), "optik": ("optik", ""), "tahta": ("tahta", ""), "masa": ("masa", ""), "okuma": ("okuma", ""), "kelime": ("kelime", ""), "butce": ("butce", ""), "cark": ("cark", ""), "elektronik": ("elektronik", ""), "baslatici": ("baslatici", ""), "gune": ("gune", ""), "pano": ("pano", ""), "hero": ("kahraman", ""), "zirh": ("zirh", ""), "gorev": ("gorev", ""), "brifing": ("brifing", ""), "starklab": ("starklab", ""), "dunya": ("dunya", ""), "odakoda": ("odakoda", ""), "guvenlik": ("guvenlik", ""), "kopru": ("kopru", "")}
_cache = {"mtime": None, "sections": {}}
_OPENER = re.compile(r"(modu|modunu|laboratuvar\w*|uygulaması\w*|haritası\w*|penceresi\w*)( aç\w*| başlat)?$|^(.*\b(aç|başlat)\b.*\b(mod\w*|laboratuvar\w*)\b.*)$")


def _sections() -> dict:
    mt = os.path.getmtime(GUIDE)
    if _cache["mtime"] == mt:
        return _cache["sections"]
    with open(GUIDE, encoding="utf-8") as f:
        lines = f.read().split("\n")
    out, buf = {}, []

    def flush():
        if not buf:
            return
        s = " ".join(x.strip() for x in buf).rstrip().rstrip(",")
        s = s[:s.rfind("}") + 1] if "}" in s else s
        s = re.sub(r'([{,]\s*)(id|t|items)\s*:', r'\1"\2":', s)
        try:
            d = json.loads(s)
            out[d["id"]] = d
        except ValueError:
            pass
        buf.clear()
    for ln in lines:
        st = ln.strip()
        if st.startswith("{id:"):
            flush()
            buf.append(st)
        elif buf:
            if st.startswith("];") or st.startswith("const ") or st.startswith("</script"):
                flush()
            else:
                buf.append(st)
    flush()
    _cache.update(mtime=mt, sections=out)
    return out


def help_for(kind: str) -> dict:
    """{'title', 'groups': [{'title', 'desc', 'cmds': [...]}]} — bulunamazsa boş gruplar."""
    sec, key = SECTION.get(kind, (kind, ""))
    d = _sections().get(sec)
    if not d:
        return {"title": kind.upper(), "groups": []}
    groups = []
    for it in d.get("items", []):
        if len(it) < 3 or not it[2]:
            continue
        cmds = [str(c) for c in it[2] if not _OPENER.search(str(c))][:40]     # mod içindeyken "X modunu aç" anlamsız
        if cmds:
            groups.append({"title": it[0], "desc": it[1][:220], "cmds": cmds})
    if key:      # o modun maddeleri önce gelsin
        groups.sort(key=lambda g: 0 if key in g["title"].lower() or key in " ".join(g["cmds"]).lower() else 1)
    return {"title": d.get("t", kind.upper()), "groups": groups}
