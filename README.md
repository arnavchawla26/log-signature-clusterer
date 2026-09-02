# log-signature-clusterer

Turn 50,000 log lines into "these are the 12 distinct things that
actually happened, and how often." `logsig` reads a raw log file,
normalizes the volatile parts of each line (numbers, timestamps, UUIDs,
hex hashes, IP addresses), and incrementally clusters lines into
frequency-ranked "signatures" — a lightweight, dependency-free,
from-scratch take on the core idea behind the
[Drain](https://github.com/logpai/Drain3) log-parsing algorithm.

```
$ logsig app.log
5 signature(s) shown (of 5 discovered) across 15 line(s) (1 blank, skipped):

[1] count=4 (26.7%)
    signature: <TIMESTAMP> INFO Connection accepted from <IP>
    example:   2024-01-15T10:30:00Z INFO  Connection accepted from 192.168.1.5:54321

[2] count=3 (20.0%)
    signature: <TIMESTAMP> INFO User * logged in
    example:   2024-01-15T10:33:00Z INFO  User user42 logged in

[3] count=3 (20.0%)
    signature: <TIMESTAMP> WARN Retry attempt <NUM> for job <NUM>
    example:   2024-01-15T10:31:00Z WARN  Retry attempt 1 for job 4471
```

## Why

Real logs are mostly noise: the same handful of log statements firing
over and over with different timestamps, request IDs, and counters
baked in. Grepping or `sort | uniq -c` doesn't help because every line
looks unique once you count the volatile bits. `logsig` strips those
out first, so lines that came from the same `logger.info(...)` call
collapse into one entry — turning an unreadable firehose into a short,
ranked list of "what actually happened."

## How it works

1. **Normalize** (`logsig/normalize.py`) — a sequence of regexes runs
   over each raw line and replaces volatile substrings with stable
   placeholders, most-specific first so a generic pattern never eats a
   more specific one's digits: UUIDs → `<UUID>`, IPv4 addresses (with
   optional port) → `<IP>`, syslog-style `Mon DD HH:MM:SS` and full ISO
   8601 timestamps → `<TIMESTAMP>`, bare dates → `<DATE>`, bare times →
   `<TIME>`, hex strings of 6+ characters that contain at least one
   `a`-`f` letter → `<HEX>`, and any remaining integer or float →
   `<NUM>`. The regexes run against the whole line (not per
   whitespace-token), so a value embedded inside a larger string like
   `failed after 250ms` still normalizes correctly, to `failed after
   <NUM>ms`.
2. **Tokenize** (`logsig/tokenize.py`) — the normalized line is split
   on whitespace into a token sequence.
3. **Cluster** (`logsig/cluster.py`) — lines are bucketed by token
   count (a different length can never be the same signature), then
   compared position-by-position against each existing cluster's
   template in that bucket. The similarity score is the fraction of
   positions that already agree (an exact match, or the template
   already has a wildcard `*` there). A line joins the most similar
   cluster at or above `--similarity` (default `0.5`), widening any
   disagreeing position to `*`; otherwise it starts a new cluster. This
   is a single pass over the input, so it's linear in the number of
   lines times the number of clusters already found for that line
   length — plenty fast for the log volumes a CLI tool like this is
   meant to handle.
4. **Report** (`logsig/report.py`) — clusters are ranked by frequency
   (most common first, ties broken by first-discovered order) and
   rendered as text, Markdown, or JSON.

## Install

```
pip install -e .
```

Requires Python 3.9+ and has zero third-party runtime dependencies
(the whole tool is standard-library `re`, `argparse`, and `json`).

## Usage

```
logsig [logfile] [--format text|markdown|json] [--similarity 0..1] [--top N] [--min-count N]
```

- `logfile` — path to a log file, or omit it (or pass `-`) to read
  stdin.
- `--format` — `text` (default), `markdown`, or `json`.
- `--similarity` — minimum fraction of matching tokens (0 to 1) for a
  line to join an existing cluster instead of starting a new one.
  Lower values merge more aggressively; higher values keep signatures
  stricter. Default `0.5`.
- `--top N` — only show the N most frequent signatures.
- `--min-count N` — only show signatures that matched at least N
  lines.

Example: pipe a live tail through it, keep only signatures that show
up 5+ times, and get JSON for downstream tooling:

```
tail -n 5000 app.log | logsig --min-count 5 --format json
```

## Tests

```
pip install -e ".[dev]"
pytest
```

43 tests across normalization, tokenization, clustering, and
CLI/end-to-end tests, including a subprocess-level `python -m logsig`
check and a seeded fixture log
(`tests/fixtures/sample.log`) whose exact clustering result the CLI
tests assert against.

## Current status

Functional v1. Handles the common cases (numbers, ISO/syslog
timestamps, UUIDs, hex hashes, IPv4) and ships with a real test suite.
Known limitations, honestly stated:

- **Regex-based normalization, not a real log-format grammar.** A
  digit run glued to a non-hex letter (`3rd`, `v2.1`) normalizes
  partially rather than as a clean unit — this is an inherent
  trade-off of regex substitution over a line, same as Drain's own
  preprocessing step. Numbers embedded inside a larger identifier that
  isn't separated by a boundary character (e.g. the `42` inside
  `user42`) are left untouched; the clustering step still wildcards
  that position across enough examples, so results stay correct even
  when normalization doesn't fire — see `tests/test_cluster.py` for a
  worked example of exactly this case.
- **No IPv6 support.** Only IPv4 dotted-quad addresses are recognized.
- **Single-pass, position-aligned similarity**, not the fixed-depth
  prefix tree the original Drain paper uses. This keeps the
  implementation small and dependency-free, but means two lines with
  extra/missing leading tokens (rather than substituted ones) always
  land in different buckets, since bucketing is purely by token count.
- **No streaming/incremental-file mode.** The whole input is read into
  memory before clustering; fine for typical log-review sizes, not
  meant for continuously tailing a multi-GB file forever.

## Tech stack

Python 3.9+, standard library only (`re`, `argparse`, `json`,
`dataclasses`). Tests use `pytest`.
