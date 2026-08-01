import pytest

from findstocks.markets import check_markets


def test_check_markets_accepts_valid_markets():
    check_markets(["FRANCE", "GERMANY"])


def test_check_markets_rejects_unknown_market():
    with pytest.raises(ValueError, match="NOEXISTE"):
        check_markets(["NOEXISTE"])


def test_check_markets_accepts_empty_list():
    check_markets([])
