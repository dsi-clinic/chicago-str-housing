"""Tests for trend-matching feature resolver."""

from __future__ import annotations

import pytest

from housing.did_spec import (
    DID_TREND_MATCH_FEATURES_2,
    DID_TREND_MATCH_FEATURES_5,
    resolve_trend_match_features,
)


def test_resolve_trend_match_features_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default env resolves to five-feature matching."""
    monkeypatch.delenv("DID_MATCH_FEATURES", raising=False)
    assert resolve_trend_match_features() == DID_TREND_MATCH_FEATURES_5


def test_resolve_trend_match_features_two_feature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``slope_level`` selects two-feature matching."""
    monkeypatch.setenv("DID_MATCH_FEATURES", "slope_level")
    assert resolve_trend_match_features() == DID_TREND_MATCH_FEATURES_2


def test_resolve_trend_match_features_five_feature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``5feat`` alias selects five-feature matching."""
    monkeypatch.setenv("DID_MATCH_FEATURES", "5feat")
    assert resolve_trend_match_features() == DID_TREND_MATCH_FEATURES_5
