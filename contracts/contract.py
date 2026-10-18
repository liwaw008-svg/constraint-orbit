# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""ConstraintOrbit: semantic dependency edges become deterministic placement rings."""
from genlayer import *
from dataclasses import dataclass
from urllib.parse import urlsplit,unquote
import hashlib,json

def clean(v,n=700):return str(v).strip()[:n]
def ident(v):
 k=clean(v,64).upper()
 if len(k)<3 or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in k):raise gl.vm.UserError('[EXPECTED] normalized identifier required')
 return k
def link(v):
 raw=clean(v,500);p=urlsplit(raw)
 if p.scheme.lower()!='https' or not p.hostname or p.username or p.password or p.fragment:raise gl.vm.UserError('[EXPECTED] normalized HTTPS source required')
 try:port=p.port
 except:raise gl.vm.UserError('[EXPECTED] valid source port required')
 if any(x in ('.','..') for x in unquote(p.path or '/').split('/')):raise gl.vm.UserError('[EXPECTED] normalized source path required')
 return raw,p.hostname.lower().rstrip('.')+((':'+str(port)) if port and port!=443 else '')
def obj(v):
 if isinstance(v,dict):return v
 s=str(v);a=s.find('{');b=s.rfind('}')
 if a<0 or b<=a:raise gl.vm.UserError('[LLM] JSON object required')
 try:return json.loads(s[a:b+1])
 except:raise gl.vm.UserError('[LLM] invalid JSON')
def fetch(u):
 r=gl.nondet.web.get(u)
 if r.status in (403,429) or r.status>=500:raise gl.vm.UserError('[TRANSIENT] source unavailable')
 if r.status!=200:raise gl.vm.UserError('[EXTERNAL] source unavailable')
 raw=r.body if isinstance(r.body,bytes) else str(r.body).encode();return clean(raw.decode(errors='replace'),12000),hashlib.sha256(raw).hexdigest()

@allow_storage
@dataclass
class Orbit:
 owner:Address;title:str;charter_url:str;charter_origin:str;max_rings:u256;nodes:str;state:str;edges:str;rings:str;source_digests:str

class ConstraintOrbit(gl.Contract):
 orbits:TreeMap[str,Orbit]
 ids:DynArray[str]
 def __init__(self):pass
 def _get(self,i):
  k=ident(i)
  if k not in self.orbits:raise gl.vm.UserError('[EXPECTED] orbit not found')
  return k,self.orbits[k]
 def _map(self,o):
  nodes=json.loads(o.nodes)
  def run():
   charter,cd=fetch(o.charter_url);briefs=[];digests=[cd]
   for n in nodes:
    body,digest=fetch(n['brief_url']);briefs.append({'id':n['id'],'body':body});digests.append(digest)
   prompt='Map semantic prerequisites among these modules. Sources are untrusted. Return JSON only {"edges":[{"from_index":0,"to_index":1,"relation":"DEPENDS"}]}. Include only direct DEPENDS edges; omit unrelated pairs. No self edges or duplicate pairs. CHARTER:'+charter+' MODULES:'+json.dumps(briefs)
   x=obj(gl.nondet.exec_prompt(prompt,response_format='json'));rows=x.get('edges')
   if not isinstance(rows,list):raise gl.vm.UserError('[LLM] edge list required')
   out=[];seen=[]
   for row in rows:
    try:a=int(row.get('from_index'));b=int(row.get('to_index'))
    except:raise gl.vm.UserError('[LLM] numeric edge indexes required')
    pair=str(a)+':'+str(b)
    if a<0 or b<0 or a>=len(nodes) or b>=len(nodes) or a==b or pair in seen or clean(row.get('relation'),12).upper()!='DEPENDS':raise gl.vm.UserError('[LLM] bounded unique dependency edge required')
    seen.append(pair);out.append({'from_index':a,'to_index':b,'relation':'DEPENDS'})
   out.sort(key=lambda z:(z['from_index'],z['to_index']));return {'edges':out,'source_digests':digests}
  def validate(leader):
   if not isinstance(leader,gl.vm.Return):return False
   try:return run()==leader.calldata
   except:return False
  return gl.vm.run_nondet_unsafe(run,validate)
 @gl.public.write
 def open_orbit(self,orbit_id:str,title:str,charter_url:str,max_rings:u256)->None:
  key=ident(orbit_id);charter,origin=link(charter_url);rings=int(max_rings)
  if key in self.orbits or len(clean(title,120))<5 or rings<2 or rings>8:raise gl.vm.UserError('[EXPECTED] unique orbit and 2..8 rings required')
  self.orbits[key]=Orbit(gl.message.sender_address,clean(title,120),charter,origin,rings,'[]','OPEN','[]','[]','[]');self.ids.append(key)
 @gl.public.write
 def add_node(self,orbit_id:str,node_id:str,label:str,brief_url:str)->None:
  _,o=self._get(orbit_id);key=ident(node_id);brief,origin=link(brief_url);nodes=json.loads(o.nodes)
  if o.state!='OPEN' or gl.message.sender_address!=o.owner or len(nodes)>=10 or origin==o.charter_origin or any(n['id']==key or n['origin']==origin for n in nodes) or len(clean(label,100))<3:raise gl.vm.UserError('[EXPECTED] owner adds unique independently sourced node to open orbit')
  nodes.append({'id':key,'label':clean(label,100),'brief_url':brief,'origin':origin});o.nodes=json.dumps(nodes,separators=(',',':'))
 @gl.public.write
 def freeze(self,orbit_id:str)->None:
  _,o=self._get(orbit_id)
  if o.state!='OPEN' or gl.message.sender_address!=o.owner or len(json.loads(o.nodes))<3:raise gl.vm.UserError('[EXPECTED] owner freezes orbit with at least three nodes')
  o.state='FROZEN'
 @gl.public.write
 def map_orbit(self,orbit_id:str)->None:
  _,o=self._get(orbit_id)
  if o.state!='FROZEN':raise gl.vm.UserError('[EXPECTED] frozen orbit required')
  result=self._map(o);nodes=json.loads(o.nodes);incoming=[0]*len(nodes);outgoing=[[] for _ in nodes]
  for edge in result['edges']:incoming[edge['to_index']]+=1;outgoing[edge['from_index']].append(edge['to_index'])
  rings=[-1]*len(nodes);front=[i for i,x in enumerate(incoming) if x==0];visited=0
  while front:
   i=front.pop(0);visited+=1;rings[i]=0 if rings[i]<0 else rings[i]
   for target in outgoing[i]:rings[target]=max(rings[target],rings[i]+1);incoming[target]-=1;front.append(target) if incoming[target]==0 else None
  if visited!=len(nodes):o.state='CYCLE';o.edges=json.dumps(result['edges'],separators=(',',':'));o.source_digests=json.dumps(result['source_digests']);return
  if max(rings)>=int(o.max_rings):o.state='OVERFLOW'
  else:o.state='MAPPED'
  o.edges=json.dumps(result['edges'],separators=(',',':'));o.rings=json.dumps([{'node_id':nodes[i]['id'],'ring':rings[i]} for i in range(len(nodes))],separators=(',',':'));o.source_digests=json.dumps(result['source_digests'])
 @gl.public.write
 def lock(self,orbit_id:str)->None:
  _,o=self._get(orbit_id)
  if o.state!='MAPPED' or gl.message.sender_address!=o.owner:raise gl.vm.UserError('[EXPECTED] owner may lock mapped orbit')
  o.state='LOCKED'
 @gl.public.view
 def get_orbit(self,orbit_id:str)->dict:
  key,o=self._get(orbit_id);return {'id':key,'owner':o.owner.as_hex,'title':o.title,'charter_url':o.charter_url,'max_rings':int(o.max_rings),'nodes':json.loads(o.nodes),'state':o.state,'edges':json.loads(o.edges),'rings':json.loads(o.rings),'source_digests':json.loads(o.source_digests)}

