# طرح تفصیلی Auto-update Rollout Telemetry برای EcoPulse

**نسخه:** 1.0
**مخاطب:** Product Operations، Security، SRE، Customer Success و IT مشتریان سازمانی
**دامنه:** کانال‌های MSIX/App Installer، Intune، Configuration Manager، WinGet و نصب آفلاین کنترل‌شده

## 1. هدف و اصل طراحی

Telemetry به‌روزرسانی EcoPulse باید به تیم انتشار پاسخ دهد که «چه نسخه‌ای، برای کدام کانال، روی چه نسبتی از نصب‌ها، با چه نرخ موفقیت و چه نوع خطاهایی deploy شده است»؛ بدون اینکه داده اقتصادی، نام کاربر، hostname، آدرس IP، مسیر فایل، عنوان workspace یا شناسه سخت‌افزار جمع‌آوری شود. بنابراین محصول باید **رویداد حداقلی، pseudonymous، tenant-scoped و قابل‌خاموش‌سازی** تولید کند.

> **قاعده داده:** Telemetry برای کنترل کیفیت انتشار است، نه برای مشاهده رفتار تحلیل‌گر. هر فیلدی که برای تصمیم rollout یا تشخیص خطای update لازم نیست، از event حذف می‌شود.

App Installer امکان بررسی در زمان launch، بررسی پس‌زمینه، fallback Update URI و کنترل رفتار prompt/activation را فراهم می‌کند؛ سیاست‌های Intune نیز می‌توانند آن را بر مبنای tenant اعمال کنند.[1] [2] از این رو، داده‌های rollout باید بین channel محصول و کنترل‌پلین IT مشتری تفکیک شوند.

## 2. معماری مرجع

```text
EcoPulse Desktop / App Installer / Intune event
                 |
                 v
       Local encrypted event queue
       (bounded; 7-day TTL; retry with backoff)
                 |
                 v
       Tenant-scoped HTTPS ingestion endpoint
       (mTLS or scoped token; schema validation)
                 |
                 +--> Immutable raw event store (access controlled)
                 +--> Aggregation job: version × channel × tenant pseudonym
                 +--> Rollout policy engine: promote / hold / rollback
                 +--> Executive dashboard and technical incident dashboard
```

Telemetry endpoint باید یک خدمت مستقل از API داده‌های اقتصادی باشد. failure endpoint نباید update را block کند؛ رویدادها locally queue می‌شوند و retry bounded انجام می‌دهند. اگر queue پس از TTL کامل نشد، رویداد حذف شود و فقط یک شمارنده محلی `telemetry_dropped` نگه‌داری شود. هیچ رویدادی نباید موجب background process دائمی خارج از سیاست IT مشتری شود.

## 3. قرارداد event و حریم خصوصی

فایل پیوست `telemetry/update-event.schema.json` قرارداد اجرایی event را تعریف می‌کند. نصب باید یک `installation_pseudonym` تصادفی و چرخشی بسازد؛ این شناسه نباید از hostname، SID، MAC address، serial number، نام کاربر، ایمیل یا داده‌ سخت‌افزاری مشتق شود. `tenant_pseudonym` نیز باید opaque باشد یا برای نصب unmanaged مقدار `unmanaged` بگیرد.

| دسته | مجاز | ممنوع |
|---|---|---|
| وضعیت انتشار | channel، نسخه مبدأ/مقصد، منبع update، نتیجه | عنوان release خصوصی یا branch نامشخص |
| پایداری | duration، error class استاندارد، correlation ID | stack trace خام، مسیر فایل، dump حافظه بدون رضایت |
| محیط | Windows release عمومی، architecture | hostname، IP، user name، شناسه سخت‌افزار |
| tenancy | pseudonym tenant | نام قانونی مشتری، domain، email، customer data |
| امنیت | SHA-256 release و نتیجه signature verify | certificate private data، token، URL دارای credential |

### رویدادهای حداقلی

| رویداد | زمان تولید | کاربرد عملیاتی |
|---|---|---|
| `update_check_started` | آغاز بررسی version | نرخ check و تاخیر manifest را اندازه می‌گیرد. |
| `update_available` | نسخه جدید تشخیص داده شد | denominator واقعی rollout را مشخص می‌کند. |
| `update_download_completed` | artifact دریافت شد | جدا کردن خطای دانلود از نصب. |
| `update_signature_verified` | hash/signature معتبر شد | تشخیص خطای supply chain و policy. |
| `update_install_started` | نصب آغاز شد | اندازه‌گیری abandonment و install duration. |
| `update_install_succeeded` | installer موفق شد | numerator اصلی نرخ موفقیت نصب. |
| `first_launch_after_update` | نخستین launch موفق | معیار واقعی adoption سالم و crash-free start. |
| `update_install_failed` | نصب ناموفق شد | routing به error class و incident policy. |
| `rollback_started/succeeded` | بازگشت اجرا شد | کیفیت rollback و شدت انتشار را می‌سنجد. |

## 4. شاخص‌ها و فرمول‌ها

تمام thresholdهای این سند **پیشنهادی** هستند و باید با baseline داخلی EcoPulse و تعهدات قرارداد مشتری تنظیم شوند.

| شاخص | فرمول | هدف پیشنهادی | مالک |
|---|---|---:|---|
| نرخ بررسی موفق | `check_started بدون network/manifest failure ÷ check_started` | ≥ 99.5٪ | SRE |
| نرخ download موفق | `download_completed ÷ update_available` | ≥ 99٪ | Release Engineering |
| نرخ verify امضا | `signature_verified ÷ download_completed` | 100٪ | Security |
| نرخ نصب موفق | `install_succeeded ÷ install_started` | ≥ 98٪ Canary؛ ≥ 99٪ Stable | Product Ops |
| نرخ launch سالم | `first_launch_after_update ÷ install_succeeded` | ≥ 99٪ | Engineering |
| rollback rate | `rollback_succeeded ÷ install_succeeded` | < 0.5٪ | Release Manager |
| P95 زمان به‌روزرسانی | P95 از `download + install + first launch` | baseline-محور | SRE |
| coverage | `نصب‌های گزارش‌دهنده ÷ نصب‌های واجد شرایط rollout` | ≥ 95٪ برای managed tenant | Customer Success |
| signature/integrity failure | تعداد `signature_invalid` یا `hash_mismatch` | **صفر** | Security Incident Commander |

### طبقه‌بندی خطا

| کلاس خطا | مثال | اقدام خودکار |
|---|---|---|
| `network_dns/tls/timeout` | feed یا proxy در دسترس نیست | retry exponential، هشدار فقط در صورت عبور از baseline. |
| `manifest_invalid` | App Installer manifest نامعتبر | pause channel؛ بررسی CI و CDN. |
| `signature_invalid/hash_mismatch` | artifact با release manifest همخوان نیست | توقف فوری rollout، P1 security incident، revoke feed. |
| `policy_blocked/auth_required` | Intune/AppLocker یا policy tenant | به IT مشتری route شود؛ promotion عمومی متوقف نشود مگر trend گسترده باشد. |
| `disk_space/install_busy/install_denied` | endpoint readiness | remediation راهنمای کاربر/IT؛ monitor trend. |
| `package_conflict` | package قدیمی یا conflict MSI/MSIX | escalation به deployment engineering. |
| `rollback_required` | regression پس از launch | توقف channel و rollback controller. |

## 5. سیاست rollout و کنترل خودکار

EcoPulse باید ابتدا در حلقه‌های مشخص منتشر شود، نه هم‌زمان برای همه مشتریان. App Installer قابلیت check on launch و background update دارد؛ `UpdateBlocksActivation` فقط در update بحرانی باید به‌کار رود، زیرا launch معمول کاربر را متوقف می‌کند.[2]

| Ring | دامنه | مدت مشاهده حداقل | شرط promotion پیشنهادی | شرط pause/rollback |
|---|---:|---:|---|---|
| Internal | تیم EcoPulse | 24 ساعت | install ≥ 98٪؛ launch سالم ≥ 99٪؛ خطای integrity صفر | هر خطای integrity یا crash P1 |
| Canary | 5–10٪ eligible installs | 48 ساعت | install ≥ 98٪؛ rollback < 0.5٪؛ error trend پایدار | install failure > 2٪ یا rollback ≥ 0.5٪ |
| Controlled | 25–50٪ | 72 ساعت | install ≥ 99٪؛ P95 خارج از baseline نباشد | رشد معنادار هر error class |
| Stable | 100٪ tenantهای مجاز | پیوسته | SLOهای Stable برقرار | breach SLO یا incident امنیتی |

**ترتیب تصمیم:** Security integrity gate همیشه بر شاخص‌های رشد مقدم است. یک `signature_invalid` یا `hash_mismatch` تأییدشده باید صرف‌نظر از حجم rollout، feed را freeze کند. برای خطاهای availability، ابتدا retry و بررسی CDN انجام شود و سپس فقط همان channel متوقف گردد.

### State machine کنترل‌پلین

```text
DRAFT -> INTERNAL -> CANARY -> CONTROLLED -> STABLE
                    |              |             |
                    +----> HOLD <---+             |
                           |                       |
                           +----> ROLLBACK <-------+

SECURITY_INTEGRITY_FAILURE from any active state -> PAUSED + P1 INCIDENT
```

هر transition باید توسط policy engine ثبت شود و شامل `release_sha256`، version، channel، decision، actor/service، timestamp و دلیل باشد. تغییر مستقیم فایل App Installer یا feed بدون transition ثبت‌شده ممنوع است.

## 6. داشبورد و هشداردهی

### نمای مدیران ارشد

| کارت | نمایش | تصمیم پشتیبانی‌شده |
|---|---|---|
| وضعیت Ring | Internal/Canary/Controlled/Stable/Hold | آیا promotion ادامه یابد؟ |
| Adoption | درصد نصب‌های eligible که update سالم گرفتند | ارزش تحقق انتشار |
| سلامت انتشار | success، rollback، integrity error | نیاز به توقف یا سرمایه‌گذاری remediation |
| ریسک مشتری | tenantهای تحت‌تأثیر به‌صورت aggregate | اولویت Customer Success |
| SLA update | زمان P50/P95 و trend | ظرفیت CDN/installer و تجربه کاربر |

### نمای فنی

1. Funnel به‌روزرسانی از check تا first launch بر حسب `channel`، `from_version` و `to_version`.
2. Top error classها با rate و delta نسبت به baseline نسخه پیشین.
3. Heatmap نسخه Windows در برابر `install_failed`، بدون شناسه endpoint.
4. Integrity pane شامل SHA-256، signature verification، certificate subject و release manifest.
5. Queue health شامل retry، drop count و ingestion latency.

### آستانه هشدار

| Severity | Trigger | مالک اولیه | زمان اقدام پیشنهادی |
|---|---|---|---|
| P1 | hash/signature failure، نشانه compromise، rollback امنیتی | Security Incident Commander | فوری؛ freeze channel |
| P2 | install failure بالاتر از 2٪ در Canary یا trend سه برابر baseline | Release Manager | کمتر از 30 دقیقه |
| P3 | network error نرخ‌بالا یا P95 کندتر از baseline | SRE | همان روز کاری |
| P4 | coverage زیر هدف telemetry | Product Ops | برنامه بهبود در sprint بعد |

## 7. کیفیت داده و retention

* **Deduplication:** کلید `event_id` و `correlation_id + event_name` از شمارش تکراری در retry جلوگیری می‌کند.
* **Clock skew:** سرور ingestion زمان دریافت را جدا از `occurred_at_utc` ذخیره می‌کند؛ metrics حساس بر مبنای زمان سرور گزارش شوند.
* **Retention:** raw event حداکثر 30 روز؛ aggregate غیرقابل‌شناسایی 13 ماه؛ audit transition و security evidence طبق قرارداد و retention policy سازمان نگهداری شود.
* **Opt-out و managed policy:** مشتری managed باید بتواند telemetry را کامل خاموش، به gateway داخلی خود route، یا فقط metrics aggregate را ارسال کند. خاموش بودن telemetry هیچ‌گاه update امنیتی را غیرفعال نکند؛ تنها visibility را کاهش می‌دهد.
* **Data processing:** قبل از فعال‌سازی عمومی، Data Processing Inventory، notice محصول و DPA مشتری بازبینی شوند.

## 8. برنامه استقرار 30 روزه

| بازه | خروجی | معیار پذیرش |
|---|---|---|
| روز 1–5 | schema، taxonomy، retention و privacy review | هیچ PII یا customer content در event schema نیست. |
| روز 6–10 | local queue و ingestion sandbox | retry/dedup و TTL در fault test تأیید می‌شود. |
| روز 11–15 | dashboard internal و alert rules | integrity incident شبیه‌سازی‌شده channel را pause می‌کند. |
| روز 16–22 | internal ring با instrumentation | funnel کامل از check تا first launch قابل مشاهده است. |
| روز 23–30 | Canary با review روزانه | promotion یا hold مطابق threshold ثبت‌شده انجام می‌شود. |

## منابع

[1]: https://learn.microsoft.com/en-us/windows/msix/app-installer/auto-update-and-repair--overview "Microsoft Learn — Auto-update and repair apps"
[2]: https://learn.microsoft.com/en-us/windows/msix/app-installer/update-settings "Microsoft Learn — Configure update settings in the App Installer file"
[3]: https://learn.microsoft.com/en-us/windows/msix/desktop/managing-your-msix-deployment-enterprise "Microsoft Learn — MSIX App Distribution"
