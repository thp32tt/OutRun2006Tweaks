#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, os, re, struct, zipfile, zlib
from pathlib import PurePosixPath

STAGES=[
('PALM','Palm Beach'),('LAKE','Deep Lake'),('INDU','Industrial Complex'),('ALPI','Alpine'),('SNOW','Snowy Mountain'),
('CLOU','Cloudy Highland'),('CAST','Castle Wall'),('GHOS','Ghost Forest'),('FORE','Coniferous Forest'),('DESE','Desert'),
('TULI','Tulip Garden'),('METR','Metropolis'),('RUIN','Ancient Ruins'),('CAPE','Cape Way'),('IMPE','Imperial Avenue'),
('BEAC','Sunny Beach'),('SEQU','Big Forest'),('NIAG','Waterfalls'),('LASV','Casino Town'),('ALAS','Ice Scape'),
('GRAN','Canyon'),('SANF','Bay Area'),('AMAZ','Jungle'),('MACH','Lost City'),('YOSE','National Park'),
('MAYA','Legend'),('NEWY','Skyscrapers'),('PRIN','Floral Village'),('FLOR','Milky Way'),('EAST','Giant Statues')]
SID={c:i for i,(c,n) in enumerate(STAGES)}; SNAME={c:n for c,n in STAGES}
SPECIAL={'PALM_T':60,'BEAC_T':61,'PALM_BT':62,'BEAC_BT':63,'PALM_BR':64,'BEAC_BR':65}
SPECIAL_NAME={'PALM_T':'(T) Palm Beach','BEAC_T':'(T) Sunny Beach','PALM_BT':'(Night) Palm Beach','BEAC_BT':'(Night) Sunny Beach','PALM_BR':'(R-Night) Palm Beach','BEAC_BR':'(R-Night) Sunny Beach'}
CANON='68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3'

def sha(b): return hashlib.sha256(b).hexdigest()
def stage_identity(folder):
    u=folder.upper()
    if u in SPECIAL: return SPECIAL[u],SPECIAL_NAME[u],'special'
    if u.endswith('_R') and u[:-2] in SID: return SID[u[:-2]]+30,'(R) '+SNAME[u[:-2]],'reverse'
    if u in SID: return SID[u],SNAME[u],'forward'
    return None,None,'unknown'

def roughness(mask, stage_id, load_coli_type=0):
    if mask==0x2:
        if load_coli_type: return 0.25,False,'junction baseline'
        sp={11:0.73,41:0.73,13:0.79,43:0.79,14:0.76,44:0.76}
        if stage_id in sp:return sp[stage_id],True,'stage wet/water override'
        return 0.25,False,'default road'
    if mask==0x400000:
        if load_coli_type or stage_id in (18,48):return 0.25,False,'junction/Casino exception'
        return 0.90,False,'default'
    t={0x1:0,0x4:.70,0x8:.85,0x10:.90,0x80:.85,0x100:.45,0x200:.35,0x400:.30,0x800:.35,0x1000:.35,0x2000:.35,0x8000:.40,0x100000:.71,0x200000:.80,0x800000:.50}
    return t.get(mask,.31),False,'native table' if mask in t else 'fallback'

def ranges(vals):
    vals=sorted(set(vals)); out=[]
    if not vals:return out
    a=p=vals[0]
    for x in vals[1:]:
        if x==p+1:p=x;continue
        out.append([a,p]);a=p=x
    out.append([a,p]); return out

def f32s(data,o,n):return struct.unpack_from('<'+'f'*n,data,o)

def parse(data, stage_id):
    if len(data)<0x44 or data[4:12]!=b'COLI0200':raise ValueError('not COLI0200')
    payload=struct.unpack_from('<I',data,0x00)[0]
    total=struct.unpack_from('<I',data,0x0c)[0]
    primary=struct.unpack_from('<I',data,0x10)[0]
    rel=list(struct.unpack_from('<9I',data,0x14)); base=4; p=[base+x for x in rel]
    if p[0]!=0x44: raise ValueError(f'unexpected first section {p[0]:#x}')
    if not all(0<=x<=len(data) for x in p): raise ValueError('offset OOB')
    if any(a>b for a,b in zip(p,p[1:])): raise ValueError('nonmonotonic')
    if primary>total:raise ValueError('primary>total')
    if p[4]-p[3] != total*64:raise ValueError('geometry 64B invariant failed')
    if p[5]-p[4] < total*48:raise ValueError('normal 48B minimum failed')
    if p[3]-p[2] < total:raise ValueError('material minimum failed')
    mats=data[p[2]:p[2]+total]
    subtype=data[p[5]:p[5]+total]
    roadsec=list(struct.unpack_from(f'<{total}H',data,p[6])) if p[6]+2*total<=len(data) else []
    light=data[p[8]:p[8]+4*total] if p[8]+4*total<=len(data) else b''
    grid=list(struct.unpack_from('<65536H',data,p[0])) if p[1]-p[0]>=131072 else []
    sec1=data[p[1]:p[2]]
    valid_lists=bad_lists=0; max_candidates=0
    if grid:
        for idx in set(grid):
            off=idx*2
            if off+2>len(sec1):bad_lists+=1;continue
            cnt=struct.unpack_from('<H',sec1,off)[0]
            if off+2+2*cnt>len(sec1):bad_lists+=1;continue
            inds=struct.unpack_from('<'+'H'*cnt,sec1,off+2) if cnt else ()
            if any(i>=total for i in inds):bad_lists+=1;continue
            valid_lists+=1; max_candidates=max(max_candidates,cnt)
    stat=collections.defaultdict(lambda:{'count':0,'primary':0,'flags':collections.Counter(),'subtypes':collections.Counter(),'roadSections':[],'meanY':[],'lightSamples':collections.Counter()})
    records=[]
    for i in range(total):
        fs=f32s(data,p[3]+i*64,15)
        flags,heading=struct.unpack_from('<Hh',data,p[3]+i*64+60)
        ns=f32s(data,p[4]+i*48,12)
        mid=mats[i]; s=stat[mid]; s['count']+=1
        if i<primary:s['primary']+=1
        s['flags'][flags]+=1; s['subtypes'][subtype[i]&0xF]+=1
        if roadsec:s['roadSections'].append(roadsec[i])
        s['meanY'].append(sum(ns[k] for k in (1,4,7,10))/4.0)
        if light:
            q=tuple(light[i*4:i*4+4]); s['lightSamples'][q]+=1
        if i in (0,max(0,primary-1),min(total-1,primary)):
            records.append({'index':i,'materialId':mid,'surfaceMask':f'0x{1<<mid:08X}','corners':[list(fs[j:j+3]) for j in (0,3,6,9)],'center':list(fs[12:15]),'collisionFlags':f'0x{flags:04X}','localHeadingAngle':heading,'normals':[list(ns[j:j+3]) for j in (0,3,6,9)],'subtype':subtype[i]&0xF,'roadSection':roadsec[i] if roadsec else None,'lightBytes':list(light[i*4:i*4+4]) if light else None})
    cat=[]
    for mid,s in sorted(stat.items()):
        mask=1<<mid; rr,water,note=roughness(mask,stage_id)
        vals=s['roadSections']; prim_secs=[roadsec[i] for i in range(primary) if mats[i]==mid] if roadsec else []
        cat.append({'materialId':mid,'surfaceMask':f'0x{mask:08X}','records':s['count'],'primaryRoadRecords':s['primary'],'nativeRoughness':rr,'waterFlag':water,'nativeNote':note,
                    'collisionFlagsTop':[{'flags':f'0x{k:04X}','count':v} for k,v in s['flags'].most_common(12)],
                    'subtypeTop':[{'subtype':k,'count':v} for k,v in s['subtypes'].most_common(12)],
                    'roadSectionMinMax':[min(vals),max(vals)] if vals else None,'primaryRoadSectionRanges':ranges(prim_secs),
                    'meanNormalY':sum(s['meanY'])/len(s['meanY']) if s['meanY'] else None,'nonUpwardFraction':sum(abs(v)<.3 for v in s['meanY'])/len(s['meanY']) if s['meanY'] else None,
                    'lightBytePatternsTop':[{'bytes':list(k),'count':v} for k,v in s['lightSamples'].most_common(8)]})
    return {'format':'COLI0200','size':len(data),'payloadSizeField':payload,'payloadSizeMatches':payload+4==len(data),'collisionCount':total,'primaryRoadCollisionCount':primary,'relativeOffsets':rel,'offsetBase':4,
            'sections':{'spatialGrid':{'offset':p[0],'bytes':p[1]-p[0],'layout':'256x256 u16; cell value is u16-index into candidateLists','validUniqueLists':valid_lists,'badUniqueLists':bad_lists,'maxCandidates':max_candidates},
            'candidateLists':{'offset':p[1],'bytes':p[2]-p[1],'layout':'u16 count; u16 collisionIndex[count]'},
            'materialId':{'offset':p[2],'stride':1,'confirmedFormula':'surfaceMask = 1u << materialId'},
            'geometry':{'offset':p[3],'stride':64,'layout':'vec3 corner[4] + vec3 center + u16 collisionFlags + s16 localHeadingAngle'},
            'cornerNormals':{'offset':p[4],'stride':48,'layout':'vec3 normal[4]'},
            'collisionSubtype':{'offset':p[5],'stride':1,'layout':'low nibble consumed by canonical lookup table at VA 0x5E0DE0'},
            'roadSectionIndex':{'offset':p[6],'stride':2,'layout':'u16; correlates with OnRoadPlace.roadSectionNum'},
            'relocatedStructure':{'offset':p[7],'bytes':p[8]-p[7],'status':'OPEN; loader relocates nested offsets/pointers'},
            'cornerLighting':{'offset':p[8],'stride':4,'layout':'4 x u8 corner intensity; canonical helper normalizes by 1/255 and contributes to vehicle lightRate'}},
            'materialCatalog':cat,'primarySubtypeAllZero':all((x&0xF)==0 for x in subtype[:primary]),'samples':records}

def grid_cell(x,z):
    # Canonical helper 0x43CB40. Inputs must already be collision-set-local.
    ix=max(0,min(255,int((x+3072.0)/6.0))); iz=max(0,min(255,int((z+3072.0)/6.0)))
    return iz*256+ix,ix,iz

def lookup_candidates(parsed_data, x,z):
    # x/z here are collision-set-local, not raw world position.
    total=struct.unpack_from('<I',parsed_data,0x0c)[0]; rel=list(struct.unpack_from('<9I',parsed_data,0x14)); p=[4+r for r in rel]
    cell,ix,iz=grid_cell(x,z); idx=struct.unpack_from('<H',parsed_data,p[0]+cell*2)[0]; off=p[1]+idx*2
    cnt=struct.unpack_from('<H',parsed_data,off)[0]; inds=list(struct.unpack_from('<'+'H'*cnt,parsed_data,off+2)) if cnt else []
    return {'cell':cell,'xCell':ix,'zCell':iz,'candidateListIndexU16':idx,'collisionIndices':inds,'valid':all(i<total for i in inds)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage_zip');ap.add_argument('-o','--output',required=True);args=ap.parse_args()
    files=[]
    with zipfile.ZipFile(args.stage_zip) as z:
        for info in z.infolist():
            if not re.search(r'/coli_(?:CS|BK)_.*_bin\.sz$',info.filename,re.I):continue
            raw=z.read(info.filename); data=zlib.decompress(raw); folder=PurePosixPath(info.filename).parts[-2]; sid,name,var=stage_identity(folder)
            rec={'path':info.filename,'folder':folder,'stageId':sid,'stageName':name,'variant':var,'compressedBytes':len(raw),'inflatedBytes':len(data),'compressedSha256':sha(raw),'inflatedSha256':sha(data),'magic':data[4:12].decode('ascii','replace')}
            if rec['magic']=='COLI0200': rec['collision']=parse(data,sid)
            else:rec['collision']={'format':rec['magic'],'status':'legacy-not-decoded'}
            files.append(rec)
    cur=[x for x in files if x['magic']=='COLI0200']; allm=collections.Counter(); prim=collections.Counter()
    for item in cur:
        for m in item['collision']['materialCatalog']:
            allm[m['materialId']]+=m['records'];prim[m['materialId']]+=m['primaryRoadRecords']
    report={'schema':'outrun-stage-coli-ffb-map-v3','source':{'file':os.path.basename(args.stage_zip),'sizeBytes':os.path.getsize(args.stage_zip),'sha256':sha(open(args.stage_zip,'rb').read())},'canonicalExeSha256':CANON,
    'canonicalExeAnchors':{'gridCellHelper':'VA 0x0043CB40: clamp(int((x+3072)/6),0,255), same for z; return zCell<<8|xCell','candidateListUse':'VA 0x0043E7E0: section0[cell] is u16 index into section1; section1 record is count + collision indices','materialMask':'VA 0x0043ECB8..0x0043ECC7: surfaceMask=1u<<materialId','geometryFlags':'VA 0x0043D440 returns geometry+0x3C u16; result flows to EVWORK_CAR+0x25C','heading':'VA 0x0043D340 reads geometry+0x3E s16 and combines with stage angle','lighting':'VA 0x0043D130 reads 4 section8 bytes, scales by 1/255; caller 0x004A45F0 contributes to car lightRate','subtype':'VA 0x0050422D: section5 byte &0xF indexed through table 0x005E0DE0','fourContactMaskWrites':'VA 0x004757FA..0x00475821 -> EVWORK_CAR+0x24C/+0x250/+0x254/+0x258'},
    'summary':{'collisionFiles':len(files),'currentColi0200':len(cur),'legacyColi0105':len(files)-len(cur),'materialIdsObserved':[f'0x{x:02X}' for x in sorted(allm)],'primaryRoadMaterialIdsObserved':[f'0x{x:02X}' for x in sorted(k for k,v in prim.items() if v)]},
    'globalMaterialCounts':[{'materialId':k,'surfaceMask':f'0x{1<<k:08X}','records':allm[k],'primaryRoadRecords':prim[k],'nativeRoughness':roughness(1<<k,-1)[0]} for k in sorted(allm)],
    'contactOrdering':{'status':'PARTIAL','loop':'contact index i=0..3 uses vector_130[i] and global wheel-work pointer 0x82EA38[i], writes surfaceMask to +0x24C+4*i','topologyEvidence':'matching four local direction constants are (-X,-Z),(+X,-Z),(-X,+Z),(+X,+Z); indices 0/1 and 2/3 form longitudinal pairs; 0/2 and 1/3 form lateral pairs','frontRearAndLeftRightNames':'OPEN until vehicle local-axis convention is proved'},
    'files':files}
    with open(args.output,'w',encoding='utf-8') as out:json.dump(report,out,ensure_ascii=False,indent=2);out.write('\n')
    print(json.dumps(report['summary'],ensure_ascii=False)); print(args.output)
if __name__=='__main__':main()
