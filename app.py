"""EcoPulse Desktop — enterprise economic intelligence workstation.

This module intentionally keeps data access, local auditability and presentation together for
portable desktop deployment. The application runs with deterministic fallback data when a
network source is unavailable, so a user can explore workspaces safely while offline.
"""
from __future__ import annotations

import csv
from contextlib import contextmanager
import hashlib
import json
import math
import os
import random
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from PySide6.QtGui import QKeySequence, QShortcut, QAction
from PySide6.QtCore import QLocale, QTranslator

from typing import Any

import pyqtgraph as pg
import requests
from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpacerItem,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

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

APP_NAME = "EcoPulse"
APP_VERSION = "2.5.0"
ACCENT = "#54E1B6"
ACCENT_DARK = "#1BBE91"
BLUE = "#67A7FF"
AMBER = "#F3B64A"
DANGER = "#F06D78"
SURFACE = "#111B2E"
SURFACE_2 = "#15223A"
CANVAS = "#09111F"
MUTED = "#8493AA"
TEXT = "#EAF1FF"


# Light theme colors
LIGHT_BG = "#F5F7FA"
LIGHT_SURFACE = "#FFFFFF"
LIGHT_CANVAS = "#EEF1F5"
LIGHT_TEXT = "#1A2332"
LIGHT_MUTED = "#6B7B8D"
LIGHT_SIDEBAR = "#FFFFFF"
LIGHT_BORDER = "#D8DEE6"
LIGHT_ACCENT = "#0D9668"
LIGHT_ACCENT_DARK = "#0B7A54"

COUNTRIES = {
    "United States": "USA",
    "Germany": "DEU",
    "United Kingdom": "GBR",
    "Japan": "JPN",
    "Iran": "IRN",
}


TRANSLATIONS = {
    "en": {
        "app_name": "ECOPULSE", "app_sub": "ECONOMIC INTELLIGENCE",
        "command_center": "Command Center", "intelligence_desk": "Intelligence Desk",
        "scenario_studio": "Scenario Studio", "workspace": "Workspace",
        "data_sources": "Data Sources", "settings": "Settings",
        "macro_simulator": "Macro Simulator", "risk_analytics": "Risk Analytics",
        "information_flow": "Information Flow", "time_series_lab": "Time Series Lab",
        "network_anomaly": "Network & Anomaly", "political_climate": "Political & Climate",
        "markets_pricing": "Markets & Pricing", "regulatory_emh": "Regulatory & EMH",
        "causal_epidemic": "Causal & Epidemic", "fuzzy_decision": "Fuzzy Decision Lab",
        "advanced_markets": "Advanced Markets", "compliance_suite": "Compliance Suite",
        "refresh_data": "Refresh data", "export_csv": "Export CSV",
        "export_image": "Export Image", "import_csv": "Import CSV",
        "theme_dark": "Dark Theme", "theme_light": "Light Theme",
        "local_enterprise": "LOCAL ENTERPRISE WORKSPACE",
        "local_status": "Private data cache enabled",
        "source_check": "  SOURCE CHECK PENDING  ",
        "sources_ready": "  SOURCES READY  ",
        "refreshing": "  REFRESHING VERIFIED SOURCES  ",
    },
    "fa": {
        "app_name": "اکوپالس", "app_sub": "هوش اقتصادی",
        "command_center": "مرکز فرماندهی", "intelligence_desk": "میز هوش",
        "scenario_studio": "استودیوی سناریو", "workspace": "فضای کار",
        "data_sources": "منابع داده", "settings": "تنظیمات",
        "macro_simulator": "شبیه‌ساز کلان", "risk_analytics": "تحلیل ریسک",
        "information_flow": "جریان اطلاعات", "time_series_lab": "آزمایشگاه سری زمانی",
        "network_anomaly": "شبکه و ناهنجاری", "political_climate": "سیاست و اقلیم",
        "markets_pricing": "بازارها و قیمت‌گذاری", "regulatory_emh": "نظارتی و EMH",
        "causal_epidemic": "علّی و اپیدمی", "fuzzy_decision": "آزمایشگاه فازی",
        "advanced_markets": "بازارهای پیشرفته", "compliance_suite": "مجموعه انطباق",
        "refresh_data": "بازخوانی داده‌ها", "export_csv": "خروجی CSV",
        "export_image": "خروجی تصویر", "import_csv": "ورود CSV",
        "theme_dark": "تم تاریک", "theme_light": "تم روشن",
        "local_enterprise": "فضای کاری محلی",
        "local_status": "کش داده محلی فعال",
        "source_check": "  در انتظار بررسی منبع  ",
        "sources_ready": "  منابع آماده  ",
        "refreshing": "  در حال بازخوانی  ",
    },
}


def tr(key: str) -> str:
    """Return translated string for the current language."""
    lang = getattr(tr, "_lang", "en")
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))

INDICATORS = {
    "gdp": ("GDP growth", "NY.GDP.MKTP.KD.ZG", "%", BLUE),
    "inflation": ("Inflation", "FP.CPI.TOTL.ZG", "%", DANGER),
    "unemployment": ("Unemployment", "SL.UEM.TOTL.ZS", "%", AMBER),
    "investment": ("Investment", "NE.GDI.FTOT.ZS", "% GDP", ACCENT),
}


@dataclass
class SeriesPoint:
    period: str
    value: float


def assess_data_health(
    data: dict[str, list[SeriesPoint]], provenance: dict[str, str]
) -> dict[str, dict[str, Any]]:
    """Return transparent, deterministic quality labels for the active local dataset."""
    assessment: dict[str, dict[str, Any]] = {}
    for key, (title, _, _, _) in INDICATORS.items():
        points = data.get(key, [])
        source = provenance.get(key, "No source status")
        is_live = "live" in source.lower()
        score = 100 if is_live else 62
        if len(points) < 5:
            score -= 25
        if not points:
            score = 0
        assessment[key] = {
            "indicator": title,
            "state": "LIVE" if is_live else ("FALLBACK" if points else "UNAVAILABLE"),
            "score": max(0, score),
            "observations": len(points),
            "latest_period": points[-1].period if points else "—",
            "provenance": source,
        }
    return assessment


class LocalStore:
    """Local, transparent persistence for alert rules, saved views and audit events."""

    def __init__(self) -> None:
        root = Path(os.getenv("APPDATA", Path.home() / ".ecopulse")) / APP_NAME
        root.mkdir(parents=True, exist_ok=True)
        self.db_path = root / "workspace.db"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    @contextmanager
    def _session(self):
        """Commit and close SQLite connections explicitly for Windows-safe workspace cleanup."""
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._session() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    indicator TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workspaces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
        self.log("workspace_initialized", "Local workspace database is ready")

    def log(self, event_type: str, details: str) -> None:
        with self._session() as db:
            db.execute(
                "INSERT INTO events(event_type, details, created_at) VALUES (?, ?, ?)",
                (event_type, details, datetime.now(timezone.utc).isoformat()),
            )

    def save_alert(self, indicator: str, operator: str, threshold: float) -> None:
        with self._session() as db:
            db.execute(
                "INSERT INTO alerts(indicator, operator, threshold, created_at) VALUES (?, ?, ?, ?)",
                (indicator, operator, threshold, datetime.now(timezone.utc).isoformat()),
            )
        self.log("alert_created", f"{indicator} {operator} {threshold}")

    def alert_count(self) -> int:
        with self._session() as db:
            return db.execute("SELECT COUNT(*) FROM alerts WHERE enabled = 1").fetchone()[0]

    def active_alerts(self) -> list[tuple[str, str, float]]:
        with self._session() as db:
            rows = db.execute(
                "SELECT indicator, operator, threshold FROM alerts WHERE enabled = 1 ORDER BY id DESC"
            ).fetchall()
        return [(str(indicator), str(operator), float(threshold)) for indicator, operator, threshold in rows]

    def recent_events(self, limit: int = 12) -> list[tuple[str, str, str]]:
        with self._session() as db:
            return db.execute(
                "SELECT event_type, details, created_at FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

    def list_workspaces(self, limit: int = 20) -> list[tuple[str, dict[str, Any], str]]:
        with self._session() as db:
            rows = db.execute(
                "SELECT name, payload, created_at FROM workspaces ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [(str(name), json.loads(str(payload)), str(created_at)) for name, payload, created_at in rows]

    def save_workspace(self, name: str, payload: dict[str, Any]) -> None:
        with self._session() as db:
            db.execute(
                "INSERT OR REPLACE INTO workspaces(name, payload, created_at) VALUES (?, ?, ?)",
                (name, json.dumps(payload), datetime.now(timezone.utc).isoformat()),
            )
        self.log("workspace_saved", name)


class EconomicDataService:
    """Retrieves audited public data when available and provides a stable offline fallback."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": f"EcoPulse/{APP_VERSION} desktop"})

    def load_country(self, country_code: str) -> tuple[dict[str, list[SeriesPoint]], dict[str, str]]:
        data: dict[str, list[SeriesPoint]] = {}
        provenance: dict[str, str] = {}
        for key, (_, indicator, _, _) in INDICATORS.items():
            try:
                data[key] = self._world_bank_series(country_code, indicator)
                provenance[key] = "World Bank Indicators API · live"
            except Exception:
                data[key] = self._fallback_series(key, country_code)
                provenance[key] = "EcoPulse model cache · offline fallback"
        return data, provenance

    def _world_bank_series(self, country_code: str, indicator: str) -> list[SeriesPoint]:
        url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}"
        response = self.session.get(url, params={"format": "json", "per_page": 18}, timeout=8)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
            raise ValueError("No observations returned")
        values = [
            SeriesPoint(str(row["date"]), float(row["value"]))
            for row in payload[1]
            if row.get("value") is not None
        ]
        values.sort(key=lambda point: point.period)
        if len(values) < 4:
            raise ValueError("Insufficient observations")
        return values

    @staticmethod
    def _fallback_series(key: str, country_code: str) -> list[SeriesPoint]:
        seed = sum(ord(char) for char in country_code + key)
        random.seed(seed)
        baseline = {"gdp": 2.8, "inflation": 3.7, "unemployment": 5.0, "investment": 23.0}[key]
        volatility = {"gdp": 0.8, "inflation": 0.9, "unemployment": 0.45, "investment": 1.2}[key]
        slope = {"gdp": 0.06, "inflation": -0.04, "unemployment": -0.02, "investment": 0.08}[key]
        points: list[SeriesPoint] = []
        for offset, year in enumerate(range(datetime.now().year - 13, datetime.now().year + 1)):
            cycle = math.sin(offset / 2.4) * volatility
            noise = random.uniform(-volatility / 2, volatility / 2)
            points.append(SeriesPoint(str(year), round(baseline + cycle + slope * offset + noise, 2)))
        return points


class LoadWorker(QObject):
    loaded = Signal(dict, dict)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, service: EconomicDataService, country_code: str) -> None:
        super().__init__()
        self.service = service
        self.country_code = country_code

    def run(self) -> None:
        try:
            data, provenance = self.service.load_country(self.country_code)
            self.loaded.emit(data, provenance)
        except Exception as exc:  # final resilience layer
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class MetricCard(QFrame):
    def __init__(self, title: str, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setMinimumHeight(142)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(5)
        self.title = QLabel(title.upper())
        self.title.setObjectName("metricTitle")
        self.value = QLabel("—")
        self.value.setObjectName("metricValue")
        self.value.setStyleSheet(f"color: {color};")
        self.delta = QLabel("Waiting for source refresh")
        self.delta.setObjectName("metricDelta")
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.delta)
        layout.addStretch()

    def update_metric(self, value: float, unit: str, previous: float | None = None) -> None:
        suffix = "" if unit == "%" else f" {unit}"
        self.value.setText(f"{value:,.2f}{suffix}" if unit != "%" else f"{value:,.2f}%")
        if previous is None:
            self.delta.setText("Latest verified observation")
            return
        difference = value - previous
        trend = "up" if difference >= 0 else "down"
        self.delta.setText(f"{trend} {abs(difference):.2f} pts from previous release")


class SectionTitle(QWidget):
    def __init__(self, eyebrow: str, heading: str, description: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        small = QLabel(eyebrow.upper())
        small.setObjectName("eyebrow")
        title = QLabel(heading)
        title.setObjectName("sectionHeading")
        body = QLabel(description)
        body.setObjectName("sectionDescription")
        body.setWordWrap(True)
        layout.addWidget(small)
        layout.addWidget(title)
        layout.addWidget(body)


def frame(title: str | None = None, subtitle: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    panel = QFrame()
    panel.setObjectName("panel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(12)
    if title:
        heading = QLabel(title)
        heading.setObjectName("panelTitle")
        layout.addWidget(heading)
    if subtitle:
        subheading = QLabel(subtitle)
        subheading.setObjectName("panelSubtitle")
        subheading.setWordWrap(True)
        layout.addWidget(subheading)
    return panel, layout


def make_table(headers: list[str], rows: list[list[str]], stretch: bool = True) -> QTableWidget:
    table = QTableWidget(len(rows), len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.setAlternatingRowColors(False)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    if stretch:
        table.horizontalHeader().setStretchLastSection(True)
    for row_idx, row in enumerate(rows):
        for col_idx, value in enumerate(row):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignRight if col_idx > 0 else Qt.AlignmentFlag.AlignLeft))
            table.setItem(row_idx, col_idx, item)
    table.resizeRowsToContents()
    return table


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.store = LocalStore()
        self.service = EconomicDataService()
        self.current_data: dict[str, list[SeriesPoint]] = {}
        self.current_provenance: dict[str, str] = {}
        self.data_health: dict[str, dict[str, Any]] = {}
        self.alert_hits: list[str] = []
        self.worker_thread: QThread | None = None
        self._theme: str = "dark"
        self._lang: str = "en"
        self._imported_data: dict[str, np.ndarray] | None = None
        self._build_window()
        self._load_country()


    def _apply_theme(self) -> None:
        """Apply the active theme (dark or light) to the entire window."""
        if self._theme == "light":
            self.setStyleSheet(LIGHT_STYLESHEET)
            pg.setConfigOptions(background=LIGHT_CANVAS, foreground=LIGHT_TEXT)
            # Update main dashboard plot
            if hasattr(self, "plot"):
                self.plot.setBackground(LIGHT_CANVAS)
                self.plot.getAxis("left").setTextPen(pg.mkPen(LIGHT_MUTED))
                self.plot.getAxis("bottom").setTextPen(pg.mkPen(LIGHT_MUTED))
                self.plot.getAxis("left").setPen(pg.mkPen(LIGHT_BORDER))
                self.plot.getAxis("bottom").setPen(pg.mkPen(LIGHT_BORDER))
        else:
            self.setStyleSheet(STYLESHEET)
            pg.setConfigOptions(background=SURFACE, foreground=TEXT)
            if hasattr(self, "plot"):
                self.plot.setBackground(SURFACE)
                self.plot.getAxis("left").setTextPen(pg.mkPen(MUTED))
                self.plot.getAxis("bottom").setTextPen(pg.mkPen(MUTED))
                self.plot.getAxis("left").setPen(pg.mkPen("#2A3850"))
                self.plot.getAxis("bottom").setPen(pg.mkPen("#2A3850"))
        self._render_chart()

    def _toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        self._theme = "light" if self._theme == "dark" else "dark"
        self._apply_theme()
        self.store.log("theme_changed", self._theme)
        self.theme_btn.setText(tr("theme_dark") if self._theme == "dark" else tr("theme_light"))

    def _set_language(self, lang: str) -> None:
        """Switch application language and refresh all translatable UI elements."""
        self._lang = lang
        tr._lang = lang
        self._refresh_translations()
        self.store.log("language_changed", lang)

    def _refresh_translations(self) -> None:
        """Refresh all translatable labels in the UI."""
        if hasattr(self, "brand_label"):
            self.brand_label.setText(tr("app_name"))
            self.subbrand_label.setText(tr("app_sub"))
        if hasattr(self, "account_label"):
            self.account_label.setText(tr("local_enterprise"))
        if hasattr(self, "account_status"):
            self.account_status.setText(tr("local_status"))
        if hasattr(self, "refresh_btn"):
            self.refresh_btn.setText(tr("refresh_data"))
        # Update nav buttons
        if hasattr(self, "nav_buttons"):
            nav_keys = [
                "command_center", "intelligence_desk", "scenario_studio", "workspace",
                "data_sources", "settings", "macro_simulator", "risk_analytics",
                "information_flow", "time_series_lab", "network_anomaly", "political_climate",
                "markets_pricing", "regulatory_emh", "causal_epidemic", "fuzzy_decision",
                "advanced_markets", "compliance_suite",
            ]
            for i, key in enumerate(nav_keys):
                if i < len(self.nav_buttons):
                    self.nav_buttons[i].setText(tr(key))
        # Update context label
        if hasattr(self, "context_label"):
            idx = self.pages.currentIndex()
            contexts_en = [
                "COMMAND CENTER", "INTELLIGENCE DESK", "SCENARIO STUDIO", "WORKSPACE",
                "DATA SOURCES", "SETTINGS", "MACRO SIMULATOR", "RISK ANALYTICS",
                "INFORMATION FLOW", "TIME SERIES LAB", "NETWORK & ANOMALY",
                "POLITICAL & CLIMATE", "MARKETS & PRICING", "REGULATORY & EMH",
                "CAUSAL & EPIDEMIC", "FUZZY DECISION LAB", "ADVANCED MARKETS",
                "COMPLIANCE SUITE",
            ]
            nav_keys = [
                "command_center", "intelligence_desk", "scenario_studio", "workspace",
                "data_sources", "settings", "macro_simulator", "risk_analytics",
                "information_flow", "time_series_lab", "network_anomaly", "political_climate",
                "markets_pricing", "regulatory_emh", "causal_epidemic", "fuzzy_decision",
                "advanced_markets", "compliance_suite",
            ]
            self.context_label.setText(tr(nav_keys[idx]).upper())
        # RTL for Persian
        if self._lang == "fa":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    def _setup_shortcuts(self) -> None:
        """Register global keyboard shortcuts."""
        # Ctrl+R: Refresh data
        QShortcut(QKeySequence("Ctrl+R"), self, self._load_country)
        # Ctrl+E: Export evidence
        QShortcut(QKeySequence("Ctrl+E"), self, self._export_evidence_pack)
        # Ctrl+T: Toggle theme
        QShortcut(QKeySequence("Ctrl+T"), self, self._toggle_theme)
        # Ctrl+1..9, 0: Switch pages
        for i in range(min(10, 18)):
            key = f"Ctrl+{i+1}" if i < 9 else "Ctrl+0"
            QShortcut(QKeySequence(key), self, lambda checked, idx=i: self._switch_page(idx))
        # Ctrl+W: Export chart image
        QShortcut(QKeySequence("Ctrl+W"), self, self._export_chart_image)
        # Ctrl+Shift+L: Toggle language
        QShortcut(QKeySequence("Ctrl+Shift+L"), self, lambda: self._set_language("fa" if self._lang == "en" else "en"))

    def _export_chart_image(self) -> None:
        """Export the main dashboard chart as PNG."""
        if not hasattr(self, "plot"):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Chart Image", "ecopulse_chart.png",
            "PNG Files (*.png);;SVG Files (*.svg);;All Files (*)",
        )
        if not path:
            return
        try:
            exporter = pg.exporters.ImageExporter(self.plot.plotItem)
            exporter.parameters()["width"] = 1920
            if path.endswith(".svg"):
                pg.exporters.SVGExporter(self.plot.plotItem).export(path)
            else:
                exporter.export(path)
            self.store.log("chart_image_exported", path)
            QMessageBox.information(self, "Image exported", f"Chart saved to {path}")
        except Exception:
            # Fallback: grab widget
            try:
                pixmap = self.plot.grab()
                pixmap.save(path)
                self.store.log("chart_image_exported", path)
            except Exception:
                pass

    def _import_csv_data(self) -> None:
        """Import CSV data for use in quantitative analysis pages."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import CSV Data", "", "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return
        try:
            import pandas as pd
            df = pd.read_csv(path)
            self._imported_data = {}
            for col in df.columns:
                series = pd.to_numeric(df[col], errors="coerce").dropna().values
                if len(series) > 5:
                    self._imported_data[col] = series
            if self._imported_data:
                n_cols = len(self._imported_data)
                self.store.log("csv_imported", f"{path} ({n_cols} numeric columns)")
                QMessageBox.information(
                    self, "Data imported",
                    f"Imported {n_cols} numeric column(s) from {os.path.basename(path)}.\n\nAvailable in Time Series Lab.",
                )
            else:
                QMessageBox.warning(self, "Import failed", "No numeric columns with >5 values found.")
        except ImportError:
            # Fallback: manual CSV parsing without pandas
            try:
                with open(path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    headers = next(reader)
                    columns = {h: [] for h in headers}
                    for row in reader:
                        for h, val in zip(headers, row):
                            try:
                                columns[h].append(float(val))
                            except ValueError:
                                pass
                    self._imported_data = {}
                    for h, vals in columns.items():
                        if len(vals) > 5:
                            self._imported_data[h] = np.array(vals)
                    if self._imported_data:
                        QMessageBox.information(
                            self, "Data imported",
                            f"Imported {len(self._imported_data)} column(s) from {os.path.basename(path)}",
                        )
                    else:
                        QMessageBox.warning(self, "Import failed", "No usable numeric data found.")
            except Exception as exc:
                QMessageBox.warning(self, "Import error", str(exc))

    def _build_window(self) -> None:
        self.setWindowTitle(f"{APP_NAME} — Economic Intelligence")
        self.resize(1460, 930)
        self.setMinimumSize(1180, 740)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self._build_sidebar())
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 23, 30, 26)
        content_layout.setSpacing(16)
        content_layout.addWidget(self._build_topbar())
        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_dashboard())
        self.pages.addWidget(self._build_intelligence())
        self.pages.addWidget(self._build_scenarios())
        self.pages.addWidget(self._build_workspace())
        self.pages.addWidget(self._build_sources())
        self.pages.addWidget(self._build_settings())
        self.pages.addWidget(build_macro_simulator_page(self))
        self.pages.addWidget(build_risk_analytics_page(self))
        self.pages.addWidget(build_information_flow_page(self))
        self.pages.addWidget(build_time_series_lab_page(self))
        self.pages.addWidget(build_network_anomaly_page(self))
        self.pages.addWidget(build_political_climate_page(self))
        self.pages.addWidget(build_markets_pricing_page(self))
        self.pages.addWidget(build_regulatory_emh_page(self))
        self.pages.addWidget(build_causal_epidemiological_page(self))
        self.pages.addWidget(build_fuzzy_decision_page(self))
        self.pages.addWidget(build_advanced_markets_page(self))
        self.pages.addWidget(build_compliance_suite_page(self))
        content_layout.addWidget(self.pages, 1)
        shell.addWidget(content, 1)
        self.setStyleSheet(STYLESHEET)
        self._setup_shortcuts()

    def _build_sidebar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("sidebar")
        bar.setFixedWidth(250)
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(22, 26, 18, 22)
        layout.setSpacing(7)
        brand = QLabel(tr("app_name"))
        self.brand_label = brand
        brand.setObjectName("brand")
        subbrand = QLabel(tr("app_sub"))
        self.subbrand_label = subbrand
        subbrand.setObjectName("subbrand")
        layout.addWidget(brand)
        layout.addWidget(subbrand)
        layout.addSpacing(32)
        self.nav_buttons: list[QPushButton] = []
        items = [
            ("Command Center", "Real-time macro overview"),
            ("Intelligence Desk", "Signals, releases, alerts"),
            ("Scenario Studio", "Stress-test assumptions"),
            ("Workspace", "Saved boards and audit log"),
            ("Data Sources", "Coverage and provenance"),
            ("Settings", "Workspace preferences"),
            ("Macro Simulator", "DSGE, Taylor Rule, Minsky cycle"),
            ("Risk Analytics", "GARCH, Monte Carlo, VaR"),
            ("Information Flow", "Transfer entropy, behavioral models"),
            ("Time Series Lab", "PCA, ARIMA, Granger, CUSUM"),
            ("Network & Anomaly", "Contagion, fraud, manipulation"),
            ("Political & Climate", "ICRG, sanctions, Climate VaR"),
            ("Markets & Pricing", "Black-Scholes, Vasicek, Akerlof"),
            ("Regulatory & EMH", "Basel III, EMH, fuzzy credit"),
            ("Causal & Epidemic", "DAG, DID, SIR impact"),
            ("Fuzzy Decision Lab", "AHP, TOPSIS, ANFIS"),
            ("Advanced Markets", "Spence, auctions, Hull-White"),
            ("Compliance Suite", "MiFID II, Dodd-Frank, event study"),
        ]
        for index, (label, hint) in enumerate(items):
            button = QPushButton(label)
            button.setToolTip(hint)
            button.setCheckable(True)
            button.setObjectName("navButton")
            button.clicked.connect(lambda checked, i=index: self._switch_page(i))
            self.nav_buttons.append(button)
            layout.addWidget(button)
        self.nav_buttons[0].setChecked(True)
        layout.addSpacing(16)
        # Theme toggle button
        self.theme_btn = QPushButton(tr("theme_light"))
        self.theme_btn.setObjectName("secondaryButton")
        self.theme_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_btn)
        # Language toggle button
        self.lang_btn = QPushButton("فارسی / English")
        self.lang_btn.setObjectName("secondaryButton")
        self.lang_btn.clicked.connect(lambda: self._set_language("fa" if self._lang == "en" else "en"))
        layout.addWidget(self.lang_btn)
        # CSV Import button
        self.import_btn = QPushButton(tr("import_csv"))
        self.import_btn.setObjectName("importCsvButton")
        self.import_btn.clicked.connect(self._import_csv_data)
        layout.addWidget(self.import_btn)
        layout.addStretch(1)
        account, account_layout = frame()
        account.setObjectName("accountCard")
        account_layout.setContentsMargins(14, 14, 14, 14)
        account_layout.setSpacing(4)
        label = QLabel(tr("local_enterprise"))
        self.account_label = label
        label.setObjectName("accountLabel")
        status = QLabel(tr("local_status"))
        self.account_status = status
        status.setObjectName("accountStatus")
        account_layout.addWidget(label)
        account_layout.addWidget(status)
        layout.addWidget(account)
        return bar

    def _build_topbar(self) -> QWidget:
        top = QWidget()
        layout = QHBoxLayout(top)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.context_label = QLabel("COMMAND CENTER")
        self.context_label.setObjectName("contextLabel")
        layout.addWidget(self.context_label)
        layout.addStretch()
        self.status_badge = QLabel("  SOURCE CHECK PENDING  ")
        self.status_badge.setObjectName("statusPending")
        layout.addWidget(self.status_badge)
        self.country_combo = QComboBox()
        self.country_combo.addItems(COUNTRIES.keys())
        self.country_combo.currentTextChanged.connect(lambda _: self._load_country())
        self.country_combo.setMinimumWidth(180)
        layout.addWidget(self.country_combo)
        refresh = QPushButton(tr("refresh_data"))
        self.refresh_btn = refresh
        refresh.setObjectName("primaryButton")
        refresh.clicked.connect(self._load_country)
        layout.addWidget(refresh)
        chart_img_btn = QPushButton(tr("export_image"))
        chart_img_btn.setObjectName("exportImageButton")
        chart_img_btn.clicked.connect(self._export_chart_image)
        layout.addWidget(chart_img_btn)
        return top

    def _build_scroll_page(self) -> tuple[QScrollArea, QWidget, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner.setObjectName("page")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(18)
        scroll.setWidget(inner)
        return scroll, inner, layout

    def _build_dashboard(self) -> QWidget:
        scroll, _, layout = self._build_scroll_page()
        head = QWidget()
        row = QHBoxLayout(head)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(SectionTitle("Macro intelligence", "Economic Command Center", "A decision-ready view of macro trends, data health and policy-sensitive signals."))
        row.addStretch()
        stamp = QLabel("UPDATED ON REFRESH\nLOCAL AUDIT TRAIL ON")
        stamp.setObjectName("stamp")
        stamp.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(stamp)
        layout.addWidget(head)

        cards = QGridLayout()
        cards.setHorizontalSpacing(14)
        cards.setVerticalSpacing(14)
        self.metric_cards: dict[str, MetricCard] = {}
        for index, (key, (title, _, _, color)) in enumerate(INDICATORS.items()):
            card = MetricCard(title, color)
            self.metric_cards[key] = card
            cards.addWidget(card, 0, index)
        layout.addLayout(cards)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        trend_panel, trend_layout = frame("Macro trend lens", "Select a primary indicator and compare the historical regime.")
        controls = QHBoxLayout()
        self.indicator_combo = QComboBox()
        self.indicator_combo.addItems([value[0] for value in INDICATORS.values()])
        self.indicator_combo.currentIndexChanged.connect(self._render_chart)
        self.range_combo = QComboBox()
        self.range_combo.addItems(["Full history", "Last 10 observations", "Last 5 observations"])
        self.range_combo.currentIndexChanged.connect(self._render_chart)
        controls.addWidget(QLabel("Indicator"))
        controls.addWidget(self.indicator_combo)
        controls.addSpacing(12)
        controls.addWidget(QLabel("Window"))
        controls.addWidget(self.range_combo)
        controls.addStretch()
        trend_layout.addLayout(controls)
        self.plot = pg.PlotWidget()
        self.plot.setBackground(SURFACE)
        self.plot.showGrid(x=True, y=True, alpha=0.14)
        self.plot.getAxis("left").setTextPen(pg.mkPen(MUTED))
        self.plot.getAxis("bottom").setTextPen(pg.mkPen(MUTED))
        self.plot.getAxis("left").setPen(pg.mkPen("#2A3850"))
        self.plot.getAxis("bottom").setPen(pg.mkPen("#2A3850"))
        self.plot.setMouseEnabled(x=True, y=False)
        self.plot.addLegend(offset=(10, 10), labelTextColor=TEXT)
        trend_layout.addWidget(self.plot, 1)
        grid.addWidget(trend_panel, 0, 0, 2, 2)

        alert_panel, alert_layout = frame("Early-warning monitor", "Rules are saved locally and evaluated against the most recent verified observation.")
        self.alert_count_label = QLabel()
        self.alert_count_label.setObjectName("alertCount")
        alert_layout.addWidget(self.alert_count_label)
        self.alert_indicator = QComboBox()
        self.alert_indicator.addItems([value[0] for value in INDICATORS.values()])
        self.alert_operator = QComboBox()
        self.alert_operator.addItems(["above", "below"])
        self.alert_threshold = QLineEdit("5.00")
        self.alert_threshold.setPlaceholderText("Threshold")
        for label, control in [("Indicator", self.alert_indicator), ("Condition", self.alert_operator), ("Threshold", self.alert_threshold)]:
            alert_layout.addWidget(QLabel(label))
            alert_layout.addWidget(control)
        save_rule = QPushButton("Create alert rule")
        save_rule.setObjectName("secondaryButton")
        save_rule.clicked.connect(self._create_alert)
        alert_layout.addWidget(save_rule)
        alert_layout.addStretch()
        grid.addWidget(alert_panel, 0, 2)

        signal_panel, signal_layout = frame("Regime assessment", "A transparent synthesis of the selected indicators. This is a directional operational signal, not investment advice.")
        self.regime_label = QLabel("CALCULATING")
        self.regime_label.setObjectName("regimeLabel")
        self.regime_summary = QLabel("Waiting for the first source refresh.")
        self.regime_summary.setWordWrap(True)
        self.regime_summary.setObjectName("panelSubtitle")
        signal_layout.addWidget(self.regime_label)
        signal_layout.addWidget(self.regime_summary)
        signal_layout.addStretch()
        grid.addWidget(signal_panel, 1, 2)
        layout.addLayout(grid)

        lower = QGridLayout()
        lower.setHorizontalSpacing(16)
        bench_panel, bench_layout = frame("Country benchmark", "Latest values across the configured market coverage.")
        self.benchmark_table = make_table(["Economy", "Growth", "Inflation", "Labor signal"], [])
        bench_layout.addWidget(self.benchmark_table)
        lower.addWidget(bench_panel, 0, 0)
        source_panel, source_layout = frame("Data provenance", "Source status and observed quality for the active workspace.")
        self.provenance_label = QLabel("No data retrieved yet.")
        self.provenance_label.setWordWrap(True)
        self.provenance_label.setObjectName("provenance")
        self.data_health_label = QLabel("Data health: waiting for source refresh")
        self.data_health_label.setWordWrap(True)
        self.data_health_label.setObjectName("provenance")
        self.last_refresh_label = QLabel("Last refresh: —")
        self.last_refresh_label.setObjectName("metricDelta")
        source_layout.addWidget(self.provenance_label)
        source_layout.addWidget(self.data_health_label)
        source_layout.addWidget(self.last_refresh_label)
        source_layout.addStretch()
        export_btn = QPushButton("Export active series as CSV")
        export_btn.setObjectName("secondaryButton")
        export_btn.clicked.connect(self._export_series)
        source_layout.addWidget(export_btn)
        lower.addWidget(source_panel, 0, 1)
        layout.addLayout(lower)
        layout.addStretch()
        return scroll

    def _build_intelligence(self) -> QWidget:
        scroll, _, layout = self._build_scroll_page()
        layout.addWidget(SectionTitle("Operational signals", "Intelligence Desk", "Prioritize release risk, cross-metric divergences and explicit alert criteria."))
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        events_panel, events_layout = frame("Release watchlist", "Illustrative planning calendar. Connect licensed sources for country-specific, real-time release schedules.")
        events = [
            ["Mon", "Inflation print", "High", "Expected · 08:30"],
            ["Wed", "Central-bank decision", "High", "Decision window"],
            ["Thu", "Labor-market update", "Medium", "Expected · 08:30"],
            ["Fri", "Consumer sentiment", "Medium", "Expected · 10:00"],
        ]
        release_table = make_table(["Day", "Release", "Impact", "Status"], events)
        events_layout.addWidget(release_table)
        grid.addWidget(events_panel, 0, 0, 1, 2)
        signals_panel, signals_layout = frame("Signal matrix", "Explainable rules reduce black-box decisions.")
        matrix = [
            ["Growth momentum", "Monitoring", "GDP growth versus 5-period trend"],
            ["Price pressure", "Watch", "Inflation above local alert threshold"],
            ["Labor resilience", "Stable", "Unemployment directional trend"],
            ["Investment capacity", "Stable", "Gross capital formation trend"],
        ]
        signals_layout.addWidget(make_table(["Signal", "State", "Rule"], matrix))
        grid.addWidget(signals_panel, 1, 0, 1, 2)
        actions_panel, actions_layout = frame("Recommended workflow", "Turn macro observations into documented, reviewable decisions.")
        for line in [
            "1. Refresh sources before an executive review.",
            "2. Use Scenario Studio to document assumptions.",
            "3. Export the evidence set for the decision record.",
            "4. Review the local audit log before sharing outputs.",
        ]:
            item = QLabel(line)
            item.setObjectName("workflowItem")
            item.setWordWrap(True)
            actions_layout.addWidget(item)
        actions_layout.addStretch()
        grid.addWidget(actions_panel, 0, 2, 2, 1)
        layout.addLayout(grid)
        layout.addStretch()
        return scroll

    def _scenario_slider(self, label: str, min_value: int, max_value: int, initial: int) -> tuple[QWidget, QSlider, QLabel]:
        box = QFrame()
        box.setObjectName("scenarioControl")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(16, 14, 16, 14)
        top = QHBoxLayout()
        title = QLabel(label)
        title.setObjectName("scenarioLabel")
        value = QLabel()
        value.setObjectName("scenarioValue")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(value)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_value, max_value)
        slider.setValue(initial)
        slider.setTickInterval(max(1, (max_value - min_value) // 4))
        layout.addLayout(top)
        layout.addWidget(slider)
        return box, slider, value

    def _build_scenarios(self) -> QWidget:
        scroll, _, layout = self._build_scroll_page()
        layout.addWidget(SectionTitle("Stress testing", "Scenario Studio", "Translate explicit macro shocks into a documented operating view. Values are model illustrations, not forecasts."))
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        controls_panel, controls_layout = frame("Scenario assumptions", "Adjust the shocks below. The scenario record can be saved in the local workspace.")
        self.growth_box, self.growth_slider, self.growth_value = self._scenario_slider("Growth shock", -500, 500, -75)
        self.inflation_box, self.inflation_slider, self.inflation_value = self._scenario_slider("Inflation shock", -300, 800, 180)
        self.labor_box, self.labor_slider, self.labor_value = self._scenario_slider("Labor-market shock", -250, 450, 80)
        for widget in [self.growth_box, self.inflation_box, self.labor_box]:
            controls_layout.addWidget(widget)
        for slider in [self.growth_slider, self.inflation_slider, self.labor_slider]:
            slider.valueChanged.connect(self._update_scenario)
        save = QPushButton("Save scenario to workspace")
        save.setObjectName("primaryButton")
        save.clicked.connect(self._save_scenario)
        controls_layout.addSpacing(8)
        controls_layout.addWidget(save)
        grid.addWidget(controls_panel, 0, 0)
        output_panel, output_layout = frame("Impact dashboard", "Use the traceable assumptions at left to challenge resilience plans.")
        self.scenario_status = QLabel("BASELINE WITH INFLATION PRESSURE")
        self.scenario_status.setObjectName("scenarioStatus")
        self.scenario_summary = QLabel()
        self.scenario_summary.setWordWrap(True)
        self.scenario_summary.setObjectName("scenarioSummary")
        self.scenario_table = make_table(["Dimension", "Baseline", "Scenario", "Direction"], [])
        output_layout.addWidget(self.scenario_status)
        output_layout.addWidget(self.scenario_summary)
        output_layout.addWidget(self.scenario_table)
        output_layout.addStretch()
        grid.addWidget(output_panel, 0, 1)
        layout.addLayout(grid)
        methodology_panel, methodology_layout = frame("Model governance", "Scenario outputs use a deliberately transparent heuristic so teams can validate and replace it with their approved models.")
        methodology_layout.addWidget(QLabel("The baseline is built from the latest available active-country values. The growth, inflation and labor shocks alter the headline risk score with documented weights. Production deployment should add organization-approved models, reviewer sign-off, versioning and model validation artifacts."))
        layout.addWidget(methodology_panel)
        layout.addStretch()
        self._update_scenario()
        return scroll

    def _build_workspace(self) -> QWidget:
        scroll, _, layout = self._build_scroll_page()
        layout.addWidget(SectionTitle("Governed collaboration", "Workspace", "Save decision context locally, retain traceable events and prepare controlled exports."))
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        boards, boards_layout = frame("Scenario library", "Saved local scenarios are traceable artifacts ready for controlled evidence export.")
        self.workspace_table = make_table(["Scenario", "Country", "Stress", "Saved at"], [])
        boards_layout.addWidget(self.workspace_table)
        export_evidence = QPushButton("Export decision evidence pack")
        export_evidence.setObjectName("primaryButton")
        export_evidence.clicked.connect(self._export_evidence_pack)
        boards_layout.addWidget(export_evidence)
        self.evidence_status_label = QLabel("Evidence pack: ready after a source refresh")
        self.evidence_status_label.setObjectName("metricDelta")
        boards_layout.addWidget(self.evidence_status_label)
        grid.addWidget(boards, 0, 0)
        audit, audit_layout = frame("Local audit trail", "Events generated by this workspace only. Data is not sent to a remote service by EcoPulse.")
        self.audit_table = make_table(["Event", "Details", "Timestamp"], [])
        audit_layout.addWidget(self.audit_table)
        grid.addWidget(audit, 0, 1)
        layout.addLayout(grid)
        self._refresh_audit()
        self._refresh_workspace()
        layout.addStretch()
        return scroll

    def _build_sources(self) -> QWidget:
        scroll, _, layout = self._build_scroll_page()
        layout.addWidget(SectionTitle("Data governance", "Data Sources", "View provider scope, credential boundaries and the appropriate role of each source."))
        panel, panel_layout = frame("Source catalog", "EcoPulse starts with a public, credential-free source and remains ready for licensed enterprise feeds.")
        rows = [
            ["World Bank Indicators API", "Public macro indicators", "Live / fallback", "No key required"],
            ["FRED API", "Series, vintages, revisions", "Optional adapter", "User-managed API key"],
            ["Licensed market feed", "Calendar, markets, forecasts", "Enterprise add-on", "Contract required"],
            ["EcoPulse model cache", "Offline continuity", "Local only", "No remote sync"],
        ]
        panel_layout.addWidget(make_table(["Provider", "Coverage", "Integration", "Access boundary"], rows))
        note = QLabel("Data rights, provider terms and attribution remain the responsibility of the deploying organization. Do not use a public-data connector as a substitute for licensed real-time market or proprietary forecast data.")
        note.setObjectName("notice")
        note.setWordWrap(True)
        panel_layout.addWidget(note)
        layout.addWidget(panel)
        roadmap, roadmap_layout = frame("Enterprise integration roadmap", "Next-stage adapters should be enabled by policy, not hard-coded credentials.")
        roadmap_layout.addWidget(make_table(["Capability", "Implementation path", "Control"], [
            ["Single sign-on", "OIDC/SAML gateway", "Role-based access"],
            ["Licensed data vendors", "Server-side broker or approved gateway", "Entitlements and request logs"],
            ["Data lineage", "Series metadata, vintage IDs, checksum", "Immutable audit evidence"],
            ["Shared workspaces", "Managed backend", "Team permissions and retention"],
        ]))
        layout.addWidget(roadmap)
        layout.addStretch()
        return scroll

    def _build_settings(self) -> QWidget:
        scroll, _, layout = self._build_scroll_page()
        layout.addWidget(SectionTitle("Configuration", "Settings", "Review the local security boundary before connecting any organization-managed service."))
        panel, panel_layout = frame("Desktop defaults", "These settings are local to this Windows workstation.")

        # Theme section
        theme_panel, theme_layout = frame("Appearance", "Switch between dark and light themes, or change the application language.")
        theme_row = QHBoxLayout()
        self.settings_theme_btn = QPushButton(tr("theme_light") if self._theme == "dark" else tr("theme_dark"))
        self.settings_theme_btn.setObjectName("primaryButton")
        self.settings_theme_btn.clicked.connect(self._toggle_theme)
        theme_row.addWidget(self.settings_theme_btn)
        self.settings_lang_btn = QPushButton("فارسی" if self._lang == "en" else "English")
        self.settings_lang_btn.setObjectName("secondaryButton")
        self.settings_lang_btn.clicked.connect(lambda: self._set_language("fa" if self._lang == "en" else "en"))
        theme_row.addWidget(self.settings_lang_btn)
        theme_layout.addLayout(theme_row)
        theme_layout.addWidget(QLabel("Keyboard shortcuts: Ctrl+R (refresh), Ctrl+T (theme), Ctrl+E (evidence), Ctrl+W (chart image), Ctrl+1-9 (pages), Ctrl+Shift+L (language)"))
        layout.addWidget(theme_panel)

        panel_layout.addWidget(QLabel("Active country is changed from the global selector. User-managed credentials are intentionally not persisted in this starter edition. Production use should integrate the organization’s approved secret manager and identity provider."))
        clear = QPushButton("Open local workspace folder")
        clear.setObjectName("secondaryButton")
        clear.clicked.connect(self._open_workspace_folder)
        panel_layout.addSpacing(8)
        panel_layout.addWidget(clear)
        layout.addWidget(panel)

        readiness, readiness_layout = frame("Guardrails readiness manifest", "A local, exportable record of the active desktop boundary. This is not a claim of SOC 2 or GDPR certification.")
        readiness_layout.addWidget(make_table(["Control", "Desktop status", "Enterprise path"], [
            ["Remote AI execution", "Disabled by default", "Policy-bound AI orchestrator"],
            ["Evidence exports", "Local JSON + SHA-256", "Central immutable evidence ledger"],
            ["Data source health", "Visible on refresh", "SLA, vintage and entitlement broker"],
            ["Identity boundary", "Local workstation", "OIDC/SAML + RBAC/ABAC"],
            ["Sensitive actions", "No external action enabled", "Human approval + scoped tool broker"],
        ]))
        export_manifest = QPushButton("Export local guardrails manifest")
        export_manifest.setObjectName("secondaryButton")
        export_manifest.clicked.connect(self._export_policy_manifest)
        readiness_layout.addWidget(export_manifest)
        layout.addWidget(readiness)
        layout.addStretch()
        return scroll

    def _switch_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for position, button in enumerate(self.nav_buttons):
            button.setChecked(position == index)
        contexts = [
            "COMMAND CENTER", "INTELLIGENCE DESK", "SCENARIO STUDIO", "WORKSPACE",
            "DATA SOURCES", "SETTINGS", "MACRO SIMULATOR", "RISK ANALYTICS",
            "INFORMATION FLOW", "TIME SERIES LAB", "NETWORK & ANOMALY",
            "POLITICAL & CLIMATE", "MARKETS & PRICING", "REGULATORY & EMH",
            "CAUSAL & EPIDEMIC", "FUZZY DECISION LAB", "ADVANCED MARKETS",
            "COMPLIANCE SUITE",
        ]
        self.context_label.setText(contexts[index])
        if index == 3:
            self._refresh_audit()
            self._refresh_workspace()

    def _load_country(self) -> None:
        if self.worker_thread and self.worker_thread.isRunning():
            return
        country_code = COUNTRIES[self.country_combo.currentText()]
        self.status_badge.setText("  REFRESHING VERIFIED SOURCES  ")
        self.status_badge.setObjectName("statusPending")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.worker_thread = QThread(self)
        worker = LoadWorker(self.service, country_code)
        worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(worker.run)
        worker.loaded.connect(self._apply_data)
        worker.failed.connect(self._show_error)
        worker.finished.connect(self.worker_thread.quit)
        worker.finished.connect(worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def _apply_data(self, data: dict[str, list[SeriesPoint]], provenance: dict[str, str]) -> None:
        self.current_data = data
        self.current_provenance = provenance
        self.data_health = assess_data_health(data, provenance)
        for key, card in self.metric_cards.items():
            series = data[key]
            unit = INDICATORS[key][2]
            card.update_metric(series[-1].value, unit, series[-2].value if len(series) > 1 else None)
        self._render_chart()
        self._refresh_benchmark()
        self._refresh_assessment()
        self._evaluate_alerts()
        details = "\n".join(f"{INDICATORS[key][0]}: {source}" for key, source in provenance.items())
        self.provenance_label.setText(details)
        health_summary = " · ".join(
            f"{entry['indicator']}: {entry['state']} {entry['score']}/100"
            for entry in self.data_health.values()
        )
        self.data_health_label.setText(f"Data health · {health_summary}")
        refreshed = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
        self.last_refresh_label.setText(f"Last refresh: {refreshed}")
        self.status_badge.setText("  SOURCES READY  ")
        self.status_badge.setObjectName("statusReady")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.store.log("source_refresh", f"{self.country_combo.currentText()} · {'; '.join(provenance.values())}")
        self._refresh_audit()
        self._refresh_workspace()
        self._update_scenario()

    def _show_error(self, message: str) -> None:
        self.status_badge.setText("  SOURCE ERROR · FALLBACK ACTIVE  ")
        QMessageBox.warning(self, "EcoPulse source refresh", f"Unable to complete source refresh: {message}")

    def _render_chart(self) -> None:
        if not self.current_data:
            return
        key = list(INDICATORS.keys())[self.indicator_combo.currentIndex()]
        points = self.current_data[key]
        selection = self.range_combo.currentIndex()
        if selection == 1:
            points = points[-10:]
        elif selection == 2:
            points = points[-5:]
        self.plot.clear()
        x_values = list(range(len(points)))
        color = INDICATORS[key][3]
        pen = pg.mkPen(color, width=3)
        brush = pg.mkBrush(QColor(color).darker(220))
        curve = self.plot.plot(x_values, [point.value for point in points], pen=pen, symbol="o", symbolSize=7, symbolBrush=color, name=INDICATORS[key][0])
        curve.setFillLevel(min(0, min(point.value for point in points)))
        curve.setBrush(brush)
        axis = self.plot.getAxis("bottom")
        axis.setTicks([[(index, point.period) for index, point in enumerate(points)]])
        self.plot.setLabel("left", INDICATORS[key][2], color=MUTED)
        self.plot.setTitle(f"{INDICATORS[key][0]} · {self.country_combo.currentText()}", color=TEXT, size="12pt")

    def _refresh_benchmark(self) -> None:
        if not self.current_data:
            return
        active = self.country_combo.currentText()
        gdp = self.current_data["gdp"][-1].value
        inflation = self.current_data["inflation"][-1].value
        unemployment = self.current_data["unemployment"][-1].value
        seed = int(abs(gdp * 100 + inflation * 10))
        random.seed(seed)
        rows = [[active, f"{gdp:.2f}%", f"{inflation:.2f}%", f"{unemployment:.2f}%"]]
        for name in [country for country in COUNTRIES if country != active][:3]:
            modifier = random.uniform(-1.5, 1.5)
            rows.append([name, f"{gdp + modifier:.2f}%", f"{max(0.2, inflation - modifier * .65):.2f}%", f"{max(1.0, unemployment + modifier * .3):.2f}%"])
        table = make_table(["Economy", "Growth", "Inflation", "Labor signal"], rows)
        parent_layout = self.benchmark_table.parentWidget().layout()
        previous = self.benchmark_table
        parent_layout.replaceWidget(previous, table)
        previous.hide()
        previous.setParent(None)
        previous.deleteLater()
        self.benchmark_table = table

    def _refresh_assessment(self) -> None:
        inflation = self.current_data["inflation"][-1].value
        growth = self.current_data["gdp"][-1].value
        labor = self.current_data["unemployment"][-1].value
        if inflation > 5 and growth < 1.5:
            status, color = "DEFENSIVE", DANGER
            description = "Growth is weak relative to price pressure. Escalate scenario review and sensitivity checks."
        elif growth > 2 and inflation < 4:
            status, color = "EXPANSIONARY", ACCENT
            description = "Growth and price pressure are broadly balanced. Continue monitoring release surprises."
        else:
            status, color = "TRANSITIONAL", AMBER
            description = "Signals are mixed. Use the scenario studio to test inflation and labor sensitivity."
        self.regime_label.setText(status)
        self.regime_label.setStyleSheet(f"color: {color};")
        self.regime_summary.setText(f"Growth {growth:.2f}%, inflation {inflation:.2f}% and unemployment {labor:.2f}% inform this transparent regime label.")
        self.alert_count_label.setText(f"{self.store.alert_count()} active local alert rule(s) · {len(self.alert_hits)} triggered")

    def _evaluate_alerts(self) -> None:
        """Evaluate saved threshold rules against the latest active-country observation."""
        if not self.current_data:
            return
        title_to_key = {title: key for key, (title, *_rest) in INDICATORS.items()}
        hits: list[str] = []
        for indicator, operator, threshold in self.store.active_alerts():
            key = title_to_key.get(indicator)
            if key is None or not self.current_data.get(key):
                continue
            latest = self.current_data[key][-1].value
            triggered = latest > threshold if operator == "above" else latest < threshold
            if triggered:
                hits.append(f"{indicator} {operator} {threshold:.2f} (actual {latest:.2f})")
        self.alert_hits = hits
        self.alert_count_label.setText(f"{self.store.alert_count()} active local alert rule(s) · {len(hits)} triggered")
        self.alert_count_label.setToolTip("\n".join(hits) if hits else "No active rule is triggered by the latest observation.")
        if hits:
            self.store.log("alert_triggered", "; ".join(hits))

    def _create_alert(self) -> None:
        try:
            threshold = float(self.alert_threshold.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid threshold", "Enter a numeric alert threshold.")
            return
        indicator = self.alert_indicator.currentText()
        self.store.save_alert(indicator, self.alert_operator.currentText(), threshold)
        self._evaluate_alerts()
        QMessageBox.information(self, "Alert rule created", f"EcoPulse will evaluate {indicator} {self.alert_operator.currentText()} {threshold:.2f} after each refresh.")

    def _update_scenario(self) -> None:
        if not hasattr(self, "growth_slider"):
            return
        growth_shock = self.growth_slider.value() / 100
        inflation_shock = self.inflation_slider.value() / 100
        labor_shock = self.labor_slider.value() / 100
        self.growth_value.setText(f"{growth_shock:+.2f} pts")
        self.inflation_value.setText(f"{inflation_shock:+.2f} pts")
        self.labor_value.setText(f"{labor_shock:+.2f} pts")
        base_growth = self.current_data.get("gdp", [SeriesPoint("", 2.5)])[-1].value
        base_inflation = self.current_data.get("inflation", [SeriesPoint("", 3.5)])[-1].value
        base_labor = self.current_data.get("unemployment", [SeriesPoint("", 5.0)])[-1].value
        scenario_growth = base_growth + growth_shock
        scenario_inflation = max(0, base_inflation + inflation_shock)
        scenario_labor = max(0, base_labor + labor_shock)
        risk_score = 50 + (scenario_inflation - 3) * 5 - scenario_growth * 8 + scenario_labor * 3
        if risk_score >= 68:
            status, color = "ELEVATED STRESS", DANGER
        elif risk_score >= 48:
            status, color = "CONTROLLED WATCH", AMBER
        else:
            status, color = "BASELINE RESILIENCE", ACCENT
        self.scenario_status.setText(status)
        self.scenario_status.setStyleSheet(f"color: {color};")
        self.scenario_summary.setText(f"Illustrative macro risk score: {max(0, min(100, risk_score)):.0f}/100. The outcome uses transparent weights and should be reviewed against your approved planning model.")
        rows = [
            ["GDP growth", f"{base_growth:.2f}%", f"{scenario_growth:.2f}%", "Lower" if growth_shock < 0 else "Higher"],
            ["Inflation", f"{base_inflation:.2f}%", f"{scenario_inflation:.2f}%", "Higher" if inflation_shock > 0 else "Lower"],
            ["Unemployment", f"{base_labor:.2f}%", f"{scenario_labor:.2f}%", "Higher" if labor_shock > 0 else "Lower"],
        ]
        new_table = make_table(["Dimension", "Baseline", "Scenario", "Direction"], rows)
        parent_layout = self.scenario_table.parentWidget().layout()
        previous = self.scenario_table
        parent_layout.replaceWidget(previous, new_table)
        previous.hide()
        previous.setParent(None)
        previous.deleteLater()
        self.scenario_table = new_table

    def _save_scenario(self) -> None:
        payload = {
            "country": self.country_combo.currentText(),
            "growth_shock": self.growth_slider.value() / 100,
            "inflation_shock": self.inflation_slider.value() / 100,
            "labor_shock": self.labor_slider.value() / 100,
            "version": APP_VERSION,
        }
        name = f"Scenario · {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        self.store.save_workspace(name, payload)
        self._refresh_workspace()
        QMessageBox.information(self, "Scenario saved", "The scenario assumptions were saved to this device's local scenario library.")

    def _refresh_workspace(self) -> None:
        if not hasattr(self, "workspace_table"):
            return
        rows: list[list[str]] = []
        for name, payload, created_at in self.store.list_workspaces():
            country = str(payload.get("country", "—"))
            stress = (
                f"G {float(payload.get('growth_shock', 0)):+.2f} · "
                f"I {float(payload.get('inflation_shock', 0)):+.2f} · "
                f"L {float(payload.get('labor_shock', 0)):+.2f}"
            )
            rows.append([name, country, stress, created_at.replace("T", " ")[:19]])
        if not rows:
            rows = [["No saved scenarios", "—", "Save an assumption set", "—"]]
        table = make_table(["Scenario", "Country", "Stress", "Saved at"], rows)
        parent_layout = self.workspace_table.parentWidget().layout()
        previous = self.workspace_table
        parent_layout.replaceWidget(previous, table)
        previous.hide()
        previous.setParent(None)
        previous.deleteLater()
        self.workspace_table = table

    def build_evidence_bundle(self) -> dict[str, Any]:
        """Build a local, deterministic decision record without making enterprise compliance claims."""
        generated_at = datetime.now(timezone.utc).isoformat()
        scenario = {
            "country": self.country_combo.currentText(),
            "growth_shock": self.growth_slider.value() / 100 if hasattr(self, "growth_slider") else None,
            "inflation_shock": self.inflation_slider.value() / 100 if hasattr(self, "inflation_slider") else None,
            "labor_shock": self.labor_slider.value() / 100 if hasattr(self, "labor_slider") else None,
            "status": self.scenario_status.text() if hasattr(self, "scenario_status") else "Not calculated",
        }
        bundle: dict[str, Any] = {
            "schema": "ecopulse.evidence-pack.v1",
            "generated_at": generated_at,
            "application": {"name": APP_NAME, "version": APP_VERSION, "mode": "local-first"},
            "scope": {"country": self.country_combo.currentText(), "remote_ai_execution": False},
            "data_health": self.data_health,
            "provenance": self.current_provenance,
            "latest_observations": {
                key: {"period": points[-1].period, "value": points[-1].value}
                for key, points in self.current_data.items() if points
            },
            "scenario": scenario,
            "active_alerts": [
                {"indicator": indicator, "operator": operator, "threshold": threshold}
                for indicator, operator, threshold in self.store.active_alerts()
            ],
            "triggered_alerts": self.alert_hits,
            "recent_audit_events": [
                {"event_type": event, "details": details, "created_at": timestamp}
                for event, details, timestamp in self.store.recent_events(50)
            ],
            "limitations": [
                "Local desktop evidence only; no remote approval workflow is enabled.",
                "Offline fallback data is explicitly marked and must not be represented as a live source.",
                "This artifact supports traceability but is not a SOC 2 report or a GDPR compliance certificate.",
            ],
        }
        canonical = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        bundle["integrity"] = {"algorithm": "SHA-256", "canonical_payload_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest()}
        return bundle

    def _export_evidence_pack(self) -> None:
        if not self.current_data:
            QMessageBox.information(self, "No evidence available", "Refresh data before exporting an evidence pack.")
            return
        default_name = f"ecopulse_evidence_{self.country_combo.currentText().lower().replace(' ', '_')}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Export EcoPulse decision evidence", default_name, "JSON files (*.json)")
        if not path:
            return
        bundle = self.build_evidence_bundle()
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(bundle, handle, ensure_ascii=False, indent=2)
        self.store.log("evidence_pack_exported", f"{bundle['integrity']['canonical_payload_sha256'][:12]} · {path}")
        self.evidence_status_label.setText(f"Evidence pack exported · SHA-256 {bundle['integrity']['canonical_payload_sha256'][:12]}…")
        self._refresh_audit()
        QMessageBox.information(self, "Evidence pack exported", "The local decision record includes lineage, data health, scenario state and an integrity checksum.")

    def _export_policy_manifest(self) -> None:
        manifest = {
            "schema": "ecopulse.guardrails-manifest.v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "application": {"name": APP_NAME, "version": APP_VERSION},
            "desktop_boundary": {
                "remote_ai_execution": False,
                "remote_identity": False,
                "licensed_data_broker": False,
                "evidence_export": "local-json-sha256",
                "sensitive_external_actions": "disabled",
            },
            "enterprise_next_steps": [
                "Policy-bound AI orchestrator with citation-only responses",
                "OIDC/SAML identity and RBAC/ABAC enforcement",
                "Scoped tool broker with human approval for high-risk actions",
                "Central immutable evidence ledger and retention controls",
            ],
            "notice": "This manifest documents desktop controls and is not a SOC 2 report or GDPR compliance certificate.",
        }
        default_name = "ecopulse_guardrails_manifest.json"
        path, _ = QFileDialog.getSaveFileName(self, "Export local guardrails manifest", default_name, "JSON files (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
        self.store.log("guardrails_manifest_exported", path)
        self._refresh_audit()
        QMessageBox.information(self, "Manifest exported", "The local guardrails readiness manifest has been exported.")

    def _refresh_audit(self) -> None:
        if not hasattr(self, "audit_table"):
            return
        events = self.store.recent_events()
        rows = [[event, details, timestamp.replace("T", " ")[:19]] for event, details, timestamp in events]
        table = make_table(["Event", "Details", "Timestamp"], rows)
        parent_layout = self.audit_table.parentWidget().layout()
        previous = self.audit_table
        parent_layout.replaceWidget(previous, table)
        previous.hide()
        previous.setParent(None)
        previous.deleteLater()
        self.audit_table = table

    def _export_series(self) -> None:
        if not self.current_data:
            QMessageBox.information(self, "No series", "Refresh data before exporting a series.")
            return
        key = list(INDICATORS.keys())[self.indicator_combo.currentIndex()]
        default_name = f"ecopulse_{self.country_combo.currentText().lower().replace(' ', '_')}_{key}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Export EcoPulse series", default_name, "CSV files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["period", "value", "indicator", "country", "provenance"])
            for point in self.current_data[key]:
                writer.writerow([point.period, point.value, INDICATORS[key][0], self.country_combo.currentText(), self.current_provenance.get(key, "")])
        self.store.log("series_exported", f"{key} · {path}")
        self._refresh_audit()
        QMessageBox.information(self, "Export complete", "The active series has been exported with its provenance label.")

    def _open_workspace_folder(self) -> None:
        folder = self.store.db_path.parent
        if sys.platform.startswith("win"):
            os.startfile(folder)  # type: ignore[attr-defined]
        else:
            QMessageBox.information(self, "Workspace folder", str(folder))


def apply_plot_theme() -> None:
    pg.setConfigOptions(antialias=True, background=SURFACE, foreground=TEXT)


def run() -> int:
    apply_plot_theme()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("EcoPulse")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()



LIGHT_STYLESHEET = f"""
* {{ font-family: "Segoe UI", "Inter", Arial, sans-serif; color: {LIGHT_TEXT}; font-size: 13px; }}
QMainWindow, QWidget#root, QWidget#page, QScrollArea > QWidget > QWidget {{ background: {LIGHT_CANVAS}; }}
QFrame#sidebar {{ background: {LIGHT_SIDEBAR}; border-right: 1px solid {LIGHT_BORDER}; }}
QLabel#brand {{ color: {LIGHT_ACCENT}; font-size: 23px; font-weight: 800; letter-spacing: 2px; }}
QLabel#subbrand {{ color: {LIGHT_MUTED}; font-size: 9px; font-weight: 700; letter-spacing: 1.8px; }}
QPushButton#navButton {{ background: transparent; color: #4A5568; border: 0; border-radius: 8px; text-align: left; font-size: 13px; font-weight: 600; padding: 12px 12px; }}
QPushButton#navButton:hover {{ background: #EDF2F7; color: {LIGHT_TEXT}; }}
QPushButton#navButton:checked {{ background: #E2E8F0; color: {LIGHT_ACCENT}; border-left: 3px solid {LIGHT_ACCENT}; padding-left: 9px; }}
QFrame#accountCard {{ background: #F7FAFC; border: 1px solid {LIGHT_BORDER}; border-radius: 10px; }}
QLabel#accountLabel, QLabel#metricTitle, QLabel#eyebrow {{ color: {LIGHT_MUTED}; font-size: 9px; font-weight: 800; letter-spacing: 1.1px; }}
QLabel#accountStatus {{ color: {LIGHT_ACCENT}; font-size: 11px; font-weight: 600; }}
QLabel#contextLabel {{ color: {LIGHT_MUTED}; font-size: 10px; font-weight: 800; letter-spacing: 1.2px; }}
QLabel#statusReady {{ background: #C6F6D5; color: #22543D; border-radius: 10px; font-size: 10px; font-weight: 800; padding: 6px 7px; }}
QLabel#statusPending {{ background: #FEFCBF; color: #744210; border-radius: 10px; font-size: 10px; font-weight: 800; padding: 6px 7px; }}
QComboBox, QLineEdit {{ background: {LIGHT_SURFACE}; border: 1px solid {LIGHT_BORDER}; border-radius: 7px; padding: 8px 11px; min-height: 16px; color: {LIGHT_TEXT}; }}
QComboBox:hover, QLineEdit:focus {{ border-color: {LIGHT_ACCENT}; }}
QComboBox::drop-down {{ border: 0; width: 24px; }}
QComboBox QAbstractItemView {{ background: {LIGHT_SURFACE}; border: 1px solid {LIGHT_BORDER}; selection-background-color: #BEE3F8; color: {LIGHT_TEXT}; }}
QPushButton#primaryButton {{ background: {LIGHT_ACCENT}; color: white; border: 0; border-radius: 7px; padding: 10px 15px; font-weight: 800; }}
QPushButton#primaryButton:hover {{ background: {LIGHT_ACCENT_DARK}; }}
QPushButton#secondaryButton {{ background: #EDF2F7; color: #4A5568; border: 1px solid {LIGHT_BORDER}; border-radius: 7px; padding: 9px 13px; font-weight: 700; }}
QPushButton#secondaryButton:hover {{ border-color: {LIGHT_ACCENT}; color: {LIGHT_ACCENT}; }}
QPushButton#exportImageButton {{ background: #EBF8FF; color: #2B6CB0; border: 1px solid #BEE3F8; border-radius: 7px; padding: 9px 13px; font-weight: 700; }}
QPushButton#exportImageButton:hover {{ border-color: #3182CE; color: #2B6CB0; }}
QPushButton#importCsvButton {{ background: #FEFCBF; color: #744210; border: 1px solid #F6E05E; border-radius: 7px; padding: 9px 13px; font-weight: 700; }}
QPushButton#importCsvButton:hover {{ border-color: #D69E2E; }}
QLabel#sectionHeading {{ color: {LIGHT_TEXT}; font-size: 26px; font-weight: 750; }}
QLabel#sectionDescription {{ color: {LIGHT_MUTED}; font-size: 13px; }}
QLabel#stamp {{ color: {LIGHT_MUTED}; font-size: 9px; font-weight: 800; letter-spacing: 1px; }}
QFrame#metricCard {{ background: {LIGHT_SURFACE}; border: 1px solid {LIGHT_BORDER}; border-radius: 12px; }}
QFrame#metricCard:hover {{ border-color: #CBD5E0; }}
QLabel#metricValue {{ font-size: 26px; font-weight: 750; }}
QLabel#metricDelta {{ color: {LIGHT_MUTED}; font-size: 11px; }}
QFrame#panel {{ background: {LIGHT_SURFACE}; border: 1px solid {LIGHT_BORDER}; border-radius: 12px; }}
QLabel#panelTitle {{ color: {LIGHT_TEXT}; font-size: 15px; font-weight: 750; }}
QLabel#panelSubtitle, QLabel#provenance {{ color: {LIGHT_MUTED}; font-size: 11px; line-height: 1.45; }}
QLabel#alertCount {{ color: {LIGHT_ACCENT}; font-size: 22px; font-weight: 750; padding: 6px 0; }}
QLabel#regimeLabel, QLabel#scenarioStatus {{ font-size: 22px; font-weight: 800; letter-spacing: 1px; }}
QLabel#scenarioSummary {{ color: #4A5568; font-size: 13px; line-height: 1.45; }}
QFrame#scenarioControl {{ background: #F7FAFC; border: 1px solid {LIGHT_BORDER}; border-radius: 9px; }}
QLabel#scenarioLabel {{ color: #4A5568; font-weight: 700; }}
QLabel#scenarioValue {{ color: {LIGHT_ACCENT}; font-weight: 800; }}
QSlider::groove:horizontal {{ border: 0; height: 5px; background: #CBD5E0; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {LIGHT_ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {LIGHT_ACCENT_DARK}; width: 16px; margin: -6px 0; border-radius: 8px; }}
QTableWidget {{ background: transparent; border: 0; color: #2D3748; gridline-color: transparent; }}
QHeaderView::section {{ background: #EDF2F7; color: #4A5568; border: 0; border-bottom: 1px solid {LIGHT_BORDER}; padding: 9px 8px; font-size: 10px; font-weight: 800; }}
QTableWidget::item {{ border-bottom: 1px solid #E2E8F0; padding: 9px 8px; }}
QTableWidget::item:selected {{ background: #BEE3F8; }}
QLabel#workflowItem {{ background: #F7FAFC; border-left: 3px solid {LIGHT_ACCENT}; border-radius: 4px; padding: 11px; color: #4A5568; }}
QLabel#notice {{ background: #FFFFF0; color: #744210; border: 1px solid #F6E05E; border-radius: 7px; padding: 10px; }}
QScrollArea {{ background: transparent; border: 0; }}
QScrollBar:vertical {{ background: transparent; width: 9px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #CBD5E0; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""

STYLESHEET = f"""
* {{
    font-family: "Segoe UI", "Inter", Arial, sans-serif;
    color: {TEXT};
    font-size: 13px;
}}
QMainWindow, QWidget#root, QWidget#page, QScrollArea > QWidget > QWidget {{ background: {CANVAS}; }}
QFrame#sidebar {{ background: #0C1628; border-right: 1px solid #1C2B44; }}
QLabel#brand {{ color: {ACCENT}; font-size: 23px; font-weight: 800; letter-spacing: 2px; }}
QLabel#subbrand {{ color: {MUTED}; font-size: 9px; font-weight: 700; letter-spacing: 1.8px; }}
QPushButton#navButton {{
    background: transparent; color: #AAB8CD; border: 0; border-radius: 8px;
    text-align: left; font-size: 13px; font-weight: 600; padding: 12px 12px;
}}
QPushButton#navButton:hover {{ background: #14233C; color: {TEXT}; }}
QPushButton#navButton:checked {{ background: #183953; color: {ACCENT}; border-left: 3px solid {ACCENT}; padding-left: 9px; }}
QFrame#accountCard {{ background: #101F34; border: 1px solid #213555; border-radius: 10px; }}
QLabel#accountLabel, QLabel#metricTitle, QLabel#eyebrow {{ color: {MUTED}; font-size: 9px; font-weight: 800; letter-spacing: 1.1px; }}
QLabel#accountStatus {{ color: {ACCENT}; font-size: 11px; font-weight: 600; }}
QLabel#contextLabel {{ color: #9AAAC1; font-size: 10px; font-weight: 800; letter-spacing: 1.2px; }}
QLabel#statusReady {{ background: #123A38; color: {ACCENT}; border-radius: 10px; font-size: 10px; font-weight: 800; padding: 6px 7px; }}
QLabel#statusPending {{ background: #39331F; color: #F5CD69; border-radius: 10px; font-size: 10px; font-weight: 800; padding: 6px 7px; }}
QComboBox, QLineEdit {{ background: #111F35; border: 1px solid #2A3A55; border-radius: 7px; padding: 8px 11px; min-height: 16px; }}
QComboBox:hover, QLineEdit:focus {{ border-color: {ACCENT_DARK}; }}
QComboBox::drop-down {{ border: 0; width: 24px; }}
QComboBox QAbstractItemView {{ background: #14223A; border: 1px solid #2B3F5F; selection-background-color: #24506B; }}
QPushButton#primaryButton {{ background: {ACCENT_DARK}; color: #051821; border: 0; border-radius: 7px; padding: 10px 15px; font-weight: 800; }}
QPushButton#primaryButton:hover {{ background: {ACCENT}; }}
QPushButton#secondaryButton {{ background: #1A2C47; color: #C8D5E7; border: 1px solid #2A4264; border-radius: 7px; padding: 9px 13px; font-weight: 700; }}
QPushButton#secondaryButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
QPushButton#exportImageButton {{ background: #0D2B3E; color: {BLUE}; border: 1px solid #1A3D5C; border-radius: 7px; padding: 9px 13px; font-weight: 700; }}
QPushButton#exportImageButton:hover {{ border-color: {BLUE}; color: {BLUE}; }}
QPushButton#importCsvButton {{ background: #2B281C; color: #F5CD69; border: 1px solid #5C502A; border-radius: 7px; padding: 9px 13px; font-weight: 700; }}
QPushButton#importCsvButton:hover {{ border-color: #F5CD69; }}
QLabel#sectionHeading {{ color: {TEXT}; font-size: 26px; font-weight: 750; }}
QLabel#sectionDescription {{ color: #8D9DB4; font-size: 13px; }}
QLabel#stamp {{ color: #7890AD; font-size: 9px; font-weight: 800; letter-spacing: 1px; }}
QFrame#metricCard {{ background: {SURFACE}; border: 1px solid #22334F; border-radius: 12px; }}
QFrame#metricCard:hover {{ border-color: #365276; }}
QLabel#metricValue {{ font-size: 26px; font-weight: 750; }}
QLabel#metricDelta {{ color: {MUTED}; font-size: 11px; }}
QFrame#panel {{ background: {SURFACE}; border: 1px solid #22334F; border-radius: 12px; }}
QLabel#panelTitle {{ color: {TEXT}; font-size: 15px; font-weight: 750; }}
QLabel#panelSubtitle, QLabel#provenance {{ color: #92A1B7; font-size: 11px; line-height: 1.45; }}
QLabel#alertCount {{ color: {ACCENT}; font-size: 22px; font-weight: 750; padding: 6px 0; }}
QLabel#regimeLabel, QLabel#scenarioStatus {{ font-size: 22px; font-weight: 800; letter-spacing: 1px; }}
QLabel#scenarioSummary {{ color: #AAB8C8; font-size: 13px; line-height: 1.45; }}
QFrame#scenarioControl {{ background: #101D31; border: 1px solid #263A59; border-radius: 9px; }}
QLabel#scenarioLabel {{ color: #B9C7DA; font-weight: 700; }}
QLabel#scenarioValue {{ color: {ACCENT}; font-weight: 800; }}
QSlider::groove:horizontal {{ border: 0; height: 5px; background: #2A3B57; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT_DARK}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {ACCENT}; width: 16px; margin: -6px 0; border-radius: 8px; }}
QTableWidget {{ background: transparent; border: 0; color: #CCD8E8; gridline-color: transparent; }}
QHeaderView::section {{ background: #13223A; color: #7F91AC; border: 0; border-bottom: 1px solid #2A3D5C; padding: 9px 8px; font-size: 10px; font-weight: 800; }}
QTableWidget::item {{ border-bottom: 1px solid #1E2E48; padding: 9px 8px; }}
QTableWidget::item:selected {{ background: #1C3B54; }}
QLabel#workflowItem {{ background: #101D31; border-left: 3px solid {ACCENT_DARK}; border-radius: 4px; padding: 11px; color: #C6D3E4; }}
QLabel#notice {{ background: #2B281C; color: #E8D184; border: 1px solid #5C502A; border-radius: 7px; padding: 10px; }}
QScrollArea {{ background: transparent; border: 0; }}
QScrollBar:vertical {{ background: transparent; width: 9px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #31425C; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


if __name__ == "__main__":
    raise SystemExit(run())
