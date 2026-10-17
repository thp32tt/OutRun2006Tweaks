#!/usr/bin/env python3
"""Isolated A/B ChatGPT image-only producer; no DDS/CLEAN/game writes.
All schedules Asia/Seoul, role A at :00/:20/:40, role B at :10/:30/:50.
Only preapproved single-PNG batch inputs and explicit prompt files are accepted.
Submission is at-most-once per task, even across browser failures and restarts.
"""
import argparse, datetime as dt, hashlib, io, json, os, re, sys, time
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image

KST = ZoneInfo('Asia/Seoul')
SCHEDULE = {0:'A',10:'B',20:'A',30:'B',40:'A',50:'B'}
SOURCE_ROOT = Path(os.getenv('INPUT_ROOT','/inputs'))
STATE_ROOT = Path(os.getenv('STATE_ROOT','/state'))
OUTPUT_ROOT = Path(os.getenv('OUTPUT_ROOT','/output'))
PROMPT_ROOT = Path(os.getenv('PROMPT_ROOT','/prompts'))
PROFILE = Path(os.getenv('PROFILE_ROOT','/profile'))
PROJECT = os.getenv('CHATGPT_PROJECT_URL','').strip()
AUTO_SEND = os.getenv('AUTO_SEND','true').lower() == 'true'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for buf in iter(lambda:f.read(1024*1024),b''):
            h.update(buf)
    return h.hexdigest()

def atomic_json(path, obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    temp.replace(path)

def slot_at(moment):
    """Match 10-min boundaries. Caller controls no-late-send safety window."""
    local=moment.astimezone(KST)
    role=SCHEDULE.get(local.minute)
    if not role:return None
    return {'role':role,'key':local.strftime('%Y-%m-%dT%H:%M%z'),'second':local.second}

def load_job(role):
    base=SOURCE_ROOT/role
    if not base.is_dir():return None
    for item in sorted(base.glob('*.json')):
        if item.name.startswith('.') or item.name=='status.json':continue
        try: data=json.loads(item.read_text(encoding='utf-8'))
        except Exception:continue
        if data.get('role')!=role or data.get('status')!='READY':continue
        if (STATE_ROOT/(data.get('task_id','')+'.json')).exists():continue
        task=data.get('task_id','')
        name=data.get('input_file','')
        prompt_name=data.get('prompt_file','')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{5,120}',task): continue
        if Path(name).name!=name or Path(prompt_name).name!=prompt_name: continue
        png=base/name; prompt=PROMPT_ROOT/prompt_name
        if not png.is_file() or not prompt.is_file():continue
        if sha(png)!=data.get('input_sha256'):continue
        if sha(prompt)!=data.get('prompt_sha256'):continue
        if not (1<=int(data.get('expected_slots',0))<=8):continue
        return item, data,png,prompt
    return None

def audit(record):
    STATE_ROOT.mkdir(parents=True,exist_ok=True)
    with (STATE_ROOT/'audit.jsonl').open('a',encoding='utf8') as f:
        f.write(json.dumps(record,ensure_ascii=False)+'\n')
        f.flush()
        os.fsync(f.fileno())

def reserve(role,slot,job):
    doc,data,_,_=job
    track=STATE_ROOT/(data['task_id']+'.json')
    if track.exists():
        # No retries on uncertain send, no duplicate across rollover/restart.
        return False,'ALREADY_ATTEMPTED'
    record={'task_id':data['task_id'],'role':role,'slot':slot['key'],
            'status':'RESERVED_BEFORE_UPLOAD','started_at':dt.datetime.now(KST).isoformat(),
            'input_sha256':data['input_sha256']}
    atomic_json(track,record)
    audit(record)
    return True,record

def update(track,status,**details):
    data=json.loads(track.read_text('utf-8'))
    data.update(status=status,updated_at=dt.datetime.now(KST).isoformat(),**details)
    atomic_json(track,data)
    audit(data)

def visible_editor(page):
    for selector in ('#prompt-textarea','[data-testid="composer-input"]',
      '[contenteditable="true"][role="textbox"]','[contenteditable="true"][data-lexical-editor]'):
        loc=page.locator(selector)
        for i in range(min(loc.count(),3)):
            if loc.nth(i).is_visible():return loc.nth(i)
    return None

def new_project_chat(context):
    if not PROJECT.startswith('https://chatgpt.com/g/g-p-'):
        raise RuntimeError('PROJECT_URL_NOT_VALIDATED')
    page=context.new_page()
    page.goto(PROJECT,wait_until='domcontentloaded',timeout=85000)
    page.wait_for_timeout(2000)
    btn=None
    for selector in ('button[data-testid="new-chat-button"]',
       'a[href$="/new"]','[data-testid="new-chat-button"]'):
        loc=page.locator(selector)
        if loc.count() and loc.first.is_visible():btn=loc.first;break
    if btn is None:
        for label in ('새 채팅','New chat','새 대화'):
            loc=page.get_by_role('button',name=label,exact=False)
            if loc.count() and loc.first.is_visible():btn=loc.first;break
    if btn is None:raise RuntimeError('PROJECT_NEW_CHAT_NOT_FOUND')
    btn.click(timeout=5000)
    page.wait_for_timeout(1600)
    if visible_editor(page) is None:raise RuntimeError('LOGIN_OR_COMPOSER_NOT_READY')
    return page

def upload(page,png):
    inp=page.locator('input[type="file"]')
    if not inp.count():
        for label in ('Attach','Add photos','Upload files','첨부','파일 추가','추가'):
            try:
                button=page.get_by_role('button',name=re.compile(re.escape(label),re.I))
                if button.count() and button.first.is_visible():
                    button.first.click(timeout=3000)
                    inp=page.locator('input[type="file"]')
                    if inp.count():break
            except Exception:pass
    if not inp.count():raise RuntimeError('UPLOAD_INPUT_NOT_FOUND')
    inp.first.set_input_files(str(png))
    page.wait_for_timeout(2400)
    # Attachment input carries the selected image. We cannot assume the upload is remote yet.
    if not (page.locator('img').count() or page.locator('[data-testid*="attachment"]').count()):
        raise RuntimeError('ATTACHMENT_PREVIEW_NOT_VERIFIED')

def collect_images(page):
    cards=page.locator('[data-message-author-role="assistant"]')
    if not cards.count():return []
    try:
        return cards.last.locator('img').evaluate_all('(e)=>e.map(i=>({src:i.currentSrc||i.src,w:i.naturalWidth,h:i.naturalHeight}))')
    except Exception:return []

def download_one_image(page,old,outfile,seconds):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        got=[i for i in collect_images(page) if i['src'] not in old and i['w']>=512 and i['h']>=512]
        if len(got)==1 and (got[0]['src'].startswith('https:') or got[0]['src'].startswith('blob:')):
            url=got[0]['src']
            data=page.evaluate('''async url => {const r=await fetch(url,{credentials:'include'});
               if(!r.ok) return null; const b=await r.blob(); if(!b.type.startsWith('image/')) return null;
               return Array.from(new Uint8Array(await b.arrayBuffer()));}''',url)
            if data and len(data)<40000000:
                raw=bytes(data)
                try:Image.open(io.BytesIO(raw)).verify()
                except Exception:raise RuntimeError('CAPTURED_IMAGE_INVALID')
                outfile.parent.mkdir(parents=True,exist_ok=True)
                outfile.write_bytes(raw)
                return raw
        if len(got)>1:raise RuntimeError('AMBIGUOUS_MULTIPLE_GENERATED_IMAGES')
        page.wait_for_timeout(5000)
    raise RuntimeError('GENERATION_TIMEOUT')

def qa(raw, expected, output):
    result={'technical_qa':'HOLD','review':'REQUIRED','expected_slots':expected}
    try:
        with Image.open(io.BytesIO(raw)) as im:
            result.update(size=list(im.size),source_mode=im.mode,source_format=im.format)
            if im.format!='PNG' or im.mode!='RGBA':
                result['reason']='NOT_NATIVE_RGBA_PNG';return result
            alpha=im.getchannel('A')
            hist=alpha.histogram()
            transparent=sum(hist[:16])/max(1,im.width*im.height)
            foreground=sum(hist[64:])/max(1,im.width*im.height)
            result.update(transparent_ratio=round(transparent,4),foreground_ratio=round(foreground,4))
            if min(im.size)<600 or transparent<0.25 or foreground<0.005 or foreground>0.8:
                result['reason']='SIZE_OR_ALPHA_DENSITY';return result
            # Don't claim spellings/slot alignment passed without semantic vision verification.
            result.update(technical_qa='PASS',reason='RGBA_ALPHA_ONLY_SEMANTIC_QA_PENDING')
            return result
    except Exception as e:
        result['reason']=type(e).__name__;return result

def browser_job(context,slot,job):
    doc,data,png,prompt=job
    page=None
    try:
        page=new_project_chat(context)
    except Exception as exc:
        try: page.close()
        except Exception: pass
        return 'HOLD_LOGIN_OR_NEW_CHAT: '+type(exc).__name__
    ok,rec=reserve(slot['role'],slot,job)
    if not ok:return rec
    track=STATE_ROOT/(data['task_id']+'.json')
    try:
        upload(page,png)
        editor=visible_editor(page)
        if editor is None:raise RuntimeError('COMPOSER_NOT_FOUND')
        text=prompt.read_text('utf8')
        if '@이미지 생성' not in text:raise RuntimeError('IMAGEGEN_MENTION_MISSING')
        editor.fill(text)
        if text[:30] not in editor.inner_text():raise RuntimeError('PROMPT_NOT_VERIFIED')
        if not AUTO_SEND:
            update(track,'MANUAL_SEND_REQUIRED');return 'MANUAL_SEND_REQUIRED'
        btn=None
        for css in ('button[data-testid="send-button"]','button[aria-label="Send prompt"]','button[aria-label="전송"]'):
            loc=page.locator(css)
            if loc.count() and loc.first.is_visible() and loc.first.is_enabled():btn=loc.first;break
        if btn is None:raise RuntimeError('SEND_BUTTON_NOT_FOUND')
        old={i['src'] for i in collect_images(page)}
        # Mark as uncertain BEFORE click so no duplicate if click times out and request actually sent.
        update(track,'SUBMISSION_UNCERTAIN')
        btn.click(timeout=7000)
        update(track,'SENT')
        dest=OUTPUT_ROOT/slot['role']/(data['task_id']+'_KOR_BATCH.png')
        raw=download_one_image(page,old,dest,int(os.getenv('GENERATION_TIMEOUT_SECONDS','600')))
        evaluation=qa(raw,data['expected_slots'],dest)
        update(track,'CAPTURED_QA_PENDING',output=str(dest),output_sha256=sha(dest),qa=evaluation)
        return 'CAPTURED_QA_PENDING'
    except Exception as exc:
        update(track,'HOLD_NO_AUTORETRY',error=type(exc).__name__+':'+str(exc)[:300]);return 'HOLD_NO_AUTORETRY'
    finally:
        if page is not None:
            try:page.close()
            except Exception:pass

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--at',help='For schedule test: ISO8601 timestamp')
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args()
    if args.at:
        value=dt.datetime.fromisoformat(args.at)
        if value.tzinfo is None:raise SystemExit('timezone required for --at')
        slot=slot_at(value)
        print(json.dumps({'slot':slot,'has_valid_job':bool(load_job(slot['role'])) if slot else False}))
        return
    if args.dry_run:
        for m in SCHEDULE:
            stamp=dt.datetime(2026,10,18,10,m,tzinfo=KST)
            sl=slot_at(stamp)
            print(json.dumps({'minute':m,'role':sl['role'],'has_valid_job':bool(load_job(sl['role']))}))
        return
    if not PROJECT.startswith('https://chatgpt.com/g/g-p-'):
        raise SystemExit('CHATGPT_PROJECT_URL must be verified project url, no fallback to personal/VR project')
    from playwright.sync_api import sync_playwright
    for path in (STATE_ROOT,OUTPUT_ROOT,PROFILE):path.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as playwright:
        context=playwright.chromium.launch_persistent_context(user_data_dir=str(PROFILE),
          headless=False,accept_downloads=True,viewport={'width':1400,'height':960},
          args=['--disable-dev-shm-usage','--no-sandbox'])
        try:
            while True:
                stamp=dt.datetime.now(KST)
                slot=slot_at(stamp)
                if slot and slot['second']<=50:
                    stamp_key=slot['key'];guard=STATE_ROOT/('slot_'+stamp_key.replace(':','-')+'.json')
                    if not guard.exists():
                        atomic_json(guard,{'slot':stamp_key,'role':slot['role'],'visited':True})
                        job=load_job(slot['role'])
                        status=browser_job(context,slot,job) if job else 'IDLE_NO_READY_SOURCE'
                        audit({'slot':stamp_key,'role':slot['role'],'status':status})
                time.sleep(4)
        finally:context.close()
if __name__=='__main__':main()