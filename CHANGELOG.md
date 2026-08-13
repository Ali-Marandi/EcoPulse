# Changelog

## Unreleased — Decision Readiness and Audit Integrity Candidate

### Added

- **Decision Readiness Gate** که Data Health، داده fallback/unavailable و alertهای فعال را به سه وضعیت شفاف `READY FOR REVIEW`، `REVIEW REQUIRED` و `BLOCKED` تبدیل می‌کند. این gate توصیه سرمایه‌گذاری یا جایگزین approval انسانی نیست.
- **Tamper-evident Local Audit Chain** برای رخدادهای جدید workspace، با زنجیره SHA-256 قابل‌راستی‌آزمایی، تشخیص break و نمایش وضعیت یکپارچگی در Workspace.
- **Evidence Pack افزوده‌شده** شامل decision readiness، audit integrity، شمار رخدادهای زنجیره‌شده و latest chain hash.
- **Evidence Pack Verifier** که checksum canonical SHA-256 هر Evidence Pack EcoPulse را در رابط Workspace محاسبه می‌کند و هرگونه تغییر در payload را آشکار می‌سازد.
- **Scenario Governance Ledger** که scenarioهای ذخیره‌شده را با assumptions، risk state، decision-readiness و digest snapshot داده versioned می‌کند؛ export آن شامل checksum هر record و checksum کل ledger است و قابلیت verification مستقل دارد.
- **حفاظت release hardening** در workflow پیشنهادی credentialless signing: job امضا اکنون tag را checkout می‌کند و SHA واقعی build را با provenance پیش از امضا تطبیق می‌دهد.
- پوشش smoke test برای readiness gate، hash-chain audit و evidence integrity افزوده شد.

### Release boundary

این تغییرات فقط در workspace محلی آماده شده‌اند و هنوز به GitHub push، tag یا Release عمومی تبدیل نشده‌اند.

## 1.1.0 — Commercial Evidence Foundations

### Added

- **Data Health lens** برای هر شاخص فعال، شامل حالت live/fallback، تعداد مشاهده و امتیاز شفاف آمادگی داده.
- **Scenario Library** پویا که سناریوهای ذخیره‌شده را همراه با کشور، shock summary و زمان ذخیره از workspace محلی نمایش می‌دهد.
- **Decision Evidence Pack** با فرمت JSON شامل data lineage، data health، latest observations، سناریو، alerts، audit events و checksum استاندارد SHA-256.
- **Local Guardrails Manifest** قابل‌صادرات که مرزهای فعلی desktop، کنترل‌های فعال و نیازهای Enterprise control plane را به‌روشنی مستند می‌کند.
- پوشش smoke test برای persistence، Data Health، Scenario Library و integrity Evidence Pack.
- کنترل کیفیت بصری اختصاصی برای صفحه Workspace و Evidence Pack.

### Fixed

- اتصال‌های SQLite اکنون پس از هر عملیات به‌طور صریح commit و بسته می‌شوند تا cleanup موقت در Windows runner با خطای `WinError 32` مواجه نشود.

### Changed

- نسخه برنامه به `1.1.0` افزایش یافت.
- جدول‌های پویا پس از refresh به‌صورت صحیح از parent جدا می‌شوند تا هم‌پوشانی visual در Workspace، Audit، Benchmark و Scenario Studio رخ ندهد.
- مستندات محصول به‌روزرسانی شد تا محدودیت‌های local-only و مرزهای دقیق مسیر Enterprise را روشن کند.

### Security and compliance boundary

این نسخه به‌صورت محلی evidence و manifest تولید می‌کند؛ **مدعی گواهی SOC 2 یا GDPR نیست**. قابلیت‌هایی نظیر SSO/RBAC، policy engine سمت سرور، tenant isolation، central immutable ledger، human approval و entitlement broker باید در Control Plane نسخه ۲.۰ پیاده‌سازی شوند.

### Validation

- آزمون دود آفلاین: موفق.
- کنترل کیفیت بصری Workspace/Evidence Pack: موفق؛ هم‌پوشانی جدول‌ها رفع شد.

## Release guidance

برای انتشار عمومی، کد را ابتدا در یک commit مستقل بررسی کنید، سپس تگ `v1.1.0` ایجاد کنید. گردش‌کار Windows CI باید روی runner ویندوزی، آزمون دود و build فایل `EcoPulse.exe` را اجرا کند. قبل از توزیع تجاری، checksum، امضای کد Windows و malware scanning را انجام دهید.
