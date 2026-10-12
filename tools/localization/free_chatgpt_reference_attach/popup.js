"use strict";
/* No OpenAI API, no automated submission, no account/session/token access. */
const REPO = "thp32tt/OutRun2006Tweaks";
const BRANCH = "korean-localization-recovery-20260928";
let references = [];
const $ = (id) => document.getElementById(id);
function status(text) { $("status").textContent = text; }
function selected() { return references.find((r) => r.id === $("ref").value); }
function promptFor(r) {
  if (!r.korean) return "대상 한글 문구 미승인. 먼저 정확한 번역/원본 소유권을 검수하세요.";
  return "첨부한 영문 원본 글자 PNG를 실제 시각 참조로 사용합니다. 정확한 한글 문구: " + r.korean +
    ". 원본의 획 굵기, 기울기, 색상, 테두리, 그림자와 광륜을 유지하고, 글자/효과 bbox를 넘기지 마세요. 투명 배경에 해당 한글 글자층 한 개만 생성합니다. 게임 화면·메뉴·자동차·추가 문구·영문 잔상을 넣지 마세요. 참조 PNG가 실제로 첨부되지 않았다면 생성을 중단하세요.";
}
function refreshMeta() {
  const r=selected();
  $("meta").textContent = r ? ("영문: " + r.english + "  /  한글: " + (r.korean || "미승인") + "\n" + r.note) : "";
}
async function loadVerified(r) {
  const safe = r.path.split("/").map(encodeURIComponent).join("/");
  const url = "https://raw.githubusercontent.com/" + REPO + "/" + BRANCH + "/" + safe;
  const response = await fetch(url,{credentials:"omit",cache:"no-store",redirect:"error"});
  if(!response.ok) throw new Error("GitHub 원본 다운로드 실패: HTTP " + response.status);
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (bytes.length > 20*1024*1024 || bytes.length < 100) throw new Error("파일 크기 비정상");
  const hash = new Uint8Array(await crypto.subtle.digest("SHA-256",bytes));
  const sha = Array.from(hash,x=>x.toString(16).padStart(2,"0")).join("");
  if (sha !== r.sha256) throw new Error("SHA-256 불일치. 첨부 중단");
  if (bytes[0]!==137 || bytes[1]!==80 || bytes[2]!==78 || bytes[3]!==71) throw new Error("PNG 서명 불일치");
  return new File([bytes],r.file,{type:"image/png",lastModified:0});
}
async function activeChatTab() {
  const tabs=await chrome.tabs.query({active:true,currentWindow:true});
  const tab=tabs[0];
  if(!tab?.id || !tab.url) throw new Error("현재 탭 확인 불가");
  const hostname=new URL(tab.url).hostname;
  if(hostname!=="chatgpt.com" && hostname!=="chat.openai.com") throw new Error("ChatGPT 웹 대화 탭에서 사용하세요");
  return tab;
}
async function injectFile(tab,file) {
  const bytes=new Uint8Array(await file.arrayBuffer());
  const outcome=await chrome.scripting.executeScript({
    target:{tabId:tab.id},
    func:({name,bytes})=>{
      const nodes=Array.from(document.querySelectorAll('input[type="file"]'));
      const input=nodes.find(el=> !el.disabled &&
        (!el.accept || el.accept.includes("image") || el.accept.includes(".png")));
      if (!input) return {status:"NO_NATIVE_FILE_INPUT",count:nodes.length};
      const dataTransfer=new DataTransfer();
      dataTransfer.items.add(new File([new Uint8Array(bytes)],name,{type:"image/png"}));
      input.files=dataTransfer.files;
      input.dispatchEvent(new Event("input",{bubbles:true}));
      input.dispatchEvent(new Event("change",{bubbles:true}));
      return {status:"DOM_FILE_CHANGE_DISPATCHED_NOT_UPLOAD_PROOF",
              count:input.files.length,size:input.files[0]?.size||0};
    },
    args:[{name:file.name,bytes:Array.from(bytes)}]
  });
  return outcome?.[0]?.result;
}
async function setClipboardImage(file) {
  if (!navigator.clipboard?.write || typeof ClipboardItem==="undefined")
    throw new Error("이미지 클립보드를 지원하지 않는 브라우저입니다");
  await navigator.clipboard.write([new ClipboardItem({"image/png":file})]);
}
async function operate(mode) {
  for (const id of ["attach","copy","prompt"]) $(id).disabled=true;
  try {
    const r=selected();
    if (!r) throw new Error("원본 이미지 선택 필요");
    if (mode==="prompt") {
      await navigator.clipboard.writeText(promptFor(r));
      status("프롬프트 복사 완료. ChatGPT 입력창에 붙여 넣으세요.");
      return;
    }
    status("GitHub 원본 다운로드 및 SHA-256 확인 중...");
    const file=await loadVerified(r);
    if(mode==="copy"){
      await setClipboardImage(file);
      status("검증된 PNG가 클립보드에 복사됐습니다. ChatGPT 입력창을 클릭하고 Ctrl+V를 누르세요. 첨부 썸네일을 확인하세요.");
      return;
    }
    const tab=await activeChatTab();
    const result=await injectFile(tab,file);
    if(result?.status==="DOM_FILE_CHANGE_DISPATCHED_NOT_UPLOAD_PROOF")
      status("ChatGPT 파일 입력 DOM에 " + file.name + " ("+result.size+"B) 전달 완료. 실제 업로드/이미지 생성기 수신은 아직 검증되지 않았습니다. 반드시 대화창에 첨부 썸네일이 나타나는지 확인하세요. 없으면 'PNG 복사' → Ctrl+V를 이용하세요.");
    else
      status("ChatGPT 페이지에 사용할 수 있는 파일 입력이 없습니다. '+' 메뉴에서 파일 첨부 UI를 연 뒤 다시 시도하거나, 'PNG 복사' → Ctrl+V를 이용하세요.");
  } catch(e) { status("중단: " + (e?.message || String(e))); }
  finally { for (const id of ["attach","copy","prompt"]) $(id).disabled=false; }
}
async function init(){
  try{
    const res=await fetch(chrome.runtime.getURL("references.json"));
    references=await res.json();
    for (const r of references){
      const opt=document.createElement("option");
      opt.value=r.id;
      opt.textContent=r.role+" q"+r.index+" · "+r.english+(r.korean?" → "+r.korean:" (한글 미승인)");
      $("ref").appendChild(opt);
    }
    $("ref").addEventListener("change",refreshMeta);
    $("attach").addEventListener("click",()=>operate("attach"));
    $("copy").addEventListener("click",()=>operate("copy"));
    $("prompt").addEventListener("click",()=>operate("prompt"));
    refreshMeta();
  }catch(e){status("초기화 오류: "+(e?.message||String(e)));}
}
init();