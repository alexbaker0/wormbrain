# ruff: noqa: E501  (the embedded HTML/JS template has long lines)
"""Build a self-contained HTML replay of trained worms, with live neuron activity.

    uv run python scripts/make_replay.py [--out reports/replay/worm_replay.html]

Simulates a few trained brains from reports/comparison/runs/ from the same start,
records the body and every neuron's transmitter release, and writes one HTML file
(data embedded, no dependencies) that plays it back. This is a replay of Python
simulations, not the in-browser simulation planned for milestone 8.
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

import numpy as np

from wormbrain.brain import ACTIVATION, Brain, BrainConfig, BrainController
from wormbrain.chemotaxis import env_config, load_run_config
from wormbrain.connectome import build_connectome, load_config
from wormbrain.controls import make_condition
from wormbrain.env import Field, make_body, run_episode, start_positions

RUNS = Path("reports/comparison/runs")
SCENARIOS = [
    ("Real connectome", "real_glu-inhibitory_seed0", ()),
    ("Real connectome, salt sensors silenced", "real_glu-inhibitory_seed0", ("ASEL", "ASER")),
    ("Random wiring", "random_glu-inhibitory_seed0", ()),
]
KEY = ["ASEL", "ASER", "AIYL", "AIZL", "AIBL", "RIAL", "SMDDL", "SMDVL", "RMDDL", "RMDVL",
       "AVAL", "AVBL"]  # fmt: skip
ROLE_ORDER = ["sensory", "inter", "motor", "other"]
DURATION, DT, EVERY = 120.0, 0.02, 5  # 0.1 s per frame


def b64(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def simulate(run: dict, lesion, head, heading, field, body):
    cfg = load_config("configs/connectome.yaml")
    cfg["signs"]["glutamate"] = run["glutamate"]
    conn = make_condition(build_connectome(cfg), run["condition"], run["seed"])
    brain = Brain(conn, BrainConfig(bounded=run["bounded"], activation=run["activation"],
                                    lesion=tuple(lesion)))  # fmt: skip
    ctrl = BrainController(brain, np.array(run["x"])[None], record_every=EVERY)
    ep = run_episode(ctrl, field, head, heading, duration=DURATION, dt=DT, body=body,
                     record_every=EVERY, record_shapes=True)  # fmt: skip
    v = np.concatenate([np.zeros((1, brain.n)), np.array(ctrl.activity)[:, 0]])
    release = ACTIVATION[brain.cfg.activation](ctrl.p["gain"][0] * v)
    return conn, ep, release


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default="reports/replay/worm_replay.html")
    p.add_argument("--start", type=int, default=3, help="index of the test start to use")
    args = p.parse_args()

    run_cfg = load_run_config("configs/chemotaxis.yaml")
    env = env_config(run_cfg["env"], run_cfg["env_overrides"])
    field = Field(env["field"])
    body = make_body(env["body"])
    heads, headings = start_positions(env["start"], field, 32, run_cfg["evaluation"]["test_seed"])
    head, heading = heads[args.start : args.start + 1], headings[args.start : args.start + 1]

    scenarios, order, groups, names = [], None, None, None
    for title, run_name, lesion in SCENARIOS:
        run = json.loads((RUNS / f"{run_name}.json").read_text())
        conn, ep, release = simulate(run, lesion, head, heading, field, body)
        if order is None:
            order = sorted(range(conn.n), key=lambda k: (ROLE_ORDER.index(conn.role[k]),
                                                        conn.cell_class[k], conn.neurons[k]))  # fmt: skip
            names = [conn.neurons[k] for k in order]
            groups = [conn.role[k] for k in order]
        nodes = np.round(ep.nodes[:, 0] * 1000).astype(np.int16)  # micrometres
        act = np.round(np.clip(release[:, order], -1, 1) * 127).astype(np.int8)
        dist = float(np.linalg.norm(ep.centroid[-1, 0] - field.center))
        scenarios.append({
            "title": title,
            "run": run_name,
            "lesion": list(lesion),
            "testReward": run["test"]["gaussian"]["brain"]["reward_mean"],
            "finalDistance": dist,
            "nodes": b64(nodes),
            "act": b64(act),
            "conc": [round(float(c), 4) for c in ep.conc[:, 0]],
        })  # fmt: skip
        print(f"{title}: final distance {dist:.2f} mm")

    g = np.linspace(-10, 10, 120)
    xx, yy = np.meshgrid(g, g)
    data = {
        "dt": DT * EVERY,
        "frames": len(scenarios[0]["conc"]),
        "nNodes": int(ep.nodes.shape[2]),
        "neurons": names,
        "groups": groups,
        "key": [names.index(k) for k in KEY],
        "keyNames": KEY,
        "food": field.center.tolist(),
        "fieldGrid": {
            "extent": 10,
            "n": 120,
            "values": b64(np.round(field.conc(np.stack([xx, yy], -1)) * 255).astype(np.uint8)),
        },  # fmt: skip
        "scenarios": scenarios,
    }
    html = TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Connectome Worm Replay</title>
<style>
  :root { --bg:#f6f7fb; --card:#ffffff; --ink:#1d2433; --muted:#5f6b7f; --line:#dfe3ec;
          --accent:#0f8b6c; --worm:#c2410c; --trail:#2563eb; }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) { --bg:#10131a; --card:#171b24; --ink:#e7eaf0;
      --muted:#9aa4b5; --line:#2a3140; --accent:#34d399; --worm:#fb923c; --trail:#60a5fa; } }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
  main { max-width:1180px; margin:0 auto; padding:16px; }
  h1 { font-size:20px; margin:4px 0 2px; }
  .sub { color:var(--muted); margin:0 0 12px; }
  .tabs { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:12px; }
  .tabs button { border:1px solid var(--line); background:var(--card); color:var(--ink);
                 padding:7px 12px; border-radius:8px; cursor:pointer; font:inherit; }
  .tabs button.on { border-color:var(--accent); box-shadow:inset 0 0 0 1px var(--accent); }
  .grid { display:grid; grid-template-columns: minmax(0,1.1fr) minmax(0,1fr); gap:12px; }
  @media (max-width: 820px) { .grid { grid-template-columns: 1fr; } }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:10px; }
  .card h2 { font-size:13px; margin:0 0 6px; color:var(--muted); font-weight:600; }
  canvas { width:100%; display:block; border-radius:8px; }
  .row { display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin:10px 0 0; }
  .row button { font:inherit; padding:6px 14px; border-radius:8px; border:1px solid var(--line);
                background:var(--accent); color:#fff; cursor:pointer; min-width:84px; }
  input[type=range] { flex:1; min-width:160px; accent-color:var(--accent); }
  select { font:inherit; padding:5px; border-radius:8px; border:1px solid var(--line);
           background:var(--card); color:var(--ink); }
  .stat { color:var(--muted); font-variant-numeric: tabular-nums; }
  .note { color:var(--muted); font-size:12px; margin-top:12px; }
  .legend { display:flex; gap:10px; align-items:center; font-size:12px; color:var(--muted);
            margin-top:6px; }
  .bar { width:120px; height:10px; border-radius:3px;
         background:linear-gradient(90deg,#2563eb,#e5e7eb 50%,#dc2626); }
</style>
</head>
<body>
<main>
  <h1>Connectome Worm: replay</h1>
  <p class="sub">A simulated worm whose brain is the real wiring diagram of <i>C. elegans</i>
    (282 neurons), trained to crawl towards food by sensing salt. Green shading is the salt
    concentration; the food is at its peak.</p>
  <div class="tabs" id="tabs"></div>
  <div class="grid">
    <div class="card">
      <h2>Arena (16 mm across) and close-up of the body</h2>
      <canvas id="arena" width="640" height="640"></canvas>
    </div>
    <div class="card">
      <h2>All 282 neurons: transmitter release right now</h2>
      <canvas id="neurons" width="560" height="300"></canvas>
      <div class="legend"><span>less</span><div class="bar"></div><span>more than at rest</span></div>
      <h2 style="margin-top:12px">Key neurons, last 20 s (each scaled to its own range)</h2>
      <canvas id="traces" width="560" height="300"></canvas>
    </div>
  </div>
  <div class="row">
    <button id="play">Pause</button>
    <input type="range" id="scrub" min="0" value="0">
    <select id="speed"><option value="1">1×</option><option value="4">4×</option>
      <option value="10" selected>10×</option><option value="20">20×</option></select>
    <span class="stat" id="stat"></span>
  </div>
  <p class="note" id="note"></p>
  <p class="note">Replay of Python simulations from the <a href="https://github.com/alexbaker0/wormbrain">wormbrain</a>
    project (milestone 6 runs; held-out start). Real worms crawl at about 0.2 mm/s, so 1×
    is real time. Brain: graded neurons on the Cook et al. 2019 connectome; only per-class
    neuron parameters were trained.</p>
</main>
<script>
const D = __DATA__;
const dec = (s, T) => { const b = atob(s), u = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return new T(u.buffer); };
const F = D.frames, NN = D.nNodes, NR = D.neurons.length;
for (const s of D.scenarios) { s.N = dec(s.nodes, Int16Array); s.A = dec(s.act, Int8Array);
  // each key trace is scaled to its own range over the episode (at least 0.1 wide)
  s.rng = D.key.map(ni => { let lo = 127, hi = -127;
    for (let f = 0; f < F; f++) { const a = s.A[f * NR + ni]; lo = Math.min(lo, a); hi = Math.max(hi, a); }
    const mid = (lo + hi) / 2, half = Math.max((hi - lo) / 2, 0.05 * 127); return [mid, half]; }); }
const field = dec(D.fieldGrid.values, Uint8Array);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let cur = 0, frame = 0, playing = true, last = performance.now(), acc = 0;

const tabs = document.getElementById("tabs");
D.scenarios.forEach((s, i) => { const b = document.createElement("button");
  b.textContent = s.title; b.onclick = () => { cur = i; draw(); mark(); }; tabs.appendChild(b); });
const mark = () => { [...tabs.children].forEach((b, i) => b.classList.toggle("on", i === cur));
  const s = D.scenarios[cur];
  document.getElementById("note").textContent = (s.lesion.length ?
    "Same trained brain with " + s.lesion.join(" and ") + " silenced. " : "") +
    "Over 32 held-out starts this brain scored " + s.testReward.toFixed(2) +
    " (hand-coded steering: 0.08). Run: " + s.run + "."; };
const scrub = document.getElementById("scrub"); scrub.max = F - 1;
scrub.oninput = () => { frame = +scrub.value; draw(); };
const playBtn = document.getElementById("play");
playBtn.onclick = () => { playing = !playing; playBtn.textContent = playing ? "Pause" : "Play"; };

// field image, drawn once
const fieldImg = document.createElement("canvas"); fieldImg.width = fieldImg.height = D.fieldGrid.n;
{ const c = fieldImg.getContext("2d"), im = c.createImageData(D.fieldGrid.n, D.fieldGrid.n);
  for (let j = 0; j < D.fieldGrid.n; j++) for (let i = 0; i < D.fieldGrid.n; i++) {
    const v = field[j * D.fieldGrid.n + i] / 255, k = ((D.fieldGrid.n - 1 - j) * D.fieldGrid.n + i) * 4;
    im.data[k] = 235 - 200 * v; im.data[k + 1] = 245 - 110 * v; im.data[k + 2] = 235 - 180 * v;
    im.data[k + 3] = 255; }
  c.putImageData(im, 0, 0); }

const node = (s, f, i) => [s.N[(f * NN + i) * 2] / 1000, s.N[(f * NN + i) * 2 + 1] / 1000];
const centroid = (s, f) => { let x = 0, y = 0; for (let i = 0; i < NN; i++) {
  const p = node(s, f, i); x += p[0]; y += p[1]; } return [x / NN, y / NN]; };

function drawWorm(ctx, s, f, tx, width) {
  ctx.lineCap = ctx.lineJoin = "round"; ctx.strokeStyle = css("--worm"); ctx.lineWidth = width;
  ctx.beginPath(); for (let i = 0; i < NN; i++) { const [x, y] = tx(node(s, f, i));
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); } ctx.stroke();
  const [hx, hy] = tx(node(s, f, 0)); ctx.fillStyle = css("--ink");
  ctx.beginPath(); ctx.arc(hx, hy, width * 0.55, 0, 7); ctx.fill(); }

function drawArena() {
  const cv = document.getElementById("arena"), ctx = cv.getContext("2d"), W = cv.width, s = D.scenarios[cur];
  const R = 8, tx = ([x, y]) => [(x + R) / (2 * R) * W, (R - y) / (2 * R) * W];
  const e = D.fieldGrid.extent, a = tx([-e, e]), b = tx([e, -e]);
  ctx.imageSmoothingEnabled = true; ctx.drawImage(fieldImg, a[0], a[1], b[0] - a[0], b[1] - a[1]);
  const fp = tx(D.food); ctx.fillStyle = css("--accent"); ctx.beginPath(); ctx.arc(fp[0], fp[1], 6, 0, 7); ctx.fill();
  ctx.strokeStyle = css("--trail"); ctx.globalAlpha = 0.7; ctx.lineWidth = 1.6; ctx.beginPath();
  for (let f = 0; f <= frame; f += 2) { const [x, y] = tx(centroid(s, f)); f ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
  ctx.stroke(); ctx.globalAlpha = 1;
  drawWorm(ctx, s, frame, tx, 3);
  // close-up following the worm
  const Z = W * 0.34, zx = W - Z - 10, zy = 10, c = centroid(s, frame), span = 1.6;
  ctx.fillStyle = css("--card"); ctx.strokeStyle = css("--line"); ctx.lineWidth = 1;
  ctx.fillRect(zx, zy, Z, Z); ctx.strokeRect(zx, zy, Z, Z);
  const tz = ([x, y]) => [zx + ((x - c[0]) / span + 0.5) * Z, zy + ((c[1] - y) / span + 0.5) * Z];
  ctx.save(); ctx.beginPath(); ctx.rect(zx, zy, Z, Z); ctx.clip(); drawWorm(ctx, s, frame, tz, 9); ctx.restore();
  ctx.fillStyle = css("--muted"); ctx.font = "12px system-ui"; ctx.fillText("close-up (1.6 mm)", zx + 8, zy + Z - 8);
}

function color(v) { // -1 blue, 0 grey, +1 red
  const t = Math.max(-1, Math.min(1, v));
  return t >= 0 ? `rgb(${229 - 9 * t},${231 - 193 * t},${235 - 197 * t})`
                : `rgb(${229 + 192 * t},${231 + 132 * t},${235 + 0 * t})`; }

function drawNeurons() {
  const cv = document.getElementById("neurons"), ctx = cv.getContext("2d"), W = cv.width, H = cv.height;
  const s = D.scenarios[cur]; ctx.clearRect(0, 0, W, H);
  const cols = 24, size = Math.floor((W - 90) / cols), names = ["sensory", "inter", "motor", "other"];
  let y = 4;
  for (const g of names) {
    const idx = []; D.groups.forEach((gg, i) => gg === g && idx.push(i)); if (!idx.length) continue;
    ctx.fillStyle = css("--muted"); ctx.font = "12px system-ui"; ctx.fillText(g + " (" + idx.length + ")", 0, y + 12);
    idx.forEach((n, k) => { const r = Math.floor(k / cols), cl = k % cols;
      ctx.fillStyle = color(s.A[frame * NR + n] / 127);
      ctx.fillRect(90 + cl * size, y + r * size, size - 1, size - 1); });
    y += Math.ceil(idx.length / cols) * size + 8; }
}

function drawTraces() {
  const cv = document.getElementById("traces"), ctx = cv.getContext("2d"), W = cv.width, H = cv.height;
  const s = D.scenarios[cur], n = D.key.length, rowH = H / n, win = Math.round(20 / D.dt);
  ctx.clearRect(0, 0, W, H); ctx.font = "11px system-ui";
  D.key.forEach((ni, r) => { const y0 = r * rowH + rowH / 2;
    ctx.strokeStyle = css("--line"); ctx.beginPath(); ctx.moveTo(60, y0); ctx.lineTo(W, y0); ctx.stroke();
    ctx.fillStyle = css("--muted"); ctx.fillText(D.keyNames[r], 0, y0 + 4);
    const [mid, half] = s.rng[r];
    ctx.strokeStyle = css("--worm"); ctx.lineWidth = 1.4; ctx.beginPath();
    for (let k = 0; k < win; k++) { const f = frame - win + 1 + k; if (f < 0) continue;
      const x = 60 + k / (win - 1) * (W - 62), y = y0 - (s.A[f * NR + ni] - mid) / half * rowH * 0.42;
      k && f > 0 ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
    ctx.stroke(); ctx.lineWidth = 1; });
}

function draw() {
  drawArena(); drawNeurons(); drawTraces(); scrub.value = frame;
  const s = D.scenarios[cur], c = centroid(s, frame);
  const d = Math.hypot(c[0] - D.food[0], c[1] - D.food[1]);
  document.getElementById("stat").textContent =
    `t = ${(frame * D.dt).toFixed(1)} s · ${d.toFixed(2)} mm from food · salt ${s.conc[frame].toFixed(3)}`;
}

function tick(now) {
  if (playing) { acc += (now - last) / 1000 * +document.getElementById("speed").value;
    while (acc >= D.dt) { acc -= D.dt; frame = frame + 1 >= F ? 0 : frame + 1; } draw(); }
  last = now; requestAnimationFrame(tick); }
mark(); draw(); requestAnimationFrame(tick);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
