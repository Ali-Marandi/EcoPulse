# راهبرد امنیت انتشار و توزیع سازمانی EcoPulse

**مبنای سند:** EcoPulse Desktop `v1.1.1`
**وضعیت مبنا:** Release عمومی با اجرای موفق Windows CI
**مالک پیشنهادی:** تیم Platform Engineering با تأیید مشترک Security، Release Management و Product
**نسخه سند:** 1.0 — 13 اوت 2026

## جمع‌بندی اجرایی

EcoPulse اکنون یک فایل اجرایی Windows قابل‌انتشار دارد، اما مسیر آن تا توزیع تجاری قابل‌اعتماد هنوز باید از حالت «artifact ساخته‌شده در CI» به «artifact امضاشده، اسکن‌شده، قابل‌ردیابی و قابل‌به‌روزرسانی تحت سیاست سازمانی» ارتقا یابد. تصمیم معماری پیشنهادی این است که **امضای Authenticode همراه با timestamp RFC 3161، gateهای چندلایه اسکن، بسته‌بندی MSIX و توزیع کانال‌محور از طریق App Installer یا Intune** به ترتیب اجرا شوند.

> **قاعده انتشار:** هیچ فایل اجرایی یا بسته MSIX نباید صرفاً به‌دلیل عبور از آزمون دود منتشر شود. انتشار تجاری تنها زمانی مجاز است که provenance ساخت، امضای معتبر، هش منتشرشده، SBOM، اسکن دفاعی، کنترل چندموتوره متناسب با سیاست داده، و تأیید Release Manager همگی ثبت شده باشند.

Authenticode هویت ناشر و یکپارچگی فایل را از طریق زنجیره گواهی تا ریشه مورداعتماد بررسی‌پذیر می‌کند.[1] Microsoft صراحتاً توصیه می‌کند که امضاهای Authenticode همواره timestamp شوند؛ در غیر این صورت، پس از انقضای گواهی Windows فایل را unsigned تلقی می‌کند.[2]

## وضعیت فعلی و مرز مسئولیت

| مؤلفه | وضعیت v1.1.1 | نتیجه عملیاتی |
|---|---|---|
| Release عمومی | موجود در GitHub Releases | کانال مناسب برای artifact مهندسی و bootstrap است، نه تنها کانال تجاری بلندمدت. |
| Windows CI | موفق روی تگ `v1.1.1` | آزمون دود و بسته‌بندی در Windows runner با موفقیت انجام شده است. |
| فایل اجرایی | `EcoPulse.exe`، 67.1 MB | فایل باید پیش از استفاده تجاری خارجی code-sign و اسکن مستقل شود. |
| هش Release | `88475d93fef26d379fbd5cc95bd22f96ac7b44b9709ed906f50b21f9fbeb0bfa` | مصرف‌کننده باید هش دانلود را با مقدار انتشار مقایسه کند. |
| امضای کد | هنوز وجود ندارد | پیش‌نیاز انتشار به مشتری سازمانی و بهبود اعتماد Windows است. |
| اسکن بدافزار رسمی | هنوز به‌عنوان gate CI مستند نشده است | باید به pipeline افزوده و evidence آن نگهداری شود. |
| به‌روزرسانی خودکار | هنوز در محصول پیاده‌سازی نشده است | مسیر هدف، MSIX + App Installer/Intune با کانال‌های کنترل‌شده است. |

---

# 1. برنامه اجرایی Code Signing

## 1.1 مدل عملیاتی پیشنهادی

دو مدل معتبر وجود دارد. برای تیمی که می‌خواهد هزینه عملیاتی و ریسک نگهداری کلید را کم کند، **سرویس signing مدیریت‌شده با هویت workload و approval محیط انتشار** ارجح است. برای مشتریان یا الزامات قراردادی که کلید باید در اختیار سازمان باقی بماند، گواهی OV/EV از CA مورداعتماد به همراه HSM یا token سخت‌افزاری و سرویس امضای داخلی استفاده شود. در هر دو مدل، private key نباید به repository، artifact، متغیر محیطی عادی، یا runner اشتراکی کپی شود.

| انتخاب | مناسب برای | الزام غیرقابل‌مذاکره |
|---|---|---|
| Signing مدیریت‌شده | تیم کوچک یا متوسط با GitHub Actions و کنترل حداقلی کلید | اتصال OIDC/identity federation، approval محیط Production و log قابل‌ممیزی. |
| CA + HSM/Cloud HSM | سازمان با الزام کنترل کلید یا مقررات داخلی | کلید non-exportable، RBAC تفکیک‌شده، دو نفر تأیید برای release. |
| Token سخت‌افزاری | انتشار کم‌تکرار و کنترل کاملاً دستی | عدم اتصال دائمی token به runner؛ امضا در workstation ایزوله. |

### کنترل‌های حاکمیتی پیش از خرید یا فعال‌سازی گواهی

1. **هویت ناشر** را با نام حقوقی، کشور ثبت، دامنه و مشخصات پشتیبانی موردنیاز CA یکپارچه کنید. نام Publisher در MSIX و نام گواهی باید با نام قراردادی EcoPulse سازگار باشد.
2. یک Signing Policy ایجاد کنید که مشخص کند چه کسانی می‌توانند release را تأیید، کلید را استفاده و revocation را درخواست کنند. نقش‌های پیشنهادشده عبارت‌اند از `Release Manager`، `Security Approver`، `Signing Operator` و `Incident Commander`.
3. یک محیط محافظت‌شده `production-signing` در GitHub تعریف کنید: فقط workflow حفاظت‌شده، تنها تگ immutable، نیازمند تأیید انسانی، و محدود به branch/tag policy مجاز بتواند به آن دسترسی یابد.
4. fingerprint گواهی، شماره سفارش CA، تاریخ انقضا، URL پاسخ به incident و برنامه تمدید 90/60/30 روزه را در inventory امن ثبت کنید؛ خود private key هرگز وارد inventory یا ticket نشود.
5. پیش از امضای نخست، سند Publisher Identity، صفحه تماس پشتیبانی، EULA/Privacy Notice و سیاست vulnerability disclosure را آماده کنید تا هویت نرم‌افزار قابل ارزیابی باشد.

## 1.2 جریان اجرایی انتشار امضاشده

| گام | مالک | اقدام | مدرک خروجی | Gate |
|---|---|---|---|---|
| 1. Freeze | Product + Engineering | نسخه، changelog و tag را freeze کنید؛ dependency lock را بازبینی کنید. | Release candidate ID | تغییر خارج از PR ممنوع. |
| 2. Build ایزوله | CI | build در Windows runner پاک با dependencyهای pinned انجام شود. | build log و digest اولیه | آزمون‌ها باید سبز باشند. |
| 3. Provenance | CI | commit SHA، runner، نسخه Python/PyInstaller و زمان build را به manifest اضافه کنید. | provenance JSON | artifact بدون provenance رد شود. |
| 4. Pre-sign scan | Security automation | Defender، dependency/SBOM و scanner سیاستی را اجرا کنید. | گزارش اسکن | هر detection حل‌نشده = توقف. |
| 5. Approval | Release Manager + Security | release candidate، گزارش اسکن و manifest را تأیید کنند. | approval audit trail | دو نقش مستقل لازم است. |
| 6. Sign + timestamp | Signing service | `EcoPulse.exe` و بعداً `.msix` را با SHA-256 و RFC 3161 امضا کنید. | signature metadata | کلید فقط در سرویس signing استفاده شود. |
| 7. Verify | CI مستقل | امضا، زنجیره، timestamp و digest را در job جدا تأیید کنید. | verify log | خروجی غیرصفر = توقف. |
| 8. Post-sign scan | Security automation | فایل **امضاشده نهایی** را اسکن کنید. | scan report | باید با digest منتشرشده منطبق باشد. |
| 9. Publish | Release Manager | Release، checksum، SBOM و release notes را در کانال مجاز منتشر کنید. | immutable release record | publish مستقیم از workstation ممنوع. |

## 1.3 دستور نمونه SignTool

دستور زیر الگوی اجرایی است. URL timestamp و روش انتخاب certificate باید با سرویس واقعی سازمان جایگزین شود. SHA-256 و timestamp RFC 3161 الگوی توصیه‌شده Microsoft هستند.[2]

```powershell
# فقط در job signing ایزوله و پس از دریافت approval اجرا شود.
$artifact = "dist\EcoPulse.exe"
$timestampUrl = "https://<approved-rfc3161-timestamp-service>"

signtool sign `
  /fd SHA256 `
  /tr $timestampUrl `
  /td SHA256 `
  /a `
  $artifact

# Verify باید در job جدا و با environment امضاکننده متفاوت انجام شود.
signtool verify /pa /all /v $artifact
Get-FileHash $artifact -Algorithm SHA256
```

`/a` صرفاً یک placeholder عملیاتی برای انتخاب گواهی مناسب در certificate store است. در مدل HSM/managed signing، به‌جای export کردن گواهی یا PFX، adapter رسمی سرویس امضا یا integration مبتنی بر OIDC باید فراخوانی شود. Secretهایی مانند PFX password، API token یا credential signing هرگز نباید در log چاپ شوند.

### معیار پذیرش امضا

| کنترل | معیار پذیرش |
|---|---|
| الگوریتم digest | SHA-256 یا قوی‌تر؛ SHA-1 به‌عنوان امضای اصلی جدید ممنوع است.[2] |
| Timestamp | RFC 3161 با digest SHA-256 و پاسخ معتبر. |
| ناشر | Subject گواهی با Publisher قانونی EcoPulse و manifest بسته سازگار باشد. |
| Verify | `signtool verify /pa /all /v` با کد خروجی صفر در job مستقل. |
| Integrity | SHA-256 artifact امضاشده با مقدار در release manifest و صفحه توزیع یکسان باشد. |
| Scope | EXE، MSIX/MSIXBundle، installer/bootstrapper و هر DLL/کمپوننت توزیع‌شده مطابق inventory امضا شوند. |

---

# 2. برنامه اسکن بدافزار و تضمین supply chain

## 2.1 اصل طراحی

اسکن بدافزار «مهر سلامت مطلق» نیست؛ یک کنترل چندلایه است. فایل باید قبل و بعد از امضا اسکن شود، اما **فایل پس از امضا و با همان digest منتشرشده** نتیجه اصلی release gate است. Microsoft Defender ابزار `MpCmdRun.exe` را برای اسکن و به‌روزرسانی intelligence در automation پشتیبانی می‌کند.[3]

## 2.2 خط لوله پیشنهادی اسکن

| لایه | هدف | ابزار/کنترل پیشنهادی | شرط رد |
|---|---|---|---|
| Source hygiene | جلوگیری از secret و کد مخرب در PR | secret scanning، branch protection، review اجباری | secret یا dependency ناشناس. |
| Dependency | شناسایی آسیب‌پذیری بسته‌ها | SBOM CycloneDX/SPDX، `pip-audit` یا scanner سازمانی | CVE با severity تعیین‌شده بدون waiver. |
| Build | کاهش ریسک artifact آلوده | runner پاک، dependency pin، provenance | build خارج از pipeline مجاز. |
| Pre-sign AV | کشف اولیه | Microsoft Defender custom scan | detection حل‌نشده. |
| Post-sign AV | بررسی فایل نهایی | Defender روی EXE/MSIX امضاشده | detection یا خطای scan. |
| Multi-engine | کشف مستقل و مدیریت false-positive | sandbox/vendor scanner سازمانی؛ VirusTotal فقط طبق data policy | نتیجه مشکوک بدون triage. |
| Dynamic test | مشاهده رفتار runtime | Windows Sandbox یا VM قرنطینه‌شده | رفتار شبکه/فایل غیرمنتظره. |

### اجرای Defender در CI یا VM ایزوله

Microsoft مستند می‌کند که `MpCmdRun.exe` با `-Scan -ScanType 3 -File` برای custom scan به‌کار می‌رود؛ `-SignatureUpdate` نیز intelligence را به‌روز می‌کند.[3] اجرای زیر باید در VM/runner Windows دارای Defender فعال، با لاگ نگه‌داری‌شده و بدون حذف artifact release باشد.

```powershell
# runner یا VM اسکن باید isolated باشد و با حساب elevated اجرا شود.
$platformRoot = "$env:ProgramData\Microsoft\Windows Defender\Platform"
$platform = Get-ChildItem $platformRoot -Directory |
  Sort-Object Name -Descending |
  Select-Object -First 1
$mp = Join-Path $platform.FullName "MpCmdRun.exe"
$artifact = Resolve-Path ".\dist\EcoPulse.exe"

& $mp -SignatureUpdate
& $mp -CheckExclusion -Path $artifact
& $mp -Scan -ScanType 3 -File $artifact -ReturnHR
if ($LASTEXITCODE -ne 0) { throw "Defender scan gate failed: $LASTEXITCODE" }
```

### کنترل چندموتوره و حریم داده

VirusTotal برای فایل‌های بزرگ‌تر از 32 MB نیازمند دریافت upload URL است و مستندات آن سقف 650 MB را برای مسیر مربوطه بیان می‌کند؛ بنابراین فایل 67.1 MB EcoPulse با API معمولی `/files` قابل آپلود مستقیم نیست.[4] با این حال، قبل از استفاده از سرویس چندموتوره عمومی، تیم حقوقی و Security باید طبقه‌بندی داده را تصویب کنند. **هیچ artifact دارای کلید، داده مشتری، مدل اختصاصی، license file یا تعهد NDA نباید بدون مجوز صریح به سرویس عمومی آپلود شود.** در چنین شرایطی از private scanning tier یا sandbox داخلی استفاده کنید.

### فرآیند رسیدگی به detection یا false positive

1. انتشار و promotion کانال را فوراً متوقف کنید؛ artifact با digest مربوطه قرنطینه شود.
2. reproduction در VM مستقل با خروجی Defender، log CI و SBOM انجام شود.
3. اگر dependency یا build step مشکوک است، release را باطل و commit/tag را به‌عنوان compromised علامت‌گذاری کنید؛ artifact مجدداً امضا نشود.
4. اگر false positive تشخیص داده شد، evidence شامل hash، certificate subject، report scanner و رفتار VM را تهیه و از طریق فرآیند vendor برای reclassification ارسال کنید.
5. پس از رفع، build پاک جدید بسازید؛ **artifact قدیمی را overwrite نکنید**. نسخه patch یا build number جدید و changelog شفاف منتشر شود.

---

# 3. مقایسه نسخه‌ها و تحلیل تغییرات

| بُعد | v1.0.0 | v1.1.0 | v1.1.1 (نسخه توصیه‌شده) |
|---|---|---|---|
| هدف محصول | پایه Windows-native برای داشبورد و تحلیل اقتصادی | افزودن پایه‌های traceability تجاری | patch پایداری برای delivery قابل‌اعتماد در Windows CI |
| داده و provenance | اتصال public data و fallback برچسب‌دار | **Data Health** با تمایز live/fallback و readiness | حفظ قابلیت‌های v1.1.0 |
| سناریو | Scenario Studio و ذخیره محلی | **Scenario Library** برای artifactهای reusable و قابل‌ردیابی | حفظ قابلیت‌های v1.1.0 |
| تصمیم و حسابرسی | CSV و audit محلی | **Decision Evidence Pack** JSON با lineage، alert، scenario، audit و SHA-256 | حفظ قابلیت‌های v1.1.0 |
| Guardrails | مرز desktop در مستندات | **Local Guardrails Manifest** صادرشدنی | حفظ قابلیت‌های v1.1.0 |
| QA | smoke اولیه و تصویر Command Center | smoke توسعه‌یافته و visual QA Workspace/Evidence | اصلاح Windows-safe cleanup و عبور CI واقعی |
| پایداری SQLite | عملیات محلی پایه | connection lifecycle در Windows runner قفل فایل ایجاد کرد | sessionها explicit commit/close می‌شوند؛ خطای `WinError 32` رفع شد |
| Windows CI | build اولیه روی Windows؛ مشکل اولیه انتشار خودکار asset نیازمند مداخله بود | build در مرحله smoke با خطای file lock متوقف شد | build، smoke و publish release با موفقیت اجرا شدند |
| فایل اجرایی Release | ساخته و در Release v1.0.0 ارائه شد | Release v1.1.0 بدون EXE به‌دلیل شکست smoke باقی ماند | `EcoPulse.exe` 67.1 MB روی Release v1.1.1 با SHA-256 منتشر شد |
| وضعیت تجاری | foundation | قابلیت‌های evidence و سلامت داده افزوده شد، اما CI ناقص بود | **نسخه عملیاتی توصیه‌شده برای ارزیابی تجاری**؛ هنوز code-signed نیست |

### نتیجه محصولی

v1.1.1 تغییر بزرگ در سطح feature نسبت به v1.1.0 نیست؛ یک patch انتشارمحور است که قابلیت‌های v1.1.0 را قابل‌تحویل و قابل‌تکرار می‌کند. این تفاوت برای مشتری سازمانی مهم است: کیفیت محصول فقط UI یا عمق تحلیل نیست، بلکه توانایی تحویل artifact قابل‌ردیابی و build تکرارپذیر را نیز شامل می‌شود.

---

# 4. راهبرد توزیع و به‌روزرسانی خودکار برای مشتریان تجاری

## 4.1 تصمیم معماری توزیع

برای توزیع تجاری، EXE فعلی باید به‌عنوان **کانال Compatibility/Bootstrap** باقی بماند، اما کانال اصلی به **MSIX امضاشده** منتقل شود. Microsoft، MSIX را قالب مدرن بسته‌بندی با نصب/حذف تمیز و قابلیت به‌روزرسانی خودکار معرفی می‌کند.[5] Intune و Microsoft Configuration Manager نیز MSIX را به‌عنوان Windows app package پشتیبانی می‌کنند و اطلاعات بسته را استخراج می‌کنند.[6]

| کانال | مخاطب | بسته | مکانیزم update | سیاست پیشنهادی |
|---|---|---|---|---|
| Developer / Internal | تیم EcoPulse | signed MSIX از feed داخلی | fast ring؛ update در launch | فقط داده synthetic و tenant آزمایشی. |
| Design Partner / Canary | 5–10٪ دستگاه‌های منتخب هر مشتری | signed MSIX + `.appinstaller` | background و on-launch با prompt | rollback در کمتر از 4 ساعت هدف‌گذاری شود. |
| Stable Commercial | مشتریان استاندارد | MSIX + App Installer | launch check هر 24 ساعت، prompt اختیاری | update اجباری فقط برای امنیت P1. |
| Managed Enterprise | شرکت‌های دارای Intune/ConfigMgr | MSIX line-of-business | policy سازمان مشتری | IT مشتری حلقه انتشار و زمان‌بندی را تعیین می‌کند. |
| Air-gapped / Regulated | شبکه جدا یا حساس | signed MSIX/installer + offline bundle + checksum/SBOM | دستی/ConfigMgr | update package از media کنترل‌شده و ثبت‌شده. |
| Public Discovery | مخاطب عمومی مجاز | EXE/MSIX یا WinGet manifest | explicit user-initiated | پس از تثبیت signing، installer contract و support model. |

## 4.2 App Installer برای کانال تجاری استاندارد

App Installer اجازه می‌دهد updateهای MSIX خارج از Microsoft Store مدیریت شوند. طبق مستندات Microsoft، Windows 10 2004 به بعد و Windows 11 از auto-update/repair پشتیبانی می‌کنند؛ Update URI fallback، بررسی هنگام launch، background task و امکان block activation در صورت update بحرانی وجود دارد.[7]

نمونه سیاست برای کانال Stable، با شناسه‌ها و URLهای placeholder:

```xml
<?xml version="1.0" encoding="utf-8"?>
<AppInstaller
  xmlns="http://schemas.microsoft.com/appx/appinstaller/2021"
  Uri="https://updates.ecopulse.example/stable/EcoPulse.appinstaller"
  Version="1.1.1.0">
  <MainPackage
    Name="EcoPulse"
    Publisher="CN=<Legal Publisher Name>"
    Version="1.1.1.0"
    ProcessorArchitecture="x64"
    Uri="https://updates.ecopulse.example/stable/EcoPulse-1.1.1.0-x64.msix" />
  <UpdateSettings>
    <OnLaunch HoursBetweenUpdateChecks="24"
              ShowPrompt="true"
              UpdateBlocksActivation="false" />
    <AutomaticBackgroundTask />
  </UpdateSettings>
</AppInstaller>
```

برای release بحرانی امنیتی، `ShowPrompt="true"` و `UpdateBlocksActivation="true"` فقط پس از تصویب Security Incident Commander فعال شود. مستندات Microsoft این الگو را برای مجبور کردن کاربر به update پیش از launch پشتیبانی می‌کند.[8] برای rollback کنترل‌شده، package N-1 باید در feed نگه‌داری شود؛ MSIX امکان update به نسخه پایین‌تر را با `ForceUpdateFromAnyVersion` فراهم می‌کند، اما این گزینه باید فقط در مسیر rollback تاییدشده فعال باشد.[6]

## 4.3 Intune، Configuration Manager و WinGet

* **Intune/Configuration Manager:** انتخاب اصلی برای مشتری enterprise managed است. IT مشتری می‌تواند گروه‌های Canary/Stable، زمان‌بندی، uninstall، block و deployment را از ابزار مدیریت endpoint خودش کنترل کند.[6]
* **App Installer:** برای مشتری کم‌پیچیدگی یا نصب self-service کنترل‌شده مناسب است؛ feed باید روی HTTPS با availability، cache policy و access control مشخص میزبانی شود.
* **WinGet:** برای discovery و نصب command-line مناسب است؛ WinGet قابلیت install، upgrade، uninstall، hash و validate manifest را پشتیبانی می‌کند.[9] برای محصول سازمانی اولیه، آن را کانال تکمیلی قرار دهید، نه کنترل‌پلین اصلی tenantهای managed.
* **GitHub Releases:** مناسب artifact مهندسی، transparency و source release است؛ برای مشتری enterprise دارای قرارداد، feed اختصاصی/portal با policy دسترسی و telemetry حداقلی ارجح است.

## 4.4 Update control plane پیشنهادی

```text
Git tag / approved release candidate
        |
        v
Windows CI: test -> build -> SBOM -> scan -> sign -> verify
        |
        v
Release manifest (version, digest, certificate, SBOM, policy decision)
        |
        +--> Internal / Canary feed
        |         |  health window + rollback decision
        |         v
        +--> Stable App Installer feed
        |
        +--> Customer-managed Intune / ConfigMgr package
        |
        +--> GitHub engineering release / WinGet (when eligible)
```

هر tenant باید `channel`، `minimum_version`، `auto_update_policy`، `maintenance_window` و `rollback_eligibility` داشته باشد. خود اپلیکیشن نباید خارج از این control plane updater دانلود کند. در نسخه‌های بعدی، یک API سبک release-manifest با امضای detached، cache کوتاه، consent telemetry و capability policy اضافه شود؛ اما تا زمانی که MSIX/App Installer در دسترس است، منطق update اختصاصی درون EXE نیاز نیست.

## 4.5 برنامه عملیاتی 12 هفته‌ای

| بازه | خروجی | معیار پذیرش |
|---|---|---|
| هفته 1–2 | Signing policy، انتخاب provider، محیط `production-signing` و Release Checklist | هیچ کلید exportable در repository یا runner نیست. |
| هفته 3–4 | Gateهای SBOM، Defender، verify signature و release manifest | build بدون evidence قابل publish نیست. |
| هفته 5–6 | بسته MSIX آزمایشی و App Installer feed داخلی | install، update و uninstall در Windows 10/11 matrix تأیید شود. |
| هفته 7–8 | Canary ring با 5–10٪ دستگاه‌های داخلی/partner | crash-free rate، update success rate و rollback تمرین‌شده ثبت شود. |
| هفته 9–10 | Template Intune/ConfigMgr و onboarding kit مشتری | یک tenant آزمایشی با policy customer-controlled deploy شود. |
| هفته 11–12 | Stable feed، incident runbook و WinGet readiness assessment | SLA انتشار، بازگشت و support escalation تأیید شود. |

---

# 5. چک‌لیست انتشار تجاری

| دسته | سؤال تصمیم | وضعیت لازم برای انتشار Stable |
|---|---|---|
| Code signing | آیا EXE/MSIX امضا، timestamp و verify شده‌اند؟ | بله؛ evidence پیوست release است. |
| Security scan | آیا post-sign Defender و scanner سیاستی سبز هستند؟ | بله؛ report قابل بازیابی است. |
| Provenance | آیا commit، build runner و SBOM ثبت شده‌اند؟ | بله؛ digest artifact immutable است. |
| Update safety | آیا Canary ring و rollback N-1 آماده‌اند؟ | بله؛ rollback تمرین شده است. |
| Enterprise deployment | آیا Intune/ConfigMgr و App Installer مسیر مشخص دارند؟ | بله؛ با template و support owner. |
| Privacy | آیا telemetry update حداقلی، tenant-scoped و قابل خاموش‌کردن است؟ | بله؛ notice و data retention مشخص است. |
| Support | آیا severity، SLA، status page و revocation plan تعیین شده‌اند؟ | بله؛ مسئول incident مشخص است. |

## منابع

[1]: https://learn.microsoft.com/en-us/windows-hardware/drivers/install/authenticode "Microsoft Learn — Authenticode digital signatures"
[2]: https://learn.microsoft.com/en-us/windows/win32/seccrypto/time-stamping-authenticode-signatures "Microsoft Learn — Time Stamping Authenticode Signatures"
[3]: https://learn.microsoft.com/en-us/defender-endpoint/command-line-arguments-microsoft-defender-antivirus "Microsoft Learn — MpCmdRun command-line tool"
[4]: https://docs.virustotal.com/reference/files-scan "VirusTotal API v3 — Upload a file"
[5]: https://learn.microsoft.com/en-us/windows/msix/overview "Microsoft Learn — What is MSIX?"
[6]: https://learn.microsoft.com/en-us/windows/msix/desktop/managing-your-msix-deployment-enterprise "Microsoft Learn — MSIX App Distribution"
[7]: https://learn.microsoft.com/en-us/windows/msix/app-installer/auto-update-and-repair--overview "Microsoft Learn — Auto-update and repair apps"
[8]: https://learn.microsoft.com/en-us/windows/msix/app-installer/update-settings "Microsoft Learn — Configure update settings in the App Installer file"
[9]: https://learn.microsoft.com/en-us/windows/package-manager/winget/ "Microsoft Learn — Use WinGet to install and manage applications"
