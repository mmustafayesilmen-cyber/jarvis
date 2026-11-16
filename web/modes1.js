"use strict";
/* Modlar 1: Zamanlayıcı (süre ekle/çıkar, duraklat, pomodoro, ayarlar), Karar çarkı, Bütçe, Listeler */

// ================================================================= ZAMANLAYICI
(function(){
 const COLS=["#3fe8ff","#7dff9a","#ffb454","#c58bff","#ff6b8a","#ffffff"];
 let st=DB.get("zaman",{end:0,paused:0,dur:0,label:"",pomo:null,fired:true}),P=Object.assign({col:"#3fe8ff",tick:true,wake:true,pw:25,pb:5},DB.get("zaman_p",{})),el=null,iv=null,wl=null,lastTick=-1;
 const save=()=>DB.set("zaman",st),saveP=()=>DB.set("zaman_p",P);
 const running=()=>st.end>0&&!st.paused&&!st.fired,active=()=>st.end>0&&!st.fired||st.paused>0;
 const left=()=>st.paused?st.paused:Math.max(0,(st.end-Date.now())/1000);
 const fmt=s=>{s=Math.ceil(s);const h=Math.floor(s/3600),m=Math.floor(s%3600/60);return(h?h+":":"")+String(m).padStart(2,"0")+":"+String(s%60).padStart(2,"0")};
 async function wake(){try{if(P.wake&&running()&&"wakeLock"in navigator&&!wl){wl=await navigator.wakeLock.request("screen");wl.addEventListener("release",()=>{wl=null})}else if(!running()&&wl){wl.release();wl=null}}catch(e){}}
 function start(sec,label,keepPomo){sec=Math.max(5,Math.min(86400,sec));st={end:Date.now()+sec*1000,paused:0,dur:sec,label:label||"",pomo:keepPomo?st.pomo:null,fired:false};save();wake();paint()}
 function adj(sec){if(!active())return;if(st.paused)st.paused=Math.max(5,st.paused+sec);else st.end=Math.max(Date.now()+5000,st.end+sec*1000);st.dur=Math.max(st.dur,left());st.fired=false;save();paint()}
 function pause(){if(running()){st.paused=left();st.end=0;save();wake();paint()}}
 function resume(){if(st.paused){st.end=Date.now()+st.paused*1000;st.paused=0;st.fired=false;save();wake();paint()}}
 function stop(){st={end:0,paused:0,dur:0,label:"",pomo:null,fired:true};save();wake();paint()}
 function alarm(){beep(880,220,.2);setTimeout(()=>beep(880,220,.2),350);setTimeout(()=>beep(1175,400,.2),700);buzz([300,150,300,150,500]);
  if(st.pomo&&st.pomo.on){const p=st.pomo,toBreak=p.phase==="work";if(toBreak){const LG=DB.get("pomo_log",{d:{}}),kk=new Date().toISOString().slice(0,10);LG.d[kk]=(LG.d[kk]||0)+P.pw;DB.set("pomo_log",LG)}p.phase=toBreak?"break":"work";if(!toBreak)p.round++;const m=toBreak?P.pb:P.pw;
   say(toBreak?`Çalışma bitti. ${P.pb} dakika mola.`:`Mola bitti. ${p.round}. tur, ${P.pw} dakika çalışma.`);start(m*60,toBreak?"Mola":"Çalışma",true)}
  else say(`Süre doldu${st.label?": "+st.label:""}.`)}
 setInterval(()=>{if(running()&&Date.now()>=st.end){st.fired=true;save();wake();alarm();paint()}},400);
 document.addEventListener("visibilitychange",()=>{if(!document.hidden)wake()});
 function paint(){if(!el||!el.isConnected)return;const l=left(),a=active(),frac=a&&st.dur?Math.min(1,l/st.dur):0,R=88,C=2*Math.PI*R;
  el.querySelector("#zt").textContent=a||st.fired&&st.end?fmt(a?l:0):"00:00";el.querySelector("#za").setAttribute("stroke-dashoffset",C*(1-frac));
  el.querySelector("#zs").textContent=st.paused?"Duraklatıldı":running()?(st.pomo&&st.pomo.on?(st.pomo.phase==="work"?"Çalışma · tur "+st.pomo.round:"Mola"):st.label||"Çalışıyor"):st.fired&&st.end?"Süre doldu":"Bir süre seçin";
  el.querySelector("#zp").textContent=st.paused?"▶ DEVAM":"⏸ DURAKLAT";el.querySelector("#zc").style.display=a?"":"none";
  if(running()&&P.tick){const s=Math.ceil(l);if(s<=10&&s>=1&&s!==lastTick){lastTick=s;beep(s<=3?1000:760,70,.08)}}}
 function render(e){el=e;const C=2*Math.PI*88;
  e.innerHTML=`<style>#zr{position:relative;width:min(70vw,300px);margin:8px auto}#zr svg{width:100%}#zm{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}#zt{font:300 56px Bahnschrift,system-ui;color:#fff;font-variant-numeric:tabular-nums}.sw{width:30px;height:30px;border-radius:50%;padding:0}.sw.on{outline:2px solid #fff;outline-offset:2px}</style>
   <div id="zr"><svg viewBox="0 0 200 200"><circle cx="100" cy="100" r="88" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="8"/><circle id="za" cx="100" cy="100" r="88" fill="none" stroke="var(--c)" stroke-width="8" stroke-linecap="round" stroke-dasharray="${C}" stroke-dashoffset="${C}" transform="rotate(-90 100 100)" style="transition:stroke-dashoffset .4s linear"/></svg><div id="zm"><div id="zt">00:00</div><div id="zs" class="mut" style="font-size:14px;text-align:center;max-width:70%"></div></div></div>
   <div class="row" style="justify-content:center;margin:6px 0"><button id="zm5">−5</button><button id="zm1">−1</button><button class="prim" id="zp" style="min-width:130px">⏸ DURAKLAT</button><button id="zp1">+1</button><button id="zp5">+5</button></div>
   <div class="row" style="justify-content:center"><button id="zr2">↻ BAŞTAN</button><button id="zc">✕ İPTAL</button></div>
   <div class="card"><h3>Süre seç</h3><div class="row" id="zpre">${[1,5,10,15,25,30,45,60].map(m=>`<button data-m="${m}">${m} dk</button>`).join("")}</div>
    <div class="row" style="margin-top:10px"><input id="zcm" type="number" inputmode="numeric" min="1" max="1440" placeholder="dk" style="width:80px"><input id="zcs" type="number" inputmode="numeric" min="0" max="59" placeholder="sn" style="width:80px"><input id="zl" placeholder="Ad (isteğe bağlı)" style="flex:1"><button class="prim" id="zg">BAŞLAT</button></div></div>
   <div class="card"><h3>Pomodoro</h3><div class="row"><span class="mut">Çalışma</span><input id="zpw" type="number" inputmode="numeric" style="width:70px" value="${P.pw}"><span class="mut">Mola</span><input id="zpb" type="number" inputmode="numeric" style="width:70px" value="${P.pb}"><button class="prim" id="zpo">BAŞLAT</button></div></div>
   <div class="card"><h3>Ayarlar</h3><div class="row sp"><span>Renk</span><span class="row" id="zcol">${COLS.map(c=>`<button class="sw" data-c="${c}" style="background:${c}"></button>`).join("")}</span></div>
    <div class="row sp" style="margin-top:12px"><span>Son 10 sn tik sesi</span><input type="checkbox" id="ztk" ${P.tick?"checked":""}></div><div class="row sp" style="margin-top:12px"><span>Ekran kapanmasın</span><input type="checkbox" id="zwk" ${P.wake?"checked":""}></div></div>`;
  const $$=s=>e.querySelector(s);document.documentElement.style.setProperty("--c",P.col);
  e.querySelectorAll("#zcol .sw").forEach(b=>{b.classList.toggle("on",b.dataset.c===P.col);b.onclick=()=>{P.col=b.dataset.c;saveP();document.documentElement.style.setProperty("--c",P.col);e.querySelectorAll("#zcol .sw").forEach(x=>x.classList.toggle("on",x===b))}});
  e.querySelectorAll("#zpre button").forEach(b=>b.onclick=()=>start(+b.dataset.m*60));
  $$("#zg").onclick=()=>{const s=(+$$("#zcm").value||0)*60+(+$$("#zcs").value||0);if(s>0)start(s,$$("#zl").value.trim())};
  $$("#zp").onclick=()=>st.paused?resume():pause();$$("#zc").onclick=stop;$$("#zr2").onclick=()=>{if(st.dur)start(st.dur,st.label,true)};
  [["zm5",-300],["zm1",-60],["zp1",60],["zp5",300]].forEach(([i,s])=>$$("#"+i).onclick=()=>adj(s));
  $$("#zpo").onclick=()=>{P.pw=Math.max(1,+$$("#zpw").value||25);P.pb=Math.max(1,+$$("#zpb").value||5);saveP();st.pomo={on:true,phase:"work",round:1};start(P.pw*60,"Çalışma",true);say(`Pomodoro başladı, ${P.pw} dakika çalışma.`)};
  $$("#ztk").onchange=ev=>{P.tick=ev.target.checked;saveP()};$$("#zwk").onchange=ev=>{P.wake=ev.target.checked;saveP();wake()};
  paint();clearInterval(iv);iv=setInterval(paint,250)}
 function cmd(t){
  if(/(?:^|\s)(duraklat|beklet|durdur)(?=\s|$)/.test(t)){pause();return"Duraklatıldı."}
  if(/(?:^|\s)(devam|sürdür)(?=\s|$)/.test(t)){resume();return"Devam ediyor."}
  if(/(?:^|\s)(iptal|bitir|sıfırla|kapat)(?=\s|$)/.test(t)){stop();return"Zamanlayıcı iptal edildi."}
  if(/(?:^|\s)baştan(?=\s|$)/.test(t)){if(st.dur){start(st.dur,st.label,true);return"Baştan başladı."}}
  if(/(?:^|\s)pomodoro(?=\s|$)/.test(t)){st.pomo={on:true,phase:"work",round:1};start(P.pw*60,"Çalışma",true);return`Pomodoro başladı, ${P.pw} dakika çalışma.`}
  if(/(?:^|\s)(kalan|ne kadar)(?=\s|$)/.test(t)){if(!active())return"Çalışan zamanlayıcı yok.";const l=Math.ceil(left()),m=Math.floor(l/60);return m?`${m} dakika ${l%60} saniye kaldı.`:`${l} saniye kaldı.`}
  let sec=0;const h=t.match(/(\d+|yarım)\s*saat/),m=t.match(/(\d+)\s*(dakika|dk)/),s=t.match(/(\d+)\s*(saniye|sn)/);
  if(h)sec+=(h[1]==="yarım"?.5:+h[1])*3600;if(m)sec+=+m[1]*60;if(s)sec+=+s[1];
  if(!sec){const n=numIn(t);if(n&&/dakika|dk/.test(t))sec=n*60}
  if(sec){if(/(?:^|\s)(ekle|uzat|daha)(?=\s|$)/.test(t)&&active()){adj(sec);return"Eklendi."}if(/(?:^|\s)(çıkar|azalt|kısalt)(?=\s|$)/.test(t)&&active()){adj(-sec);return"Çıkarıldı."}
   start(sec);return`${m&&!h&&!s?m[1]+" dakika":fmt(sec)} başladı.`}
  return null}
 reg({id:"zaman",name:"Zamanlayıcı",icon:"⏱",say:/zamanlay|sayaç|sayac|pomodoro|(?:^|\s)süre(?=\s|$)/,weak:/dakika|saniye|(?:^|\s)saat(?=\s|$)/,render,cmd,leave(){clearInterval(iv)}});
})();

// ================================================================= KARAR ÇARKI
(function(){
 const DEF={"ders çalışma":["Matematik","Fizik","Kimya","Biyoloji","Türkçe","Tarih","Coğrafya"],"yemek":["Tavuk döner","Makarna","Pizza","Mercimek çorbası","Omlet","Köfte"],"ne yapsam":["Kitap oku","Yürüyüşe çık","Film izle","Müzik dinle","Arkadaşını ara","Bir şey çiz"]};
 const CL=["#ff7ad9","#7aa7ff","#5ee08a","#ffd84a","#ff9a5c","#c58bff","#4fe0e0","#ff6b8a"];
 let D=DB.get("cark",{wheels:DEF,cur:"ders çalışma"}),el=null,ang=0,spinning=false;const save=()=>DB.set("cark",D);
 const opts=()=>D.wheels[D.cur]||[];
 function draw(){const c=el&&el.querySelector("#cv");if(!c)return;const g=c.getContext("2d"),o=opts(),n=o.length||1,R=c.width/2-14,cx=c.width/2,cy=c.height/2;g.clearRect(0,0,c.width,c.height);g.save();g.translate(cx,cy);g.rotate(ang);
  for(let i=0;i<n;i++){const a0=i/n*6.2832,a1=(i+1)/n*6.2832;g.beginPath();g.moveTo(0,0);g.arc(0,0,R,a0,a1);g.closePath();g.fillStyle=CL[i%CL.length];g.fill();g.strokeStyle="#0008";g.lineWidth=3;g.stroke();
   g.save();g.rotate((a0+a1)/2);g.textAlign="right";g.fillStyle="#111";g.font="600 "+(n>9?15:19)+"px system-ui";let t=o[i]||"";if(t.length>14)t=t.slice(0,13)+"…";g.fillText(t,R-14,6);g.restore()}
  g.restore();g.beginPath();g.arc(cx,cy,24,0,6.2832);g.fillStyle="#120410";g.fill();g.strokeStyle="#ff7ad9";g.lineWidth=4;g.stroke();
  g.beginPath();g.moveTo(cx+R-26,cy);g.lineTo(cx+R+10,cy-14);g.lineTo(cx+R+10,cy+14);g.closePath();g.fillStyle="#fff";g.strokeStyle="#120410";g.lineWidth=2.5;g.fill();g.stroke()}
 function spin(){const o=opts();if(spinning)return null;if(o.length<2){say("Çarkta en az iki seçenek olmalı.");return null}spinning=true;const idx=rnd(o.length),n=o.length,seg=6.2832/n,target=-((idx+.5)*seg)+(Math.random()-.5)*seg*.6,from=ang%6.2832,to=from+6.2832*(5+rnd(3))+(((target-from)%6.2832)+6.2832)%6.2832,t0=performance.now(),Dm=4200;
  el.querySelector("#res").textContent="…";
  (function f(now){const p=Math.min(1,(now-t0)/Dm);ang=from+(to-from)*(1-Math.pow(1-p,4));draw();if(p<1)requestAnimationFrame(f);else{ang=to%6.2832;spinning=false;el.querySelector("#res").textContent=o[idx];buzz(80);say(o[idx]+" çıktı.")}})(t0);return idx}
 function ui(){if(!el||!el.isConnected)return;el.querySelector("#wl").innerHTML=Object.keys(D.wheels).map(k=>`<button data-k="${esc(k)}" class="${k===D.cur?"cur":""}">${esc(k)} (${D.wheels[k].length})</button>`).join("");
  el.querySelectorAll("#wl button").forEach(b=>b.onclick=()=>{D.cur=b.dataset.k;save();ang=0;ui()});
  el.querySelector("#ol").innerHTML=opts().map((x,i)=>`<div class="it"><span style="color:${CL[i%CL.length]}">● <span style="color:#fff">${esc(x)}</span></span><a data-i="${i}">×</a></div>`).join("");
  el.querySelectorAll("#ol a").forEach(a=>a.onclick=()=>{D.wheels[D.cur].splice(+a.dataset.i,1);save();ui()});draw()}
 function render(e){el=e;e.innerHTML=`<div id="wl" class="row" style="margin:6px 0"></div><canvas id="cv" width="420" height="420" style="width:min(88vw,400px);display:block;margin:6px auto"></canvas><div id="res" class="big" style="text-align:center;min-height:50px;font-size:30px"></div>
  <div class="row" style="justify-content:center"><button class="prim" id="sp" style="padding:14px 40px;font-size:15px">ÇEVİR</button></div>
  <div class="card"><h3>Seçenekler</h3><div id="ol"></div><div class="row" style="margin-top:8px"><input id="no" placeholder="Seçenek ekle" style="flex:1"><button id="na">+</button></div></div>
  <div class="card"><h3>Yeni çark</h3><div class="row"><input id="nn" placeholder="Ad" style="width:110px"><input id="nv" placeholder="seçenekler, virgülle" style="flex:1"><button id="nc">OLUŞTUR</button></div></div>
  <div class="card"><h3>Rastgele</h3><div class="row"><input id="ra" type="number" inputmode="numeric" value="1" style="width:70px"><span>–</span><input id="rb" type="number" inputmode="numeric" value="50" style="width:70px"><button id="rn">SAYI</button><button id="yt">YAZI TURA</button><button id="zr">ZAR</button></div><div id="rr" class="big" style="margin-top:8px;text-align:center"></div></div>`;
  e.querySelector("#sp").onclick=spin;e.querySelector("#na").onclick=()=>{const v=e.querySelector("#no").value.trim();if(v){D.wheels[D.cur].push(v);save();e.querySelector("#no").value="";ui()}};
  e.querySelector("#nc").onclick=()=>{const n=e.querySelector("#nn").value.trim().toLowerCase(),o=e.querySelector("#nv").value.split(",").map(x=>x.trim()).filter(Boolean);if(n&&o.length>1){D.wheels[n]=o;D.cur=n;save();ui()}};
  e.querySelector("#rn").onclick=()=>num(+e.querySelector("#ra").value,+e.querySelector("#rb").value);e.querySelector("#yt").onclick=()=>coin();e.querySelector("#zr").onclick=()=>dice();ui()}
 const out=t=>{const r=el&&el.querySelector("#rr");if(r)r.textContent=t};
 const num=(a,b)=>{if(a>b)[a,b]=[b,a];const n=a+rnd(b-a+1);out(n);return`${a} ile ${b} arasında ${n} çıktı.`};const coin=()=>{const r=Math.random()<.5?"Yazı":"Tura";out(r);return r+" geldi."};const dice=()=>{const n=1+rnd(6);out("⚀⚁⚂⚃⚄⚅"[n-1]+" "+n);return n+" geldi."};
 function cmd(t,raw){
  const m=t.match(/(\d+)\s*(?:ile|ve)\s*(\d+)\s*arası/);if(m&&/sayı/.test(t))return num(+m[1],+m[2]);
  if(/yazı tura|para at/.test(t))return coin();if(/(?:^|\s)zar(?=\s|$)/.test(t))return dice();
  const name=Object.keys(D.wheels).sort((a,b)=>b.length-a.length).find(k=>t.includes(norm(k)));
  if(/(?:^|\s)(ekle)(?=\s|$)/.test(t)&&/seçenek|çarka/.test(t)){const body=raw.includes(":")?raw.split(":").slice(1).join(":"):raw.replace(/.*ekle\w*\s*/i,"");const o=body.split(",").map(x=>x.trim()).filter(Boolean);if(!o.length)return"Ne ekleyeyim?";const k=name||D.cur;D.wheels[k]=D.wheels[k].concat(o);D.cur=k;save();ui();return o.join(", ")+" eklendi."}
  if(/(?:^|\s)(sil|çıkar|kaldır)(?=\s|$)/.test(t)){const k=name||D.cur,body=(raw.includes(":")?raw.split(":").slice(1).join(":"):raw).toLowerCase().replace(/(?:^|\s)(sil|çıkar|kaldır)\w*/g,"").replace(/çark\w*/g,"").trim();const n0=D.wheels[k].length;D.wheels[k]=D.wheels[k].filter(x=>norm(x)!==norm(body));save();ui();return D.wheels[k].length<n0?"Çıkarıldı.":"Bulamadım."}
  if(/(?:^|\s)(çevir|döndür|seç|çek)(?=\s|$)/.test(t)||name){if(name){D.cur=name;save();ui()}spin();return" "}
  return null}
 reg({id:"cark",name:"Karar çarkı",icon:"🎡",say:/çark|karar çark|(?:^|\s)kura(?=\s|$)|(?:^|\s)zar(?=\s|$)|yazı tura|rastgele/,render,cmd:(t,r)=>{const x=cmd(t,r);return x===" "?"Çark dönüyor.":x}});
})();

// ================================================================= BÜTÇE
(function(){
 const CATS=[["Kırtasiye",/kitap|kalem|defter|silgi|fotokopi|kırtasiye|çanta/],["Ulaşım",/otobüs|metro|taksi|dolmuş|servis|benzin|bilet|ulaşım|tramvay/],["Eğlence",/sinema|oyun|netflix|spotify|konser|eğlence|abonelik/],["Yemek",/yemek|döner|kafe|kahve|çay|pizza|burger|tost|simit|börek|cips|çikolata|dondurma|kantin|market|içecek|tatlı/],["Giyim",/tişört|pantolon|ayakkabı|mont|kıyafet|elbise|kazak/]];
 const COL={"Kırtasiye":"#6ab7ff","Ulaşım":"#ffd84a","Eğlence":"#c58bff","Yemek":"#ff9a5c","Giyim":"#ff6b8a","Diğer":"#9aa7b5"};
 let D=DB.get("butce",{allow:0,tx:[],goals:[]}),el=null;const save=()=>DB.set("butce",D);
 const fm=n=>Math.round(n).toLocaleString("tr-TR")+" ₺";const cat=t=>(CATS.find(c=>c[1].test(t))||["Diğer"])[0];
 const money=s=>{const m=String(s).match(/(\d{1,3}(?:\.\d{3})+|\d+(?:[.,]\d+)?)\s*(bin(?=\s|$))?/);if(!m)return null;let v=m[1];v=/^\d{1,3}(\.\d{3})+$/.test(v)?v.replace(/\./g,""):v.replace(",",".");return +v*(m[2]?1000:1)||null};
 function month(){const ym=new Date().toISOString().slice(0,7),tx=D.tx.filter(x=>x.ts.startsWith(ym)),cats={};let sp=0,inc=0;tx.forEach(x=>{if(x.kind==="gider"){sp+=x.amt;cats[x.cat]=(cats[x.cat]||0)+x.amt}else inc+=x.amt});return{sp,inc,cats,left:D.allow+inc-sp}}
 function ui(){if(!el||!el.isConnected)return;const m=month(),tot=D.allow+m.inc,pc=tot?Math.min(100,m.sp/tot*100):0;
  el.querySelector("#bl").textContent=fm(m.left);el.querySelector("#bl").style.color=m.left<0?"var(--bad)":"#fff";el.querySelector("#bs").textContent=fm(m.sp);el.querySelector("#bi").textContent=fm(m.inc);el.querySelector("#ba").textContent=fm(D.allow);
  const pb=el.querySelector("#bp");pb.style.width=pc+"%";pb.style.background=pc>85?"var(--bad)":pc>60?"var(--warn)":"linear-gradient(90deg,#5ee08a,#22a85a)";
  const mx=Math.max(1,...Object.values(m.cats));el.querySelector("#bc").innerHTML=Object.entries(m.cats).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<div style="margin:8px 0"><div class="row sp"><span>${esc(k)}</span><b>${fm(v)}</b></div><div class="bar" style="margin:4px 0"><i style="width:${v/mx*100}%;background:${COL[k]||"#9aa7b5"}"></i></div></div>`).join("")||'<span class="mut">Henüz harcama yok.</span>';
  el.querySelector("#bt").innerHTML=D.tx.slice(-10).reverse().map(x=>`<div class="it"><span>${esc(x.note||x.cat)} <small class="mut">${esc(x.cat)} · ${esc(x.ts.slice(5,10))}</small></span><b class="${x.kind==="gelir"?"ok":"bad"}">${x.kind==="gelir"?"+":"−"}${fm(x.amt)}</b></div>`).join("")||'<span class="mut">Kayıt yok.</span>';
  el.querySelector("#bg").innerHTML=D.goals.map((g,i)=>{const p=Math.min(100,g.saved/g.target*100);return`<div style="margin:10px 0"><div class="row sp"><span>${esc(g.name)}</span><b>${fm(g.saved)} / ${fm(g.target)}</b></div><div class="bar" style="margin:4px 0"><i style="width:${p}%;background:linear-gradient(90deg,#ffd84a,#5ee08a)"></i></div><a data-g="${i}" class="bad" style="font-size:12px;cursor:pointer">hedefi sil</a></div>`}).join("")||'<span class="mut">Hedef yok.</span>';
  el.querySelectorAll("#bg a").forEach(a=>a.onclick=()=>{D.goals.splice(+a.dataset.g,1);save();ui()})}
 function add(kind,amt,note){D.tx.push({ts:new Date().toISOString().slice(0,16).replace("T"," "),amt:Math.round(amt*100)/100,cat:kind==="gelir"?"Gelir":cat(note.toLowerCase()),note:note.trim().slice(0,40),kind});D.tx=D.tx.slice(-500);save();ui()}
 function render(e){el=e;e.innerHTML=`<div class="card"><h3>Bu ay</h3><div class="mut" style="font-size:12px;letter-spacing:.2em">KALAN HARÇLIK</div><div class="big" id="bl">0 ₺</div><div class="bar"><i id="bp" style="width:0"></i></div>
   <div class="row sp"><span class="mut">Harcanan <b id="bs" class="bad">0</b></span><span class="mut">Gelir <b id="bi" class="ok">0</b></span><span class="mut">Harçlık <b id="ba">0</b></span></div></div>
  <div class="card"><h3>Ekle</h3><div class="row"><input id="qn" placeholder="Ne için? (kitap, otobüs…)" style="flex:1;min-width:140px"><input id="qa" type="number" inputmode="decimal" placeholder="₺" style="width:90px"></div><div class="row" style="margin-top:8px"><button class="prim" id="q1">HARCAMA</button><button id="q2">GELİR</button><input id="ql" type="number" inputmode="numeric" placeholder="Aylık harçlık" style="width:130px"><button id="q3">AYARLA</button></div></div>
  <div class="card"><h3>Kategoriler</h3><div id="bc"></div></div><div class="card"><h3>Son işlemler <a id="un" class="bad" style="float:right;font-size:12px;cursor:pointer;letter-spacing:0">son kaydı sil</a></h3><div id="bt"></div></div>
  <div class="card"><h3>Birikim hedefleri</h3><div id="bg"></div><div class="row" style="margin-top:8px"><input id="gn" placeholder="Hedef" style="flex:1;min-width:100px"><input id="gt" type="number" inputmode="numeric" placeholder="₺" style="width:90px"><button id="g1">EKLE</button></div><div class="row" style="margin-top:8px"><input id="gs" type="number" inputmode="numeric" placeholder="Yatır ₺" style="width:110px"><button id="g2">YATIR</button></div></div>`;
  const v=s=>e.querySelector(s).value.trim();
  e.querySelector("#q1").onclick=()=>{const a=+v("#qa");if(a>0){add("gider",a,v("#qn")||"harcama");e.querySelector("#qa").value=e.querySelector("#qn").value=""}};
  e.querySelector("#q2").onclick=()=>{const a=+v("#qa");if(a>0){add("gelir",a,v("#qn")||"harçlık");e.querySelector("#qa").value=e.querySelector("#qn").value=""}};
  e.querySelector("#q3").onclick=()=>{if(+v("#ql")>0){D.allow=+v("#ql");save();ui()}};e.querySelector("#un").onclick=()=>{D.tx.pop();save();ui()};
  e.querySelector("#g1").onclick=()=>{if(v("#gn")&&+v("#gt")>0){D.goals.push({name:v("#gn"),target:+v("#gt"),saved:0});save();ui();e.querySelector("#gn").value=e.querySelector("#gt").value=""}};
  e.querySelector("#g2").onclick=()=>{if(D.goals.length&&+v("#gs")>0){D.goals[D.goals.length-1].saved+=+v("#gs");save();ui();e.querySelector("#gs").value=""}};ui()}
 function cmd(t,raw){const a=money(raw);
  if(/son (harcama|gider|işlem)\w*.*(?:^|\s)(sil|kaldır)(?=\s|$)/.test(t)){const x=D.tx.pop();save();ui();return x?"Son kaydı sildim.":"Silinecek kayıt yok."}
  if(/harçlığ\w*/.test(t)&&/(?:^|\s)(olsun|yap|ayarla)(?=\s|$)/.test(t)&&a){D.allow=a;save();ui();return`Aylık harçlığınız ${fm(a)} oldu.`}
  if(/(?:^|\s)(ne kadar|kaç)(?=\s|$).*(?:^|\s)(harca\w*)/.test(t)){const m=month(),top=Object.entries(m.cats).sort((x,y)=>y[1]-x[1])[0];return`Bu ay ${fm(m.sp)} harcadınız`+(top?`, en çok ${top[0]}.`:".")}
  if(/(?:^|\s)kalan(?=\s|$)|harçlığım ne kadar/.test(t))return`Kalan harçlığınız ${fm(month().left)}.`;
  if(/(?:^|\s)(birikim|hedef)\w*/.test(t)&&a){const dative=/hedef(ine|e|ime)(?=\s|$)|birikim(e|ime)(?=\s|$)/.test(t),mm=raw.match(/hedef\w*\s*[:：]?\s*(.*?)\s*\d/i),name=(mm?mm[1]:"").replace(/(?:^|\s)(ekle|koy|yeni|için)(?=\s|$)/gi,"").trim();
   if(!dative&&name){D.goals.push({name:name.slice(0,40),target:a,saved:0});save();ui();return`${name} hedefi eklendi: ${fm(a)}.`}
   if(D.goals.length){const g=D.goals[D.goals.length-1];g.saved+=a;save();ui();return`${g.name} hedefine ${fm(a)} eklendi, şu an ${fm(g.saved)}.`}return"Önce bir hedef oluşturun."}
  if(/(?:^|\s)(ekle|harcadım|harcama|ödedim|aldım|gelir|kazandım)(?=\s|$)/.test(t)){if(!a)return"Tutarı anlayamadım.";const inc=/(?:^|\s)(gelir|harçlık aldım|kazandım|maaş)(?=\s|$)/.test(t)&&!/harcama|harcadım/.test(t);
   const note=raw.replace(/(?:^|\s)(harcama|gelir|ekle|için|harcadım|ödedim|aldım|kazandım|bugün)(?=\s|$)/gi,"").replace(/[:：]|[\d.,]+\s*(bin)?\s*(tl|lira|₺)?/gi," ").replace(/\s+/g," ").trim();add(inc?"gelir":"gider",a,note||(inc?"harçlık":"harcama"));return`${inc?"Gelir":"Harcama"} kaydedildi: ${fm(a)}.`}
  return null}
 reg({id:"butce",name:"Bütçe",icon:"💰",say:/bütçe|butce|harçl\w*|harca\w*|birikim|hedef/,render,cmd});
})();

// ================================================================= LİSTELER (alışveriş / yapılacaklar)
(function(){
 let D=DB.get("listeler",{cur:"Alışveriş",l:{"Alışveriş":[],"Yapılacaklar":[]}}),el=null;const save=()=>DB.set("listeler",D);
 function ui(){if(!el||!el.isConnected)return;el.querySelector("#tb").innerHTML=Object.keys(D.l).map(k=>`<button data-k="${esc(k)}" class="${k===D.cur?"cur":""}">${esc(k)} (${D.l[k].filter(x=>!x.d).length})</button>`).join("");
  el.querySelectorAll("#tb button").forEach(b=>b.onclick=()=>{D.cur=b.dataset.k;save();ui()});
  el.querySelector("#li").innerHTML=D.l[D.cur].map((x,i)=>`<div class="it"><label style="flex:1;display:flex;gap:12px;align-items:center;${x.d?"opacity:.5;text-decoration:line-through":""}"><input type="checkbox" data-i="${i}" ${x.d?"checked":""} style="width:22px;height:22px">${esc(x.t)}</label><a data-x="${i}">×</a></div>`).join("")||'<span class="mut">Liste boş.</span>';
  el.querySelectorAll("#li input").forEach(c=>c.onchange=()=>{D.l[D.cur][+c.dataset.i].d=c.checked;save();ui()});el.querySelectorAll("#li a").forEach(a=>a.onclick=()=>{D.l[D.cur].splice(+a.dataset.x,1);save();ui()})}
 function addMany(txt){const items=txt.split(/,| ve /).map(x=>x.trim()).filter(Boolean);items.forEach(x=>D.l[D.cur].push({t:x.charAt(0).toUpperCase()+x.slice(1),d:false}));save();ui();return items.length}
 function render(e){el=e;e.innerHTML=`<div class="row" id="tb" style="margin:6px 0"></div><div class="card"><div class="row"><input id="ni" placeholder="Ekle (virgülle birden çok)" style="flex:1"><button class="prim" id="na">EKLE</button></div><div id="li" style="margin-top:8px"></div>
  <div class="row" style="margin-top:10px"><button id="cd">YAPILANLARI SİL</button><button id="ca">TÜMÜNÜ TEMİZLE</button></div></div><div class="card"><h3>Yeni liste</h3><div class="row"><input id="nl" placeholder="Ad" style="flex:1"><button id="nc">OLUŞTUR</button></div></div>`;
  const add=()=>{const v=e.querySelector("#ni").value;if(v.trim()){addMany(v);e.querySelector("#ni").value=""}};e.querySelector("#na").onclick=add;e.querySelector("#ni").addEventListener("keydown",ev=>{if(ev.key==="Enter")add()});
  e.querySelector("#cd").onclick=()=>{D.l[D.cur]=D.l[D.cur].filter(x=>!x.d);save();ui()};e.querySelector("#ca").onclick=()=>{D.l[D.cur]=[];save();ui()};
  e.querySelector("#nc").onclick=()=>{const n=e.querySelector("#nl").value.trim();if(n&&!D.l[n]){D.l[n]=[];D.cur=n;save();ui();e.querySelector("#nl").value=""}};ui()}
 function cmd(t,raw){
  const k=Object.keys(D.l).find(k=>t.includes(norm(k)));if(k&&/(?:^|\s)(listesi|listeye|listem)(?=\s|$)/.test(t)){D.cur=k;save();ui()}
  if(/(?:^|\s)(temizle|boşalt)(?=\s|$)/.test(t)){D.l[D.cur]=[];save();ui();return"Liste temizlendi."}
  if(/yapılanları sil|işaretlileri sil/.test(t)){D.l[D.cur]=D.l[D.cur].filter(x=>!x.d);save();ui();return"Yapılanlar silindi."}
  const mk=t.match(/(.+?)\s*(?:i|ı|u|ü)?\s*(işaretle|aldım|yaptım|tamam)(?=\s|$)/);if(mk){const w=mk[1].replace(/(?:^|\s)(listeden|listemden)(?=\s|$)/g,"").trim(),it=D.l[D.cur].find(x=>norm(x.t).includes(w));if(it){it.d=true;save();ui();return`${it.t} işaretlendi.`}}
  const body=raw.includes(":")?raw.split(":").slice(1).join(":"):raw.replace(/(?:^|\s)(listeye|listemize|listem\w*|liste\w*|ekle\w*|ekler misin|alışveriş|yapılacak\w*)(?=\s|$)/gi,"").trim();
  if(/(?:^|\s)ekle\w*|listeye(?=\s|$)/.test(t)&&body.trim()){const n=addMany(body);return`${n} öğe eklendi.`}
  if(/(?:^|\s)(neler var|oku|listem|ne lazım)(?=\s|$)/.test(t)){const o=D.l[D.cur].filter(x=>!x.d).map(x=>x.t);return o.length?`${D.cur} listesinde: ${o.join(", ")}.`:"Liste boş."}
  return null}
 reg({id:"liste",name:"Listeler",icon:"📝",say:/liste|alışveriş|yapılacak/,render,cmd});
})();
