"""Offline smoke tests for EcoPulse desktop build.

Validates core pages, quantitative page construction, data persistence,
Data Health scoring, scenario logic and evidence bundle integrity.
"""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from app import EconomicDataService, INDICATORS, LocalStore, MainWindow, assess_data_health
from quant_pages import (
    build_macro_simulator_page,
    build_risk_analytics_page,
    build_information_flow_page,
    build_time_series_lab_page,
    build_network_anomaly_page,
    build_political_climate_page,
    build_markets_pricing_page,
    build_regulatory_emh_page,
    build_causal_epidemiological_page,
    build_fuzzy_decision_page,
    build_advanced_markets_page,
    build_compliance_suite_page,
)

_ALL_QUANT_BUILDERS = [
    build_macro_simulator_page,
    build_risk_analytics_page,
    build_information_flow_page,
    build_time_series_lab_page,
    build_network_anomaly_page,
    build_political_climate_page,
    build_markets_pricing_page,
    build_regulatory_emh_page,
    build_causal_epidemiological_page,
    build_fuzzy_decision_page,
    build_advanced_markets_page,
    build_compliance_suite_page,
]


def test_quant_page_construction() -> None:
    """Verify every quantitative page builds without raising an exception."""
    qt = QApplication.instance() or QApplication([])
    # Build a minimal MainWindow stub so page builders can reference parent
    window = MainWindow.__new__(MainWindow)
    # Avoid triggering _build_window during __new__
    for builder in _ALL_QUANT_BUILDERS:
        page = builder(window)
        assert page is not None, f"{builder.__name__} returned None"
        page.deleteLater()
    print(f"All {len(_ALL_QUANT_BUILDERS)} quant pages constructed successfully")


def test_core_app() -> None:
    """Validate core app functionality: data service, persistence, evidence."""
    temp = tempfile.TemporaryDirectory()
    os.environ["APPDATA"] = temp.name

    service = EconomicDataService()
    series = service._fallback_series("gdp", "USA")
    assert len(series) == 14
    assert series == sorted(series, key=lambda point: point.period)

    store = LocalStore()
    store.save_alert("Inflation", "above", 4.5)
    store.save_workspace("smoke", {"status": "ok"})
    assert store.alert_count() == 1
    assert any(name == "smoke" for name, _payload, _created_at in store.list_workspaces())

    health = assess_data_health({"gdp": series}, {"gdp": "offline smoke source"})
    assert health["gdp"]["state"] == "FALLBACK"
    assert health["gdp"]["score"] == 62

    qt = QApplication.instance() or QApplication([])
    original_load_country = MainWindow._load_country
    MainWindow._load_country = lambda self: None
    window = MainWindow()
    MainWindow._load_country = original_load_country
    payload = {key: service._fallback_series(key, "USA") for key in INDICATORS}
    window._apply_data(payload, {key: "offline smoke source" for key in INDICATORS})
    assert "SOURCE" in window.status_badge.text()
    assert window.metric_cards["gdp"].value.text() != "—"
    assert "FALLBACK 62/100" in window.data_health_label.text()
    window.growth_slider.setValue(-150)
    evidence = window.build_evidence_bundle()
    assert evidence["schema"] == "ecopulse.evidence-pack.v1"
    assert len(evidence["integrity"]["canonical_payload_sha256"]) == 64
    assert evidence["latest_observations"]["gdp"]["period"] == payload["gdp"][-1].period
    window.close()
    qt.quit()
    temp.cleanup()
    print("Core app smoke tests passed")


def main() -> None:
    test_quant_page_construction()
    test_core_app()
    print("All EcoPulse smoke tests passed")


if __name__ == "__main__":
    main()
