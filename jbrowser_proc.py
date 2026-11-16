"""Jarvis tarayıcısı: AYRI SÜREÇTE çalışan tek pencereli tarayıcı (pywebview / WebView2). Neden ayrı süreç: WebView2'nin ağ ayarları (proxy) süreç başına tek
seferde verilir; Jarvis'in ana süreci MEBİ, harita ve yerel arayüzle aynı WebView2'yi paylaştığı için VPN'i yalnızca bu pencereye uygulamak ancak böyle mümkün.
Kendi profili vardır (jarvis_tarayici_profil/: oturumlar kalır), ana Jarvis profilinden ayrıdır.

Ana süreçle konuşma: stdin'den satır başına bir JSON komutu okunur ({'cmd': 'goto', 'url': ...}, back, forward, reload, fullscreen, badge, close);
stdout'a olaylar yazılır ({'ev': 'ready'|'loaded'|'closed', ...}). stdin kapanırsa (ana Jarvis kapandı) pencere de kapanır.
Proxy: --proxy sunucusu verilirse tüm trafik oradan (socks5) çıkar; DNS de proxy üzerinden çözülür, WebRTC yerel IP sızdırmaz, proxy ölürse bağlantı kopar (doğrudan bağlantıya düşmez)."""
import argparse
import ctypes
import json
import os
import re
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
TITLE = "JARVIS TARAYICI"
BADGE_JS = r"""(function(t,ok){try{var id='__jarvis_rozet',e=document.getElementById(id);
if(!e){e=document.createElement('div');e.id=id;e.style.cssText='position:fixed;right:14px;bottom:14px;z-index:2147483647;padding:5px 12px;border-radius:14px;'
+'font:600 12px Segoe UI,sans-serif;color:#fff;pointer-events:none;opacity:.88;box-shadow:0 2px 12px rgba(0,0,0,.5);transition:opacity .4s';
(document.body||document.documentElement).appendChild(e);}
e.textContent=t;e.style.background=ok?'rgba(20,110,70,.92)':'rgba(40,50,70,.88)';
clearTimeout(window.__jarvis_rozet_t);window.__jarvis_rozet_t=setTimeout(function(){e.style.opacity='.35'},5000);}catch(x){}})(%s,%s);"""


# Fareyi pencerenin üst kenarına götürünce çıkan araç çubuğu: geri, ileri, yenile, ana sayfa ve adres/arama kutusu. Ana Jarvis sürecine köprü yoktur:
# düğmeler yalnızca sayfanın kendi history/location işlevlerini kullanır. Stil CSSOM ile verilir (sitenin CSP'si satır içi <style>'ı engellese de çalışır),
# kapalı shadow DOM sitenin kendi stilleriyle karışmaz. Adres: http(s):// aynen, alan adı gibi görünen https:// ile, diğerleri Google araması olur.
BAR_JS = r"""(function(){try{
if(window.top!==window||!document.documentElement)return;
var ID='__jarvis_bar';if(document.getElementById(ID))return;
var host=document.createElement('div');host.id=ID;host.style.cssText='all:initial;position:fixed;top:0;left:0;width:0;height:0;z-index:2147483646;';
var sh=host.attachShadow({mode:'closed'});
function mk(t,css,txt){var e=document.createElement(t);e.style.cssText=css;if(txt!==undefined)e.textContent=txt;return e;}
var BC='all:unset;box-sizing:border-box;min-width:34px;height:30px;padding:0 9px;display:flex;align-items:center;justify-content:center;border-radius:9px;border:1px solid rgba(95,230,255,.28);background:rgba(0,14,20,.75);color:#5fe6ff;cursor:pointer;font:600 15px Segoe UI,sans-serif;';
function btn(lb,tt,fn){var b=mk('button',BC,lb);b.title=tt;
 b.onmouseenter=function(){b.style.background='rgba(20,70,90,.9)'};b.onmouseleave=function(){b.style.background='rgba(0,14,20,.75)'};
 b.onclick=function(e){e.stopPropagation();fn();};return b;}
var handle=mk('div','position:fixed;top:0;left:50%;transform:translateX(-50%);width:46px;height:4px;border-radius:0 0 4px 4px;background:rgba(95,230,255,.4);pointer-events:none;transition:opacity .2s;');
var bar=mk('div','position:fixed;top:8px;left:50%;transform:translate(-50%,-150%);opacity:0;transition:transform .22s ease,opacity .22s;display:flex;align-items:center;gap:6px;padding:6px 8px;background:rgba(10,15,24,.95);border:1px solid rgba(95,230,255,.35);border-radius:14px;box-shadow:0 6px 28px rgba(0,0,0,.55);pointer-events:auto;');
var inp=mk('input','all:unset;box-sizing:border-box;width:min(46vw,420px);height:30px;padding:0 12px;border-radius:9px;border:1px solid rgba(95,230,255,.28);background:rgba(0,0,0,.45);color:#fff;font:13px Segoe UI,sans-serif;');
inp.spellcheck=false;inp.placeholder='Adres ya da arama';
function go(){var v=inp.value.trim();if(!v)return;var u;
 if(/^https?:\/\/\S+$/i.test(v))u=v;else if(/^[\w-]+(\.[\w-]+)+(\/\S*)?$/.test(v))u='https://'+v;else u='https://www.google.com/search?q='+encodeURIComponent(v);
 location.href=u;}
['keydown','keyup','keypress'].forEach(function(k){inp.addEventListener(k,function(e){e.stopPropagation();if(k==='keydown'){if(e.key==='Enter')go();else if(e.key==='Escape'){inp.blur();hide(true);}}});});
bar.appendChild(btn('◀','Geri (Alt+Sol)',function(){history.back();}));
bar.appendChild(btn('▶','İleri (Alt+Sağ)',function(){history.forward();}));
bar.appendChild(btn('⟳','Yenile',function(){location.reload();}));
bar.appendChild(btn('⌂','Ana sayfa',function(){location.href='https://www.google.com/';}));
bar.appendChild(btn('＋','Yeni sekme (Ctrl+T)',function(){window.__jv={a:'new'};}));
bar.appendChild(btn('✕','Sekmeyi kapat (Ctrl+W)',function(){window.__jv={a:'close'};}));
bar.appendChild(inp);
sh.appendChild(handle);sh.appendChild(bar);(document.body||document.documentElement).appendChild(host);
var hideT=0,over=false;
function focused(){return sh.activeElement===inp;}
function show(){bar.style.transform='translate(-50%,0)';bar.style.opacity='1';handle.style.opacity='0';if(!focused())inp.value=location.href;clearTimeout(hideT);hideT=setTimeout(hide,3200);}
function hide(force){if(!force&&(over||focused()))return;bar.style.transform='translate(-50%,-150%)';bar.style.opacity='0';handle.style.opacity='1';}
bar.onmouseenter=function(){over=true;clearTimeout(hideT);};bar.onmouseleave=function(){over=false;hideT=setTimeout(hide,1200);};
document.addEventListener('mousemove',function(e){if(e.clientY<6)show();},true);
document.addEventListener('keydown',function(e){
 if(e.altKey&&e.key==='ArrowLeft'){history.back();}else if(e.altKey&&e.key==='ArrowRight'){history.forward();}
 else if(e.ctrlKey&&(e.key==='l'||e.key==='L')){e.preventDefault();show();inp.focus();inp.select();}
 else if(e.ctrlKey&&!e.shiftKey&&(e.key==='t'||e.key==='T')){e.preventDefault();window.__jv={a:'new'};}
 else if(e.ctrlKey&&(e.key==='w'||e.key==='W')){e.preventDefault();window.__jv={a:'close'};}
 else if(e.ctrlKey&&e.key==='Tab'){e.preventDefault();window.__jv={a:e.shiftKey?'prev':'next'};}},true);
function linkTab(e){var a=e.target&&e.target.closest?e.target.closest('a[href]'):null;if(!a||!/^https?:/i.test(a.href))return;
 if((e.type==='click'&&(e.ctrlKey||e.metaKey||a.target==='_blank'))||(e.type==='auxclick'&&e.button===1)){e.preventDefault();e.stopPropagation();window.__jv={a:'new',u:a.href};}}
document.addEventListener('click',linkTab,true);document.addEventListener('auxclick',linkTab,true);
}catch(x){}})();"""


def emit(**o):
    try:
        sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except Exception:
        pass


def safe_url(u: str) -> bool:
    return bool(re.match(r"^https?://[^\s]+$", str(u))) and len(str(u)) < 2000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="about:blank")
    ap.add_argument("--proxy", default="")             # örn. 127.0.0.1:18081 (socks5)
    ap.add_argument("--badge", default="")             # sayfa köşesindeki rozet metni
    ap.add_argument("--badge-ok", default="0")
    ap.add_argument("--gpu", default="2")
    ap.add_argument("--adblock", default="1")              # 1 = reklam/izleyici engelleyici açık (adblock.py)
    ap.add_argument("--cdp", type=int, default=0)          # telefondan uzaktan erişim: yalnızca 127.0.0.1'de bu portta hata ayıklama (CDP) açılır; kapalıysa 0
    ap.add_argument("--bg", default="0")                   # 1 = pencere küçültülmüş (arka planda) açılır
    ap.add_argument("--w", type=int, default=1280)
    ap.add_argument("--h", type=int, default=800)
    ap.add_argument("--x", type=int, default=None)       # yalnızca testte: pencereyi ekran dışına koymak için
    ap.add_argument("--y", type=int, default=None)
    a = ap.parse_args()

    args = ["--autoplay-policy=no-user-gesture-required"]
    feats = []                                         # Chromium yalnızca SON --disable-features bayrağını okur; hepsi tek bayrakta birleştirilir
    if a.gpu == "0":
        args += ["--disable-gpu", "--disable-gpu-compositing"]
    elif a.gpu == "2":                                 # varsayılan: video çözme/raster GPU'da kalır, ama yerel LLM ile GPU çekişmesinde pencerenin siyah kalmasına yol açan GPU birleştirme kapalı
        args += ["--disable-gpu-compositing"]
    if a.proxy:
        if not re.fullmatch(r"127\.0\.0\.1:\d{2,5}", a.proxy):
            emit(ev="error", msg="proxy yalnızca 127.0.0.1 olabilir")
            return 2
        args += [f"--proxy-server=socks5://{a.proxy}",
                 '--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1',        # DNS sızıntısı yok: adlar proxy tarafında çözülür
                 "--force-webrtc-ip-handling-policy=disable_non_proxied_udp"]       # WebRTC gerçek IP'yi söylemesin
        feats.append("WebRtcHideLocalIpsWithMdns")
    if a.cdp:
        if not (1024 <= a.cdp <= 65535):
            emit(ev="error", msg="geçersiz cdp portu")
            return 2
        args += [f"--remote-debugging-port={a.cdp}", "--remote-debugging-address=127.0.0.1"]
        feats.append("CalculateNativeWinOcclusion")
        args += ["--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding", "--disable-background-timer-throttling"]
    if feats:
        args.append("--disable-features=" + ",".join(feats))
    os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = " ".join(args)

    import webview
    import jb_theme
    profile = os.path.join(HERE, "jarvis_tarayici_profil")
    os.makedirs(profile, exist_ok=True)
    start_mode = a.url == "about:blank"                # adres verilmediyse Google yerine başlangıç sayfası (jb_theme.start_html); ilk sekme bunu normal bir sayfa gibi açar

    start_url = a.url if safe_url(a.url) else "about:blank"
    if start_mode:
        start_url = jb_theme.write_start(jb_theme.load())      # pywebview yerel dosyayı kendi sunucusundan açar; ilk sekme normal bir sayfa gibi yüklenir

    def pub(u):
        """Ana sürece bildirilen adres: başlangıç sayfası gerçek adres sayılmaz (yeniden açılışta ölü yerel porta gidilmesin)."""
        return "about:blank" if jb_theme.is_start_url(u) else u
    if a.bg == "1" and a.x is None:
        a.x, a.y = -20000, -20000                       # telefon için arka planda: pencere ekranın dışında açılır (küçültülmüş pencere kare üretmez)
    state = {"badge": a.badge, "ok": a.badge_ok == "1", "adblock": a.adblock == "1", "blocked": 0, "look": jb_theme.load()}
    win = webview.create_window(TITLE, start_url, width=a.w, height=a.h, x=a.x, y=a.y, resizable=True, background_color="#0a0f18", text_select=True)
    tabs = []                                           # {"ctl": WebView2, "btn": Button}; aynı pencerede sekmeler: üstte kendi sekme şeridi, her sekme ayrı WebView2 (aynı profil/proxy)
    cur = {"t": None, "ui": None, "fs": False}

    loaded_once = threading.Event()

    def on_closed():
        emit(ev="closed")
    win.events.closed += on_closed
    win.events.loaded += lambda: loaded_once.set()

    def ui(fn):
        """fn'i pencerenin arayüz iş parçacığında çalıştırır (WinForms/WebView2 yalnızca orada güvenli)."""
        from System import Action
        form = win.native
        done = threading.Event()
        box = {}

        def run():
            try:
                box["r"] = fn()
            except Exception as e:
                box["e"] = e
            done.set()
        form.Invoke(Action(run))
        done.wait(10)
        if "e" in box:
            raise box["e"]
        return box.get("r")

    def run_js(t, js):
        """Sekmede betik çalıştırır, sonucu (JSON metni) döner. Görev arayüz iş parçacığında başlar, sonuç burada beklenir (arayüzü kilitlemez)."""
        holder = {}

        def start():
            # Kapanmış/hazır olmayan sekmede .NET istisnası üretme: pythonnet istisnayı Python'a çevirirken (AllocateTypeObject) süreci çökertebiliyor/kilitliyordu
            if t.get("closed") or t not in tabs:
                return
            cw = t["ctl"].CoreWebView2
            if cw is not None:
                holder["task"] = cw.ExecuteScriptAsync(js)
        ui(start)
        task = holder.get("task")
        if task is None:
            return ""
        from System import Array
        from System.Threading.Tasks import Task
        Task.WaitAny(Array[Task]([task]), 2500)                     # Wait() hatalı görevde istisna fırlatır; WaitAny fırlatmaz
        if int(task.Status) == 5:                       # RanToCompletion
            return str(task.Result)
        return ""

    def ensure_ui():
        """İlk açılışta bir kez: sekme şeridini kurar ve pywebview'in kendi WebView2'sini ilk sekme yapar."""
        import clr
        import System.Windows.Forms as WF
        from System.Drawing import Color
        form = win.native
        first = form.webview
        bar = WF.Panel()
        bar.Dock = WF.DockStyle.Top
        bar.Height = 34
        bar.BackColor = look_colors(Color)["bar"]
        strip = WF.FlowLayoutPanel()
        strip.Dock = WF.DockStyle.Fill
        strip.WrapContents = False
        strip.AutoScroll = False
        strip.BackColor = look_colors(Color)["bar"]
        strip.Padding = WF.Padding(4, 3, 0, 0)
        plus = WF.Button()
        plus.Text = "＋"
        plus.Dock = WF.DockStyle.Right
        plus.Width = 38
        plus.FlatStyle = WF.FlatStyle.Flat
        plus.ForeColor = look_colors(Color)["acc"]
        plus.BackColor = look_colors(Color)["off"]
        plus.FlatAppearance.BorderSize = 0
        plus.Click += lambda s_, e_: tab_cmd("new")
        theme_btn = WF.Button()
        theme_btn.Text = "Tema"
        theme_btn.Dock = WF.DockStyle.Right
        theme_btn.Width = 58
        theme_btn.FlatStyle = WF.FlatStyle.Flat
        theme_btn.ForeColor = look_colors(Color)["acc"]
        theme_btn.BackColor = look_colors(Color)["off"]
        theme_btn.FlatAppearance.BorderSize = 0
        theme_btn.Click += lambda s_, e_: theme_menu(theme_btn)
        ad_btn = WF.Button()
        ad_btn.Dock = WF.DockStyle.Right
        ad_btn.Width = 150
        ad_btn.FlatStyle = WF.FlatStyle.Flat
        ad_btn.FlatAppearance.BorderSize = 0
        ad_btn.Click += lambda s_, e_: threading.Thread(target=lambda: set_adblock(not state["adblock"]), daemon=True).start()
        bar.Controls.Add(strip)
        bar.Controls.Add(plus)
        bar.Controls.Add(theme_btn)
        bar.Controls.Add(ad_btn)
        form.Controls.Add(bar)
        bar.SendToBack()                               # üst şerit önce yerleşir, sayfa kalan alanı doldurur
        first.BringToFront()
        cur["ui"] = {"bar": bar, "strip": strip, "plus": plus, "theme": theme_btn, "ad": ad_btn, "WF": WF, "Color": Color, "first": first}
        style_ad()
        add_tab(first, "Sekme", existing=True)

    def look_colors(Color):
        """Seçili temanın şerit renkleri: bar (şerit zemini), off (etkin olmayan sekme), on (etkin sekme), acc (vurgu), txt (etkin olmayan yazı)."""
        r, g, b = jb_theme.accent(state["look"]["tema"])
        mix = lambda k: Color.FromArgb(int(r * k + 10 * (1 - k)), int(g * k + 12 * (1 - k)), int(b * k + 18 * (1 - k)))
        return {"bar": Color.FromArgb(10, 12, 18), "off": mix(0.08), "on": mix(0.38), "acc": Color.FromArgb(r, g, b),
                "txt": Color.FromArgb(int(r * 0.4 + 150), int(g * 0.4 + 150), int(b * 0.4 + 150))}

    def style_btn(t, active):
        Color = cur["ui"]["Color"]
        c = look_colors(Color)
        t["btn"].BackColor = c["on"] if active else c["off"]
        t["btn"].ForeColor = Color.White if active else c["txt"]

    def apply_look():
        """Tema değişti: sekme şeridini yeniden boyar (arayüz iş parçacığında çağrılır)."""
        if cur["ui"] is None:
            return
        Color = cur["ui"]["Color"]
        c = look_colors(Color)
        cur["ui"]["bar"].BackColor = c["bar"]
        cur["ui"]["strip"].BackColor = c["bar"]
        for k in ("plus", "theme"):
            cur["ui"][k].ForeColor = c["acc"]
            cur["ui"][k].BackColor = c["off"]
        for x in tabs:
            style_btn(x, x is cur["t"])
        style_ad()

    def style_ad():
        """'Reklam engel' düğmesinin yazısı ve rengi (açık: yeşil, kapalı: kırmızı). Arayüz iş parçacığında çağrılır."""
        u = cur["ui"]
        if u is None or "ad" not in u:
            return
        Color, on = u["Color"], state["adblock"]
        u["ad"].Text = "Reklam engel: AÇIK" if on else "Reklam engel: KAPALI"
        u["ad"].ForeColor = Color.FromArgb(120, 230, 160) if on else Color.FromArgb(255, 150, 150)
        u["ad"].BackColor = Color.FromArgb(18, 60, 40) if on else Color.FromArgb(70, 28, 28)

    def set_adblock(on, save=True):
        """Reklam engelleyiciyi açar/kapatır: ağ süzgeci anında değişir, açık sayfalardaki gizleme kuralı da (yenilemeden) açılıp kapanır. save=True ise ayar config.json'a yazılır
        (diğer ayarlara dokunulmaz) ve bir sonraki açılışta hatırlanır. Arayüz iş parçacığı DIŞINDA çağrılır."""
        import adblock
        state["adblock"] = bool(on)
        if save:
            try:
                import settings
                settings.set("reklam_engel", bool(on))
            except Exception as e:
                emit(ev="error", msg="reklam-ayar: " + type(e).__name__)
        try:
            ui(style_ad)
        except Exception:
            pass
        for t in list(tabs):
            if t.get("ready"):
                run_js(t, adblock.JS_ON if on else adblock.JS_OFF)
        emit(ev="adblock", n=state["blocked"], on=state["adblock"])

    def refresh_look():
        """Ayarlar (config.json) değişti: şeridi, sayfalardaki ses bayrağını ve açık başlangıç sayfalarını yeniler. Arayüz iş parçacığı DIŞINDA çağrılır (sayfa betiği beklenir)."""
        state["look"] = jb_theme.load()
        ui(apply_look)
        for t in list(tabs):
            if t.get("ready"):
                run_js(t, snd_js())
                if t.get("start") and ui(lambda t=t: str(t["ctl"].CoreWebView2.DocumentTitle) == "Yeni sekme"):
                    if t.get("first"):                                  # ilk sekme dosyadan açılır: dosyayı yeniden yaz, sayfayı yenile
                        jb_theme.write_start(state["look"])
                        ui(lambda t=t: t["ctl"].CoreWebView2.Reload())
                    else:
                        ui(lambda t=t: t["ctl"].CoreWebView2.NavigateToString(jb_theme.start_html(state["look"])))

    def theme_menu(btn):
        """'Tema' düğmesi: temalar ve tuş sesleri menüsü. Seçim config.json'a yazılır (sesli komutla aynı ayarlar), sonra yenilenir."""
        WF, Color = cur["ui"]["WF"], cur["ui"]["Color"]
        from System.Drawing import Point
        menu = WF.ContextMenuStrip()
        menu.BackColor = Color.FromArgb(18, 20, 28)
        menu.ForeColor = Color.White

        def pick(name=None, snd=None):
            import settings
            if name is not None:
                settings.set("tarayici_tema", name)
            if snd is not None:
                settings.set("tarayici_ses", snd)
            threading.Thread(target=refresh_look, daemon=True).start()

        for name, (rgb, _b1, _b2, label) in jb_theme.THEMES.items():
            it = menu.Items.Add("%s%s" % ("● " if name == state["look"]["tema"] else "    ", label[:1].upper() + label[1:]))
            it.ForeColor = Color.FromArgb(*rgb)
            it.Click += lambda s_, e_, n=name: pick(name=n)
        menu.Items.Add(WF.ToolStripSeparator())
        on = state["look"]["ses"]
        it = menu.Items.Add("Tuş ve tıklama sesleri: " + ("AÇIK" if on else "kapalı"))
        it.Click += lambda s_, e_: pick(snd=not on)
        menu.Show(btn, Point(0, btn.Height))

    def snd_js():
        return "window.__jvSound=%s;" % ("true" if state["look"]["ses"] else "false")

    def install_look(cw):
        """Yazma/tıklama seslerini her belgeye ekler (açık/kapalı bayrağı sayfa yüklenince ve 'look' komutuyla yazılır)."""
        try:
            cw.AddScriptToExecuteOnDocumentCreatedAsync(jb_theme.SOUND_JS)
        except Exception as e:
            emit(ev="error", msg="ses: " + type(e).__name__)

    def show_tab(t):
        for x in tabs:
            x["ctl"].Visible = x is t
            style_btn(x, x is t)
        t["ctl"].BringToFront()
        t["ctl"].Focus()
        cur["t"] = t
        try:
            emit(ev="loaded", url=pub(str(t["ctl"].Source)) if t["ctl"].Source else "", tabs=len(tabs))
        except Exception:
            pass

    def add_tab(ctl, title, existing=False):
        WF, Color = cur["ui"]["WF"], cur["ui"]["Color"]
        btn = WF.Button()
        btn.Text = title
        btn.Width = 170
        btn.Height = 28
        btn.FlatStyle = WF.FlatStyle.Flat
        btn.FlatAppearance.BorderSize = 0
        btn.TextAlign = __import__("System.Drawing", fromlist=["ContentAlignment"]).ContentAlignment.MiddleLeft
        t = {"ctl": ctl, "btn": btn}
        btn.MouseUp += lambda s_, e_: (tab_cmd("close", tab=t) if int(e_.Button) == 0x400000 else show_tab(t))       # orta tuş sekmeyi kapatır
        cur["ui"]["strip"].Controls.Add(btn)
        tabs.append(t)
        wire(t)
        show_tab(t)
        return t

    def install_adblock(cw):
        """Bu sekmenin ağ isteklerini adblock.is_blocked ile süzer (kapalıyken state['adblock'] yanlış olur, istek geçer) ve kozmetik betiği her belgeye ekler."""
        try:
            import adblock
            from Microsoft.Web.WebView2.Core import CoreWebView2WebResourceContext as Ctx

            def on_req(sn, ea):
                try:
                    if not state["adblock"]:
                        return
                    ctx = ea.ResourceContext
                    if ctx == Ctx.Document:                       # sayfanın kendisi hiçbir zaman engellenmez
                        return
                    if adblock.is_blocked(str(ea.Request.Uri)):
                        ea.Response = cw.Environment.CreateWebResourceResponse(None, 403, "Engellendi", "")
                        state["blocked"] += 1
                        if state["blocked"] % 25 == 0:
                            emit(ev="adblock", n=state["blocked"])
                except Exception:
                    pass
            # Her isteği Python'a (arayüz iş parçacığında, GIL ile) sokmak sekmeler çoğalınca pencerenin "yanıt vermiyor" olmasına yol açıyordu:
            # yalnızca engellenebilecek alan adı / yol kalıpları için süzgeç kaydedilir; kesin karar yine adblock.is_blocked'ta.
            for d in sorted(adblock.DOMAINS):
                cw.AddWebResourceRequestedFilter("*" + d + "/*", Ctx.All)
            for pat in ("adframe", "adsbygoogle", "ad-banner", "adserver", "adsense", "prebid", "pagead", "ads.js"):
                cw.AddWebResourceRequestedFilter("*/" + pat + "*", Ctx.All)
            cw.WebResourceRequested += on_req
            cw.AddScriptToExecuteOnDocumentCreatedAsync(adblock.COSMETIC_JS)
        except Exception as e:
            emit(ev="error", msg="reklam-engel: " + type(e).__name__)

    def wire(t):
        ctl = t["ctl"]

        def title_changed(s_, e_):
            try:
                tt = str(s_.DocumentTitle or "")[:22] or "Yeni sekme"
                t["btn"].Text = tt
            except Exception:
                pass

        def navigated(s_, e_):
            try:
                if t.get("start") and not t.get("sdone"):              # yeni sekme: ilk (boş) gezinme bitince başlangıç sayfası yüklenir (önce yüklenirse ezilir)
                    t["sdone"] = True
                    s_.CoreWebView2.NavigateToString(jb_theme.start_html(state["look"]))
                    return

                if t is cur["t"]:
                    emit(ev="loaded", url=pub(str(s_.Source)) if s_.Source else "", tabs=len(tabs))
                s_.ExecuteScriptAsync(jb_theme.bar_js(BAR_JS, state["look"]["tema"]))
                s_.ExecuteScriptAsync(snd_js())
                if not state["adblock"]:
                    import adblock
                    s_.ExecuteScriptAsync(adblock.JS_OFF)
                if state["badge"]:
                    s_.ExecuteScriptAsync(BADGE_JS % (json.dumps(state["badge"]), "true" if state["ok"] else "false"))
            except Exception:
                pass

        def ready(s_, e_):
            if not e_.IsSuccess:
                return
            cw = s_.CoreWebView2
            t["ready"] = True
            cw.DocumentTitleChanged += title_changed
            cw.Settings.AreBrowserAcceleratorKeysEnabled = False
            cw.Settings.AreDefaultContextMenusEnabled = False
            cw.Settings.IsStatusBarEnabled = False
            install_adblock(cw)
            install_look(cw)

            def newwin(sn, ea):
                ea.set_Handled(True)
                u = str(ea.get_Uri())
                if safe_url(u):
                    threading.Thread(target=tab_cmd, args=("new", u), daemon=True).start()
            cw.NewWindowRequested += newwin
        if t["ctl"] is cur["ui"]["first"]:
            t["first"] = True
            t["ready"] = True
            ctl.NavigationCompleted += lambda s_, e_: (title_changed(s_, None) if s_.CoreWebView2 else None)
            try:
                cw = ctl.CoreWebView2
                cw.DocumentTitleChanged += title_changed
                install_adblock(cw)
                install_look(cw)
            except Exception:
                pass
        else:
            ctl.CoreWebView2InitializationCompleted += ready
        ctl.NavigationCompleted += navigated

    def new_tab(url):
        from Microsoft.Web.WebView2.WinForms import WebView2
        from System import Uri
        form = win.native
        first = cur["ui"]["first"]
        WF = cur["ui"]["WF"]
        ctl = WebView2()
        ctl.CreationProperties = first.CreationProperties          # aynı profil + aynı bayraklar (proxy dahil): tek tarayıcı ortamı
        ctl.DefaultBackgroundColor = first.DefaultBackgroundColor
        ctl.Dock = WF.DockStyle.Fill
        ctl.Visible = False
        form.Controls.Add(ctl)
        ctl.Source = Uri(url or "about:blank")
        t = add_tab(ctl, "Yeni sekme" if not url else "Yükleniyor…")
        t["start"] = not url                                          # adres yoksa başlangıç sayfası (hazır olunca NavigateToString)
        ctl.EnsureCoreWebView2Async(None)
        return t

    def tab_cmd(act, url="", tab=None):
        def go():
            if cur["ui"] is None:
                ensure_ui()
            t = cur["t"]
            if act == "new":
                new_tab(url if safe_url(url) else "")
            elif act in ("next", "prev") and len(tabs) > 1:
                i = tabs.index(t) if t in tabs else 0
                show_tab(tabs[(i + (1 if act == "next" else -1)) % len(tabs)])
            elif act == "close":
                x = tab or t
                if x is None:
                    return
                if len(tabs) <= 1:
                    win.destroy()
                    return
                i = tabs.index(x)
                x["closed"] = True
                tabs.remove(x)
                cur["ui"]["strip"].Controls.Remove(x["btn"])
                x["btn"].Dispose()
                if x.get("first"):
                    x["ctl"].Visible = False                       # pywebview'in kendi denetimi yok edilmez (form kapanırken ona başvurur)
                    try:
                        x["ctl"].CoreWebView2.Navigate("about:blank")
                    except Exception:
                        pass
                else:
                    win.native.Controls.Remove(x["ctl"])
                    x["ctl"].Dispose()
                if cur["t"] is x:
                    show_tab(tabs[min(i, len(tabs) - 1)])
        ui(go)

    def active_cw():
        t = cur["t"]
        return t["ctl"].CoreWebView2 if t is not None else None

    def poll():
        """Sayfalar köprüsüz olduğundan düğme/kısayol/bağlantı sayfada window.__jv bayrağını bırakır; burada yoklanıp uygulanır."""
        import time
        # Müzik görselleştirici için: sayfadaki çalan medya (başlık/sanatçı/konum) de aynı yoklamada okunur; yalnızca okuma, sayfaya bir şey yazılmaz
        js = ("(function(){var v=window.__jv;window.__jv=null;var m=null;try{var e=document.querySelector('video,audio');"
              "var md=navigator.mediaSession&&navigator.mediaSession.metadata;"
              "if(e&&e.duration>0&&isFinite(e.duration)){m={t:(md&&md.title)||document.title,a:(md&&md.artist)||'',p:e.currentTime,d:e.duration,pl:!e.paused&&!e.ended}}}catch(x){}"
              "return JSON.stringify({v:v,m:m})})()")
        last_media = 0.0
        while True:
            time.sleep(0.4)
            try:
                if cur["ui"] is None:
                    continue
                for t in ([cur["t"]] if cur["t"] is not None else []):         # yalnızca öndeki sekme: gizli sekmelerde betik yanıtı gelmez (2,5 sn bekleme) ve arayüz iş parçacığı boşuna yorulur
                    if not t.get("ready") or t not in tabs:
                        continue
                    r = run_js(t, js)
                    r = json.loads(r) if r else ""
                    if not r:
                        continue
                    d = json.loads(r)
                    m = d.get("m")
                    if m and t is cur["t"] and m.get("pl") and time.time() - last_media > 0.9:
                        last_media = time.time()
                        emit(ev="media", title=str(m.get("t") or "")[:200], artist=str(m.get("a") or "")[:120],
                             pos=float(m.get("p") or 0), dur=float(m.get("d") or 0))
                    v = d.get("v")
                    if v:
                        tab_cmd(str(v.get("a")), str(v.get("u") or ""), tab=t if v.get("a") == "close" else None)
            except Exception:
                pass

    def reader():
        emit(ev="ready", proxy=a.proxy)
        import time
        loaded_once.wait(30)                           # ilk sayfa yüklenene kadar bekle (arayüz dışı iş parçacığından WebView2 özelliği okunmaz: kilitlenir)
        try:
            ui(lambda: cur["ui"] is None and ensure_ui())
        except Exception as e:
            emit(ev="error", msg="sekme-şeridi: " + type(e).__name__)
        if start_mode and cur["t"] is not None:
            cur["t"]["start"] = cur["t"]["sdone"] = True
        threading.Thread(target=poll, daemon=True).start()
        for line in sys.stdin:                         # stdin kapanınca (ana Jarvis öldü) döngü biter ve pencere kapanır
            try:
                c = json.loads(line)
            except ValueError:
                continue
            cmd = c.get("cmd")
            try:
                if cmd in ("newtab", "closetab", "nexttab", "prevtab"):
                    tab_cmd({"newtab": "new", "closetab": "close", "nexttab": "next", "prevtab": "prev"}[cmd], c.get("url", ""))
                elif cmd == "close":
                    break
                elif cmd == "fullscreen":
                    win.toggle_fullscreen()
                    cur["fs"] = not cur["fs"]
                    ui(lambda: setattr(cur["ui"]["bar"], "Visible", not cur["fs"]))
                elif cmd == "look":
                    refresh_look()
                elif cmd == "adblock":
                    set_adblock(bool(c.get("on")), save=False)         # ana süreç ayarı zaten yazdı
                elif cmd == "badge":
                    state["badge"], state["ok"] = str(c.get("text", ""))[:60], bool(c.get("ok"))
                    for t in list(tabs):
                        if t.get("ready"):
                            run_js(t, BADGE_JS % (json.dumps(state["badge"]), "true" if state["ok"] else "false"))
                elif cmd == "goto" and safe_url(c.get("url", "")):
                    ui(lambda: active_cw().Navigate(c["url"]))
                elif cmd == "back":
                    ui(lambda: active_cw().GoBack())
                elif cmd == "forward":
                    ui(lambda: active_cw().GoForward())
                elif cmd == "reload":
                    ui(lambda: active_cw().Reload())
                elif cmd == "scroll" and cur["t"] is not None:
                    run_js(cur["t"], "window.scrollBy({top:%d,behavior:'smooth'})" % max(-3000, min(3000, int(c.get("dy", 0)))))
            except Exception as e:
                emit(ev="error", msg=type(e).__name__)
        try:
            win.destroy()
        except Exception:
            pass

    try:                                                # target=_blank / window.open (ilk sekme): pywebview bunları varsayılan tarayıcıya atıyordu; artık yeni sekme
        from webview.platforms import edgechromium as _ec

        def _new_window(self, sender, args):
            args.set_Handled(True)
            uri = str(args.get_Uri())
            if safe_url(uri):
                threading.Thread(target=tab_cmd, args=("new", uri), daemon=True).start()
        _ec.EdgeChrome.on_new_window_request = _new_window
    except Exception as e:
        emit(ev="error", msg="yeni-pencere: " + type(e).__name__)
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False

    webview.start(lambda: threading.Thread(target=reader, daemon=True).start(), private_mode=False, storage_path=profile)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
