"""
Build the static GitHub Pages version of Company Brain into docs/.

Single source of truth: docs/index.html is GENERATED from web/index.html by
swapping the network data layer (fetch → baked data.json) for a client-side
one (search + paste-extract run in the browser). Edit web/index.html only.

    python build_static.py
"""

from __future__ import annotations

import json
import os

from company_brain import api  # sets up BRAIN + fake backdrop at import

HERE = os.path.dirname(__file__)

# ---- 1. bake the data ------------------------------------------------------
api._load_seed()
data = {
    "graph": api._full_graph(),
    "attention": api.BRAIN.attention(),
    "decisions": {d.id: d.to_dict() for d in api.BRAIN.decisions},
}
os.makedirs(os.path.join(HERE, "docs"), exist_ok=True)
with open(os.path.join(HERE, "docs", "data.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(data, f)

# ---- 2. generate docs/index.html from web/index.html -----------------------
DYNAMIC = (
    "const jget = async u => (await fetch(u)).json();\n"
    "const jpost = async (u,b) => (await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)})).json();"
)

STATIC_LAYER = r"""/* ---------- static data layer (no backend): baked data + client search/extract ---------- */
let state={graph:{nodes:[],edges:[]},attention:[],decisions:{}};
async function jget(u){
  if(u==='/api/graph') return state.graph;
  if(u==='/api/attention') return state.attention;
  if(u.indexOf('/api/decision')===0){ const id=new URLSearchParams(u.split('?')[1]).get('id');
    return state.decisions[id]||{error:'not found'}; }
  if(u==='/api/tokens') return {total:0};
  return {};
}
async function jpost(u,b){
  if(u==='/api/query'||u==='/api/voice/ask') return clientQuery(b.q);
  if(u==='/api/extract') return clientExtract(b.text);
  return {};
}
const _kw=s=>new Set((String(s).toLowerCase().match(/[a-z0-9][a-z0-9+/.-]{2,}/g)||[])
  .filter(w=>!['the','our','and','for','with','that','this'].includes(w)));
function clientQuery(q){
  const qk=_kw(q), boost={live:.12,needs_review:0,superseded:-.12};
  let best=null,bs=-1;
  for(const id in state.decisions){ const d=state.decisions[id];
    const hay=d.statement+' '+(d.evidence||[]).map(e=>e.verbatim_quote).join(' ');
    const hk=_kw(hay); let ov=0; qk.forEach(w=>{if(hk.has(w))ov++;});
    const score=ov/(qk.size||1)+(boost[d.status]||0);
    if(score>bs){bs=score;best=d;} }
  if(!best||bs<=0) return {answer:"I don't have a decision on record for that.",decision:null,citation:null};
  const owner=best.owner||'nobody yet';
  const st={live:'current',needs_review:'flagged (a newer decision may have changed it)',superseded:'superseded'}[best.status]||best.status;
  return {answer:`The ${st} decision is: ${best.statement} Owner: ${owner}. Decided ${best.decided_on}.`,
    decision:best, citation:(best.evidence&&best.evidence[0])?best.evidence[0].verbatim_quote:null};
}
const _CUES=['decided','decision:',"we'll",'going with','standardize on','we should',"let's go with",'changing the free tier'];
const _TOPICS=[['infrastructure',['aws','gcp','infra','migrat','region']],['pricing-pro',['pro at','$','price pro']],
  ['pricing-free-tier',['free tier','calls/day','api calls']],['hiring',['hire','hiring','engineer']],
  ['tech-stack',['python','standardize','framework']]];
function _clean(l){ let s=l.replace(/^\s*[A-Za-z][\w'-]*:\s*/,'').replace(/decision:\s*/i,'')
  .replace(/^\s*-\s*/,'').replace(/we (decided|are going|'re going) (to|that|with)?\s*/i,'')
  .replace(/we'll\s*/i,'').replace(/going with/i,'use').replace(/we're\s*/i,'');
  const parts=s.split(/\.\s+/).map(p=>p.trim()).filter(Boolean);
  if(parts.length>1) s=parts.reduce((a,b)=>((/\d/.test(b)?25:0)+b.length)>((/\d/.test(a)?25:0)+a.length)?b:a);
  s=s.replace(/^(yes|ok|so|well|right)\b[\s,—-]*/i,'').trim().replace(/^\.|\.$/,'').trim();
  return s? s[0].toUpperCase()+s.slice(1):s; }
function _owner(lines){ const j=lines.join(' ').toLowerCase();
  for(const l of lines){ if(/i'll own|i own|i will own/i.test(l)){ const m=l.match(/^\s*([A-Za-z][\w'-]*)\s*:/); if(m) return m[1].toLowerCase(); } }
  if(/nobody|no one|tbd|unassigned|no owner/.test(j)) return null; return null; }
function _topic(t){ t=t.toLowerCase(); let best='general',bh=0;
  for(const [k,ws] of _TOPICS){ const h=ws.filter(w=>t.includes(w)).length; if(h>bh){bh=h;best=k;} } return best; }
const _HUB={infrastructure:'Backend',api:'Backend','public-api':'Backend',auth:'Backend',devops:'Backend',tech:'Backend','tech-stack':'Backend',
  frontend:'Frontend',mobile:'Frontend',design:'Frontend',data:'Data & ML','data-platform':'Data & ML',ml:'Data & ML','ml-models':'Data & ML',analytics:'Data & ML',
  security:'Security',compliance:'Security',pricing:'Finance',billing:'Finance',legal:'Finance',
  marketing:'Social / GTM',sales:'Social / GTM',support:'Social / GTM',partnerships:'Social / GTM',hiring:'People/Product',roadmap:'People/Product'};
function _hubOf(t){ if(!t)return 'General'; const p=t.split('-'); for(const c of [t,p[0],...p]){ if(_HUB[c])return _HUB[c]; } return 'General'; }
function clientExtract(text){
  const lines=text.split('\n').map(s=>s.trim()).filter(Boolean);
  const dl=lines.filter(l=>_CUES.some(c=>l.toLowerCase().includes(c)));
  if(!dl.length) return {extracted:[],attention:state.attention};
  const best=dl.reduce((a,b)=>(_clean(b).length>_clean(a).length?b:a));
  const stmt=_clean(best), owner=_owner(lines), topic=_topic(text), hub=_hubOf(topic);
  const id='UI-'+Object.keys(state.decisions).length+'-'+(text.length%997);
  const link='paste://ui', today=new Date().toISOString().slice(0,10);
  const dec={id,statement:stmt,status:'live',owner,decided_on:today,
    source:{type:'paste',link},evidence:dl.map(l=>({verbatim_quote:l,link})),assumptions:[],edges:[],topic,hub};
  let peer=Object.values(state.decisions).find(d=>d.topic===topic&&d.status==='live');
  if(peer){ dec.edges.push({type:'supersedes',target_id:peer.id}); peer.status='needs_review';
    const pn=state.graph.nodes.find(n=>n.id===peer.id); if(pn)pn.status='needs_review'; }
  else { const near=state.graph.nodes.find(n=>n.topic&&topic.split('-').some(w=>(n.topic||'').split('-').includes(w)));
    if(near) dec.edges.push({type:'depends_on',target_id:near.id}); }
  state.decisions[id]=dec;
  state.graph.nodes.push({id,statement:stmt,status:'live',owner,topic,hub,subcluster:topic,real:true});
  dec.edges.forEach(e=>state.graph.edges.push({source:id,type:e.type,target:e.target_id}));
  const items=[...state.attention];
  if(peer) items.unshift({type:'superseded',decision_id:peer.id,
    message:`“${peer.statement.slice(0,52)}” was changed by a newer decision (“${stmt.slice(0,40)}”) — check it still holds.`,related_id:id});
  if(!owner) items.unshift({type:'unowned',decision_id:id,message:`“${stmt}” has no owner — assign one.`,related_id:null});
  state.attention=items;
  return {extracted:[dec],attention:items};
}"""

STATIC_BOOT = ("async function boot(){\n"
               "  try{ state=await (await fetch('data.json')).json(); }\n"
               "  catch(e){ console.error('failed to load data.json',e); }\n"
               "  refresh(); loop();\n"
               "}\nboot();")

with open(os.path.join(HERE, "web", "index.html"), encoding="utf-8") as f:
    html = f.read()

assert DYNAMIC in html, "dynamic jget/jpost block not found in web/index.html"
assert "refresh(); loop();" in html, "entrypoint not found in web/index.html"
html = html.replace(DYNAMIC, STATIC_LAYER).replace("refresh(); loop();", STATIC_BOOT)

with open(os.path.join(HERE, "docs", "index.html"), "w", encoding="utf-8", newline="\n") as f:
    f.write(html)

# ---- report ----------------------------------------------------------------
g = data["graph"]
from collections import Counter
print("wrote docs/data.json + docs/index.html")
print(f"  graph: {len(g['nodes'])} nodes / {len(g['edges'])} edges "
      f"({sum(1 for n in g['nodes'] if n.get('real'))} real)")
print(f"  hubs: {dict(Counter(n['hub'] for n in g['nodes']))}")
print(f"  attention: {len(data['attention'])} items")
