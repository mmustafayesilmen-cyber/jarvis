"""Şarkı sözleri (lrclib.net, anahtarsız genel API). Zaman damgalıysa (LRC) çalan satır ekranda vurgulanır. Yalnızca şarkı adı ve sanatçı
gönderilir; sonuçlar bellekte tutulur, diske yazılmaz."""
import re

import httpx

_cache: dict = {}
_UA = {"User-Agent": "JarvisLocalAssistant/1.0"}


def clean_title(t: str) -> str:
    t = re.sub(r"\s*[\(\[][^)\]]*(official|video|audio|lyric|söz|klip|clip|hd|4k|live|remaster|visuali[sz]er|müzik|music|m/v|mv)[^)\]]*[\)\]]", "", t, flags=re.I)
    t = re.sub(r"\s*[-–|]\s*(official|resmi)?\s*(music\s*)?(video|audio|lyrics?|klip)\b.*$", "", t, flags=re.I)
    t = re.sub(r"\s*[\(\[]?\s*(ft\.?|feat\.?|featuring)\s.*$", "", t, flags=re.I)
    t = re.sub(r"\s*-\s*topic\b", "", t, flags=re.I)
    t = re.sub(r"\s*vevo$", "", t, flags=re.I)
    return t.strip(" -–|")


def parse_lrc(text: str):
    out = []
    for line in text.splitlines():
        m = re.match(r"\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*)", line)
        if m:
            out.append([int(m.group(1)) * 60 + float(m.group(2)), m.group(3).strip()])
    return out


def fetch(title: str, artist: str = "", dur: float = 0.0):
    """{'synced': bool, 'lines': [[t, metin]...], 'plain': str, 'name': str} ya da None."""
    title, artist = clean_title(title or ""), clean_title(artist or "")
    key = (title.lower(), artist.lower())
    if key in _cache:
        return _cache[key]
    res = None
    queries = []
    if artist:
        queries.append({"track_name": title, "artist_name": artist})
    queries.append({"q": f"{artist} {title}".strip()})
    if artist:
        queries.append({"q": title})                      # sanatçı kanal adıysa (YouTube) yanlış olabilir: yalnızca şarkı adıyla da dene
    for q in queries:
        try:
            r = httpx.get("https://lrclib.net/api/search", params=q, timeout=8, headers=_UA)
            items = r.json() if r.status_code == 200 else []
        except Exception as e:
            print("söz arama hatası:", e, flush=True)
            continue
        items = [x for x in items if x.get("syncedLyrics") or x.get("plainLyrics")]
        if not items:
            continue

        def score(x):
            s = 0
            if x.get("syncedLyrics"):
                s -= 5
            if dur and x.get("duration"):
                s += min(abs(x["duration"] - dur), 60) / 6
            return s
        best = min(items, key=score)
        if best.get("syncedLyrics"):
            lines = parse_lrc(best["syncedLyrics"])
            res = {"synced": True, "lines": lines, "plain": "", "name": best.get("trackName", title)}
        else:
            res = {"synced": False, "lines": [], "plain": best.get("plainLyrics", ""), "name": best.get("trackName", title)}
        break
    _cache[key] = res
    if len(_cache) > 60:
        _cache.pop(next(iter(_cache)))
    return res
