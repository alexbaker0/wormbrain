// Runs web/sim.js on an exported model and compares with a Python reference run.
//   node web/agree.mjs <model.json> <reference.json>
// Prints the largest absolute differences as JSON (used by tests/test_web.py).
import { readFileSync } from "node:fs";
import { Field, PatchField, Worm } from "./sim.js";

const [model, ref] = process.argv.slice(2).map((p) => JSON.parse(readFileSync(p, "utf8")));
const f = ref.field;
const field = f.type === "patches"
  ? new PatchField({ xy: f.xy, half: f.half_size, sigma: f.sigma, capacity: f.capacity,
      eatRadius: f.eat_radius, eatRate: f.eat_rate, periodic: f.periodic })
  : new Field(f.peak, f.sigma, f.amplitude);
const worm = new Worm(model, field, { lesion: ref.lesion, dt: ref.dt });
worm.reset(ref.head0, ref.heading0);

const err = { head: 0, theta0: 0, kappa: 0, v: 0, eaten: 0 };
const maxAbs = (a, b) => a.reduce((m, x, i) => Math.max(m, Math.abs(x - b[i])), 0);
let c = 0;
for (let k = 1; k <= ref.steps; k++) {
  worm.step();
  if (c < ref.out.step.length && k === ref.out.step[c]) {
    err.head = Math.max(err.head, maxAbs(worm.body.head, ref.out.head[c]));
    err.theta0 = Math.max(err.theta0, Math.abs(worm.body.theta0 - ref.out.theta0[c]));
    err.kappa = Math.max(err.kappa, maxAbs(Array.from(worm.body.kappa), ref.out.kappa[c]));
    err.v = Math.max(err.v, maxAbs(Array.from(worm.brain.v), ref.out.v[c]));
    err.eaten = Math.max(err.eaten, Math.abs(worm.eaten - ref.out.eaten[c]));
    c++;
  }
}
console.log(JSON.stringify({ checked: c, ...err }));
