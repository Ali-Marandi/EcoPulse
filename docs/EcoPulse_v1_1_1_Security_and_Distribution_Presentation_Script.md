# سناریوی ارائه گزارش امنیت و توزیع EcoPulse v1.1.1

**مخاطب:** مدیران ارشد، مالک محصول، Security، Platform Engineering، SRE و Customer Success
**زمان پیشنهادی:** 15 دقیقه ارائه + 10 دقیقه پرسش و پاسخ
**هدف جلسه:** تصویب مسیر انتشار تجاری قابل‌اعتماد، نه اعلام «تکمیل امنیت» یا ادعای certification.

## پیام محوری

> EcoPulse v1.1.1 یک baseline اجرایی سالم برای Windows است: build و artifact آن تکرارپذیر و قابل‌ردیابی شده‌اند. تصمیم بعدی، تبدیل این baseline به یک زنجیره انتشار تجاری است که artifact امضاشده، اسکن‌شده، قابل‌rollback و قابل‌مشاهده تحویل می‌دهد.

## دستور اجرای جلسه

| بخش | زمان | مالک پیام | تصمیم یا خروجی موردانتظار |
|---|---:|---|---|
| افتتاح و چارچوب | 1 دقیقه | Product/Executive Sponsor | هم‌راستایی درباره هدف و مرز ادعاها |
| وضعیت v1.1.1 | 2 دقیقه | Release Engineering | تأیید baseline عملیاتی |
| امنیت artifact و signing | 3 دقیقه | Security + Platform | تصویب OIDC و محیط signing محافظت‌شده |
| اسکن و رسیدگی incident | 2 دقیقه | Security Operations | تصویب release gate و severity model |
| توزیع و به‌روزرسانی | 3 دقیقه | Product Ops + IT | انتخاب Canary/Stable و مسیر MSIX |
| Telemetry و تصمیم rollout | 2 دقیقه | SRE | تصویب KPI و pause/rollback policy |
| درخواست تصمیم و گام بعد | 2 دقیقه | Executive Sponsor | تعیین مالک، بودجه و تاریخ review |

---

# متن کامل سخنرانی

## 1. افتتاح و تعریف موفقیت — دقیقه 0 تا 1

«از حضور همه سپاسگزارم. هدف امروز ارائه یک گزارش وضعیت صرف نیست؛ می‌خواهیم درباره گذار EcoPulse از یک فایل اجرایی تولیدشده در CI به یک محصول دسکتاپ سازمانیِ قابل‌اعتماد تصمیم بگیریم. موفقیت در این جلسه به معنای تصویب سه اصل است: نخست، هیچ artifact تجاری بدون امضا، اسکن و evidence منتشر نشود. دوم، هیچ updateای بدون حلقه Canary و امکان rollback به همه مشتریان نرسد. سوم، telemetry فقط برای سلامت انتشار باشد، نه برای نظارت بر کاربر یا محتوای تحلیلی او.

اکنون v1.1.1 یک baseline قابل‌اجراست. این به معنای پایان مسیر امنیت نیست و نباید چنین ادعایی داشته باشیم. معنای آن این است که اکنون یک نقطه شروع پایدار داریم که می‌توان روی آن کنترل‌های تجاری واقعی ساخت.»

**انتقال:** «ابتدا مختصراً توضیح می‌دهم چرا v1.1.1 را baseline می‌نامیم و چرا آن را نسخه پیشنهادی برای ادامه کار می‌دانیم.»

## 2. وضعیت v1.1.1 و درس Release قبلی — دقیقه 1 تا 3

«در v1.0.0، EcoPulse یک workstation بومی Windows با dashboard اقتصادی، scenario analysis، alert محلی و export پایه ارائه کرد. در v1.1.0، ارزش تجاری محصول تقویت شد: Data Health منشأ live و fallback را آشکار می‌کند؛ Scenario Library سناریوها را reusable و قابل‌ردیابی می‌سازد؛ Decision Evidence Pack یک پرونده تصمیم شامل lineage، وضعیت داده، alertها و SHA-256 تولید می‌کند؛ و Local Guardrails Manifest مرزهای نسخه دسکتاپ را شفاف می‌سازد.

اما در مسیر ساخت v1.1.0 یک خطای عملیاتی واقعی آشکار شد. فایل SQLite موقت در Windows runner در زمان cleanup قفل می‌ماند و آزمون دود شکست می‌خورد. این مسئله به‌جای پنهان شدن، به یک درس مهم تبدیل شد: reliability انتشار بخشی از کیفیت محصول است. در v1.1.1 اتصال‌های SQLite به‌طور صریح commit و close می‌شوند. سپس Windows CI با موفقیت اجرا شد و فایل `EcoPulse.exe` به Release متصل گردید.

امروز این تفاوت را باید درست تعبیر کنیم. v1.1.1 feature بزرگ تازه‌ای نسبت به 1.1.0 اضافه نمی‌کند؛ بلکه قابلیت‌های تجاری 1.1.0 را به یک artifact قابل‌تحویل و قابل‌تکرار تبدیل می‌کند. برای مشتری سازمانی، همین distinction مهم است.»

**پیام برای مدیران:** «پیشنهاد من این است که v1.1.1 را تنها baseline مهندسی قرار دهیم، نه اینکه آن را بدون gateهای امنیتی به‌عنوان Stable Commercial توزیع کنیم.»

## 3. تصمیم امنیتی: از artifact به هویت قابل‌اعتماد — دقیقه 3 تا 6

«گام بعدی، code signing است. Authenticode به مصرف‌کننده اجازه می‌دهد هویت ناشر و یکپارچگی binary را با زنجیره گواهی بررسی کند.[1] به‌علاوه، Microsoft تأکید می‌کند که timestamp برای امضا ضروری است؛ بدون timestamp، پس از انقضای گواهی، Windows می‌تواند فایل را unsigned تلقی کند.[2]

اما نکته مهم‌تر از ابزار، مدل مسئولیت است. ما private key را در GitHub secret، فایل PFX یا runner قرار نمی‌دهیم. به‌جای آن، workflow یک token کوتاه‌عمر OIDC دریافت می‌کند و signing provider فقط وقتی این token را می‌پذیرد که repository، tag، environment و policy موردتأیید با trust policy هم‌خوان باشند. GitHub توضیح می‌دهد که OIDC نیاز به credential بلندمدت در repository را حذف می‌کند و token برای همان job صادر و منقضی می‌شود.[3]

در سطح عملیاتی، job signing در محیط `production-signing` اجرا می‌شود. این محیط باید reviewer اجباری، جلوگیری از self-review و محدودیت tagهای مجاز داشته باشد. GitHub environments می‌توانند job را پیش از دسترسی به secret یا اجرای deployment پشت protection rule نگه دارند.[4]

پس ما چهار کنترل را هم‌زمان می‌خواهیم: tag immutable، build در Windows runner پاک، approval دو نقش مستقل و signing با OIDC. خروجی این چرخه فقط EXE نیست؛ یک release manifest شامل hash، signer subject، fingerprint، timestamp presence، provenance و dependency evidence نیز منتشر می‌شود.»

**درخواست تصمیم:** «از تیم مدیریت درخواست می‌کنم provider signing مدیریت‌شده یا HSM-backed را تصویب کند و برای محیط production-signing دو reviewer تعیین شود. از Security می‌خواهیم owner revocation plan و certificate renewal calendar را مشخص کند.»

## 4. اسکن بدافزار و پاسخ به هشدار — دقیقه 6 تا 8

«امضای کد به‌تنهایی اثبات نمی‌کند که artifact امن است؛ فقط نشان می‌دهد چه کسی آن را امضا کرده و آیا پس از امضا تغییر کرده است. به همین دلیل، دو گیت اسکن می‌گذاریم: یکی قبل از امضا و دیگری بعد از امضا، بر روی همان فایل نهایی که منتشر می‌شود.

Microsoft Defender ابزار `MpCmdRun.exe` را برای automation scan فراهم می‌کند و custom scan روی یک file مشخص را پشتیبانی می‌کند.[5] در pipeline، definitions به‌روزرسانی می‌شوند، artifact اسکن می‌شود، و هر detection حل‌نشده release را متوقف می‌کند. سپس پس از signing، دوباره همان artifact اسکن می‌شود. اگر از scanner چندموتوره استفاده شود، باید طبقه‌بندی داده رعایت شود؛ فایل دارای کلید، license اختصاصی یا داده مشتری بدون مجوز نباید به سرویس عمومی ارسال شود.

سیاست incident نیز روشن است: `hash mismatch` یا `signature invalid` یک P1 است؛ channel فوراً freeze می‌شود، artifact قرنطینه می‌گردد و rollback در صورت نیاز آغاز می‌شود. خطاهای network یا disk-space یک P3 یا P2 هستند و ابتدا در سطح endpoint یا CDN تحلیل می‌شوند. این تفکیک جلوی واکنش افراطی به خطاهای عادی و واکنش دیرهنگام به خطر supply chain را می‌گیرد.»

**پیام برای تیم فنی:** «اسکن در مسیر build به‌تنهایی کافی نیست؛ evidence اسکن باید به digest فایل منتشرشده متصل باشد.»

## 5. استراتژی توزیع: EXE امروز، MSIX سازمانی فردا — دقیقه 8 تا 11

«فایل EXE v1.1.1 برای compatibility و bootstrap مفید است، اما کانال اصلی توزیع سازمانی نباید بر download دستی EXE تکیه کند. پیشنهاد ما MSIX امضاشده به‌همراه App Installer است. MSIX نصب و حذف تمیز و همچنین به‌روزرسانی خودکار را پشتیبانی می‌کند.[6]

برای مشتریان استاندارد، App Installer می‌تواند check در زمان launch، update پس‌زمینه و fallback URI داشته باشد.[7] ما برای Stable پیشنهاد می‌کنیم check هر 24 ساعت انجام شود و کاربر در updateهای معمول prompt ببیند، اما launch او block نشود. برای update بحرانی امنیتی، با تأیید Incident Commander می‌توان UpdateBlocksActivation را فعال کرد تا اپ تا دریافت نسخه امن اجرا نشود.[8]

برای مشتریان Managed، مسیر اصلی Intune یا Configuration Manager است. این روش مالکیت زمان‌بندی و کنترل policy را به IT مشتری می‌دهد. Microsoft MSIX را در Intune و Configuration Manager به‌عنوان line-of-business package پشتیبانی می‌کند.[9] مشتریانی که air-gapped هستند، bundle امضاشده، checksum، SBOM و procedure نصب آفلاین می‌گیرند. GitHub Release برای transparency و engineering artifact حفظ می‌شود، اما portal/feed اختصاصی کانال تجاری پایدار خواهد بود.

این architecture به ما اجازه می‌دهد پنج ring داشته باشیم: Internal، Canary، Controlled، Stable و Managed Enterprise. هیچ releaseای مستقیم به همه مشتریان نمی‌رود.»

**درخواست تصمیم:** «تأیید کنید که MSIX/App Installer مسیر استاندارد جدید است و EXE فقط مسیر compatibility باقی می‌ماند. همچنین نخستین مشتریان Canary را با معیار پذیرش مشخص انتخاب کنیم.»

## 6. Telemetry، rollout و تصمیم توقف — دقیقه 11 تا 13

«اگر update را کنترل می‌کنیم، باید اثر آن را نیز ببینیم. اما داده‌ای که می‌گیریم باید حداقلی باشد. Telemetry فقط eventهایی مانند update check، download complete، signature verified، install succeeded، first launch و rollback را ثبت می‌کند. identifierها pseudonymous هستند؛ نام کاربر، hostname، IP، محتوای اقتصادی و داده workspace ارسال نمی‌شوند.

داشبورد مدیران چهار چیز را نشان می‌دهد: ring فعلی، adoption، نرخ موفقیت/rollback و هر رخداد integrity. dashboard فنی funnel کامل update و top error classها را نشان می‌دهد. سه شاخص امنیتی غیرقابل‌مذاکره داریم: signature verification باید صددرصد باشد؛ hash mismatch باید صفر باشد؛ و هر integrity failure باید channel را pause کند.

برای rollout، Internal دست‌کم 24 ساعت observe می‌شود؛ Canary بین 5 تا 10 درصد نصب‌های eligible را می‌گیرد و حداقل 48 ساعت monitor می‌شود؛ سپس Controlled و Stable می‌آیند. thresholdهای اولیه پیشنهادی‌اند: در Canary نرخ install success حداقل 98 درصد، rollback کمتر از نیم درصد و launch سالم حداقل 99 درصد. این اعداد را پس از baseline داخلی بازتنظیم می‌کنیم، اما policy تصمیم از روز اول باید مکتوب باشد.

اگر telemetry endpoint خود دچار مشکل شود، update نباید متوقف شود. eventها local queue می‌شوند، retry محدود دارند و بعد از TTL حذف می‌شوند. telemetry برای سلامت انتشار است، نه شرط availability محصول.»

**پیام برای مدیران:** «این telemetry به ما کمک می‌کند سرمایه‌گذاری بر release را با داده هدایت کنیم؛ نه اینکه با حدس تصمیم promotion یا rollback بگیریم.»

## 7. جمع‌بندی و درخواست اقدام — دقیقه 13 تا 15

«اجازه دهید جلسه را با سه تصمیم مشخص ببندم. نخست، مسیر code signing مبتنی بر OIDC و محیط production-signing با approval اجباری تصویب شود. دوم، مسیر MSIX، App Installer و Intune به‌عنوان معماری توزیع تجاری انتخاب شود و نخستین Canary cohort مشخص گردد. سوم، telemetry حداقلی با schema تصویب‌شده و policy pause/rollback فعال شود.

با این تصمیم‌ها، برنامه 12 هفته‌ای ما روشن است: در دو هفته نخست provider signing، policy و environment ساخته می‌شوند. تا هفته ششم MSIX و App Installer داخلی آماده می‌شوند. تا هفته هشتم Canary با monitoring واقعی اجرا می‌شود. تا هفته دوازدهم templateهای Intune، incident runbook و Stable feed با evidence کامل آماده خواهند بود.

آنچه امروز می‌خواهیم، سرعت بدون کنترل نیست. هدف، یک velocity قابل‌اعتماد است: هر release هویت دارد، هر artifact evidence دارد، هر update قابل مشاهده است و هر مشکل مسیر بازگشت روشن دارد. سپاسگزارم و آماده پرسش‌ها هستم.»

---

# پرسش و پاسخ پیشنهادی

| پرسش احتمالی | پاسخ پیشنهادی |
|---|---|
| «آیا v1.1.1 برای همه مشتریان آماده است؟» | «برای ارزیابی و baseline مهندسی آماده است. برای Stable Commercial باید signing، post-sign scanning، MSIX packaging و Canary rollout را تکمیل کنیم.» |
| «چرا GitHub Release به‌تنهایی کافی نیست؟» | «برای engineering transparency مناسب است، اما کنترل حلقه انتشار، policy مشتری، update خودکار و rollback سازمانی را به‌تنهایی فراهم نمی‌کند.» |
| «آیا OIDC یعنی هیچ secret نداریم؟» | «private key در repository نداریم. شناسه‌های غیرحساس ممکن است به‌صورت environment variable باشند، اما authorization با token کوتاه‌عمر و trust policy انجام می‌شود.» |
| «اگر signing provider در دسترس نبود چه می‌شود؟» | «Release جدید منتشر نمی‌شود؛ artifact امضانشده promotion نمی‌گیرد. این fail-closed policy عمدی است.» |
| «اگر telemetry خاموش باشد، چه رخ می‌دهد؟» | «محصول و update امنیتی همچنان کار می‌کنند؛ فقط visibility roll-out کاهش می‌یابد و مشتری managed باید سلامت را از کنترل‌پلین خودش گزارش کند.» |
| «بزرگ‌ترین ریسک باقی‌مانده چیست؟» | «تا قبل از فعال شدن signing و Canary، ریسک اصلی نه feature محصول بلکه اعتماد supply-chain و کنترل rollout است. برنامه پیشنهادی دقیقاً برای بستن این شکاف طراحی شده است.» |

## منابع

[1]: https://learn.microsoft.com/en-us/windows-hardware/drivers/install/authenticode "Microsoft Learn — Authenticode digital signatures"
[2]: https://learn.microsoft.com/en-us/windows/win32/seccrypto/time-stamping-authenticode-signatures "Microsoft Learn — Time Stamping Authenticode Signatures"
[3]: https://docs.github.com/en/actions/concepts/security/openid-connect "GitHub Docs — OpenID Connect"
[4]: https://docs.github.com/actions/deployment/targeting-different-environments/using-environments-for-deployment "GitHub Docs — Managing environments for deployment"
[5]: https://learn.microsoft.com/en-us/defender-endpoint/command-line-arguments-microsoft-defender-antivirus "Microsoft Learn — MpCmdRun command-line tool"
[6]: https://learn.microsoft.com/en-us/windows/msix/overview "Microsoft Learn — What is MSIX?"
[7]: https://learn.microsoft.com/en-us/windows/msix/app-installer/auto-update-and-repair--overview "Microsoft Learn — Auto-update and repair apps"
[8]: https://learn.microsoft.com/en-us/windows/msix/app-installer/update-settings "Microsoft Learn — Configure update settings in the App Installer file"
[9]: https://learn.microsoft.com/en-us/windows/msix/desktop/managing-your-msix-deployment-enterprise "Microsoft Learn — MSIX App Distribution"
