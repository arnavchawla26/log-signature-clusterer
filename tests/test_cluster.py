import pytest

from logsig.cluster import Cluster, ClusterEngine, cluster_lines
from logsig.tokenize import tokenize


def _add(engine: ClusterEngine, line: str, line_no: int = 1) -> Cluster:
    return engine.add_line(line, tokenize(line), line_no)


def test_identical_lines_form_one_cluster():
    engine = ClusterEngine()
    _add(engine, "User user42 logged in", 1)
    _add(engine, "User user42 logged in", 2)
    clusters = engine.clusters()
    assert len(clusters) == 1
    assert clusters[0].count == 2


def test_lines_differing_only_by_number_merge_and_wildcard():
    engine = ClusterEngine()
    _add(engine, "Retry attempt 1 for job 4471", 1)
    _add(engine, "Retry attempt 2 for job 4471", 2)
    _add(engine, "Retry attempt 3 for job 9981", 3)
    clusters = engine.clusters()
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.count == 3
    assert cluster.template == ["Retry", "attempt", "<NUM>", "for", "job", "<NUM>"]


def test_different_token_count_never_merges():
    engine = ClusterEngine()
    _add(engine, "short line", 1)
    _add(engine, "a somewhat longer line here", 2)
    clusters = engine.clusters()
    assert len(clusters) == 2


def test_dissimilar_same_length_lines_stay_separate_at_default_threshold():
    engine = ClusterEngine(similarity_threshold=0.8)
    _add(engine, "alpha beta gamma delta", 1)
    _add(engine, "wolf tiger eagle shark", 2)
    clusters = engine.clusters()
    assert len(clusters) == 2
    assert all(c.count == 1 for c in clusters)


def test_zero_threshold_merges_even_fully_disjoint_same_length_lines():
    engine = ClusterEngine(similarity_threshold=0.0)
    _add(engine, "alpha beta gamma delta", 1)
    _add(engine, "wolf tiger eagle shark", 2)
    clusters = engine.clusters()
    # A zero threshold accepts any same-length line, so even fully
    # disjoint token sequences merge into one all-wildcard signature.
    assert len(clusters) == 1
    assert clusters[0].template == ["*", "*", "*", "*"]


def test_low_but_nonzero_threshold_merges_partially_similar_lines():
    engine = ClusterEngine(similarity_threshold=0.2)
    _add(engine, "alpha beta gamma delta", 1)
    # Shares one of four tokens ("delta") -> similarity 0.25, clears 0.2.
    _add(engine, "wolf tiger eagle delta", 2)
    clusters = engine.clusters()
    assert len(clusters) == 1
    assert clusters[0].template == ["*", "*", "*", "delta"]


def test_clusters_ranked_by_frequency_descending():
    engine = ClusterEngine()
    _add(engine, "common event A", 1)
    _add(engine, "common event A", 2)
    _add(engine, "common event A", 3)
    _add(engine, "rare event B", 4)
    ranked = engine.clusters()
    assert ranked[0].count == 3
    assert ranked[1].count == 1


def test_ties_keep_first_discovered_order():
    engine = ClusterEngine()
    _add(engine, "first one", 1)
    _add(engine, "second two", 2)
    ranked = engine.clusters()
    assert [c.count for c in ranked] == [1, 1]
    assert ranked[0].example == "first one"


def test_example_is_first_line_seen_in_cluster():
    engine = ClusterEngine()
    _add(engine, "Retry attempt 1 for job 4471", 1)
    _add(engine, "Retry attempt 2 for job 4471", 2)
    cluster = engine.clusters()[0]
    assert cluster.example == "Retry attempt 1 for job 4471"
    assert cluster.first_line_no == 1


def test_blank_lines_are_tracked_and_excluded_by_default():
    engine = ClusterEngine()
    _add(engine, "", 1)
    _add(engine, "real line here", 2)
    _add(engine, "   ", 3)
    assert engine.blank_lines == 2
    assert engine.total_lines == 3
    assert len(engine.clusters()) == 1
    assert len(engine.clusters(include_blank=True)) == 2


def test_invalid_similarity_threshold_raises():
    with pytest.raises(ValueError):
        ClusterEngine(similarity_threshold=1.5)
    with pytest.raises(ValueError):
        ClusterEngine(similarity_threshold=-0.1)


def test_cluster_lines_convenience_wrapper():
    lines = [
        "User user42 logged in",
        "User user77 logged in",
        "User user3 logged in",
    ]
    engine = cluster_lines(lines)
    clusters = engine.clusters()
    assert len(clusters) == 1
    assert clusters[0].count == 3
    assert clusters[0].template == ["User", "*", "logged", "in"]


def test_signature_joins_template_with_spaces():
    cluster = Cluster(template=["User", "*", "logged", "in"], count=3)
    assert cluster.signature() == "User * logged in"


def test_three_way_merge_widens_multiple_positions():
    engine = ClusterEngine()
    _add(engine, "a b c d", 1)
    _add(engine, "a X c d", 2)
    _add(engine, "a b Y d", 3)
    cluster = engine.clusters()[0]
    assert cluster.template == ["a", "*", "*", "d"]
    assert cluster.count == 3
