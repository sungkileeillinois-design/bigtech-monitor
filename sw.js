const CACHE='bigtech-monitor-v1';
const CORE=['./','./index.html','./manifest.webmanifest','./icon-192.png','./icon-512.png'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(CORE)));self.skipWaiting()});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('fetch',event=>{if(event.request.method!=='GET')return;
 const req=event.request; if(req.mode==='navigate'||req.url.includes('updates.json')){
  event.respondWith(fetch(req).then(res=>{if(res.ok){const c=res.clone();caches.open(CACHE).then(cache=>cache.put(req,c))}return res}).catch(()=>caches.match(req).then(res=>res||caches.match('./index.html'))));
 }else{event.respondWith(caches.match(req).then(res=>res||fetch(req)))}
});
