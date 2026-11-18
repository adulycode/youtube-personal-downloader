const $ = id => document.getElementById(id);
const manifest = chrome.runtime.getManifest();
$('versionInfo').textContent = 'เวอร์ชัน '+manifest.version;
const releaseDate = manifest.version_name?.match(/\d{4}-\d{2}-\d{2}/)?.[0];
$('releaseInfo').textContent = 'เผยแพร่รุ่นนี้: '+(releaseDate ? new Date(releaseDate+'T12:00:00Z').toLocaleDateString('th-TH',{year:'numeric',month:'short',day:'numeric'}) : 'ไม่ระบุ');
function updateDates(data) {
  const fmt = value => value ? new Date(value).toLocaleString('th-TH',{dateStyle:'medium',timeStyle:'short'}) : 'ยังไม่มีข้อมูล';
  $('installedInfo').textContent = 'ติดตั้ง/อัปเดตในเครื่อง: '+fmt(data.installedAt);
  $('checkedInfo').textContent = 'ตรวจอัปเดตล่าสุด: '+fmt(data.lastUpdateCheckAt);
}
chrome.storage.local.get(['installedAt','lastUpdateCheckAt']).then(updateDates);
chrome.storage.onChanged.addListener(c=>{if(c.installedAt || c.lastUpdateCheckAt) chrome.storage.local.get(['installedAt','lastUpdateCheckAt']).then(updateDates);});
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
chrome.storage.local.get('updateStatus').then(s=>{$('updateStatus').textContent=s.updateStatus||'อัปเดตอัตโนมัติทุก 6 ชั่วโมง · ไม่ต้องล็อกอิน GitHub';});
chrome.storage.onChanged.addListener(c=>{if(c.updateStatus) $('updateStatus').textContent=c.updateStatus.newValue||'';});
$('checkUpdate').onclick = async () => {
  $('checkUpdate').disabled=true;
  try {
    const r=await chrome.runtime.sendMessage({action:'check_update'});
    if(r?.error && !r.message) $('updateStatus').textContent=typeof r.error==='string'?r.error:'ตรวจอัปเดตไม่สำเร็จ';
  } catch {$('updateStatus').textContent='ถ้าอัปเดตสำเร็จแล้ว ให้เปิดหน้าส่วนขยายใหม่';}
  finally {$('checkUpdate').disabled=false;}
};
