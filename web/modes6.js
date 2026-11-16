"use strict";
/* Mod 6: Jarvis Tarayıcı (başlangıç sayfası). Telefondaki Jarvis uygulamasının tarayıcı başlangıç ekranının aynısı: arama kutusu + hızlı erişim kutuları.
   Not: web uygulaması kendi içinde başka sitelerin sayfasını gösteremez (siteler buna izin vermez); adresler telefonun tarayıcısında açılır.
   Komut kalıplarında \b KULLANMAYIN. */
(function(){
 const DEF=[["YouTube","https://www.youtube.com/","#ff2d4d","▶"],["Google","https://www.google.com/","#4d8dff","G"],["ChatGPT","https://chatgpt.com/","#2dffb0","C"],["Gemini","https://gemini.google.com/","#b06dff","✦"],["Claude","https://claude.ai/","#ff9a3d","✳"],["Vikipedi","https://tr.wikipedia.org/","#e8e8e8","W"],["GitHub","https://github.com/","#8aa0b0","⌥"],["Reddit","https://www.reddit.com/","#ff5a1f","R"]];
 const COL=["#ff2d4d","#4d8dff","#2dffb0","#b06dff","#ff9a3d","#e8e8e8","#8aa0b0","#ff5a1f","#ffd84a"];
 let D=DB.get("tarayici",{sites:DEF}),el=null;const save=()=>DB.set("tarayici",D);
 // adres mi arama mı: "ornek.com" / "http..." -> adres; diğerleri Google araması (aramalar saklanmaz)
 function toUrl(q){q=q.trim();if(!q)return null;if(/^https?:\/\/\S+$/i.test(q))return q;if(/^[\w-]+(\.[\w-]+)+(\/\S*)?$/.test(q)&&!/\s/.test(q))return"https://"+q;return"https://www.google.com/search?q="+encodeURIComponent(q)}
 function go(url){if(!url)return false;let w=null;try{w=window.open(url,"_blank","noopener")}catch(e){}
  if(!w){const b=el&&el.querySelector("#tgo");if(b){b.style.display="block";b.innerHTML=`<a href="${esc(url)}" target="_blank" rel="noopener" style="display:block;text-align:center;padding:14px;border-radius:14px;background:var(--c);color:#02141a;font-weight:700;text-decoration:none">AÇ ›  ${esc(url.replace(/^https?:\/\//,"").slice(0,40))}</a>`}}return true}
 function ui(){if(!el||!el.isConnected)return;el.querySelector("#tg").innerHTML=D.sites.map((s,i)=>`<a href="${esc(s[1])}" target="_blank" rel="noopener" data-i="${i}" style="--k:${s[2]}" class="ts"><i>${esc(s[3])}</i><span>${esc(s[0])}</span><b data-x="${i}">×</b></a>`).join("");
  el.querySelectorAll("#tg [data-x]").forEach(b=>b.onclick=ev=>{ev.preventDefault();ev.stopPropagation();D.sites.splice(+b.dataset.x,1);save();ui()})}
 function render(e){el=e;e.innerHTML=`<style>.hb{text-align:center;padding:26px 0 8px}.hb h2{margin:0;font:700 32px system-ui;letter-spacing:.35em;color:var(--c);text-shadow:0 0 18px var(--c),0 0 40px #3fe8ff66}.hb div{font-size:11px;letter-spacing:.3em;color:var(--mut);margin-top:6px}
  #tgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px 8px;margin:22px 0}.ts{position:relative;display:flex;flex-direction:column;align-items:center;gap:8px;text-decoration:none;color:var(--tx);font-size:12px}
  .ts i{width:58px;height:58px;border-radius:18px;display:flex;align-items:center;justify-content:center;font:700 22px system-ui;font-style:normal;color:#fff;background:#071a26;border:1.5px solid var(--k);box-shadow:0 0 12px color-mix(in srgb,var(--k) 40%,transparent)}.ts:active i{transform:scale(.92)}
  .ts b{display:none;position:absolute;top:-6px;right:6px;width:20px;height:20px;border-radius:50%;background:var(--bad);color:#fff;font-size:13px;line-height:20px;text-align:center}body.edit .ts b{display:block}
  #tq{width:100%;padding:15px 20px;border-radius:30px;border:1.5px solid var(--c);background:#04121bcc;color:#fff;font-size:16px;box-shadow:0 0 14px #3fe8ff55,inset 0 0 12px #3fe8ff22}</style>
  <div class="hb"><h2>JARVIS</h2><div>TARAYICI</div></div><form id="tf"><input id="tq" placeholder="Ara ya da adres yaz" autocomplete="off" autocapitalize="off" enterkeyhint="go"></form><div id="tgo" style="display:none;margin-top:12px"></div><div id="tg"></div>
  <div class="row" style="justify-content:center"><button id="te">DÜZENLE</button></div>
  <div class="card" id="tadd" style="display:none"><h3>Site ekle</h3><div class="row"><input id="tn" placeholder="Ad" style="width:110px"><input id="tu" placeholder="adres (örn. ornek.com)" style="flex:1;min-width:120px"><button class="prim" id="tb">EKLE</button></div></div>
  <div class="mut" style="font-size:12px;text-align:center;margin-top:14px;line-height:1.5">Adresler telefonunuzun tarayıcısında açılır. Aramalar ve gezdiğiniz siteler bu uygulamada saklanmaz.</div>`;
  const q=s=>e.querySelector(s);q("#tg").style.cssText="display:grid;grid-template-columns:repeat(4,1fr);gap:18px 8px;margin:22px 0";
  q("#tf").onsubmit=ev=>{ev.preventDefault();const u=toUrl(q("#tq").value);if(u){go(u);q("#tq").value=""}};
  q("#te").onclick=()=>{document.body.classList.toggle("edit");q("#tadd").style.display=document.body.classList.contains("edit")?"block":"none";q("#te").textContent=document.body.classList.contains("edit")?"BİTTİ":"DÜZENLE"};
  q("#tb").onclick=()=>{const u=toUrl(q("#tu").value),n=q("#tn").value.trim();if(u&&!/google\.com\/search/.test(u)){D.sites.push([n||u.replace(/^https?:\/\/(www\.)?/,"").split("/")[0],u,COL[rnd(COL.length)],(n||"•").charAt(0).toUpperCase()]);save();ui();q("#tu").value=q("#tn").value=""}};ui()}
 function cmd(t,raw){
  const s=D.sites.find(s=>t.includes(norm(s[0])));const m=t.match(/(?:^|\s)ara(?:\s+|$)(.*)/)||t.match(/(.+?)\s+ara$/);
  const sm=t.match(/(youtube|google|vikipedi)\s*(?:da|de|'da)?\s*ara\w*\s+(.+)/);
  if(sm){const q=encodeURIComponent(sm[2]);go(sm[1]==="youtube"?"https://www.youtube.com/results?search_query="+q:sm[1]==="vikipedi"?"https://tr.wikipedia.org/w/index.php?search="+q:"https://www.google.com/search?q="+q);return sm[1]+" aranıyor."}
  if(s&&/(aç|git|göster)/.test(t)){go(s[1]);return s[0]+" açılıyor."}
  if(/(?:^|\s)ara(?:\s|$)/.test(t)&&m&&m[1]&&m[1].trim().length>1){go("https://www.google.com/search?q="+encodeURIComponent(raw.replace(/(?:^|\s)ara\w*/i,"").trim()));return"Aranıyor."}return null}
 reg({id:"tarayici",name:"Jarvis Tarayıcı",icon:"🌐",say:/tarayıcı|youtube|google|gemini|chatgpt|claude|vikipedi|github|reddit/,render,cmd,leave(){document.body.classList.remove("edit")}});
})();
