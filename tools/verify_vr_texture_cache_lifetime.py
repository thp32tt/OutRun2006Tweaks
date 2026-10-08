#!/usr/bin/env python3
"""Catch cross-thread DDS cache LRU ownership and pointer lifetime regressions."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def body(s,marker):
    pos=s.find(marker)
    if pos<0:raise ValueError("missing: "+marker)
    brace=s.find("{",pos)
    depth=0
    for j in range(brace,len(s)):
        if s[j]=="{":depth+=1
        elif s[j]=="}":
            depth-=1
            if depth==0:return s[brace+1:j]
    raise ValueError("unbalanced: "+marker)

def verify(s):
    start=s.find("class FileDataCache")
    end=s.find("// QnD file entry cache",start)
    if start<0 or end<0:raise ValueError("cache class unavailable")
    scope=s[start:end]
    getter=body(scope,"const uint8_t* getFileData(")
    background=body(scope,"void cacheFile(")
    budget=body(scope,"void setMaxCacheSize(")
    tests=[
        ("cache owns shared data", "std::shared_ptr<std::vector<uint8_t>> data;" in scope),
        ("cache owner constructed before read", "std::make_shared<std::vector<uint8_t>>(size)" in background),
        ("preload LRU, budget and publish use mtx1", background.count("std::lock_guard cacheLock(mtx1);")==3),
        ("serialize competing cache loads", "std::lock_guard populationLock(cachePopulationMutex);" in background),
        ("never hold mtx1 while reading disk", "evictToFit(size);\n\t\t}\n\t\tfile.seekg(0, std::ios::beg);" in background),
        ("publish lock acquired only after read", background.rfind("std::lock_guard cacheLock(mtx1);") > background.find("if (!file.read(")),
        ("never open file with cache lock held", "}\n\n\t\tstd::ifstream file(" in background),
        ("cache budget protected", "std::lock_guard _(mtx1);" in budget),
        ("file loads serialized", "std::lock_guard fileRequestLock(mtx2);" in getter),
        ("all cached read+LRU under same mutex", "std::lock_guard cacheLock(mtx1);" in getter),
        ("cache ref returned", "return found->second.data;" in getter),
        ("cache miss read outside cache lock", "cacheFile(filename);" in getter),
        ("cached buffer owner retained through D3DX", "*transientOwner = std::move(owner);" in getter),
        ("both cache and transient pointers are retained", getter.count("return (*transientOwner)->data();")==2),
        ("never return unowned pointer", "if (!transientOwner)" in getter and "return nullptr;" in getter),
        ("cache miss transient owner still retained", "std::make_shared<std::vector<uint8_t>>(" in getter),
        ("evict size uses current owner", "found->second.data->size()" in scope),
        ("getCacheSize synchronized", "std::lock_guard cacheLock(mtx1);" in body(scope,"std::size_t getCacheSize() const")),
        ("UI and scene D3DX wrappers own texture buffer", s.count("std::shared_ptr<std::vector<uint8_t>> transientTextureData;")>=5),
        ("DDS loader gets owner", "FileData.getFileData(" in s and "path_load, &size, &transientOwner);" in s),
    ]
    for label,ok in tests:
        if not ok:raise ValueError(label)
    if "std::vector<uint8_t> data;" in scope:
        raise ValueError("bare evictable cached vector returned")
    if "return it->second.data.data();" in scope:
        raise ValueError("unowned cached data pointer")
    return len(tests)

def mutations(s):
    tokens=[
        "std::shared_ptr<std::vector<uint8_t>> data;",
        "std::make_shared<std::vector<uint8_t>>(size)",
        "std::lock_guard _(mtx1);",
        "std::lock_guard populationLock(cachePopulationMutex);",
        "evictToFit(size);\n\t\t}\n\t\tfile.seekg(0, std::ios::beg);",
        "std::ifstream file(filename, std::ios::binary | std::ios::ate);",
        "std::lock_guard fileRequestLock(mtx2);",
        "std::lock_guard cacheLock(mtx1);",
        "*transientOwner = std::move(owner);",
        "return (*transientOwner)->data();",
        "return found->second.data;",
        "found->second.data->size()",
        "if (!transientOwner)"
    ]
    for t in tokens:
        corrupt=s.replace(t,"__UNOWNED_EVICTION_HAZARD__",1)
        if corrupt==s:raise ValueError("mutation not applied "+t)
        try:verify(corrupt)
        except ValueError:continue
        raise ValueError("failed to catch "+t)
    return len(tokens)

if __name__=="__main__":
    code=(ROOT/"src/hooks_textures.cpp").read_text(encoding="utf-8")
    try:
        n=verify(code)
        p=mutations(code) if "--self-test" in sys.argv[1:] else 0
    except ValueError as exc:
        sys.exit("DDS CACHE LIFETIME FAIL: "+str(exc))
    print(f"DDS CACHE cross-thread PASS: {n} ownership contracts; negatives={p}/13; runtime UNTESTED")
