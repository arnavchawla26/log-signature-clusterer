"""log-signature-clusterer: turn a pile of log lines into the distinct
"signatures" that produced them, ranked by frequency.

A small, dependency-free, from-scratch take on the core idea behind the
Drain log-parsing algorithm (He et al., 2017): normalize volatile tokens
(numbers, timestamps, UUIDs, hex hashes, IPs) out of each line, then
incrementally cluster lines whose remaining tokens are similar enough
into a shared template.
"""

__version__ = "0.1.0"
