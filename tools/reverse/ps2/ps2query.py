#!/usr/bin/env python3
import argparse
import pathlib
import re
import sqlite3

def hx(v):
    return "-" if v is None else f"0x{v:08X}"

def parse_addr(q):
    q=q.strip()
    return int(q,16) if re.fullmatch(r"(?:0x)?[0-9a-fA-F]{5,8}",q) else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--db",type=pathlib.Path,default=pathlib.Path("ps2_knowledge_map.sqlite"))
    ap.add_argument("--context",type=int,default=8)
    ap.add_argument("--limit",type=int,default=30)
    a=ap.parse_args()
    con=sqlite3.connect(a.db)
    con.row_factory=sqlite3.Row
    addr=parse_addr(a.query)
    if addr is not None:
        anchor=con.execute("select * from anchors where va<=? order by va desc limit 1",(addr,)).fetchone()
        print("ADDRESS",hx(addr))
        if anchor:
            print("NEAREST_ANCHOR",hx(anchor["va"]),anchor["name"],"reasons="+anchor["reasons"])
        for r in con.execute("select * from instructions where va between ? and ? order by va",(addr-a.context*4,addr+a.context*4)):
            print(">" if r["va"]==addr else " ",hx(r["va"]),r["bytes"],r["text"])
        if anchor:
            start=anchor["va"]
            nxt=con.execute("select min(va) from anchors where va>?",(start,)).fetchone()[0] or start+0x1000
            print("CALLS_OUT")
            for r in con.execute("select * from calls where from_va>=? and from_va<? order by from_va",(start,nxt)):
                n=con.execute("select name from anchors where va=?",(r["to_va"],)).fetchone()
                print(" ",hx(r["from_va"]),"->",hx(r["to_va"]),n[0] if n else "")
            print("STRING_REFS")
            for r in con.execute("select sx.from_va,s.value from string_xrefs sx join strings s on s.va=sx.to_va where sx.anchor_va=? order by sx.from_va",(start,)):
                print(" ",hx(r["from_va"]),repr(r["value"][:240]))
    else:
        like="%"+a.query+"%"
        for title,sql,args in [
            ("SEMANTICS","select va,name,tags,confidence from semantics where name like ? or tags like ? limit ?",(like,like,a.limit)),
            ("ANCHORS","select va,name,reasons from anchors where name like ? limit ?",(like,a.limit)),
            ("STRINGS","select va,section,value from strings where value like ? limit ?",(like,a.limit)),
            ("INSTRUCTIONS","select va,text from instructions where text like ? limit ?",(like,a.limit))]:
            rows=con.execute(sql,args).fetchall()
            if rows:
                print(title)
                for r in rows:
                    print("  "+" | ".join(f"{k}={hx(r[k]) if k=='va' else r[k]}" for k in r.keys()))
    con.close()

if __name__=="__main__":
    main()
