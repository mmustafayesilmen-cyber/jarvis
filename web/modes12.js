"use strict";
/* Mod 12: MEBİ takibi. Herkes KENDİ MEBİ hesabını kullanır: bu sayfa MEBİ'nin içini okuyamaz (farklı site), bu yüzden MEBİ sekmesinde çalışan küçük bir
   yer imi (bookmarklet) sayfayı PASİF okur ve yalnızca bu Jarvis Cep sekmesine postMessage ile yollar. Hiçbir şey sunucuya gitmez, tıklama yapılmaz,
   şifre okunmaz/saklanmaz; kayıtlar yalnızca bu tarayıcının localStorage'ında (jv:mebi). Komut kalıplarında \b KULLANMAYIN. */
(function(){
const HOST="mebi.eba.gov.tr",GUID="[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",PAGE=new RegExp("^/student/(section/subject-details|interactive-quiz|quiz)/("+GUID+")$");
const MAXT=500,MAXEV=60,POLL=5;
let el=null,listening=false,lastMsg=0,sess=null;

/* ---- MEBİ sekmesinde çalışan okuyucu (masaüstündeki mebi.POLL_JS ile aynı mantık, yalnızca okur) ---- */
const READER=`(function(){var T=__ORIGIN__;if(location.hostname!=='${HOST}'){alert('Bu yer imi yalnızca ${HOST} sayfasında çalışır.');return}
if(window.__jvm){alert('Jarvis MEBİ takibi zaten açık.');return}window.__jvm=1;
var op=window.opener||null;
function send(m){try{if(op&&!op.closed)op.postMessage(m,T)}catch(e){}}
var b=document.createElement('div');b.style.cssText='position:fixed;right:8px;bottom:8px;z-index:2147483647;font:12px sans-serif;background:#0b1620;color:#7fe3ff;border:1px solid #2a6;padding:4px 8px;border-radius:8px;opacity:.85';b.textContent='Jarvis ● bağlanıyor';document.body.appendChild(b);
function poll(){try{var fr=document.getElementById('mainFrame'),w=window;if(fr){try{w=fr.contentWindow;w.document}catch(e){w=window}}var d=w.document;
if(!w.__jv){w.__jv={q:[]};var q=w.__jv.q,push=function(o){o.t=Date.now();if(q.length<150)q.push(o)},P=w.XMLHttpRequest.prototype,XO=P.open,XS=P.send;
P.open=function(m,u){this.__m=m;this.__u=String(u);return XO.apply(this,arguments)};
P.send=function(bd){var x=this;if(x.__m&&String(x.__m).toUpperCase()==='POST'&&x.__u.indexOf('/student/')>=0&&!/kanka|ai-send|stay-fit|feedback|review/.test(x.__u)){x.addEventListener('loadend',function(){push({k:'post',u:x.__u.split('?')[0].slice(0,80),b:(typeof bd==='string'?bd:'').slice(0,300),r:(x.responseText||'').slice(0,/get-student-subject|video-app-list/.test(x.__u)?2000:200)})})}return XS.apply(this,arguments)};
d.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a,button');if(!a)return;push({k:'click',x:(a.innerText||'').trim().slice(0,40),o:(a.getAttribute('onclick')||'').slice(0,30)})},true)}
var cr=[].map.call(d.querySelectorAll('.breadcrumb li,.breadcrumb-item'),function(e){return e.innerText.trim()}).filter(Boolean);
var vs=[].map.call(d.querySelectorAll('video'),function(v){return{t:Math.round(v.currentTime),d:Math.round(v.duration||0),p:v.paused,e:v.ended}}).slice(0,3);var J=w.__jv;
if(!J.kzDone&&/subject-details/.test(w.location.pathname)&&d.body){J.kzDone=1;J.kz=[];J.an=[];var bc=d.body.cloneNode(true);[].forEach.call(bc.querySelectorAll('script,style'),function(e){e.remove()});
var seen={};(bc.textContent.match(/[A-ZÇĞİÖŞÜ]{2,5}\\.\\d+\\.\\d+\\.\\d+\\.\\s+[^\\n\\r]{12,170}/g)||[]).forEach(function(s){var c=s.replace(/\\s+/g,' ').trim();if(/Kapat$/.test(c))return;var k=c.slice(0,12);if(!seen[k]){seen[k]=1;J.kz.push(c)}});
[].forEach.call(d.querySelectorAll('[onclick*="App("]'),function(a){var n=(a.textContent||'').replace(/\\s+/g,' ').trim();if(n&&J.an.indexOf(n)<0)J.an.push(n)})}
send({jvMebi:1,p:{path:w.location.pathname,crumbs:cr,v:vs,ev:J.q.splice(0),kz:J.kz||[],an:J.an||[]}});if(op&&!op.closed)b.textContent='Jarvis ● izleniyor'}catch(e){b.textContent='Jarvis ● okuma hatası'}}
if(!op){b.textContent='Jarvis ● Jarvis Cep sekmesi yok: MEBİ’yi Jarvis Cep’ten açın';b.style.color='#fa6'}
send({jvMebi:1,hello:1});poll();setInterval(poll,${POLL*1000})})()`;
function bookmarklet(){return "javascript:"+encodeURIComponent(READER.replace("__ORIGIN__",JSON.stringify(location.origin)).replace(/\n/g,""))}

/* ---- kayıt (masaüstündeki mebi.ingest / _apply_event'in birebir karşılığı) ---- */
const S=()=>{const d=DB.get("mebi",null);return d&&d.topics?d:{last:"",topics:{}}};
const newT=()=>({ders:"",unite:"",konu:"",t:0,watch_s:0,pct:0,video:false,ozet:false,podcast:false,acts:0,clicks:0,quiz_seen:false,hazir_seen:false,ev:[],view_s:0,dur:0,apps:[],act_done:[],pend:"",kaz:[],act_names:[]});
const cut=(v,n=120)=>String(v==null?"":v).trim().slice(0,n);
function applyEv(tp,e){
 if(e.k==="click"){tp.clicks++;if(/^show\w*App\(/.test(cut(e.o,40)))tp.pend=cut(e.x,60);return""}
 const u=cut(e.u,80);
 if(u.includes("get-student-subject")){let r;try{r=JSON.parse(e.r||"")}catch(x){return""}let got="";
  if(r&&typeof r==="object"){[["video","video"],["summary","ozet"],["podcast","podcast"]].forEach(([a,b])=>{if(r[a]===true&&!tp[b]){tp[b]=true;got=b}});
   if(typeof r.viewingTime==="number")tp.view_s=Math.max(tp.view_s,Math.floor(r.viewingTime))}return got}
 if(u.includes("video-app-list")){let r;try{r=JSON.parse(e.r||"")}catch(x){return""}if(Array.isArray(r))tp.apps=r.slice(0,20).filter(a=>a&&typeof a==="object").map(a=>({n:cut(a.name,60),s:cut(a.startTime,8)}));return""}
 if(/list|update-viewing-time/.test(u))return"";
 let got="";
 if(u.includes("save-video")){got=tp.video?"":"video";tp.video=true}
 else if(u.includes("save-summary")){got=tp.ozet?"":"ozet";tp.ozet=true}
 else if(u.includes("save-podcast")){got=tp.podcast?"":"podcast";tp.podcast=true}
 else if(/save|score|complet/.test(u)){const m=cut(e.b,400).match(/([0-9a-f]{8})-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/),aid=m?m[1]:cut(e.t);
  if(!tp.act_done.some(a=>a.id===aid)&&tp.act_done.length<100){tp.act_done.push({id:aid,n:tp.pend||"",u:u.split("/").pop().slice(0,30)});tp.acts=tp.act_done.length;got="etkinlik"}tp.pend=""}
 tp.ev=tp.ev.concat([{t:Math.floor((e.t||0)/1000),u:u.split("/").pop().slice(0,40)}]).slice(-MAXEV);return got}
const NAME={video:"konu anlatım videosu",ozet:"özet",podcast:"podcast",etkinlik:"bir etkinlik"};
function ingest(p){if(!p||typeof p!=="object"||p.off||p.err)return[];const m=PAGE.exec(cut(p.path,200));if(!m)return[];
 const kind=m[1],guid=m[2],d=S();if(!d.topics[guid]){if(Object.keys(d.topics).length>=MAXT)return[];d.topics[guid]=newT()}
 const tp=Object.assign(newT(),d.topics[guid]),cr=[];(Array.isArray(p.crumbs)?p.crumbs:[]).forEach(c=>{c=cut(c);if(c&&!cr.includes(c))cr.push(c)});
 if(kind==="section/subject-details"&&cr.length>=6){tp.ders=cr[3];tp.unite=cr[4];tp.konu=cr[5]}
 if(kind==="interactive-quiz")tp.quiz_seen=true;else if(kind==="quiz")tp.hazir_seen=true;
 (Array.isArray(p.v)?p.v:[]).slice(0,1).forEach(v=>{if(v&&v.d>0){if(!v.p&&!v.e)tp.watch_s+=Math.min(POLL,10);tp.pct=Math.max(tp.pct,Math.min(100,Math.round(100*(v.t||0)/v.d)));tp.dur=Math.floor(v.d)}});
 const kz=[];(Array.isArray(p.kz)?p.kz:[]).slice(0,12).forEach(s=>{const x=/^([A-ZÇĞİÖŞÜ]{2,5}\.\d+\.\d+\.\d+)\.\s+(.{12,170})$/.exec(cut(s,200));if(x)kz.push({kod:x[1],ad:x[2]})});
 if(kz.length&&kind==="section/subject-details")tp.kaz=kz;
 const an=(Array.isArray(p.an)?p.an:[]).slice(0,30).map(x=>cut(x,70)).filter(Boolean);if(an.length&&kind==="section/subject-details")tp.act_names=an;
 const miles=[];(Array.isArray(p.ev)?p.ev:[]).slice(0,150).forEach(e=>{if(e&&typeof e==="object"){const g=applyEv(tp,e);if(g)miles.push(g)}});
 tp.t=Math.floor(Date.now()/1000);d.topics[guid]=tp;d.last=guid;DB.set("mebi",d);return miles}

function describe(tp){const name=tp.konu||"son konunuz",done=[],left=[];
 if(tp.video)done.push("konu anlatım videosu");else{const mins=Math.floor((tp.view_s||0)/60);left.push("konu anlatım videosu"+(mins?` (${mins} dakikası izlendi`+(tp.dur?`, toplam ${Math.round(tp.dur/60)} dakika`:"")+")":""))}
 (tp.ozet?done:left).push("özet");if(tp.acts)done.push(tp.acts+" etkinlik");else left.push("etkinlikler");(tp.quiz_seen?done:left).push("değerlendirme soruları");
 let s=name+": ";if(done.length)s+="kayıtlarıma göre "+done.join(", ")+" tamam";if(left.length)s+=(done.length?"; ":"kayıtlarımda ")+left.join(", ")+(done.length?" kaldı":" yok");return s+"."}

function onMsg(ev){if(ev.origin!=="https://"+HOST)return;const d=ev.data;if(!d||d.jvMebi!==1)return;sess=ev.source;lastMsg=Date.now();
 if(d.hello){try{sess.postMessage({jvMebi:1,ack:1},ev.origin)}catch(e){}}
 else{const miles=ingest(d.p);if(miles.length&&typeof say==="function")say("Kaydettim: "+miles.map(x=>NAME[x]||x).join(", ")+".",false)}
 if(el&&el.isConnected)draw()}
function listen(){if(!listening){listening=true;window.addEventListener("message",onMsg)}}
listen();   /* mod açık olmasa da MEBİ sekmesinden gelen veriyi kaydeder */

function bar(p){return`<div style="height:6px;background:#1a2a36;border-radius:3px;overflow:hidden"><div style="height:6px;width:${p}%;background:var(--acc,#00e5ff)"></div></div>`}
function draw(){const box=el.querySelector("#mb"),d=S(),ids=Object.keys(d.topics).sort((a,b)=>d.topics[b].t-d.topics[a].t),on=Date.now()-lastMsg<15000;
 el.querySelector("#st").innerHTML=on?'<span style="color:var(--ok,#4f4)">● MEBİ sekmesi bağlı, izleniyor</span>':'<span class="mut">○ MEBİ sekmesi bağlı değil</span>';
 box.innerHTML=ids.length?ids.map(g=>{const t=d.topics[g],ok=x=>x?"✓":"–";return`<div class="card"><div style="font-size:12px;color:var(--mut)">${esc(t.ders)} › ${esc(t.unite)}</div><b>${esc(t.konu||"Konu")}</b>
  <div style="margin:6px 0">${bar(t.video?100:t.pct)}<span class="mut" style="font-size:12px">Video %${t.video?100:t.pct}${t.video?" (tamam)":""}</span></div>
  <div class="row" style="font-size:13px"><span>Video ${ok(t.video)}</span><span>Özet ${ok(t.ozet)}</span><span>Etkinlik ${t.acts}${t.act_names&&t.act_names.length?"/"+t.act_names.length:""}</span><span>Değerlendirme ${ok(t.quiz_seen)}</span></div>
  ${t.kaz&&t.kaz.length?`<details style="margin-top:6px"><summary class="mut" style="font-size:12px">Kazanımlar (${t.kaz.length})</summary>${t.kaz.map(k=>`<div style="font-size:12px">${esc(k.kod)} ${esc(k.ad)}</div>`).join("")}</details>`:""}</div>`}).join(""):'<div class="card mut">Henüz kayıt yok. Aşağıdaki adımları izleyin.</div>'}
function render(e){el=e;const bm=bookmarklet();
 e.innerHTML=`<div class="card"><div id="st"></div><div class="row" style="margin-top:8px"><button class="prim" id="op">MEBİ'Yİ AÇ</button><button id="cl">KAYITLARI SİL</button></div></div>
 <div id="mb"></div>
 <div class="card"><h3>Nasıl çalışır?</h3><ol style="padding-left:18px;margin:6px 0;font-size:14px;line-height:1.5">
  <li>Önce yer imini kurun (bir kez): bu düğmeyi yer imleri çubuğuna sürükleyin: <a id="bk" href="${bm.replace(/"/g,"&quot;")}" style="display:inline-block;padding:4px 10px;border:1px solid var(--acc,#0ee);border-radius:8px" onclick="return false">Jarvis MEBİ</a>
   <br><span class="mut" style="font-size:12px">Telefonda sürükleme olmaz: <button id="cp">YER İMİ KODUNU KOPYALA</button>, yeni bir yer imi oluşturup adres olarak yapıştırın.</span></li>
  <li><b>MEBİ'Yİ AÇ</b> ile MEBİ'yi bu sayfadan açın ve <b>kendi hesabınızla</b> girin.</li>
  <li>MEBİ açıkken yer imine dokunun. Sağ altta “Jarvis ● izleniyor” görünür; konular burada birikir.</li></ol>
  <div class="mut" style="font-size:12px;line-height:1.5">Gizlilik: şifrenizi hiç okumaz. Giriş sayfasında çalışmaz. Hiçbir şeye tıklamaz, MEBİ'ye bir şey göndermez; yalnızca sayfada görünen durumu okur. Kayıtlar yalnızca bu tarayıcıda durur, hiçbir sunucuya gitmez. MEBİ'nin yapısı değişirse okuma bozulabilir. Bu bir deneme sürümüdür.</div></div>`;
 const q=s=>e.querySelector(s);
 q("#op").onclick=()=>{window.open("https://"+HOST+"/student/home/content","_blank")};   /* noopener YOK: yer imi bu sekmeye geri yazabilsin */
 q("#cl").onclick=()=>{if(confirm("Tüm MEBİ kayıtları silinsin mi?")){DB.set("mebi",{last:"",topics:{}});draw()}};
 q("#cp").onclick=async()=>{try{await navigator.clipboard.writeText(bm);q("#cp").textContent="KOPYALANDI"}catch(x){prompt("Bu kodu kopyalayın:",bm)}};
 draw();el._t=setInterval(()=>{if(!el.isConnected)clearInterval(el._t);else draw()},4000)}
function cmd(t){const d=S(),g=d.last,tp=g&&d.topics[g];
 if(/(nerede kald|son konu|durum|ne yapt|kald[ıi]m)/.test(t)||/^meb[iı]$/.test(t.trim())){return tp?describe(tp):"MEBİ'den henüz kayıt almadım. MEBİ'yi buradan açıp yer imine dokunun."}
 if(/(a[cç]|başlat|git)/.test(t)){window.open("https://"+HOST+"/student/home/content","_blank");return"MEBİ'yi yeni sekmede açtım. Girdikten sonra yer imine dokunun."}
 if(/(sil|temizle)/.test(t)){return"Kayıtları silmek için sayfadaki KAYITLARI SİL düğmesini kullanın."}
 return null}
reg({id:"mebi",name:"MEBİ takibi",icon:"🎓",say:/meb[iı]/,render,cmd});
})();
