"""MEBİ (mebi.eba.gov.tr) izleyicisi. MEBİ kendi penceresinde açılır (kalıcı profil: mebi_profile/, öğrenci girişi kendisi yapar; şifre ne okunur ne saklanır).
İzleme PASİFTİR: Jarvis sayfaya tıklamaz, hiçbir şey göndermez, MEBİ'ye köprü işlevi açılmaz. Python birkaç saniyede bir sayfadaki durumu okur:
açık konu, video oynuyor mu ve ne kadar, ve sayfanın KENDİ kayıt çağrıları (video tamamlandı, özet, etkinlik bitti). Okunanlar mebi.json'da kalır.
Yalnızca mebi.eba.gov.tr üzerinde okunur; giriş sayfasında (sso.eba.gov.tr) hiçbir şey okunmaz, girilen alanlar hiçbir zaman kaydedilmez."""
import json
import os
import re
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "mebi.json")
PROFILE = os.path.join(HERE, "mebi_profile")
HOST = "mebi.eba.gov.tr"
HOME = f"https://{HOST}/student/home/content"
TITLE = "JARVIS MEBİ"
GUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
PAGE = re.compile(r"^/student/(section/subject-details|interactive-quiz|quiz)/(" + GUID + r")$")
MAX_TOPICS, MAX_EV, POLL_S = 500, 60, 5
_lock = threading.RLock()

# Sayfada çalışır; yalnızca okur. Ana sayfa 'mainFrame' iframe'i içinde konu sayfalarını açar (aynı alan adı, içine erişilebilir).
POLL_JS = r"""(function(){try{
if(location.hostname!=='mebi.eba.gov.tr')return JSON.stringify({off:true});
var fr=document.getElementById('mainFrame'),w=window;
if(fr){try{w=fr.contentWindow;w.document;}catch(e){w=window;}}
var d=w.document;
if(!w.__jv){
 w.__jv={q:[]};var q=w.__jv.q;
 var push=function(o){o.t=Date.now();if(q.length<150)q.push(o);};
 var P=w.XMLHttpRequest.prototype,XO=P.open,XS=P.send;
 P.open=function(m,u){this.__m=m;this.__u=String(u);return XO.apply(this,arguments);};
 P.send=function(b){var x=this;
  if(x.__m&&String(x.__m).toUpperCase()==='POST'&&x.__u.indexOf('/student/')>=0&&!/kanka|ai-send|stay-fit|feedback|review/.test(x.__u)){
   x.addEventListener('loadend',function(){push({k:'post',u:x.__u.split('?')[0].slice(0,80),b:(typeof b==='string'?b:'').slice(0,300),r:(x.responseText||'').slice(0,/get-student-subject|video-app-list/.test(x.__u)?2000:200)});});}
  return XS.apply(this,arguments);};
 d.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a,button');if(!a)return;
  push({k:'click',x:(a.innerText||'').trim().slice(0,40),o:(a.getAttribute('onclick')||'').slice(0,30)});},true);
}
var cr=[].map.call(d.querySelectorAll('.breadcrumb li,.breadcrumb-item'),function(e){return e.innerText.trim();}).filter(Boolean);
var vs=[].map.call(d.querySelectorAll('video'),function(v){return{t:Math.round(v.currentTime),d:Math.round(v.duration||0),p:v.paused,e:v.ended};}).slice(0,3);
var J=w.__jv;
if(!J.kzDone&&/subject-details/.test(w.location.pathname)&&d.body){J.kzDone=1;J.kz=[];J.an=[];
 var b=d.body.cloneNode(true);[].forEach.call(b.querySelectorAll('script,style'),function(e){e.remove();});
 var seen={};(b.textContent.match(/[A-ZÇĞİÖŞÜ]{2,5}\.9\.\d+\.\d+\.\s+[^\n\r]{12,170}/g)||[]).forEach(function(s){
  var c=s.replace(/\s+/g,' ').trim();if(/-[A-ZÇĞİÖŞÜ]{2,5}\.9\.|Kapat$/.test(c))return;var k=c.slice(0,12);if(!seen[k]){seen[k]=1;J.kz.push(c);}});
 [].forEach.call(d.querySelectorAll('[onclick*="App("]'),function(a){var n=(a.textContent||'').replace(/\s+/g,' ').trim();if(n&&J.an.indexOf(n)<0)J.an.push(n);});}
return JSON.stringify({path:w.location.pathname,crumbs:cr,v:vs,ev:J.q.splice(0),kz:J.kz||[],an:J.an||[]});
}catch(e){return JSON.stringify({err:String(e).slice(0,80)});}})()"""


def _load() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("topics"), dict):
            return d
    except (OSError, ValueError):
        pass
    return {"last": "", "topics": {}}


def _save(d: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=HERE, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, PATH)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _s(v, n=120) -> str:
    return str(v or "").strip()[:n]


def _crumbs(raw) -> list:
    out = []
    for c in raw if isinstance(raw, list) else []:
        c = _s(c)
        if c and c not in out:
            out.append(c)
    return out


def _new(guid: str) -> dict:
    return {"ders": "", "unite": "", "konu": "", "t": 0, "watch_s": 0, "pct": 0, "video": False, "ozet": False, "podcast": False,
            "acts": 0, "clicks": 0, "quiz_seen": False, "hazir_seen": False, "ev": [], "view_s": 0, "dur": 0, "apps": [], "act_done": [], "pend": "", "kaz": [], "act_names": []}


def _apply_event(tp: dict, e: dict) -> str:
    """Sayfanın kendi kayıt çağrısını konu kaydına işler; yeni bir kilometre taşıysa kısa adını döner."""
    if e.get("k") == "click":
        tp["clicks"] += 1
        if re.match(r"show\w*App\(", _s(e.get("o"), 40)):      # showSkillBasedApp('..') gibi: hangi etkinlik açıldı
            tp["pend"] = _s(e.get("x"), 60)
        return ""
    u = _s(e.get("u"), 80)
    if "get-student-subject" in u:                   # MEBİ'nin kendi kaydı: {"video":..,"summary":..,"podcast":..,"viewingTime":sn}
        try:
            r = json.loads(e.get("r") or "")
        except ValueError:
            return ""
        got = ""
        if isinstance(r, dict):
            for src, dst in (("video", "video"), ("summary", "ozet"), ("podcast", "podcast")):
                if r.get(src) is True and not tp[dst]:
                    tp[dst] = True
                    got = dst
            if isinstance(r.get("viewingTime"), (int, float)):
                tp["view_s"] = max(tp["view_s"], int(r["viewingTime"]))     # sunucuda biriken izleme süresi (sn)
        return got
    if "video-app-list" in u:                        # videonun içine gömülü etkinlikler ve çıkış zamanları
        try:
            r = json.loads(e.get("r") or "")
        except ValueError:
            return ""
        if isinstance(r, list):
            tp["apps"] = [{"n": _s(a.get("name"), 60), "s": _s(a.get("startTime"), 8)} for a in r[:20] if isinstance(a, dict)]
        return ""
    if re.search(r"list|update-viewing-time", u):
        return ""
    got = ""
    if "save-video" in u:
        got = "video" if not tp["video"] else ""
        tp["video"] = True
    elif "save-summary" in u:
        got = "ozet" if not tp["ozet"] else ""
        tp["ozet"] = True
    elif "save-podcast" in u:
        got = "podcast" if not tp["podcast"] else ""
        tp["podcast"] = True
    elif re.search(r"save|score|complet", u):                # örn. save-skill-based-app, gövde {"SkillBasedAppId": "<guid>"}
        m = re.search(r"([0-9a-f]{8})-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", _s(e.get("b"), 400))
        aid = m.group(1) if m else _s(e.get("t"))
        if not any(a.get("id") == aid for a in tp["act_done"]) and len(tp["act_done"]) < 100:
            tp["act_done"].append({"id": aid, "n": tp.get("pend", ""), "u": u.rsplit("/", 1)[-1][:30]})
            tp["acts"] = len(tp["act_done"])
            got = "etkinlik"
        tp["pend"] = ""
    tp["ev"] = (tp["ev"] + [{"t": int(e.get("t", 0) / 1000), "u": u.rsplit("/", 1)[-1][:40]}])[-MAX_EV:]
    return got


def ingest(p: dict, dt: float = POLL_S) -> list:
    """Bir okuma sonucunu işler. Yeni kilometre taşlarının listesini döner (video / ozet / podcast / etkinlik)."""
    if not isinstance(p, dict) or p.get("off") or p.get("err"):
        return []
    m = PAGE.match(_s(p.get("path"), 200))
    if not m:
        return []
    kind, guid = m.group(1), m.group(2)
    miles = []
    with _lock:
        d = _load()
        if guid not in d["topics"]:
            if len(d["topics"]) >= MAX_TOPICS:
                return []
            d["topics"][guid] = _new(guid)
        tp = {**_new(guid), **d["topics"][guid]}
        cr = _crumbs(p.get("crumbs"))
        if kind == "section/subject-details" and len(cr) >= 6:
            tp["ders"], tp["unite"], tp["konu"] = cr[3], cr[4], cr[5]
        if kind == "interactive-quiz":
            tp["quiz_seen"] = True
        elif kind == "quiz":
            tp["hazir_seen"] = True
        for v in (p.get("v") if isinstance(p.get("v"), list) else [])[:1]:
            if isinstance(v, dict) and v.get("d", 0) > 0:
                if not v.get("p") and not v.get("e"):
                    tp["watch_s"] += min(float(dt), 10.0)
                tp["pct"] = max(tp["pct"], min(100, round(100 * v.get("t", 0) / v["d"])))
                tp["dur"] = int(v["d"])
        kz = []
        for s in (p.get("kz") if isinstance(p.get("kz"), list) else [])[:12]:
            m2 = re.match(r"([A-ZÇĞİÖŞÜ]{2,5}\.9\.\d+\.\d+)\.\s+(.{12,170})$", _s(s, 200))
            if m2:
                kz.append({"kod": m2.group(1), "ad": m2.group(2)})
        if kz and kind == "section/subject-details":
            tp["kaz"] = kz
        an = [_s(x, 70) for x in (p.get("an") if isinstance(p.get("an"), list) else [])[:30] if _s(x, 70)]
        if an and kind == "section/subject-details":
            tp["act_names"] = an
        for e in (p.get("ev") if isinstance(p.get("ev"), list) else [])[:150]:
            if isinstance(e, dict):
                got = _apply_event(tp, e)
                if got:
                    miles.append(got)
        tp["t"] = int(time.time())
        d["topics"][guid] = tp
        d["last"] = guid
        _save(d)
    return miles


def topic_url(guid: str):
    return f"https://{HOST}/student/section/subject-details/{guid}" if re.fullmatch(GUID, str(guid)) else None


def last_topic():
    """(guid, kayıt) ya da (None, None)."""
    with _lock:
        d = _load()
    g = d.get("last")
    return (g, d["topics"][g]) if g in d["topics"] else (None, None)


def describe(tp: dict) -> str:
    """Konu için YALNIZCA kayıtlı olanı söyler; kaydı olmayan 'yapılmadı' değil 'kayıtlarımda yok' demektir."""
    name = tp.get("konu") or "son konunuz"
    done, left = [], []
    if tp.get("video"):
        done.append("konu anlatım videosu")
    else:
        mins = int(tp.get("view_s", 0)) // 60
        extra = (f" ({mins} dakikası izlendi" + (f", toplam {round(tp['dur'] / 60)} dakika" if tp.get("dur") else "") + ")") if mins else ""
        left.append("konu anlatım videosu" + extra)
    (done if tp.get("ozet") else left).append("özet")
    if tp.get("acts"):
        done.append(f"{tp['acts']} etkinlik")
    else:
        left.append("etkinlikler")
    (done if tp.get("quiz_seen") else left).append("değerlendirme soruları")
    s = f"{name}: "
    if done:
        s += "kayıtlarıma göre " + ", ".join(done) + " tamam"
    if left:
        s += ("; " if done else "kayıtlarımda ") + ", ".join(left) + (" kaldı" if done else " yok")
    return s + " efendim."


# MEBİ ders adı -> ders_data id (listede olmayanlar 'ozel' ders olarak açılır)
DERS_IDS = {"matematik": "matematik", "fizik": "fizik", "kimya": "kimya", "biyoloji": "biyoloji", "türk dili ve edebiyatı": "edebiyat",
            "tarih": "tarih", "coğrafya": "cografya"}


def quiz_topic(tp: dict):
    """Ders modunda (ders_srv.open_topic) bu MEBİ konusunu açmak için gereken girdi. Konu adı okunamamışsa None."""
    konu, ders = _s(tp.get("konu")), _s(tp.get("ders"))
    if not konu or not ders:
        return None
    did = DERS_IDS.get(ders.lower().replace("İ", "i").replace("I", "ı"), "") or DERS_IDS.get(ders.lower(), "")
    return {"ders": did or "ozel", "dersAd": ders, "unite": _s(tp.get("unite")) or "Serbest ünite", "konu": konu, "stage": "quiz"}


def outcomes(ders: str, unite: str, konu: str) -> dict:
    """ders_ai için: MEBİ'nin bu konudaki kazanımları ve etkinlik adları. Kayıtlı değilse boş."""
    with _lock:
        d = _load()
    for tp in d["topics"].values():
        if _s(tp.get("konu")).lower() == _s(konu).lower() and _s(tp.get("unite")).lower() == _s(unite).lower():
            return {"kazanimlar": list(tp.get("kaz") or []), "etkinlikler": list(tp.get("act_names") or [])}
    return {"kazanimlar": [], "etkinlikler": []}


class Tracker:
    """Pencere açıkken POLL_S saniyede bir sayfayı okur. goto: giriş sonrası bu konuya git (bir kez)."""

    def __init__(self, window, goto=None, on_milestone=None):
        self.w, self.goto, self.on_milestone = window, goto, on_milestone
        self.stop_ev = threading.Event()
        self.th = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.th.start()

    def stop(self):
        self.stop_ev.set()

    def _run(self):
        last = time.time()
        while not self.stop_ev.wait(POLL_S):
            now = time.time()
            dt, last = now - last, now
            try:
                raw = self.w.evaluate_js(POLL_JS)
                p = json.loads(raw) if isinstance(raw, str) else {}
            except Exception:
                continue                               # sayfa yükleniyor ya da pencere kapanıyor
            try:
                if self.goto and not p.get("off") and p.get("path"):
                    url = topic_url(self.goto)
                    self.goto = None
                    if url:
                        self.w.evaluate_js("(function(){var f=document.getElementById('mainFrame');(f?f.contentWindow:window).location.href=" + json.dumps(url) + ";})()")
                miles = ingest(p, dt)
                if miles and self.on_milestone:
                    self.on_milestone(miles)
            except Exception as e:
                print("MEBİ izleme hatası:", type(e).__name__, e, flush=True)
