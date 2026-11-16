// GX Shield arka plan servisi: sayaç, rozet, site istisnaları, genel açma/kapama.

const DNR = chrome.declarativeNetRequest;
const counts = {}; // tabId -> engellenen istek sayısı
let total = 0;

async function load() {
  const s = await chrome.storage.local.get({ total: 0, enabled: true });
  total = s.total;
  return s;
}
load();

function hostOf(url) {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return null; }
}

function setBadge(tabId) {
  const n = counts[tabId] || 0;
  chrome.action.setBadgeBackgroundColor({ tabId, color: '#fa1e4e' });
  chrome.action.setBadgeText({ tabId, text: n ? (n > 999 ? '999+' : String(n)) : '' });
}

// Not: onRuleMatchedDebug yalnızca "paketlenmemiş" (geliştirici modu) uzantılarda çalışır.
if (DNR.onRuleMatchedDebug) {
  DNR.onRuleMatchedDebug.addListener((info) => {
    const tabId = info.request.tabId;
    if (tabId < 0) return;
    counts[tabId] = (counts[tabId] || 0) + 1;
    total++;
    setBadge(tabId);
    if (total % 10 === 0) chrome.storage.local.set({ total });
  });
}

chrome.tabs.onUpdated.addListener((tabId, change) => {
  if (change.status === 'loading' && change.url) { counts[tabId] = 0; setBadge(tabId); }
});
chrome.tabs.onRemoved.addListener((tabId) => { delete counts[tabId]; });

// Site istisnası: o sitede tüm engellemeyi kapatır (dinamik "allowAllRequests" kuralı).
function ruleIdFor(host) {
  let h = 0;
  for (const c of host) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return 1000 + (h % 1000000);
}

async function setSiteAllowed(host, allowed) {
  const id = ruleIdFor(host);
  const add = allowed ? [{
    id, priority: 100,
    action: { type: 'allowAllRequests' },
    condition: { requestDomains: [host], resourceTypes: ['main_frame', 'sub_frame'] }
  }] : [];
  await DNR.updateDynamicRules({ removeRuleIds: [id], addRules: add });
  const { allowlist = [] } = await chrome.storage.local.get('allowlist');
  const next = allowed ? [...new Set([...allowlist, host])] : allowlist.filter((x) => x !== host);
  await chrome.storage.local.set({ allowlist: next });
}

async function setEnabled(on) {
  await DNR.updateEnabledRulesets(on ? { enableRulesetIds: ['ads'] } : { disableRulesetIds: ['ads'] });
  await chrome.storage.local.set({ enabled: on });
}

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  (async () => {
    if (msg.type === 'state') {
      const s = await chrome.storage.local.get({ enabled: true, allowlist: [], total: 0 });
      const host = hostOf(msg.url);
      reply({
        enabled: s.enabled,
        host,
        allowed: host ? s.allowlist.includes(host) : false,
        blocked: counts[msg.tabId] || 0,
        total: Math.max(total, s.total)
      });
    } else if (msg.type === 'toggleSite') {
      await setSiteAllowed(msg.host, msg.allowed);
      reply({ ok: true });
    } else if (msg.type === 'toggleAll') {
      await setEnabled(msg.enabled);
      reply({ ok: true });
    }
  })();
  return true;
});
