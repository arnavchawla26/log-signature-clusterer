"""Render a clustering result as text, Markdown, or JSON."""

from __future__ import annotations

import json

from .cluster import Cluster, ClusterEngine


def _rows(
    engine: ClusterEngine, top: int | None, min_count: int | None
) -> list[Cluster]:
    clusters = engine.clusters()
    if min_count is not None:
        clusters = [c for c in clusters if c.count >= min_count]
    if top is not None:
        clusters = clusters[:top]
    return clusters


def _percentage(count: int, total: int) -> float:
    return (count / total * 100.0) if total else 0.0


def render_text(
    engine: ClusterEngine, *, top: int | None = None, min_count: int | None = None
) -> str:
    total = engine.total_lines
    clusters = _rows(engine, top, min_count)
    lines = [
        f"{len(clusters)} signature(s) shown "
        f"(of {len(engine.clusters())} discovered) across {total} line(s)"
        + (
            f" ({engine.blank_lines} blank, skipped)"
            if engine.blank_lines
            else ""
        )
        + ":",
        "",
    ]
    for rank, cluster in enumerate(clusters, start=1):
        pct = _percentage(cluster.count, total)
        lines.append(f"[{rank}] count={cluster.count} ({pct:.1f}%)")
        lines.append(f"    signature: {cluster.signature()}")
        lines.append(f"    example:   {cluster.example}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_markdown(
    engine: ClusterEngine, *, top: int | None = None, min_count: int | None = None
) -> str:
    total = engine.total_lines
    clusters = _rows(engine, top, min_count)
    lines = [
        f"# Log signatures ({len(clusters)} shown of "
        f"{len(engine.clusters())} discovered, {total} lines)",
        "",
        "| Rank | Count | % | Signature | Example |",
        "|---:|---:|---:|---|---|",
    ]
    for rank, cluster in enumerate(clusters, start=1):
        pct = _percentage(cluster.count, total)
        sig = cluster.signature().replace("|", "\\|")
        example = cluster.example.replace("|", "\\|")
        lines.append(f"| {rank} | {cluster.count} | {pct:.1f}% | `{sig}` | `{example}` |")
    return "\n".join(lines) + "\n"


def render_json(
    engine: ClusterEngine, *, top: int | None = None, min_count: int | None = None
) -> str:
    total = engine.total_lines
    clusters = _rows(engine, top, min_count)
    payload = {
        "total_lines": total,
        "blank_lines": engine.blank_lines,
        "total_clusters": len(engine.clusters()),
        "shown_clusters": len(clusters),
        "clusters": [
            {
                "rank": rank,
                "count": cluster.count,
                "percentage": round(_percentage(cluster.count, total), 4),
                "signature": cluster.signature(),
                "example": cluster.example,
                "first_line_no": cluster.first_line_no,
            }
            for rank, cluster in enumerate(clusters, start=1)
        ],
    }
    return json.dumps(payload, indent=2) + "\n"


RENDERERS = {
    "text": render_text,
    "markdown": render_markdown,
    "json": render_json,
}
