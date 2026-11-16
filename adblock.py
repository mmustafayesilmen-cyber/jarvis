"""Jarvis tarayıcısı için reklam / izleyici engelleyici (jbrowser_proc.py kullanır). Ağ isteklerini WebView2'nin WebResourceRequested olayında alan adına göre keser;
sayfada kalan reklam kutularını ve YouTube reklamlarını CSS + küçük bir betikle gizler. Hiçbir veri dışarı gitmez, liste elle bakımlıdır."""
import re

DOMAINS = frozenset("""
doubleclick.net googlesyndication.com googleadservices.com adservice.google.com googletagservices.com google-analytics.com googletagmanager.com
adnxs.com adsrvr.org adform.net advertising.com criteo.com criteo.net taboola.com outbrain.com revcontent.com mgid.com zemanta.com
rubiconproject.com pubmatic.com openx.net casalemedia.com indexww.com smartadserver.com amazon-adsystem.com media.net contextweb.com yieldmo.com
moatads.com adsafeprotected.com doubleverify.com scorecardresearch.com quantserve.com hotjar.com hotjar.io mouseflow.com crazyegg.com fullstory.com clarity.ms
ads-twitter.com analytics.twitter.com ads.linkedin.com snap.licdn.com ads.pinterest.com ads.tiktok.com analytics.tiktok.com sc-static.net
bat.bing.com ads.yahoo.com analytics.yahoo.com adtech.com yieldlab.net exoclick.com juicyads.com trafficjunky.net propellerads.com popads.net
popcash.net adcash.com clickadu.com hilltopads.net adsterra.com bidswitch.net sharethrough.com triplelift.com teads.tv gumgum.com
33across.com lijit.com sovrn.com everesttech.net serving-sys.com mathtag.com turn.com demdex.net krxd.net bluekai.com agkn.com rlcdn.com tapad.com
adition.com weborama.com segment.io mixpanel.com amplitude.com branch.io appsflyer.com adjust.com kochava.com chartbeat.com newrelic.com
""".split())

# Yalnızca üçüncü taraf isteklerde bakılan yol kalıpları.
PATH_RE = re.compile(r"/(adframe|adsbygoogle|ad-banner|adserver|adsense|prebid|pagead)([._/?-]|$)|/ads\.js", re.I)

# Hiçbir koşulda kesilmeyecek ana siteler (giriş, ödeme vb. bozulmasın).
KEEP = frozenset("youtube.com googlevideo.com ytimg.com google.com gstatic.com".split())

SELECTORS = [
    "ins.adsbygoogle", '[id^="google_ads_"]', '[id^="div-gpt-ad"]', '[class*="adsbygoogle"]', '[class*="ad-banner"]',
    "[data-ad-slot]", "[data-google-query-id]", 'iframe[src*="doubleclick"]', 'iframe[src*="googlesyndication"]',
    ".taboola", "#taboola-below-article", ".OUTBRAIN", '[id^="outbrain"]', ".sticky-ad", ".ad-slot", ".ad-wrapper", ".banner-ad",
    "ytd-ad-slot-renderer", "ytd-promoted-sparkles-web-renderer", "#masthead-ad", "ytd-display-ad-renderer", "ytd-banner-promo-renderer",
]

# Her belge yaratılırken (iframe'ler dahil) çalışır. Stil CSSOM ile eklenir: sitenin CSP'si satır içi <style>'ı engellese de çalışır.
COSMETIC_JS = r"""(function(){try{
var sel=%s;
window.__jvAdb=true;
function css(){try{if(window.__jvSheet)return;var s=new CSSStyleSheet();s.replaceSync(sel.join(',')+'{display:none!important}');window.__jvSheet=s;document.adoptedStyleSheets=[...document.adoptedStyleSheets,s];}catch(e){}}
window.__jvOn=function(){window.__jvAdb=true;css();};
window.__jvOff=function(){window.__jvAdb=false;try{var s=window.__jvSheet;window.__jvSheet=null;document.adoptedStyleSheets=document.adoptedStyleSheets.filter(function(x){return x!==s;});}catch(e){}};
css();
if(/(^|\.)youtube\.com$/.test(location.hostname)&&window.top===window){
 setInterval(function(){try{
  if(window.__jvAdb===false)return;
  var p=document.querySelector('.html5-video-player.ad-showing'),v=document.querySelector('video');
  if(p&&v&&isFinite(v.duration)){v.muted=true;v.currentTime=v.duration;}
  var b=document.querySelector('.ytp-ad-skip-button,.ytp-ad-skip-button-modern,.ytp-skip-ad-button');if(b)b.click();
 }catch(e){}},400);
}
}catch(e){}})();""" % __import__("json").dumps(SELECTORS)


# Düğmeyle açıp kapatırken açık sayfalarda çalıştırılır (yenilemeye gerek kalmaz; iframe'lerdeki gizlemeler sayfa yenilenince değişir).
JS_ON = "try{window.__jvOn&&window.__jvOn();}catch(e){}"
JS_OFF = "try{window.__jvOff&&window.__jvOff();}catch(e){}"


def _host(url: str) -> str:
    m = re.match(r"^[a-z][a-z0-9+.-]*://(?:[^/@]*@)?([^/:?#]+)", url, re.I)
    return m.group(1).lower() if m else ""


def _suffix_in(host: str, names) -> bool:
    parts = host.split(".")
    return any(".".join(parts[i:]) in names for i in range(len(parts) - 1))


def is_blocked(url: str, page_host: str = "") -> bool:
    """Bu istek kesilsin mi? page_host verilirse aynı siteye giden istek (birinci taraf) yol kalıplarından muaf tutulur."""
    h = _host(url)
    if not h:
        return False
    if _suffix_in(h, DOMAINS):
        return True
    if _suffix_in(h, KEEP):
        return False
    if PATH_RE.search(url) and not (page_host and _suffix_in(h, {page_host})):
        return True
    return False
