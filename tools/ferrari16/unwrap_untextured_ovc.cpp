// Offline lossless UV-only reconstruction for constant-color OVC3/4.
// C++ counterpart to planar_patches in unwrap_untextured_ovc.py.
// No authored map is changed. Independent native parser and AO baker
// revalidate the output. Geometry, normals, materials and triangle order
// are preserved per indexed corner. No LOD or topology deletion.
#include "ovc_flat_albedo.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <unordered_map>
using namespace OutRunVR::DinoSidecar;
using Bytes=std::vector<std::uint8_t>;
struct V {double x,y,z;};
static V operator-(V a,V b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
static V operator*(V a,double s){return {a.x*s,a.y*s,a.z*s};}
static double dot(V a,V b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static V cross(V a,V b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
static V pos(const Vertex& v){return {v.x,v.y,v.z};}
static V unit(V a){const auto s=dot(a,a);return s>0.?a*(1./std::sqrt(s)):V{};}
struct P {double x,y;};
using Poly=std::array<P,3>;
static double side(P a,P b,P p){return (b.x-a.x)*(p.y-a.y)-(b.y-a.y)*(p.x-a.x);}
static bool overlap(const Poly& a,const Poly& b){
 // Convex SAT for CCW projected triangles. Boundary contact is allowed.
 for(const auto* p:{&a,&b}){
  const auto& q=p==&a?b:a;
  for(unsigned i=0;i<3;++i){
   const auto x=(*p)[i],y=(*p)[(i+1)%3],z=(*p)[(i+2)%3];
   const auto tol=1.e-12*std::max(side(x,y,z),1.e-30);
   if(side(x,y,q[0])<=tol&&side(x,y,q[1])<=tol&&side(x,y,q[2])<=tol)return false;
  }
 }
 return true;
}
static bool glass(const Mesh& m){return m.name.rfind("EXT_GLASS_",0)==0||m.name.rfind("F50_GLASS_",0)==0;}
static std::uint64_t edgeKey(unsigned a,unsigned b){
 return (std::uint64_t(std::min(a,b))<<32)|std::max(a,b);
}
struct Edge {unsigned count=0;unsigned face[2]{},a[2]{},b[2]{};};
struct Face {std::array<unsigned,3> id{};V normal{};bool drawable=false,done=false;};
struct Chart {std::array<unsigned,8> face{};std::array<Poly,8> poly{};unsigned count=0;};
static Poly project(const Mesh& m,const Face& f,V origin,V axis,V vertical){
 Poly p{};
 for(unsigned i=0;i<3;++i){
  const auto d=pos(m.vertices[f.id[i]])-origin;p[i]={dot(d,axis),dot(d,vertical)};
 }
 return p;
}
static bool basis(const Mesh& m,const Face& f,V& origin,V& axis,V& vertical){
 unsigned longest=0;double len=0;
 for(unsigned i=0;i<3;++i){
  const auto d=pos(m.vertices[f.id[(i+1)%3]])-pos(m.vertices[f.id[i]]);
  if(dot(d,d)>len){longest=i;len=dot(d,d);}
 }
 if(!(len>0.))return false;
 origin=pos(m.vertices[f.id[longest]]);
 axis=unit(pos(m.vertices[f.id[(longest+1)%3]])-origin);
 vertical=cross(f.normal,axis);
 return dot(vertical,vertical)>.5;
}
struct Stats {unsigned vertices=0,charts=0,maxFaces=0,materials=0,drawables=0;};
static Mesh rebuild(const Mesh& original,unsigned tiles,unsigned& ordinal,Stats& stats){
 Mesh out=original;
 const unsigned count=static_cast<unsigned>(original.indices.size()/3);
 std::vector<Face> faces(count);
 std::unordered_map<std::uint64_t,Edge> edges;edges.reserve(count*2u);
 for(unsigned i=0;i<count;++i){
  auto& f=faces[i];
  for(unsigned k=0;k<3;++k)f.id[k]=original.indices[i*3+k];
  const auto a=pos(original.vertices[f.id[0]]),b=pos(original.vertices[f.id[1]]),c=pos(original.vertices[f.id[2]]);
  const auto n=cross(b-a,c-a);f.drawable=dot(n,n)>0.;
  if(!f.drawable)continue;
  f.normal=unit(n);
  for(unsigned k=0;k<3;++k){
   const auto x=f.id[k],y=f.id[(k+1)%3];auto& e=edges[edgeKey(x,y)];
   if(e.count<2){e.face[e.count]=i;e.a[e.count]=x;e.b[e.count]=y;}
   ++e.count;
  }
 }
 std::vector<bool> assigned(original.vertices.size(),false);
 std::vector<unsigned> zero(original.vertices.size(),std::numeric_limits<unsigned>::max());
 auto vertex=[&](unsigned index,float u,float v){
  auto d=original.vertices[index];d.u=u;d.v=v;
  unsigned dst=index;
  if(assigned[index]){dst=static_cast<unsigned>(out.vertices.size());out.vertices.push_back(d);}
  else {assigned[index]=true;out.vertices[index]=d;}
  return dst;
 };
 // Degenerate source helper triangles keep their original corners and
 // zero UVs. The independent baker excludes them from atlas ownership.
 for(unsigned i=0;i<count;++i)if(!faces[i].drawable){
  for(unsigned k=0;k<3;++k){
   const auto id=faces[i].id[k];auto& dst=zero[id];
   if(dst==std::numeric_limits<unsigned>::max())dst=vertex(id,0.f,0.f);
   out.indices[i*3+k]=dst;
  }
 }
 auto writeChart=[&](const Chart& chart)->bool{
  double lx=1e30,ly=1e30,hx=-1e30,hy=-1e30;
  for(unsigned i=0;i<chart.count;++i)for(auto p:chart.poly[i]){
   lx=std::min(lx,p.x);ly=std::min(ly,p.y);hx=std::max(hx,p.x);hy=std::max(hy,p.y);
  }
  const auto scale=std::max(hx-lx,hy-ly);
  if(!(scale>0.)||ordinal>=std::uint64_t(tiles)*tiles)return false;
  const unsigned col=ordinal%tiles,row=ordinal/tiles;
  std::array<Poly,8> packed{};
  for(unsigned i=0;i<chart.count;++i){
   for(unsigned k=0;k<3;++k){
    const auto p=chart.poly[i][k];
    packed[i][k]={float((col+.125+.75*(p.x-lx)/scale)/tiles),
                  float((row+.125+.75*(p.y-ly)/scale)/tiles)};
   }
   if(!(side(packed[i][0],packed[i][1],packed[i][2])>0.))return false;
   for(unsigned j=0;j<i;++j)if(overlap(packed[i],packed[j]))return false;
  }
  // Chart-local source-index sharing; different chart UVs stay separate.
  std::array<unsigned,24> old{},dest{};unsigned used=0;
  for(unsigned i=0;i<chart.count;++i){
   const auto fi=chart.face[i];const auto& f=faces[fi];
   for(unsigned k=0;k<3;++k){
    unsigned j=0;for(;j<used&&old[j]!=f.id[k];++j){}
    if(j==used){
     old[used]=f.id[k];dest[used]=vertex(f.id[k],float(packed[i][k].x),float(packed[i][k].y));++used;
    }
    out.indices[fi*3+k]=dest[j];
   }
  }
  ++ordinal;++stats.charts;stats.maxFaces=std::max(stats.maxFaces,chart.count);
  return true;
 };
 for(unsigned i=0;i<count;++i){
  auto& f=faces[i];if(!f.drawable||f.done)continue;
  V origin{},axis{},vertical{};
  if(!basis(original,f,origin,axis,vertical))throw std::runtime_error("face basis");
  Chart chart{};chart.face[0]=i;chart.poly[0]=project(original,f,origin,axis,vertical);chart.count=1;f.done=true;
  for(unsigned cursor=0;cursor<chart.count&&chart.count<8;++cursor){
   const auto id=chart.face[cursor];const auto& from=faces[id];
   for(unsigned k=0;k<3&&chart.count<8;++k){
    const auto a=from.id[k],b=from.id[(k+1)%3];const auto it=edges.find(edgeKey(a,b));
    if(it==edges.end()||it->second.count!=2)continue;
    const auto& e=it->second;const unsigned j=e.face[0]==id?1u:0u;
    auto& other=faces[e.face[j]];
    if(other.done||!other.drawable||e.a[j]!=b||e.b[j]!=a||dot(f.normal,other.normal)<.995)continue;
    const auto poly=project(original,other,origin,axis,vertical);
    if(!(side(poly[0],poly[1],poly[2])>0.))continue;
    bool hit=false;for(unsigned l=0;l<chart.count;++l)if(overlap(poly,chart.poly[l])){hit=true;break;}
    if(hit)continue;
    chart.face[chart.count]=e.face[j];chart.poly[chart.count++]=poly;other.done=true;
   }
  }
  if(!writeChart(chart)){
   // Float quantization can collapse very thin patches. Never publish
   // an overlapping chart: retry its original faces in separate tiles.
   for(unsigned k=0;k<chart.count;++k){
    const auto j=chart.face[k];const auto& single=faces[j];V o{},u{},v{};
    if(!basis(original,single,o,u,v))throw std::runtime_error("single basis");
    Chart one{};one.count=1;one.face[0]=j;one.poly[0]=project(original,single,o,u,v);
    if(!writeChart(one))throw std::runtime_error("float UV collapse");
   }
  }
 }
 out.index32=out.vertices.size()>65535u;
 if(out.vertices.size()>MaxVertices)throw std::runtime_error("mesh vertex budget");
 // Prove every indexed corner's position/normal bytes before serialization.
 for(unsigned i=0;i<original.indices.size();++i)
  if(std::memcmp(&original.vertices[original.indices[i]],&out.vertices[out.indices[i]],6*sizeof(float))!=0)
   throw std::runtime_error("indexed geometry changed");
 return out;
}
static void put(Bytes& b,std::uint32_t x,unsigned width=4){
 for(unsigned i=0;i<width;++i)b.push_back(static_cast<std::uint8_t>(x>>(i*8)));
}
static void patch(Bytes& b,size_t p,std::uint32_t x){for(unsigned i=0;i<4;++i)b[p+i]=static_cast<std::uint8_t>(x>>(i*8));}
static Bytes read(const std::filesystem::path& p){
 std::ifstream f(p,std::ios::binary|std::ios::ate);const auto n=f.tellg();
 if(!f||n<36||n>MaxSidecarBytes)throw std::runtime_error("source envelope");
 Bytes b(static_cast<size_t>(n));f.seekg(0);f.read(reinterpret_cast<char*>(b.data()),n);
 if(!f)throw std::runtime_error("source read");
 return b;
}
static Bytes unwrap(const Bytes& raw,Stats& stats){
 Model m;std::string error;
 if(!Parse(raw.data(),raw.size(),m,error)||!m.pbrEnabled)throw std::runtime_error("native source parser: "+error);
 const unsigned nm=static_cast<unsigned>(m.textures.size());
 std::vector<std::vector<unsigned>> groups(nm);
 std::vector<bool> sharedGlass(nm,false),changed(m.meshes.size(),false);
 size_t tail=36;
 for(unsigned i=0;i<m.meshes.size();++i){
  const auto& mesh=m.meshes[i];
  if(glass(mesh))sharedGlass[mesh.material]=true;else groups[mesh.material].push_back(i);
  tail+=16+mesh.name.size()+mesh.vertices.size()*32+mesh.indices.size()*(mesh.index32?4u:2u);
 }
 for(unsigned mat=0;mat<nm;++mat){
  const auto& ids=groups[mat];const auto& p=m.pbrMaterials[mat];
  if(ids.empty()||sharedGlass[mat]||!p.normal.dds.empty()||!p.orm.dds.empty()||!uniform_albedo(m.textures[mat]))continue;
  const auto& first=m.meshes[ids[0]].vertices[0];
  bool constant=true;unsigned faces=0;
  for(auto id:ids){
   const auto& mesh=m.meshes[id];
   for(const auto& v:mesh.vertices)if(v.u!=first.u||v.v!=first.v){constant=false;break;}
   if(!constant)break;
   for(unsigned i=0;i<mesh.indices.size();i+=3){
    const auto a=pos(mesh.vertices[mesh.indices[i]]),b=pos(mesh.vertices[mesh.indices[i+1]]),c=pos(mesh.vertices[mesh.indices[i+2]]);
    const auto n=cross(b-a,c-a);if(dot(n,n)>0.)++faces;
   }
  }
  if(!constant||!faces)continue;
  unsigned tiles=1;while(std::uint64_t(tiles)*tiles<faces)++tiles;
  if(tiles>512u)throw std::runtime_error("atlas size budget");
  unsigned ordinal=0;
  for(auto id:ids){auto mesh=rebuild(m.meshes[id],tiles,ordinal,stats);m.meshes[id]=std::move(mesh);changed[id]=true;}
  ++stats.materials;stats.drawables+=faces;
  std::cout<<"UV_MATERIAL "<<mat<<" "<<faces<<" "<<ordinal<<"\n";
 }
 if(!stats.materials)throw std::runtime_error("no eligible constant-color material");
 Bytes out(raw.begin(),raw.begin()+36);
 size_t original=36;
 for(unsigned i=0;i<m.meshes.size();++i){
  const unsigned name=U16(raw.data()+original),nv=U32(raw.data()+original+4),ni=U32(raw.data()+original+8),w=U32(raw.data()+original+12);
  const size_t next=original+16+name+size_t(nv)*32+size_t(ni)*w;
  const auto& mesh=m.meshes[i];stats.vertices+=static_cast<unsigned>(mesh.vertices.size());
  if(!changed[i])out.insert(out.end(),raw.begin()+original,raw.begin()+next);
  else {
   put(out,name,2);put(out,mesh.material,2);put(out,static_cast<unsigned>(mesh.vertices.size()));
   put(out,ni);put(out,mesh.index32?4u:2u);
   out.insert(out.end(),mesh.name.begin(),mesh.name.end());
   const auto* vb=reinterpret_cast<const std::uint8_t*>(mesh.vertices.data());
   out.insert(out.end(),vb,vb+mesh.vertices.size()*sizeof(Vertex));
   for(auto index:mesh.indices)put(out,index,mesh.index32?4u:2u);
  }
  original=next;
 }
 if(original!=tail||stats.vertices>MaxVertices||out.size()+raw.size()-tail>MaxSidecarBytes)throw std::runtime_error("output bounds");
 out.insert(out.end(),raw.begin()+tail,raw.end());
 patch(out,20,stats.vertices);patch(out,28,static_cast<unsigned>(out.size()-36));patch(out,32,Crc32(out.data()+36,out.size()-36));
 Model checked;if(!Parse(out.data(),out.size(),checked,error)||checked.triangles!=m.triangles||checked.meshes.size()!=m.meshes.size())
  throw std::runtime_error("native output parser: "+error);
 return out;
}
int main(int argc,char** argv){
 try{
  if(argc!=3)throw std::runtime_error("usage: unwrap_untextured_ovc input.ovc output.ovc");
  const std::filesystem::path src=argv[1],dst=argv[2];auto part=dst;part+=".part";
  if(std::filesystem::exists(dst)||std::filesystem::exists(part))throw std::runtime_error("refuse overwrite");
  const auto raw=read(src);Stats stats{};const auto out=unwrap(raw,stats);
  std::ofstream f(part,std::ios::binary);f.write(reinterpret_cast<const char*>(out.data()),out.size());f.close();
  if(!f)throw std::runtime_error("output write");
  std::filesystem::rename(part,dst);
  std::cout<<"NATIVE_UV_PATCH_PASS vertices="<<stats.vertices<<" charts="<<stats.charts<<" maxFaces="<<stats.maxFaces<<" materials="<<stats.materials<<" drawable="<<stats.drawables<<"\n";
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
