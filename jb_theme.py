"""Jarvis tarayıcısı için GX tarzı görünüm: renk temaları, tıklama/yazma sesleri ve hızlı erişim kutulu başlangıç sayfası. jbrowser_proc.py (ayrı süreç) kullanır;
ayarlar config.json'dan okunur (yazan: ana süreç, jbrowser.set_look): tarayici_tema, tarayici_ses, tarayici_kutular. Sayfalara köprü açılmaz: başlangıç sayfası yalnızca düz bağlantı ve arama formudur."""
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "config.json")

# ad: (vurgu RGB, koyu zemin 1, koyu zemin 2, açıklama)
THEMES = {
    "gx":      ((250, 30, 78),   "#12060a", "#2a0a14", "GX kırmızısı"),
    "mor":     ((167, 90, 255),  "#0d0716", "#22103d", "neon mor"),
    "mavi":    ((70, 160, 255),  "#050b16", "#0b2140", "buz mavisi"),
    "camgöbeği": ((95, 230, 255), "#04101a", "#08303f", "siber camgöbeği"),
    "yeşil":   ((60, 255, 140),  "#04120a", "#0a2f1a", "matrix yeşili"),
    "turuncu": ((255, 140, 40),  "#140a04", "#3a1a08", "gün batımı"),
    "pembe":   ((255, 90, 190),  "#15060f", "#3a0f2b", "sakura pembesi"),
}
DEFAULT_THEME = "gx"
DEFAULT_DIALS = [
    {"ad": "YouTube", "url": "https://www.youtube.com/"},
    {"ad": "Google", "url": "https://www.google.com/"},
    {"ad": "WhatsApp", "url": "https://web.whatsapp.com/"},
    {"ad": "Twitch", "url": "https://www.twitch.tv/"},
    {"ad": "Discord", "url": "https://discord.com/app"},
    {"ad": "GitHub", "url": "https://github.com/"},
    {"ad": "Reddit", "url": "https://www.reddit.com/"},
    {"ad": "Spotify", "url": "https://open.spotify.com/"},
]


def load() -> dict:
    """Güncel görünüm ayarları (config.json yoksa/bozuksa varsayılanlar)."""
    try:
        with open(CFG, encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError):
        c = {}
    th = c.get("tarayici_tema")
    dials = [d for d in (c.get("tarayici_kutular") or DEFAULT_DIALS)
             if isinstance(d, dict) and re.match(r"^https?://\S+$", str(d.get("url", ""))) and str(d.get("ad", "")).strip()][:12]
    return {"tema": th if th in THEMES else DEFAULT_THEME, "ses": bool(c.get("tarayici_ses", False)), "kutular": dials or DEFAULT_DIALS}


def accent(theme: str):
    return THEMES.get(theme, THEMES[DEFAULT_THEME])[0]


def rgb_str(theme: str) -> str:
    return "%d,%d,%d" % accent(theme)


def hex_str(theme: str) -> str:
    return "#%02x%02x%02x" % accent(theme)


def bar_js(bar_src: str, theme: str) -> str:
    """Sayfa içi araç çubuğunun (BAR_JS) camgöbeği vurgusunu seçili temaya çevirir."""
    return bar_src.replace("95,230,255", rgb_str(theme))


# Yazma ve tıklama sesleri: WebAudio, ilk kullanıcı hareketinde başlar; window.__jvSound açıkken çalar (bayrağı süreç her yüklemede ve 'look' komutunda yazar).
SOUND_JS = r"""(function(){try{
if(window.__jvSoundInit)return;window.__jvSoundInit=true;if(window.__jvSound===undefined)window.__jvSound=false;
var ac=null;function ctx(){if(!ac){try{ac=new (window.AudioContext||window.webkitAudioContext)();}catch(e){}}return ac;}
function tick(f,d,v,type){if(!window.__jvSound)return;var c=ctx();if(!c)return;if(c.state==='suspended')c.resume();
 var o=c.createOscillator(),g=c.createGain(),t=c.currentTime;o.type=type||'square';o.frequency.setValueAtTime(f,t);o.frequency.exponentialRampToValueAtTime(f*0.55,t+d);
 g.gain.setValueAtTime(v,t);g.gain.exponentialRampToValueAtTime(0.0001,t+d);o.connect(g);g.connect(c.destination);o.start(t);o.stop(t+d+0.02);}
document.addEventListener('keydown',function(e){if(e.repeat)return;var k=e.key;
 if(k==='Enter')tick(520,0.09,0.05,'triangle');else if(k==='Backspace'||k==='Delete')tick(260,0.06,0.04,'square');
 else if(k.length===1||k==='Tab'||k===' ')tick(900+Math.random()*180,0.035,0.035,'square');},true);
document.addEventListener('mousedown',function(e){tick(380,0.07,0.05,'sine');},true);
}catch(e){}})();"""


def start_html(cfg: dict) -> str:
    """Yeni sekmede gösterilen sayfa: saat, arama kutusu ve hızlı erişim kutuları, seçili temanın renkleriyle."""
    th = cfg["tema"]
    rgb, bg1, bg2, _ = THEMES[th]
    a = "%d,%d,%d" % rgb
    tiles = "".join(
        '<a class="t" href="%s"><i>%s</i><span>%s</span></a>' % (html.escape(d["url"], quote=True), html.escape(str(d["ad"]).strip()[:1].upper()), html.escape(str(d["ad"]).strip()[:18]))
        for d in cfg["kutular"])
    return """<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Yeni sekme</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--a:rgb(%(a)s);--g:rgba(%(a)s,.45);--bg1:%(bg1)s;--bg2:%(bg2)s}
*{box-sizing:border-box}html,body{height:100%%;margin:0}
body{background:radial-gradient(1200px 700px at 20%% 10%%,var(--bg2),transparent 60%%),radial-gradient(900px 600px at 90%% 90%%,var(--bg2),transparent 55%%),var(--bg1);
 color:#f2f2f5;font:15px/1.4 "Segoe UI",system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:28px;overflow:hidden}
body::before{content:"";position:fixed;inset:-40%%;background:conic-gradient(from 0deg,transparent,rgba(%(a)s,.10),transparent 30%%);animation:sp 18s linear infinite;pointer-events:none}
@keyframes sp{to{transform:rotate(360deg)}}
#clock{font-size:76px;font-weight:700;letter-spacing:2px;color:var(--a);text-shadow:0 0 34px var(--g);position:relative}
#date{margin-top:-18px;color:#9a9aab;position:relative}
form{position:relative;width:min(640px,86vw)}
input{width:100%%;height:50px;padding:0 20px;border-radius:26px;border:1px solid rgba(%(a)s,.35);background:rgba(0,0,0,.45);color:#fff;font:16px "Segoe UI",sans-serif;outline:none;backdrop-filter:blur(8px)}
input:focus{border-color:var(--a);box-shadow:0 0 0 3px rgba(%(a)s,.22),0 0 30px var(--g)}
.g{position:relative;display:grid;grid-template-columns:repeat(4,110px);gap:16px}
.t{display:flex;flex-direction:column;align-items:center;gap:8px;padding:16px 8px;border-radius:18px;text-decoration:none;color:#e8e8ef;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);transition:.18s}
.t:hover{transform:translateY(-4px);border-color:var(--a);box-shadow:0 8px 28px rgba(%(a)s,.28);background:rgba(%(a)s,.10)}
.t i{font-style:normal;width:44px;height:44px;border-radius:14px;display:grid;place-items:center;font-weight:700;font-size:20px;background:linear-gradient(135deg,var(--a),rgba(%(a)s,.45));color:#0b0b10}
.t span{font-size:13px;text-align:center}
small{position:fixed;bottom:12px;color:#6c6c7a}
</style></head><body>
<div id="clock">00:00</div><div id="date"></div>
<form action="https://www.google.com/search" method="get"><input name="q" placeholder="Google'da ara ya da adres yaz" autofocus autocomplete="off"></form>
<div class="g">%(tiles)s</div>
<small>JARVIS TARAYICI · tema: %(tema)s</small>
<script>
function t(){var d=new Date();document.getElementById('clock').textContent=('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2);
document.getElementById('date').textContent=d.toLocaleDateString('tr-TR',{weekday:'long',day:'numeric',month:'long'});}
t();setInterval(t,10000);
</script></body></html>""" % {"a": a, "bg1": bg1, "bg2": bg2, "tiles": tiles, "tema": html.escape(th)}


START_DIR = os.path.join(HERE, "jarvis_tarayici_baslangic")      # yalnızca başlangıç sayfasını içerir (pywebview bu klasörü yerel sunucuyla sunar; profil klasörü asla sunulmaz)
START_FILE = "baslangic.html"


def write_start(cfg: dict) -> str:
    """Başlangıç sayfasını diske yazar (pencere bu dosyayla açılır, tema değişince yeniden yazılıp sayfa yenilenir). Dosya yolunu döner."""
    os.makedirs(START_DIR, exist_ok=True)
    p = os.path.join(START_DIR, START_FILE)
    with open(p, "w", encoding="utf-8") as f:
        f.write(start_html(cfg))
    return p


def is_start_url(u: str) -> bool:
    """pywebview'in yerel sunucusundaki başlangıç sayfası mı? (ana sürece gerçek adres diye bildirilmesin)"""
    return bool(re.match(r"^http://127\.0\.0\.1:\d+/" + re.escape(START_FILE) + r"$", str(u)))


def theme_from_text(t: str):
    """Sesli komuttaki tema adını bulur (kırmızı → gx, camgöbeği/turkuaz/siber → camgöbeği ...); yoksa None."""
    t = t.lower()
    alias = {"gx": "gx", "kırmızı": "gx", "kirmizi": "gx", "mor": "mor", "mavi": "mavi", "camgöbeği": "camgöbeği", "turkuaz": "camgöbeği", "siber": "camgöbeği",
             "yeşil": "yeşil", "yesil": "yeşil", "matrix": "yeşil", "turuncu": "turuncu", "gün batımı": "turuncu", "pembe": "pembe", "sakura": "pembe"}
    for k, v in alias.items():
        if re.search(r"\b" + re.escape(k), t):
            return v
    return None
