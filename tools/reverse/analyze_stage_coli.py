#!/usr/bin/env python3
import argparse, collections, hashlib, json, os, re, struct, zipfile, zlib
from pathlib import PurePosixPath

STAGES = [
 ('PALM','Palm Beach'),('LAKE','Deep Lake'),('INDU','Industrial Complex'),('ALPI','Alpine'),('SNOW','Snowy Mountain'),
 ('CLOU','Cloudy Highland'),('CAST','Castle Wall'),('GHOS','Ghost Forest'),('FORE','Coniferous Forest'),('DESE','Desert'),
 ('TULI','Tulip Garden'),('METR','Metropolis'),('RUIN','Ancient Ruins'),('CAPE','Cape Way'),('IMPE','Imperial Avenue'),
 ('BEAC','Sunny Beach'),('SEQU','Big Forest'),('NIAG','Waterfalls'),('LASV','Casino Town'),('ALAS','Ice Scape'),
 ('GRAN','Canyon'),('SANF','Bay Area'),('AMAZ','Jungle'),('MACH','Lost City'),('YOSE','National Park'),
 ('MAYA','Legend'),('NEWY','Skyscrapers'),('PRIN','Floral Village'),('FLOR','Milky Way'),('EAST','Giant Statues')]
STAGE_ID={c:i for i,(c,_) in enumerate(STAGES)}
STAGE_NAME={c:n for c,n in STAGES}
SPECIAL={'PALM_T':60,'BEAC_T':61,'PALM_BT':62,'BEAC_BT':63,'PALM_BR':64,'BEAC_BR':65}
SPECIAL_NAME={'PALM_T':'(T) Palm Beach','BEAC_T':'(T) Sunny Beach','PALM_BT':'(Night) Palm Beach','BEAC_BT':'(Night) Sunny Beach','PALM_BR':'(R-Night) Palm Beach','BEAC_BR':'(R-Night) Sunny Beach'}
CANON_EXE='68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3'

def sha(b): return hashlib.sha256(b).hexdigest()

def stage_identity(folder):
    u=folder.upper()
    if u in SPECIAL: return SPECIAL[u], SPECIAL_NAME[u], 'special'
    if u.endswith('_R') and u[:-2] in STAGE_ID:
        c=u[:-2]; return STAGE_ID[c]+30, '(R) '+STAGE_NAME[c], 'reverse'
    if u in STAGE_ID: return STAGE_ID[u], STAGE_NAME[u], 'forward'
    return None,None,'unknown'

def roughness(mask, stage_id, load_coli_type=0):
    if mask==0x2:
        if load_coli_type: return 0.25, False, 'junction forces baseline'
        special={11:0.73,41:0.73,13:0.79,43:0.79,14:0.76,44:0.76}
        if stage_id in special: return special[stage_id], True, 'stage wet/water override'
        return 0.25, False, 'default primary-road baseline'
    if mask==0x400000:
        if load_coli_type: return 0.25, False, 'junction forces baseline'
        if stage_id in (18,48): return 0.25, False, 'Casino Town exception'
        return 0.90, False, 'default 0x400000 behavior'
    table={0x1:0.0,0x4:0.70,0x8:0.85,0x10:0.90,0x80:0.85,0x100:0.45,0x200:0.35,
           0x400:0.30,0x800:0.35,0x1000:0.35,0x2000:0.35,0x8000:0.40,0x100000:0.71,
           0x200000:0.80,0x800000:0.50}
    return table.get(mask,0.31), False, 'native fallback' if mask not in table else 'native table'

def parse_current(data, stage_id):
    if len(data)<64 or data[4:12]!=b'COLI0200': raise ValueError('not COLI0200')
    total, primary = struct.unpack_from('<II',data,0x0c)
    rel=list(struct.unpack_from('<9I',data,0x14)); base=4
    p=[base+x for x in rel]
    if any(x<0 or x>len(data) for x in p): raise ValueError('section pointer OOB')
    if any(a>b for a,b in zip(p,p[1:])): raise ValueError('non-monotonic sections')
    if primary>total: raise ValueError('primary count > total')
    if p[4]-p[3] != total*64: raise ValueError('geometry stride mismatch')
    if p[5]-p[4] < total*48: raise ValueError('normal section too small')
    if p[3]-p[2] < total: raise ValueError('material section too small')

    mats=bytes(data[p[2]:p[2]+total])
    subtype=bytes(data[p[5]:p[5]+total])
    roadsec=list(struct.unpack_from(f'<{total}H',data,p[6])) if p[6]+total*2<=len(data) else []

    samples=[]
    for i in sorted(set([0, max(0,primary-1), min(total-1,primary)])):
        if i<0 or i>=total: continue
        fs=struct.unpack_from('<15f',data,p[3]+i*64)
        flags=struct.unpack_from('<I',data,p[3]+i*64+60)[0]
        ns=struct.unpack_from('<12f',data,p[4]+i*48)
        samples.append({
            'index':i,'materialId':mats[i],
            'geometry':{'corners':[list(fs[j:j+3]) for j in (0,3,6,9)],'center':list(fs[12:15]),'flags':f'0x{flags:08X}'},
            'normals':[list(ns[j:j+3]) for j in (0,3,6,9)],
            'subtype':subtype[i],
            'roadSectionIndex':roadsec[i] if roadsec else None})

    def matmeta(counter, limit):
        out=[]
        for mid,count in sorted(counter.items()):
            mask=1<<mid
            rr,water,note=roughness(mask,stage_id)
            inds=[i for i in range(limit) if mats[i]==mid] if limit else []
            runs=1+sum(b!=a+1 for a,b in zip(inds,inds[1:])) if inds else 0
            centers=[]
            for i in inds:
                fs=struct.unpack_from('<15f',data,p[3]+i*64)
                centers.append(fs[12:15])
            bounds=None
            if centers:
                bounds={'x':[min(v[0] for v in centers),max(v[0] for v in centers)],
                        'y':[min(v[1] for v in centers),max(v[1] for v in centers)],
                        'z':[min(v[2] for v in centers),max(v[2] for v in centers)]}
            out.append({'materialId':mid,'surfaceMask':f'0x{mask:08X}','records':count,
                        'fraction':round(count/limit,6) if limit else None,'runs':runs,
                        'nativeRoughness':rr,'setsWaterFlag':water,'nativeNote':note,
                        'centerBounds':bounds})
        return out

    return {
      'format':'COLI0200','size':len(data),'payloadSizeField':struct.unpack_from('<I',data,0)[0],
      'payloadSizeMatches':struct.unpack_from('<I',data,0)[0]+4==len(data),
      'collisionCount':total,'primaryRoadCollisionCount':primary,'relativeOffsets':rel,'offsetBaseBytes':4,
      'sections':{
       'spatialLookup':{'offset':p[0],'bytes':p[1]-p[0],'interpretation':'65536 x u16 spatial lookup/bucket map candidate'},
       'candidateLists':{'offset':p[1],'bytes':p[2]-p[1],'interpretation':'variable collision-candidate lists used by query'},
       'materialId':{'offset':p[2],'bytesMinimum':total,'recordStride':1,'confirmedUse':'surfaceMask = 1u << materialId'},
       'geometry':{'offset':p[3],'bytes':total*64,'recordStride':64,'layout':'vec3 corner[4] + vec3 center + u32 flags'},
       'cornerNormals':{'offset':p[4],'bytes':total*48,'recordStride':48,'layout':'vec3 normal[4]'},
       'collisionSubtype':{'offset':p[5],'bytesMinimum':total,'recordStride':1,'interpretation':'lower nibble consumed through lookup table at canonical EXE VA 0x5E0DE0; semantic names open'},
       'roadSectionIndex':{'offset':p[6],'bytesMinimum':total*2,'recordStride':2,'interpretation':'u16 index compared with OnRoadPlace.roadSectionNum'},
       'section7':{'offset':p[7],'bytes':p[8]-p[7],'interpretation':'open'},
       'section8':{'offset':p[8],'bytes':len(data)-p[8],'interpretation':'open'}},
      'primaryMaterials':matmeta(collections.Counter(mats[:primary]), primary),
      'allMaterials':[{'materialId':m,'surfaceMask':f'0x{1<<m:08X}','records':c,
                       'nativeRoughness':roughness(1<<m,stage_id)[0]}
                      for m,c in sorted(collections.Counter(mats).items())],
      'primarySubtypeAllZero':all(v==0 for v in subtype[:primary]),
      'primaryRoadSectionMax':max(roadsec[:primary]) if roadsec and primary else None,
      'samples':samples}

def read_zip(path):
    out=[]
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            name=info.filename
            if not re.search(r'/coli_(?:CS|BK)_.*_bin\.sz$',name,re.I): continue
            raw=z.read(name)
            try: data=zlib.decompress(raw)
            except Exception as e:
                out.append({'path':name,'compressedBytes':len(raw),'error':str(e)})
                continue
            folder=PurePosixPath(name).parts[-2]
            sid,sname,variant=stage_identity(folder)
            rec={'path':name,'folder':folder,'stageId':sid,'stageName':sname,'variant':variant,
                 'compressedBytes':len(raw),'inflatedBytes':len(data),
                 'compressedSha256':sha(raw),'inflatedSha256':sha(data)}
            magic=data[4:12].decode('ascii','replace') if len(data)>=12 else ''
            rec['magic']=magic
            if magic=='COLI0200': rec['collision']=parse_current(data,sid)
            elif magic.startswith('COLI010'): rec['collision']={'format':magic,'status':'legacy-not-decoded'}
            else: rec['collision']={'format':magic,'status':'unknown'}
            out.append(rec)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('stage_zip')
    ap.add_argument('-o','--output',required=True)
    args=ap.parse_args()

    records=read_zip(args.stage_zip)
    current=[x for x in records if x.get('magic')=='COLI0200']
    legacy=[x for x in records if x.get('magic')!='COLI0200']
    all_counts=collections.Counter()
    primary_counts=collections.Counter()
    for x in current:
        for m in x['collision']['allMaterials']: all_counts[m['materialId']]+=m['records']
        for m in x['collision']['primaryMaterials']: primary_counts[m['materialId']]+=m['records']

    with open(args.stage_zip,'rb') as fh: zip_sha=sha(fh.read())
    report={
      'schema':'outrun-stage-coli-ffb-map-v2',
      'source':{'file':os.path.basename(args.stage_zip),'sizeBytes':os.path.getsize(args.stage_zip),'sha256':zip_sha},
      'canonicalExeSha256':CANON_EXE,
      'confirmedRuntimeAnchors':{
       'collisionSurfaceQuery':'RVA 0x0003DB60 / VA 0x0043EB60',
       'materialReadAndMask':'VA 0x0043ECB8..0x0043ECC7: materialId = materialArray[collisionIndex]; surfaceMask = 1u << materialId',
       'fourContactWriter':'VA 0x004757FA..0x00475821 writes returned masks to EVWORK_CAR+0x24C/+0x250/+0x254/+0x258',
       'geometryUse':'VA 0x0043E833 uses 64-byte collision records',
       'normalUse':'VA 0x0043EA49 uses 48-byte normal records'},
      'summary':{
       'collisionFiles':len(records),'currentColi0200':len(current),'legacy':len(legacy),
       'materialIdsObserved':[f'0x{x:02X}' for x in sorted(all_counts)],
       'primaryMaterialIdsObserved':[f'0x{x:02X}' for x in sorted(primary_counts)]},
      'materialCatalog':[
       {'materialId':m,'surfaceMask':f'0x{1<<m:08X}','allRecords':all_counts[m],
        'primaryRoadRecords':primary_counts[m],'defaultNativeRoughness':roughness(1<<m,-1)[0]}
       for m in sorted(all_counts)],
      'files':records}

    with open(args.output,'w',encoding='utf-8') as fh:
        json.dump(report,fh,ensure_ascii=False,indent=2)
        fh.write('\n')
    print(json.dumps(report['summary'],ensure_ascii=False))
    print(args.output)

if __name__=='__main__':
    main()
