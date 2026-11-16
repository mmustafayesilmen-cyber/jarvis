const $ = (id) => document.getElementById(id);

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const st = await chrome.runtime.sendMessage({ type: 'state', tabId: tab.id, url: tab.url });

  $('blocked').textContent = st.blocked;
  $('total').textContent = st.total.toLocaleString('tr-TR');
  $('all').checked = st.enabled;
  $('host').textContent = st.host || 'Bu sayfada kullanılamaz';
  $('site').checked = !st.allowed;
  $('site').disabled = !st.host;

  $('all').onchange = async (e) => {
    await chrome.runtime.sendMessage({ type: 'toggleAll', enabled: e.target.checked });
    chrome.tabs.reload(tab.id);
  };
  $('site').onchange = async (e) => {
    await chrome.runtime.sendMessage({ type: 'toggleSite', host: st.host, allowed: !e.target.checked });
    chrome.tabs.reload(tab.id);
  };
}
init();
