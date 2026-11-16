"use strict";
/* Ortak mod kabuğu: üst çubuk, komut kutusu, WebSocket. Kullanım: Mode.start({kind, title, placeholder, init(data), act(do), tick()}) */
const $=id=>document.getElementById(id);
const Mode=(()=>{
 const TOK=new URLSearchParams(location.search).get("t");let ws,cfg,lt;
 const REMOTE=!!document.querySelector('meta[name="jv-remote"]');          // uzaktan (internet) telefon sayfası: remote.py sunar, oturum anahtarı dakikada bir yenilenir
 const ls=(k,v)=>{try{if(v===undefined)return localStorage.getItem(k)||"";localStorage.setItem(k,v)}catch(e){return ""}};
 async function renew(){try{const r=await fetch("/session",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({d:ls("jv_rdev")})});const d=await r.json();
   if(d.ok){ls("jv_s",d.s);return true}}catch(e){}return false}
 const send=o=>{if(ws&&ws.readyState===1)ws.send(JSON.stringify(REMOTE?{...o,s:ls("jv_s")}:o))};
 const cmd=t=>{send({type:"text",text:t});$("log").textContent="› komut uygulanıyor…"};
 const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
 function shell(c){
  document.body.insertAdjacentHTML("afterbegin",'<canvas id="bg"></canvas><div id="top"><span id="logo"></span><span id="title">'+esc(c.title)+'</span><span id="pill">HAZIR</span><span id="sp"></span><span id="clock"></span><button id="peek" title="Masaüstüne geç (Ctrl+Alt+M)">MASAÜSTÜ</button><button id="close">KAPAT · ESC</button></div>');
  document.body.insertAdjacentHTML("beforeend",'<div id="bar"><div id="cmdw"><span>›</span><input id="cmd" placeholder="'+esc(c.placeholder||"")+'" spellcheck="false" autocomplete="off"></div><div id="log">Jarvis: '+esc(c.title.toLowerCase())+' hazır.</div></div>');
 }
 function particles(){const c=$("bg"),x=c.getContext("2d");let W,H;const P=[];const rs=()=>{W=c.width=innerWidth;H=c.height=innerHeight};rs();addEventListener("resize",rs);
  for(let i=0;i<55;i++)P.push({x:Math.random(),y:Math.random(),r:Math.random()*1.5+.4,v:Math.random()*.0002+.00006,a:Math.random()*.5+.15});
  (function f(){x.clearRect(0,0,W,H);x.fillStyle=getComputedStyle(document.documentElement).getPropertyValue("--c")||"#3fe8ff";
   for(const p of P){p.y-=p.v;if(p.y<-.02){p.y=1.02;p.x=Math.random()}x.globalAlpha=p.a*(.5+.5*Math.sin(performance.now()/1500+p.x*20));x.beginPath();x.arc(p.x*W,p.y*H,p.r,0,6.283);x.fill()}
   x.globalAlpha=1;requestAnimationFrame(f)})()}
 function connect(){ws=new WebSocket(REMOTE?(location.protocol==="https:"?"wss://":"ws://")+location.host+"/ws?k="+cfg.kind:"ws://127.0.0.1:8765/ws?t="+TOK);ws.onopen=()=>send({type:"scene_ready",kind:cfg.kind});
  ws.onmessage=ev=>{let m;try{m=JSON.parse(ev.data)}catch(e){return}
   if(m.type==="auth"&&!m.ok){renew().then(ok=>{if(!ok)location.href="/"});return}
   if(m.kind!==cfg.kind)return;
   if(m.type==="scene_init"&&m.data)cfg.init(m.data);
   else if(m.type==="scene_do"){const d=m.do||{};if(d.msg){$("log").textContent="Jarvis: "+d.msg;clearTimeout(lt);lt=setTimeout(()=>{$("log").textContent=""},6000)}cfg.act(d)}};
  ws.onclose=()=>setTimeout(connect,1500)}
 function start(c){cfg=c;shell(c);particles();
  const shut=()=>{if(REMOTE)location.href="/";else send({type:"scene_close"})};
  $("close").onclick=shut;$("peek").onclick=()=>send({type:"mode_peek"});
  if(REMOTE){$("peek").style.display="none";$("close").textContent="MENÜ";setInterval(renew,45000)}
  $("cmd").addEventListener("keydown",e=>{e.stopPropagation();if(e.key==="Enter"&&e.target.value.trim()){cmd(e.target.value.trim());e.target.value=""}else if(e.key==="Escape")shut()});
  addEventListener("keydown",e=>{if(e.key==="Escape"){const a=document.activeElement;if(a&&a.tagName==="INPUT"){a.blur();return}shut()}});
  setInterval(()=>{$("clock").textContent=new Date().toLocaleTimeString("tr-TR");if(c.tick)c.tick()},500);
  if(REMOTE)renew().then(ok=>{if(ok)connect();else location.href="/"});else connect();window.focus()}
 return{start,send,cmd,esc,shut:()=>{if(REMOTE)location.href="/";else send({type:"scene_close"})},pill:t=>{$("pill").textContent=t},tok:TOK};
})();
