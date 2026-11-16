"""Notebook-only diagrams and measured charts, with a consistent visual language."""

import textwrap
from typing import Literal

MeasurementKind = Literal[
    "heuristic estimate", "fixture measurement", "live measurement", "illustrative"
]


def diagram(
    title: str,
    labels: list[str],
    edges: list[tuple[int, int]],
    *,
    columns=3,
    caption="Arrows show permitted transitions or data flow.",
):
    """Render directly with Matplotlib; no Mermaid extension or network renderer."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    rows = (len(labels) + columns - 1) // columns
    fig, ax = plt.subplots(figsize=(11, 1.9 * rows + 1.1), dpi=120)
    fig.patch.set_facecolor("#f5f8fc")
    ax.set_facecolor("#f5f8fc")
    ax.set_xlim(-0.7, columns * 3 - 0.3)
    has_top_branch = any(a // columns == b // columns == 0 and abs(a - b) > 1 for a, b in edges)
    ax.set_ylim(-1.1, rows * 1.8 + (0.8 if has_top_branch else 0))
    ax.axis("off")
    positions = {
        i: ((i % columns) * 3 + 0.85, (rows - 1 - i // columns) * 1.8 + 0.6)
        for i in range(len(labels))
    }
    for start, end in edges:
        x1, y1 = positions[start]
        x2, y2 = positions[end]
        dx, dy = x2 - x1, y2 - y1
        boundary = min(
            1.30 / abs(dx) if dx else float("inf"), 0.62 / abs(dy) if dy else float("inf")
        )
        source = (x1 + boundary * dx, y1 + boundary * dy)
        target = (x2 - boundary * dx, y2 - boundary * dy)
        curvature = 0.08 if start > end else 0
        if dy == 0 and abs(dx) > 3:
            # Route a long branch around intervening boxes rather than through them.
            above = y1 > 1
            offset = 0.64 if above else -0.64
            source, target = (x1, y1 + offset), (x2, y2 + offset)
            curvature = (-0.15 if dx > 0 else 0.15) * (1 if above else -1)
        arrow = FancyArrowPatch(
            source,
            target,
            arrowstyle="-|>",
            mutation_scale=16,
            color="#64748b",
            linewidth=1.6,
            shrinkA=0,
            shrinkB=0,
            connectionstyle=f"arc3,rad={curvature}",
        )
        ax.add_patch(arrow)
    for index, label in enumerate(labels):
        x, y = positions[index]
        color = ["#15324f", "#076f70", "#8a4e14"][index % 3]
        box = FancyBboxPatch(
            (x - 1.15, y - 0.48),
            2.3,
            0.96,
            boxstyle="round,pad=0.08,rounding_size=0.12",
            facecolor=color,
            edgecolor="white",
            linewidth=2,
            zorder=3,
        )
        ax.add_patch(box)
        ax.text(
            x,
            y,
            textwrap.fill(label, 22),
            ha="center",
            va="center",
            color="white",
            fontsize=10,
            fontweight="normal",
            zorder=4,
        )
    ax.set_title(title, loc="left", fontsize=16, color="#15324f", pad=18, weight="bold")
    fig.text(0.05, 0.025, caption, fontsize=9, color="#475569", wrap=True)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    return fig


def bars(title: str, values: dict[str, float], *, ylabel: str, measurement_kind: MeasurementKind):
    import matplotlib.pyplot as plt

    if measurement_kind not in {
        "heuristic estimate",
        "fixture measurement",
        "live measurement",
        "illustrative",
    }:
        raise ValueError("Unknown measurement kind")
    fig, ax = plt.subplots(figsize=(9, 3.5), dpi=120)
    ax.bar(list(values), list(values.values()), color="#076f70", width=0.6)
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title} — {measurement_kind}", loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


def tool_sequence(participants: list[str], events: list[tuple[int, int, str]]):
    """Align correlated requests and observations with participant lifelines."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, max(3, len(events) * 0.7 + 1.5)), dpi=120)
    for index, participant in enumerate(participants):
        ax.axvline(index, linestyle="--", color="#94a3b8", linewidth=1)
        ax.text(index, 0, participant, ha="center", va="bottom")
    for index, (source, destination, label) in enumerate(events, 1):
        ax.annotate(
            "",
            xy=(destination, -index),
            xytext=(source, -index),
            arrowprops={"arrowstyle": "->", "color": "#076f70"},
        )
        ax.text((source + destination) / 2, -index + 0.12, label, ha="center", fontsize=9)
    ax.set_ylim(-len(events) - 0.5, 0.8)
    ax.set_xlim(-0.5, len(participants) - 0.5)
    ax.axis("off")
    ax.set_title("Tool requests and observations", loc="left", pad=20)
    fig.tight_layout()
    return fig


def dependencies(tasks: dict[str, set[str]]):
    """Lay out dependency layers with prerequisite-to-dependent arrows."""
    import matplotlib.pyplot as plt

    remaining = dict(tasks)
    positions = {}
    layer = 0
    while remaining:
        ready = sorted(key for key, parents in remaining.items() if parents <= positions.keys())
        if not ready:
            raise ValueError("Unknown dependency or dependency cycle")
        for row, key in enumerate(ready):
            positions[key] = (layer, -row)
            del remaining[key]
        layer += 1
    fig, ax = plt.subplots(figsize=(10, 4), dpi=120)
    for key, parents in tasks.items():
        for parent in parents:
            ax.annotate(
                "",
                xy=positions[key],
                xytext=positions[parent],
                arrowprops={"arrowstyle": "->", "shrinkA": 35, "shrinkB": 35},
            )
        x, y = positions[key]
        ax.text(
            x,
            y,
            key,
            ha="center",
            va="center",
            bbox={"boxstyle": "round,pad=0.6", "fc": "#dbeafe"},
        )
    ax.set_xlim(-0.5, max(1, layer) - 0.5)
    ax.set_ylim(min(y for x, y in positions.values()) - 0.7, 0.7)
    ax.axis("off")
    ax.set_title("Research task dependencies", loc="left")
    fig.tight_layout()
    return fig


def confusion_matrix(counts: dict[str, dict[str, int]]):
    import matplotlib.pyplot as plt

    labels = sorted(counts)
    values = [[counts[actual][predicted] for predicted in labels] for actual in labels]
    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    ax.imshow(values, cmap="Blues")
    for row in range(len(labels)):
        for column in range(len(labels)):
            ax.text(column, row, str(values[row][column]), ha="center", va="center")
    ax.set_xticks(range(len(labels)), labels, rotation=25)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Live judge prediction")
    ax.set_ylabel("Draft reference annotation")
    ax.set_title("Judge disagreement - live measurement", loc="left")
    fig.tight_layout()
    return fig
