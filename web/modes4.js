"use strict";
/* Modlar 4: Ortam sesleri, Uyku, Mola, Notlar, Ezber kartları, Sınav takvimi, Planlama.
   NOT: Komut kalıplarında \b KULLANMAYIN (Türkçe harflerle çalışmaz). */

// ---- ortak: sentezlenmiş ortam sesi üretici (yağmur, deniz, rüzgar, orman, şömine, kafe, gece, nehir, fırtına, beyaz gürültü) ----
const Amb=(()=>{let ac=null,cur=null;
 const bufs={};function noise(type){if(bufs[type])return bufs[type];const n=ac.sampleRate*3,b=ac.createBuffer(1,n,ac.sampleRate),d=b.getChannelData(0);let l=0,l2=0;for(let i=0;i<n;i++){const w=Math.random()*2-1;if(type==="white")d[i]=w*.5;else if(type==="pink"){l=.97*l+.03*w;d[i]=l*4}else{l=(l+.02*w)/1.02;d[i]=l*3.5}}return bufs[type]=b}
 const SPEC={rain:{n:"white",f:["bandpass",2200,.5],g:.5},storm:{n:"white",f:["bandpass",1500,.4],g:.7,thunder:1},sea:{n:"brown",f:["lowpass",700,1],g:.9,lfo:.11},wind:{n:"brown",f:["lowpass",450,1],g:.8,lfo:.2},
  forest:{n:"pink",f:["bandpass",3200,.6],g:.18,chirp:1},fire:{n:"brown",f:["lowpass",900,1],g:.6,crackle:1},cafe:{n:"pink",f:["lowpass",1100,.7],g:.35,murmur:1},night:{n:"white",f:["bandpass",4500,3],g:.06,cricket:1},river:{n:"pink",f:["bandpass",1200,.5],g:.45,lfo:.3},white:{n:"white",f:["lowpass",6000,1],g:.35}};
 const NAMES={rain:"Yağmur",storm:"Fırtına",sea:"Deniz",forest:"Orman",fire:"Şömine",cafe:"Kafe",night:"Gece",wind:"Rüzgar",river:"Nehir",white:"Beyaz gürültü"};
 function stop(){if(!cur)return;cur.timers.forEach(clearTimeout);cur.timers.length=0;try{cur.src.stop()}catch(e){}try{cur.lfo&&cur.lfo.stop()}catch(e){}try{cur.master.disconnect()}catch(e){}cur=null}
 function play(kind,vol){stop();try{if(!ac)ac=new (window.AudioContext||window.webkitAudioContext)();ac.state==="suspended"&&ac.resume()}catch(e){return false}const s=SPEC[kind];if(!s)return false;
  const src=ac.createBufferSource();src.buffer=noise(s.n);src.loop=true;const f=ac.createBiquadFilter();f.type=s.f[0];f.frequency.value=s.f[1];f.Q.value=s.f[2];const master=ac.createGain();master.gain.value=vol*s.g;src.connect(f);f.connect(master);master.connect(ac.destination);src.start();
  const o={src,master,kind,base:s.g,timers:[],lfo:null};
  if(s.lfo){const l=ac.createOscillator(),lg=ac.createGain();l.frequency.value=s.lfo;lg.gain.value=kind==="sea"?300:150;l.connect(lg);lg.connect(f.frequency);l.start();o.lfo=l}
  const pop=(fq,len,vv,dur)=>{if(!cur||cur!==o)return;const x=ac.createOscillator(),g=ac.createGain();x.type="sine";x.frequency.value=fq;g.gain.value=0;x.connect(g);g.connect(ac.destination);const t=ac.currentTime;g.gain.linearRampToValueAtTime(vv*master.gain.value*3,t+.02);g.gain.linearRampToValueAtTime(0,t+len);x.start(t);x.stop(t+len+.05)};
  const loop=(fn,min,max)=>{const t=setTimeout(()=>{if(cur===o){fn();loop(fn,min,max)}},min+Math.random()*(max-min));o.timers.push(t)};
  if(s.chirp)loop(()=>{const b=2200+Math.random()*1800;pop(b,.09,.12);setTimeout(()=>pop(b*1.2,.09,.1),110)},1200,4500);
  if(s.crackle)loop(()=>{try{const b=ac.createBufferSource(),buf=ac.createBuffer(1,800,ac.sampleRate),d=buf.getChannelData(0);for(let i=0;i<800;i++)d[i]=(Math.random()*2-1)*(1-i/800);b.buffer=buf;const g=ac.createGain();g.gain.value=master.gain.value*2.5;b.connect(g);g.connect(ac.destination);b.start()}catch(e){}},120,900);
  if(s.cricket)loop(()=>{pop(4300,.05,.06);setTimeout(()=>pop(4300,.05,.06),90);setTimeout(()=>pop(4300,.05,.06),180)},300,1100);
  if(s.thunder)loop(()=>{try{const g=master.gain,v=g.value;g.setTargetAtTime(v*2.4,ac.currentTime,.05);g.setTargetAtTime(v,ac.currentTime+.4,.8)}catch(e){}},9000,20000);
  cur=o;return true}
 return{play,stop,NAMES,KINDS:Object.keys(NAMES),setVol(v){if(cur)cur.master.gain.setTargetAtTime(v*cur.base,ac.currentTime,.1)},playing:()=>cur&&cur.kind,fade(sec){if(!cur)return;try{cur.master.gain.setTargetAtTime(0,ac.currentTime,sec/3)}catch(e){}}}})();

// ================================================================= ORTAM
(function(){let P=DB.get("ortam",{vol:.6,sleep:0}),el=null,sl=null;const save=()=>DB.set("ortam",P);
 function ui(){if(!el||!el.isConnected)return;const pl=Amb.playing();el.querySelectorAll("#ob button").forEach(b=>b.classList.toggle("cur",b.dataset.k===pl));el.querySelector("#os").textContent=pl?Amb.NAMES[pl]+" çalıyor":"Bir ses seçin"}
 function play(k){Amb.play(k,P.vol);ui();setSleep(P.sleep)}
 function setSleep(m){P.sleep=m;save();clearTimeout(sl);if(m>0&&Amb.playing())sl=setTimeout(()=>{Amb.fade(8);setTimeout(()=>{Amb.stop();ui();say("Uyku zamanlayıcısı bitti, ses kapandı.",true)},9000)},m*60000);if(el&&el.isConnected)el.querySelector("#osl").textContent=m?m+" dk sonra kapanır":"kapalı"}
 function render(e){el=e;e.innerHTML=`<div class="card"><div id="os" class="big" style="font-size:22px;text-align:center">Bir ses seçin</div></div><div class="grid" id="ob">${Amb.KINDS.map(k=>`<button class="tile" data-k="${k}">${Amb.NAMES[k]}</button>`).join("")}</div>
  <div class="card"><h3>Ses seviyesi</h3><input type="range" id="ov" min="0" max="100" value="${P.vol*100}" style="width:100%"></div>
  <div class="card"><h3>Kapanma zamanlayıcısı <small class="mut" id="osl" style="letter-spacing:0"></small></h3><div class="row">${[0,15,30,45,60,90].map(m=>`<button data-s="${m}">${m?m+" dk":"Kapalı"}</button>`).join("")}</div></div><div class="row"><button id="ost">⏹ SUSTUR</button></div>`;
  e.querySelectorAll("#ob button").forEach(b=>b.onclick=()=>play(b.dataset.k));e.querySelector("#ov").oninput=ev=>{P.vol=ev.target.value/100;save();Amb.setVol(P.vol)};e.querySelectorAll("[data-s]").forEach(b=>b.onclick=()=>setSleep(+b.dataset.s));e.querySelector("#ost").onclick=()=>{Amb.stop();ui()};setSleep(P.sleep);ui()}
 function cmd(t){const names={rain:/yağmur|yağış/,storm:/fırtına|şimşek/,sea:/deniz|dalga|okyanus/,forest:/orman|kuş|doğa/,fire:/şömine|ateş|kamp/,cafe:/kafe|kahve/,night:/gece|cırcır|böcek/,wind:/rüzgar|rüzgâr/,river:/nehir|dere|şelale/,white:/beyaz|gürültü/};
  if(/sustur|durdur|kapat|sessiz/.test(t)){Amb.stop();ui();return"Ses durdu."}
  const m=t.match(/(\d+)\s*(dakika|dk|saat)/);if(m&&/kapa|uyku|zamanlay|sonra/.test(t)){const x=+m[1]*(m[2]==="saat"?60:1);setSleep(x);return`${x} dakika sonra kapanacak.`}
  if(/ses/.test(t)&&/(artır|yüksel)/.test(t)){P.vol=Math.min(1,P.vol+.15);save();Amb.setVol(P.vol);return"Sesi artırdım."}if(/ses/.test(t)&&/(azalt|kıs|düşür)/.test(t)){P.vol=Math.max(0,P.vol-.15);save();Amb.setVol(P.vol);return"Sesi kıstım."}
  for(const k in names)if(names[k].test(t)){play(k);return Amb.NAMES[k]+" açıldı."}return null}
 reg({id:"ortam",name:"Ortam sesleri",icon:"🌧",say:/ortam|yağmur sesi|deniz sesi|orman sesi|şömine|beyaz gürültü|nehir sesi/,render,cmd});window.__ortamStop=()=>Amb.stop()})();

// ================================================================= UYKU
(function(){let S=DB.get("uyku",{end:0,left:0,len:0,paused:false,on:false,def:30,snd:"rain",vol:.5}),el=null,iv=null,fired=false;const save=()=>DB.set("uyku",S);
 const left=()=>S.on?(S.paused?S.left:Math.max(0,(S.end-Date.now())/1000)):0,mm=s=>{s=Math.ceil(s);const h=Math.floor(s/3600);return(h?h+":":"")+String(Math.floor(s%3600/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0")};
 function start(min){S.on=true;S.paused=false;S.len=min*60;S.end=Date.now()+min*60000;fired=false;save();if(S.snd!=="none")Amb.play(S.snd,S.vol);paint()}
 function stop(){S.on=false;save();Amb.stop();paint()}
 function paint(){if(!el||!el.isConnected)return;const l=left(),C=2*Math.PI*90;el.querySelector("#ut").textContent=S.on?mm(l):mm(S.def*60);el.querySelector("#ua").setAttribute("stroke-dashoffset",C*(1-(S.on&&S.len?Math.min(1,l/S.len):1)));
  el.querySelector("#ug").textContent=!S.on?"BAŞLAT":S.paused?"DEVAM":"DURAKLAT";document.body.style.opacity=S.on&&!S.paused&&l<S.len-20?.55:1;
  if(S.on&&!S.paused){if(l<60)Amb.setVol(S.vol*Math.max(0,l/60));if(l<=0&&!fired){fired=true;Amb.stop();S.on=false;save();say("İyi geceler.",true);paint()}}}
 function render(e){el=e;const C=2*Math.PI*90;e.innerHTML=`<div style="position:relative;width:min(70vw,300px);margin:10px auto"><svg viewBox="0 0 200 200" style="width:100%"><circle cx="100" cy="100" r="90" fill="none" stroke="rgba(255,255,255,.07)" stroke-width="8"/><circle id="ua" cx="100" cy="100" r="90" fill="none" stroke="#9fb4ff" stroke-width="8" stroke-linecap="round" stroke-dasharray="${C}" stroke-dashoffset="0" transform="rotate(-90 100 100)"/></svg><div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center"><div id="ut" class="big" style="font-weight:300;font-size:46px">00:00</div></div></div>
  <div class="row" style="justify-content:center"><button class="prim" id="ug">BAŞLAT</button><button id="up5">+5 DK</button><button id="ue">İPTAL</button></div>
  <div class="card"><h3>Süre</h3><div class="row">${[10,15,20,30,45,60,90].map(m=>`<button data-m="${m}">${m} dk</button>`).join("")}</div></div>
  <div class="card"><h3>Uyku sesi</h3><div class="row" id="usn">${["rain","sea","wind","white","none"].map(k=>`<button data-k="${k}" class="${k===S.snd?"cur":""}">${k==="none"?"Sessiz":Amb.NAMES[k]}</button>`).join("")}</div><input type="range" id="uv" min="0" max="100" value="${S.vol*100}" style="width:100%;margin-top:10px"></div>
  <div class="mut" style="font-size:13px;text-align:center">Son dakikada ses yavaşça kısılır. Ekran kararır; telefonu şarja takmanız önerilir.</div>`;
  const q=s=>e.querySelector(s);e.querySelectorAll("[data-m]").forEach(b=>b.onclick=()=>{S.def=+b.dataset.m;save();start(S.def)});q("#ug").onclick=()=>{if(!S.on)start(S.def);else if(S.paused){S.paused=false;S.end=Date.now()+S.left*1000;if(S.snd!=="none")Amb.play(S.snd,S.vol)}else{S.paused=true;S.left=left();Amb.stop()}save();paint()};
  q("#up5").onclick=()=>{if(!S.on)return;S.paused?S.left+=300:S.end+=300000;S.len+=300;save();paint()};q("#ue").onclick=stop;
  e.querySelectorAll("#usn button").forEach(b=>b.onclick=()=>{S.snd=b.dataset.k;save();e.querySelectorAll("#usn button").forEach(x=>x.classList.toggle("cur",x===b));if(S.on&&!S.paused){S.snd==="none"?Amb.stop():Amb.play(S.snd,S.vol)}});q("#uv").oninput=ev=>{S.vol=ev.target.value/100;save();Amb.setVol(S.vol)};clearInterval(iv);iv=setInterval(paint,500);paint()}
 function cmd(t){const m=t.match(/(\d+|yarım)\s*(dakika|dk|saat)/);
  if(/sesi/.test(t)||/(yağmur|deniz|rüzgar|beyaz|sessiz)/.test(t)){const k=/yağmur/.test(t)?"rain":/deniz/.test(t)?"sea":/rüzgar/.test(t)?"wind":/beyaz/.test(t)?"white":/sessiz/.test(t)?"none":null;if(k){S.snd=k;save();if(S.on)k==="none"?Amb.stop():Amb.play(k,S.vol);render(el);return"Uyku sesi "+(k==="none"?"kapalı":Amb.NAMES[k])+"."}}
  if(/(ekle|uzat)/.test(t)&&m&&S.on){const x=(m[1]==="yarım"?30:+m[1])*(m[2]==="saat"?60:1);S.end+=x*60000;S.len+=x*60;save();return x+" dakika eklendi."}
  if(/(duraklat|beklet)/.test(t)){if(S.on&&!S.paused){S.paused=true;S.left=left();Amb.stop();save();return"Duraklatıldı."}}if(/(devam|sürdür)/.test(t)&&S.paused){S.paused=false;S.end=Date.now()+S.left*1000;if(S.snd!=="none")Amb.play(S.snd,S.vol);save();return"Devam ediyor."}
  if(/(bitir|iptal|vazgeç)/.test(t)){stop();return"İptal edildi."}if(/(kalan|ne kadar)/.test(t))return S.on?Math.floor(left()/60)+" dakika kaldı.":"Sayaç çalışmıyor.";
  if(m||/(başlat|uyu|yat)/.test(t)){const x=m?(m[1]==="yarım"?30:+m[1])*(m[2]==="saat"?60:1):S.def;S.def=x;start(x);return`${x} dakika sonra uyku modu kapanacak. İyi geceler.`}return null}
 reg({id:"uyku",name:"Uyku",icon:"🌙",say:/uyku|uyuyacağım|yatıyorum/,render,cmd,leave(){clearInterval(iv);document.body.style.opacity=1}})})();

// ================================================================= MOLA
(function(){let S=DB.get("mola",{end:0,len:0,on:false,def:10}),el=null,iv=null,fired=true;const save=()=>DB.set("mola",S);
 const TIPS=["Bir bardak su için 💧","Ayağa kalkıp esneyin","20 sn uzağa bakın (göz molası)","Omuzlarınızı gevşetin, 5 derin nefes alın","Pencereyi açıp biraz hava alın","Kısa bir yürüyüş yapın","Gözlerinizi kapatıp 1 dakika dinlenin"];
 const left=()=>S.on?Math.max(0,(S.end-Date.now())/1000):0;
 function start(m){S.on=true;S.len=m*60;S.end=Date.now()+m*60000;S.def=m;fired=false;save();paint()}function stop(){S.on=false;save();paint()}
 function paint(){if(!el||!el.isConnected)return;const l=Math.ceil(left()),C=2*Math.PI*88;el.querySelector("#mt").textContent=S.on?Math.floor(l/60)+":"+String(l%60).padStart(2,"0"):S.def+":00";el.querySelector("#ma").setAttribute("stroke-dashoffset",C*(1-(S.on&&S.len?Math.min(1,l/S.len):1)));
  if(S.on&&!fired&&Date.now()>=S.end){fired=true;S.on=false;save();beep(880,200,.2);setTimeout(()=>beep(1175,300,.2),300);buzz([200,100,200]);say("Mola bitti, çalışmaya dönebilirsiniz.");paint()}}
 function render(e){el=e;const C=2*Math.PI*88;e.innerHTML=`<div style="position:relative;width:min(64vw,260px);margin:10px auto"><svg viewBox="0 0 200 200" style="width:100%"><circle cx="100" cy="100" r="88" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="8"/><circle id="ma" cx="100" cy="100" r="88" fill="none" stroke="#5ee08a" stroke-width="8" stroke-linecap="round" stroke-dasharray="${C}" stroke-dashoffset="0" transform="rotate(-90 100 100)"/></svg><div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center"><div id="mt" class="big" style="font-weight:300">10:00</div></div></div>
  <div class="row" style="justify-content:center"><button class="prim" id="mg">MOLAYI BAŞLAT</button><button id="me">BİTİR</button></div><div class="card"><h3>Süre</h3><div class="row">${[3,5,10,15,20,30].map(m=>`<button data-m="${m}">${m} dk</button>`).join("")}</div></div>
  <div class="card"><h3>Mola önerisi</h3><div id="mtip" style="font-size:17px">${TIPS[rnd(TIPS.length)]}</div><button id="mn" style="margin-top:10px">BAŞKA ÖNERİ</button></div>`;
  e.querySelectorAll("[data-m]").forEach(b=>b.onclick=()=>start(+b.dataset.m));e.querySelector("#mg").onclick=()=>start(S.def);e.querySelector("#me").onclick=stop;e.querySelector("#mn").onclick=()=>{e.querySelector("#mtip").textContent=TIPS[rnd(TIPS.length)]};clearInterval(iv);iv=setInterval(paint,500);paint()}
 function cmd(t){const m=t.match(/(\d+)\s*(dakika|dk)/);if(/(bitir|iptal)/.test(t)){stop();return"Mola bitti."}if(m||/(ver|başlat|mola)/.test(t)){const x=m?+m[1]:S.def;start(Math.min(180,x));return`${x} dakika mola başladı.`}return null}
 reg({id:"mola",name:"Mola",icon:"☕",say:/mola/,render,cmd,leave(){clearInterval(iv)}})})();

// ================================================================= NOTLAR
(function(){let D=DB.get("notlar",{n:[],next:1}),el=null,open=null;const save=()=>DB.set("notlar",D);
 function list(){if(!el||!el.isConnected)return;const q=el.querySelector("#nq").value.trim().toLowerCase();const items=D.n.filter(x=>!q||(x.t+" "+x.b).toLowerCase().includes(q)).sort((a,b)=>(b.pin?1:0)-(a.pin?1:0)||b.ts-a.ts);
  el.querySelector("#nl").innerHTML=items.map(x=>`<div class="it" data-id="${x.id}" style="cursor:pointer"><span style="flex:1;min-width:0"><b>${x.pin?"★ ":""}${esc(x.t||"Başlıksız")}</b><div class="mut" style="font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(x.b.slice(0,90))}</div></span><span class="mut" style="font-size:12px">${new Date(x.ts).toLocaleDateString("tr-TR")}</span></div>`).join("")||'<span class="mut">Not yok.</span>';
  el.querySelectorAll("#nl .it").forEach(r=>r.onclick=()=>edit(+r.dataset.id))}
 function edit(id){open=D.n.find(x=>x.id===id);if(!open)return;el.querySelector("#ne").style.display="block";el.querySelector("#nt").value=open.t;el.querySelector("#nb").value=open.b;el.querySelector("#np").textContent=open.pin?"★ SABİT":"☆ SABİTLE";el.querySelector("#nt").focus()}
 function add(t,b){const x={id:D.next++,t:t||"",b:b||"",ts:Date.now(),pin:false};D.n.push(x);save();list();return x}
 function render(e){el=e;e.innerHTML=`<div class="row" style="margin:6px 0"><input id="nq" placeholder="Notlarda ara…" style="flex:1"><button class="prim" id="nn">+ YENİ</button></div><div class="card" id="ne" style="display:none"><input id="nt" placeholder="Başlık" style="width:100%;margin-bottom:8px"><textarea id="nb" rows="8" placeholder="Notunuz…" style="width:100%"></textarea>
  <div class="row" style="margin-top:8px"><button class="prim" id="ns">KAYDET</button><button id="np">☆ SABİTLE</button><button id="nd" style="color:var(--bad)">SİL</button><button id="nc">KAPAT</button></div></div><div class="card" id="nl"></div>`;
  const q=s=>e.querySelector(s);q("#nq").oninput=list;q("#nn").onclick=()=>{const x=add("","");edit(x.id)};q("#ns").onclick=()=>{if(open){open.t=q("#nt").value.trim();open.b=q("#nb").value;open.ts=Date.now();save();list();q("#ne").style.display="none";open=null}};
  q("#np").onclick=()=>{if(open){open.pin=!open.pin;save();q("#np").textContent=open.pin?"★ SABİT":"☆ SABİTLE";list()}};q("#nd").onclick=()=>{if(open&&confirm("Not silinsin mi?")){D.n=D.n.filter(x=>x!==open);save();open=null;q("#ne").style.display="none";list()}};q("#nc").onclick=()=>{q("#ne").style.display="none";open=null;list()};list()}
 function cmd(t,raw){const b=raw.includes(":")?raw.split(":").slice(1).join(":").trim():"";
  if(/(not|notu)\s*(ekle|yaz|al)|yeni not/.test(t)&&b){const x=add(b.split(/[.!?\n]/)[0].slice(0,40),b);return"Not kaydedildi."}
  if(/(notları|notlarımı)\s*(oku|söyle|listele)/.test(t)){const l=D.n.slice(-5).map(x=>x.t||x.b.slice(0,30));return l.length?"Son notlarınız: "+l.join(", ")+".":"Not yok."}
  if(/son notu sil/.test(t)){D.n.pop();save();list();return"Son notu sildim."}return null}
 reg({id:"notlar",name:"Notlar",icon:"🗒",say:/not defter|notlar|\bnot\b/,render,cmd})})();

// ================================================================= EZBER KARTLARI
(function(){let D=DB.get("kartlar",{decks:{"Genel":[]},cur:"Genel"}),el=null,Q={ids:[],i:0,show:false};const save=()=>DB.set("kartlar",D),BOX=[0,1,2,4,8,16],today=()=>new Date().toISOString().slice(0,10);
 const cards=()=>D.decks[D.cur]||[];
 function session(){const c=cards(),due=[];c.forEach((x,i)=>{if(!x.seen||(x.due||"")<=today())due.push(i)});Q={ids:due.sort(()=>Math.random()-.5),i:0,show:false};ui()}
 const cc=()=>Q.i<Q.ids.length?cards()[Q.ids[Q.i]]:null;
 function ui(){if(!el||!el.isConnected)return;const c=cc(),q=s=>el.querySelector(s);q("#kd").innerHTML=Object.keys(D.decks).map(k=>`<button data-k="${esc(k)}" class="${k===D.cur?"cur":""}">${esc(k)} (${D.decks[k].length})</button>`).join("");q("#kd").querySelectorAll("button").forEach(b=>b.onclick=()=>{D.cur=b.dataset.k;save();Q={ids:[],i:0,show:false};ui()});
  q("#kf").textContent=c?c.f:Q.ids.length?"Tebrikler!":"Başlamak için ‘ÇALIŞ’";q("#kb2").textContent=c&&Q.show?c.b:"";q("#kp2").textContent=Q.ids.length?`${Math.min(Q.i+1,Q.ids.length)}/${Q.ids.length}`:`${cards().length} kart`;
  q("#kl").innerHTML=cards().map((x,i)=>`<div class="it"><span>${esc(x.f)} <span class="mut">→ ${esc(x.b)}</span></span><a data-i="${i}">×</a></div>`).join("")||'<span class="mut">Kart yok.</span>';q("#kl").querySelectorAll("a").forEach(a=>a.onclick=()=>{cards().splice(+a.dataset.i,1);save();ui()})}
 function judge(v){const c=cc();if(!c)return"Önce çalışmayı başlatın.";c.seen=(c.seen||0)+1;if(v==="yes")c.box=Math.min(5,(c.box||0)+1);else if(v==="no")c.box=1;c.due=new Date(Date.now()+(v==="no"?0:BOX[c.box||1])*864e5).toISOString().slice(0,10);Q.i++;Q.show=false;save();ui();return v==="yes"?"Harika.":"Tekrar edeceğiz."}
 function render(e){el=e;e.innerHTML=`<div class="row" id="kd" style="margin:6px 0"></div><div class="mut" id="kp2" style="text-align:center;letter-spacing:.2em;font-size:13px"></div><div class="card" style="text-align:center;min-height:200px;display:flex;flex-direction:column;justify-content:center;gap:12px"><div id="kf" class="big" style="font-size:34px">—</div><div id="kb2" style="font-size:22px;color:var(--c);min-height:30px"></div></div>
  <div class="row" style="justify-content:center"><button class="prim" id="kg">ÇALIŞ</button><button id="ksh">ÇEVİR</button><button id="kye" style="color:var(--ok)">BİLDİM</button><button id="kno" style="color:var(--bad)">BİLMEDİM</button></div>
  <div class="card"><h3>Kart ekle</h3><div class="row"><input id="a" placeholder="Ön yüz" style="flex:1;min-width:100px"><input id="b" placeholder="Arka yüz" style="flex:1;min-width:100px"><button id="ka">EKLE</button></div></div>
  <div class="card"><h3>Yeni deste</h3><div class="row"><input id="dn" placeholder="Deste adı" style="flex:1"><button id="dc">OLUŞTUR</button></div></div><div class="card"><h3>Kartlar</h3><div id="kl"></div></div>`;
  const q=s=>e.querySelector(s);q("#kg").onclick=session;q("#ksh").onclick=()=>{if(cc()){Q.show=true;ui()}};q("#kye").onclick=()=>say(judge("yes"),true);q("#kno").onclick=()=>say(judge("no"),true);
  q("#ka").onclick=()=>{const a=q("#a").value.trim(),b=q("#b").value.trim();if(a&&b){cards().push({f:a,b,box:0,seen:0,due:""});save();q("#a").value=q("#b").value="";ui()}};q("#dc").onclick=()=>{const n=q("#dn").value.trim();if(n&&!D.decks[n]){D.decks[n]=[];D.cur=n;save();q("#dn").value="";ui()}};ui()}
 function cmd(t,raw){const b=raw.includes(":")?raw.split(":").slice(1).join(":"):"";
  if(/kart ekle/.test(t)&&b){const m=b.match(/(.+?)\s*(?:=|eşittir)\s*(.+)/);if(!m)return"Kart ekle: ön = arka biçiminde söyleyin.";cards().push({f:m[1].trim(),b:m[2].trim(),box:0,seen:0,due:""});save();ui();return"Kart eklendi."}
  if(/(çalış|başla|başlat)/.test(t)){session();return`${Q.ids.length} kart hazır.`}if(/(çevir|göster)/.test(t)){if(cc()){Q.show=true;ui();return cc().b}return"Önce çalışmayı başlatın."}
  if(/bilmedim|yanlış/.test(t))return judge("no");if(/bildim|doğru|kolay/.test(t))return judge("yes");if(/yeni deste/.test(t)&&b){D.decks[b.trim()]=D.decks[b.trim()]||[];D.cur=b.trim();save();ui();return"Deste oluşturuldu."}return null}
 reg({id:"kartlar",name:"Ezber kartları",icon:"🃏",say:/kart|ezber kart|deste/,render,cmd})})();

// ================================================================= SINAV TAKVİMİ
(function(){let D=DB.get("sinav",{e:[]}),el=null;const save=()=>DB.set("sinav",D);const AY=["ocak","şubat","mart","nisan","mayıs","haziran","temmuz","ağustos","eylül","ekim","kasım","aralık"];
 const ymd=d=>d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");
 const days=e=>Math.round((new Date(e.d+"T00:00")-new Date(ymd(new Date())+"T00:00"))/864e5);
 const target=n=>n>14?30:n>7?45:n>2?90:120;
 function parseDate(t){const now=new Date();let m=t.match(/(\d{1,2})\s*(ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)/);if(m){const y=now.getFullYear();let d=new Date(y,AY.indexOf(m[2]),+m[1]);if(d<new Date(now.getFullYear(),now.getMonth(),now.getDate()))d=new Date(y+1,AY.indexOf(m[2]),+m[1]);return ymd(d)}
  m=t.match(/(\d+)\s*gün sonra/);if(m)return ymd(new Date(Date.now()+m[1]*864e5));if(/yarın/.test(t))return ymd(new Date(Date.now()+864e5));if(/bugün/.test(t))return ymd(now);return null}
 function ui(){if(!el||!el.isConnected)return;const l=D.e.map(e=>({...e,n:days(e)})).filter(e=>e.n>=0).sort((a,b)=>a.n-b.n);el.querySelector("#sl").innerHTML=l.map(e=>`<div class="it"><span><b>${esc(e.ders)}</b>${e.konu?` <span class="mut">· ${esc(e.konu)}</span>`:""}<div class="mut" style="font-size:13px">${new Date(e.d+"T12:00").toLocaleDateString("tr-TR",{day:"numeric",month:"long"})}</div></span><span style="text-align:right"><b style="font-size:22px;color:${e.n<=3?"var(--bad)":e.n<=7?"var(--warn)":"var(--ok)"}">${e.n===0?"BUGÜN":e.n===1?"YARIN":e.n+" gün"}</b> <a data-id="${e.id}">×</a></span></div>`).join("")||'<span class="mut">Kayıtlı sınav yok.</span>';
  el.querySelectorAll("#sl a").forEach(a=>a.onclick=()=>{D.e=D.e.filter(x=>x.id!==+a.dataset.id);save();ui()});const n=l[0];el.querySelector("#sa").textContent=n?`${n.ders} sınavına ${n.n===0?"bugün":n.n+" gün"} var. Bugünkü odak hedefi: ${target(n.n)} dakika.`:"Sınav ekleyin, günlük odak hedefini hesaplayayım."}
 function add(ders,d,konu){D.e.push({id:Date.now(),ders:ders.slice(0,30),d,konu:(konu||"").slice(0,40)});save();ui()}
 function render(e){el=e;e.innerHTML=`<div class="card"><h3>Bugünün hedefi</h3><div id="sa" style="font-size:17px;line-height:1.5"></div></div><div class="card"><h3>Sınav ekle</h3><div class="row"><input id="sd" placeholder="Ders" style="flex:1;min-width:100px"><input id="st" type="date" style="width:150px"></div><div class="row" style="margin-top:8px"><input id="sk" placeholder="Konu (isteğe bağlı)" style="flex:1"><button class="prim" id="sb">EKLE</button></div></div><div class="card"><h3>Sınavlar</h3><div id="sl"></div></div>`;
  e.querySelector("#sb").onclick=()=>{const d=e.querySelector("#sd").value.trim(),t=e.querySelector("#st").value;if(d&&t){add(d,t,e.querySelector("#sk").value.trim());e.querySelector("#sd").value=e.querySelector("#sk").value=""}};ui()}
 function cmd(t,raw){
  if(/sınavlarım|sıradaki sınav|sınav ne zaman/.test(t)){const l=D.e.map(e=>({...e,n:days(e)})).filter(e=>e.n>=0).sort((a,b)=>a.n-b.n);return l.length?`Sıradaki: ${l[0].ders}, ${l[0].n===0?"bugün":l[0].n===1?"yarın":l[0].n+" gün sonra"}.`:"Kayıtlı sınav yok."}
  if(/ne çalış/.test(t)){const l=D.e.map(e=>days(e)).filter(n=>n>=0).sort((a,b)=>a-b);return l.length?`Bugün ${target(l[0])} dakika odaklanın.`:"Kayıtlı sınav yok."}
  const m=t.match(/(.+?)\s+sınav/);const d=parseDate(t);if(m&&d&&!/sil/.test(t)){const ders=m[1].replace(/(bir|şu|bu)\s/g,"").trim();const k=raw.match(/konu\s+(.+)$/i);add(ders.charAt(0).toUpperCase()+ders.slice(1),d,k?k[1]:"");return`${ders} sınavı eklendi.`}
  if(/sil/.test(t)&&m){const w=m[1].replace(/sil\w*/,"").trim();const n0=D.e.length;D.e=D.e.filter(e=>!norm(e.ders).includes(w));save();ui();return D.e.length<n0?"Sınavı sildim.":"Bulamadım."}return null}
 reg({id:"sinav",name:"Sınav takvimi",icon:"📅",say:/sınavlarım|sınav takvim|sınav ekle|(\S+) sınavı/,render,cmd})})();

// ================================================================= PLANLAMA (görev + ödül)
(function(){let D=DB.get("plan",{t:[],r:[],next:1}),el=null;const save=()=>DB.set("plan",D);
 function ui(){if(!el||!el.isConnected)return;const rw=D.r.map(r=>{const ts=D.t.filter(t=>t.r===r.id),done=ts.filter(t=>t.d).length,all=ts.length&&done===ts.length;return{...r,ts,done,all}});
  el.querySelector("#pr").innerHTML=rw.map(r=>`<div class="it"><span>${r.all?"🏆":"🎁"} <b>${esc(r.n)}</b><div class="mut" style="font-size:13px">${r.ts.length?r.done+"/"+r.ts.length+" görev":"görev bağlanmadı"}</div></span><span style="color:${r.all?"var(--ok)":"var(--mut)"}">${r.all?"KAZANDIN!":""} <a data-r="${r.id}">×</a></span></div>`).join("")||'<span class="mut">Ödül yok.</span>';
  el.querySelector("#pt").innerHTML=D.t.map(t=>`<div class="it"><label style="flex:1;display:flex;gap:10px;align-items:center;${t.d?"opacity:.5;text-decoration:line-through":""}"><input type="checkbox" data-t="${t.id}" ${t.d?"checked":""} style="width:22px;height:22px">${esc(t.n)}</label><select data-s="${t.id}" style="max-width:120px"><option value="0">ödül yok</option>${D.r.map(r=>`<option value="${r.id}" ${t.r===r.id?"selected":""}>${esc(r.n)}</option>`).join("")}</select><a data-x="${t.id}">×</a></div>`).join("")||'<span class="mut">Görev yok.</span>';
  el.querySelectorAll("#pt input").forEach(c=>c.onchange=()=>{const t=D.t.find(x=>x.id===+c.dataset.t);t.d=c.checked;save();ui();const r=D.r.find(x=>x.id===t.r);if(r&&c.checked){const ts=D.t.filter(x=>x.r===r.id);if(ts.every(x=>x.d)){beep(1000,150);setTimeout(()=>beep(1300,250),180);say(`Tebrikler! ${r.n} ödülünü kazandın.`)}}});
  el.querySelectorAll("#pt select").forEach(s=>s.onchange=()=>{D.t.find(x=>x.id===+s.dataset.s).r=+s.value;save();ui()});el.querySelectorAll("#pt [data-x]").forEach(a=>a.onclick=()=>{D.t=D.t.filter(x=>x.id!==+a.dataset.x);save();ui()});el.querySelectorAll("#pr [data-r]").forEach(a=>a.onclick=()=>{D.r=D.r.filter(x=>x.id!==+a.dataset.r);D.t.forEach(t=>{if(t.r===+a.dataset.r)t.r=0});save();ui()})}
 const addT=n=>{D.t.push({id:D.next++,n:n.slice(0,60),d:false,r:0});save();ui()},addR=n=>{D.r.push({id:D.next++,n:n.slice(0,40)});save();ui()};
 function render(e){el=e;e.innerHTML=`<div class="card"><h3>Görevler</h3><div id="pt"></div><div class="row" style="margin-top:8px"><input id="a" placeholder="Yeni görev" style="flex:1"><button class="prim" id="b">EKLE</button></div></div><div class="card"><h3>Ödüller <small class="mut" style="letter-spacing:0">bağlı tüm görevler bitince kazanılır</small></h3><div id="pr"></div><div class="row" style="margin-top:8px"><input id="c" placeholder="Yeni ödül (örn. film izle)" style="flex:1"><button id="d">EKLE</button></div></div>`;
  const q=s=>e.querySelector(s);q("#b").onclick=()=>{const v=q("#a").value.trim();if(v){addT(v);q("#a").value=""}};q("#d").onclick=()=>{const v=q("#c").value.trim();if(v){addR(v);q("#c").value=""}};ui()}
 function cmd(t,raw){const b=raw.includes(":")?raw.split(":").slice(1).join(":").trim():"";
  if(/görev ekle/.test(t)&&b){addT(b);return"Görev eklendi."}if(/ödül ekle/.test(t)&&b){addR(b);return"Ödül eklendi."}
  const m=raw.match(/(.+?)\s*(?:görevini|ödevini|işini)?\s*(bitir|tamamla|yaptım)/i);if(m){const w=norm(m[1]);const x=D.t.find(x=>!x.d&&norm(x.n).includes(w));if(x){x.d=true;save();ui();return`${x.n} tamamlandı.`}}
  if(/(görevlerim|neler kaldı)/.test(t)){const l=D.t.filter(x=>!x.d).map(x=>x.n);return l.length?"Kalan: "+l.join(", ")+".":"Tüm görevler tamam."}return null}
 reg({id:"plan",name:"Planlama",icon:"🧩",say:/planlama|görev ekle|ödül ekle|görevlerim/,render,cmd})})();
