"""Panel modu komutları: 'hava kutusunu büyüt', 'kur kutusunu gizle', 'müzik kutusunu göster', 'yenile', 'sıfırla', 'bugün ne kadar kullandım', 'dolar kaç'.
Kutucuk boyutu/sırası/gizliliği sayfada tutulur (sürükle-bırak); sesle de değiştirilebilir. Kutucuklar mevcut verileri okur, hiçbir şeyi değiştirmez."""
import re

import panel as P
import scenes


def _tile(t: str):
    for k, pat in P.NAMES.items():
        if re.search(pat, t):
            return k
    return None


def _hm(sec: int) -> str:
    h, m = divmod(sec // 60, 60)
    return (f"{h} saat " if h else "") + f"{m} dakika"


def _panel(text: str, st: dict):
    t = scenes.norm(text)
    if not t:
        return None
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Kutucuğun adını söyleyip büyüt, küçült, gizle ya da göster diyebilirsiniz; örneğin hava kutusunu büyüt. Kutucukları fareyle sürükleyerek de yerleştirebilirsiniz. Yenile ve sıfırla da var."}
    if re.search(r"\b(sıfırla|varsayılan düzen|düzeni sıfırla)\b", t):
        return {"do": {"reset": True}, "say": "Panel düzeni varsayılana döndü efendim."}
    k = _tile(t)
    op = ("big" if re.search(r"büyüt|genişlet|artır", t) else "small" if re.search(r"küçült|daralt", t) else
          "hide" if re.search(r"gizle|kapat|kaldır", t) else "show" if re.search(r"göster|aç|getir|ekle", t) and re.search(r"kutu|kutucuk|panel", t) else None)
    if k and op and re.search(r"kutu|kutucuk|pencere", t):
        return {"do": {"tile": k, "op": op}, "say": {"big": "Büyüttüm", "small": "Küçülttüm", "hide": "Gizledim", "show": "Gösterdim"}[op] + " efendim."}
    if re.search(r"\b(yenile|güncelle)\w*", t):
        return {"do": {"data": P.view()}, "say": ""}
    if k == "sure" and re.search(r"ne kadar|kaç", t):
        import usage
        return {"say": f"Bugün bilgisayarı yaklaşık {_hm(usage.today()['sec'])} kullandınız efendim."}
    return {"do": {"data": P.view()}, "say": "Panel yenilendi efendim. Kutucuk adı ve büyüt, gizle ya da göster diyebilirsiniz."}


panel = _panel


def init_payload():
    return P.init_payload()
