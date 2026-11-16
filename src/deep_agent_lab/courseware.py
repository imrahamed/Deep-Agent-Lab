"""Notebook-only diagrams and measured charts, with a consistent visual language."""

import textwrap


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


def bars(title: str, values: dict[str, float], *, ylabel: str, measured=True):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 3.5), dpi=120)
    ax.bar(list(values), list(values.values()), color="#076f70", width=0.6)
    ax.set_ylabel(ylabel)
    ax.set_title(title + (" — measured in this run" if measured else " — illustrative"), loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig
