"use strict";
/* Jarvis Cep — çekirdek: depolama (yalnızca bu telefonda localStorage), mod kaydı, sesle komut (tarayıcının kendi konuşma tanıma/sentezi), yönlendirme.
   Hiçbir veri sunucuya gönderilmez; komut metni saklanmaz. */
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const DB={get(k,d){try{const v=localStorage.getItem("jv:"+k);return v==null?d:JSON.parse(v)}catch(e){return d}},set(k,v){try{localStorage.setItem("jv:"+k,JSON.stringify(v))}catch(e){}}};
const norm=s=>String(s).replace(/İ/g,"i").replace(/I/g,"ı").toLowerCase().replace(/[^\wçğıöşü%\s]/g," ").replace(/\s+/g," ").trim();
const rnd=n=>Math.floor(Math.random()*n);
const MODES=[];const reg=m=>MODES.push(m);let cur=null,speakOn=DB.get("speak",true),logT;
const NUMW={sıfır:0,bir:1,iki:2,üç:3,dört:4,beş:5,altı:6,yedi:7,sekiz:8,dokuz:9,on:10,yirmi:20,otuz:30,kırk:40,elli:50,altmış:60,yetmiş:70,seksen:80,doksan:90,yüz:100};
function numIn(t){const m=t.match(/\d+/);if(m)return +m[0];const w=t.split(" ").filter(x=>x in NUMW);return w.length&&w.length<=3?w.reduce((a,x)=>a+NUMW[x],0):null}

/* Ses: bilgisayardaki Jarvis'in sesine (tr-TR-AhmetNeural, hafif yavaş ve kalın) en yakın tarayıcı sesini seçer. Edge'de "Ahmet" tam eşleşir; diğer tarayıcılarda sistemdeki en iyi Türkçe erkek ses. */
const VF=/emel|yelda|filiz|female|kad[ıi]n|zira|hazel|google/i,VP={Ultron:[-14,-32],Friday:[3,0],Luna:[-6,22]};
function pickVoice(fem){let v=[];try{v=speechSynthesis.getVoices().filter(x=>/^tr/i.test(x.lang))}catch(e){}if(!v.length)return null;
 const sc=x=>(/ahmet/i.test(x.name)?100:0)+(/online|natural|neural/i.test(x.name)?20:0)+(fem?(/emel|yelda|female|kad[ıi]n/i.test(x.name)?50:0):(VF.test(x.name)?-30:10))+(x.localService?0:1);
 return v.sort((a,b)=>sc(b)-sc(a))[0]}
function voiceFor(u){let n="Jarvis";try{n=AI.personaName()}catch(e){}const t=VP[n]||[-4,-6],fem=n==="Friday"||n==="Luna",v=pickVoice(fem);if(v){u.voice=v;u.lang=v.lang}
 u.rate=Math.max(.5,Math.min(1.5,1+t[0]/100));u.pitch=Math.max(.3,Math.min(2,1+t[1]/100*(Math.abs(t[1])>10?.6:1)))}
try{speechSynthesis.getVoices();speechSynthesis.onvoiceschanged=()=>{}}catch(e){}
function say(t,quiet){if(!t)return;$("#log").textContent="Jarvis: "+t;clearTimeout(logT);logT=setTimeout(()=>{$("#log").textContent=""},7000);   // yanıt satırı kısa süre sonra silinir
 if(speakOn&&!quiet&&"speechSynthesis"in window){try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(t);u.lang="tr-TR";voiceFor(u);speechSynthesis.speak(u)}catch(e){}}}
function beep(f=880,ms=180,vol=.15){try{const a=new (window.AudioContext||window.webkitAudioContext)(),o=a.createOscillator(),g=a.createGain();o.frequency.value=f;g.gain.value=vol;o.connect(g);g.connect(a.destination);o.start();o.stop(a.currentTime+ms/1000);setTimeout(()=>a.close(),ms+200)}catch(e){}}
function buzz(p){try{navigator.vibrate&&navigator.vibrate(p)}catch(e){}}

function home(){cur&&cur.leave&&cur.leave();cur=null;location.hash="";$("#title").textContent="Jarvis Cep";$("#back").style.display="none";
 $("#view").innerHTML=`<div class="card"><h3>Merhaba</h3><div class="mut" style="font-size:14px;line-height:1.5">Bir mod seçin ya da 🎤'a basıp “çarkı çevir”, “harcama ekle kitap 150”, “10 dakika zamanlayıcı” gibi söyleyin. Her şey yalnızca bu telefonda kalır.</div></div>
 <div class="grid">${MODES.map(m=>`<button class="tile" data-id="${m.id}"><i>${m.icon}</i>${esc(m.name)}</button>`).join("")}</div><div id="hint" class="card"></div>
 <div id="apk" class="card" style="display:none"><h3>Android uygulaması</h3><div class="mut" style="font-size:14px;line-height:1.5;margin-bottom:10px"><b style="color:#fff">Jarvis Tarayıcı</b>: kendi sekmeleri ve reklam engelleyicisi olan, telefonda tek başına çalışan tarayıcı. Chrome'dan bağımsızdır; geçmişi ve çerezleri yalnızca bu uygulamada kalır.</div>
 <a class="btn prim" href="Jarvis-Tarayici.apk" download style="display:block;text-align:center;text-decoration:none;color:#02141a;padding:13px">UYGULAMAYI İNDİR (80 KB)</a>
 <div class="mut" style="font-size:12px;line-height:1.5;margin-top:10px">İndirince açın; Android “bilinmeyen kaynaklardan yükleme” izni isteyebilir. Uygulama Play Store dışında dağıtıldığı için bu uyarı normaldir; yalnızca güvendiğiniz birinden aldıysanız kurun.</div></div>`;
 $("#view").querySelectorAll(".tile").forEach(b=>b.onclick=()=>openMode(b.dataset.id));installHint();if(/android/i.test(navigator.userAgent))$("#apk").style.display="block"}
function openMode(id){const m=MODES.find(x=>x.id===id);if(!m)return home();cur&&cur.leave&&cur.leave();cur=m;location.hash=id;$("#title").textContent=m.name;$("#back").style.display="";
 $("#view").innerHTML="";const el=document.createElement("div");$("#view").appendChild(el);m.render(el);$("#view").scrollTop=0}
// komutu en uzun eşleşen modun alanına yönlendirir; açık mod komutu da anlıyorsa onda kalır
const bestMode=t=>{let b=null,bl=0;MODES.forEach(m=>{const x=m.say.exec(t);if(x&&x[0].length>bl){b=m;bl=x[0].length}});
 if(!b)MODES.forEach(m=>{const x=m.weak&&m.weak.exec(t);if(x&&x[0].length>bl){b=m;bl=x[0].length}});return b};     // 'weak': yalnızca başka hiçbir mod eşleşmezse (örn. 'N dakika')
function route(raw){const t=norm(raw);if(!t)return;
 if(/^(ana ekran|ana menü|ana sayfa|geri|çık|kapat|menü)$/.test(t)){home();return}
 if(/^(sesi|sesli yanıt)(?=\s|$).*(?:^|\s)(kapat|kıs|sustur)(?=\s|$)|^sus$/.test(t)){setSpeak(false);return}
 if(/^(sesi|sesli yanıt)(?=\s|$).*(?:^|\s)aç(?=\s|$)/.test(t)){setSpeak(true);return}
 const bm=bestMode(t);
 if(bm&&(!cur||bm!==cur)&&t.split(" ").length<=4&&/(?:^|\s)(aç|git|göster|başlat|modu|moduna|ekranı)(?=\s|$)/.test(t)&&!/\d/.test(t)){openMode(bm.id);const r=/(başlat|başla|çöz|çevir|getir)/.test(t)&&bm.cmd?bm.cmd(t,raw):null;say(r&&r!==" "?r:bm.name+" açıldı.",!r);return}
 let m=cur;if(!cur||(!cur.sticky&&bm&&bm!==cur&&!cur.say.test(t)))m=bm||cur;const sw=m&&m!==cur;if(sw)openMode(m.id);
 const rest=()=>{if(window.__labFind){const a=window.__labFind(t);if(a){say(a);return}}      // ‘atom nedir’ gibi ders kavramları: yerleşik laboratuvar bilgisi
  if(sw){say(m.name+" açıldı.",true);return}
  if(typeof AI!=="undefined"&&AI.on()){AI.quick(raw);return}      // hiçbir mod anlamadıysa ve kullanıcı yapay zekâyı onayladıysa: sohbet cevabı
  say(cur?"Anlayamadım. Modun düğmelerini kullanabilir ya da başka bir şekilde söyleyebilirsiniz. Yapay zekâ cevabı için Sohbet modunu açıp onaylayın.":"Anlayamadım. Bir mod adı söyleyin, örneğin çark ya da bütçe; serbest sorular için Sohbet modunu açın.")};
 if(m&&m.cmd){const r=m.cmd(t,raw);
  if(r&&typeof r.then==="function"){r.then(v=>{if(v&&v!==" ")say(v);else if(!v)rest()}).catch(()=>rest());return}
  if(r){if(r!==" ")say(r);return}}
 rest()}
function setSpeak(v){speakOn=v;DB.set("speak",v);$("#spk").classList.toggle("on",v);$("#spk").textContent=v?"🔊":"🔇";if(!v)try{speechSynthesis.cancel()}catch(e){}}

// ---- sesle komut (tarayıcının konuşma tanıması; Android Chrome/Edge/Samsung, iOS Safari 14.5+ destekler) ----
let rec=null,recOn=false;const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
function mic(){if(!SR){say("Bu tarayıcı sesle komutu desteklemiyor, yazarak kullanabilirsiniz.",true);return}
 if(recOn){try{rec.stop()}catch(e){}return}
 rec=new SR();rec.lang="tr-TR";rec.interimResults=false;rec.maxAlternatives=1;
 rec.onstart=()=>{recOn=true;$("#mic").classList.add("rec")};rec.onend=()=>{recOn=false;$("#mic").classList.remove("rec")};
 rec.onerror=e=>{recOn=false;$("#mic").classList.remove("rec");if(e.error==="not-allowed")say("Mikrofon izni verilmedi.",true)};
 rec.onresult=e=>{const t=e.results[0][0].transcript;route(t)};try{rec.start()}catch(e){}}

// ---- uygulama olarak yükle ----
let dp=null;addEventListener("beforeinstallprompt",e=>{e.preventDefault();dp=e;installHint()});
function installHint(){const h=$("#hint");if(!h)return;const standalone=matchMedia("(display-mode: standalone)").matches||navigator.standalone;if(standalone)return;
 const ios=/iphone|ipad|ipod/i.test(navigator.userAgent);
 if(dp){h.style.display="block";h.innerHTML=`<h3>Uygulama olarak yükle</h3><div class="mut" style="font-size:14px;margin-bottom:10px">Ana ekranınıza eklenir, internetsiz de çalışır.</div><button class="prim" id="inst">YÜKLE</button>`;$("#inst").onclick=async()=>{dp.prompt();await dp.userChoice;dp=null;h.style.display="none"}}
 else if(ios){h.style.display="block";h.innerHTML=`<h3>Ana ekrana ekle</h3><div class="mut" style="font-size:14px">Safari'de Paylaş ⬆ düğmesi → “Ana Ekrana Ekle”.</div>`}}

function start(){$("#spk").onclick=()=>setSpeak(!speakOn);setSpeak(speakOn);$("#mic").onclick=mic;$("#back").onclick=home;
 const go=()=>{const v=$("#cmd").value;$("#cmd").value="";route(v)};$("#go").onclick=go;$("#cmd").addEventListener("keydown",e=>{if(e.key==="Enter")go()});
 const h=location.hash.slice(1);MODES.find(m=>m.id===h)?openMode(h):home();
 if("serviceWorker"in navigator&&location.protocol.startsWith("http"))navigator.serviceWorker.register("sw.js").catch(()=>{})}
