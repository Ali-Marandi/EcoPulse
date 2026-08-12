# EcoPulse Desktop

> **A Windows economic-intelligence workstation for transparent macro monitoring, controlled scenarios and locally auditable decisions.**

EcoPulse Desktop transforms the original Dash prototype into a native **Windows-ready** workstation. The current commercial-ready edition replaces random in-memory demo data with a resilient provider layer, a high-density desktop interface, local alert rules, scenario controls, provenance-aware exports, Data Health labels, a Scenario Library and a local audit trail. It is designed for macro strategy teams, corporate planning, risk functions and analysts who need a decision workspace rather than a static chart page.

![EcoPulse Command Center](assets/ecopulse-command-center.png)

## Product scope in this release

| Capability | Delivered behavior | Commercial value |
| --- | --- | --- |
| **Economic Command Center** | A dark, native desktop dashboard exposes GDP growth, inflation, unemployment and investment trends for a selected economy. | Gives executives a coherent macro lens rather than fragmented browser tabs. |
| **Resilient public-data adapter** | World Bank data is requested without an embedded credential; EcoPulse falls back to deterministic local series if the source is unavailable. | Supports continuity while clearly labelling live versus fallback provenance. |
| **Data Health lens** | Each active indicator receives a transparent live/fallback state, observation count and deterministic readiness score. | Prevents a fallback source from being silently treated as verified live data. |
| **Signal and early-warning workspace** | Users can define locally stored threshold rules and review a transparent regime assessment. | Makes the analytical process repeatable and reviewable. |
| **Scenario Studio and Library** | Explicit growth, inflation and labour shocks drive transparent, illustrative outcomes; saved scenarios appear as reusable local artifacts. | Supports structured planning conversations and stress-test preparation. |
| **Evidence and auditability** | CSV export carries provenance; a JSON Decision Evidence Pack includes data health, lineage, scenario state, alerts, audit events and a SHA-256 integrity checksum. | Creates a lightweight, exportable decision record without an external backend. |
| **Local Guardrails Manifest** | Settings can export the enabled local control boundary and the required enterprise next steps. | Improves staging readiness and makes desktop limitations explicit. |
| **Windows release pipeline** | A GitHub Actions workflow validates the app on Windows and builds `EcoPulse.exe` on a Windows runner. A version tag creates a release. | Makes builds reproducible and avoids unreliable cross-platform binary generation. |

## Why these product choices

Economic data products compete on breadth, release awareness, methodology, scenario capability and delivery—not merely chart polish. Trading Economics documents APIs for historical indicators, live calendar updates, markets and forecasts, while Moody’s positions alternative economic scenarios as the basis for *what-if* risk-management and planning analysis.[1][2] EcoPulse therefore prioritizes source-aware monitoring, alert rules, transparent stress inputs and a clear route to licensed feeds.

The current application starts from a public macro-data connector. The World Bank Indicators API documents programmatic access to almost 16,000 time-series indicators and does not require an API key; this is appropriate for a desktop starter edition, but it does **not** confer rights to redistribute proprietary real-time market, calendar or forecast data.[3] FRED remains a strong optional provider for series metadata, releases and vintage/revision-aware analysis because its API exposes observation, release-date and vintage-date endpoints.[4]

## Architecture

```text
+-------------------------+       +-----------------------------+
| Native Windows desktop  |       | Provider layer              |
| PySide6 + pyqtgraph     |<----->| World Bank live connector   |
| Command Center          |       | Deterministic offline cache |
| Intelligence Desk       |       | Future licensed adapters    |
| Scenario Studio         |       +-----------------------------+
+------------+------------+
             |
             v
+-------------------------+
| Local governed workspace|
| SQLite: alert rules     |
| scenarios, audit events |
| provenance-rich export  |
+-------------------------+
```

The application separates user-facing analytics from source acquisition and local storage. There is no hard-coded data-provider key, no remote synchronization in this edition and no hidden claim that synthetic fallback data is a live market observation. The source status badge and provenance panel are explicit by design.

## Run locally

Install Python 3.12 or newer, then run the following from the repository root.

```bash
python -m pip install -r requirements.txt
python main.py
```

The desktop app uses an active internet connection only while retrieving public source data. If the provider cannot be reached, it remains usable with labelled, deterministic fallback series. It stores the local workspace under `%APPDATA%\EcoPulse` on Windows.

## Build `EcoPulse.exe` on Windows

Run the included build script from a 64-bit Windows terminal:

```bat
build_windows.bat
```

The executable is written to `dist\EcoPulse.exe`. The app is intentionally built **on Windows**. PyInstaller bundles for the active operating system and interpreter architecture; its documentation specifies that distributions for a different operating system or architecture must be created on that target platform.[5]

> The executable produced by the automated workflow is a functional package, not a code-signed enterprise installer. Before external commercial distribution, sign the binary and installer with the organization’s Windows code-signing certificate, perform malware scanning and publish checksums.

## Automated validation and release

`.github/workflows/windows-release.yml` implements the controlled pipeline below.

| Trigger | What happens | Output |
| --- | --- | --- |
| Pull request or manual workflow dispatch | Installs locked requirements, executes the offline smoke test and builds on `windows-latest`. | Downloadable CI artifact `EcoPulse-Windows`. |
| Push a version tag such as `v1.1.0` | Performs the same validation and packages `EcoPulse.exe`; then creates a GitHub release using the tag. | GitHub Release with `EcoPulse.exe` attached. |

The workflow deliberately runs the packager on Windows. Qt for Python also documents `pyside6-deploy` as a deployment option that emits an `.exe` on Windows; its configuration is a viable later alternative for a Nuitka-based hardened build.[6]

## Secure deployment boundary

This edition makes a distinction between **product-ready foundations** and **enterprise infrastructure**.

| Included now | Required before regulated or multi-user production |
| --- | --- |
| Local SQLite audit events and saved scenario payloads. | Central immutable audit service, retention schedules and legal holds. |
| Credential-free public source integration and clear provenance. | Approved vendor contracts, entitlement checks, request metering and data-licensing governance. |
| Local desktop workspace without remote transmission. | OIDC/SAML authentication, role-based permissions, SCIM provisioning and tenant isolation. |
| Transparent heuristic scenario calculations with user-specified shocks. | Validated forecasting models, model registry, reviewer sign-off, performance monitoring and model-risk controls. |
| CSV evidence export. | Controlled PDF/Excel templates, watermarking, export policy enforcement and DLP integration. |

No personal or provider credentials are included in this source tree. If optional licensed feeds are introduced, retrieve their credentials through the organization’s approved secret manager or secure identity broker; never commit them to Git or embed them in a desktop binary.

## Commercial feature backlog

The following roadmap extends the delivered foundation in commercially meaningful layers.

| Horizon | Features | Outcome |
| --- | --- | --- |
| **Next release** | Economic-release calendar adapter, user-configurable country sets, custom watchlists, multi-series overlays, alert notifications, Excel export, data-vintage display and automatic update checks. | Replaces manual monitoring workflows for analysts. |
| **Professional edition** | Licensed data-vendor adapters, forecast-consensus comparison, attribution-aware research notes, saved chart templates, report generator, presentation export, multi-language support and organization policy configuration. | Enables paid analyst and planning workflows. |
| **Enterprise edition** | SSO, RBAC, SCIM, shared workspaces, approval chains, central audit, policy engine, encrypted managed settings, data entitlements, model registry and managed updater. | Supports controlled deployment inside larger organizations. |
| **Differentiated intelligence layer** | Nowcasting, release-surprise scoring, macro-regime classifier with feature explanations, scenario library, assumption versioning, supply-chain/industry exposure maps and API/SDK access. | Builds a defensible product moat beyond dashboard visualization. |

## Suggested commercial packaging

| Edition | Primary user | Package boundary |
| --- | --- | --- |
| **Analyst** | Individual researcher or planner | Command Center, public data, local alerts, scenario studio, local export. |
| **Professional** | Team lead or research desk | Licensed vendor connectors, shared templates, research/report generation and managed deployment. |
| **Enterprise** | Financial institution, corporation or public-sector organization | SSO/RBAC, centralized governance, private deployment, entitlements, audit and model governance. |

## Quality controls

The repository contains an offline smoke test that validates fallback series, local persistence, Data Health scoring, Scenario Library rendering, Evidence Pack integrity, application construction, source-rendering, metric cards and scenario logic without requiring a live provider. A visual QA record and screenshot are stored under `docs/visual_qa.md` and `assets/` respectively.

Run the smoke test manually with:

```bash
QT_QPA_PLATFORM=offscreen python tests/smoke.py
```

## Repository migration note

The original project was a small browser-hosted Dash application whose current signals were produced by `numpy.random`. EcoPulse Desktop deliberately changes the product boundary: it is a native application with a provider interface, offline continuity, local governance primitives and a release build pipeline. The original Dash file is not deleted by this migration plan; it can remain available as an experimental web demo or be retired after the desktop release is accepted.

## References

[1] [Trading Economics API — indicators, calendar, markets, financials and forecasts](https://tradingeconomics.com/api/)

[2] [Moody’s Analytics — Economic Scenarios](https://www.economy.com/products/alternative-scenarios/standard-scenarios)

[3] [World Bank — About the Indicators API Documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation)

[4] [Federal Reserve Bank of St. Louis — FRED API](https://fred.stlouisfed.org/docs/api/fred/)

[5] [PyInstaller — Operating Mode and platform-specific bundles](https://pyinstaller.org/en/stable/operating-mode.html)

[6] [Qt for Python — `pyside6-deploy`](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html)
