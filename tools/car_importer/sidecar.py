"""Experimental OVRCABH2 export bridge. No game assets modified."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import zlib

HEADER = b"OVRCABH2"
MAX_FILE = 128*1024*1024
class SidecarError(ValueError):
    pass

def sha256(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def inspect_ovc(path):
    path=Path(path)
    if not path.is_file() or not 36 <= path.stat().st_size <= MAX_FILE:
        raise SidecarError("OVC size invalid")
    data=path.read_bytes()
    if data[:8]!=HEADER:raise SidecarError("Unsupported OVC header")
    version,groups,mats,verts,tris,payload_size,crc=struct.unpack_from('<7I',data,8)
    if version!=2 or not 0<groups<=512 or not 0<mats<=64 or verts>1000000 or tris>2000000:
        raise SidecarError("OVC limits rejected")
    if payload_size!=len(data)-36 or zlib.crc32(data[36:])!=crc:
        raise SidecarError("OVC payload integrity/CRC failed")
    pos=36
    vtotal=0;ttotal=0
    for _ in range(groups):
        if pos+16>len(data):raise SidecarError("OVC group truncated")
        name_len,mat,nv,ni,idxwidth=struct.unpack_from('<HHIII',data,pos);pos+=16
        if not 0<name_len<=256 or mat>=mats or not 3<=nv<=65535 or ni<3 or ni%3 or idxwidth!=2:
            raise SidecarError("OVC group bounds invalid")
        needed=name_len+nv*32+ni*2
        if pos+needed>len(data):raise SidecarError("OVC group data truncated")
        label=data[pos:pos+name_len]
        if b'\x00' in label:raise SidecarError("OVC group name invalid")
        pos+=name_len
        for (value,) in struct.iter_unpack('<f',data[pos:pos+nv*32]):
            if not math.isfinite(value) or abs(value)>=10000:
                raise SidecarError("OVC vertex invalid")
        pos+=nv*32
        for (ix,) in struct.iter_unpack('<H',data[pos:pos+ni*2]):
            if ix>=nv:raise SidecarError("OVC index invalid")
        pos+=ni*2
        vtotal+=nv;ttotal+=ni//3
    if vtotal!=verts or ttotal!=tris:raise SidecarError("OVC geometry totals mismatch")
    for _ in range(mats):
        if pos+4>len(data):raise SidecarError("OVC material truncated")
        length=struct.unpack_from('<I',data,pos)[0];pos+=4
        if length<128 or pos+length>len(data):raise SidecarError("OVC DDS bounds invalid")
        d=data[pos:pos+length]
        if d[:4]!=b'DDS ' or struct.unpack_from('<I',d,4)[0]!=124 or struct.unpack_from('<I',d,76)[0]!=32:
            raise SidecarError("OVC DDS header invalid")
        width,height=struct.unpack_from('<II',d,16)[0],struct.unpack_from('<I',d,12)[0]
        if width<=0 or height<=0 or width>2048 or height>2048 or width&(width-1) or height&(height-1):
            raise SidecarError("OVC DDS image dimensions invalid")
        if struct.unpack_from('<I',d,84)[0]!=0 or struct.unpack_from('<I',d,88)[0]!=32:
            raise SidecarError("OVC only supports ARGB32 test DDS")
        if length!=128+width*height*4:raise SidecarError("OVC DDS payload size invalid")
        pos+=length
    if pos!=len(data):raise SidecarError("OVC trailing bytes")
    return {'status':'OVRCABH2_STATIC_PARSE_PASS_RUNTIME_UNTESTED','sha256':sha256(path),
            'groups':groups,'materials':mats,'vertices':verts,'triangles':tris,
            'size_bytes':len(data),'game_installable':False}

def export_experimental_ovc(staged_blend, blender_exe, output_dir, rights_confirmed=False, timeout=240):
    if not rights_confirmed:raise SidecarError("Source model usage/conversion permission must be verified")
    source=Path(staged_blend).expanduser().resolve(strict=True)
    if source.name!='staged_car.blend':raise SidecarError("Input must be a staged_car.blend created by this importer")
    exe=Path(blender_exe).expanduser().resolve(strict=True)
    out=Path(output_dir).expanduser().resolve()
    if not exe.is_file() or not source.is_file():raise SidecarError("Invalid Blender or staged .blend")
    if out==source.parent or source.parent in out.parents:
        # Separate output is allowed in output_dir/ovc_test, but never overwrite staged scene
        if out==source.parent:raise SidecarError("Choose a separate OVC output subfolder")
    for parent in (out,*out.parents):
        if any((parent/name).is_file() for name in ('OR2006C2C.exe','OR2006C2C.EXE','or2006c2c.exe')):
            raise SidecarError("Never export into the installed game directory")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise SidecarError("OVC output folder must be empty")
    out.mkdir(parents=True,exist_ok=True)
    worker=Path(__file__).with_name('sidecar_worker.py')
    if not worker.is_file():raise SidecarError("OVC Blender worker missing")
    file=out/'f50_external_test.ovc'
    args=[str(exe),'--background','--factory-startup','--disable-autoexec','--python',str(worker),
          '--','--blend',str(source),'--output',str(file)]
    try:
        r=subprocess.run(args,capture_output=True,text=True,timeout=timeout,check=False,
                         env={**os.environ,'PYTHONUTF8':'1'})
    except subprocess.TimeoutExpired as exc:
        raise SidecarError("OVC Blender timeout; game unchanged") from exc
    if r.returncode!=0 or not file.is_file():
        raise SidecarError("OVC Blender export failed: "+(r.stdout+'\n'+r.stderr)[-2500:])
    result=inspect_ovc(file)
    manifest=json.loads(file.with_suffix('.json').read_text(encoding='utf-8'))
    if result['sha256']!=manifest.get('sidecar_sha256') or result['triangles']!=manifest.get('triangles'):
        raise SidecarError("OVC worker and independent validator disagree")
    result.update({'output':str(file),'source_sha256':sha256(source),
                   'game_files_modified':False,'status':'EXPERIMENTAL_OVC_VALIDATED_NOT_GAME_LOADED'})
    (out/'validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return result
def install_test_sidecar(game_root, sidecar_file, rights_confirmed=False):
    """Only writes an optional sidecar under CarImporter/f50; never touches Cars/.
    Game DLL remains separate and must be installed/removed by the user.
    """
    if not rights_confirmed:raise SidecarError("Permission confirmation required")
    from .game import verify_game
    info=verify_game(game_root,'f50')
    game=Path(info['root'])
    src=Path(sidecar_file).resolve(strict=True)
    if src.name!='f50_external_test.ovc' or game in src.parents:
        raise SidecarError("Choose external f50_external_test.ovc outside game folder")
    pre=inspect_ovc(src)
    folder=game/'CarImporter'/'f50'
    for p in (game/'CarImporter', folder):
        if p.is_symlink():raise SidecarError("Symlinked sidecar output path refused")
    folder.mkdir(parents=True,exist_ok=True)
    dst=folder/'f50_external_test.ovc'
    receipt=folder/'sidecar_install_receipt.json'
    if dst.exists() or dst.is_symlink() or receipt.exists():
        raise SidecarError("Existing test sidecar or receipt; refusing overwrite")
    import shutil
    try:
        with src.open('rb') as f, dst.open('xb') as out:
            shutil.copyfileobj(f,out,1024*1024)
            out.flush();os.fsync(out.fileno())
        if sha256(dst)!=pre['sha256']:raise SidecarError("Copied sidecar SHA verification failed")
        data={'status':'F50_SIDECAR_ONLY_INSTALLED_NO_NATIVE_PMT_CHANGED',
              'source_sha256':pre['sha256'], 'source_game_pmt_sha256':info['source_sha256'],
              'relative_path':'CarImporter/f50/f50_external_test.ovc'}
        with receipt.open('x',encoding='utf-8') as out:
            json.dump(data,out,indent=2);out.write('\n')
        return {'status':data['status'],'sidecar_file':str(dst),'sidecar_sha256':pre['sha256'],
                'game_files_modified':False,'original_pmt_unchanged':True,
                'runtime_tested':False,'game_setting':'[VR] F50ExternalModelTest=true'}
    except BaseException:
        dst.unlink(missing_ok=True)
        receipt.unlink(missing_ok=True)
        raise

def remove_test_sidecar(game_root):
    """Remove only importer-owned OVC whose receipt SHA matches; do not touch PMT."""
    from .game import verify_game
    info=verify_game(game_root,'f50')
    folder=Path(info['root'])/'CarImporter'/'f50'
    dst=folder/'f50_external_test.ovc'
    receipt=folder/'sidecar_install_receipt.json'
    if folder.is_symlink() or dst.is_symlink() or receipt.is_symlink():
        raise SidecarError("Symlinked sidecar file refused")
    if not dst.is_file() or not receipt.is_file():
        raise SidecarError("No importer-owned sidecar and matching receipt")
    data=json.loads(receipt.read_text(encoding='utf-8'))
    if data.get('status')!='F50_SIDECAR_ONLY_INSTALLED_NO_NATIVE_PMT_CHANGED' or \
       data.get('source_game_pmt_sha256')!=info['source_sha256'] or \
       sha256(dst)!=data.get('source_sha256'):
        raise SidecarError("Unknown or edited sidecar; no files removed")
    dst.unlink()
    receipt.unlink()
    return {'status':'F50_TEST_SIDECAR_REMOVED_NO_NATIVE_PMT_CHANGED',
            'game_files_modified':False,'original_pmt_unchanged':True}
