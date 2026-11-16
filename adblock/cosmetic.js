// Kozmetik filtre: ağ seviyesinde engellenen reklamların bıraktığı boş kutuları ve
// engellenemeyen yaygın reklam öğelerini gizler.
(async () => {
  let s = { enabled: true, allowlist: [] };
  try { s = await chrome.storage.local.get({ enabled: true, allowlist: [] }); } catch {}
  const host = location.hostname.replace(/^www\./, '');
  if (!s.enabled || s.allowlist.includes(host)) return;

  const selectors = [
    'ins.adsbygoogle', '[id^="google_ads_"]', '[id^="div-gpt-ad"]', '[id*="ad-container"]',
    '[class*="adsbygoogle"]', '[class*="ad-banner"]', '[class*="advert"]', '[class*="sponsored"]',
    '[class^="ad-"]', '[class$="-ad"]', '[data-ad]', '[data-ad-slot]', '[data-google-query-id]',
    'iframe[src*="doubleclick"]', 'iframe[src*="googlesyndication"]', 'iframe[id^="google_ads"]',
    'a[href*="doubleclick.net"]', 'a[href*="adnxs.com"]',
    '.taboola', '#taboola-below-article', '.OUTBRAIN', '[id^="outbrain"]',
    '#cookie-banner-ads', '.sticky-ad', '.ad-slot', '.ad-wrapper', '.banner-ad'
  ];

  const style = document.createElement('style');
  style.textContent = selectors.join(',\n') + ' { display: none !important; }';
  (document.head || document.documentElement).appendChild(style);

  // YouTube: reklam gelince atla / hızlandır (basit yöntem).
  if (host.endsWith('youtube.com')) {
    const tick = () => {
      const player = document.querySelector('.html5-video-player.ad-showing');
      const video = document.querySelector('video');
      if (player && video && isFinite(video.duration)) {
        video.muted = true;
        video.currentTime = video.duration;
      }
      const skip = document.querySelector('.ytp-ad-skip-button, .ytp-ad-skip-button-modern, .ytp-skip-ad-button');
      if (skip) skip.click();
      document.querySelectorAll('ytd-ad-slot-renderer, ytd-promoted-sparkles-web-renderer, #masthead-ad')
        .forEach((el) => el.remove());
    };
    setInterval(tick, 400);
  }
})();
