"""Offline smoke tests for EcoPulse Desktop."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from app import (
    EconomicDataService,
    LocalStore,
    MainWindow,
    INDICATORS,
    assess_data_health,
    assess_decision_readiness,
    verify_evidence_bundle,
    verify_scenario_ledger,
)


def main() -> None:
    temp = tempfile.TemporaryDirectory()
    os.environ["APPDATA"] = temp.name

    service = EconomicDataService()
    series = service._fallback_series("gdp", "USA")
    assert len(series) == 14
    assert all(isinstance(point.value, float) for point in series)
    assert series == sorted(series, key=lambda point: point.period)

    store = LocalStore()
    store.save_alert("Inflation", "above", 4.5)
    assert store.alert_count() == 1
    store.save_workspace("smoke", {"status": "ok"})
    assert any(event[0] == "workspace_saved" for event in store.recent_events())
    assert any(name == "smoke" for name, _payload, _created_at in store.list_workspaces())
    chain = store.verify_audit_chain()
    assert chain["verified"] is True
    assert chain["checked_events"] >= 3

    health = assess_data_health({"gdp": series}, {"gdp": "offline smoke source"})
    assert health["gdp"]["state"] == "FALLBACK"
    assert health["gdp"]["score"] == 62
    readiness = assess_decision_readiness(health, ["Inflation above 4.50"])
    assert readiness["state"] == "BLOCKED"
    assert "Unavailable data" in readiness["blockers"][0]
    full_fallback_health = assess_data_health(
        {key: service._fallback_series(key, "USA") for key in INDICATORS},
        {key: "offline smoke source" for key in INDICATORS},
    )
    reviewed_readiness = assess_decision_readiness(full_fallback_health, ["Inflation above 4.50"])
    assert reviewed_readiness["state"] == "REVIEW REQUIRED"
    assert "Fallback data" in reviewed_readiness["blockers"][0]

    qt = QApplication.instance() or QApplication([])
    original_load_country = MainWindow._load_country
    MainWindow._load_country = lambda self: None
    window = MainWindow()
    MainWindow._load_country = original_load_country
    assert window.windowTitle().startswith("EcoPulse")
    payload = {key: service._fallback_series(key, "USA") for key in INDICATORS}
    provenance = {key: "offline smoke source" for key in INDICATORS}
    window._apply_data(payload, provenance)
    assert "SOURCE" in window.status_badge.text()
    assert window.metric_cards["gdp"].value.text() != "—"
    assert "FALLBACK 62/100" in window.data_health_label.text()
    window.growth_slider.setValue(-150)
    assert "risk score" in window.scenario_summary.text().lower()
    evidence = window.build_evidence_bundle()
    assert evidence["schema"] == "ecopulse.evidence-pack.v1"
    assert len(evidence["integrity"]["canonical_payload_sha256"]) == 64
    assert evidence["latest_observations"]["gdp"]["period"] == payload["gdp"][-1].period
    assert evidence["decision_readiness"]["state"] == "REVIEW REQUIRED"
    assert evidence["audit_integrity"]["verified"] is True
    assert verify_evidence_bundle(evidence)["valid"] is True
    evidence["scenario"]["status"] = "tampered"
    assert verify_evidence_bundle(evidence)["valid"] is False
    assert "AUDIT VERIFIED" in window.audit_integrity_label.text()
    window.store.save_workspace(
        "governed-smoke",
        {
            "schema": "ecopulse.scenario-record.v1",
            "country": "United States",
            "growth_shock": -1.0,
            "inflation_shock": 1.5,
            "labor_shock": 0.5,
            "risk_score": 61,
            "decision_readiness": "REVIEW REQUIRED",
        },
    )
    ledger = window.build_scenario_ledger()
    assert len(ledger["records"]) >= 1
    assert verify_scenario_ledger(ledger)["valid"] is True
    ledger["records"][0]["payload"]["risk_score"] = 99
    assert verify_scenario_ledger(ledger)["valid"] is False
    window.close()
    qt.quit()
    temp.cleanup()
    print("EcoPulse smoke tests passed")


if __name__ == "__main__":
    main()
