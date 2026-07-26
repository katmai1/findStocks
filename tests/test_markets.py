from findstocks.markets import EURONEXT, expand_markets


def test_expand_markets_euronext():
    assert expand_markets("EURONEXT") == EURONEXT


def test_expand_markets_case_insensitive():
    assert expand_markets("euronext") == EURONEXT
    assert expand_markets(["france"]) == ["FRANCE"]


def test_expand_markets_deduplicates_preserving_order():
    result = expand_markets(["EURONEXT", "FRANCE", "GERMANY"])
    assert result == [*EURONEXT, "GERMANY"]


def test_expand_markets_accepts_single_string():
    assert expand_markets("america") == ["AMERICA"]
