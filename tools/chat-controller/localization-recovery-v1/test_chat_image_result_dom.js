#!/usr/bin/env node
// Pure-Node DOM fixture tests for the browser-side assistant-image extraction.
// Run: node test_chat_image_result_dom.js
// These tests use NO account login, image API, paid API, or server processes.
'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'chat_image_result_rescue.py'),'utf8');
const found=source.match(/ASSISTANT_IMAGE_JS = r"""([\s\S]*?)"""/);
assert(found,'browser image probe source not found');
const payload={
 task:'HDRW-A-'+'d'.repeat(20),
 english:'Ghost Forest',
 korean:'고스트 포레스트',
 sha:'a'.repeat(64)
};
const src='blob:https://chatgpt.com/one-image';
function img(url=src){
 return {complete:true,naturalWidth:256,naturalHeight:96,currentSrc:url,src:url};
}
function turn(images=[]){
 return {images,querySelectorAll(selector){
   return selector.includes('[data-testid="generated-image-preview"] img')?this.images:[];
 }};
}
function message(kind,text,parent){
 return {parent,kind,innerText:text,textContent:text,
  matches(selector){
   return selector.includes('[data-markdown-text-tone="'+(kind==='user'?'user-message':'assistant')+'"]');
  },
  closest(selector){
   return selector.includes('data-chatgpt-search-unit-key')?this.parent:null;
  }};
}
function check(label,messages,want,method=null){
 const context={
  document:{querySelectorAll:()=>messages},
  location:{hostname:'chatgpt.com',pathname:'/g/some-project/c/a-verified-id'}
 };
 const fn=vm.runInNewContext('('+found[1]+')',context,{timeout:2000});
 const actual=fn(payload);
 assert.equal(actual.status,want,label+': '+actual.status);
 if(method)assert.equal(actual.match_method,method,label);
 console.log('PASS '+label);
}
const english='영문 원문: '+payload.english;
const korean='한국어 번역: '+payload.korean;
const sha='원본 DDS SHA: '+payload.sha;
function pair(text,imgs=[img()]){
 return [message('user',text,turn([img('blob:https://chatgpt.com/source-reference')])),
         message('assistant','완성 이미지',turn(imgs))];
}
check('exact task marker on Project DOM',
      pair(english+'\n'+korean+'\n'+sha+'\nUPLOAD_TASK_ID='+payload.task),
      'ASSISTANT_IMAGE_SOURCE_VERIFIED','TASK_ID');
check('strict source triple without hidden task footer',
      pair(english+'\n'+korean+'\n'+sha),
      'ASSISTANT_IMAGE_SOURCE_VERIFIED','SOURCE_TRIPLE');
check('reject absent DDS SHA',
      pair(english+'\n'+korean),
      'SOURCE_BOUND_USER_TURN_MISSING');
check('reject wrong Korean translation',
      pair(english+'\n한국어 번역: 틀린 번역\n'+sha),
      'SOURCE_BOUND_USER_TURN_MISSING');
check('never select user English reference alone',
      pair(english+'\n'+korean+'\n'+sha,[]),
      'ASSISTANT_GENERATED_IMAGE_SELECTOR_MISSING');
check('never infer from multiple assistant candidates',
      pair(english+'\n'+korean+'\n'+sha,[img(src),img('blob:https://chatgpt.com/second')]),
      'ASSISTANT_IMAGE_AMBIGUOUS');
check('fail closed if Project user turns unavailable',[],
      'CHAT_USER_TURNS_NOT_RENDERED');
const duo=[
 ...pair(english+'\n'+korean+'\n'+sha),
 ...pair(english+'\n'+korean+'\n'+sha)
];
check('never pick ambiguous duplicated user turn',duo,
      'SOURCE_BOUND_USER_TURN_AMBIGUOUS');
console.log('ALL 8 PROJECT DOM FIXTURES PASSED');
