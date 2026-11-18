importScripts('video-url.js');
let port = null;
let running = false;
let checkingUpdate = false;
async function checkForUpdate() {
  if (running || checkingUpdate) return {error:'มีงานกำลังทำงานอยู่ กรุณาลองอีกครั้ง'};
  checkingUpdate = true;
  await chrome.storage.local.set({updateStatus:'กำลังตรวจอัปเดตจาก GitHub…'});
  return new Promise(resolve => {
    let done = false;
    let connection;
    const finish = async result => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      connection?.disconnect();
      checkingUpdate = false;
      await chrome.storage.local.set({updateStatus:result.message});
      resolve(result);
      if (result.updated) chrome.runtime.reload();
    };
    const timer = setTimeout(()=>finish({message:'ตรวจอัปเดตหมดเวลา กรุณาลองอีกครั้ง',error:true}),420000);
    try {
      connection = chrome.runtime.connectNative('com.personal.youtube_downloader');
      connection.onMessage.addListener(data => {if(data.type === 'update_result') finish(data);});
      connection.onDisconnect.addListener(() => {
        const error = chrome.runtime.lastError?.message;
        if (!done) finish({message:error ? 'เชื่อมโปรแกรมช่วยไม่ได้ กรุณาอัปเดตชุดไฟล์ครั้งแรกก่อน' : 'โปรแกรมช่วยปิดการเชื่อมต่อ',error:true});
      });
      connection.postMessage({action:'check_update'});
    } catch {finish({message:'เชื่อมโปรแกรมช่วยไม่ได้',error:true});}
  });
}
function scheduleUpdates() {chrome.alarms.create('private-github-update',{delayInMinutes:2,periodInMinutes:360});}
chrome.runtime.onInstalled.addListener(scheduleUpdates);
chrome.runtime.onStartup.addListener(scheduleUpdates);
chrome.alarms.onAlarm.addListener(alarm => {if(alarm.name === 'private-github-update') checkForUpdate().catch(()=>{});});
let writes = Promise.resolve();
function state(value) {writes = writes.catch(()=>{}).then(()=>chrome.storage.local.set({job:value}));}
chrome.runtime.onStartup.addListener(() => state({busy:false,message:'พร้อมใช้งาน'}));
chrome.runtime.onInstalled.addListener(() => state({busy:false,message:'พร้อมใช้งาน — ติดตั้งโปรแกรมช่วยก่อนเริ่มดาวน์โหลด'}));
async function handleMessage(msg, sender) {
  let response;
  const reply = value => {response = value;};
  if(sender.id !== chrome.runtime.id) return;
  if(msg.action === 'check_update') {
    if (sender.tab || !sender.url?.startsWith(chrome.runtime.getURL(''))) return {error:'เปิดจากหน้าส่วนขยายเท่านั้น'};
    return checkForUpdate();
  }
  if (['start','cancel'].includes(msg.action)) {
    const tab = sender.tab ? await chrome.tabs.get(sender.tab.id) : (await chrome.tabs.query({active:true,currentWindow:true}))[0];
    const current = youtubeVideoURL(tab?.url);
    if (!current) return {error:'เปิดหน้าวิดีโอ YouTube ก่อนใช้งาน'};
    if (msg.action === 'start') {
      if (youtubeVideoURL(msg.url) !== current) return {error:'หน้าวิดีโอเปลี่ยนแล้ว กรุณาลองอีกครั้ง'};
      msg = {...msg,url:current};
    }
  }
  if(msg.action === 'cancel') {port?.postMessage({action:'cancel'}); return {ok:true};}
  if(msg.action !== 'start') return;
  if(running || checkingUpdate) return {error:'มีงานดาวน์โหลดหรือตรวจอัปเดตอยู่ กรุณารอสักครู่'};
  running = true;
  state({busy:true,message:'กำลังเชื่อมต่อโปรแกรมช่วย…'});
  try {
    const connection = chrome.runtime.connectNative('com.personal.youtube_downloader');
    port = connection;
    connection.onMessage.addListener(data => {
      if(data.type === 'progress') state({busy:true,message:data.message,percent:data.percent});
      if(['done','error','cancelled'].includes(data.type)) {
        running = false;
        state({busy:false,message:data.message,percent:data.type === 'done' ? 100 : 0});
        port = null;
        connection.disconnect();
      }
    });
    connection.onDisconnect.addListener(() => {
      const error = chrome.runtime.lastError?.message;
      if(port !== connection) return;
      port = null; running = false;
      state({busy:false,message:error ? 'เชื่อมต่อไม่ได้: '+error+' — ตรวจสอบการติดตั้งโปรแกรมช่วยและ Extension ID' : 'โปรแกรมช่วยปิดการเชื่อมต่อ'});
    });
    connection.postMessage(msg);
    reply({ok:true});
  } catch(e) {running=false; state({busy:false,message:e.message}); reply({error:e.message});}
  return response;
}
chrome.runtime.onMessage.addListener((msg,sender,reply) => {
  handleMessage(msg,sender).then(reply).catch(e=>reply({error:e.message}));
  return true;
});
