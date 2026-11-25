"""Draw Paul's route in Acts: dist/maps/paul-journeys.{geojson,svg,html}.

The SVG is self-contained (Natural Earth land, public domain). The HTML uses Leaflet with
OpenStreetMap tiles, so it needs an internet connection when opened. Deterministic output.
"""
import json, pathlib, sys
from html import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bibleobj import Bible  # noqa: E402

LEG_COLORS = {"Conversion": "#6b7280", "Early years": "#9ca3af", "Famine relief": "#a16207",
              "First journey": "#2563eb", "Jerusalem council": "#7c3aed", "Second journey": "#059669",
              "Third journey": "#dc2626", "Arrest and trials": "#b45309", "Voyage to Rome": "#0e7490"}
W, H = 1200, 620
LON0, LON1, LAT0, LAT1 = 10.0, 38.5, 29.5, 43.5


def xy(lon, lat):
    return round((lon - LON0) / (LON1 - LON0) * W, 1), round((LAT1 - lat) / (LAT1 - LAT0) * H, 1)


def land_paths():
    g = json.loads((ROOT / "sources/naturalearth/geojson/ne_50m_land.geojson").read_text(encoding="utf-8"))
    out = []
    for f in g["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            if not any(LON0 - 5 < x < LON1 + 5 and LAT0 - 5 < y < LAT1 + 5 for x, y in poly[0]):
                continue
            out.append("".join("M" + "L".join(f"{a},{b}" for a, b in (xy(x, y) for x, y in ring)) + "Z"
                               for ring in poly))
    return out


def svg(j):
    stops = [s for s in j["stops"] if s["site"]]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H + 70}" font-family="Georgia, serif">',
             f'<title>Paul in Acts, in narrative order</title><rect width="{W}" height="{H + 70}" fill="#cfe2f3"/>',
             f'<clipPath id="c"><rect width="{W}" height="{H}"/></clipPath><g clip-path="url(#c)">',
             *(f'<path d="{d}" fill="#efe5c8" fill-rule="evenodd" stroke="#c9bfa5" stroke-width="0.6"/>'
               for d in land_paths())]
    for a, b in zip(stops, stops[1:]):
        (x1, y1), (x2, y2) = xy(a["site"]["lon"], a["site"]["lat"]), xy(b["site"]["lon"], b["site"]["lat"])
        if (x1, y1) == (x2, y2):
            continue
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{LEG_COLORS[b["leg"]]}" '
                     f'stroke-width="2.2" stroke-opacity="0.85"><title>{escape(a["place"])} to {escape(b["place"])} '
                     f'({b["ref"].replace("Acts.", "Acts ").replace(".", ":", 1)})</title></line>')
    seen = {}
    for s in stops:
        seen.setdefault(s["place_id"], s)
    for pid, s in seen.items():
        x, y = xy(s["site"]["lon"], s["site"]["lat"])
        parts.append(f'<circle cx="{x}" cy="{y}" r="3.4" fill="#111827"><title>{escape(s["place"])}</title></circle>')
        for attrs in ('fill="#ffffff" stroke="#ffffff" stroke-width="3" stroke-linejoin="round"', 'fill="#111827"'):
            parts.append(f'<text x="{x + 5}" y="{y - 4}" font-size="11" {attrs}>{escape(s["place"])}</text>')
    parts.append("</g>")
    x = 14
    for leg, col in LEG_COLORS.items():
        parts.append(f'<rect x="{x}" y="{H + 18}" width="16" height="6" fill="{col}"/>'
                     f'<text x="{x + 20}" y="{H + 25}" font-size="11" fill="#111827">{escape(leg)}</text>')
        x += 20 + 6.4 * len(leg) + 12
    parts.append(f'<text x="14" y="{H + 55}" font-size="11" fill="#374151">Order is the narrative order of Acts (KJV); '
                 'Acts gives no dates. Sites: OpenBible.info (CC BY 4.0), best-scored identification. '
                 'Land: Natural Earth (public domain).</text></svg>')
    return "\n".join(parts) + "\n"


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paul in Acts</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>html,body,#map{height:100%;margin:0}.lg{background:#fff;padding:6px 8px;font:12px Georgia,serif;line-height:1.5}</style>
</head><body><div id="map"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
const DATA = __DATA__;
const COLORS = __COLORS__;
const map = L.map('map').setView([36, 25], 5);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 12,
  attribution: '&copy; OpenStreetMap contributors | sites: OpenBible.info CC BY 4.0 | text: KJV'}).addTo(map);
const pts = DATA.features.filter(f => f.geometry.type === 'Point');
for (let i = 1; i < pts.length; i++) {
  const a = pts[i-1].geometry.coordinates, b = pts[i].geometry.coordinates, p = pts[i].properties;
  L.polyline([[a[1], a[0]], [b[1], b[0]]], {color: COLORS[p.leg], weight: 3, opacity: .8}).addTo(map);
}
for (const f of pts) {
  const p = f.properties, c = f.geometry.coordinates;
  L.circleMarker([c[1], c[0]], {radius: 4, color: '#111', fillOpacity: 1}).addTo(map)
   .bindPopup(`<b>${p.seq}. ${p.place}</b><br>${p.leg}<br>${p.ref.replace('Acts.', 'Acts ').replace('.', ':')}: “${p.quote}”`);
}
const lg = L.control({position: 'bottomleft'});
lg.onAdd = () => { const d = L.DomUtil.create('div', 'lg');
  d.innerHTML = Object.entries(COLORS).map(([k, v]) => `<span style="color:${v}">&#9644;</span> ${k}`).join('<br>'); return d; };
lg.addTo(map);
</script></body></html>
"""


def main():
    b = Bible.open(use_layer=False)
    j, gj = b.journey("paul"), b.journey_geojson("paul")
    out = ROOT / "dist/maps"
    out.mkdir(parents=True, exist_ok=True)
    (out / "paul-journeys.geojson").write_text(json.dumps(gj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "paul-journeys.svg").write_text(svg(j), encoding="utf-8")
    (out / "paul-journeys.html").write_text(HTML.replace("__DATA__", json.dumps(gj, ensure_ascii=False))
                                            .replace("__COLORS__", json.dumps(LEG_COLORS)), encoding="utf-8")
    print(f"maps: {out}")


if __name__ == "__main__":
    main()
