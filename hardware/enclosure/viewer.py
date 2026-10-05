"""Write one self-contained HTML file with an interactive 3D view (three.js from a CDN; drag to rotate, scroll to zoom)."""
import json


def _mesh(shape, tol=0.05):
    if isinstance(shape, tuple):                       # already (flat xyz list, flat triangle index list)
        return shape
    verts, tris = shape.tessellate(tol)
    return [round(c, 3) for p in verts for c in (p.X, p.Y, p.Z)], [i for t in tris for i in t]


def write_html(path, items, title="3D view"):
    """items: [(name, shape, colour, opacity)]"""
    data = []
    for name, shape, colour, opacity in items:
        v, i = _mesh(shape)
        data.append({"name": name, "colour": colour, "opacity": opacity, "v": v, "i": i})
    with open(path, "w") as f:
        f.write(HTML.replace("__TITLE__", title).replace("__DATA__", json.dumps(data)))


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  html, body { margin: 0; height: 100%; background: #f4f5f7; font-family: -apple-system, 'Segoe UI', sans-serif; color: #1f2328; }
  #box { position: absolute; inset: 0; }
  #info { position: absolute; left: 14px; top: 12px; background: rgba(255,255,255,.88); padding: 10px 14px; border-radius: 10px; font-size: 14px; line-height: 1.5; }
  #info b { font-size: 15px; }
  .sw { display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: 7px; border: 1px solid rgba(0,0,0,.25); }
  #hint { color: #59636e; font-size: 12.5px; margin-top: 6px; }
  #err { position: absolute; left: 14px; bottom: 12px; color: #b3261e; font-size: 13px; }
</style></head>
<body>
<div id="box"></div>
<div id="info"><b>__TITLE__</b><div id="legend"></div><div id="hint">drag = rotate &nbsp; scroll = zoom &nbsp; right-drag = pan</div></div>
<div id="err"></div>
<script type="importmap">{"imports": {"three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
  "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
const DATA = __DATA__;
try {
  const box = document.getElementById('box');
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf4f5f7);
  const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.5, 2000);
  camera.up.set(0, 0, 1);
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(devicePixelRatio);
  renderer.setSize(innerWidth, innerHeight);
  box.appendChild(renderer.domElement);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.1));
  const sun = new THREE.DirectionalLight(0xffffff, 1.3);
  sun.position.set(60, -80, 120);
  scene.add(sun);
  const bounds = new THREE.Box3();
  const legend = document.getElementById('legend');
  for (const d of DATA) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(d.v, 3));
    g.setIndex(d.i);
    g.computeVertexNormals();
    const m = new THREE.MeshStandardMaterial({ color: d.colour, roughness: 0.55, metalness: 0.05,
      transparent: d.opacity < 1, opacity: d.opacity, side: THREE.DoubleSide, depthWrite: d.opacity >= 1 });
    const mesh = new THREE.Mesh(g, m);
    scene.add(mesh);
    scene.add(new THREE.LineSegments(new THREE.EdgesGeometry(g, 30), new THREE.LineBasicMaterial({ color: 0x333333, transparent: true, opacity: 0.45 })));
    bounds.expandByObject(mesh);
    const row = document.createElement('div');
    row.innerHTML = '<span class="sw" style="background:' + d.colour + '"></span>' + d.name;
    legend.appendChild(row);
  }
  const c = bounds.getCenter(new THREE.Vector3()), s = bounds.getSize(new THREE.Vector3());
  const r = Math.max(s.x, s.y, s.z);
  camera.position.set(c.x + r * 1.1, c.y - r * 1.5, c.z + r * 1.1);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.copy(c);
  controls.enableDamping = true;
  controls.update();
  addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
  (function loop() { requestAnimationFrame(loop); controls.update(); renderer.render(scene, camera); })();
} catch (e) { document.getElementById('err').textContent = 'Could not draw the 3D view: ' + e; }
</script>
</body></html>
"""
