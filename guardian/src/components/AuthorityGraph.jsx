import { useId, useMemo, useState } from 'react';
import { Bot, CircleHelp, Database, GitBranch, LockKeyhole, Network, Settings2, UserRound, X } from 'lucide-react';
import './authority-graph.css';

const metadata = {
  operator: { label: 'Operator', description: 'Human', Icon: UserRound },
  planner: { label: 'Planner agent', description: 'Plans and creates tasks', Icon: Bot },
  delegate: { label: 'Delegate agent', description: 'Executes delegated tasks', Icon: Bot },
  gateway: { label: 'Tool gateway', description: 'Controls tool access', Icon: Settings2 },
  protected: { label: 'Protected action', description: 'Synthetic operation', Icon: LockKeyhole },
  queue: { label: 'Queue', description: 'Holds pending actions', Icon: Database },
  service: { label: 'Service account', description: 'Independent authority', Icon: GitBranch },
};

function roleFor(node) {
  const value = `${node.id} ${node.label} ${node.kind}`.toLowerCase();
  if (/operator|human/.test(value)) return 'operator';
  if (/planner/.test(value)) return 'planner';
  if (/queue/.test(value)) return 'queue';
  if (/delegate|executor|worker/.test(value)) return 'delegate';
  if (/gateway|tool/.test(value)) return 'gateway';
  if (/service|alternate|independent/.test(value)) return 'service';
  if (/protect|resource|action|funds/.test(value)) return 'protected';
  return null;
}

const edgeCopy = { Authorize: 'authorized', Delegate: 'delegated', Invoke: 'invokes', Enqueue: 'queued', 'Commit check': 'commit check', 'Synthetic only': 'executes', 'Independent grant': 'independent', 'Alternate path': 'alternate path' };

const standardPositions = {
  operator: { x: 12, y: 88, w: 104, h: 112 },
  planner: { x: 180, y: 88, w: 104, h: 112 },
  delegate: { x: 348, y: 88, w: 104, h: 112 },
  gateway: { x: 516, y: 88, w: 104, h: 112 },
  protected: { x: 684, y: 88, w: 104, h: 112 },
  queue: { x: 338, y: 263, w: 132, h: 102 },
  service: { x: 85, y: 263, w: 132, h: 102 },
};

function lineFor(source, target) {
  const a = source.position;
  const b = target.position;
  const ar = source.role;
  const br = target.role;
  const midA = a.y + a.h / 2;
  const midB = b.y + b.h / 2;
  if (ar === 'planner' && br === 'queue') {
    const sx = a.x + a.w / 2;
    return { d: `M ${sx} ${a.y+a.h} V ${midB-10} Q ${sx} ${midB} ${sx+10} ${midB} H ${b.x-6}`, x: sx + 12, y: midB - 45 };
  }
  if (ar === 'queue' && br === 'gateway') {
    const tx = b.x+b.w/2;
    return { d: `M ${a.x+a.w} ${midA} H ${tx-10} Q ${tx} ${midA} ${tx} ${midA-10} V ${b.y+b.h+6}`, x: tx + 9, y: midA - 45 };
  }
  if (ar === 'operator' && br === 'service') {
    const sx = a.x+a.w/2;
    return { d: `M ${sx} ${a.y+a.h} V ${midB-10} Q ${sx} ${midB} ${sx+10} ${midB} H ${b.x-6}`, x: 14, y: midB-42 };
  }
  if (ar === 'service' && br === 'gateway') {
    const tx=b.x+b.w/2;
    const routeY=390;
    return { d: `M ${a.x+a.w/2} ${a.y+a.h} V ${routeY-10} Q ${a.x+a.w/2} ${routeY} ${a.x+a.w/2+10} ${routeY} H ${tx-10} Q ${tx} ${routeY} ${tx} ${routeY-10} V ${b.y+b.h+6}`, x: 290, y: routeY-8 };
  }
  if (Math.abs(midA-midB) < 10 && a.x < b.x) {
    return { d: `M ${a.x+a.w+6} ${midA} H ${b.x-6}`, x:(a.x+a.w+b.x)/2, y:midA-12, centered:true };
  }
  const sx=a.x+a.w/2, tx=b.x+b.w/2;
  return { d: `M ${sx} ${a.y+a.h} C ${sx} ${a.y+a.h+36}, ${tx} ${b.y-36}, ${tx} ${b.y-6}`, x:(sx+tx)/2, y:(a.y+a.h+b.y)/2-10, centered:true };
}

export default function AuthorityGraph({ state }) {
  const markerId = useId().replace(/:/g, '');
  const [selectedId, setSelectedId] = useState(null);
  const nodes = useMemo(() => (state?.nodes || []).map((node,index) => {
    const role=roleFor(node);
    const position = standardPositions[role] || {x: 12 + index*140, y:263, w:118,h:102};
    return {...node,role,position};
  }),[state?.nodes]);
  const nodesById=Object.fromEntries(nodes.map(node=>[node.id,node]));
  const edges=(state?.edges || []).filter(edge=>nodesById[edge.source] && nodesById[edge.target]);
  const selected=nodesById[selectedId];
  const selectedGrantIds=new Set(edges.filter(edge=>edge.target===selectedId || edge.source===selectedId).map(edge=>edge.grantId));
  const selectedGrants=(state?.grants || []).filter(grant=>grant.principal===selectedId || grant.id===selectedId || grant.principal===selected?.principal || selectedGrantIds.has(grant.id));
  const unknown=state?.scenario==='unknown';

  return (
    <section className="panel authority-graph-panel" aria-labelledby="authority-graph-heading">
      <header className="authority-graph-heading"><h2 id="authority-graph-heading">Authority graph</h2><span><Network size={17} aria-hidden="true" /> Registered paths</span></header>
      <p className="graph-scroll-hint">Scroll horizontally to inspect every node.</p>
      <div className="authority-graph-scroll" tabIndex={0} aria-label="Scrollable registered authority graph">
        <div className={`authority-graph-stage ${state?.scenario==='alternate'?'has-alternate':''}`}>
          {!state && <p className="graph-loading">Loading authority graph…</p>}
          <svg className="authority-graph-lines" viewBox="0 0 800 410" aria-hidden="true" preserveAspectRatio="none">
            <defs>
              <marker id={`${markerId}-active`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 8 4 L 0 8 z" fill="#315ff6" /></marker>
              <marker id={`${markerId}-revoked`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 8 4 L 0 8 z" fill="#b6757a" /></marker>
            </defs>
            {edges.map(edge=>{
              const source=nodesById[edge.source], target=nodesById[edge.target];
              const line=lineFor(source,target);
              const active=edge.active!==false;
              return <g key={edge.id} className={`graph-edge ${active?'is-active':'is-revoked'}`}><title>{edge.label}: {active ? 'active registered edge' : 'inactive registered edge'}</title><path className="graph-edge-line" d={line.d} markerEnd={`url(#${markerId}-${active?'active':'revoked'})`} /><text x={line.x} y={line.y} textAnchor={line.centered?'middle':'start'}>{edgeCopy[edge.label] || edge.label || 'delegated'}</text></g>;
            })}
          </svg>
          {nodes.map(node=>{
            const m=metadata[node.role] || {label:node.label || node.id,description:node.kind || 'Registered node',Icon:CircleHelp};
            const Icon=m.Icon;
            const p=node.position;
            const incoming=edges.filter(edge=>edge.target===node.id);
            const inactive=incoming.length>0 && incoming.every(edge=>edge.active===false);
            return <button key={node.id} type="button" className={`graph-node ${inactive?'is-inactive':''} ${selectedId===node.id?'is-selected':''}`} style={{left:`${p.x/8}%`,top:`${p.y/4.1}%`,width:`${p.w/8}%`,height:`${p.h/4.1}%`}} onClick={()=>setSelectedId(selectedId===node.id?null:node.id)} aria-pressed={selectedId===node.id} aria-label={`Inspect ${m.label}`} title={`${node.label || m.label}: ${inactive?'no active registered incoming path':'registered node'}`}><Icon className="graph-node-icon" size={27} strokeWidth={1.65} aria-hidden="true" /><strong>{m.label}</strong><span>{m.description}</span></button>;
          })}
          {unknown && <div className="graph-coverage-note"><CircleHelp size={15} /> Registry coverage is incomplete</div>}
        </div>
      </div>
      <dl className="graph-state" aria-live="polite"><div><dt>Synthetic actions executed</dt><dd>{state?.stats?.protectedActions ?? 0}</dd></div><div><dt>Queued operations</dt><dd>{state?.stats?.queuedActions ?? 0}</dd></div>{state?.queue?.[0] && <div><dt>Last queued attempt</dt><dd>{state.queue[0].status}</dd></div>}</dl>
      {selected && <div className="graph-inspector" role="status"><div><strong>{selected.label || selected.id}</strong><code>{selected.id}</code><span>{selectedGrants.length ? selectedGrants.map(g=>`${g.id}: ${g.active?'active':g.revoked?'revoked':'ancestor invalid'}`).join(' · ') : 'No grant is assigned directly to this node.'}</span></div><button type="button" className="graph-inspector-close" aria-label="Close node details" onClick={()=>setSelectedId(null)}><X size={15} /></button></div>}
    </section>
  );
}
