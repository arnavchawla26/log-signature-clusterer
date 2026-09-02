from logsig.normalize import normalize_line


def test_uuid_replaced():
    line = "request req-550e8400-e29b-41d4-a716-446655440000 failed"
    assert normalize_line(line) == "request req-<UUID> failed"


def test_ipv4_replaced():
    assert (
        normalize_line("Connection accepted from 192.168.1.5:54321")
        == "Connection accepted from <IP>"
    )


def test_ipv4_without_port():
    assert normalize_line("client 10.0.0.2 connected") == "client <IP> connected"


def test_iso_timestamp_with_z_replaced():
    line = "2024-01-15T10:30:00Z INFO started"
    assert normalize_line(line) == "<TIMESTAMP> INFO started"


def test_iso_timestamp_with_millis_and_offset():
    line = "2024-01-15T10:30:00.123+05:30 INFO started"
    assert normalize_line(line) == "<TIMESTAMP> INFO started"


def test_iso_timestamp_space_separated():
    line = "2024-01-15 10:30:00 INFO started"
    assert normalize_line(line) == "<TIMESTAMP> INFO started"


def test_bare_date_replaced():
    assert normalize_line("archived on 2024-01-15") == "archived on <DATE>"


def test_bare_time_replaced():
    assert normalize_line("elapsed 10:30:00 total") == "elapsed <TIME> total"


def test_syslog_style_timestamp():
    line = "Jan 15 10:30:00 host sshd[123]: accepted"
    normalized = normalize_line(line)
    assert normalized.startswith("<TIMESTAMP> host sshd[")


def test_hex_hash_replaced():
    assert normalize_line("cache hit for key abc123def456") == (
        "cache hit for key <HEX>"
    )


def test_pure_decimal_run_is_number_not_hex():
    # No a-f letters present, so this is a number, not a hex hash.
    assert normalize_line("retry count 123456") == "retry count <NUM>"


def test_number_replaced():
    assert normalize_line("Retry attempt 1 for job 4471") == (
        "Retry attempt <NUM> for job <NUM>"
    )


def test_number_glued_to_unit_suffix():
    # A digit run immediately followed by a letter (no separating
    # whitespace/punctuation) must still be recognized as a number.
    assert normalize_line("failed after 250ms") == "failed after <NUM>ms"


def test_float_replaced():
    assert normalize_line("load average 2.5 over 1m") == (
        "load average <NUM> over <NUM>m"
    )


def test_mixed_line():
    line = (
        "2024-01-15T10:32:00Z ERROR Request "
        "req-550e8400-e29b-41d4-a716-446655440000 from 10.0.0.2 "
        "failed after 250ms"
    )
    assert normalize_line(line) == (
        "<TIMESTAMP> ERROR Request req-<UUID> from <IP> failed after <NUM>ms"
    )


def test_no_volatile_tokens_unchanged():
    line = "Service starting up"
    assert normalize_line(line) == line
