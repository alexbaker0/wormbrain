// Browser (and Node) port of the wormbrain simulation: src/wormbrain/brain.py,
// body.py and the Gaussian field in env.py. It follows the Python step for step,
// in the same order, so tests/test_web.py can check the two agree.
// Models come from src/wormbrain/export.py.

const sigmoid = (x) => 0.5 * (1 + Math.tanh(0.5 * x));
const ACT = { tanh: Math.tanh, sigmoid };
export const ROWS = 24; // muscle rows per quadrant; quadrants DL, DR, VL, VR

export class Field {
  constructor(peak = [0, 0], sigma = 4, amplitude = 1) {
    this.peak = [...peak]; this.sigma = sigma; this.amp = amplitude;
  }
  conc(x, y) {
    const dx = x - this.peak[0], dy = y - this.peak[1];
    return this.amp * Math.exp(-(dx ** 2 + dy ** 2) / (2 * this.sigma ** 2));
  }
}

export class Brain {
  constructor(m, lesion = []) {
    this.m = m;
    const n = (this.n = m.neurons.length);
    this.alive = new Float64Array(n).fill(1);
    for (const name of lesion) this.alive[m.neurons.indexOf(name)] = 0;
    const al = this.alive;
    // lesions are applied after normalisation, as in brain.py
    this.W = coo(m.W, (r) => al[r]);
    this.M = coo(m.M, (r, c) => al[r] * al[c]);
    this.R = coo(m.R, (r) => al[r]);
    this.gapSelf = new Float64Array(n);
    for (let e = 0; e < this.M.val.length; e++) this.gapSelf[this.M.col[e]] += this.M.val[e];
    this.act = ACT[m.activation];
    this.reset();
  }
  reset() {
    this.v = new Float64Array(this.n);
    this.a = new Float64Array(this.n);
    this.out = new Float64Array(this.n);
    this.cAvg = null;
  }
  sensoryInput(conc, kappa, dt) {
    const m = this.m, inp = new Float64Array(this.n);
    if (this.cAvg === null) this.cAvg = conc;
    const rel = (conc - this.cAvg) / (m.concRef + Math.abs(this.cAvg));
    this.cAvg = this.cAvg + ((conc - this.cAvg) * dt) / m.saltTau;
    for (const i of m.onIdx) inp[i] += m.saltOn * Math.max(rel, 0);
    for (const i of m.offIdx) inp[i] += m.saltOff * Math.max(-rel, 0);
    const kMax = m.body.kappaMax;
    m.propIdx.forEach((i, j) => {
      let s = 0;
      const row = m.jointsToProp[j];
      for (let k = 0; k < row.length; k++) s += kappa[k] * row[k];
      inp[i] += m.proprioGain * m.propSide[j] * (s / kMax);
    });
    return inp;
  }
  step(conc, kappa, dt) {
    const m = this.m, n = this.n, v = this.v, a = this.a, out = this.out;
    for (let i = 0; i < n; i++) out[i] = this.act(m.gain[i] * v[i]) * this.alive[i];
    const chem = matvec(this.W, out, n), gap = matvec(this.M, v, n);
    const inp = this.sensoryInput(conc, kappa, dt);
    const ra = m.adapt ? dt / m.adaptTau : 0;
    for (let i = 0; i < n; i++) {
      const drive = m.gChem * chem[i] + m.gGap * gap[i] + m.bias[i] + inp[i];
      const r = dt / m.tau[i];
      const leak = 1 + r * (1 + m.gGap * this.gapSelf[i]);
      if (m.adapt) {
        const w = m.adapt[i];
        v[i] = (v[i] + r * drive - (r * w * a[i]) / (1 + ra)) / (leak + (r * w * ra) / (1 + ra));
        a[i] = (a[i] + ra * v[i]) / (1 + ra);
      } else {
        v[i] = (v[i] + r * drive) / leak;
      }
      v[i] *= this.alive[i];
      if (!Number.isFinite(v[i])) throw new Error("brain state became non-finite");
    }
    const drive = matvec(this.R, out, 4 * ROWS), muscle = new Float64Array(4 * ROWS);
    const dv = m.muscleDV || 0; // dorsal/ventral offset: + on DL, DR rows, - on VL, VR rows
    for (let s = 0; s < 4 * ROWS; s++)
      muscle[s] = sigmoid(m.muscleGain * drive[s] + m.muscleBias + (s < 2 * ROWS ? 0.5 : -0.5) * dv);
    return muscle;
  }
}

export class Body {
  constructor(b) {
    this.b = b;
    this.n = b.nSegments;
    this.ds = b.length / b.nSegments;
  }
  reset(head, heading) {
    this.head = [...head];
    this.theta0 = heading + Math.PI;
    this.kappa = new Float64Array(this.n - 1);
  }
  angles(theta0, kappa) {
    const th = new Float64Array(this.n);
    let c = 0;
    th[0] = theta0;
    for (let i = 1; i < this.n; i++) { c += kappa[i - 1] * this.ds; th[i] = theta0 + c; }
    return th;
  }
  nodes() {
    const th = this.angles(this.theta0, this.kappa), pts = [[...this.head]];
    let sx = 0, sy = 0;
    for (let i = 0; i < this.n; i++) {
      sx += this.ds * Math.cos(th[i]); sy += this.ds * Math.sin(th[i]);
      pts.push([this.head[0] + sx, this.head[1] + sy]);
    }
    return pts;
  }
  centroid() {
    const p = this.nodes();
    let x = 0, y = 0;
    for (let i = 0; i < this.n; i++) { x += 0.5 * (p[i][0] + p[i + 1][0]); y += 0.5 * (p[i][1] + p[i + 1][1]); }
    return [x / this.n, y / this.n];
  }
  targetCurvature(muscle) {
    const b = this.b, nj = this.n - 1, t = new Float64Array(nj);
    const clip = (x) => Math.min(1, Math.max(0, x));
    const dv = new Float64Array(ROWS);
    for (let r = 0; r < ROWS; r++) {
      const dorsal = 0.5 * (clip(muscle[r]) + clip(muscle[ROWS + r]));
      const ventral = 0.5 * (clip(muscle[2 * ROWS + r]) + clip(muscle[3 * ROWS + r]));
      dv[r] = b.kappaMax * (dorsal - ventral);
    }
    for (let j = 0; j < nj; j++) {
      let s = 0;
      for (let r = 0; r < ROWS; r++) s += dv[r] * b.rowsToJoints[j][r];
      t[j] = s;
    }
    return t;
  }
  // Rigid-body velocity (head velocity, rotation rate) making RFT force and torque vanish.
  velocities(head, theta0, kappa, dkappa) {
    const n = this.n, ds = this.ds, dT = this.b.dragT, dN = this.b.dragN;
    const th = this.angles(theta0, kappa);
    let ca0 = 0, ca1 = 0, cb0 = 0, cb1 = 0, q = 0;
    const A = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], rhs = [0, 0, 0];
    for (let i = 0; i < n; i++) {
      if (i > 0) q += dkappa[i - 1] * ds;
      const t0 = Math.cos(th[i]), t1 = Math.sin(th[i]), n0 = -Math.sin(th[i]), n1 = Math.cos(th[i]);
      // midpoint velocity per unit head rotation (a) and from the shape change (b)
      const fa0 = ds * n0, fa1 = ds * n1, fb0 = ds * (q * n0), fb1 = ds * (q * n1);
      ca0 += fa0; ca1 += fa1; cb0 += fb0; cb1 += fb1;
      const a0 = ca0 - fa0 + 0.5 * fa0, a1 = ca1 - fa1 + 0.5 * fa1;
      const b0 = cb0 - fb0 + 0.5 * fb0, b1 = cb1 - fb1 + 0.5 * fb1;
      const D00 = dT * t0 * t0 + dN * (n0 * n0), D01 = dT * t0 * t1 + dN * (n0 * n1);
      const D11 = dT * t1 * t1 + dN * (n1 * n1);
      const Da0 = D00 * a0 + D01 * a1, Da1 = D01 * a0 + D11 * a1;
      const Db0 = D00 * b0 + D01 * b1, Db1 = D01 * b0 + D11 * b1;
      A[0][0] += D00; A[0][1] += D01; A[1][0] += D01; A[1][1] += D11;
      A[0][2] += Da0; A[1][2] += Da1;
      A[2][2] += a0 * Da0 + a1 * Da1;
      rhs[0] -= Db0; rhs[1] -= Db1; rhs[2] -= a0 * Db0 + a1 * Db1;
    }
    A[2][0] = A[0][2]; A[2][1] = A[1][2];
    const s = solve3(A, rhs);
    return [[s[0], s[1]], s[2]];
  }
  step(muscle, dt) {
    const target = this.targetCurvature(muscle), nj = this.n - 1;
    const decay = Math.exp(-dt / this.b.tauMuscle);
    const newK = new Float64Array(nj), dk = new Float64Array(nj), midK = new Float64Array(nj);
    for (let j = 0; j < nj; j++) {
      newK[j] = target[j] + (this.kappa[j] - target[j]) * decay;
      dk[j] = (newK[j] - this.kappa[j]) / dt;
      midK[j] = 0.5 * (this.kappa[j] + newK[j]);
    }
    // midpoint rule, as in body.py
    let [v0, om] = this.velocities(this.head, this.theta0, this.kappa, dk);
    const midHead = [this.head[0] + 0.5 * dt * v0[0], this.head[1] + 0.5 * dt * v0[1]];
    [v0, om] = this.velocities(midHead, this.theta0 + 0.5 * dt * om, midK, dk);
    this.head = [this.head[0] + v0[0] * dt, this.head[1] + v0[1] * dt];
    this.theta0 += om * dt;
    this.kappa = newK;
  }
}

// One worm: brain + body + field, stepped exactly like env.run_episode.
export class Worm {
  constructor(model, field, { lesion = [], dt = 0.02 } = {}) {
    this.model = model; this.field = field; this.dt = dt;
    this.brain = new Brain(model, lesion);
    this.body = new Body(model.body);
  }
  reset(head, heading) {
    this.body.reset(head, heading);
    this.brain.reset();
    this.k = 0;
  }
  step() {
    const b = this.body, conc = this.field.conc(b.head[0], b.head[1]);
    const muscle = this.brain.step(conc, b.kappa, this.dt);
    b.step(muscle, this.dt);
    this.k += 1;
    return conc;
  }
}

function coo(c, mask) {
  const val = c.val.map((x, e) => x * mask(c.row[e], c.col[e]));
  return { row: c.row, col: c.col, val };
}

// out[col] = sum over entries of x[row] * val
function matvec(c, x, size) {
  const out = new Float64Array(size);
  for (let e = 0; e < c.val.length; e++) out[c.col[e]] += x[c.row[e]] * c.val[e];
  return out;
}

// 3x3 linear solve, Gaussian elimination with partial pivoting
function solve3(A0, b0) {
  const A = A0.map((r) => [...r]), b = [...b0];
  for (let k = 0; k < 3; k++) {
    let p = k;
    for (let i = k + 1; i < 3; i++) if (Math.abs(A[i][k]) > Math.abs(A[p][k])) p = i;
    [A[k], A[p]] = [A[p], A[k]]; [b[k], b[p]] = [b[p], b[k]];
    for (let i = k + 1; i < 3; i++) {
      const f = A[i][k] / A[k][k];
      for (let j = k; j < 3; j++) A[i][j] -= f * A[k][j];
      b[i] -= f * b[k];
    }
  }
  const x = [0, 0, 0];
  for (let i = 2; i >= 0; i--) {
    let s = b[i];
    for (let j = i + 1; j < 3; j++) s -= A[i][j] * x[j];
    x[i] = s / A[i][i];
  }
  return x;
}
