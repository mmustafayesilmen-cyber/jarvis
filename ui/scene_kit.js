/* JARVIS ortak mod/laboratuvar kiti. Sayfanın kendi WebSocket bağlantısını paylaşır (ikinci bağlantı açmaz).
   Ekledikleri: Jarvis durum adası (dinliyor / düşünüyor / konuşuyor), mikrofon aç-kapa, konuşmayı kes, altyazı, aranabilir komut paleti (F1 / Ctrl+K),
   gizlilik göstergesi: komut yalnızca işlenirken RAM'de durur, işlenince silinir; sayfadaki "› komut" yankısı da birkaç saniye sonra ekrandan kalkar. */
(() => {
  "use strict";
  const P = location.pathname;
  const KIND = P.startsWith("/scene/") ? P.split("/")[2] : P.replace(/^\//, "");
  let sock = null, help = null, mic = null, capT = 0, sel = -1;
  const LS = (k, v) => { try { if (v === undefined) return localStorage.getItem("kit_" + k); localStorage.setItem("kit_" + k, v); } catch (e) { return null; } };
  let captions = LS("cap") !== "0", capMuteUntil = 0;     // capMuteUntil: hafıza oyunu gibi sayfalar altyazıyı kısa süre susturabilir

  // ---- sayfanın WebSocket'ini paylaş
  const NWS = window.WebSocket;
  function KitWS(url, prot) {
    const w = prot === undefined ? new NWS(url) : new NWS(url, prot);
    if (/127\.0\.0\.1:8765\/ws/.test(String(url))) {
      sock = w;
      w.addEventListener("message", onMsg);
      w.addEventListener("open", () => conn(true));
      w.addEventListener("close", () => conn(false));
    }
    return w;
  }
  KitWS.prototype = NWS.prototype;
  ["CONNECTING", "OPEN", "CLOSING", "CLOSED"].forEach((k, i) => { KitWS[k] = i; });
  window.WebSocket = KitWS;
  const send = o => { if (sock && sock.readyState === 1) sock.send(JSON.stringify(o)); };

  const ICON = {
    mic: '<path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.9V21h2v-3.1A7 7 0 0 0 19 11z"/>',
    micoff: '<path d="M19 11h-2a5 5 0 0 1-.6 2.4l1.5 1.5A7 7 0 0 0 19 11zM15 11V5a3 3 0 0 0-5.9-.8L15 10.1zM3.3 3.3 2 4.6l7 7V11a3 3 0 0 0 4.5 2.6l1.6 1.6A5 5 0 0 1 7 11H5a7 7 0 0 0 6 6.9V21h2v-3.1a7 7 0 0 0 3.4-1.4l3 3 1.3-1.3z"/>',
    stop: '<path d="M6 6h12v12H6z"/>',
    cmd: '<path d="M3 5h18v2H3zm0 6h12v2H3zm0 6h18v2H3z"/>',
    lock: '<path d="M17 9V7a5 5 0 0 0-10 0v2H5v12h14V9zm-8-2a3 3 0 0 1 6 0v2H9z"/>',
    search: '<path d="M10 3a7 7 0 0 1 5.6 11.2l5.1 5.1-1.4 1.4-5.1-5.1A7 7 0 1 1 10 3zm0 2a5 5 0 1 0 0 10 5 5 0 0 0 0-10z"/>'
  };
  const svg = n => `<svg viewBox="0 0 24 24">${ICON[n]}</svg>`;
  const ST = { idle: "Hazır", listening: "Dinliyor", thinking: "Düşünüyor", speaking: "Konuşuyor" };
  let $d, $st, $mic, $stop, $priv, $cap, $toasts, $pal, $q, $list;

  function build() {
    if (KIND !== "illusion" && KIND !== "kuran") { const v = document.createElement("div"); v.className = "kit-vig"; document.body.appendChild(v); }   // illüzyonlarda algıyı bozmasın
    $d = document.createElement("div"); $d.id = "kit-dock"; $d.dataset.s = "idle";
    $d.innerHTML = `<span id="kit-orb"></span><span id="kit-st">Hazır</span><span class="kit-sep"></span>
      <button class="kit-b" id="kit-mic" title="Mikrofonu aç / kapat">${svg("mic")}<span>MİKROFON</span></button>
      <button class="kit-b" id="kit-stop" title="Jarvis'in konuşmasını kes" hidden>${svg("stop")}<span>SUS</span></button>
      <button class="kit-b" id="kit-cmdb" title="Komutlar (F1 ya da Ctrl+K)">${svg("cmd")}<span>KOMUTLAR</span><span class="kit-k">F1</span></button>
      <span class="kit-b" id="kit-priv" title="Bu modda söylediğiniz ve yazdığınız komutlar günlüğe ya da diske yazılmaz; yalnızca işlenirken bellekte durur ve hemen silinir.">${svg("lock")}<span id="kit-pt">UNUTULUYOR</span></span>`;
    // sayfanın kendi üst çubuğuna (MASAÜSTÜ / KAPAT düğmesinin soluna) yerleşir; böylece sekme ve düğmelerin üstüne binmez
    const anchor = document.getElementById("peek") || document.getElementById("close");
    if (anchor && anchor.parentNode && anchor.getBoundingClientRect().top < 80) { $d.classList.add("inline"); anchor.parentNode.insertBefore($d, anchor); }
    else document.body.appendChild($d);
    $st =$d.querySelector("#kit-st"); $mic = $d.querySelector("#kit-mic"); $stop = $d.querySelector("#kit-stop"); $priv = $d.querySelector("#kit-priv");
    $mic.onclick = () => send({ type: "mic_toggle" });
    $stop.onclick = () => send({ type: "stop" });
    $d.querySelector("#kit-cmdb").onclick = () => openPal();
    $cap = document.createElement("div"); $cap.id = "kit-cap";
    const slot = document.getElementById("kit-cap-slot");          // sayfa isterse altyazıyı kendi yerine koyar (ör. satranç: tahtanın üstüne binmesin)
    if (slot) { $cap.classList.add("slot"); slot.appendChild($cap); } else document.body.appendChild($cap);
    $toasts = document.createElement("div"); $toasts.id = "kit-toasts"; document.body.appendChild($toasts);
    $pal = document.createElement("div"); $pal.id = "kit-pal";
    $pal.innerHTML = `<div id="kit-box"><div id="kit-head">${svg("search")}<input id="kit-q" placeholder="Komut ara ya da yazıp Enter'a basın…" spellcheck="false" autocomplete="off"><span id="kit-tt"></span></div>
      <div id="kit-list"><div class="kit-empty">Komutlar yükleniyor…</div></div>
      <div id="kit-foot"><span>↑↓ seç · Enter gönder · Esc kapat</span><span>Komutlar uygulanınca unutulur</span><label><input type="checkbox" id="kit-capc"> Altyazı</label></div></div>`;
    document.body.appendChild($pal);
    $q = $pal.querySelector("#kit-q"); $list = $pal.querySelector("#kit-list");
    $pal.addEventListener("mousedown", e => { if (e.target === $pal) closePal(); });
    $q.addEventListener("input", () => { sel = -1; renderPal(); });
    const cc = $pal.querySelector("#kit-capc"); cc.checked = captions;
    cc.onchange = () => { captions = cc.checked; LS("cap", captions ? "1" : "0"); if (!captions) $cap.classList.remove("on"); };
    watchEcho();
  }

  // ---- sunucu mesajları
  function onMsg(ev) {
    let m; try { m = JSON.parse(ev.data); } catch (e) { return; }
    if (!$d) return;
    if (m.type === "state" && ST[m.state]) {
      $d.dataset.s = m.state; $st.textContent = ST[m.state]; $stop.hidden = m.state !== "speaking";
      if (m.state === "idle" || m.state === "listening") { clearTimeout(capT); capT = setTimeout(() => $cap.classList.remove("on"), 2200); }
    } else if (m.type === "mic") {
      mic = !m.muted; $mic.classList.toggle("muted", !mic); $mic.innerHTML = svg(mic ? "mic" : "micoff") + `<span>${mic ? "MİKROFON" : "MİKROFON KAPALI"}</span>`;
      if (mic) delete $d.dataset.off; else $d.dataset.off = "1";
    } else if (m.type === "jarvis" && m.text && captions && Date.now() > capMuteUntil) {
      $cap.innerHTML = "<b>JARVIS</b>"; $cap.appendChild(document.createTextNode(String(m.text).slice(0, 400)));
      $cap.classList.add("on"); clearTimeout(capT); capT = setTimeout(() => $cap.classList.remove("on"), Math.min(16000, 2500 + String(m.text).length * 70));
    } else if (m.type === "cmdbuf") {
      const n = (m.items || []).length; $priv.classList.toggle("busy", n > 0);
      $priv.querySelector("#kit-pt").textContent = n ? "İŞLENİYOR…" : "UNUTULDU ✓";
      if (!n) setTimeout(() => { if (!$priv.classList.contains("busy")) $priv.querySelector("#kit-pt").textContent = "UNUTULUYOR"; }, 2500);
    }
  }
  function conn(ok) { if ($d) { if (ok) $d.classList.remove("hide"); $st.textContent = ok ? ST[$d.dataset.s] || "Hazır" : "Bağlanıyor…"; } }

  function toast(text, cls) {
    const t = document.createElement("div"); t.className = "kit-t " + (cls || ""); t.textContent = text; $toasts.appendChild(t);
    setTimeout(() => { t.style.transition = "opacity .4s"; t.style.opacity = "0"; setTimeout(() => t.remove(), 450); }, 2600);
  }

  // ---- sayfadaki "› komut" yankısını birkaç saniye sonra ekrandan kaldır (komut unutuldu)
  function watchEcho() {
    const seen = new WeakMap();
    const check = el => {
      if (!el || el.nodeType !== 1 || el.children.length || el === $q || el.closest("#kit-pal,#kit-dock")) return;
      const tx = el.textContent || "";
      if (!/^\s*›/.test(tx)) return;
      clearTimeout(seen.get(el));
      seen.set(el, setTimeout(() => {
        if ((el.textContent || "") === tx) { el.textContent = "✓ komut uygulandı ve unutuldu"; el.classList.add("kit-forgot"); }
      }, 3000));
    };
    new MutationObserver(ms => ms.forEach(m => check(m.type === "characterData" ? m.target.parentElement : m.target)))
      .observe(document.body, { subtree: true, childList: true, characterData: true });
  }

  // ---- komut paleti
  async function loadHelp() {
    if (help) return help;
    try { help = await (await fetch("/kit-help/" + encodeURIComponent(KIND))).json(); } catch (e) { help = { title: "", groups: [] }; }
    return help;
  }
  const norm = s => String(s).toLocaleLowerCase("tr").replace(/[^\p{L}\p{N} ]/gu, " ");
  function items() { return [...$list.querySelectorAll(".kit-cmd")]; }
  function renderPal() {
    const q = norm($q.value).trim(), h = help || { groups: [] };
    $pal.querySelector("#kit-tt").textContent = h.title || "";
    $list.innerHTML = "";
    let n = 0;
    h.groups.forEach(g => {
      const cm = g.cmds.filter(c => !q || norm(c).includes(q) || norm(g.title).includes(q));
      if (!cm.length) return;
      const box = document.createElement("div"); box.className = "kit-g";
      const h4 = document.createElement("h4"); h4.textContent = g.title; box.appendChild(h4);
      if (!q && g.desc) { const p = document.createElement("p"); p.textContent = g.desc; box.appendChild(p); }
      const wr = document.createElement("div"); wr.className = "kit-cmds";
      cm.forEach(c => { const b = document.createElement("button"); b.className = "kit-cmd"; b.textContent = c; b.onclick = () => run(c); wr.appendChild(b); n++; });
      box.appendChild(wr); $list.appendChild(box);
    });
    if (!n) {
      const e = document.createElement("div"); e.className = "kit-empty";
      e.textContent = q ? `Eşleşen komut yok. Enter'a basarsanız "${$q.value.trim()}" komut olarak gönderilir.` : "Bu mod için kılavuzda örnek komut bulunamadı.";
      $list.appendChild(e);
    }
    items().forEach((b, i) => b.classList.toggle("sel", i === sel));
  }
  async function openPal() { $pal.classList.add("on"); $q.value = ""; sel = -1; renderPal(); setTimeout(() => $q.focus(), 30); await loadHelp(); renderPal(); }
  function closePal() { $pal.classList.remove("on"); $q.value = ""; }
  function run(text) {
    text = String(text).trim(); if (!text) return;
    send({ type: "text", text }); closePal(); toast("Komut uygulanıyor, sonra unutulacak");
  }
  // yakalama evresinde: palet açıkken tuşlar sayfaya (ör. Esc = modu kapat) ulaşmaz
  window.addEventListener("keydown", e => {
    const open = $pal && $pal.classList.contains("on");
    if (e.key === "F1" || ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K"))) { e.preventDefault(); e.stopImmediatePropagation(); open ? closePal() : openPal(); return; }
    if (!open) return;
    e.stopImmediatePropagation();
    const it = items();
    if (e.key === "Escape") { e.preventDefault(); closePal(); }
    else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault(); if (!it.length) return;
      sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + it.length) % it.length;
      it.forEach((b, i) => b.classList.toggle("sel", i === sel)); it[sel].scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") { e.preventDefault(); run(sel >= 0 && it[sel] ? it[sel].textContent : $q.value); }
  }, true);

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build); else build();
  window.JarvisKit = { toast, openPal, muteCaptions: ms => { capMuteUntil = Date.now() + (ms || 0); if ($cap) $cap.classList.remove("on"); } };
})();

/* Ortak görünüm sınıfları (bkz. scene_kit.css sonu): vurgu rengi olan sayfaya kit-acc, düz koyu arka planlı sayfaya kit-flat. */
(function(){
  function lum(s){const m=(s.match(/[\d.]+/g)||[]).map(Number);return m.length<3||(m.length>3&&m[3]<.5)?null:m[0]*.3+m[1]*.59+m[2]*.11}
  function mark(){try{
    const de=document.documentElement,b=getComputedStyle(document.body),h=getComputedStyle(de);
    if(!h.getPropertyValue("--c").trim())return;
    de.classList.add("kit-acc");
    let l=lum(b.backgroundColor);if(l===null)l=lum(h.backgroundColor);
    if(l!==null&&l<60&&b.backgroundImage==="none")de.classList.add("kit-flat");
  }catch(e){}}
  document.readyState==="loading"?addEventListener("DOMContentLoaded",mark):mark();
})();
