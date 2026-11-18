const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..');
const elements=new Map();const get=id=>{if(!elements.has(id))elements.set(id,{value:'',textContent:'',disabled:false,removeAttribute:()=>{}});return elements.get(id)};
const stored={installedAt:'2026-11-18T03:00:00Z',lastUpdateCheckAt:'2026-11-18T04:00:00Z'};
const c={URL,Date,document:{getElementById:get},chrome:{runtime:{id:'test',getManifest:()=>({version:'1.6.0',version_name:'1.6.0 (2026-11-18)'})},storage:{local:{get:async()=>stored},onChanged:{addListener:()=>{}}},tabs:{query:async()=>[{url:'https://www.youtube.com/shorts/1Ujb6FTm59I'}]}}};
vm.createContext(c);for(const file of ['video-url.js','popup.js'])vm.runInContext(fs.readFileSync(path.join(root,'extension',file),'utf8'),c);
setImmediate(()=>{assert(get('versionInfo').textContent.includes('1.6.0'));assert(!get('releaseInfo').textContent.includes('ไม่ระบุ'));assert(!get('installedInfo').textContent.includes('ยังไม่มี'));assert(!get('checkedInfo').textContent.includes('ยังไม่มี'));assert.equal(get('url').value,'https://www.youtube.com/watch?v=1Ujb6FTm59I');assert.equal(get('start').disabled,false);console.log('PASS: installed version, release date, installed/check times and Shorts popup download');});
