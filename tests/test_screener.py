import pandas as pd
import pytest

from findstocks.config import ScreenerConfig
from findstocks.screener import filter_candidates

FUTURE_EARNINGS = (pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=30)).isoformat()
NEAR_EARNINGS = (pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=2)).isoformat()
PAST_EARNINGS = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=2)).isoformat()


def make_row(**overrides):
    """Fila base que cumple TODOS los criterios por defecto."""
    row = {
        "Name": "ACME",
        "ISIN": "FR0000000001",
        "Exchange": "EPA",
        "Market": "FRANCE",
        "Price": 100.0,
        "Market Capitalization": 5_000_000_000,
        "Relative Strength Index (14)": 42,
        "Average Directional Index (14)": 25,
        "Simple Moving Average (50)": 95,
        "Simple Moving Average (200)": 90,
        "Yearly Performance": 10.0,
        "Relative Volume": 0.8,
        "Volume*Price": 100_000,
        "Upcoming Earnings Date": FUTURE_EARNINGS,
    }
    row.update(overrides)
    return row


@pytest.fixture
def config():
    return ScreenerConfig()


def test_valid_candidate_is_kept(config):
    df = pd.DataFrame([make_row()])
    result = filter_candidates(df, config)
    assert len(result) == 1


def test_downtrend_is_discarded(config):
    # precio por debajo de la SMA200 -> no hay tendencia alcista
    df = pd.DataFrame([make_row(Price=80, **{"Simple Moving Average (200)": 90})])
    result = filter_candidates(df, config)
    assert result.empty


def test_rsi_outside_pullback_zone_is_discarded(config):
    df = pd.DataFrame([make_row(**{"Relative Strength Index (14)": 80})])
    result = filter_candidates(df, config)
    assert result.empty


def test_low_adx_is_discarded(config):
    df = pd.DataFrame([make_row(**{"Average Directional Index (14)": 5})])
    result = filter_candidates(df, config)
    assert result.empty


def test_near_earnings_is_discarded_by_default(config):
    df = pd.DataFrame([make_row(**{"Upcoming Earnings Date": NEAR_EARNINGS})])
    result = filter_candidates(df, config)
    assert result.empty


def test_earnings_filter_can_be_disabled(config):
    config.days_min_earnings = 0
    df = pd.DataFrame([make_row(**{"Upcoming Earnings Date": NEAR_EARNINGS})])
    result = filter_candidates(df, config)
    assert len(result) == 1


def test_past_earnings_is_not_discarded(config):
    # earnings ya ocurridos (fecha en el pasado) no deben descartar el candidato
    df = pd.DataFrame([make_row(**{"Upcoming Earnings Date": PAST_EARNINGS})])
    result = filter_candidates(df, config)
    assert len(result) == 1


def test_max_price_filter(config):
    config.max_price = 50
    df = pd.DataFrame([make_row(Price=100)])
    result = filter_candidates(df, config)
    assert result.empty


def test_max_price_filter_disabled_when_zero(config):
    config.max_price = 0
    # precio alto pero manteniendo el resto de condiciones (tendencia, distancia a SMA200...)
    df = pd.DataFrame([make_row(
        Price=200,
        **{"Simple Moving Average (50)": 195, "Simple Moving Average (200)": 190},
    )])
    result = filter_candidates(df, config)
    assert len(result) == 1


def test_rows_with_missing_required_data_are_dropped(config):
    df = pd.DataFrame([make_row(Price=None)])
    result = filter_candidates(df, config)
    assert result.empty


def test_top_n_cap_per_market(config):
    config.top_n_cap = 1
    df = pd.DataFrame([
        make_row(**{"Market Capitalization": 1_000_000_000}),
        make_row(**{"Market Capitalization": 9_000_000_000}),
    ])
    result = filter_candidates(df, config)
    assert len(result) == 1
    assert result.iloc[0]["Market Capitalization"] == 9_000_000_000


def test_top_n_cap_preserves_market_column(config):
    # regresión: antes, groupby().apply() descartaba la columna "Market"
    # del resultado en versiones recientes de pandas
    config.top_n_cap = 100
    df = pd.DataFrame([
        make_row(**{"Market Capitalization": 1_000_000_000}),
        make_row(**{"Market Capitalization": 9_000_000_000}),
    ])
    result = filter_candidates(df, config)
    assert "Market" in result.columns


def test_top_n_cap_keeps_highest_market_cap(config):
    # regresión: antes no se ordenaba por capitalización antes de recortar,
    # así que "top" no cogía necesariamente las de mayor capitalización
    config.top_n_cap = 50
    df = pd.DataFrame([
        make_row(**{"Market Capitalization": 1_000_000_000}),
        make_row(**{"Market Capitalization": 2_000_000_000}),
        make_row(**{"Market Capitalization": 9_000_000_000}),
        make_row(**{"Market Capitalization": 3_000_000_000}),
    ])
    result = filter_candidates(df, config)
    assert len(result) == 2
    assert set(result["Market Capitalization"]) == {9_000_000_000, 3_000_000_000}


# --- SHORT ---

def make_row_short(**overrides):
    """Fila base bajista que cumple TODOS los criterios de short por defecto."""
    row = {
        "Name": "ACME",
        "ISIN": "FR0000000001",
        "Exchange": "EPA",
        "Market": "FRANCE",
        "Price": 90.0,
        "Market Capitalization": 5_000_000_000,
        "Relative Strength Index (14)": 58,
        "Average Directional Index (14)": 25,
        "Simple Moving Average (50)": 95,
        "Simple Moving Average (200)": 100,
        "Yearly Performance": -10.0,
        "Relative Volume": 0.8,
        "Volume*Price": 100_000,
        "Upcoming Earnings Date": FUTURE_EARNINGS,
    }
    row.update(overrides)
    return row


@pytest.fixture
def short_config():
    return ScreenerConfig(long_enabled=False, short_enabled=True)


def test_valid_short_candidate_is_kept(short_config):
    df = pd.DataFrame([make_row_short()])
    result = filter_candidates(df, short_config)
    assert len(result) == 1
    assert result.iloc[0]["Direction"] == "SHORT"


def test_short_uptrend_is_discarded(short_config):
    # precio por encima de la SMA200 -> no hay tendencia bajista
    df = pd.DataFrame([make_row_short(Price=110, **{"Simple Moving Average (200)": 100})])
    result = filter_candidates(df, short_config)
    assert result.empty


def test_short_rsi_outside_rally_zone_is_discarded(short_config):
    df = pd.DataFrame([make_row_short(**{"Relative Strength Index (14)": 20})])
    result = filter_candidates(df, short_config)
    assert result.empty


def test_short_positive_performance_is_discarded(short_config):
    df = pd.DataFrame([make_row_short(**{"Yearly Performance": 5.0})])
    result = filter_candidates(df, short_config)
    assert result.empty


def test_short_low_adx_is_discarded(short_config):
    df = pd.DataFrame([make_row_short(**{"Average Directional Index (14)": 5})])
    result = filter_candidates(df, short_config)
    assert result.empty


def test_short_too_far_below_sma200_is_discarded(short_config):
    short_config.max_distance_sma200_short = 0.05
    df = pd.DataFrame([make_row_short(Price=80, **{"Simple Moving Average (200)": 100})])
    result = filter_candidates(df, short_config)
    assert result.empty


def test_long_and_short_together_produce_both_directions():
    config = ScreenerConfig(long_enabled=True, short_enabled=True, top_n_cap=100)
    df = pd.DataFrame([make_row(), make_row_short(**{"ISIN": "FR0000000002"})])
    result = filter_candidates(df, config)
    assert set(result["Direction"]) == {"LONG", "SHORT"}
    assert len(result) == 2


def test_both_disabled_returns_empty_with_direction_column():
    config = ScreenerConfig(long_enabled=False, short_enabled=False)
    df = pd.DataFrame([make_row()])
    result = filter_candidates(df, config)
    assert result.empty
    assert "Direction" in result.columns
