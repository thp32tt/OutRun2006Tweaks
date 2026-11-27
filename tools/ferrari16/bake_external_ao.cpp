// Offline, private OVC3/4 AO baker using the same parser as the runtime.
// Keep original mesh, albedo, normal, authored ORM and dashboard bytes.
// Approximate geometry-only AO; no source-authored normal/metalness invented.
#include "../../src/vr/game/dino_external_sidecar.hpp"
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <filesystem>
using namespace OutRunVR::DinoSidecar;
using Bytes=std::vector<std::uint8_t>;
struct V {double x,y,z;};
static V operator+(V a,V b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
static V operator-(V a,V b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
static V operator*(V a,double s){return {a.x*s,a.y*s,a.z*s};}
static double dot(V a,V b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static V cross(V a,V b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
static V unit(V a){double d=std::sqrt(dot(a,a));return d>1e-12?a*(1/d):V{};}
static V pos(const Vertex& v){return {v.x,v.y,v.z};}
static V normal(const Vertex& v){return {v.nx,v.ny,v.nz};}
static bool glass(const Mesh& m){return m.name.rfind("F50_GLASS_",0)==0||m.name.rfind("EXT_GLASS_",0)==0;}
static void put(Bytes& b,std::uint32_t x){for(unsigned i=0;i<4;++i)b.push_back(static_cast<std::uint8_t>(x>>(i*8)));}
static void patch(Bytes& b,size_t p,std::uint32_t x){for(unsigned i=0;i<4;++i)b[p+i]=static_cast<std::uint8_t>(x>>(i*8));}
static Bytes read(const std::filesystem::path& p){
 std::ifstream f(p,std::ios::binary|std::ios::ate);auto n=f.tellg();
 if(!f||n<36||n>MaxSidecarBytes)throw std::runtime_error("input envelope");
 Bytes b(static_cast<size_t>(n));f.seekg(0);f.read(reinterpret_cast<char*>(b.data()),n);
 if(!f)throw std::runtime_error("input read");return b;
}
struct Atlas {
 std::vector<unsigned> sum,count;
 unsigned valid=0,skipped=0;std::uint64_t work=0;bool capped=false;
 explicit Atlas(unsigned size):sum(size*size),count(size*size){}
};
struct Grid {
 static constexpr int side=56;
 std::array<std::uint8_t,side*side*side> used{};
 bool inside(int x,int y,int z)const{return x>=0&&x<side&&y>=0&&y<side&&z>=0&&z<side;}
 bool get(V v)const{int x=int(std::floor(v.x)),y=int(std::floor(v.y)),z=int(std::floor(v.z));return inside(x,y,z)&&used[(z*side+y)*side+x];}
 void mark(V v){int x=int(std::floor(v.x)),y=int(std::floor(v.y)),z=int(std::floor(v.z));if(inside(x,y,z))used[(z*side+y)*side+x]=1;}
};
static unsigned shade(V p,V n,const Grid& g){
 auto t=unit(cross(n,std::abs(n.x)<.8?V{1,0,0}:V{0,1,0}));auto b=cross(n,t);
 constexpr double cs[6]{1,.5,-.5,-1,-.5,.5},ss[6]{0,.8660254038,.8660254038,0,-.8660254038,-.8660254038};
 unsigned hits=0;for(unsigned k=0;k<6;++k){
  const auto d=n*.8+t*(.6*cs[k])+b*(.6*ss[k]);
  for(double i=1.5;i<=5.5;i+=1)if(g.get(p+d*i)){++hits;break;}
 }
 return unsigned(std::lround(255*(1-.55*hits/6.)));
}
static Bytes dds(std::vector<std::uint8_t> ao,unsigned size){
 Bytes out{'D','D','S',' '};unsigned levels=1;for(unsigned n=size;n>1;n>>=1)++levels;
 const unsigned header[31]{124,0x2100f,size,size,size*4,0,levels,0,0,0,0,0,0,0,0,0,0,0,32,0x41,0,32,0x00ff0000,0x0000ff00,0x000000ff,0xff000000,0x401008,0,0,0,0};
 for(auto x:header)put(out,x);
 for(unsigned n=size;;n>>=1){
  for(auto a:ao){out.push_back(255);out.push_back(255);out.push_back(a);out.push_back(255);}
  if(n==1)break;
  std::vector<std::uint8_t> next(n*n/4);
  for(unsigned y=0;y<n/2;++y)for(unsigned x=0;x<n/2;++x){
   unsigned i=y*2*n+x*2;next[y*(n/2)+x]=static_cast<std::uint8_t>((unsigned(ao[i])+ao[i+1]+ao[i+n]+ao[i+n+1]+2)/4);
  }
  ao.swap(next);
 }
 return out;
}
static std::vector<std::uint8_t> make_image(const Atlas& a,unsigned size){
 std::vector<std::uint8_t> image(size*size,255),known(size*size);
 for(unsigned i=0;i<image.size();++i)if(a.count[i]){image[i]=static_cast<std::uint8_t>(a.sum[i]/a.count[i]);known[i]=1;}
 // Extend only from actually covered texels, never from neutral background.
 for(unsigned pass=0;pass<2;++pass){
  auto next=image,mask=known;
  for(unsigned y=0;y<size;++y)for(unsigned x=0;x<size;++x){
   unsigned i=y*size+x;if(known[i])continue;unsigned total=0,num=0;
   for(int dy=-1;dy<=1;++dy)for(int dx=-1;dx<=1;++dx){
    int nx=int(x)+dx,ny=int(y)+dy;if(nx<0||ny<0||nx>=int(size)||ny>=int(size))continue;
    unsigned j=unsigned(ny)*size+unsigned(nx);if(known[j]){total+=image[j];++num;}
   }
   if(num){next[i]=static_cast<std::uint8_t>(total/num);mask[i]=1;}
  }
  image.swap(next);known.swap(mask);
 }
 return image;
}
// Exact flat-color proof for the preserved albedo. All BC mip blocks
// must use equal color endpoints, and BC3 alpha must decode to one value.
static bool uniform_albedo(const Texture& texture){
 const auto& d=texture.dds;
 if(d.size()<132)return false;
 if(texture.format==TextureFormat::ARGB32){
  if((d.size()-128)%4)return false;
  for(size_t i=132;i<d.size();i+=4)
   if(std::memcmp(d.data()+i,d.data()+128,4)!=0)return false;
  return true;
 }
 const unsigned block=texture.format==TextureFormat::DXT1?8u:16u;
 if((d.size()-128)%block)return false;
 unsigned color=0,alpha=0;bool first=true;
 for(size_t off=128;off<d.size();off+=block){
  const auto* p=d.data()+off+(block==16u?8u:0u);
  const unsigned c0=U16(p),c1=U16(p+2),indices=U32(p+4);
  if(c0!=c1||(!first&&c0!=color))return false;
  color=c0;
  if(block==8u){
   for(unsigned i=0;i<16;++i)if(((indices>>(2*i))&3u)==3u)return false;
  }else{
   const unsigned a0=d[off],a1=d[off+1];
   if(a0!=a1||(!first&&a0!=alpha))return false;
   alpha=a0;std::uint64_t bits=0;
   for(unsigned i=0;i<6;++i)bits|=std::uint64_t(d[off+2+i])<<(8*i);
   for(unsigned i=0;i<16;++i){
    const auto index=(bits>>(3*i))&7u;
    if((index==6u&&a0!=0u)||(index==7u&&a0!=255u))return false;
   }
  }
  first=false;
 }
 return !first;
}
// Dedicated mode for the generated per-triangle diagnostic atlas. Each
// actual opaque face has its own tile. Fill the entire tile with its
// geometry-derived AO, including the gutter, rather than undersampling
// 60k+ tiny UV islands in the ordinary 64/128 atlas.
template<class GridPos>
static Bytes triangle_atlas(const Model& m,unsigned material,const Grid& grid,GridPos gridPos,bool paired=false,bool patches=false){
 const auto& texture=m.textures[material];
 if(!uniform_albedo(texture)||!m.pbrMaterials[material].normal.dds.empty())return {};
 struct Sample {const Vertex *a,*b,*c;V face;};
 std::vector<Sample> samples;
 for(const auto& mesh:m.meshes)if(mesh.material==material){
  if(glass(mesh))return {};
  for(size_t i=0;i<mesh.indices.size();i+=3){
   const auto &a=mesh.vertices[mesh.indices[i]],&b=mesh.vertices[mesh.indices[i+1]],&c=mesh.vertices[mesh.indices[i+2]];
   auto n=cross(pos(b)-pos(a),pos(c)-pos(a));
   double len2=dot(n,n);
   if(!(len2>0)){
    // Non-rasterizing source faces are preserved but have no AO texels.
    if(a.u||a.v||b.u||b.v||c.u||c.v)return {};
    continue;
   }
   samples.push_back({&a,&b,&c,n*(1/std::sqrt(len2))});
  }
 }
 if(samples.empty())return {};
 unsigned tiles=1;
 while(std::uint64_t(tiles)*tiles<samples.size())++tiles;
 // Bounded diagnostic texture footprint. Every tile has at least four
 // texels along each axis at mip zero; lower mips remain approximate.
 unsigned size=64;while(size<tiles*4u&&size<2048u)size*=2;
 if(size<tiles*4u)return {};
 std::vector<std::uint8_t> image(std::size_t(size)*size,255);
 struct Tile {std::array<unsigned,8> faces{};unsigned count=0;};
 std::vector<Tile> chart(std::size_t(tiles)*tiles);
 for(unsigned i=0;i<samples.size();++i){
  const auto& s=samples[i];
  const double cx=std::floor((double(s.a->u)+s.b->u+s.c->u)*tiles/3);
  const double cy=std::floor((double(s.a->v)+s.b->v+s.c->v)*tiles/3);
  if(cx<0||cy<0||cx>=tiles||cy>=tiles)return {};
  const auto x=static_cast<unsigned>(cx),y=static_cast<unsigned>(cy);
  const unsigned index=y*tiles+x;
  if(!paired&&!patches&&index!=i)return {};
  for(const auto* v:{s.a,s.b,s.c}){
   const double u=double(v->u)*tiles-x,w=double(v->v)*tiles-y;
   if(u<.124||u>.876||w<.124||w>.876)return {};
  }
  const double du=s.b->u-s.a->u,dv=s.b->v-s.a->v,
      eu=s.c->u-s.a->u,ev=s.c->v-s.a->v;
  if(du*ev-dv*eu==0)return {};
  auto& tile=chart[index];
  if(tile.count>=(patches?8u:paired?2u:1u))return {};
  tile.faces[tile.count++]=i;
 }
 auto valueFor=[&](const Sample& s){
  V n=unit(normal(*s.a)+normal(*s.b)+normal(*s.c));
  if(dot(n,n)<.5)n=s.face;
  return static_cast<std::uint8_t>(shade(gridPos((pos(*s.a)+pos(*s.b)+pos(*s.c))*(1./3)),n,grid));
 };
 auto edge=[&](unsigned cell){return static_cast<unsigned>(
    (std::max)(0.0,std::ceil(double(cell)*size/tiles-.5)));};
 auto same=[](const Vertex* a,const Vertex* b){
    return a->u==b->u&&a->v==b->v&&
           std::memcmp(a,b,6*sizeof(float))==0;
 };
 bool ended=false;
 for(unsigned index=0;index<chart.size();++index){
  const auto& tile=chart[index];
  if(!tile.count){ended=true;continue;}
  if(ended)return {}; // generated charts must occupy contiguous tiles
  const auto& a=samples[tile.faces[0]];
  const auto first=valueFor(a);
  auto second=first;
  const Vertex *e0=nullptr,*e1=nullptr,*third=nullptr;
  double side=0;
  auto sign=[&](double u,double v){
     return (double(e1->u)-e0->u)*(v-e0->v)-(double(e1->v)-e0->v)*(u-e0->u);
  };
  if(patches){
   // Independently prove each patch is connected by exact source corners
   // and contains no overlapping projected interiors. The converter's
   // report is not trusted. Fill gutters from the nearest triangle.
   struct Point {double u,v;};
   auto verts=[](const Sample& s){return std::array<const Vertex*,3>{s.a,s.b,s.c};};
   auto points=[&](const Sample& s){return std::array<Point,3>{{{s.a->u,s.a->v},{s.b->u,s.b->v},{s.c->u,s.c->v}}};};
   auto projection=[](Point p,Point n){return p.u*n.u+p.v*n.v;};
   auto overlap=[&](const auto& x,const auto& y){
    for(const auto* tri:{&x,&y})for(unsigned k=0;k<3;++k){
     const auto p=(*tri)[k],q=(*tri)[(k+1)%3];const Point n{p.v-q.v,q.u-p.u};
     double loX=projection(x[0],n),hiX=loX,loY=projection(y[0],n),hiY=loY;
     for(unsigned l=1;l<3;++l){const auto a=projection(x[l],n),b=projection(y[l],n);
      loX=std::min(loX,a);hiX=std::max(hiX,a);loY=std::min(loY,b);hiY=std::max(hiY,b);}
     if(std::min(hiX,hiY)-std::max(loX,loY)<=1e-9*std::max({hiX-loX,hiY-loY,1e-30}))return false;
    }
    return true;
   };
   unsigned connections[8]{};
   std::array<std::array<Point,3>,8> polygons{};
   std::array<std::uint8_t,8> values{};
   for(unsigned k=0;k<tile.count;++k){
    const auto& s=samples[tile.faces[k]];polygons[k]=points(s);values[k]=valueFor(s);
    for(unsigned l=0;l<k;++l){
     const auto& other=samples[tile.faces[l]];
     if(overlap(polygons[k],polygons[l])||dot(s.face,other.face)<.98)return {};
     unsigned shared=0;
     for(auto* v:verts(s))for(auto* w:verts(other))if(same(v,w))++shared;
     if(shared==2){connections[k]|=1u<<l;connections[l]|=1u<<k;}
     if(shared>2)return {};
    }
   }
   unsigned seen=1;
   for(unsigned k=0;k<tile.count;++k)for(unsigned l=0;l<tile.count;++l)
    if(seen&(1u<<l))seen|=connections[l];
   if(seen!=((1u<<tile.count)-1u))return {};
   auto distance=[](Point p,const std::array<Point,3>& tri){
    double best=1e30;bool positive=false,negative=false;
    for(unsigned k=0;k<3;++k){
     const auto a=tri[k],b=tri[(k+1)%3];
     const double u=b.u-a.u,v=b.v-a.v,x=p.u-a.u,y=p.v-a.v;
     const double side=u*y-v*x;positive|=side>0;negative|=side<0;
     const double d=u*u+v*v;
     const double t=d>0?std::clamp((x*u+y*v)/d,0.,1.):0.;
     best=std::min(best,(x-u*t)*(x-u*t)+(y-v*t)*(y-v*t));
    }
    return positive&&negative?best:0.;
   };
   const unsigned x=index%tiles,y=index/tiles;
   for(unsigned row=edge(y);row<edge(y+1);++row)
    for(unsigned col=edge(x);col<edge(x+1);++col){
     const Point p{(col+.5)/size,(row+.5)/size};unsigned best=0;double d=1e30;
     for(unsigned k=0;k<tile.count;++k){const auto next=distance(p,polygons[k]);if(next<d){d=next;best=k;}}
     image[std::size_t(row)*size+col]=values[best];
    }
   continue;
  }
  if(tile.count==2){
    const auto& b=samples[tile.faces[1]];
    const Vertex* other=nullptr;
    for(auto* av:{a.a,a.b,a.c}){
      bool shared=false;
      for(auto* bv:{b.a,b.b,b.c})if(same(av,bv)){shared=true;break;}
      if(shared){if(!e0)e0=av;else if(!e1)e1=av;else return {};}
      else third=av;
    }
    if(!e0||!e1||!third)return {};
    for(auto* bv:{b.a,b.b,b.c})if(!same(e0,bv)&&!same(e1,bv)){if(other)return {};other=bv;}
    if(!other)return {};
    side=sign(third->u,third->v);
    if(!(side*sign(other->u,other->v)<0))return {};
    second=valueFor(b);
  }
  const unsigned x=index%tiles,y=index/tiles;
  for(unsigned row=edge(y);row<edge(y+1);++row)
   for(unsigned col=edge(x);col<edge(x+1);++col)
    image[std::size_t(row)*size+col]=
       tile.count==1||sign((col+.5)/size,(row+.5)/size)*side>=0?first:second;
 }
 return dds(std::move(image),size);
}
static Bytes bake(const Bytes& input,unsigned size,
                  std::size_t gpuBudget=MaxGpuPayloadBytes,bool triangleAtlas=false,bool pairedAtlas=false,bool patchAtlas=false){
 gpuBudget=(std::min)(gpuBudget,MaxGpuPayloadBytes);
 Model m;std::string err;if(!Parse(input.data(),input.size(),m,err)||!m.pbrEnabled)throw std::runtime_error("source parser: "+err);
 const unsigned nm=static_cast<unsigned>(m.pbrMaterials.size());
 // Match the runtime parser's independent GPU payload budget, not just
 // the outer OVC envelope. Preserve existing source bytes if no room.
 std::size_t gpuBytes=0;
 for(const auto& mesh:m.meshes)
  gpuBytes+=mesh.vertices.size()*sizeof(Vertex)+mesh.indices.size()*(mesh.index32?4u:2u);
 for(const auto& tex:m.textures)gpuBytes+=tex.dds.size();
 for(const auto& mat:m.pbrMaterials)gpuBytes+=mat.normal.dds.size()+mat.orm.dds.size();
 if(gpuBytes>gpuBudget)throw std::runtime_error("source GPU budget");
 std::vector<bool> opaque(nm),transparent(nm);
 V lo{1e20,1e20,1e20},hi{-1e20,-1e20,-1e20};
 for(auto& mesh:m.meshes){
  if(glass(mesh)){transparent[mesh.material]=true;continue;}
  opaque[mesh.material]=true;
  IndexedMeshBounds bounds{};if(!ComputeIndexedMeshBounds(mesh,bounds))throw std::runtime_error("bounds");
  lo={std::min(lo.x,double(bounds.low[0])),std::min(lo.y,double(bounds.low[1])),std::min(lo.z,double(bounds.low[2]))};
  hi={std::max(hi.x,double(bounds.high[0])),std::max(hi.y,double(bounds.high[1])),std::max(hi.z,double(bounds.high[2]))};
 }
 double extent=std::max({hi.x-lo.x,hi.y-lo.y,hi.z-lo.z});if(!(extent>1e-6))throw std::runtime_error("opaque bounds");
 auto gridPos=[&](V p){return (p-lo)*(48/extent)+V{3,3,3};};
 Grid g;std::vector<Atlas> atlases;
 if(!triangleAtlas)for(unsigned i=0;i<nm;++i)atlases.emplace_back(size);
 // Geometry occupancy from the actual opaque indexed triangles, not AABB fill.
 for(auto& mesh:m.meshes)if(!glass(mesh))for(size_t i=0;i<mesh.indices.size();i+=3){
  V a=gridPos(pos(mesh.vertices[mesh.indices[i]])),b=gridPos(pos(mesh.vertices[mesh.indices[i+1]])),c=gridPos(pos(mesh.vertices[mesh.indices[i+2]]));
  V e=b-a,f=c-a;unsigned steps=std::min(48u,std::max(1u,unsigned(std::ceil(std::sqrt(std::max({dot(e,e),dot(f,f),dot(c-b,c-b)}))))));
  for(unsigned x=0;x<=steps;++x)for(unsigned y=0;y+x<=steps;++y)g.mark(a+e*(double(x)/steps)+f*(double(y)/steps));
 }
 if(!triangleAtlas)for(auto& mesh:m.meshes)if(!glass(mesh)&&!transparent[mesh.material]&&m.pbrMaterials[mesh.material].orm.dds.empty()){
  auto& atlas=atlases[mesh.material];
  for(size_t i=0;i<mesh.indices.size();i+=3){
   if(atlas.capped||atlas.skipped)break;
   const auto &a=mesh.vertices[mesh.indices[i]],&b=mesh.vertices[mesh.indices[i+1]],&c=mesh.vertices[mesh.indices[i+2]];
   const V geometric=cross(pos(b)-pos(a),pos(c)-pos(a));
   const double geomSq=dot(geometric,geometric);
   // A truly zero-area helper never rasterizes; preserve its source
   // bytes but do not veto AO for drawable faces of the same material.
   if(!(geomSq>0.))continue;
   const double du=double(b.u)-a.u,dv=double(b.v)-a.v,
       eu=double(c.u)-a.u,ev=double(c.v)-a.v,det=du*ev-dv*eu;
   // Relative UV conditioning, not an absolute area threshold. Tiny
   // well-conditioned charts are legitimate (sample centroid if subpixel).
   const double energy=(du*du+dv*dv)*(eu*eu+ev*ev);
   if(!(energy>1e-30)||!(det*det>energy*1e-8)){++atlas.skipped;continue;}
   V n=unit(normal(a)+normal(b)+normal(c));
   if(dot(n,n)<.5)n=geometric*(1./std::sqrt(geomSq));
   double xmin=std::min({double(a.u),double(b.u),double(c.u)}),xmax=std::max({double(a.u),double(b.u),double(c.u)});
   double ymin=std::min({double(a.v),double(b.v),double(c.v)}),ymax=std::max({double(a.v),double(b.v),double(c.v)});
   if(std::floor(xmax)-std::floor(xmin)>4||std::floor(ymax)-std::floor(ymin)>4){++atlas.skipped;continue;}
   int x0=int(std::floor(xmin*size)),x1=int(std::ceil(xmax*size)),y0=int(std::floor(ymin*size)),y1=int(std::ceil(ymax*size));
   atlas.work+=std::uint64_t(x1-x0+1)*(y1-y0+1);
   // Refuse extreme UV overdraw instead of shipping a partially baked map.
   if(atlas.work>20000000ull){atlas.capped=true;break;}
   auto putSample=[&](int x,int y,unsigned value){
    unsigned j=unsigned((y%int(size)+int(size))%int(size))*size+unsigned((x%int(size)+int(size))%int(size));
    if(atlas.count[j]<1000000u){atlas.sum[j]+=value;++atlas.count[j];}
   };
   const unsigned value=shade(gridPos((pos(a)+pos(b)+pos(c))*(1./3)),n,g);
   bool covered=false;
   for(int y=y0;y<=y1;++y)for(int x=x0;x<=x1;++x){
    double u=(x+.5)/size-a.u,v=(y+.5)/size-a.v,s=(u*ev-v*eu)/det,t=(du*v-dv*u)/det;
    if(s>=-1e-6&&t>=-1e-6&&s+t<=1.000001){putSample(x,y,value);covered=true;}
   }
   if(!covered)putSample(int(std::floor((double(a.u)+b.u+c.u)*size/3)),int(std::floor((double(a.v)+b.v+c.v)*size/3)),value);
   ++atlas.valid;
  }
 }
 // Exact raw byte splice. Native parser already checked every envelope.
 size_t p=36;for(unsigned k=0;k<m.meshes.size();++k){
  auto name=U16(input.data()+p),nv=U32(input.data()+p+4),ni=U32(input.data()+p+8),w=U32(input.data()+p+12);
  p+=16+name+size_t(nv)*32+size_t(ni)*w;
 }
 for(unsigned k=0;k<nm;++k)p+=4+U32(input.data()+p);
 p+=8;Bytes out(input.begin(),input.begin()+p);unsigned generated=0,existing=0,missing=0;
 for(unsigned i=0;i<nm;++i){
  size_t start=p;p+=12;p+=4+U32(input.data()+p);size_t end=p;
  unsigned old=U32(input.data()+p);p+=4+old;
  out.insert(out.end(),input.begin()+start,input.begin()+end);
  if(old){out.insert(out.end(),input.begin()+end,input.begin()+p);if(opaque[i])++existing;continue;}
  if(!opaque[i]||transparent[i]){put(out,0);if(opaque[i])++missing;continue;}
  Bytes map;
  if(triangleAtlas)map=triangle_atlas(m,i,g,gridPos,pairedAtlas,patchAtlas);
  else{
   auto& a=atlases[i];
   if(a.valid&&!a.skipped&&!a.capped)map=dds(make_image(a,size),size);
  }
  // Never claim AO coverage when a drawable face could not be mapped.
  if(map.empty()){put(out,0);++missing;continue;}
  if(map.size()>gpuBudget-gpuBytes||
     out.size()+map.size()+input.size()-p+4>MaxSidecarBytes){
   put(out,0);++missing;continue;
  }
  gpuBytes+=map.size();
  put(out,static_cast<unsigned>(map.size()));out.insert(out.end(),map.begin(),map.end());
  ++generated;
 }
 out.insert(out.end(),input.begin()+p,input.end());
 patch(out,28,static_cast<unsigned>(out.size()-36));patch(out,32,Crc32(out.data()+36,out.size()-36));
 Model checked;if(!Parse(out.data(),out.size(),checked,err))throw std::runtime_error("output parser: "+err);
 if(checked.meshes.size()!=m.meshes.size()||checked.dashboardBindings.size()!=m.dashboardBindings.size())throw std::runtime_error("identity");
 for(unsigned i=0;i<nm;++i)if(checked.textures[i].dds!=m.textures[i].dds||checked.pbrMaterials[i].normal.dds!=m.pbrMaterials[i].normal.dds||
    (!m.pbrMaterials[i].orm.dds.empty()&&checked.pbrMaterials[i].orm.dds!=m.pbrMaterials[i].orm.dds))throw std::runtime_error("preservation");
 std::cout<<"generated="<<generated<<" existingOpaque="<<existing<<" missingOpaque="<<missing<<" ";
 return out;
}
int main(int argc,char** argv){
 try{
  if(argc!=4)throw std::runtime_error("usage: bake_external_ao input.ovc output.ovc 64|128|triangle-atlas|paired-atlas|patch-atlas");
  const bool pairedAtlas=std::strcmp(argv[3],"paired-atlas")==0;
  const bool patchAtlas=std::strcmp(argv[3],"patch-atlas")==0;
  const bool triangleAtlas=patchAtlas||pairedAtlas||std::strcmp(argv[3],"triangle-atlas")==0;
  const auto size=triangleAtlas?64ul:std::stoul(argv[3]);
  if(size!=64&&size!=128)throw std::runtime_error("size");
  std::filesystem::path src=argv[1],dst=argv[2];if(std::filesystem::exists(dst))throw std::runtime_error("refuse existing output");
  auto b=read(src);auto output=bake(b,static_cast<unsigned>(size),MaxGpuPayloadBytes,triangleAtlas,pairedAtlas,patchAtlas);
  auto tmp=dst;tmp+=".part";if(std::filesystem::exists(tmp))throw std::runtime_error("refuse existing temporary");
  std::ofstream f(tmp,std::ios::binary);f.write(reinterpret_cast<const char*>(output.data()),output.size());f.close();if(!f)throw std::runtime_error("write");
  std::filesystem::rename(tmp,dst);std::cout<<dst.filename().string()<<" PASS\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
