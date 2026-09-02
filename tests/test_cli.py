import json
import subprocess
import sys
from pathlib import Path

from logsig.cli import run

FIXTURE = Path(__file__).parent / "fixtures" / "sample.log"


def test_run_text_format_against_fixture(capsys):
    exit_code = run([str(FIXTURE)])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "signature(s) shown" in out
    # The three "Connection accepted from <IP>" lines should be one
    # cluster with count 4 (three initial + one after the blank line).
    assert "count=4" in out


def test_run_json_format_is_valid_and_ranked(capsys):
    exit_code = run([str(FIXTURE), "--format", "json"])
    out = capsys.readouterr().out
    assert exit_code == 0
    payload = json.loads(out)
    assert payload["total_lines"] == 15
    assert payload["blank_lines"] == 1
    counts = [c["count"] for c in payload["clusters"]]
    assert counts == sorted(counts, reverse=True)
    top = payload["clusters"][0]
    assert top["count"] == 4
    assert "<IP>" in top["signature"]


def test_run_markdown_format(capsys):
    exit_code = run([str(FIXTURE), "--format", "markdown"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert out.startswith("# Log signatures")
    assert "| Rank | Count | % | Signature | Example |" in out


def test_run_top_limits_output(capsys):
    exit_code = run([str(FIXTURE), "--format", "json", "--top", "2"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["shown_clusters"] == 2
    assert len(payload["clusters"]) == 2


def test_run_min_count_filters_output(capsys):
    exit_code = run([str(FIXTURE), "--format", "json", "--min-count", "3"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert all(c["count"] >= 3 for c in payload["clusters"])


def test_run_missing_file_returns_error(capsys):
    exit_code = run(["/no/such/file.log"])
    err = capsys.readouterr().err
    assert exit_code == 2
    assert "cannot read" in err


def test_run_invalid_similarity_returns_error(capsys):
    exit_code = run([str(FIXTURE), "--similarity", "2.0"])
    err = capsys.readouterr().err
    assert exit_code == 2
    assert "similarity_threshold" in err


def test_run_reads_stdin_when_dash(capsys, monkeypatch):
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO("a b c\na b d\n"))
    exit_code = run(["-", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["total_lines"] == 2
    assert payload["total_clusters"] == 1


def test_console_script_end_to_end():
    result = subprocess.run(
        [sys.executable, "-m", "logsig", str(FIXTURE)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "signature(s) shown" in result.stdout
