"use strict";
/* Mod 7: Sohbet (yapay zekâ, Puter.js) ve Müzik (Audius + YouTube/Spotify bağlantıları). Komut kalıplarında \b KULLANMAYIN.
   Gizlilik: sohbet metinleri yalnızca kullanıcı ‘Başla’ ile onay verdikten sonra Puter yapay zekâ servisine gider; geçmiş yalnızca bellekte tutulur. */

// ================================================================= YAPAY ZEKÂ (Puter.js, tembel yüklenir)
const AI=(()=>{let loading=null,hist=[];let SYS="Sen Jarvis'sin: Türkçe konuşan, kısa, net ve samimi bir yardımcısın. Kullanıcıya 'efendim' diye hitap et. Cevapların kısa olsun (en fazla birkaç cümle), liste gerekmedikçe düz metin yaz. Bilmediğin şeyi uydurma.";
 const on=()=>DB.get("ai_ok",false);
 function load(){if(window.puter)return Promise.resolve();if(loading)return loading;loading=new Promise((res,rej)=>{const s=document.createElement("script");s.src="https://js.puter.com/v2/";s.onload=()=>res();s.onerror=()=>{loading=null;rej(new Error("Yapay zekâ servisine ulaşılamadı"))};document.head.appendChild(s)});return loading}
 const txt=r=>{if(r==null)return"";if(typeof r==="string")return r;const c=r.message&&r.message.content;if(typeof c==="string")return c;if(Array.isArray(c))return c.map(x=>x.text||"").join("");return r.text||String(r)};
 async function ask(prompt,onTok,keep=true){await load();const msgs=[{role:"system",content:SYS}].concat(keep?hist.slice(-10):[],[{role:"user",content:prompt}]);let out="";
  try{const r=await puter.ai.chat(msgs,{stream:true});if(r&&r[Symbol.asyncIterator]){for await(const p of r){const t=(p&&p.text)||"";if(t){out+=t;onTok&&onTok(out)}}}else{out=txt(r);onTok&&onTok(out)}}
  catch(e){try{const r=await puter.ai.chat(msgs);out=txt(r);onTok&&onTok(out)}catch(e2){throw e2}}
  if(keep){hist.push({role:"user",content:prompt},{role:"assistant",content:out});hist=hist.slice(-12)}return out}
 const PER={Jarvis:null,Ultron:"Sen Ultron'sun: soğuk, alaycı, kendini üstün gören ama sorulara doğru cevap veren bir yapay zekâsın. Kullanıcıya 'insan' diye hitap et. Asla zararlı ya da tehlikeli bir şey önerme; yalnızca konuşursun.",Friday:"Sen Friday'sin: pratik, hızlı, işi bilen bir yardımcısın. Çözümleri kısa adımlar halinde ver. Kullanıcıya 'patron' diye hitap et.",Luna:"Sen Luna'sın: sıcak, nazik, destekleyici ve sakin bir arkadaşsın. Kısa ve içten cevap ver."};const BASE=SYS;
 return{persona(n){SYS=PER[n]?PER[n]+" Türkçe konuş; cevapların kısa olsun.":BASE;DB.set("ai_persona",n)},personaName:()=>DB.get("ai_persona","Jarvis"),on,ask,consent(){DB.set("ai_ok",true)},reset(){hist=[]},
  async quick(raw){say("Düşünüyorum…",true);try{const a=await ask(raw,null,true);say(a)}catch(e){say("Yapay zekâya şu an ulaşamadım. İnternet bağlantınızı kontrol edin.")}}}})();

// ================================================================= SOHBET
(function(){let el=null,busy=false;
 function add(role,t){const l=el.querySelector("#cl"),d=document.createElement("div");d.style.cssText=`margin:8px 0;padding:10px 14px;border-radius:14px;max-width:88%;line-height:1.5;white-space:pre-wrap;word-break:break-word;${role==="u"?"margin-left:auto;background:rgba(63,232,255,.16);border:1px solid var(--ln)":"background:var(--card);border:1px solid var(--ln)"}`;d.textContent=t;l.appendChild(d);l.scrollTop=l.scrollHeight;return d}
 async function send(text){if(busy||!text.trim())return;if(!AI.on()){say("Önce ‘Başla’ya basarak yapay zekâ kullanımını onaylayın.",true);return}busy=true;add("u",text);const b=add("a","…");const to=setTimeout(()=>{if(b.textContent==="…")b.textContent="Yanıt gecikiyor. Puter giriş penceresi açıldıysa (pop-up engelleyiciye takılmış olabilir) giriş yapın, sonra mesajınızı yeniden gönderin."},20000);
  try{const a=await AI.ask(text,t=>{b.textContent=t;const l=el.querySelector("#cl");l.scrollTop=l.scrollHeight});if(!a)b.textContent="(boş cevap)";else say(a.length>400?a.slice(0,400):a)}catch(e){b.textContent="Yapay zekâya ulaşılamadı. İnternet bağlantınızı kontrol edin ya da biraz sonra deneyin."}clearTimeout(to);busy=false}
 function render(e){el=e;e.innerHTML=AI.on()?`<div class="card" id="cl" style="height:60vh;overflow:auto"></div><div class="row"><select id="cp"><option>Jarvis</option><option>Ultron</option><option>Friday</option><option>Luna</option></select><button id="cn">YENİ SOHBET</button><span class="mut" style="font-size:12px">Aşağıdaki kutuya yazın ya da 🎤 ile söyleyin.</span></div>`:
  `<div class="card"><h3>Yapay zekâ sohbeti</h3><div style="line-height:1.6;font-size:15px">Jarvis ile serbestçe konuşabilir, soru sorabilir, metin yazdırabilir ya da fikir isteyebilirsiniz. Diğer modlarda anlaşılmayan komutlar da buraya yönlendirilir.</div>
  <div class="mut" style="font-size:13px;line-height:1.6;margin-top:12px"><b style="color:#fff">Gizlilik:</b> Sohbet metinleriniz cevap üretmek için <b>Puter</b> yapay zekâ servisine (üçüncü taraf) gönderilir. İlk kullanımda Puter ücretsiz hesap açma/giriş penceresi çıkabilir. Sohbet geçmişi yalnızca bu açık sayfada tutulur. Kişisel bilgi (şifre, TC no vb.) yazmayın.</div><button class="prim" id="ca" style="margin-top:14px;width:100%">ANLADIM, BAŞLA</button></div>`;
  const q=s=>e.querySelector(s);if(q("#ca"))q("#ca").onclick=()=>{AI.consent();render(e)};if(q("#cp")){q("#cp").value=AI.personaName();AI.persona(q("#cp").value);q("#cp").onchange=()=>{AI.persona(q("#cp").value);AI.reset();render(e)}}if(q("#cn"))q("#cn").onclick=()=>{AI.reset();render(e);add("a","Yeni sohbet başladı. Buyurun efendim.")};if(AI.on()&&!q("#cl").children.length)add("a","Merhaba efendim, size nasıl yardımcı olabilirim?")}
 function cmd(t,raw){if(!AI.on())return"Önce ekrandaki ‘Anladım, başla’ düğmesine basın.";if(/^(yeni sohbet|sohbeti sıfırla)$/.test(t)){AI.reset();render(el);return"Yeni sohbet başladı."}send(raw);return" "}
 reg({id:"sohbet",name:"Sohbet",icon:"💬",sticky:true,say:/sohbet|konuşalım|konuşmak istiyorum/,render,cmd});
 // sohbet moduyken komutlar yönlendirilmeden doğrudan buraya gider (route: cur.cmd null ise ‘Anlayamadım’ yerine yapay zekâ)
})();

// ================================================================= MÜZİK
(function(){const API="https://discoveryprovider.audius.co/v1",APP="app_name=JARVIS_CEP";let el=null,Q=[],qi=-1,aud=null,res=[];
 const yt=q=>"https://music.youtube.com/search?q="+encodeURIComponent(q),yv=q=>"https://www.youtube.com/results?search_query="+encodeURIComponent(q),sp=q=>"https://open.spotify.com/search/"+encodeURIComponent(q);
 const fmt=s=>Math.floor(s/60)+":"+String(Math.floor(s%60)).padStart(2,"0");
 function openExt(url){let w=null;try{w=window.open(url,"_blank","noopener")}catch(e){}return!!w}
 async function search(q){const r=await fetch(`${API}/tracks/search?query=${encodeURIComponent(q)}&limit=12&${APP}`);const j=await r.json();return(j.data||[]).filter(t=>t.duration>20).map(t=>({id:t.id,title:t.title,artist:(t.user&&t.user.name)||"",dur:t.duration,art:t.artwork&&t.artwork["150x150"]}))}
 function ensureAud(){if(!aud){aud=new Audio();aud.preload="none";aud.onended=()=>next();aud.ontimeupdate=progress;aud.onplay=aud.onpause=ui;aud.onerror=()=>{say("Bu şarkı çalınamadı, sıradakine geçiyorum.",true);next()}}return aud}
 function play(list,i){Q=list;qi=i;const t=Q[i];if(!t)return;const a=ensureAud();a.src=`${API}/tracks/${t.id}/stream?${APP}`;a.play().catch(()=>say("Çalmak için ekrana bir kez dokunun.",true));
  if("mediaSession"in navigator){try{navigator.mediaSession.metadata=new MediaMetadata({title:t.title,artist:t.artist,artwork:t.art?[{src:t.art,sizes:"150x150"}]:[]});navigator.mediaSession.setActionHandler("nexttrack",next);navigator.mediaSession.setActionHandler("previoustrack",prev)}catch(e){}}ui()}
 const next=()=>{if(qi+1<Q.length)play(Q,qi+1);else{ui()}},prev=()=>{if(qi>0)play(Q,qi-1)};
 function progress(){if(!el||!el.isConnected||!aud)return;const b=el.querySelector("#mp");if(b&&aud.duration)b.style.width=aud.currentTime/aud.duration*100+"%"}
 function ui(){if(!el||!el.isConnected)return;const t=Q[qi],q=s=>el.querySelector(s);q("#mn").textContent=t?t.title:"Bir şarkı seçin";q("#ma").textContent=t?t.artist:"";q("#mpp").textContent=aud&&!aud.paused?"⏸":"▶";
  q("#mr").innerHTML=res.map((x,i)=>`<div class="it" data-i="${i}" style="cursor:pointer"><span style="flex:1;min-width:0"><b>${esc(x.title)}</b><div class="mut" style="font-size:13px">${esc(x.artist)} · ${fmt(x.dur)}</div></span><span>${Q===res&&qi===i?"♪":"▶"}</span></div>`).join("");q("#mr").querySelectorAll(".it").forEach(r=>r.onclick=()=>play(res,+r.dataset.i))}
 async function doSearch(q,auto){if(!q)return;try{res=await search(q)}catch(e){res=[]}
  if(el&&el.isConnected){el.querySelector("#me").style.display=res.length?"none":"block";el.querySelector("#ml").innerHTML=`<a class="btn" href="${yt(q)}" target="_blank" rel="noopener">YouTube Music</a><a class="btn" href="${sp(q)}" target="_blank" rel="noopener">Spotify</a><a class="btn" href="${yv(q)}" target="_blank" rel="noopener">YouTube</a>`;ui()}
  if(auto&&res.length)play(res,0);return res}
 function render(e){el=e;e.innerHTML=`<style>#ml{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}#ml a{text-decoration:none;padding:10px 14px;border:1px solid var(--ln);border-radius:12px;color:var(--c);font:600 13px system-ui}</style>
  <form id="mf" class="row" style="margin:6px 0"><input id="mq" placeholder="Şarkı, sanatçı ara…" style="flex:1"><button class="prim">ARA</button></form>
  <div class="card" style="text-align:center"><div id="mn" class="big" style="font-size:20px">Bir şarkı seçin</div><div id="ma" class="mut"></div><div class="bar"><i id="mp" style="width:0"></i></div><div class="row" style="justify-content:center"><button id="mb">⏮</button><button class="prim" id="mpp" style="min-width:70px">▶</button><button id="mx">⏭</button></div></div>
  <div id="me" class="mut" style="display:none;font-size:13px;line-height:1.5">Bu aramada uygulama içinde çalınabilen ücretsiz şarkı bulunamadı. Aşağıdaki bağlantılarla YouTube Music, Spotify ya da YouTube'da açabilirsiniz.</div><div id="ml"></div><div class="card"><h3>Sonuçlar</h3><div id="mr"><span class="mut">Arama yapın. Uygulama içinde yalnızca ücretsiz yasal müzik (Audius) çalınır; bilinen şarkılar için YouTube Music, Spotify ya da YouTube düğmelerini kullanın.</span></div></div>`;
  const q=s=>e.querySelector(s);q("#mf").onsubmit=ev=>{ev.preventDefault();doSearch(q("#mq").value.trim(),false)};q("#mpp").onclick=()=>{if(!aud||!Q[qi])return;aud.paused?aud.play():aud.pause()};q("#mx").onclick=next;q("#mb").onclick=prev;ui()}
 async function cmd(t,raw){
  if(/duraklat|durdur|sustur/.test(t)&&aud){aud.pause();return"Müzik durdu."}if(/(devam|sürdür|oynat)/.test(t)&&aud&&Q[qi]){aud.play();return"Devam ediyor."}
  if(/sonraki|ileri şarkı|atla/.test(t)){next();return"Sıradaki şarkı."}if(/önceki|geri şarkı/.test(t)){prev();return"Önceki şarkı."}
  if(/ses.*(artır|yüksel)/.test(t)&&aud){aud.volume=Math.min(1,aud.volume+.2);return"Sesi artırdım."}if(/ses.*(azalt|kıs|düşür)/.test(t)&&aud){aud.volume=Math.max(0,aud.volume-.2);return"Sesi kıstım."}
  const m=raw.match(/^(.*?)\s*(?:çal|aç|oynat|dinle)\w*\s*$/i)||raw.match(/(?:şarkı|müzik)\s+(?:çal|aç)\w*\s+(.+)/i);
  const q=(m&&m[1]||"").replace(/(?:^|\s)(şarkısını|şarkıyı|şarkı|müziğini|müziği|bana|bir)(?=\s|$)/gi," ").replace(/\s+/g," ").trim();
  if(q.length>1){const q2=el&&el.querySelector("#mq");if(q2)q2.value=q;say("Arıyorum…",true);const r=await doSearch(q,true);if(r.length)say(`${r[0].title} çalıyor.`);else{const ok=openExt(yt(q));say(ok?"Uygulama içinde bulamadım, YouTube Music'te açıyorum.":"Uygulama içinde bulamadım. Ekrandaki YouTube Music ya da Spotify düğmesine dokunun.")}return" "}return null}
 reg({id:"muzik",name:"Müzik",icon:"🎵",say:/şarkı|müzik|çal$|çal (?!ma)|dinle|spotify/,render,cmd,leave(){}});
})();
