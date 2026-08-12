"""Offline smoke tests for EcoPulse Desktop."""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from app import EconomicDataService, LocalStore, MainWindow, INDICATORS


def main() -> None:
    temp = tempfile.TemporaryDirectory()
    os.environ["APPDATA"] = temp.name
    service = EconomicDataService()
    assert len(service._fallback_series("gdp", "USA")) == 14

    store = LocalStore()
    store.save_alert("Inflation", "above", 4.5)
    assert store.alert_count() == 1
    store.save_workspace("smoke", {"status": "ok"})

    qt = QApplication.instance() or QApplication([])
    original_load_country = MainWindow._load_country
    MainWindow._load_country = lambda self: None
    window = MainWindow()
    MainWindow._load_country = original_load_country
    payload = {key: service._fallback_series(key, "USA") for key in INDICATORS}
    window._apply_data(payload, {key: "offline smoke source" for key in INDICATORS})
    assert "SOURCE" in window.status_badge.text()
    assert window.metric_cards["gdp"].value.text() != "—"
    window.growth_slider.setValue(-150)
    assert "risk score" in window.scenario_summary.text().lower()
    window.close()
    qt.quit()
    temp.cleanup()
    print("EcoPulse smoke tests passed")


if __name__ == "__main__":
    main()
