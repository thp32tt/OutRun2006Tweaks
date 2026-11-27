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
static Bytes bake(const Bytes& input,unsigned size){
 Model m;std::string err;if(!Parse(input.data(),input.size(),m,err)||!m.pbrEnabled)throw std::runtime_error("source parser: "+err);
 const unsigned nm=static_cast<unsigned>(m.pbrMaterials.size());
 // Match the runtime parser's independent GPU payload budget, not just
 // the outer OVC envelope. Preserve existing source bytes if no room.
 std::size_t gpuBytes=0;
 for(const auto& mesh:m.meshes)
  gpuBytes+=mesh.vertices.size()*sizeof(Vertex)+mesh.indices.size()*(mesh.index32?4u:2u);
 for(const auto& tex:m.textures)gpuBytes+=tex.dds.size();
 for(const auto& mat:m.pbrMaterials)gpuBytes+=mat.normal.dds.size()+mat.orm.dds.size();
 if(gpuBytes>MaxGpuPayloadBytes)throw std::runtime_error("source GPU budget");
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
 Grid g;std::vector<Atlas> atlases;for(unsigned i=0;i<nm;++i)atlases.emplace_back(size);
 // Geometry occupancy from the actual opaque indexed triangles, not AABB fill.
 for(auto& mesh:m.meshes)if(!glass(mesh))for(size_t i=0;i<mesh.indices.size();i+=3){
  V a=gridPos(pos(mesh.vertices[mesh.indices[i]])),b=gridPos(pos(mesh.vertices[mesh.indices[i+1]])),c=gridPos(pos(mesh.vertices[mesh.indices[i+2]]));
  V e=b-a,f=c-a;unsigned steps=std::min(48u,std::max(1u,unsigned(std::ceil(std::sqrt(std::max({dot(e,e),dot(f,f),dot(c-b,c-b)}))))));
  for(unsigned x=0;x<=steps;++x)for(unsigned y=0;y+x<=steps;++y)g.mark(a+e*(double(x)/steps)+f*(double(y)/steps));
 }
 for(auto& mesh:m.meshes)if(!glass(mesh)&&!transparent[mesh.material]&&m.pbrMaterials[mesh.material].orm.dds.empty()){
  auto& atlas=atlases[mesh.material];
  for(size_t i=0;i<mesh.indices.size();i+=3){
   if(atlas.capped||atlas.skipped)break;
   const auto &a=mesh.vertices[mesh.indices[i]],&b=mesh.vertices[mesh.indices[i+1]],&c=mesh.vertices[mesh.indices[i+2]];
   double du=b.u-a.u,dv=b.v-a.v,eu=c.u-a.u,ev=c.v-a.v,det=du*ev-dv*eu;
   V n=unit(normal(a)+normal(b)+normal(c)),face=unit(cross(pos(b)-pos(a),pos(c)-pos(a)));
   if(std::abs(det)<=1e-7||dot(face,face)<.5){++atlas.skipped;continue;}
   if(dot(n,n)<.5)n=face;
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
  auto& a=atlases[i];
  if(old){out.insert(out.end(),input.begin()+end,input.begin()+p);if(opaque[i])++existing;continue;}
  if(!opaque[i]||transparent[i]||!a.valid||a.skipped||a.capped){put(out,0);if(opaque[i])++missing;continue;}
  // Never claim a material has AO coverage when any of its triangles could
  // not be mapped: the untouched source remains eligible for UV repair.
  auto image=make_image(a,size);auto map=dds(image,size);
  if(map.size()>MaxGpuPayloadBytes-gpuBytes||
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
  if(argc!=4)throw std::runtime_error("usage: bake_external_ao input.ovc output.ovc 64|128");
  auto size=std::stoul(argv[3]);if(size!=64&&size!=128)throw std::runtime_error("size");
  std::filesystem::path src=argv[1],dst=argv[2];if(std::filesystem::exists(dst))throw std::runtime_error("refuse existing output");
  auto b=read(src);auto output=bake(b,static_cast<unsigned>(size));
  auto tmp=dst;tmp+=".part";if(std::filesystem::exists(tmp))throw std::runtime_error("refuse existing temporary");
  std::ofstream f(tmp,std::ios::binary);f.write(reinterpret_cast<const char*>(output.data()),output.size());f.close();if(!f)throw std::runtime_error("write");
  std::filesystem::rename(tmp,dst);std::cout<<dst.filename().string()<<" PASS\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
