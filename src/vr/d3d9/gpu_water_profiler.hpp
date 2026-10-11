#pragma once
// Opt-in DX9Ex GPU timestamp + sparse blend-state measurement.
// Timestamp intervals include possible GPU idle gaps; not water attribution.
#include <d3d9.h>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
namespace OutRunVRStereo::GpuWaterProbe {
inline bool Enabled() noexcept {
    static const bool on=[] { const char* v=std::getenv("OUTRUN_VR_GPU_PROFILE"); return v && std::strcmp(v,"1")==0; }();
    return on;
}
struct Slot {
    IDirect3DQuery9 *disjoint=nullptr,*freq=nullptr,*begin=nullptr,*end=nullptr,*sampleBegin=nullptr,*sampleEnd=nullptr;
    bool pending=false,sampleSet=false,blend=false;
    unsigned draws=0, samples=0, blendSamples=0, alphaTestSamples=0, pick=0;
    void release() noexcept {
        for(IDirect3DQuery9** q : {&disjoint,&freq,&begin,&end,&sampleBegin,&sampleEnd}) {
            if(*q) { (*q)->Release(); *q=nullptr; }
        }
        pending=sampleSet=false;
    }
    ~Slot(){ release(); }
    bool create(IDirect3DDevice9* d) noexcept {
        if(begin) return true;
        if(FAILED(d->CreateQuery(D3DQUERYTYPE_TIMESTAMPDISJOINT,&disjoint)) ||
           FAILED(d->CreateQuery(D3DQUERYTYPE_TIMESTAMPFREQ,&freq)) ||
           FAILED(d->CreateQuery(D3DQUERYTYPE_TIMESTAMP,&begin)) ||
           FAILED(d->CreateQuery(D3DQUERYTYPE_TIMESTAMP,&end)) ||
           FAILED(d->CreateQuery(D3DQUERYTYPE_TIMESTAMP,&sampleBegin)) ||
           FAILED(d->CreateQuery(D3DQUERYTYPE_TIMESTAMP,&sampleEnd))) {
            release(); return false;
        }
        return true;
    }
};
class Meter {
    std::array<Slot,4> ring_{};
    Slot* active_=nullptr;
    IDirect3DDevice9* game_=nullptr; // borrowed; invalidated before Reset
    unsigned next_=0,lastDraws_=1024;
    std::uint64_t frame_=0, samples_=0, alpha_=0, alphaTest_=0, frames_=0, dropped_=0, invalid_=0, timedBlend_=0, timedOpaque_=0;
    double sumFrame_=0,maxFrame_=0,sumBlend_=0,sumOpaque_=0;
    ULONGLONG logAt_=0;
    bool unsupported_=false,skip_=false;
    template<typename T> static HRESULT read(IDirect3DQuery9* q,T& v) noexcept {
        return q->GetData(&v,sizeof(v),0); // no flush or busy waiting
    }
    void poll() noexcept {
        for(Slot& s:ring_) {
            if(!s.pending) continue;
            UINT64 a=0,b=0,f=0,x=0,y=0; BOOL disjoint=TRUE;
            const HRESULT ready=read(s.end,b);
            if(ready==S_FALSE) continue;
            const HRESULT p=ready==S_OK?read(s.begin,a):ready;
            const HRESULT q=ready==S_OK?read(s.freq,f):ready;
            const HRESULT r=ready==S_OK?read(s.disjoint,disjoint):ready;
            const HRESULT t=ready==S_OK&&s.sampleSet?read(s.sampleBegin,x):S_OK;
            const HRESULT u=ready==S_OK&&s.sampleSet?read(s.sampleEnd,y):S_OK;
            if(p==S_FALSE||q==S_FALSE||r==S_FALSE||t==S_FALSE||u==S_FALSE) continue;
            s.pending=false;
            if(ready!=S_OK||p!=S_OK||q!=S_OK||r!=S_OK||t!=S_OK||u!=S_OK||disjoint||!f||b<a||(s.sampleSet&&y<x)) { ++invalid_; continue; }
            const double ms=double(b-a)*1000.0/double(f);
            ++frames_; sumFrame_+=ms; if(ms>maxFrame_) maxFrame_=ms;
            samples_+=s.samples; alpha_+=s.blendSamples; alphaTest_+=s.alphaTestSamples;
            if(s.sampleSet) {
                const double drawMs=double(y-x)*1000.0/double(f);
                if(s.blend){++timedBlend_;sumBlend_+=drawMs;}else{++timedOpaque_;sumOpaque_+=drawMs;}
            }
        }
    }
    void log() noexcept {
        ULONGLONG now=GetTickCount64();
        if(!logAt_) { logAt_=now; return; }
        if(now-logAt_<5000) return;
        spdlog::info("VR GPU WATER 5s: gpuIntervals={} gpuSpanAvgMs={:.3f} gpuSpanMaxMs={:.3f} sampledBlendDrawAvgMs={:.4f} sampledOpaqueDrawAvgMs={:.4f} blendDraws={} opaqueDraws={} stateSamples={} alphaBlendSamples={} alphaTestSamples={} dropped={} invalid={} waterAttribution=UNPROVEN",
            frames_,frames_?sumFrame_/frames_:0.0,maxFrame_,
            timedBlend_?sumBlend_/timedBlend_:0.0,timedOpaque_?sumOpaque_/timedOpaque_:0.0,
            timedBlend_,timedOpaque_,samples_,alpha_,alphaTest_,dropped_,invalid_);
        samples_=alpha_=alphaTest_=frames_=dropped_=invalid_=timedBlend_=timedOpaque_=0;
        sumFrame_=maxFrame_=sumBlend_=sumOpaque_=0; logAt_=now;
    }
public:
    void reset() noexcept {
        active_=nullptr; for(Slot& s:ring_) s.release();
        game_=nullptr; unsupported_=skip_=false;
    }
    bool beforeDraw(IDirect3DDevice9* d,UINT /*primitives*/) noexcept {
        if(!Enabled()||!d||unsupported_||skip_) return false;
        if(game_&&game_!=d) reset();
        game_=d;
        if(!active_) {
            Slot& s=ring_[next_++%ring_.size()];
            if(s.pending) { ++dropped_; skip_=true; return false; }
            if(!s.create(d)) {
                unsupported_=true;
                spdlog::warn("VR GPU WATER: timestamp queries unsupported (disabled); DX9Ex unaffected");
                return false;
            }
            s.draws=s.samples=s.blendSamples=s.alphaTestSamples=0;
            s.sampleSet=false;
            s.pick=static_cast<unsigned>((frame_*997u+13u)%lastDraws_);
            if(FAILED(s.disjoint->Issue(D3DISSUE_BEGIN))||FAILED(s.begin->Issue(D3DISSUE_END))) {
                ++invalid_; skip_=true; return false;
            }
            active_=&s;
        }
        Slot& s=*active_;
        const unsigned i=s.draws++;
        const bool sample=((i+static_cast<unsigned>(frame_*7u))&15u)==0;
        const bool time=i==s.pick;
        if(!sample&&!time) return false;
        DWORD alpha=FALSE,test=FALSE;
        const bool valid=SUCCEEDED(d->GetRenderState(D3DRS_ALPHABLENDENABLE,&alpha)) &&
                         SUCCEEDED(d->GetRenderState(D3DRS_ALPHATESTENABLE,&test));
        if(sample&&valid) { ++s.samples; s.blendSamples+=(alpha!=FALSE); s.alphaTestSamples+=(test!=FALSE); }
        if(!time||!valid||FAILED(s.sampleBegin->Issue(D3DISSUE_END))) return false;
        s.sampleSet=true; s.blend=alpha!=FALSE; return true;
    }
    void afterDraw(bool timed) noexcept {
        if(timed&&active_&&FAILED(active_->sampleEnd->Issue(D3DISSUE_END))) active_->sampleSet=false;
    }
    void beforePresent(IDirect3DDevice9* d) noexcept {
        if(!Enabled()||!d||d!=game_) return;
        if(active_) {
            Slot& s=*active_;
            if(s.draws) lastDraws_=s.draws;
            if(SUCCEEDED(s.end->Issue(D3DISSUE_END)) &&
               SUCCEEDED(s.freq->Issue(D3DISSUE_END)) &&
               SUCCEEDED(s.disjoint->Issue(D3DISSUE_END))) s.pending=true;
            else ++invalid_;
            active_=nullptr;
        }
        ++frame_; skip_=false;
    }
    void afterPresent(IDirect3DDevice9* d) noexcept {
        if(!Enabled()||!d||d!=game_) return;
        poll(); log();
    }
};
inline Meter& instance() noexcept { static Meter value; return value; }
}
