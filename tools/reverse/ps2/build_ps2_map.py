#!/usr/bin/env python3
"""Build a reusable PS2 MIPS map from SLPM_666.28 and IOPRP310.IMG.

Requires llvm-objdump. The full one-off analysis package contains richer XREF
exports; this repository version intentionally stays compact and reproducible.
"""
import argparse, hashlib, json, pathlib, re, shutil, sqlite3, struct, subprocess

ROOT=pathlib.Path(__file__).resolve().parents[3]
SEMANTICS_JSON=ROOT/"reverse/ps2/semantics.json"

ALLOC=2
EXEC=4
INS_RE=re.compile(r"^\\s*([0-9a-fA-F]+):\\s+((?:[0-9a-fA-F]{2}\\s+){4})\\s*(.*)$")
CALL_RE=re.compile(r"^(?:jal|bal)\\s+(0x[0-9a-fA-F]+)")

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def align(v,a=16):
    return (v+a-1)//a*a

def elf32(path):
    b=path.read_bytes()
    if b[:6]!=b"\\x7fELF\\x01\\x01":
        raise SystemExit("expected ELF32 little-endian input")
    e=struct.unpack_from("<16sHHIIIIIHHHHHH",b,0)
    entry=e[4]; shoff=e[6]; shentsz=e[11]; shnum=e[12]; shstrndx=e[13]
    raw=[struct.unpack_from("<IIIIIIIIII",b,shoff+i*shentsz) for i in range(shnum)]
    shstr=raw[shstrndx]
    names=b[shstr[4]:shstr[4]+shstr[5]]
    secs=[]
    for i,s in enumerate(raw):
        noff,typ,flags,addr,off,size,link,info,al,entsz=s
        end=names.find(b"\\0",noff)
        name=names[noff:end].decode("ascii","replace") if 0<=noff<len(names) and end>=0 else ""
        secs.append({"index":i,"name":name,"type":typ,"flags":flags,"addr":addr,"offset":off,"size":size})
    gp=None
    for s in secs:
        if s["name"]==".reginfo" and s["size"]>=24:
            gp=struct.unpack_from("<I",b,s["offset"]+20)[0]
    return b,entry,gp,secs

def strings_from_elf(data,secs,minlen=4):
    rows=[]
    for s in secs:
        if not (s["flags"]&ALLOC) or (s["flags"]&EXEC) or s["type"]==8:
            continue
        d=data[s["offset"]:s["offset"]+s["size"]]
        i=0
        while i<len(d):
            j=i
            while j<len(d) and (32<=d[j]<=126 or d[j] in (9,10,13)): j+=1
            if j-i>=minlen:
                rows.append((s["addr"]+i,s["offset"]+i,s["name"],j-i,d[i:j].decode("ascii","replace")))
            i=j+1
    return rows

def disassemble(path,outasm):
    obj=shutil.which("llvm-objdump")
    if not obj:
        raise SystemExit("llvm-objdump is required")
    p=subprocess.run([obj,"-d","--triple=mipsel-unknown-elf",str(path)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    outasm.write_text(p.stdout,encoding="utf-8")
    rows=[]; section=""
    for line in p.stdout.splitlines():
        if line.startswith("Disassembly of section "):
            section=line.split("Disassembly of section ",1)[1].rstrip(":")
            continue
        m=INS_RE.match(line)
        if not m: continue
        va=int(m.group(1),16); raw="".join(m.group(2).split()); text=m.group(3).strip()
        if not text or text=="...": continue
        parts=text.split(None,1)
        rows.append((va,section,raw,parts[0],parts[1] if len(parts)>1 else "",text))
    return rows

def romdir(path):
    b=path.read_bytes(); entries=[]; off=0
    while off+16<=len(b):
        name=b[off:off+10].split(b"\\0",1)[0].decode("ascii","replace")
        ext=struct.unpack_from("<H",b,off+10)[0]
        size=struct.unpack_from("<I",b,off+12)[0]
        if not name: break
        entries.append({"name":name,"extinfo_size":ext,"size":size})
        off+=16
    romdir_size=len(entries)*16+16
    extinfo_size=sum(x["extinfo_size"] for x in entries)
    cur=align(romdir_size+extinfo_size)
    for x in entries:
        if x["name"]=="RESET": x["data_offset"]=None
        elif x["name"]=="ROMDIR": x["data_offset"]=0
        elif x["name"]=="EXTINFO": x["data_offset"]=romdir_size
        else:
            x["data_offset"]=cur
            cur=align(cur+x["size"])
    return {"romdir_size":romdir_size,"extinfo_size":extinfo_size,"data_start":align(romdir_size+extinfo_size),"entries":entries}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("slpm",type=pathlib.Path)
    ap.add_argument("ioprp",type=pathlib.Path)
    ap.add_argument("out",type=pathlib.Path)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    data,entry,gp,secs=elf32(a.slpm)
    ins=disassemble(a.slpm,a.out/"SLPM_666.28.asm")
    strs=strings_from_elf(data,secs)
    exec_ranges=[(s["addr"],s["addr"]+s["size"]) for s in secs if s["flags"]&EXEC]
    calls=[]; anchors={entry:{"entry"}}
    for va,sec,raw,mn,ops,text in ins:
        m=CALL_RE.match(text)
        if m:
            to=int(m.group(1),16)
            calls.append((va,to,mn))
            if any(lo<=to<hi for lo,hi in exec_ranges):
                anchors.setdefault(to,set()).add("call_target")
        if mn in ("addiu","daddiu") and ops.startswith("$sp, $sp, -"):
            anchors.setdefault(va,set()).add("prologue")
    db=a.out/"ps2_knowledge_map.sqlite"
    if db.exists(): db.unlink()
    con=sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE sections(name TEXT,addr INTEGER,offset INTEGER,size INTEGER,flags INTEGER,type INTEGER);
    CREATE TABLE instructions(va INTEGER PRIMARY KEY,section TEXT,bytes TEXT,mnemonic TEXT,operands TEXT,text TEXT);
    CREATE TABLE strings(va INTEGER PRIMARY KEY,file_offset INTEGER,section TEXT,length INTEGER,value TEXT);
    CREATE TABLE anchors(va INTEGER PRIMARY KEY,reasons TEXT,name TEXT);
    CREATE TABLE calls(id INTEGER PRIMARY KEY,from_va INTEGER,to_va INTEGER,type TEXT);
    CREATE TABLE semantics(va INTEGER PRIMARY KEY,name TEXT,tags TEXT,confidence TEXT,evidence TEXT);
    CREATE INDEX calls_from ON calls(from_va);
    CREATE INDEX calls_to ON calls(to_va);
    """)
    meta={"slpm_sha256":sha256(a.slpm),"ioprp_sha256":sha256(a.ioprp),"entry":f"0x{entry:08X}","gp":f"0x{gp:08X}" if gp else None}
    con.executemany("INSERT INTO meta VALUES(?,?)",[(k,json.dumps(v)) for k,v in meta.items()])
    con.executemany("INSERT INTO sections VALUES(?,?,?,?,?,?)",[(s["name"],s["addr"],s["offset"],s["size"],s["flags"],s["type"]) for s in secs])
    con.executemany("INSERT INTO instructions VALUES(?,?,?,?,?,?)",ins)
    con.executemany("INSERT INTO strings VALUES(?,?,?,?,?)",strs)
    con.executemany("INSERT INTO anchors VALUES(?,?,?)",[(va,",".join(sorted(r)),f"sub_{va:08X}") for va,r in sorted(anchors.items())])
    con.executemany("INSERT INTO calls(from_va,to_va,type) VALUES(?,?,?)",calls)
    semantic_rows=[]
    if SEMANTICS_JSON.is_file():
        semantic_doc=json.loads(SEMANTICS_JSON.read_text(encoding="utf-8"))
        for rec in semantic_doc.get("records",[]):
            semantic_rows.append((
                int(rec["va"],16), rec["name"], ",".join(rec.get("tags",[])),
                rec.get("confidence",""), rec.get("evidence","")))
        con.executemany("INSERT OR REPLACE INTO semantics VALUES(?,?,?,?,?)",semantic_rows)
    con.commit()
    integrity=con.execute("pragma integrity_check").fetchone()[0]
    con.close()
    (a.out/"ioprp_romdir.json").write_text(json.dumps(romdir(a.ioprp),indent=2)+"\\n",encoding="utf-8")
    summary={"meta":meta,"counts":{"instructions":len(ins),"strings":len(strs),"calls":len(calls),"anchors":len(anchors),"semantics":len(semantic_rows)},"sqlite_integrity":integrity}
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2)+"\\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
