"""2D worm body crawling by resistive force theory (RFT).

The worm is a chain of ``n_segments`` rigid segments of equal length lying on its
side, so dorsal/ventral bending happens in the plane. Muscle activations set a
target curvature at each joint; the actual curvature relaxes towards it with time
constant ``tau_muscle``. The body is small and slow enough that inertia is
negligible, so at every instant the RFT drag on all segments must have zero net
force and zero net torque. Given the shape change, that is a 3x3 linear system
for the rigid-body velocity (head velocity and rotation rate), solved per worm.

RFT drag on a segment moving with velocity ``w`` (unit tangent ``t``, normal ``n``):
``f = -ds * (c_t (w.t) t + c_n (w.n) n)``. Only the ratio ``c_n / c_t`` affects
the motion, since the shape is prescribed; on agar it is large (the body slides
along its length far more easily than sideways).

Everything is batched over a leading axis of ``P`` worms. Units: mm and seconds.

Conventions
-----------
- Node 0 is the tip of the head; segment tangents point from head towards tail.
- The worm faces ``heading = theta_0 + pi`` (away from its own body).
- Positive curvature is a dorsal bend.
- Muscle activations are ``(P, 4, 24)``: quadrants in ``QUADRANTS`` order, rows 1..24
  from head to tail, values in [0, 1], the same layout as the connectome's muscles.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

QUADRANTS = ("DL", "DR", "VL", "VR")
MUSCLE_ROWS = 24


@dataclass(frozen=True)
class BodyParams:
    length: float = 1.0  # mm, adult hermaphrodite
    n_segments: int = 16
    drag_tangential: float = 1.0
    drag_normal: float = 20.0  # only the ratio to drag_tangential matters
    kappa_max: float = 8.0  # 1/mm, curvature at full one-sided activation
    tau_muscle: float = 0.1  # s, curvature relaxation time


@dataclass
class BodyState:
    head: np.ndarray  # (P, 2) position of node 0
    theta0: np.ndarray  # (P,) angle of segment 0's tangent
    kappa: np.ndarray  # (P, n_segments - 1) joint curvatures

    def copy(self) -> BodyState:
        return BodyState(self.head.copy(), self.theta0.copy(), self.kappa.copy())


class Body:
    def __init__(self, params: BodyParams | None = None):
        self.p = params or BodyParams()
        n = self.p.n_segments
        self.ds = self.p.length / n
        # joints sit between segments; muscle rows tile the body from head to tail
        joint_s = np.arange(1, n) * self.ds
        row_s = (np.arange(MUSCLE_ROWS) + 0.5) * self.p.length / MUSCLE_ROWS
        eye = np.eye(MUSCLE_ROWS)
        self.rows_to_joints = np.stack([np.interp(joint_s, row_s, e) for e in eye], axis=1)

    def reset(self, head, heading) -> BodyState:
        """Straight worm with its head at ``head`` facing ``heading`` (radians)."""
        head = np.atleast_2d(np.asarray(head, dtype=float))
        heading = np.atleast_1d(np.asarray(heading, dtype=float))
        kappa = np.zeros((len(heading), self.p.n_segments - 1))
        return BodyState(head.copy(), heading + np.pi, kappa)

    # --- geometry -------------------------------------------------------------

    def angles(self, s: BodyState) -> np.ndarray:
        """(P, n) segment angles."""
        cum = np.cumsum(s.kappa * self.ds, axis=1)
        return s.theta0[:, None] + np.concatenate([np.zeros((len(cum), 1)), cum], axis=1)

    def nodes(self, s: BodyState) -> np.ndarray:
        """(P, n + 1, 2) node positions, head first."""
        th = self.angles(s)
        steps = self.ds * np.stack([np.cos(th), np.sin(th)], axis=-1)
        return s.head[:, None, :] + np.concatenate(
            [np.zeros((len(th), 1, 2)), np.cumsum(steps, axis=1)], axis=1
        )

    def heading(self, s: BodyState) -> np.ndarray:
        return s.theta0 + np.pi

    def centroid(self, s: BodyState) -> np.ndarray:
        x = self.nodes(s)
        return 0.5 * (x[:, 1:] + x[:, :-1]).mean(axis=1)

    # --- dynamics -------------------------------------------------------------

    def target_curvature(self, muscle: np.ndarray) -> np.ndarray:
        """(P, 4, 24) activations -> (P, n - 1) target joint curvature."""
        muscle = np.clip(muscle, 0.0, 1.0)
        dorsal = 0.5 * (muscle[:, 0] + muscle[:, 1])
        ventral = 0.5 * (muscle[:, 2] + muscle[:, 3])
        return self.p.kappa_max * (dorsal - ventral) @ self.rows_to_joints.T

    def velocities(self, s: BodyState, dkappa: np.ndarray):
        """Rigid-body velocity making RFT force and torque vanish.

        Returns head velocity (P, 2), rotation rate (P,), segment-midpoint velocities
        (P, n, 2) and drag forces (P, n, 2).
        """
        p, ds = self.p, self.ds
        th = self.angles(s)
        t = np.stack([np.cos(th), np.sin(th)], axis=-1)
        nrm = np.stack([-np.sin(th), np.cos(th)], axis=-1)
        # shape part of each segment's angular velocity: q_i = sum_{k<i} dkappa_k ds
        q = np.concatenate([np.zeros((len(th), 1)), np.cumsum(dkappa * ds, axis=1)], axis=1)

        def to_mid(vecs):  # sum over earlier segments plus half of this one
            full = ds * vecs
            return np.cumsum(full, axis=1) - full + 0.5 * full

        a = to_mid(nrm)  # midpoint velocity per unit head rotation (perp of offset)
        b = to_mid(q[..., None] * nrm)  # midpoint velocity from the shape change
        D = p.drag_tangential * t[..., :, None] * t[..., None, :] + p.drag_normal * (
            nrm[..., :, None] * nrm[..., None, :]
        )  # (P, n, 2, 2)
        Da, Db = (D @ a[..., None])[..., 0], (D @ b[..., None])[..., 0]
        A = np.empty((len(th), 3, 3))
        A[:, :2, :2] = D.sum(axis=1)
        A[:, :2, 2] = Da.sum(axis=1)
        A[:, 2, :2] = A[:, :2, 2]
        A[:, 2, 2] = (a * Da).sum(axis=(1, 2))
        rhs = -np.concatenate([Db.sum(axis=1), (a * Db).sum(axis=(1, 2))[:, None]], axis=1)
        sol = np.linalg.solve(A, rhs[..., None])[..., 0]
        v0, omega = sol[:, :2], sol[:, 2]
        w = v0[:, None, :] + omega[:, None, None] * a + b
        force = -ds * (D @ w[..., None])[..., 0]
        return v0, omega, w, force

    def step(self, s: BodyState, muscle: np.ndarray, dt: float) -> np.ndarray:
        """Advance ``s`` in place by ``dt``; returns the power dissipated by drag (P,)."""
        target = self.target_curvature(muscle)
        new_kappa = target + (s.kappa - target) * np.exp(-dt / self.p.tau_muscle)
        dkappa = (new_kappa - s.kappa) / dt
        # midpoint rule: velocities evaluated half way through the step (second order)
        v0, omega, _, _ = self.velocities(s, dkappa)
        mid = BodyState(
            s.head + 0.5 * dt * v0, s.theta0 + 0.5 * dt * omega, 0.5 * (s.kappa + new_kappa)
        )
        v0, omega, w, force = self.velocities(mid, dkappa)
        s.head += v0 * dt
        s.theta0 += omega * dt
        s.kappa = new_kappa
        return -(force * w).sum(axis=(1, 2))
