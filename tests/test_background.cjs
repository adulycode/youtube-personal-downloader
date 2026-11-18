const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..');
let listener,receive,disconnected;
const stored={};
const connection={
  onMessage:{addListener:f=>receive=f},onDisconnect:{addListener:f=>disconnected=f},
  postMessage:()=>{},disconnect:()=>disconnected?.()
};
const context={URL,Date,setTimeout,clearTimeout,chrome:{
  tabs:{query:async()=>[{url:'https://www.youtube.com/shorts/1Ujb6FTm59I'}]},
  runtime:{id:'test',onStartup:{addListener:()=>{}},onInstalled:{addListener:()=>{}},
    onMessage:{addListener:f=>listener=f},connectNative:()=>connection},
  alarms:{create:()=>{},onAlarm:{addListener:()=>{}}},
  storage:{local:{set:async s=>Object.assign(stored,s),get:async()=>stored}}
}};
vm.createContext(context);
context.importScripts=file=>vm.runInContext(fs.readFileSync(path.join(root,'extension',file),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(root,'extension/background.js'),'utf8'),context);
const send=message=>new Promise(resolve=>listener(message,{id:'test'},resolve));
(async()=>{
  const started=await send({action:'start',url:'https://www.youtube.com/watch?v=1Ujb6FTm59I',format:'mp4',quality:1080});
  assert(started.ok);assert(started.job.busy);assert.equal(started.job.stage,'connecting');
  receive({type:'progress',stage:'downloading',message:'42.5%',percent:42.5});
  let current=await send({action:'get_job'});
  assert.equal(current.job.percent,42.5);assert(current.job.busy);
  receive({type:'progress',stage:'processing',message:'merging'});
  current=await send({action:'get_job'});
  assert.equal(current.job.stage,'processing');assert.equal(current.job.percent,undefined);
  receive({type:'done',message:'saved'});
  current=await send({action:'get_job'});
  assert.equal(current.job.stage,'done');assert.equal(current.job.percent,100);assert.equal(current.job.busy,false);
  await new Promise(resolve=>setImmediate(resolve));assert.equal(stored.job.stage,'done');
  console.log('PASS: start acknowledgment and job polling track progress, processing and completion');
})().catch(error=>{console.error(error);process.exit(1)});
