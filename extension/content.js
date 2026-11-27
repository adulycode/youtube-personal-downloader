(() => {
  let host, ui, job = {}, scheduled = false, lastURL = '', starting = false, polling = false, revision = 0;
  const get = id => ui.querySelector('#' + id);
  function receiveJob(next) {
    if (!next || starting) return;
    if (next.updatedAt && job.updatedAt && next.updatedAt < job.updatedAt) return;
    revision++;
    job=next;
    render();
  }
  async function refreshJob() {
    if (polling || starting || !ui || (!job.busy && get('menu').hidden)) return;
    polling=true;
    try {const r=await chrome.runtime.sendMessage({action:'get_job'});receiveJob(r?.job);} catch {} finally {polling=false;}
  }
  function isOpen() {
    return !!ui && !get('menu').hidden && (!get('menu').showPopover || get('menu').matches(':popover-open'));
  }
  function close() {
    if (!ui) return;
    try { if (get('menu').matches(':popover-open')) get('menu').hidePopover(); } catch {}
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
    get('start').textContent = job.busy ? 'กำลังทำงาน…' : 'ดาวน์โหลดลงเครื่อง';
    get('cancel').hidden = !job.busy;
    get('cancel').disabled = starting || job.stage === 'cancelling';
    get('format').disabled = !!job.busy;
    get('quality').disabled = !!job.busy || get('format').value === 'mp3';
    get('status').textContent = job.message || 'เลือกไฟล์ที่ต้องการดาวน์โหลด';
    get('status').dataset.stage=job.stage || '';
    const percent = Number.isFinite(job.percent) ? Math.max(0,Math.min(100,job.percent)) : null;
    get('progressArea').hidden = !job.busy && job.stage !== 'done';
    if (percent === null) get('downloadProgress').removeAttribute('value');
    else get('downloadProgress').value=percent;
    get('percent').textContent = percent === null ? (job.stage === 'processing' ? 'กำลังรวม/แปลงไฟล์' : 'กำลังเตรียม…') : percent.toFixed(1)+'%';
    get('toggle').classList.toggle('busy', !!job.busy);
    get('toggle').classList.toggle('spin', !!job.busy && percent === null);
    get('ring').toggleAttribute('hidden', !job.busy);
    get('arc').style.strokeDashoffset = percent === null ? 72 : 100 - percent;
    get('toggle').title = job.busy ? job.message : 'ดาวน์โหลด MP4 / MP3';
    get('caption').textContent = job.busy ? (percent === null ? 'กำลังทำงาน' : Math.round(percent)+'%') : 'Download';
    position();
  }
  function create() {
    document.querySelectorAll('#personal-youtube-downloader').forEach(e=>e.remove());
    host = document.createElement('div');
    host.id = 'personal-youtube-downloader';
    ui = host.attachShadow({mode:'open'});
    ui.innerHTML = `<style>
      :host{display:inline-flex;flex:0 0 auto;align-items:center;margin:0 4px;vertical-align:middle;font:14px system-ui;color:#f1f5f9}
      :host([data-shorts]){flex-direction:column;margin:0 0 8px;width:48px;min-height:64px;pointer-events:auto}
      :host([data-shorts]) #toggle{width:48px;height:48px}
      #caption{display:none;font-size:11px;line-height:16px;margin-top:4px;color:#f1f5f9}
      :host([data-shorts]) #caption{display:block}
      *{box-sizing:border-box}[hidden]{display:none!important}
      button,select{font:inherit;color:inherit}button{cursor:pointer}
      #toggle{position:relative;display:grid;place-items:center;width:40px;height:40px;padding:0;border:0;border-radius:50%;background:#ffffff1a;color:#75a7ff}
      #toggle:hover,#toggle[aria-expanded=true]{background:#ffffff30}#toggle:focus-visible,button:focus-visible,select:focus-visible{outline:2px solid #7eb0ff;outline-offset:3px}
      #toggle>svg:first-child{width:30px;height:30px}
      #ring{position:absolute;inset:0;width:100%;height:100%;transform:rotate(-90deg);pointer-events:none}
      #toggle.spin #ring{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(270deg)}}
      #arc{transition:stroke-dashoffset .2s ease}
      #menu{position:fixed;inset:auto;margin:0;z-index:2147483647;width:320px;max-height:calc(100vh - 24px);overflow:auto;padding:18px;background:#202124;color:#f1f5f9;border:1px solid #494b50;border-radius:16px;box-shadow:0 12px 40px #0008;text-align:left}
      header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}strong{font-size:17px}
      #close{border:0;background:transparent;font-size:24px;line-height:1;padding:2px 5px;color:#cbd5e1}
      label{display:block;margin:12px 0 6px;color:#cbd5e1;font-size:12px}select{width:100%;background:#303238;border:1px solid #60636c;border-radius:8px;padding:10px}
      #start,#cancel{width:100%;padding:11px;border:0;border-radius:9px;margin-top:14px;background:#3970ff;font-weight:600}#cancel{background:#41444b;margin-top:8px}
      button:disabled{opacity:.5;cursor:default}#status{margin:12px 0 8px;font-size:12px;line-height:1.6;overflow-wrap:anywhere}small{font-size:11px;color:#aab2c0;line-height:1.6}
      #progressArea{margin-top:14px}#downloadProgress{display:block;width:100%;height:10px;accent-color:#4f83ff}#percent{display:block;text-align:right;margin-top:5px;font-size:13px;font-weight:600}
      #status[data-stage=error]{color:#fda4af}#status[data-stage=done]{color:#86efac}
    </style>
    <button id="toggle" title="ดาวน์โหลด MP4 / MP3" aria-label="ดาวน์โหลดวิดีโอหรือเสียง" aria-haspopup="dialog" aria-expanded="false">
      <svg viewBox="0 0 128 128" aria-hidden="true"><rect x="4" y="16" width="120" height="86" rx="24" fill="#ff0033"/><path d="M48 35V81L84 58Z" fill="white"/><circle cx="99" cy="98" r="29" fill="#111827"/><path d="M99 80V106M88 96L99 107L110 96M86 117H112" fill="none" stroke="white" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <svg id="ring" viewBox="0 0 40 40" aria-hidden="true" hidden><circle cx="20" cy="20" r="18.75" fill="none" stroke="#73a6ff38" stroke-width="2.5"/><circle id="arc" cx="20" cy="20" r="18.75" fill="none" stroke="#73a6ff" stroke-width="2.5" stroke-linecap="round" pathLength="100" stroke-dasharray="100" stroke-dashoffset="72"/></svg>
    </button>
    <span id="caption">Download</span>
    <section id="menu" role="dialog" aria-label="ดาวน์โหลดจาก YouTube" hidden>
      <header><strong>ดาวน์โหลด</strong><button id="close" aria-label="ปิด">×</button></header>
      <label for="format">รูปแบบไฟล์</label><select id="format"><option value="mp4">วิดีโอ MP4</option><option value="mp3">เสียง MP3 · 192 kbps</option></select>
      <label for="quality">ความละเอียดสูงสุด</label><select id="quality"><option value="720">720p</option><option value="1080" selected>1080p</option><option value="2160">4K</option></select>
      <button id="start">ดาวน์โหลดลงเครื่อง</button><button id="cancel" hidden>ยกเลิกดาวน์โหลด</button>
      <div id="progressArea" hidden><progress id="downloadProgress" max="100" aria-label="ความคืบหน้าดาวน์โหลด"></progress><span id="percent"></span></div>
      <div id="status" role="status" aria-live="polite"></div><small>บันทึกใน Downloads / YouTube Personal<br>ใช้กับเนื้อหาที่คุณมีสิทธิ์ดาวน์โหลด</small>
    </section>`;
    get('toggle').onclick = () => {
      if (!chrome.runtime?.id) {location.reload();return;}
      if (isOpen()) {close();return;}
      get('menu').hidden = false;
      try {
        if (get('menu').showPopover) {
          get('menu').setAttribute('popover','manual');
          if (!get('menu').matches(':popover-open')) get('menu').showPopover();
        }
      } catch {}
      get('toggle').setAttribute('aria-expanded','true');
      position();get('format').focus();refreshJob();
    };
    get('close').onclick = () => {close();get('toggle').focus();};
    get('format').onchange = () => {get('quality').disabled = get('format').value === 'mp3';};
    get('start').onclick = async () => {
      const url = youtubeVideoURL(location.href);
      if (!url) {close();return;}
      starting=true;
      revision++;
      job={busy:true,stage:'connecting',message:'กำลังส่งคำสั่งและเชื่อมต่อโปรแกรมช่วย…'};
      render();position();
      try {
        const response = await Promise.race([
          chrome.runtime.sendMessage({action:'start',url,format:get('format').value,quality:Number(get('quality').value)}),
          new Promise((_,reject)=>setTimeout(()=>reject(new Error('timeout')),8000))
        ]);
        starting=false;
        if (!response?.ok) receiveJob({busy:false,stage:'error',message:response?.error || 'เชื่อมส่วนขยายไม่ได้ กรุณารีเฟรชหน้า YouTube แล้วลองอีกครั้ง'});
        else {if(response.job) receiveJob(response.job);await refreshJob();}
      } catch {starting=false;receiveJob({busy:false,stage:'error',message:'เชื่อมส่วนขยายไม่ได้ กรุณารีเฟรชหน้า YouTube (F5) แล้วลองอีกครั้ง'});}
    };
    get('cancel').onclick = async () => {
      job={...job,stage:'cancelling',message:'กำลังยกเลิกดาวน์โหลด…'};render();
      try {const r=await chrome.runtime.sendMessage({action:'cancel'});if(r?.error) get('status').textContent=r.error;} catch {get('status').textContent='กรุณารีเฟรชหน้า YouTube';}
    };
    render();
  }
  function visible(element) {
    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && rect.bottom > 64 && rect.top < innerHeight && rect.right > 0 && rect.left < innerWidth;
  }
  function shortsAnchor() {
    // Modern Shorts extracts its action bar outside ytd-reel-video-renderer.
    // Older layouts keep #actions in the reel and may omit is-active entirely.
    const bars = Array.from(document.querySelectorAll('ytd-shorts reel-action-bar-view-model, ytd-reel-video-renderer #actions'))
      .filter(visible).sort((a,b) => {
        const center = e => {const r=e.getBoundingClientRect();return Math.abs((r.top+r.bottom)/2-innerHeight/2);};
        return center(a)-center(b);
      });
    for (const bar of bars) {
      const buttons = Array.from(bar.querySelectorAll('button')).filter(visible);
      const share = buttons.find(b => /^(share|แชร์|แบ่งปัน)$/i.test(b.getAttribute('aria-label') || b.getAttribute('title') || ''));
      const entry = share?.closest('button-view-model, ytd-button-renderer, yt-button-shape');
      if (entry && entry.parentElement === bar) return {target:bar,after:entry};
      return {target:bar};
    }
    return null;
  }
  function mount() {
    scheduled = false;
    const url = youtubeVideoURL(location.href);
    if (url !== lastURL) {close();lastURL=url;}
    if (!url) {host?.remove();return;}
    const shorts = location.pathname.startsWith('/shorts/');
    const anchor = shorts ? shortsAnchor() : null;
    const target = shorts ? anchor?.target
      : document.querySelector('ytd-watch-metadata #actions #top-level-buttons-computed')
        || document.querySelector('ytd-watch-metadata #actions #menu')
        || document.querySelector('ytd-watch-metadata #actions')
        || document.querySelector('ytd-watch-metadata #title');
    if (!target) {host?.remove();return;}
    if (!host) create();
    host.toggleAttribute('data-shorts',shorts);
    host.dataset.videoUrl=url;
    if (anchor?.after) {
      if (anchor.after.nextElementSibling !== host) anchor.after.after(host);
    } else if (host.parentElement !== target) target.append(host);
  }
  function schedule() {if (!scheduled) {scheduled=true;setTimeout(mount,150);}}
  const initialRevision=revision;
  chrome.storage.local.get('job').then(({job:s})=>{if(revision===initialRevision) receiveJob(s||{});}).catch(()=>{});
  chrome.storage.onChanged.addListener(c=>{if(c.job) receiveJob(c.job.newValue||{});});
  setInterval(refreshJob,1000);
  document.addEventListener('pointerdown',event=>{if(host&&!event.composedPath().includes(host))close();},true);
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&ui&&!get('menu').hidden){close();get('toggle').focus();}});
  window.addEventListener('resize',()=>{position();schedule();});
  window.addEventListener('scroll',()=>{close();schedule();},true);
  new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['is-active','hidden','aria-hidden','video-id']});
  document.addEventListener('yt-navigate-finish',schedule);
  window.addEventListener('popstate',schedule);
  mount();
})();
