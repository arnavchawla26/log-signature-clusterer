from logsig.tokenize import tokenize


def test_tokenize_splits_on_whitespace_after_normalization():
    line = "2024-01-15T10:30:00Z INFO  Connection accepted from 192.168.1.5:54321"
    assert tokenize(line) == ["<TIMESTAMP>", "INFO", "Connection", "accepted", "from", "<IP>"]


def test_tokenize_strips_trailing_newline():
    assert tokenize("hello world\n") == ["hello", "world"]


def test_tokenize_blank_line_is_empty():
    assert tokenize("") == []
    assert tokenize("   \n") == []


def test_tokenize_collapses_repeated_whitespace():
    assert tokenize("a    b\tc") == ["a", "b", "c"]
