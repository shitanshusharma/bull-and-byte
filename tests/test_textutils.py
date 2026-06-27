from src.utils import jaccard, matches_keywords, title_tokens


def test_title_tokens_drops_stopwords_and_short_tokens():
    tokens = title_tokens("The new AI model is a big deal")
    assert "the" not in tokens   # stopword
    assert "is" not in tokens    # stopword
    assert "model" in tokens
    assert "big" in tokens


def test_title_tokens_strips_html_and_lowercases():
    tokens = title_tokens("<b>Nvidia</b> Soars")
    assert tokens == {"nvidia", "soars"}


def test_jaccard_identical_and_disjoint():
    a = {"alpha", "beta"}
    assert jaccard(a, a) == 1.0
    assert jaccard(a, {"gamma", "delta"}) == 0.0


def test_jaccard_partial_overlap():
    assert jaccard({"a", "b", "c"}, {"b", "c", "d"}) == 0.5


def test_jaccard_empty_is_zero():
    assert jaccard(set(), {"a"}) == 0.0


def test_matches_keywords_whole_word_only():
    assert matches_keywords("Breaking: OpenAI ships GPT", ["gpt"])
    # substring inside another word should not match
    assert not matches_keywords("encryption matters", ["ai"])


def test_matches_keywords_case_insensitive():
    assert matches_keywords("KUBERNETES at scale", ["kubernetes"])
