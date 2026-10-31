// Runs web/sim.js on an exported model and compares with a Python reference run.
//   node web/agree.mjs <model.json> <reference.json>
// Prints the largest absolute differences as JSON (used by tests/test_web.py).
import { readFileSync } from "node:fs";
import { Field, Worm } from "./sim.js";

const [model, ref] = process.argv.slice(2).map((p) => JSON.parse(readFileSync(p, "utf8")));
const f = ref.field;
const worm = new Worm(model, new Field(f.peak, f.sigma, f.amplitude), { lesion: ref.lesion, dt: ref.dt });
worm.reset(ref.head0, ref.heading0);

const err = { head: 0, theta0: 0, kappa: 0, v: 0 };
const maxAbs = (a, b) => a.reduce((m, x, i) => Math.max(m, Math.abs(x - b[i])), 0);
let c = 0;
for (let k = 1; k <= ref.steps; k++) {
  worm.step();
  if (c < ref.out.step.length && k === ref.out.step[c]) {
    err.head = Math.max(err.head, maxAbs(worm.body.head, ref.out.head[c]));
    err.theta0 = Math.max(err.theta0, Math.abs(worm.body.theta0 - ref.out.theta0[c]));
    err.kappa = Math.max(err.kappa, maxAbs(Array.from(worm.body.kappa), ref.out.kappa[c]));
    err.v = Math.max(err.v, maxAbs(Array.from(worm.brain.v), ref.out.v[c]));
    c++;
  }
}
console.log(JSON.stringify({ checked: c, ...err }));
