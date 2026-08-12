# Changelog

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
