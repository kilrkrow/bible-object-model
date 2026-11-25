"""Write dist/graph/index.html: the typed-relationship graph as one offline page.

    python build/make_graph.py

The page is self-contained (vis-network is inlined from build/vendor, MIT or Apache-2.0), so it opens from disk
with no internet. Each relationship type has its own colour and a checkbox to show or hide it; clicking a node
or an edge lists the verses behind it.
"""
import colorsys, html, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bibleobj import Bible  # noqa: E402

KIND_SHAPE = {"person": "dot", "place": "square", "group": "triangle", "speech": "diamond"}
GROUPS = [  # how the filter panel groups types; any type not listed lands in "Other"
    ("Family", ["parent_of", "descendant_of", "spouse_of", "sibling_of", "kin_of"]),
    ("Travel and letters", ["visited", "wrote_to"]),
    ("Speaking", ["preached", "spoke", "defended", "prayed"]),
    ("Acts done to people", ["killed", "imprisoned", "healed", "raised", "baptized", "taught", "chose", "replaced",
                             "heard_by", "appealed_to"]),
]


def colour(i, n):
    r, g, b = colorsys.hls_to_rgb((i / max(n, 1) + 0.03) % 1.0, 0.45, 0.65)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def main(out=ROOT / "dist/graph"):
    b = Bible.open(use_layer=False)
    types = b.edge_types()
    names = [t["type"] for t in types]
    tcol = {t: colour(i, len(names)) for i, t in enumerate(names)}
    edges = b.edges()
    used = sorted({e["subject"] for e in edges} | {e["object"] for e in edges})
    nodes = []
    for eid in used:
        e = b._entity_row(eid)
        nodes.append({"id": eid, "label": e["label"].split(" (")[0], "title": e["label"], "kind": e["kind"],
                      "shape": KIND_SHAPE.get(e["kind"], "ellipse"), "brief": e["brief"] or ""})
    links = []
    for e in edges:
        links.append({"id": e["id"], "from": e["subject"], "to": e["object"], "type": e["type"], "ref": e["ref"],
                      "quote": e["quote"], "note": e["note"], "basis": e["basis"], "seq": e["seq"],
                      "color": tcol[e["type"]]})
    listed = {t for _, ts in GROUPS for t in ts}
    groups = [(g, [t for t in ts if t in tcol]) for g, ts in GROUPS] + [("Other", [t for t in names if t not in listed])]
    groups = [(g, ts) for g, ts in groups if ts]
    data = {"nodes": nodes, "edges": links, "types": {t["type"]: {"color": tcol[t["type"]], "count": t["count"],
                                                                  "description": t["description"]} for t in types},
            "groups": groups, "hash": b.info().get("content_sha256", "")}
    js = (ROOT / "build/vendor/vis-network.min.js").read_text(encoding="utf-8")
    page = PAGE.replace("/*VIS*/", js.replace("</script", "<\\/script")) \
               .replace("/*DATA*/", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print(f"graph: {out / 'index.html'} ({len(nodes)} nodes, {len(links)} edges, {len(names)} types)")


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bible relationship graph</title>
<style>
:root{--bg:#fbfaf7;--panel:#ffffff;--ink:#1f2328;--muted:#5b6370;--line:#e4e1da;--accent:#7a4b18}
@media (prefers-color-scheme:dark){:root{--bg:#16181c;--panel:#1e2127;--ink:#e8e6e1;--muted:#9aa1ad;--line:#333842;--accent:#e0a96d}}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
#app{display:grid;grid-template-columns:280px 1fr 320px;height:100%}
aside{background:var(--panel);border-right:1px solid var(--line);overflow:auto;padding:14px 16px}
#detail{border-right:0;border-left:1px solid var(--line)}
h1{font-size:16px;margin:0 0 4px}h2{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:16px 0 6px}
p.small{color:var(--muted);font-size:12px;margin:0 0 8px}
label.t{display:flex;align-items:center;gap:8px;padding:3px 0;cursor:pointer}
label.t .sw{width:22px;height:4px;border-radius:2px;flex:none}label.t .n{margin-left:auto;color:var(--muted);font-variant-numeric:tabular-nums}
input[type=search]{width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink)}
button{font:inherit;padding:4px 9px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);cursor:pointer}
#net{height:100%;min-height:300px}
.ev{border-top:1px solid var(--line);padding:8px 0}.ev b{color:var(--accent)}.ev q{display:block;color:var(--muted);margin-top:2px}
.legend span{display:inline-block;margin-right:10px;color:var(--muted);font-size:12px}
@media (max-width:900px){#app{grid-template-columns:1fr;grid-template-rows:auto 60vh auto}aside{border:0;border-bottom:1px solid var(--line)}}
</style></head><body>
<div id="app">
<aside>
  <h1>Relationship graph</h1>
  <p class="small">Acts and Paul's letters, KJV. Every line rests on a verse; click it to see the quote.</p>
  <input type="search" id="q" placeholder="Find a person, place or speech">
  <h2>Relationship types</h2>
  <div><button id="all">All</button> <button id="none">None</button></div>
  <div id="filters"></div>
  <h2>Shapes</h2>
  <div class="legend"><span>● person</span><span>■ place</span><span>▲ group</span><span>◆ speech</span></div>
  <p class="small" id="hash"></p>
</aside>
<div id="net"></div>
<aside id="detail"><h2>Details</h2><p class="small">Click a node or a line.</p></aside>
</div>
<script>/*VIS*/</script>
<script>
const D = /*DATA*/;
const on = new Set(Object.keys(D.types));
const dark = matchMedia('(prefers-color-scheme: dark)').matches;
const ink = dark ? '#e8e6e1' : '#1f2328';
const kindColor = {person:'#3b6ea8', place:'#4c8a4c', group:'#8a6a2c', speech:'#8b4a8b'};
const nodes = new vis.DataSet(D.nodes.map(n => ({id:n.id, label:n.label, title:n.title, shape:n.shape,
  size: n.shape==='dot'?9:10, color:{background:kindColor[n.kind]||'#777', border:kindColor[n.kind]||'#777'},
  font:{color:ink, size:13}})));
const edges = new vis.DataSet(D.edges.map(e => ({id:e.id, from:e.from, to:e.to, type:e.type, color:{color:e.color, highlight:e.color},
  arrows:'to', width:1.6, title:e.type + ' · ' + e.ref})));
const visible = new vis.DataView(edges, {filter: e => on.has(e.type)});
const net = new vis.Network(document.getElementById('net'), {nodes, edges: visible},
  {physics:{solver:'forceAtlas2Based', stabilization:{iterations:250}}, interaction:{hover:true}, edges:{smooth:{type:'dynamic'}}});
const f = document.getElementById('filters');
for (const [g, ts] of D.groups) {
  const h = document.createElement('h2'); h.textContent = g; f.appendChild(h);
  for (const t of ts) {
    const m = D.types[t], l = document.createElement('label'); l.className = 't'; l.title = m.description;
    l.innerHTML = `<input type="checkbox" checked data-t="${t}"><span class="sw" style="background:${m.color}"></span>${t.replace(/_/g,' ')}<span class="n">${m.count}</span>`;
    f.appendChild(l);
  }
}
f.addEventListener('change', e => { const t = e.target.dataset.t; if (!t) return; e.target.checked ? on.add(t) : on.delete(t); visible.refresh(); });
document.getElementById('all').onclick = () => { f.querySelectorAll('input').forEach(i => { i.checked = true; on.add(i.dataset.t); }); visible.refresh(); };
document.getElementById('none').onclick = () => { f.querySelectorAll('input').forEach(i => { i.checked = false; on.delete(i.dataset.t); }); visible.refresh(); };
document.getElementById('hash').textContent = 'Data ' + D.hash.slice(0, 12);
const byId = Object.fromEntries(D.edges.map(e => [e.id, e])), nodeById = Object.fromEntries(D.nodes.map(n => [n.id, n]));
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pretty = r => { const [b, c, v] = r.split('.'); return `${b} ${c}:${v}`; };
function evHtml(e) {
  const a = nodeById[e.from].label, b = nodeById[e.to].label;
  return `<div class="ev"><b>${esc(a)}</b> ${esc(e.type.replace(/_/g,' '))} <b>${esc(b)}</b><br>${pretty(e.ref)}${e.seq?` · stop ${e.seq}`:''}<q>${esc(e.quote)}</q>${e.note?`<p class="small">${esc(e.note)}</p>`:''}</div>`;
}
const det = document.getElementById('detail');
net.on('click', p => {
  if (p.edges.length && !p.nodes.length) { det.innerHTML = '<h2>Relationship</h2>' + evHtml(byId[p.edges[0]]); return; }
  if (!p.nodes.length) return;
  const n = nodeById[p.nodes[0]];
  const es = D.edges.filter(e => (e.from === n.id || e.to === n.id) && on.has(e.type));
  det.innerHTML = `<h2>${esc(n.kind)}</h2><h1>${esc(n.title)}</h1><p class="small">${esc(n.brief)}</p>` + es.map(evHtml).join('');
});
document.getElementById('q').addEventListener('input', e => {
  const s = e.target.value.trim().toLowerCase(); if (!s) return;
  const hit = D.nodes.find(n => n.title.toLowerCase().includes(s) || n.id.includes(s));
  if (hit) { net.selectNodes([hit.id]); net.focus(hit.id, {scale:1.2, animation:true}); }
});
</script></body></html>
"""

if __name__ == "__main__":
    main()
