"use strict";
/* Modlar 2: Kelime kutusu (Leitner), Hızlı okuma (RSVP), Fikir tahtası, Deneme sınavı optik formu */

// ================================================================= KELİME KUTUSU
(function(){
 const SEED=`substantial|önemli, hatırı sayılır|considerable|The company made a substantial profit.
reluctant|isteksiz|unwilling|She was reluctant to share her results.
abundant|bol|plentiful|Fresh water is abundant here.
inevitable|kaçınılmaz|unavoidable|Change is inevitable.
conclude|sonuca varmak|deduce|The study concluded that sleep helps memory.
essential|temel, şart|vital|Water is essential for life.
estimate|tahmin etmek|approximate|Experts estimate the population will double.
obtain|elde etmek|acquire|You must obtain permission.
frequent|sık|regular|Frequent exercise keeps you healthy.
reduce|azaltmak|decrease|We need to reduce energy use.
ancient|çok eski|archaic|Ancient civilizations built great cities.
benefit|fayda|advantage|Reading has many benefits.
challenge|zorluk|obstacle|Learning a language is a challenge.
consequence|sonuç|outcome|Every action has a consequence.
contribute|katkıda bulunmak|donate|Many people contributed to the project.
demand|talep|request|The demand for electric cars is rising.
enhance|artırmak|improve|Good lighting can enhance your mood.
evidence|kanıt|proof|There is no evidence for this.
flexible|esnek|adaptable|A flexible schedule helps.
generate|üretmek|produce|Wind turbines generate electricity.
hesitate|tereddüt etmek|pause|Don't hesitate to ask.
impact|etki|effect|Technology has a huge impact.
indicate|göstermek|suggest|Results indicate a clear trend.
maintain|sürdürmek, korumak|preserve|It is hard to maintain a healthy diet.
neglect|ihmal etmek|ignore|Do not neglect your homework.
obvious|açık, bariz|evident|The answer was obvious.
prevent|önlemek|avoid|Vaccines prevent many diseases.
rare|nadir|scarce|Snow is rare in this city.
severe|şiddetli|harsh|The region suffered a severe drought.
tend|eğilimi olmak|incline|Teenagers tend to sleep late.
reveal|ortaya çıkarmak|disclose|The test revealed an error.
urgent|acil|pressing|This is an urgent matter.
vast|geniş|enormous|A vast desert lies to the south.
accurate|doğru, kesin|precise|The map is not accurate.
ambitious|hırslı|determined|She is an ambitious student.
adapt|uyum sağlamak|adjust|Animals adapt to their environment.
appropriate|uygun|suitable|Wear appropriate clothes.
reliable|güvenilir|dependable|He is a reliable friend.
ability|yetenek|skill|She has the ability to learn quickly.
increase|artmak|rise|Prices continue to increase.`;
 const DE=`das Haus|ev||Das Haus ist sehr groß.
die Schule|okul||Ich gehe zur Schule.
der Freund|arkadaş|der Kamerad|Mein Freund heißt Max.
lernen|öğrenmek|studieren|Ich lerne jeden Tag Deutsch.
das Wasser|su||Ich trinke viel Wasser.
das Buch|kitap||Das Buch liegt auf dem Tisch.
arbeiten|çalışmak||Er arbeitet im Büro.
schnell|hızlı|rasch|Der Zug ist sehr schnell.
die Zeit|zaman||Ich habe keine Zeit.
schön|güzel|hübsch|Das Wetter ist schön.`;
 const BOX=[0,1,2,4,8,16];
 function seed(){const w=[];[["en",SEED],["de",DE]].forEach(([l,b])=>b.split("\n").forEach(x=>{const[a,tr,syn,ex]=x.split("|");w.push({w:a,tr,syn,ex,lang:l,box:0,due:"",seen:0})}));return w}
 let D=DB.get("kelime",null);if(!D){D={words:seed()};DB.set("kelime",D)}let V={ids:[],i:0,show:false,await:null},el=null;const save=()=>DB.set("kelime",D);
 const today=()=>new Date().toISOString().slice(0,10),cw=()=>V.ids.length&&V.i<V.ids.length?D.words[V.ids[V.i]]:null;
 function speak(){const c=cw();if(!c)return;try{const u=new SpeechSynthesisUtterance(c.w.replace(/^(der|die|das)\s+/,""));u.lang=c.lang==="de"?"de-DE":"en-US";u.rate=.85;speechSynthesis.cancel();speechSynthesis.speak(u)}catch(e){}}
 function session(n){const due=[],nw=[];D.words.forEach((w,i)=>{if(w.seen&&(w.due||"")<=today())due.push(i);else if(!w.seen)nw.push(i)});nw.sort(()=>Math.random()-.5);V={ids:due.concat(nw).slice(0,n),i:0,show:false,await:null};ui()}
 function ui(){if(!el||!el.isConnected)return;const c=cw();el.querySelector("#kw").textContent=c?c.w:V.ids.length?"Tebrikler!":"—";el.querySelector("#kt").textContent=c&&V.show?c.tr:"";el.querySelector("#ks").textContent=c&&V.show&&c.syn?"eş anlamlı: "+c.syn:"";el.querySelector("#ke").textContent=c&&V.show&&c.ex?"“"+c.ex+"”":"";
  el.querySelector("#kp").textContent=V.ids.length?`${Math.min(V.i+1,V.ids.length)} / ${V.ids.length}`:"Kelime getirin";
  const bx=[0,1,2,3,4,5].map(b=>D.words.filter(w=>w.box===b).length),mx=Math.max(1,...bx);el.querySelector("#kb").innerHTML=bx.map((n,i)=>`<div class="row" style="gap:10px;margin:5px 0"><span class="mut" style="width:56px;font-size:13px">${i?"Kutu "+i:"Yeni"}</span><div class="bar" style="flex:1;margin:0"><i style="width:${n/mx*100}%"></i></div><b>${n}</b></div>`).join("")}
 function verdict(v){const c=cw();if(!c)return"Önce kelimeleri getirin.";c.seen++;if(v==="yes")c.box=Math.min(5,c.box+1);else if(v==="no")c.box=1;c.due=new Date(Date.now()+(v==="no"?0:BOX[c.box])*864e5).toISOString().slice(0,10);V.i++;V.show=false;save();ui();
  return(v==="yes"?"Harika. ":"Tekrar edeceğiz. ")+(cw()?"Sıradaki: "+cw().w+".":"Bugünkü kelimeler bitti, tebrikler.")}
 function render(e){el=e;e.innerHTML=`<div class="mut" id="kp" style="text-align:center;letter-spacing:.2em;font-size:13px;margin-top:8px"></div><div class="card" style="text-align:center;min-height:240px;display:flex;flex-direction:column;justify-content:center;gap:10px"><div id="kw" class="big" style="font-size:40px">—</div><div id="kt" style="font-size:24px;color:var(--c);min-height:32px"></div><div id="ks" class="mut"></div><div id="ke" class="mut" style="font-style:italic;min-height:40px"></div></div>
  <div class="row" style="justify-content:center"><button class="prim" id="kg">BUGÜNKÜ 10 KELİME</button><button id="ksh">GÖSTER</button><button id="ksp">🔊</button></div>
  <div class="row" style="justify-content:center;margin-top:8px"><button id="kye" style="color:var(--ok)">BİLDİM</button><button id="khd">ZOR</button><button id="kno" style="color:var(--bad)">BİLMEDİM</button><button id="ksk">GEÇ</button></div>
  <div class="card"><h3>Leitner kutuları</h3><div id="kb"></div><div class="mut" style="font-size:13px">Bildikçe kelime üst kutuya çıkar, daha seyrek sorulur. Bilmediğiniz 1. kutuya döner.</div></div>
  <div class="card"><h3>Kelime ekle</h3><div class="row"><input id="nw" placeholder="apple" style="flex:1;min-width:90px"><input id="nt" placeholder="elma" style="flex:1;min-width:90px"><button id="na">EKLE</button></div></div>`;
  const q=s=>e.querySelector(s);q("#kg").onclick=()=>session(10);q("#ksh").onclick=()=>{if(cw()){V.show=true;ui();speak()}};q("#ksp").onclick=speak;q("#kye").onclick=()=>say(verdict("yes"),true);q("#kno").onclick=()=>say(verdict("no"),true);q("#khd").onclick=()=>say(verdict("hard"),true);q("#ksk").onclick=()=>{V.i++;V.show=false;ui()};
  q("#na").onclick=()=>{const a=q("#nw").value.trim(),b=q("#nt").value.trim();if(a&&b){D.words.push({w:a,tr:b,syn:"",ex:"",lang:"en",box:0,due:"",seen:0});save();q("#nw").value=q("#nt").value="";ui()}};ui()}
 function cmd(t,raw){
  if(/(?:^|\s)(getir|başlat|başla|çalışalım)(?=\s|$)/.test(t)&&/kelime/.test(t)){const n=numIn(t.replace(/bugünkü/,""))||10;session(Math.max(1,Math.min(40,n)));return`${V.ids.length} kelime hazır. Anlamı için göster deyin.`}
  if(/kelime ekle/.test(t)){const b=raw.includes(":")?raw.split(":")[1]:raw.replace(/.*kelime ekle\w*/i,""),m=b.match(/\s*(.+?)\s*(?:=|eşittir|eşit)\s*(.+)/)||b.match(/\s*(\S+)\s+(.+)/);if(!m)return"Kelime ekle: apple eşittir elma biçiminde söyleyin.";D.words.push({w:m[1].trim(),tr:m[2].trim(),syn:"",ex:"",lang:"en",box:0,due:"",seen:0});save();ui();return m[1].trim()+" eklendi."}
  if(/istatistik/.test(t)){const b5=D.words.filter(w=>w.box===5).length;return`Kutuda ${D.words.length} kelime var, ${b5} tanesi ezberlendi.`}
  if(!V.ids.length)return"Önce bugünkü kelimelerinizi getirin.";if(!cw())return"Bugünkü kelimeler bitti. Yeniden için kelimeleri getir deyin.";
  if(/(?:^|\s)(göster|anlam\w*|çevir\w*|ne demek)(?=\s|$)/.test(t)){V.show=true;ui();return cw().w+": "+cw().tr+"."}
  if(/(?:^|\s)(bilmedim|yanlış|hatırlamadım)(?=\s|$)/.test(t))return verdict("no");if(/(?:^|\s)(zor|zorlandım)(?=\s|$)/.test(t))return verdict("hard");if(/(?:^|\s)(bildim|doğru|kolay|biliyorum)(?=\s|$)/.test(t))return verdict("yes");
  if(/(?:^|\s)(sonraki|geç|atla)(?=\s|$)/.test(t)){V.i++;V.show=false;ui();return"Geçtim."}return null}
 reg({id:"kelime",name:"Kelime kutusu",icon:"🔤",say:/kelime|sözcük|ezber/,render,cmd});
})();

// ================================================================= HIZLI OKUMA
(function(){
 const TR=["Dünya'nın en derin noktası olan Mariana Çukuru yaklaşık on bir kilometre derinliğindedir. Buraya ışık hiç ulaşmaz ve basınç deniz seviyesindekinin bin katından fazladır. Buna rağmen çukurun dibinde yaşayan küçük canlılar bulunmuştur. Bilim insanları bu canlıların aşırı koşullara nasıl uyum sağladığını inceleyerek yaşamın sınırlarını araştırmaktadır.",
 "Uyku yalnızca dinlenmek değildir. Gece boyunca beyin gün içinde öğrenilen bilgileri düzenler, önemli olanları uzun süreli belleğe aktarır ve gereksiz ayrıntıları temizler. Yeterince uyumayan insanların dikkatini daha zor topladığı birçok araştırmada gösterilmiştir. Bu nedenle önemli bir günden önceki gece uyumak çoğu zaman daha doğru bir tercihtir.",
 "Anadolu'daki Göbeklitepe tarihin bilinen en eski tapınak alanıdır ve yaklaşık on iki bin yıl öncesine uzanır. Dikilitaşlardaki hayvan kabartmaları insanların tarım yapmadan önce bile büyük yapılar kurabildiğini göstermiştir. Bu keşif medeniyetin tarımla başladığı düşüncesini sorgulatmıştır.",
 "Aralıklı tekrar, yeni bir şey öğrenmenin en etkili yollarından biridir. Bir bilgiyi bir kez ezberlemek yerine artan aralıklarla yeniden görmek onun uzun süreli belleğe yerleşmesini sağlar. Günde yirmi dakikalık düzenli çalışma, haftada bir saatlik yoğun çalışmadan genellikle daha verimlidir."];
 const EN=["Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are more than three thousand years old and still perfectly edible. Honey contains very little water and is naturally acidic, so bacteria cannot grow in it.",
 "The human brain uses about twenty percent of the body's energy, even though it makes up only two percent of its weight. Even when we are resting, large parts of the brain stay active, which is why a short walk or a good night's sleep can improve concentration so much.",
 "Cities around the world are trying to become greener. Many of them are planting trees on rooftops, building more bicycle lanes, and replacing diesel buses with electric ones. Experts say these changes make people healthier and happier."];
 let P=DB.get("okuma",{wpm:250,hist:[]}),el=null,words=[],idx=0,tm=null,paused=false,running=false,lang="tr",last=0;const save=()=>DB.set("okuma",P);
 const orp=w=>{const n=w.replace(/[^\p{L}\p{N}]/gu,"").length,i=n<2?0:n<6?1:n<10?2:3;return esc(w.slice(0,i))+'<span style="color:#ff6b5e">'+esc(w[i]||"")+"</span>"+esc(w.slice(i+1))};
 function begin(txt,l){clearTimeout(tm);words=txt.split(/\s+/).filter(Boolean);idx=0;paused=false;running=true;lang=l;last=words.length;if(!el)return;el.querySelector("#kv").style.display="none";el.querySelector("#rz").textContent="⏸ DURAKLAT";
  el.querySelector("#rt").innerHTML=words.map((w,i)=>`<span id="w${i}">${esc(w)}</span>`).join(" ");setTimeout(step,500)}
 function step(){if(paused||!running||!el||!el.isConnected)return;if(idx>=words.length){running=false;el.querySelector("#rw").innerHTML='<span class="mut" style="font-size:18px">Bitti — anlama puanınızı verin</span>';el.querySelector("#kv").style.display="flex";return}
  const w=words[idx];el.querySelector("#rw").innerHTML=orp(w);const a=el.querySelector("#w"+idx),b=el.querySelector("#w"+(idx-1));if(b)b.style.background="";if(a){a.style.background="var(--c)";a.style.color="#02141a";a.style.borderRadius="4px";if(b){b.style.color="";}}
  el.querySelector("#rp").style.width=(idx+1)/words.length*100+"%";let d=60000/P.wpm;if(/[.!?]$/.test(w))d*=2.2;else if(/[,;:]$/.test(w))d*=1.5;else if(w.length>9)d*=1.25;idx++;tm=setTimeout(step,d)}
 function startNew(l){const pool=l==="en"?EN:TR;begin(pool[rnd(pool.length)],l)}
 function setWpm(v){P.wpm=Math.max(80,Math.min(1000,v));save();if(el)el.querySelector("#rv").textContent=P.wpm}
 function pause(p){if(!running)return;paused=p;el&&(el.querySelector("#rz").textContent=p?"▶ DEVAM":"⏸ DURAKLAT");if(!p)step();else clearTimeout(tm)}
 function rate(k){P.hist.push({ts:new Date().toISOString().slice(5,16).replace("T"," "),wpm:P.wpm,words:last,kav:k*20});P.hist=P.hist.slice(-60);save();if(el){el.querySelector("#kv").style.display="none";el.querySelector("#rw").textContent="Kaydedildi";hist()}}
 function hist(){const h=P.hist.slice(-12),mx=Math.max(300,...h.map(x=>x.wpm));el.querySelector("#rh").innerHTML=h.length?h.map(x=>`<div class="row" style="gap:8px;margin:4px 0"><span class="mut" style="width:80px;font-size:12px">${esc(x.ts)}</span><div class="bar" style="flex:1;margin:0"><i style="width:${x.wpm/mx*100}%"></i></div><b style="width:90px;text-align:right;font-size:13px">${x.wpm} · %${x.kav}</b></div>`).join(""):'<span class="mut">Henüz kayıt yok.</span>'}
 function render(e){el=e;e.innerHTML=`<div class="card" style="text-align:center"><div id="rw" style="height:110px;display:flex;align-items:center;justify-content:center;font:500 46px system-ui;color:#fff;white-space:pre"><span class="mut" style="font-size:18px">Başlamak için BAŞLAT'a basın</span></div><div class="bar"><i id="rp" style="width:0"></i></div>
  <div class="row" style="justify-content:center;margin-top:8px"><button id="rm">−25</button><span><b id="rv" style="font-size:24px;color:#fff">${P.wpm}</b> <span class="mut">kelime/dk</span></span><button id="rpl">+25</button></div>
  <div class="row" style="justify-content:center;margin-top:10px"><button class="prim" id="rg">▶ TÜRKÇE</button><button id="rge">▶ ENGLISH</button><button id="rz">⏸ DURAKLAT</button><button id="rf">METİN</button></div>
  <div id="kv" class="row" style="display:none;justify-content:center;margin-top:12px"><span class="mut">Ne kadar anladınız?</span>${[1,2,3,4,5].map(k=>`<button data-k="${k}">${k}</button>`).join("")}</div></div>
  <div id="rt" class="card" style="display:none;line-height:1.9;font-size:17px;max-height:40vh;overflow:auto"></div>
  <div class="card"><h3>Hız ve kavrama geçmişi</h3><div id="rh"></div></div><div class="card"><h3>Kendi metniniz</h3><textarea id="ru" rows="3" placeholder="Metni yapıştırın" style="width:100%"></textarea><button id="rb" style="margin-top:8px">BU METNİ OKU</button></div>`;
  const q=s=>e.querySelector(s);q("#rm").onclick=()=>setWpm(P.wpm-25);q("#rpl").onclick=()=>setWpm(P.wpm+25);q("#rg").onclick=()=>startNew("tr");q("#rge").onclick=()=>startNew("en");q("#rz").onclick=()=>pause(!paused);
  q("#rf").onclick=()=>{const t=q("#rt");t.style.display=t.style.display==="none"?"block":"none"};e.querySelectorAll("#kv button").forEach(b=>b.onclick=()=>rate(+b.dataset.k));
  q("#rb").onclick=()=>{const v=q("#ru").value.trim();if(v)begin(v,"tr")};hist()}
 function cmd(t,raw){const m=t.match(/(\d{2,4})\s*kelime/);
  if(m&&/(?:^|\s)(çıkar|yap|ayarla|olsun)(?=\s|$)/.test(t)){setWpm(+m[1]);return`Okuma hızı dakikada ${P.wpm} kelime.`}
  if(/hızlan|hızlandır/.test(t)){setWpm(P.wpm+25);return`Dakikada ${P.wpm} kelime.`}if(/yavaşla/.test(t)){setWpm(P.wpm-25);return`Dakikada ${P.wpm} kelime.`}
  if(/(?:^|\s)(durdur|duraklat|dur)(?=\s|$)/.test(t)){pause(true);return"Durdurdum."}if(/(?:^|\s)(devam|sürdür)(?=\s|$)/.test(t)){pause(false);return"Devam ediyorum."}
  const k=t.match(/kavrama\s*(\d)/);if(k&&last){rate(Math.min(5,+k[1]));return"Kaydedildi."}
  if(/(?:^|\s)(başlat|başla|paragraf|antrenman\w*|oku)(?=\s|$)/.test(t)){startNew(/ingiliz|english/.test(t)?"en":"tr");return`Başlıyorum, dakikada ${P.wpm} kelime.`}return null}
 reg({id:"okuma",name:"Hızlı okuma",icon:"📖",say:/okuma|paragraf|rsvp/,render,cmd,leave(){clearTimeout(tm);running=false}});
})();

// ================================================================= FİKİR TAHTASI
(function(){
 const COLS=[["sarı","#ffe66d"],["pembe","#ff9fc2"],["mavi","#8fd3ff"],["yeşil","#a6f09a"],["turuncu","#ffb774"],["mor","#d2a8ff"]];
 let D=DB.get("tahta",{notes:[],next:1}),el=null,sel=null;const save=()=>DB.set("tahta",D);
 const place=i=>({x:.04+(i%3)*.32+Math.random()*.02,y:.03+(Math.floor(i/3)%6)*.14+Math.random()*.02});
 function add(text,col){const i=D.next++;const p=place(D.notes.length);D.notes.push({id:i,text:text.slice(0,300),c:col||COLS[rnd(6)][1],x:p.x,y:p.y});save();ui();return i}
 function ui(){if(!el||!el.isConnected)return;const b=el.querySelector("#bd");b.innerHTML="";const W=b.clientWidth,H=b.clientHeight;
  D.notes.forEach(n=>{const d=document.createElement("div");d.style.cssText=`position:absolute;left:${n.x*W}px;top:${n.y*H}px;width:42%;min-height:70px;padding:10px;background:${n.c};color:#2b2208;font:600 14px/1.3 system-ui;border-radius:3px;box-shadow:2px 4px 10px #0007;touch-action:none;word-break:break-word;transform:rotate(${(n.id*37)%5-2}deg)`;
   d.innerHTML=`<span style="position:absolute;top:1px;left:5px;font:700 10px monospace;opacity:.5">${n.id}</span><span class="x" style="position:absolute;top:0;right:6px;font-size:18px;padding:2px 4px;opacity:.6">×</span><div class="t"></div>`;d.querySelector(".t").textContent=n.text;
   d.querySelector(".x").onpointerdown=e=>{e.stopPropagation();D.notes=D.notes.filter(x=>x!==n);save();ui()};
   let sx,sy,ox,oy,mv=false;d.onpointerdown=e=>{if(e.target.classList.contains("x"))return;d.setPointerCapture(e.pointerId);sx=e.clientX;sy=e.clientY;ox=d.offsetLeft;oy=d.offsetTop;mv=false};
   d.onpointermove=e=>{if(!d.hasPointerCapture(e.pointerId))return;const dx=e.clientX-sx,dy=e.clientY-sy;if(Math.abs(dx)+Math.abs(dy)>4)mv=true;d.style.left=Math.max(0,Math.min(W-d.offsetWidth,ox+dx))+"px";d.style.top=Math.max(0,Math.min(H-40,oy+dy))+"px"};
   d.onpointerup=e=>{if(mv){n.x=d.offsetLeft/W;n.y=d.offsetTop/H;save()}else{const t=prompt("Notu düzenle",n.text);if(t!==null&&t.trim()){n.text=t.trim().slice(0,300);save();ui()}}};b.appendChild(d)});
  el.querySelector("#tc").textContent=D.notes.length+" not"}
 function group(){const by={};D.notes.forEach(n=>(by[n.c]=by[n.c]||[]).push(n));const cs=Object.keys(by);cs.forEach((c,gi)=>by[c].forEach((n,r)=>{n.x=.03+gi*(0.94/Math.max(cs.length,1));n.y=.04+r*.13}));save();ui();return cs.length}
 function render(e){el=e;e.innerHTML=`<div class="row" style="margin:6px 0"><input id="tx" placeholder="Yeni fikir…" style="flex:1;min-width:140px"><select id="cl"><option value="">renk</option>${COLS.map(c=>`<option value="${c[1]}">${c[0]}</option>`).join("")}</select><button class="prim" id="ta">EKLE</button></div>
  <div class="row"><button id="tg">RENGE GÖRE AYIR</button><button id="td">TEMİZLE</button><span class="mut" id="tc"></span></div><div id="bd" style="position:relative;height:62vh;margin-top:10px;border-radius:14px;overflow:hidden;border:5px solid #6b4423;background:repeating-linear-gradient(45deg,#8a6038 0 6px,#7e5732 6px 12px)"></div><div class="mut" style="font-size:12px;margin-top:6px">Sürükleyin · dokununca düzenle · × ile sil</div>`;
  const q=s=>e.querySelector(s),go=()=>{const v=q("#tx").value.trim();if(v){add(v,q("#cl").value);q("#tx").value=""}};q("#ta").onclick=go;q("#tx").addEventListener("keydown",ev=>{if(ev.key==="Enter")go()});
  q("#tg").onclick=group;q("#td").onclick=()=>{if(confirm("Tahta temizlensin mi?")){D={notes:[],next:1};save();ui()}};setTimeout(ui,30)}
 function cmd(t,raw){
  if(/(?:^|\s)(tahtayı|panoyu|hepsini)(?=\s|$).*(?:^|\s)(temizle|sil)(?=\s|$)/.test(t)){D={notes:[],next:1};save();ui();return"Tahtayı temizledim."}
  if(/(?:^|\s)(ayır|grupla|kategori\w*)(?=\s|$)/.test(t)&&!/(?:^|\s)ekle(?=\s|$)/.test(t)){return`${group()} renk grubuna ayırdım.`}
  if(/(?:^|\s)(sil|kaldır)(?=\s|$)/.test(t)&&!/(?:^|\s)(ekle|yaz)(?=\s|$)/.test(t)){const n=t.match(/\d+/);if(/(?:^|\s)son(?=\s|$)/.test(t))D.notes.pop();else if(n)D.notes=D.notes.filter(x=>x.id!==+n[0]);else return"Hangi not? Numarasını söyleyin.";save();ui();return"Notu sildim."}
  if(/(?:^|\s)(ekle|yaz|not al)(?=\s|$)/.test(t)){const body=raw.includes(":")?raw.split(":").slice(1).join(":").trim():raw.replace(/.*(?:^|\s)(ekle|yaz)\w*\s*/i,"").trim();if(!body)return"Ne yazayım?";const c=COLS.find(c=>t.split(/ekle|yaz/)[0].includes(c[0]));const i=add(body,c&&c[1]);return`${i} numaralı not eklendi.`}return null}
 reg({id:"tahta",name:"Fikir tahtası",icon:"📌",say:/tahta|post.?it|beyin fırtınası|fikir|nota yaz/,render,cmd});
})();

// ================================================================= DENEME SINAVI (optik form)
(function(){
 const PRE={"tyt türkçe":[40,55],"tyt sosyal":[20,27],"tyt matematik":[40,55],"tyt fen":[20,27],"tyt":[120,165],"ayt matematik":[40,45],"ayt fen":[40,45],"ayt edebiyat":[40,45],"ayt sosyal":[40,45],"ayt":[160,180],"ydt":[80,120]};
 let S=DB.get("optik",{on:false,fin:false,name:"",n:0,dur:0,end:0,ans:{},flag:[],key:"",res:null,hist:[]}),el=null,iv=null;const save=()=>DB.set("optik",S);const LET={a:"A",b:"B",be:"B",c:"C",ce:"C",d:"D",de:"D",e:"E"};
 function start(name,n,dur){S=Object.assign(S,{on:true,fin:false,name,n,dur,end:Date.now()+dur*60000,ans:{},flag:[],key:"",res:null});save();render(el)}
 function score(){let d=0,y=0,b=0;const marks={};for(let q=1;q<=S.n;q++){const a=S.ans[q];if(!a){b++;marks[q]="b"}else if(S.key&&q<=S.key.length){const ok=S.key[q-1]===a;ok?d++:y++;marks[q]=ok?"d":"y"}else marks[q]="?"}
  S.res=S.key?{keyed:true,d,y,b,net:Math.round((d-y/4)*100)/100,marks}:{keyed:false,marked:Object.keys(S.ans).length,b:S.n-Object.keys(S.ans).length,marks};return S.res}
 function finish(){S.on=false;S.fin=true;const r=score();S.hist=(S.hist||[]).concat({ts:new Date().toISOString().slice(5,16).replace("T"," "),ad:S.name,n:S.n,net:r.net,d:r.d,y:r.y}).slice(-30);save();render(el);return r}
 function paint(){if(!el||!el.isConnected)return;const l=S.on?Math.max(0,(S.end-Date.now())/1000):0,m=Math.floor(l/60),s=Math.floor(l%60),h=Math.floor(m/60),t=el.querySelector("#ot");if(!t)return;t.textContent=S.on?(h?h+":":"")+String(m%60).padStart(2,"0")+":"+String(s).padStart(2,"0"):"--:--";t.style.color=S.on&&l<300?"var(--bad)":"#fff";
  const pb=el.querySelector("#op");if(pb)pb.style.width=S.on&&S.dur?l/(S.dur*60)*100+"%":"0";if(S.on&&l<=0){finish();say("Süre doldu, deneme teslim edildi.")}}
 function render(e){el=e;const marks=S.res&&S.res.marks||{};let bub="";
  for(let q=1;q<=S.n;q++){bub+=`<div class="q"><span class="n${S.flag.includes(q)?" fl":""}" data-f="${q}">${q}</span>${["A","B","C","D","E"].map(L=>{let c="b";if(S.ans[q]===L){c+=" on";if(S.fin&&S.res&&S.res.keyed)c=`b ${marks[q]==="d"?"ok":"bad"}`}return`<button class="${c}" data-q="${q}" data-l="${L}">${L}</button>`}).join("")}</div>`}
  const r=S.res;
  e.innerHTML=`<style>.q{display:flex;align-items:center;gap:6px;margin:4px 0}.q .n{width:30px;text-align:right;font:600 12px monospace;color:var(--mut)}.q .n.fl{background:var(--bad);color:#fff;border-radius:4px}.b{width:34px;height:34px;border-radius:50%;padding:0;font:600 13px monospace;color:var(--mut);border:1.5px solid var(--ln);background:transparent}.b.on{background:#fff;color:#02141a}.b.ok{background:var(--ok);color:#fff;border:0}.b.bad{background:var(--bad);color:#fff;border:0}#of{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));column-gap:14px}</style>
   <div class="card"><div class="row sp"><div><div class="mut" style="font-size:12px;letter-spacing:.2em">KALAN SÜRE</div><div id="ot" class="big">--:--</div></div><div style="text-align:right">${S.n?`<b>${esc(S.name)}</b><div class="mut">${Object.keys(S.ans).length}/${S.n} işaretli</div>`:""}</div></div><div class="bar"><i id="op" style="width:0"></i></div>
   <div class="row"><button class="prim" id="oz" ${S.on?"":"disabled"}>SINAVI TESLİM ET</button><button id="oi" ${S.on||S.fin?"":"disabled"}>İPTAL</button></div></div>
   ${S.on||S.fin?"":`<div class="card"><h3>Deneme seç</h3><div class="row" id="opr">${Object.keys(PRE).map(k=>`<button data-k="${k}">${k.toUpperCase()}<br><small class="mut">${PRE[k][0]} soru · ${PRE[k][1]} dk</small></button>`).join("")}</div><div class="row" style="margin-top:10px"><input id="on" type="number" inputmode="numeric" placeholder="soru" style="width:80px"><input id="od" type="number" inputmode="numeric" placeholder="dakika" style="width:90px"><button id="og">ÖZEL BAŞLAT</button></div></div>`}
   ${r?`<div class="card"><h3>${r.keyed?"Sonuç":"Teslim edildi"}</h3>${r.keyed?`<div class="big">NET ${r.net}</div><div class="row sp"><span class="ok">Doğru ${r.d}</span><span class="bad">Yanlış ${r.y}</span><span>Boş ${r.b}</span></div>`:`<div>İşaretlenen ${r.marked}, boş ${r.b}. Net için cevap anahtarını girin.</div>`}</div>`:""}
   ${S.n?`<div class="card"><h3>Cevap anahtarı</h3><div class="row"><input id="ok" placeholder="ABCDE…" value="${esc(S.key)}" style="flex:1" autocapitalize="characters"><button id="ob">NET HESAPLA</button></div></div><div class="card"><h3>Optik form <small class="mut" style="letter-spacing:0">(numaraya uzun bas = turla)</small></h3><div id="of">${bub}</div></div>`:""}
   ${S.hist&&S.hist.length?`<div class="card"><h3>Son denemeler</h3>${S.hist.slice(-6).reverse().map(h=>`<div class="it"><span>${esc(h.ts)} · ${esc(h.ad)}</span><b>${h.net!=null?"net "+h.net:"—"}</b></div>`).join("")}</div>`:""}`;
  const q=s=>e.querySelector(s);e.querySelectorAll("#opr button").forEach(b=>b.onclick=()=>start(b.dataset.k.toUpperCase(),...PRE[b.dataset.k]));
  q("#og")&&(q("#og").onclick=()=>{const n=+q("#on").value,d=+q("#od").value;if(n>0&&d>0)start(n+" soruluk deneme",Math.min(n,200),Math.min(d,300))});
  q("#oz")&&(q("#oz").onclick=()=>{if(S.on)finish()});q("#oi")&&(q("#oi").onclick=()=>{S=Object.assign(S,{on:false,fin:false,n:0,ans:{},flag:[],res:null});save();render(el)});
  q("#ob")&&(q("#ob").onclick=()=>{S.key=q("#ok").value.replace(/[^A-Ea-e]/g,"").toUpperCase();score();if(S.fin&&S.hist.length){const h=S.hist[S.hist.length-1],r=S.res;if(r.keyed){h.net=r.net;h.d=r.d;h.y=r.y}}save();render(el)});
  e.querySelectorAll(".b").forEach(b=>b.onclick=()=>{if(!S.on)return;const qn=+b.dataset.q,L=b.dataset.l;S.ans[qn]===L?delete S.ans[qn]:S.ans[qn]=L;save();render(el)});
  e.querySelectorAll(".n").forEach(n=>{let tt;n.onpointerdown=()=>{tt=setTimeout(()=>{const f=+n.dataset.f;if(S.on){S.flag=S.flag.includes(f)?S.flag.filter(x=>x!==f):S.flag.concat(f);save();render(el)}},500)};n.onpointerup=n.onpointerleave=()=>clearTimeout(tt)});
  clearInterval(iv);iv=setInterval(paint,500);paint()}
 function cmd(t){
  const pre=Object.keys(PRE).sort((a,b)=>b.length-a.length).find(k=>t.includes(k)),m=t.match(/(\d+)\s*soruluk.*?(\d+)\s*(?:dakika|dk)/);
  if(/(?:^|\s)(başlat|başla|çöz)(?=\s|$)/.test(t)&&(pre||m)){if(m)start(m[1]+" soruluk deneme",+m[1],+m[2]);else start(pre.toUpperCase(),...PRE[pre]);return`${S.name} başladı, ${S.n} soru, ${S.dur} dakika. Başarılar.`}
  if(/(?:^|\s)(kalan|ne kadar)(?=\s|$)/.test(t)){if(!S.on)return"Çalışan deneme yok.";return`${Math.floor((S.end-Date.now())/60000)} dakika kaldı.`}
  if(/cevap anahtar/.test(t)){const rest=t.split(/cevap anahtar\w*/)[1]||"",L=[];rest.split(" ").forEach(x=>{if(LET[x])L.push(LET[x]);else if(/^[a-e]{2,}$/.test(x))L.push(...x.toUpperCase())});if(!L.length)return"Cevap anahtarını harflerle söyleyin.";S.key=L.join("");if(S.fin)score();save();render(el);return"Cevap anahtarı kaydedildi."}
  if(/(?:^|\s)(teslim|sınavı bitir|denemeyi bitir)(?=\s|$)/.test(t)){if(!S.on)return"Çalışan deneme yok.";const r=finish();return r.keyed?`${r.d} doğru, ${r.y} yanlış, ${r.b} boş. Netiniz ${r.net}.`:`Teslim edildi, ${r.marked} soru işaretlendi.`}
  const f=t.match(/(\d{1,3})\s*(?:numaralı|\.)?\s*(?:soru\w*)?\s*(işaretle|turla)/);if(f&&S.on){const q=+f[1];S.flag=S.flag.includes(q)?S.flag.filter(x=>x!==q):S.flag.concat(q);save();render(el);return`${q}. soru işaretlendi.`}
  const bo=t.match(/(\d{1,3})\s*(?:numaralı|\.)?\s*(?:soru\w*)?\s*(boş|sil\w*|temizle)/);if(bo&&S.on){delete S.ans[+bo[1]];save();render(el);return`${bo[1]}. soru boş.`}
  const hits=[...t.matchAll(/(\d{1,3})\s*(?:numaralı|\.)?\s*(?:soru\w*)?\s*(?:cevab\w*|şık\w*)?\s*(?:^|\s)(a|b|be|c|ce|d|de|e)(?=\s|$)/g)];
  if(hits.length){if(!S.on)return"Önce bir deneme başlatın.";hits.forEach(h=>{const q=+h[1];if(q>=1&&q<=S.n)S.ans[q]=LET[h[2]]});save();render(el);return hits.map(h=>h[1]+" "+LET[h[2]]).join(", ")+" işaretlendi."}return null}
 reg({id:"optik",name:"Deneme sınavı",icon:"🎯",say:/deneme|optik|sınav|tyt|ayt|ydt/,render,cmd,leave(){clearInterval(iv)}});
})();
