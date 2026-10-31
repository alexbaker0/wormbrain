# ruff: noqa: E501  (long matplotlib call lines)
"""Pictures of the wiring: the whole connectome, and the salt-steering circuit.

    uv run python scripts/connectome_figure.py

Panel A: all 282 non-pharyngeal neurons in three columns (sensory, inter, motor),
ordered so that connected neurons sit near each other; every chemical synapse and gap
junction drawn faintly. Panel B: the circuit from the salt sensors (ASE) to the
motor neurons at the level of neuron classes, with synapse counts.

Edges are coloured by the presynaptic neuron's transmitter (Wang et al. 2024):
acetylcholine (excitatory), GABA (inhibitory), glutamate (excitatory or inhibitory
depending on the receptor; the model's sign for it is an assumption) and other.
Writes reports/connectome/connectome.png.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402

from wormbrain.connectome import build_connectome, load_config, sign_rules  # noqa: E402
from wormbrain.layout import CIRCUIT, whole_layout  # noqa: E402

OUT = Path("reports/connectome")
COLOURS = {"Acetylcholine": "#d1495b", "GABA": "#2e86de", "Glutamate": "#8e44ad",
           "other": "#8a8f98"}  # fmt: skip
GAP = "#2a9d8f"


def transmitter(rule: str) -> str:
    for t in ("Acetylcholine", "GABA", "Glutamate"):
        if rule.startswith(t):
            return t
    return "other"


def panel_whole(ax, conn, tx):
    n = conn.n
    x, y = whole_layout(conn)

    def curves(pairs, bulge):
        segs = []
        for i, j in pairs:
            p0, p1 = np.array([x[i], y[i]]), np.array([x[j], y[j]])
            mid = (p0 + p1) / 2 + np.array([bulge * (0.15 + 0.4 * abs(y[i] - y[j])), 0]) * (
                x[i] == x[j]
            )
            t = np.linspace(0, 1, 12)[:, None]
            segs.append((1 - t) ** 2 * p0 + 2 * (1 - t) * t * mid + t**2 * p1)
        return segs

    src, dst = np.nonzero(conn.chem)
    for t, colour in COLOURS.items():
        sel = [(i, j) for i, j in zip(src, dst, strict=True) if tx[i] == t]
        ax.add_collection(LineCollection(curves(sel, 1), colors=colour, linewidths=0.4,
                                         alpha=0.10))  # fmt: skip
    gi, gj = np.nonzero(np.triu(conn.gap, 1))
    ax.add_collection(LineCollection(curves(zip(gi, gj, strict=True), -1), colors=GAP,
                                     linewidths=0.4, alpha=0.12, linestyles="--"))  # fmt: skip
    degree = (conn.chem > 0).sum(0) + (conn.chem > 0).sum(1) + (conn.gap > 0).sum(1)
    ax.scatter(x, y, s=4 + degree * 0.6, c=[COLOURS[t] for t in tx], zorder=3,
               edgecolors="white", linewidths=0.4)  # fmt: skip
    # label the most connected classes once each, at their members' mean height
    by_class: dict[str, list[int]] = {}
    for i, c in enumerate(conn.cell_class):
        by_class.setdefault(c, []).append(i)
    top = sorted(by_class, key=lambda c: -degree[by_class[c]].sum())[:22]
    labels = [(x[by_class[c][0]], float(np.mean(y[by_class[c]])), c)
              for c in dict.fromkeys(top + ["ASE", "AIY", "AIZ"])]  # fmt: skip
    for column in (0.0, 1.0, 2.0):  # spread labels in each column at least 0.022 apart
        col_labels = sorted(lab for lab in labels if lab[0] == column)
        last = -1.0
        for lx, ly, c in sorted(col_labels, key=lambda lab: lab[1]):
            ly = max(ly, last + 0.022)
            last = ly
            side = -1 if lx == 0 else 1
            ax.text(lx + side * 0.06, ly, c, fontsize=7, ha="right" if side < 0 else "left",
                    va="center", zorder=4)  # fmt: skip
    for c, label in [(0, "sensory (83)"), (1, "interneurons (81 + 2 other)"), (2, "motor (116)")]:
        ax.text(c, 1.04, label, ha="center", fontsize=10, fontweight="bold")
    ax.set_xlim(-0.45, 2.45)
    ax.set_ylim(-0.03, 1.08)
    ax.axis("off")
    ax.set_title(f"A. The whole connectome: {n} neurons, {int((conn.chem > 0).sum())} chemical "
                 f"synapse connections, {int(np.triu(conn.gap > 0, 1).sum())} gap junctions",
                 fontsize=11, loc="left")  # fmt: skip


def panel_circuit(ax, conn, tx):
    members = {c: [i for i, k in enumerate(conn.cell_class) if k == c] for c, _, _ in CIRCUIT}
    pos = {c: (col * 1.0, -row) for c, col, row in CIRCUIT}
    names = [c for c, _, _ in CIRCUIT]
    motor = {c for c, col, _ in CIRCUIT if col == 3}
    for a in names:
        for b in names:
            if a == b or (a in motor and b in motor):  # motor-to-motor left out for clarity
                continue
            w = conn.chem[np.ix_(members[a], members[b])].sum()
            if w >= 8:
                t = tx[members[a][0]]
                rad = 0.15 if pos[a][0] == pos[b][0] else 0.08
                ax.add_patch(FancyArrowPatch(pos[a], pos[b], connectionstyle=f"arc3,rad={rad}",
                                             arrowstyle="-|>", mutation_scale=9, color=COLOURS[t],
                                             lw=0.4 + w / 22, alpha=0.75, shrinkA=13,
                                             shrinkB=13))  # fmt: skip
    for k, a in enumerate(names):
        for b in names[k + 1 :]:
            g = conn.gap[np.ix_(members[a], members[b])].sum()
            if g >= 8 and not (a in motor and b in motor):
                ax.add_patch(FancyArrowPatch(pos[a], pos[b], connectionstyle="arc3,rad=-0.2",
                                             arrowstyle="-", color=GAP, lw=0.4 + g / 22,
                                             ls="--", alpha=0.8, shrinkA=13,
                                             shrinkB=13))  # fmt: skip
    for c in names:
        t = tx[members[c][0]]
        ax.scatter(*pos[c], s=620, color="white", edgecolors=COLOURS[t], linewidths=2.2, zorder=3)
        ax.text(*pos[c], c, ha="center", va="center", fontsize=8, fontweight="bold", zorder=4)
        ax.text(pos[c][0], pos[c][1] - 0.42, f"{len(members[c])}", ha="center", fontsize=6,
                color="#666", zorder=4)  # fmt: skip
    for x, label in [(0, "salt\nsensor"), (1, "first\ninterneurons"), (2, "command and\nhead interneurons"),
                     (3, "motor neurons\n(head, then body)")]:  # fmt: skip
        ax.text(x, 1.6, label, ha="center", fontsize=9, fontweight="bold")
    ax.set_xlim(-0.5, 3.6)
    ax.set_ylim(-11, 2.4)
    ax.axis("off")
    ax.set_title("B. From the salt sensors to the muscles (neuron classes; arrows = chemical "
                 "synapses, ≥ 8;\nline width = number of synapses; small number = neurons in "
                 "the class; motor-to-motor links not shown)", fontsize=11, loc="left")  # fmt: skip


def main():
    conn = build_connectome(load_config("configs/connectome.yaml"))
    rules = sign_rules()
    tx = [transmitter(rules[nm]) for nm in conn.neurons]
    fig, axes = plt.subplots(1, 2, figsize=(20, 11), gridspec_kw={"width_ratios": [1.15, 1]})
    panel_whole(axes[0], conn, tx)
    panel_circuit(axes[1], conn, tx)
    handles = [Line2D([], [], color=COLOURS["Acetylcholine"], lw=2, label="acetylcholine (excitatory)"),
               Line2D([], [], color=COLOURS["GABA"], lw=2, label="GABA (inhibitory)"),
               Line2D([], [], color=COLOURS["Glutamate"], lw=2,
                      label="glutamate (excitatory or inhibitory; sign assumed in the model)"),
               Line2D([], [], color=COLOURS["other"], lw=2, label="other / unidentified transmitter"),
               Line2D([], [], color=GAP, lw=2, ls="--", label="gap junction (electrical, two-way)")]  # fmt: skip
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, fontsize=10)
    fig.suptitle("The C. elegans hermaphrodite connectome used as the worm's brain "
                 "(Cook et al. 2019; transmitters from Wang et al. 2024)", fontsize=14,
                 fontweight="bold")  # fmt: skip
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "connectome.png", dpi=130)
    print(f"wrote {OUT / 'connectome.png'}")


if __name__ == "__main__":
    main()
