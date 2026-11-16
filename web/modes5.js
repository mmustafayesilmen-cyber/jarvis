"use strict";
/* Modlar 5: Zihin oyunları (hızlı hesap, hafıza eşleştirme, renk dizisi, sayı dizisi) ve Tarif defteri (39 yerleşik tarif, kişi sayısı ölçekleme, adım sayaçları). */

// ================================================================= ZİHİN OYUNLARI
(function(){let H=DB.get("oyun",{calc:0,mem:0,simon:0,seq:0}),el=null,g=null;const save=()=>DB.set("oyun",H);
 const stop=()=>{if(g&&g.stop)g.stop();g=null};
 function out(h){el.querySelector("#og").innerHTML=h}
 function hs(){el.querySelector("#oh").textContent=`Rekorlar · hesap ${H.calc} · hafıza ${H.mem||"-"} hamle · renk ${H.simon} · dizi ${H.seq}`}
 // --- hızlı hesap: 60 sn
 function calc(){stop();let sc=0,t=60,ans=0,iv;const next=()=>{const a=2+rnd(12),b=2+rnd(12),op=["+","−","×"][rnd(3)];ans=op==="+"?a+b:op==="−"?a-b:a*b;el.querySelector("#q").textContent=`${a} ${op} ${b} = ?`;const i=el.querySelector("#i");i.value="";i.focus()};
  out(`<div class="card" style="text-align:center"><div class="mut">Süre <b id="t">60</b> · Puan <b id="s">0</b></div><div id="q" class="big" style="margin:16px 0">…</div><input id="i" type="number" inputmode="numeric" style="width:140px;text-align:center;font-size:24px"></div>`);
  const i=el.querySelector("#i");i.onkeydown=e=>{if(e.key==="Enter"){if(+i.value===ans){sc++;el.querySelector("#s").textContent=sc;beep(900,60)}else beep(200,120);next()}};next();
  iv=setInterval(()=>{t--;el.querySelector("#t").textContent=t;if(t<=0){clearInterval(iv);if(sc>H.calc){H.calc=sc;save()}hs();out(`<div class="card" style="text-align:center"><div class="big">${sc} doğru</div><div class="mut">Rekor ${H.calc}</div></div>`)}},1000);g={stop:()=>clearInterval(iv)}}
 // --- hafıza eşleştirme
 function mem(){stop();const E=["🍎","🚀","🎸","🐱","🌵","⚽","🎲","🍕"],cards=E.concat(E).sort(()=>Math.random()-.5);let open=[],moves=0,found=0,lock=false;
  out(`<div class="mut" style="text-align:center;margin:6px">Hamle <b id="mv">0</b></div><div id="gr" style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">${cards.map((c,i)=>`<button data-i="${i}" style="height:72px;font-size:30px;padding:0">?</button>`).join("")}</div>`);
  el.querySelectorAll("#gr button").forEach(b=>b.onclick=()=>{if(lock||b.disabled||open.includes(+b.dataset.i))return;const i=+b.dataset.i;b.textContent=cards[i];b.classList.add("cur");open.push(i);
   if(open.length===2){moves++;el.querySelector("#mv").textContent=moves;const[x,y]=open;if(cards[x]===cards[y]){[x,y].forEach(k=>{el.querySelector(`[data-i="${k}"]`).disabled=true});open=[];found++;beep(900,80);if(found===8){if(!H.mem||moves<H.mem){H.mem=moves;save()}hs();say(`Bitti, ${moves} hamle.`,true)}}else{lock=true;setTimeout(()=>{[x,y].forEach(k=>{const bb=el.querySelector(`[data-i="${k}"]`);bb.textContent="?";bb.classList.remove("cur")});open=[];lock=false},700)}}});g={}}
 // --- renk dizisi (Simon)
 function simon(){stop();const C=["#ff6b8a","#5ee08a","#6ab7ff","#ffd84a"],F=[260,330,392,523];let seq=[],pos=0,busy=true;
  out(`<div class="mut" style="text-align:center;margin:6px">Tur <b id="r">0</b></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">${C.map((c,i)=>`<button data-c="${i}" style="height:110px;background:${c};opacity:.45;border:0"></button>`).join("")}</div><div class="row" style="justify-content:center;margin-top:12px"><button class="prim" id="sg">BAŞLA</button></div>`);
  const flash=i=>new Promise(r=>{const b=el.querySelector(`[data-c="${i}"]`);b.style.opacity=1;beep(F[i],220,.15);setTimeout(()=>{b.style.opacity=.45;r()},300)});
  const play=async()=>{busy=true;pos=0;await new Promise(r=>setTimeout(r,500));for(const i of seq){await flash(i);await new Promise(r=>setTimeout(r,150))}busy=false};
  const nextRound=()=>{seq.push(rnd(4));el.querySelector("#r").textContent=seq.length;play()};
  el.querySelector("#sg").onclick=()=>{seq=[];nextRound()};
  el.querySelectorAll("[data-c]").forEach(b=>b.onclick=async()=>{if(busy||!seq.length)return;const i=+b.dataset.c;await flash(i);if(seq[pos]!==i){busy=true;const s=seq.length-1;if(s>H.simon){H.simon=s;save()}hs();beep(150,400);say(`Yanlış. ${s} tur geçtiniz.`,true);seq=[];return}pos++;if(pos===seq.length){busy=true;setTimeout(nextRound,600)}});g={}}
 // --- sayı dizisi
 function seqg(){stop();let sc=0,lives=3,ans=0;const mk=()=>{const t=rnd(4),a=1+rnd(9),d=2+rnd(7);let s=[];if(t===0)for(let i=0;i<5;i++)s.push(a+d*i);else if(t===1)for(let i=0;i<5;i++)s.push(a*Math.pow(2,i));else if(t===2)for(let i=0;i<5;i++)s.push(a+i*i);else{s=[a,d];for(let i=2;i<5;i++)s.push(s[i-1]+s[i-2])}return s};
  const next=()=>{const s=mk();ans=s[4];el.querySelector("#q").textContent=s.slice(0,4).join(", ")+", ?";const i=el.querySelector("#i");i.value="";i.focus()};
  out(`<div class="card" style="text-align:center"><div class="mut">Can ${"❤️".repeat(3)} <span id="l"></span> · Puan <b id="s">0</b></div><div id="q" class="big" style="margin:16px 0;font-size:30px">…</div><input id="i" type="number" inputmode="numeric" style="width:140px;text-align:center;font-size:24px"></div>`);
  const i=el.querySelector("#i");i.onkeydown=e=>{if(e.key!=="Enter")return;if(+i.value===ans){sc++;beep(900,60)}else{lives--;beep(200,150)}el.querySelector("#s").textContent=sc;el.querySelector("#l").textContent=lives+" can";if(lives<=0){if(sc>H.seq){H.seq=sc;save()}hs();out(`<div class="card" style="text-align:center"><div class="big">${sc} puan</div><div class="mut">Rekor ${H.seq}</div></div>`)}else next()};el.querySelector("#l").textContent="3 can";next();g={}}
 let iv;
 function render(e){el=e;e.innerHTML=`<div class="grid"><button class="tile" id="g1"><i>➕</i>Hızlı hesap</button><button class="tile" id="g2"><i>🧠</i>Hafıza</button><button class="tile" id="g3"><i>🎨</i>Renk dizisi</button><button class="tile" id="g4"><i>🔢</i>Sayı dizisi</button></div><div id="og" style="margin-top:12px"></div><div class="mut" id="oh" style="font-size:13px;margin-top:10px;text-align:center"></div>`;
  e.querySelector("#g1").onclick=calc;e.querySelector("#g2").onclick=mem;e.querySelector("#g3").onclick=simon;e.querySelector("#g4").onclick=seqg;hs()}
 function cmd(t){if(/hesap/.test(t)){calc();return"Hızlı hesap başladı."}if(/hafıza|eşleştir/.test(t)){mem();return"Hafıza oyunu başladı."}if(/renk/.test(t)){simon();return"Renk dizisi başladı."}if(/sayı dizi|dizi/.test(t)){seqg();return"Sayı dizisi başladı."}if(/rekor/.test(t))return`Rekorlar: hesap ${H.calc}, renk ${H.simon}, dizi ${H.seq}.`;return null}
 reg({id:"oyunlar",name:"Zihin oyunları",icon:"🎮",say:/oyun|hızlı hesap|hafıza oyunu|renk dizisi|sayı dizisi/,render,cmd,leave(){stop()}})})();

// ================================================================= TARİF DEFTERİ
(function(){let R=null,el=null,sel=null,P=1,tm=null,tleft=0,tlabel="";const SH=()=>DB.get("alisveris_tarif",[]);
 const FR={"½":.5,"¼":.25,"¾":.75,"⅓":1/3};function fmt(x){if(Math.abs(x-Math.round(x))<.01)return String(Math.round(x));const w=Math.floor(x),f=x-w;const m=[[.25,"¼"],[.33,"⅓"],[.5,"½"],[.67,"⅔"],[.75,"¾"]].find(p=>Math.abs(p[0]-f)<.06);return m?(w?w+" ":"")+m[1]:x.toFixed(1)}
 function scale(line,f){if(f===1)return line;return line.replace(/^(\d+(?:[.,]\d+)?(?:\s*[½¼¾⅓])?|[½¼¾⅓])/,m=>{const mm=m.match(/^(\d+(?:[.,]\d+)?)?\s*([½¼¾⅓])?$/);const v=(mm[1]?parseFloat(mm[1].replace(",",".")):0)+(mm[2]?FR[mm[2]]:0);return fmt(v*f)})}
 async function load(){if(R)return R;if(window.__TARIF){R=window.__TARIF;return R}try{R=await (await fetch("data/tarif.json")).json()}catch(e){R=[]}return R}
 function list(){if(!el||!el.isConnected||!R)return;const q=el.querySelector("#tq").value.trim().toLowerCase(),k=el.querySelector("#tk").value;const items=R.filter(r=>(!k||r.kat===k)&&(!q||(r.ad+" "+r.mal.join(" ")).toLowerCase().includes(q)));
  el.querySelector("#tl").innerHTML=items.map(r=>`<div class="it" data-id="${r.id}" style="cursor:pointer"><span><b>${esc(r.ad)}</b><div class="mut" style="font-size:13px">${esc(r.kat)} · ${r.dk} dk · ${r.kisi} kişilik</div></span><span>›</span></div>`).join("")||'<span class="mut">Tarif bulunamadı.</span>';el.querySelectorAll("#tl .it").forEach(r=>r.onclick=()=>show(r.dataset.id))}
 function show(id){sel=R.find(r=>r.id===id);if(!sel)return;P=sel.kisi;stopT();draw()}
 function draw(){if(!el||!el.isConnected)return;const v=el.querySelector("#tv");if(!sel){v.innerHTML="";return}const f=P/sel.kisi;
  v.innerHTML=`<div class="card"><h3>${esc(sel.ad)}</h3><div class="row sp"><span class="mut">${esc(sel.kat)} · ${sel.dk} dk</span><span class="row"><button id="tm">−</button><b>${P} kişilik</b><button id="tp">+</button></span></div>
   <h3 style="margin-top:14px">Malzemeler</h3>${sel.mal.map(m=>`<div class="it">${esc(scale(m,f))}</div>`).join("")}<button id="ta" style="margin-top:10px">🛒 ALIŞVERİŞ LİSTESİNE EKLE</button>
   <h3 style="margin-top:14px">Hazırlanışı</h3>${sel.adim.map((a,i)=>`<div class="it" style="align-items:flex-start"><span><b>${i+1}.</b> ${esc(a[0])}</span>${a[1]?`<button data-t="${a[1]}" data-i="${i}" style="white-space:nowrap">⏱ ${a[1]} dk</button>`:""}</div>`).join("")}<div id="tc" class="big" style="text-align:center;margin-top:10px"></div></div>`;
  const q=s=>v.querySelector(s);q("#tm").onclick=()=>{P=Math.max(1,P-1);draw()};q("#tp").onclick=()=>{P=Math.min(30,P+1);draw()};q("#ta").onclick=()=>{const L=SH(),n=sel.mal.map(m=>scale(m,f));DB.set("alisveris_tarif",L.concat(n.filter(x=>!L.includes(x))));
   const D2=DB.get("listeler",null);if(D2){D2.l["Alışveriş"]=(D2.l["Alışveriş"]||[]).concat(n.map(t=>({t,d:false})));DB.set("listeler",D2)}say("Malzemeler alışveriş listesine eklendi.",true)};
  v.querySelectorAll("[data-t]").forEach(b=>b.onclick=()=>startT(+b.dataset.t,`${+b.dataset.i+1}. adım`))}
 function startT(m,l){stopT();tleft=m*60;tlabel=l;tm=setInterval(()=>{tleft--;const c=el&&el.querySelector("#tc");if(c)c.textContent=tlabel+" · "+Math.floor(tleft/60)+":"+String(tleft%60).padStart(2,"0");if(tleft<=0){stopT();beep(880,250,.2);setTimeout(()=>beep(1175,300,.2),350);buzz([300,150,300]);say(tlabel+" süresi doldu.")}},1000)}
 function stopT(){clearInterval(tm);tm=null;const c=el&&el.querySelector("#tc");if(c)c.textContent=""}
 async function render(e){el=e;e.innerHTML=`<div class="row" style="margin:6px 0"><input id="tq" placeholder="Tarif ya da malzeme ara…" style="flex:1;min-width:120px"><select id="tk"><option value="">hepsi</option></select></div><div id="tv"></div><div class="card"><div id="tl"><span class="mut">Yükleniyor…</span></div></div>`;
  await load();const ks=[...new Set(R.map(r=>r.kat))];el.querySelector("#tk").innerHTML='<option value="">hepsi</option>'+ks.map(k=>`<option>${esc(k)}</option>`).join("");el.querySelector("#tq").oninput=list;el.querySelector("#tk").onchange=list;list();if(sel)draw()}
 function cmd(t,raw){if(!R)return null;
  if(/(malzeme|elimde).*(var)/.test(t)&&/(ne yap|tarif)/.test(t)){const w=t.replace(/(elimde|var|ne yapabilirim|tarif|ve)/g," ").split(" ").filter(x=>x.length>2);const sc=R.map(r=>({r,n:w.filter(x=>r.mal.join(" ").toLowerCase().includes(x)).length})).filter(x=>x.n).sort((a,b)=>b.n-a.n).slice(0,3);return sc.length?"Şunları yapabilirsiniz: "+sc.map(x=>x.r.ad).join(", ")+".":"Eşleşen tarif bulamadım."}
  const r=R.find(r=>t.includes(norm(r.ad))||(norm(r.ad).split(" ")[0].length>3&&t.includes(norm(r.ad).split(" ")[0])));
  if(r&&/tarif|nasıl yapılır|yapalım|yapacağım/.test(t)){if(!el||!el.isConnected)return null;show(r.id);return`${r.ad} tarifi açıldı, ${r.kisi} kişilik, ${r.dk} dakika.`}
  if(sel&&/malzeme/.test(t))return sel.mal.map(m=>scale(m,P/sel.kisi)).join(", ")+".";
  const k=t.match(/(\d+)\s*kişilik/);if(sel&&k){P=Math.min(30,+k[1]);draw();return`${P} kişilik olarak ayarladım.`}
  const sy=t.match(/(\d+)\.?\s*adım/);if(sel&&sy&&sel.adim[+sy[1]-1])return sel.adim[+sy[1]-1][0];return null}
 reg({id:"tarif",name:"Tarifler",icon:"🍳",say:/tarif|yemek yap|nasıl yapılır|elimde.*var/,render,cmd,leave(){stopT()}});load()})();
