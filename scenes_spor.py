"""Spor modu komutları: 'basketbol', 'voleybol maçları', 'yarınki maçlar', 'dünün sonuçları', 'canlı maçlar', 'Fenerbahçe maçı', 'Süper Lig', 'yenile'."""
import re

import scenes
import spor as P

_SPORT = [("futbol", r"futbol\w*|\bfut\b|\bmaç\w* futbol"), ("basketbol", r"basket\w*|nba|euroleague"), ("voleybol", r"voleybol\w*|sultanlar|filenin")]
_LEAGUE = {"süper lig": "süper lig", "nba": "nba", "şampiyonlar ligi": "champions", "avrupa ligi": "europa", "premier lig": "premier",
           "euroleague": "euroleague", "sultanlar ligi": "sultanlar", "la liga": "la liga", "bundesliga": "bundesliga", "serie a": "serie a",
           "eredivisie": "eredivisie", "hollanda ligi": "eredivisie", "portekiz ligi": "portekiz", "belçika ligi": "belçika", "iskoçya ligi": "premiership", "championship": "championship",
           "fa cup": "fa cup", "kral kupası": "kral kupası", "italya kupası": "italya kupası", "libertadores": "libertadores", "mls": "mls", "brezilya ligi": "brezilya",
           "arjantin ligi": "arjantin", "meksika ligi": "meksika", "suudi lig": "suudi", "hazırlık maçları": "hazırlık", "dünya kupası": "dünya kupası", "uluslar ligi": "uluslar"}
_STOP = {"maç", "maçı", "maçlar", "maçları", "maçlarını", "ne", "zaman", "nasıl", "bitti", "kaç", "kaçta", "skor", "skoru", "sonucu", "sonuç", "sonuçları", "göster", "bugün", "yarın", "dün", "canlı", "var", "mı", "mi", "hangi", "takım", "liste"}


def _result(say_extra=""):
    v = P.view()
    return {"do": {"data": v}, "say": say_extra + P.say_summary(v)}


def spor(text: str, st: dict):
    t = scenes.norm(text)
    if not t:
        return None
    if re.search(r"\b(yardım|neler yapabilirsin|komutlar)\b", t):
        return {"say": "Futbol, basketbol ya da voleybol deyin. Bugün, yarın, dün, canlı maçlar, Süper Lig, NBA gibi bir lig ya da bir takım adı söyleyebilirsiniz. Yenile ve temizle de var."}
    m = re.search(r"([a-zçğıöşü0-9 ]{3,30}?)\s*(?:takımını|takımı|kulübünü|kulübü|u|ü|yi|yı|i|ı)?\s*favori\w*\s*(?:takım\w*\s*)?(ekle|yap|kaydet|çıkar|sil|kaldır)", t)
    if m and not re.search(r"\b(favorilerim|favori maç\w*)\b", t):
        name = re.sub(r"\b(favori\w*|takım\w*|benim|ekle|çıkar)\b", "", m.group(1)).strip()
        name = re.sub(r"(nin|nın|in|ın|yi|yı|ü|u|i|ı)$", "", name) if len(name) > 5 else name
        if name:
            cur = P.favs()
            if m.group(2) in ("çıkar", "sil", "kaldır"):
                P.set_favs([f for f in cur if f.lower() != name.lower()])
                return {"do": {"data": P.view()}, "say": f"{name} favorilerden çıkarıldı efendim."}
            P.set_favs(cur + [name])
            return {"do": {"data": P.view()}, "say": f"{name} favorilere eklendi efendim, maçları en üstte göstereceğim."}
    if re.search(r"\b(favorilerim|favori maç\w*|favori takım\w*)\b", t):
        if re.search(r"\b(neler|hangi|kim|liste)\b", t):
            f = P.favs()
            return {"say": ("Favori takımlarınız: " + ", ".join(f) + ".") if f else "Henüz favori takımınız yok efendim. Fenerbahçe favorilere ekle diyebilirsiniz."}
        P.S["onlyfav"] = True
        r = _result()
        r["say"] = P.say_summary(r["do"]["data"]) if r["do"]["data"]["n"] else "Favori takımlarınızın bugün maçı görünmüyor efendim."
        return r
    for k, pat in _SPORT:
        if re.search(pat, t):
            P.S.update(sport=k, league="", team="")
            break
    if re.search(r"\byarın\w*", t):
        P.S["day"] = 1
    elif re.search(r"\bdün\w*", t):
        P.S["day"] = -1
    elif re.search(r"\bbugün\w*|\bşimdi\w*|\bcanlı\b|\byenile\w*|\bgüncelle\w*", t):
        P.S["day"] = 0
    if re.search(r"\b(temizle|tümü|hepsi|filtreyi kaldır)\b", t):
        P.S.update(league="", team="", onlyfav=False)
    for name, key in _LEAGUE.items():
        if name in t:
            P.S.update(league=key, team="")
            break
    else:
        rest = [w for w in t.split() if w not in _STOP and not re.search(r"futbol|basket|voleybol|yenile|güncelle|temizle|tümü|hepsi", w)]
        if rest and re.search(r"\bmaç\w*|skor\w*|sonuç\w*|oynuyor|oynadı|ne zaman", t) and len(rest) <= 3:
            P.S.update(team=re.sub(r"(nin|nın|in|ın|un|ün|'?[ıi]n)$", "", " ".join(rest)), league="")
    r = _result()
    if re.search(r"\bcanlı\b", t):
        v = r["do"]["data"]
        r["say"] = (f"Şu an {v['canli']} canlı maç var efendim." if v["canli"] else "Şu an canlı oynanan maç görünmüyor efendim.")
    return r


def init_payload():
    return P.init_payload()
