# بررسی فنی SHA-256 Hash-Chain و Evidence Pack Verifier در EcoPulse

**دامنه:** قابلیت‌های local-first در commit پیشنهادی B
**هدف:** افزایش قابلیت تشخیص تغییر در رخدادهای workspace و Decision Evidence Pack، بدون ادعای ledger تغییرناپذیر مرکزی، non-repudiation یا certification.

## خلاصه اجرایی

EcoPulse دو کنترل مکمل را اضافه می‌کند. نخست، **Hash-Chain محلی** هر رخداد جدید audit را با هش رخداد پیشین پیوند می‌دهد؛ بنابراین تغییر، حذف یا درج مجدد یک رخداد در بخش زنجیره‌شده باید در هنگام verification آشکار شود. دوم، **Evidence Pack Verifier** هش SHA-256 محتوای canonical یک فایل evidence را دوباره محاسبه و با checksum ذخیره‌شده مقایسه می‌کند؛ بنابراین تغییر payload پس از export، در صورت باقی ماندن checksum اصلی، تشخیص داده می‌شود.

NIST توضیح می‌دهد که digestهای hash برای تشخیص تغییر پیام پس از تولید digest به‌کار می‌روند و SHA-256 حداقل پیشنهادی NIST برای interoperability در کاربردهای hash امن است.[1] [2] بااین‌حال، hash بدون کلید **هویت نویسنده یا منشأ مستقل** را ثابت نمی‌کند. OWASP میان hash، MAC و digital signature تفکیک می‌گذارد: MAC با کلید برای integrity و data-origin authentication به‌کار می‌رود و signature می‌تواند authentication، integrity و non-repudiation فراهم کند.[3]

> **نتیجه صحیح:** این قابلیت‌ها برای local evidence hygiene و تشخیص دستکاریِ بدون بازنویسی صحیح cryptographic state مناسب‌اند؛ اما جای HMAC با کلید محافظت‌شده، امضای دیجیتال، timestamp قابل‌اعتماد، storage append-only یا ledger مرکزی را نمی‌گیرند.

## 1. مدل داده Hash-Chain

جدول SQLite `events` در نسخه محلی شامل دو ستون افزوده‌شده است:

| ستون | معنای امنیتی | مقدار نمونه |
|---|---|---|
| `previous_hash` | هش رخداد زنجیره‌شده قبلی؛ برای نخستین رخداد `GENESIS` | `a7…f2` یا `GENESIS` |
| `event_hash` | SHA-256 رکورد canonical جاری شامل ارجاع به `previous_hash` | `d4…9b` |

مهاجرت کاملاً backward-compatible است. اگر workspace قدیمی موجود باشد، دو ستون با `ALTER TABLE` افزوده می‌شوند. رخدادهای قدیمی بدون `event_hash` به‌عنوان **legacy** شمارش می‌شوند و بازنویسی نمی‌شوند؛ رخدادهای جدید از نخستین ثبت پس از migration وارد chain می‌گردند. این انتخاب از تغییر retroactive تاریخچه اجتناب می‌کند.

### 1.1 فرمول رخداد

برای رخداد `i` با نوع `Tᵢ`، جزئیات `Dᵢ`، timestamp `Cᵢ` و هش پیشین `Hᵢ₋₁`، EcoPulse یک JSON canonical می‌سازد:

```text
Pᵢ = JSON_canonical({
  event_type: Tᵢ,
  details: Dᵢ,
  created_at: Cᵢ,
  previous_hash: Hᵢ₋₁
})

Hᵢ = SHA-256(UTF-8(Pᵢ))
```

Canonicalization در implementation فعلی با `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))` انجام می‌شود. `sort_keys=True` ترتیب کلیدها را پایدار می‌کند و separatorهای فشرده، تفاوت‌های صرفاً whitespace را از digest دور نگه می‌دارند. UTF-8 نیز representation متن را تعیین می‌کند.

### 1.2 نوشتن رخداد

هر `LocalStore.log()` این عملیات را انجام می‌دهد:

1. آخرین `event_hash` غیرخالی خوانده می‌شود؛ اگر وجود نداشته باشد، `GENESIS` انتخاب می‌شود.
2. payload canonical ساخته و SHA-256 محاسبه می‌شود.
3. `event_type`، `details`، `created_at`، `previous_hash` و `event_hash` در یک transaction SQLite ثبت می‌شوند.
4. session با commit و close صریح پایان می‌یابد؛ این همان policy سازگار با Windows است که در v1.1.1 برای جلوگیری از lock cleanup اعمال شد.

## 2. الگوریتم verification chain

`LocalStore.verify_audit_chain()` رخدادها را با ترتیب صعودی `id` می‌خواند و از `GENESIS` آغاز می‌کند. برای هر رخداد زنجیره‌شده، verifier سه کنترل دارد:

| کنترل | شرط | معنی شکست |
|---|---|---|
| پیوستگی | `previous_hash == prior` | حذف، درج یا جابه‌جایی رخداد در chain یا reference نادرست |
| صحت payload | `event_hash == SHA-256(canonical payload)` | تغییر در نوع، جزئیات، timestamp یا `previous_hash` |
| ترتیب | بررسی بر مبنای `id ASC` | chain باید با ترتیب append local ارزیابی شود |

در حالت موفق، verifier مقدارهای `verified=true`، `checked_events`، `legacy_events` و `latest_hash` را بازمی‌گرداند. در حالت شکست، `verified=false`، state `CHAIN BREAK DETECTED` و `failed_event_id` نمایش داده می‌شود. Workspace این نتیجه را به‌صورت badge مستقل نشان می‌دهد و Evidence Pack نیز همان نتیجه را حمل می‌کند.

## 3. مدل تهدید و محدودیت Hash-Chain

| سناریو | آیا پیاده‌سازی فعلی آن را آشکار می‌کند؟ | دلیل |
|---|---|---|
| تغییر یک `details` بدون تغییر hash | بله | محاسبه دوباره SHA-256 mismatch می‌دهد. |
| حذف یک رخداد زنجیره‌شده بدون بازنویسی رخداد بعدی | بله | `previous_hash` رخداد بعدی دیگر با prior تطبیق ندارد. |
| واردکردن رخداد میان دو رخداد بدون بازنویسی chain | بله | reference یا hash رخدادهای مرتبط mismatch می‌شود. |
| تغییر همزمان payload و `event_hash` همان رخداد | معمولاً بله، مگر chain بعدی نیز بازنویسی شود | رخداد بعدی هنوز به hash قدیمی اشاره می‌کند. |
| مهاجم با دسترسی نوشتن کامل به SQLite که همه hashها را از ابتدا بازنویسی کند | خیر | hash بدون کلید و بدون anchor خارجی قابل محاسبه مجدد است. |
| حذف کل فایل SQLite یا rollback به نسخه قدیمی | خیر | anchor خارج از دستگاه یا monotonic counter امضاشده وجود ندارد. |
| اثبات اینکه کاربر خاصی رخداد را ایجاد کرده است | خیر | local event chain identity-bound یا digitally signed نیست. |

بنابراین state `VERIFIED` باید به این معنا تفسیر شود: **رکوردهای زنجیره‌شده موجود با قواعد local hash-chain سازگارند.** این state نباید به معنای «تاریخچه از ابتدا غیرقابل‌تغییر» یا «یک طرف ثالث آن را تأیید کرده است» بیان شود.

### 3.1 مسیر ارتقای Enterprise

برای گذار به assurance قوی‌تر، مسیر زیر پیشنهاد می‌شود:

1. هر `latest_hash` به‌صورت دوره‌ای با HMACِ کلید نگه‌داری‌شده در HSM/KMS یا با امضای سازمانی seal شود.
2. sealها به یک event store append-only مرکزی با retention، legal hold و clock قابل‌اعتماد ارسال شوند.
3. هر Evidence Pack با identity کاربر، approval record و timestamp قابل‌اعتماد امضا شود.
4. یک verifier مستقل (CLI یا portal) integrity و signature chain را بدون نیاز به code client بررسی کند.
5. برای رویه‌های حساس، digest Evidence Pack و hash-chain head در یک ledger خارجی یا transparency log anchor شوند.

## 4. Evidence Pack Verifier

### 4.1 ایجاد Evidence Pack

`build_evidence_bundle()` داده‌های تصمیم شامل کشور، health، provenance، latest observations، scenario، alertها، readiness، audit integrity و audit events را در یک dictionary می‌سازد. سپس، **قبل از افزودن کلید `integrity`**، این object canonical می‌شود:

```text
C = JSON_canonical(bundle_without_integrity)
checksum = SHA-256(UTF-8(C))
bundle.integrity = {
  algorithm: "SHA-256",
  canonical_payload_sha256: checksum
}
```

جدا کردن `integrity` از payload ضروری است؛ در غیر این صورت checksum شامل خودش می‌شد و یک مسئله self-referential ایجاد می‌کرد.

### 4.2 verification فایل انتخاب‌شده

کاربر در Workspace گزینه **Verify an evidence pack** را انتخاب می‌کند. EcoPulse مراحل زیر را اجرا می‌کند:

1. فایل JSON خوانده می‌شود و schema `ecopulse.evidence-pack.v1` بررسی می‌شود.
2. فیلد `canonical_payload_sha256` باید یک string با طول 64 hexadecimal-character باشد.
3. تمام کلیدها به‌جز `integrity` به همان روش canonical می‌شوند.
4. SHA-256 جدید محاسبه می‌شود.
5. checksum جدید با checksum ذخیره‌شده مقایسه می‌شود.
6. نتیجه `valid`/`invalid`، digest محاسبه‌شده و علت در رابط نمایش داده و در local audit ثبت می‌شود.

این verifier تغییر در هر بخش تحت پوشش payload، مانند scenario، data health یا alerts، را تشخیص می‌دهد؛ smoke test نیز صریحاً یک فیلد scenario را پس از build تغییر می‌دهد و انتظار mismatch دارد.

## 5. حدود Evidence Pack Verifier

| ادعا | وضعیت |
|---|---|
| «این payload نسبت به checksum داخل همان فایل تغییر کرده است» | در صورت mismatch درست است. |
| «این فایل از همان EcoPulse client صادر شده است» | تضمین نمی‌شود؛ برای آن signature یا HMAC با کلید محافظت‌شده لازم است. |
| «فایل از export تا حالا تغییر نکرده است» | فقط وقتی یک digest مورداعتماد خارج از فایل یا signature وجود داشته باشد قابل اثبات است. |
| «داده‌های اقتصادی صحیح، به‌روز یا مجاز هستند» | تضمین نمی‌شود؛ Data Health و provenance باید جداگانه بررسی شوند. |
| «Evidence Pack مصوب یا legally admissible است» | تضمین نمی‌شود؛ approval workflow، retention و policy سازمانی لازم است. |

## 6. ارتباط دو کنترل با Decision Readiness Gate

Decision Readiness Gate بر کیفیت و وضعیت **ورودی تصمیم** تمرکز دارد: score Data Health، داده fallback/unavailable و alertهای فعال. Hash-Chain بر یکپارچگی **تاریخچه رویداد local** تمرکز دارد. Evidence Verifier بر یکپارچگی **فایل export شده** تمرکز دارد. این سه کنترل مکمل‌اند و هیچ‌یک دیگری را جایگزین نمی‌کند.

| کنترل | پرسش پاسخ‌داده‌شده | نمونه نتیجه |
|---|---|---|
| Decision Readiness | «آیا evidence باید پیش از اتکا توسط reviewer بررسی شود؟» | `REVIEW REQUIRED` |
| Audit Hash-Chain | «آیا رخدادهای زنجیره‌شده local با حالت cryptographic ذخیره‌شده سازگارند؟» | `VERIFIED` یا `CHAIN BREAK DETECTED` |
| Evidence Pack Verifier | «آیا payload این فایل با checksum داخل آن هم‌خوان است؟» | `valid` یا `invalid` |

## 7. Scenario Governance Ledger

Scenario Governance Ledger قابلیت محلی جدیدی است که سناریوهای ذخیره‌شده را به recordهای versioned تبدیل می‌کند. هر record شامل assumptions، `risk_score`، `risk_state`، state آمادگی تصمیم، نام مدل heuristic، نسخه برنامه و `data_snapshot_sha256` است. Snapshot digest از latest observations، provenance و Data Health در لحظه ذخیره سناریو ساخته می‌شود؛ بنابراین record نشان می‌دهد تصمیم با چه lineage داده‌ای ثبت شده است.

برای هر record، `record_sha256` از JSON canonical record بدون خود checksum ساخته می‌شود. سپس کل ledger شامل آرایه recordها، metadata application و limitations canonical می‌شود و `canonical_payload_sha256` سطح ledger برای آن محاسبه می‌گردد. verifier ابتدا checksum کل ledger و سپس checksum تک‌تک recordها را بررسی می‌کند. تغییر در payload یک record، حتی اگر checksum کل ledger بدون تغییر بماند، باید در مرحله record verification آشکار شود.

| سطح کنترل | پاسخ قابل‌ارائه | مرز |
|---|---|---|
| Scenario record | «آیا assumptions و decision context این record با checksum خودش سازگارند؟» | منشأ بیرونی یا approval سازمانی را ثابت نمی‌کند. |
| Ledger bundle | «آیا فهرست export‌شده scenarioها با checksum کل ledger سازگار است؟» | rollback کامل فایل یا بازنویسی همه checksumها را بدون anchor خارجی متوقف نمی‌کند. |
| Source snapshot digest | «کدام خلاصه lineage داده هنگام ذخیره سناریو استفاده شد؟» | داده را در ledger بازتولید یا صحت provider را تضمین نمی‌کند. |

## 8. معیارهای آزمون پیاده‌سازی فعلی

| آزمون | نتیجه مورد انتظار |
|---|---|
| ثبت چند رخداد جدید سپس `verify_audit_chain()` | `verified=true` و تعداد رخداد زنجیره‌شده مثبت |
| Data Health ناقص | Gate در حالت `BLOCKED` |
| همه شاخص‌ها fallback با alert فعال | Gate در حالت `REVIEW REQUIRED` |
| Evidence Pack تازه ساخته‌شده | `verify_evidence_bundle(...).valid=true` |
| تغییر فیلد scenario پس از checksum | `verify_evidence_bundle(...).valid=false` |
| Scenario Ledger تازه | `verify_scenario_ledger(...).valid=true` |
| تغییر risk score یک record | `verify_scenario_ledger(...).valid=false` |
| Smoke test headless | همه assertionها عبور کنند |

## منابع

[1]: https://csrc.nist.gov/pubs/fips/180-4/upd1/final "NIST — FIPS 180-4 Secure Hash Standard"
[2]: https://csrc.nist.gov/projects/hash-functions/nist-policy-on-hash-functions "NIST — Policy on Hash Functions"
[3]: https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html "OWASP — Key Management Cheat Sheet"
