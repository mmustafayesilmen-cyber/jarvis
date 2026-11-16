/* Jarvis Cep servis çalışanı: uygulama dosyalarını önbelleğe alır, internetsiz de açılır. Hava/kur istekleri önbelleğe alınmaz. */
const V="jv-cep-11",F=["./","index.html","core.js","modes1.js","modes2.js","modes3.js","modes4.js","modes5.js","modes6.js","modes7.js","modes8.js","modes9.js","modes10.js","modes11.js","modes12.js","data/lab.json","data/sky.json","data/diger.json","data/tarif.json","manifest.webmanifest","icon-192.png","icon-512.png"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(F)).then(()=>self.skipWaiting()))});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==V).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",e=>{const u=new URL(e.request.url);if(e.request.method!=="GET"||u.origin!==location.origin)return;
 e.respondWith(fetch(e.request).then(r=>{const c=r.clone();caches.open(V).then(x=>x.put(e.request,c));return r}).catch(()=>caches.match(e.request).then(m=>m||caches.match("index.html"))))});
