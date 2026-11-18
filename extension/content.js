(() => {
  let host, ui, job = {}, scheduled = false, lastURL = '';
  const get = id => ui.querySelector('#' + id);
  function close() {
    if (!ui) return;
    get('menu').hidden = true;
    get('toggle').setAttribute('aria-expanded', 'false');
  }
  function position() {
    if (!ui || get('menu').hidden) return;
    const rect = get('toggle').getBoundingClientRect();
    const menu = get('menu');
    const width = Math.min(320, innerWidth - 24);
    menu.style.width = width + 'px';
    menu.style.left = Math.max(12, Math.min(rect.right - width, innerWidth - width - 12)) + 'px';
    const height = menu.getBoundingClientRect().height;
    menu.style.top = Math.max(12, Math.min(rect.bottom + 8, innerHeight - height - 12)) + 'px';
  }
  function render() {
    if (!ui) return;
    get('start').disabled = !!job.busy;
    get('cancel').hidden = !job.busy;
    get('status').textContent = job.message || 'เลือกไฟล์ที่ต้องการดาวน์โหลด';
    get('toggle').classList.toggle('busy', !!job.busy);
    get('toggle').title = job.busy ? 'กำลังดาวน์โหลด — คลิกดูสถานะ' : 'ดาวน์โหลด MP4 / MP3';
  }
  function create() {
    host = document.createElement('div');
    host.id = 'personal-youtube-downloader';
    ui = host.attachShadow({mode:'open'});
    ui.innerHTML = `<style>
      :host{display:inline-flex;flex:0 0 auto;align-items:center;margin:0 4px;vertical-align:middle;font:14px system-ui;color:#f1f5f9}
      *{box-sizing:border-box}[hidden]{display:none!important}
      button,select{font:inherit;color:inherit}button{cursor:pointer}
      #toggle{display:grid;place-items:center;width:40px;height:40px;padding:0;border:0;border-radius:50%;background:#ffffff1a;color:#75a7ff}
      #toggle:hover,#toggle[aria-expanded=true]{background:#ffffff30}#toggle:focus-visible,button:focus-visible,select:focus-visible{outline:2px solid #7eb0ff;outline-offset:3px}
      #toggle svg{width:30px;height:30px}#toggle.busy{box-shadow:inset 0 0 0 2px #73a6ff}
      #menu{position:fixed;z-index:2147483647;width:320px;max-height:calc(100vh - 24px);overflow:auto;padding:18px;background:#202124;border:1px solid #494b50;border-radius:16px;box-shadow:0 12px 40px #0008;text-align:left}
      header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}strong{font-size:17px}
      #close{border:0;background:transparent;font-size:24px;line-height:1;padding:2px 5px;color:#cbd5e1}
      label{display:block;margin:12px 0 6px;color:#cbd5e1;font-size:12px}select{width:100%;background:#303238;border:1px solid #60636c;border-radius:8px;padding:10px}
      #start,#cancel{width:100%;padding:11px;border:0;border-radius:9px;margin-top:14px;background:#3970ff;font-weight:600}#cancel{background:#41444b;margin-top:8px}
      button:disabled{opacity:.5;cursor:default}#status{margin:12px 0 8px;font-size:12px;line-height:1.6;overflow-wrap:anywhere}small{font-size:11px;color:#aab2c0;line-height:1.6}
    </style>
    <button id="toggle" title="ดาวน์โหลด MP4 / MP3" aria-label="ดาวน์โหลดวิดีโอหรือเสียง" aria-haspopup="dialog" aria-expanded="false">
      <svg viewBox="0 0 128 128" aria-hidden="true"><rect x="4" y="16" width="120" height="86" rx="24" fill="#ff0033"/><path d="M48 35V81L84 58Z" fill="white"/><circle cx="99" cy="98" r="29" fill="#111827"/><path d="M99 80V106M88 96L99 107L110 96M86 117H112" fill="none" stroke="white" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </button>
    <section id="menu" role="dialog" aria-label="ดาวน์โหลดจาก YouTube" hidden>
      <header><strong>ดาวน์โหลด</strong><button id="close" aria-label="ปิด">×</button></header>
      <label for="format">รูปแบบไฟล์</label><select id="format"><option value="mp4">วิดีโอ MP4</option><option value="mp3">เสียง MP3 · 192 kbps</option></select>
      <label for="quality">ความละเอียดสูงสุด</label><select id="quality"><option value="720">720p</option><option value="1080" selected>1080p</option><option value="2160">4K</option></select>
      <button id="start">ดาวน์โหลดลงเครื่อง</button><button id="cancel" hidden>ยกเลิกดาวน์โหลด</button>
      <div id="status" role="status" aria-live="polite"></div><small>บันทึกใน Downloads / YouTube Personal<br>ใช้กับเนื้อหาที่คุณมีสิทธิ์ดาวน์โหลด</small>
    </section>`;
    get('toggle').onclick = () => {
      if (!get('menu').hidden) {close();return;}
      get('menu').hidden = false;
      get('toggle').setAttribute('aria-expanded','true');
      position();get('format').focus();
    };
    get('close').onclick = () => {close();get('toggle').focus();};
    get('format').onchange = () => {get('quality').disabled = get('format').value === 'mp3';};
    get('start').onclick = async () => {
      const url = youtubeVideoURL(location.href);
      if (!url) {close();return;}
      get('start').disabled = true;
      try {
        const response = await chrome.runtime.sendMessage({action:'start',url,format:get('format').value,quality:Number(get('quality').value)});
        if (response?.error) {render();get('status').textContent=response.error;}
      } catch {render();get('status').textContent='กรุณารีเฟรชหน้า YouTube แล้วลองอีกครั้ง';}
    };
    get('cancel').onclick = async () => {
      try {await chrome.runtime.sendMessage({action:'cancel'});} catch {get('status').textContent='กรุณารีเฟรชหน้า YouTube';}
    };
    render();
  }
  function mount() {
    scheduled = false;
    const url = youtubeVideoURL(location.href);
    if (url !== lastURL) {close();lastURL=url;}
    if (!url) {host?.remove();return;}
    const shorts = location.pathname.startsWith('/shorts/');
    const target = shorts
      ? document.querySelector('ytd-reel-video-renderer[is-active] #actions')
      : document.querySelector('ytd-watch-metadata #actions #top-level-buttons-computed')
        || document.querySelector('ytd-watch-metadata #actions #menu')
        || document.querySelector('ytd-watch-metadata #actions')
        || document.querySelector('ytd-watch-metadata #title');
    if (!target) return;
    if (!host) create();
    if (host.parentElement !== target) target.append(host);
  }
  function schedule() {if (!scheduled) {scheduled=true;setTimeout(mount,150);}}
  chrome.storage.local.get('job').then(({job:s})=>{job=s||{};render();}).catch(()=>{});
  chrome.storage.onChanged.addListener(c=>{if(c.job){job=c.job.newValue||{};render();}});
  document.addEventListener('pointerdown',event=>{if(host&&!event.composedPath().includes(host))close();},true);
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&ui&&!get('menu').hidden){close();get('toggle').focus();}});
  window.addEventListener('resize',position);
  window.addEventListener('scroll',close,true);
  new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true});
  document.addEventListener('yt-navigate-finish',schedule);
  window.addEventListener('popstate',schedule);
  mount();
})();
