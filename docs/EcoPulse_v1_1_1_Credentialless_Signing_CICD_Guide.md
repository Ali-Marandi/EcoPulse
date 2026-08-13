# راهنمای راه‌اندازی CI/CD امضای credentialless برای EcoPulse

**وضعیت:** الگوی آماده پیاده‌سازی؛ تا زمان پیکربندی environment و provider، workflow به‌صورت manual-only باقی می‌ماند.
**فایل اصلی:** `.github/workflows/signed-windows-release.yml`

## هدف

Workflow امضای EcoPulse از private key، فایل PFX و client secret استفاده نمی‌کند. job امضا در یک GitHub environment محافظت‌شده اجرا می‌شود و از OIDC برای دریافت توکن کوتاه‌عمر provider بهره می‌گیرد. GitHub بیان می‌کند که OIDC نیاز به credential بلندمدت در repository را حذف می‌کند و token برای همان job صادر می‌شود.[1]

## پیش‌نیازهای یک‌باره

| مرحله | مالک | اقدام |
|---|---|---|
| 1. Provider | Security | یک Artifact Signing account و certificate profile ایجاد کنید؛ private key فقط در provider/HSM باقی بماند. |
| 2. هویت workload | Cloud Identity | یک application/service principal بسازید و GitHub OIDC issuer را به‌عنوان federated credential ثبت کنید. |
| 3. Trust policy | Cloud Identity + Security | subject را به repository `Ali-Marandi/EcoPulse`، environment `production-signing` و tagهای نسخه محدود کنید. |
| 4. Role | Cloud Identity | فقط نقش `Artifact Signing Certificate Profile Signer` را به workload بدهید.[2] |
| 5. GitHub environment | Repository Admin | environment `production-signing` ایجاد کنید؛ reviewer اجباری، جلوگیری از self-review و tag policy `v*` را فعال کنید.[3] |
| 6. Variables | Repository Admin | شناسه‌های غیرحساس زیر را در environment variables تنظیم کنید؛ از secret فقط در صورت وجود credential واقعاً حساس استفاده کنید. |
| 7. Dry run | Release Engineering | یک tag آزمایشی immutable بسازید، workflow را دستی اجرا و evidence را بازبینی کنید. |

## Environment variables موردنیاز

| نام | حساسیت | نمونه ساختار |
|---|---|---|
| `AZURE_CLIENT_ID` | شناسه، غیرحساس | GUID application registration |
| `AZURE_TENANT_ID` | شناسه، غیرحساس | GUID tenant |
| `AZURE_SUBSCRIPTION_ID` | شناسه، غیرحساس | GUID subscription |
| `SIGNING_ENDPOINT` | configuration | `https://<region>.codesigning.azure.net/` |
| `SIGNING_ACCOUNT_NAME` | configuration | نام signing account |
| `SIGNING_CERTIFICATE_PROFILE` | configuration | نام certificate profile |
| `SIGNING_SUBJECT_CONTAINS` | policy | بخشی از subject قانونی ناشر |

> **ممنوع:** `AZURE_CLIENT_SECRET`، PFX، password گواهی و private key را در repository، GitHub variable، GitHub secret عمومی، artifact یا log قرار ندهید. از OIDC استفاده کنید.

## اجرای workflow

1. تغییرات release را merge و آزمون‌ها را کامل کنید.
2. یک tag immutable مانند `v1.1.2` بسازید. هرگز tag منتشرشده را جابه‌جا نکنید.
3. از Actions، workflow **Signed Windows release** را با مقدار `release_tag=v1.1.2` شروع کنید.
4. reviewer محیط `production-signing` evidence build را بررسی و job امضا را تأیید می‌کند.
5. workflow به‌ترتیب build، scan پیش از امضا، امضای SHA-256 همراه با timestamp RFC 3161، verify signature، scan پس از امضا و انتشار evidence را اجرا می‌کند.
6. Release Manager، `EcoPulse.exe.release-manifest.json`، `EcoPulse.exe.sha256`، provenance و گزارش scan را بررسی و سپس promotion Canary را آغاز می‌کند.

## خروجی‌های الزامی Release

| خروجی | کاربرد |
|---|---|
| `EcoPulse.exe` | artifact امضاشده برای distribution compatibility |
| `EcoPulse.exe.sha256` | تطبیق integrity توسط مشتری/IT |
| `EcoPulse.exe.release-manifest.json` | subject، fingerprint، timestamp presence و SHA-256 |
| `provenance.json` | tag، commit، run و metadata build |
| `python-dependencies.txt` | dependency evidence اولیه؛ در milestone بعدی به SBOM رسمی ارتقا یابد |
| Defender reports | evidence scan پیش و پس از امضا |

## کنترل‌های عملیاتی

* workflow به‌طور عمدی فقط `workflow_dispatch` و `workflow_call` دارد. پس از تکمیل dry run و تصویب Security می‌توان trigger tag را در pull request جداگانه فعال کرد.
* workflow ابتدا artifact unsigned می‌سازد و سپس فقط job دوم در environment محافظت‌شده اجازه signing و publication دارد.
* job امضا باید به Windows runner اجرا شود؛ action رسمی Azure Artifact Signing فقط Windows runner را پشتیبانی می‌کند.[2]
* Verify با `Get-AuthenticodeSignature` و وجود TimeStamperCertificate انجام می‌شود؛ بنابراین امضای بدون timestamp رد خواهد شد.
* هر error در scan، signing یا verify باید workflow را fail کند و upload artifact به Release را متوقف سازد.

## rollback و پاسخ به incident

اگر signature invalid، hash mismatch یا compromise مشکوک رخ دهد، Stable feed را pause کنید، release را حذف/replace نکنید، artifact را با digest ثبت‌شده قرنطینه کنید و patch version جدید بسازید. اگر rollback عملکردی لازم باشد، MSIX N-1 در channel نگهداری شود و transition rollback در telemetry ثبت گردد.

## منابع

[1]: https://docs.github.com/en/actions/concepts/security/openid-connect "GitHub Docs — OpenID Connect"
[2]: https://github.com/Azure/artifact-signing-action "Azure Artifact Signing Action — README"
[3]: https://docs.github.com/actions/deployment/targeting-different-environments/using-environments-for-deployment "GitHub Docs — Managing environments for deployment"
