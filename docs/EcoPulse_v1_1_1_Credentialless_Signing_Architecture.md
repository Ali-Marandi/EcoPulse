# معماری فنی Credentialless Signing در GitHub Actions برای EcoPulse

**دامنه:** امضای artifactهای Windows EcoPulse در GitHub Actions با Microsoft Entra Workload Identity Federation و Azure Artifact Signing
**وضعیت:** الگوی پیاده‌سازی محلی و آماده پیکربندی؛ تا زمانی که federation، environment policy و profile امضا واقعاً ساخته نشده‌اند، هیچ artifact موجود را نباید «امضاشده» تلقی کرد.

## 1. مسئله‌ای که حل می‌شود

در مدل سنتی، private key یا فایل PFX به‌صورت secret در CI نگه‌داری می‌شود. این مدل یک target با ارزش برای exfiltration، misuse و خطای operational است. در مدل credentialless، GitHub برای همان job یک JWT کوتاه‌عمر OIDC صادر می‌کند؛ `azure/login` آن JWT را نزد Microsoft Entra با یک access token کوتاه‌عمر مبادله می‌کند؛ و Azure Artifact Signing تنها با همان identity مجاز، digest فایل را با کلید محافظت‌شده در سرویس signing امضا می‌کند. GitHub تصریح می‌کند که `id-token: write` فقط اجازه درخواست OIDC token را می‌دهد و خودبه‌خود permission نوشتن روی resourceهای cloud ایجاد نمی‌کند.[1]

> **نتیجه:** یک binary تجاری می‌تواند امضا شود، بدون اینکه private key، PFX یا `AZURE_CLIENT_SECRET` در repository، log، GitHub secret یا Windows runner قرار گیرد.

## 2. زنجیره اعتماد end-to-end

| گام | مؤلفه | ورودی اعتماد | کنترل اصلی | خروجی |
|---:|---|---|---|---|
| 1 | Release Manager | tag `vX.Y.Z` | tag versioned و immutable | درخواست build |
| 2 | `build-and-validate` | tag checkout | آزمون دود آفلاین + build تکرارپذیر | `EcoPulse.exe` unsigned candidate |
| 3 | Provenance | SHA واقعی `git rev-parse HEAD` | اتصال candidate به tag و commit واقعی | `provenance.json` |
| 4 | GitHub environment | job امضا | reviewer، منع self-review و محدودیت tag | اجازه ورود به signing job |
| 5 | GitHub OIDC issuer | `id-token: write` | JWT job-scoped با subject محدود | OIDC JWT |
| 6 | Microsoft Entra | federated credential | تطبیق issuer، audience و subject | Azure access token کوتاه‌عمر |
| 7 | Artifact Signing | role assignment | فقط نقش Certificate Profile Signer | امضای SHA-256 + RFC 3161 timestamp |
| 8 | Verify و Defender | EXE نهایی | Authenticode، timestamp، hash و scan پس از امضا | manifest و checksum |
| 9 | Release | evidence نهایی | artifact + evidence به همان tag | release قابل‌ممیزی |

## 3. گردش اجرایی workflow EcoPulse

### 3.1 ساخت candidate و اثبات منشأ

job `build-and-validate` روی `windows-2025` ابتدا فقط tag منطبق با الگوی `v<major>.<minor>.<patch>` را می‌پذیرد. سپس همان tag را checkout می‌کند، وابستگی‌ها را نصب می‌کند، smoke test مناسب ساختار مخزن را اجرا می‌کند و `EcoPulse.exe` را می‌سازد. پیش از upload candidate، workflow مقدار واقعی `git rev-parse HEAD` را در `provenance.json` ذخیره و به‌عنوان output job منتشر می‌کند.

این تفکیک مهم است: `github.sha` در workflow دستی ممکن است context branch یا caller را نشان دهد، اما `git rev-parse HEAD` پس از checkout tag، commit مورد ساخت را نمایندگی می‌کند. در job امضا، همان tag دوباره checkout می‌شود و SHA آن باید با SHA ثبت‌شده در provenance برابر باشد؛ در غیر این صورت job متوقف می‌شود. بنابراین یک artifact از tag A با کنترل‌های tag B منتشر نخواهد شد.

### 3.2 گیت محیط امضا

job `sign-verify-and-publish` به environment با نام `production-signing` متصل است. قبل از دسترسی job به variables و قبل از شروع deployment، protection ruleهای environment می‌توانند reviewer الزامی، جلوگیری از self-review و restriction روی branch/tag اعمال کنند.[1] در EcoPulse این environment باید فقط tagهای `v*` و reviewerهای مستقل Security/Release Engineering را بپذیرد.

این کنترل OIDC را تکمیل می‌کند. OIDC به‌تنهایی اثبات می‌کند که یک job از یک context مشخص آمده است؛ environment protection تعیین می‌کند کدام job مجاز است به آن context حساس ارتقا یابد.

### 3.3 صدور و مبادله OIDC token

سطح permission job فقط دو مقدار لازم را دارد: `contents: write` برای attach کردن evidence به Release و `id-token: write` برای گرفتن JWT. GitHub بر اساس context job یک JWT صادر می‌کند. Microsoft Entra برای application یا user-assigned managed identity یک **federated identity credential** دارد که issuer GitHub، audience و subject را بررسی می‌کند.[1] فقط اگر این assertions با policy هم‌خوان باشند، Entra یک access token کوتاه‌عمر می‌دهد.

مقادیر `AZURE_CLIENT_ID`، `AZURE_TENANT_ID` و `AZURE_SUBSCRIPTION_ID` که در environment variables قرار می‌گیرند، secret key نیستند؛ آن‌ها شناسه‌های مسیریابی identity هستند. Azure Login از آن‌ها برای مبادله token بهره می‌گیرد. پیکربندی رسمی Azure نیز ایجاد Entra application/service principal، افزودن federated credential و اعطای role حداقلی را پیشنهاد می‌کند.[2]

## 4. Trust policy پیشنهادی

| Claim/Control | مقدار یا قاعده پیشنهادی | دلیل |
|---|---|---|
| Issuer | `https://token.actions.githubusercontent.com` | پذیرش صرفاً tokenهای GitHub Actions |
| Audience | `api://AzureADTokenExchange` در Azure Public Cloud | audience پیشنهادی GitHub/Azure برای token exchange [1] |
| Subject | repository `Ali-Marandi/EcoPulse` + environment `production-signing` | جلوگیری از reuse توسط repository یا environment دیگر |
| Repository visibility/ID | در صورت دسترس، claim immutable repository owner ID و repository ID | جلوگیری از اثر rename/transfer و impersonation نام |
| Ref | tag release محافظت‌شده `v*` | جلوگیری از signing از branch یا PR غیرمجاز |
| Role | `Artifact Signing Certificate Profile Signer` فقط روی account/profile لازم | حداقل‌سازی سطح دسترسی [3] |
| Environment | reviewer اجباری و منع self-review | کنترل انسانی قبل از استفاده از identity حساس |

GitHub از 15 ژوئیه 2026 برای repositoryهای تازه و انتقال/renameهای جدید، claim پیش‌فرض immutable مبتنی بر owner/repository ID را توصیه می‌کند؛ مخزن‌های قدیمی باید migration آن را در برنامه hardening خود بررسی کنند.[1]

## 5. چرا `azure/login` پیش از action امضا اجرا می‌شود

`azure/login@v3` JWT دریافتی از issuer GitHub را نزد Microsoft Entra مبادله و session Azure CLI job را با access token کوتاه‌عمر آماده می‌کند. Azure Artifact Signing action از `DefaultAzureCredential` استفاده می‌کند. در workflow EcoPulse، credentialهای محیطی، managed identity، cache توسعه‌دهنده و interactive browser عمداً غیرفعال‌اند؛ تنها Azure CLI credential که از `azure/login` آمده فعال می‌ماند. این پیکربندی ambiguity credential را کاهش می‌دهد و action را از fallback ناخواسته به user credential یا secret-based authentication دور می‌کند.[3]

## 6. عملیات امضا و timestamp

Azure Artifact Signing action فقط روی Windows runnerهای پشتیبانی‌شده اجرا می‌شود.[4] Action فایل `release\EcoPulse.exe` را با digest `SHA256` به service ارسال می‌کند، certificate profile تعیین‌شده را استفاده می‌کند و امضای Authenticode به همراه timestamp RFC 3161 تولید می‌کند. مستند action، timestamp server و digest `SHA256` را برای معتبر ماندن امضا پس از دوره کوتاه اعتبار service توصیه می‌کند.[4]

پس از امضا، `verify-signed-artifact.ps1` سه شرط را fail-closed بررسی می‌کند: وضعیت Authenticode باید `Valid` باشد؛ subject امضا باید با مقدار policy مورد انتظار تطبیق داشته باشد؛ و timestamp certificate باید وجود داشته باشد. سپس checksum SHA-256 و `release-manifest.json` ساخته می‌شود. این manifest evidence قابل‌بررسی برای Release Manager و مشتری سازمانی است، نه جایگزین verification روی endpoint مشتری.

## 7. کنترل‌های supply-chain پیرامونی

| کنترل | جایگاه | تهدیدی که کاهش می‌دهد |
|---|---|---|
| smoke test و build از tag | پیش از signing | binary معیوب یا build خارج از release reference |
| pre-sign Defender scan | candidate | آلودگی پیش از تماس با signing provider |
| post-sign Defender scan | EXE نهایی | اختلاف artifact یا آلودگی پس از transformation |
| Authenticode verify + expected subject | پس از signing | امضای نامعتبر یا identity اشتباه |
| SHA-256 + release manifest | release evidence | خطای دانلود و نبود traceability |
| 365-day evidence retention | artifact retention | نبود مدارک برای audit یا investigation |
| Canary/MSIX rollout | پس از انتشار | گسترش سریع defect به کل نصب‌ها |

## 8. مراحل setup عملیاتی

1. یک Entra application و service principal ایجاد کنید.
2. در Azure، federated identity credential را با issuer GitHub، audience مناسب و subject محدود به environment `production-signing` بسازید.
3. روی Artifact Signing Account یا Certificate Profile، فقط role `Artifact Signing Certificate Profile Signer` را به همان principal واگذار کنید.[3]
4. در GitHub، environment `production-signing` را بسازید و reviewer اجباری، منع self-review و policy tag را فعال کنید.
5. environment variables غیرحساس workflow را قرار دهید: `AZURE_CLIENT_ID`، `AZURE_TENANT_ID`، `AZURE_SUBSCRIPTION_ID`، endpoint، account، certificate profile و expected signing subject.
6. با یک tag آزمایشی immutable و certificate profile non-production، workflow را دستی اجرا کنید. سپس manifest، hash، signer subject، timestamp، Defender reports و SHA تطبیق tag را review کنید.
7. پس از تصویب Security، فقط trigger و promotion policy را با pull request جداگانه فعال کنید. Automation نباید جای approval را بگیرد.

## 9. مرزهای مهم و ریسک‌های باقی‌مانده

Credentialless به معنی «بدون identity» نیست؛ به معنی «بدون secret بلندمدت قابل‌استفاده برای login» است. اگر trust policy بسیار باز باشد، یک job ناخواسته هم می‌تواند token بگیرد. اگر environment protection ضعیف باشد، reviewer bypass می‌شود. اگر actionها به tag mutable وابسته باشند، supply-chain risk باقی می‌ماند. در milestone بعدی، actionهای third-party باید به SHA کامل pin شوند، workflow تغییرات نیازمند CODEOWNERS باشند، tag protection واقعی اعمال شود و SBOM استاندارد CycloneDX یا SPDX به release evidence اضافه گردد.

## منابع

[1]: https://docs.github.com/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure "GitHub Docs — Configuring OpenID Connect in Azure"
[2]: https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect "Microsoft Learn — Use Azure Login action with OpenID Connect"
[3]: https://github.com/Azure/artifact-signing-action/blob/main/docs/OIDC.md "Azure Artifact Signing Action — OIDC authentication guide"
[4]: https://github.com/marketplace/actions/artifact-signing "GitHub Marketplace — Azure Artifact Signing action"
