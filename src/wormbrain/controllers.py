"""Controllers turn observations into muscle activations (P, 4, 24).

Every controller has ``reset(n_worms)`` and ``step(obs, dt) -> muscle``; ``obs`` is
a dict with ``t`` (s), ``conc`` (P,) concentration at the head tip and ``kappa``
(P, joints) body curvature. The connectome brain (milestone 4) uses the same API.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .body import MUSCLE_ROWS


@dataclass
class TravelingWave:
    """Hand-coded oscillator: a bending wave travelling along the body.

    ``direction=+1`` sends the wave from head to tail, which drives the worm forward;
    ``-1`` drives it backward. ``bias`` > 0 adds a constant dorsal bend (steady
    turn), < 0 a ventral one.
    """

    frequency: float = 0.4  # Hz
    wavelength: float = 0.65  # body lengths
    amplitude: float = 1.0  # fraction of full activation contrast
    bias: float = 0.0
    direction: int = 1

    def reset(self, n_worms: int) -> None:
        self.n = n_worms

    def step(self, obs: dict, dt: float) -> np.ndarray:
        s = (np.arange(MUSCLE_ROWS) + 0.5) / MUSCLE_ROWS
        phase = 2 * np.pi * (self.frequency * obs["t"] - self.direction * s / self.wavelength)
        bend = self.amplitude * np.sin(phase) + self.bias  # dorsal minus ventral
        dorsal = np.clip(0.5 + 0.5 * bend, 0, 1)
        ventral = np.clip(0.5 - 0.5 * bend, 0, 1)
        rows = np.stack([dorsal, dorsal, ventral, ventral])  # DL, DR, VL, VR
        return np.broadcast_to(rows, (self.n, 4, MUSCLE_ROWS)).copy()


@dataclass
class GradientSteering:
    """Hand-coded chemotaxis baseline: crawl forward, turn while things get worse.

    Compares the concentration now with a running average over ``tau`` seconds
    (adaptation, as in the ASE neurons) and adds a steady turning bias while the
    concentration is falling (klinokinesis). Not biologically detailed; it checks
    that the arena and reward reward the right thing, and gives a reference score.
    """

    turn_bias: float = 0.4
    tau: float = 3.0  # s
    wave: TravelingWave | None = None

    def reset(self, n_worms: int) -> None:
        self.wave = self.wave or TravelingWave()
        self.wave.reset(n_worms)
        self.avg = None

    def step(self, obs: dict, dt: float) -> np.ndarray:
        c = obs["conc"]
        self.avg = c.copy() if self.avg is None else self.avg + (c - self.avg) * dt / self.tau
        muscle = self.wave.step(obs, dt)
        turn = np.where(c < self.avg, self.turn_bias, 0.0)
        shift = 0.5 * turn[:, None, None]
        muscle[:, :2] = np.clip(muscle[:, :2] + shift, 0, 1)
        muscle[:, 2:] = np.clip(muscle[:, 2:] - shift, 0, 1)
        return muscle


@dataclass
class Forager:
    """Hand-coded forager for patch worlds: crawl, turn while the smell weakens, and stop
    (muscles relaxed) to eat while the smell is strong, i.e. on a patch. Once the patch
    is eaten its smell fades and the worm moves on. A reference, not a model of biology.
    """

    turn_bias: float = 0.4
    tau: float = 3.0
    stop_conc: float = 0.85  # about 1 mm from a 1.5 mm-wide patch centre: inside eating range

    def reset(self, n_worms: int) -> None:
        self.steer = GradientSteering(turn_bias=self.turn_bias, tau=self.tau)
        self.steer.reset(n_worms)

    def step(self, obs: dict, dt: float) -> np.ndarray:
        muscle = self.steer.step(obs, dt)
        muscle[obs["conc"] > self.stop_conc] = 0.5  # dorsal = ventral: no bending, no motion
        return muscle
