const $ = id => document.getElementById(id);
$('extensionId').textContent = chrome.runtime.id;
let allowed = false;
let lastJob = {};
$('url').readOnly = true;
$('start').disabled = true;
function render(s = {}) {
  lastJob = s;
  $('status').textContent = allowed ? (s.message || 'พร้อมใช้งาน') : 'เปิดหน้าวิดีโอ YouTube เพื่อดาวน์โหลด';
  $('start').disabled = !allowed || !!s.busy;
  $('cancel').disabled = !allowed || !s.busy;
  if (s.busy && s.percent == null) $('progress').removeAttribute('value');
  else $('progress').value = s.percent || 0;
}
chrome.storage.local.get('job').then(({job}) => render(job));
chrome.storage.onChanged.addListener(changes => {if(changes.job) render(changes.job.newValue);});
chrome.tabs.query({active:true,currentWindow:true}).then(([tab]) => {
  const url = youtubeVideoURL(tab?.url);
  allowed = !!url;
  $('url').value = url || '';
  render(lastJob);
});
$('format').onchange = () => {$('quality').disabled = $('format').value === 'mp3';};
$('start').onclick = async () => {
  try {
    const result = await chrome.runtime.sendMessage({action:'start',url:$('url').value,format:$('format').value,quality:Number($('quality').value)});
    if(result?.error) $('status').textContent = result.error;
  } catch(e) {$('status').textContent = e.message;}
};
$('cancel').onclick = () => chrome.runtime.sendMessage({action:'cancel'});
chrome.storage.local.get('updateStatus').then(s=>{$('updateStatus').textContent=s.updateStatus||'อัปเดตอัตโนมัติทุก 6 ชั่วโมง · เชื่อมผ่าน CONNECT-GITHUB.cmd ครั้งแรก';});
chrome.storage.onChanged.addListener(c=>{if(c.updateStatus) $('updateStatus').textContent=c.updateStatus.newValue||'';});
$('checkUpdate').onclick = async () => {
  $('checkUpdate').disabled=true;
  try {
    const r=await chrome.runtime.sendMessage({action:'check_update'});
    if(r?.error && !r.message) $('updateStatus').textContent=typeof r.error==='string'?r.error:'ตรวจอัปเดตไม่สำเร็จ';
  } catch {$('updateStatus').textContent='ถ้าอัปเดตสำเร็จแล้ว ให้เปิดหน้าส่วนขยายใหม่';}
  finally {$('checkUpdate').disabled=false;}
};
