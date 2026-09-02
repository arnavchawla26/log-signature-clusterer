"""Incremental, similarity-based log line clustering.

The approach is a deliberately small subset of the Drain log-parsing
algorithm's core idea:

1. Bucket candidate templates by token count -- two lines that tokenize
   to a different number of tokens can never belong to the same
   signature.
2. Within a bucket, compare a new line's tokens position-by-position
   against each existing cluster's template. The similarity score is
   the fraction of positions that already agree (either an exact token
   match, or the template already has a wildcard there).
3. The new line joins the most similar cluster whose similarity is at
   or above ``similarity_threshold``; any position where the new line
   disagrees with the template gets widened to a wildcard (``*``). If
   no cluster qualifies, the line starts a new cluster of its own.

This is a single pass over the input (O(lines x clusters-per-bucket)),
which is more than fast enough for the log volumes a portfolio tool
like this is meant to handle, and it avoids pulling in a dependency for
the fixed-depth prefix tree the real Drain paper uses.
"""

from __future__ import annotations

from dataclasses import dataclass

WILDCARD = "*"


@dataclass
class Cluster:
    """One discovered log signature."""

    template: list[str]
    count: int = 0
    example: str = ""
    first_line_no: int = 0

    def signature(self) -> str:
        return " ".join(self.template)


def _similarity(template: list[str], tokens: list[str]) -> float:
    """Fraction of positions where ``tokens`` already agrees with
    ``template`` (an exact match, or the template is already a
    wildcard there)."""
    if not template:
        return 1.0
    matches = sum(
        1
        for t, tok in zip(template, tokens)
        if t == WILDCARD or t == tok
    )
    return matches / len(template)


class ClusterEngine:
    """Accumulates lines and groups them into :class:`Cluster` objects."""

    def __init__(self, similarity_threshold: float = 0.5) -> None:
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0 and 1")
        self.similarity_threshold = similarity_threshold
        # Bucketed by token count, preserving insertion order within a
        # bucket so ties in similarity favor the earliest-seen cluster.
        self._buckets: dict[int, list[Cluster]] = {}
        self.total_lines = 0
        self.blank_lines = 0

    def add_line(self, raw_line: str, tokens: list[str], line_no: int) -> Cluster:
        """Assign one already-tokenized line to a cluster, creating a
        new cluster if nothing matches closely enough."""
        self.total_lines += 1
        if not tokens:
            self.blank_lines += 1
            return self._blank_cluster(raw_line, line_no)

        bucket = self._buckets.setdefault(len(tokens), [])

        best: Cluster | None = None
        best_score = -1.0
        for cluster in bucket:
            score = _similarity(cluster.template, tokens)
            if score >= self.similarity_threshold and score > best_score:
                best = cluster
                best_score = score

        if best is None:
            cluster = Cluster(
                template=list(tokens),
                count=1,
                example=raw_line,
                first_line_no=line_no,
            )
            bucket.append(cluster)
            return cluster

        # Widen any disagreeing position to a wildcard.
        for i, (t, tok) in enumerate(zip(best.template, tokens)):
            if t != WILDCARD and t != tok:
                best.template[i] = WILDCARD
        best.count += 1
        return best

    def _blank_cluster(self, raw_line: str, line_no: int) -> Cluster:
        bucket = self._buckets.setdefault(0, [])
        if not bucket:
            bucket.append(Cluster(template=[], count=0, example=raw_line, first_line_no=line_no))
        cluster = bucket[0]
        cluster.count += 1
        return cluster

    def clusters(self, *, include_blank: bool = False) -> list[Cluster]:
        """All discovered clusters, ranked by frequency (most common
        first). Ties keep first-discovered order."""
        result: list[Cluster] = []
        for size, bucket in self._buckets.items():
            if size == 0 and not include_blank:
                continue
            result.extend(bucket)
        result.sort(key=lambda c: c.count, reverse=True)
        return result


def cluster_lines(
    lines: list[str], similarity_threshold: float = 0.5
) -> ClusterEngine:
    """Convenience wrapper: tokenize and cluster a list of raw lines."""
    from .tokenize import tokenize

    engine = ClusterEngine(similarity_threshold=similarity_threshold)
    for i, line in enumerate(lines, start=1):
        engine.add_line(line, tokenize(line), i)
    return engine
