# طرح فنی اصالت‌سنجی رمزنگاری‌شده برای Scenario Governance Ledger

**وضعیت:** طرح معماری برای مسیر Enterprise؛ پیاده‌سازی local-first فعلی را جایگزین نمی‌کند.  
**دامنه:** Scenario Governance Ledger، Decision Evidence Pack و exportهای قابل‌راستی‌آزمایی EcoPulse.

## خلاصه تصمیم

پیاده‌سازی فعلی EcoPulse از SHA-256 روی JSON canonical برای تشخیص تغییرات اتفاقی یا ناسازگار در یک export استفاده می‌کند. این کنترل برای **integrity محلی** مفید است، اما اگر مهاجم بتواند هم payload و هم checksum را بنویسد، می‌تواند digestهای تازه‌ای بسازد که verifier محلی آن‌ها را معتبر می‌داند. SHA-256 بدون کلید، هویت نویسنده یا مجازبودن تغییر را اثبات نمی‌کند.[1]

برای مسیر Enterprise، EcoPulse باید دو لایه مکمل داشته باشد:

| لایه | الگوریتم پیشنهادی | نگهدارنده کلید | هدف | روش راستی‌آزمایی |
|---|---|---|---|---|
| Server integrity | `HMAC-SHA-256` | KMS/HSM و سرویس امضای سروری | جلوگیری از جعل توسط کسی که فقط به ledger/write storage دسترسی دارد | سرویس trusted یا verifier سازمانی دارای دسترسی کنترل‌شده به کلید |
| Export authenticity | امضای نامتقارن `ECDSA P-256`/`ES256` یا الگوریتم مورد تأیید سیاست سازمان | KMS/HSM و گواهی سازمانی | اصالت صادرکننده و بررسی آفلاین با public key/certificate | verifier آفلاین، certificate chain و policy trust |

ترکیب پیشنهادی این است که backend، recordها و root manifest را با HMAC در لحظه ثبت محافظت کند و سپس root manifest export را به‌صورت detached یا envelope با کلید نامتقارن امضا کند. HMAC یک MAC متقارن است و با کلید مخفی می‌تواند تغییر غیرمجاز را آشکار کند؛ امضای دیجیتال نیز یک verifier خارجی را قادر می‌سازد بدون دانستن private key، اصالت امضا را بررسی کند.[2] [3]

> **اصل غیرقابل مذاکره:** هیچ HMAC secret یا private signing key نباید در EcoPulse.exe، SQLite محلی، فایل configuration، log، crash dump یا export قرار گیرد.

## 1. مدل تهدید و مرز کنترل

### 1.1 آنچه باید متوقف شود

کنترل جدید باید سناریوی زیر را متوقف کند: مهاجم فایل JSON ledger یا SQLite local را تغییر می‌دهد، `risk_score` یا assumptions را دست‌کاری می‌کند، و سپس تمام SHA-256های بدون کلید را دوباره محاسبه می‌کند. در طراحی فعلی، چنین مهاجمی می‌تواند فایل خودسازگار بسازد. در طراحی Enterprise، او فاقد HMAC key و private signing key است؛ بنابراین قادر به تولید tag یا signature معتبر نخواهد بود.

### 1.2 آنچه این کنترل به‌تنهایی حل نمی‌کند

اگر مهاجم بتواند به API امضای سروری با همان identity و همان scope مجاز دسترسی پیدا کند، HMAC یا signature نیز به‌تنهایی کافی نیست. سرویس signer باید authorization دقیق، tenant binding، approval policy، rate limit، audit append-only و detection رفتار غیرعادی داشته باشد. اگر private key یا KMS administrator compromise شود، باید incident response، key revocation و re-signing policy فعال شود.

| تهدید | SHA-256 فعلی | HMAC سروری | امضای دیجیتال سروری |
|---|---|---|---|
| تغییر تصادفی فایل | آشکار | آشکار | آشکار |
| تغییر payload با write access | قابل جعل | بدون key قابل جعل نیست | بدون private key قابل جعل نیست |
| بررسی آفلاین توسط شخص ثالث | ممکن، اما بدون اصالت | معمولاً نامناسب؛ secret نباید توزیع شود | مناسب با public key/certificate |
| انتساب به صادرکننده سازمانی | ندارد | shared-secret authentication، نه non-repudiation | قوی‌تر؛ signature evidence قابل بررسی توسط third party |
| key rotation | نامشخص در مدل محلی | `key_id` و key version لازم است | `kid`، certificate chain، validity و revocation لازم است |

## 2. Canonical payload و domain separation

هر دو مکانیزم باید دقیقاً روی یک byte sequence قطعی عمل کنند. JSON معمولی به‌خاطر ترتیب کلید، whitespace، Unicode normalization و number serialization به‌تنهایی contract رمزنگاری نیست. EcoPulse باید schema-versioned canonicalization را تثبیت و test vector منتشر کند.

### 2.1 Canonicalization contract

| قاعده | الزام |
|---|---|
| Schema | `ecopulse.scenario-ledger.v2` و field ordering مشخص |
| Encoding | UTF-8، Unicode normalization policy صریح |
| Object keys | مرتب‌سازی lexicographic قطعی |
| Numbers | قرارداد serialisation صریح؛ از `NaN`، `Infinity` و locale-dependent formatting پرهیز شود |
| Arrays | ترتیب business-defined حفظ شود؛ در ledger باید `sequence_no` قطعی داشته باشند |
| Exclusions | `integrity`، `auth` و `signature` از payload امضاشده حذف می‌شوند تا self-reference رخ ندهد |
| Domain | prefix ثابت و versioned مانند `EcoPulse-Ledger-Auth-v2\0` قبل از payload قرار می‌گیرد |

Canonical payload پیشنهادی:

```text
payload_bytes = UTF8(CanonicalJSON(ledger_without_auth_and_signature))
domain_bytes  = UTF8("EcoPulse-Ledger-Auth-v2\0")
auth_input    = domain_bytes || tenant_id || "\0" || ledger_id || "\0" || payload_bytes
```

binding کردن `tenant_id` و `ledger_id` مانع آن می‌شود که یک tag/signature معتبر از یک tenant یا یک ledger بدون تغییر context، برای object دیگری replay شود.

## 3. گزینه A: HMAC-SHA-256 برای integrity سروری

NIST، HMAC را MAC مبتنی بر hash و secret shared key معرفی می‌کند که برای message authentication استفاده می‌شود.[2] در EcoPulse، secret باید تنها در KMS/HSM یا signer service نگهداری شود؛ Desktop صرفاً درخواست sign و نتیجه را دریافت می‌کند.

### 3.1 Envelope پیشنهادی

```json
{
  "schema": "ecopulse.scenario-ledger.v2",
  "ledger_id": "01J...",
  "tenant_id": "tenant_abc",
  "sequence_no": 1842,
  "previous_root_sha256": "...",
  "records": ["..."],
  "integrity": {
    "canonical_payload_sha256": "..."
  },
  "auth": {
    "scheme": "HMAC-SHA-256",
    "key_id": "ep-ledger-hmac-2026-q3",
    "issued_at_utc": "2026-08-14T00:00:00Z",
    "key_version": 3,
    "tag_b64url": "..."
  }
}
```

محاسبه:

\[
Tag = HMAC\text{-}SHA256(K_{tenant,ledger}, Domain || Tenant || LedgerId || CanonicalPayload)
\]

کلیدها باید per-environment و ترجیحاً per-tenant از key hierarchy مشتق یا جداگانه provision شوند. `key_id` فقط identifier است و secret نیست.

### 3.2 جریان ثبت و verify

1. Desktop با OIDC access token، scenario payload و expected parent root را به API می‌فرستد.
2. API identity، tenant، entitlement، approval state و optimistic concurrency (`expected_sequence_no`) را بررسی می‌کند.
3. API canonical payload را می‌سازد، `payload_sha256` را ثبت و HMAC را در signer/KMS تولید می‌کند.
4. API ledger record، tag، actor identity، correlation ID و server timestamp را در append-only store می‌نویسد.
5. برای verify، trusted backend یا یک verifier سازمانی که مجاز به استفاده از KMS است tag را بازحساب و constant-time compare می‌کند.

```python
expected = hmac.new(key_bytes, auth_input, hashlib.sha256).digest()
valid = hmac.compare_digest(expected, received_tag)
```

مقایسه constant-time برای جلوگیری از leakage مبتنی بر زمان لازم است. verifier نباید صرفاً `==` روی bytes یا string استفاده کند.

### 3.3 محدودیت HMAC

HMAC برای export عمومی یا offline verifier نامناسب است، زیرا هر verifier دارای secret می‌تواند tag جدید نیز بسازد. اگر secret را منتشر نکنیم، verify باید به API سازمانی متکی بماند. بنابراین HMAC برای **server-side write integrity** مناسب است، اما برای non-repudiation یا تبادل evidence با auditor خارجی، امضای نامتقارن گزینه بهتر است.

## 4. گزینه B: امضای دیجیتال برای export و third-party verification

FIPS 186-5 توضیح می‌دهد که امضاهای دیجیتال تغییر غیرمجاز را آشکار می‌کنند، هویت signatory را authenticate می‌کنند و می‌توانند برای اثبات به شخص ثالث به کار روند.[3] برای EcoPulse، کلید private باید non-exportable و در HSM/KMS سازمانی نگهداری شود؛ سرویس signer با policy، digest یا canonical bytes را sign می‌کند.

### 4.1 انتخاب الگوریتم

| گزینه | کاربرد پیشنهادی | ملاحظه |
|---|---|---|
| `ES256` / ECDSA P-256 + SHA-256 | default سازگار با اکوسیستم‌های enterprise و policyهای FIPS | private key در HSM/KMS؛ signature DER/JWS encoding را مشخص کنید |
| Ed25519 / `EdDSA` | workflowهای modern با signature کوچک و deterministic | فقط پس از تأیید compliance و قابلیت KMS/HSM سازمان |
| RSA-PSS | interoperability با محیط‌های legacy | signature بزرگ‌تر و عملیات سنگین‌تر؛ برای requirement legacy نگه‌داری شود |

### 4.2 قالب detached signature پیشنهادی

خروجی ledger باید payload و signature را جدا نگه دارد تا verifier بتواند artifact را بدون mutation verify کند:

```json
{
  "signature_schema": "ecopulse.detached-signature.v1",
  "ledger_id": "01J...",
  "payload_sha256": "...",
  "alg": "ES256",
  "kid": "https://keys.ecopulse.example/ledger/2026-q3",
  "signed_at_utc": "2026-08-14T00:00:00Z",
  "signature_b64url": "...",
  "certificate_chain": ["optional PEM/DER reference"],
  "timestamp": {
    "scheme": "RFC3161",
    "token_ref": "optional detached token"
  }
}
```

امضای دیجیتال باید بر `Domain || tenant_id || ledger_id || canonical_payload` انجام شود، نه صرفاً روی `payload_sha256` بدون context. `kid` برای انتخاب public key و rotation استفاده می‌شود. certificate chain یا JWKS endpoint باید با pinning/trust policy کنترل شود؛ از اعتماد کورکورانه به URL داخل artifact پرهیز کنید.

### 4.3 جریان verify آفلاین

1. verifier schema، `alg` و `kid` را با allowlist policy مقایسه می‌کند.
2. canonical payload را مجدداً می‌سازد و `payload_sha256` را check می‌کند.
3. public key یا certificate معتبر را از trust store سازمانی دریافت می‌کند؛ نه صرفاً یک URL کنترل‌شده توسط sender.
4. signature را verify و validity window، key rotation/revocation policy و timestamp را بررسی می‌کند.
5. نتیجه باید شامل `VALID`، `INVALID_SIGNATURE`، `UNKNOWN_KEY`، `EXPIRED_KEY` یا `CANONICALIZATION_MISMATCH` باشد.

## 5. معماری پیشنهادی Hybrid

بهترین مسیر Enterprise، جایگزینی تمام checksumهای محلی با signature در همان روز نیست. مسیر مرحله‌ای زیر ریسک را پایین نگه می‌دارد.

| مرحله | تغییر | کنترل حاصل |
|---|---|---|
| 0 | حفظ SHA-256 local verifier و test vectors | سازگاری export و detection غیررمزنگاری‌شده |
| 1 | افزودن backend ledger API، tenant binding و append-only sequence | ownership و server timestamp |
| 2 | افزودن HMAC server-side به هر record و root manifest | جلوگیری از جعل توسط writer صرفاً storage |
| 3 | افزودن detached ES256 signature برای export root | offline verification و evidence سازمانی |
| 4 | RFC 3161 timestamp، key rotation، revocation و monitoring | assurance زمانی و lifecycle کامل کلید |

### 5.1 Anchor و anti-replay

هر export باید `ledger_id`، `tenant_id`، `sequence_no`، `previous_root_sha256` و `issued_at_utc` داشته باشد. API فقط sequence بعدی را قبول می‌کند و root قبلی را در یک store append-only نگه می‌دارد. این الگو حذف یا reordering رکوردها را قابل‌آشکارتر می‌کند. برای مقاومت قوی‌تر، rootهای روزانه به یک WORM/object-lock store یا transparency log anchor شوند.

### 5.2 Key lifecycle

| رویداد | الزام |
|---|---|
| Create | key غیرقابل export در HSM/KMS؛ `kid` و owner ثبت شوند |
| Use | signer service با OIDC workload identity، least privilege و policy tenant/environment |
| Rotate | `kid` و key version در هر artifact؛ public keys پیشین برای verify تاریخی نگهداری شوند |
| Revoke/compromise | deny signing، انتشار revocation state، incident record، re-sign policy برای rootهای لازم |
| Audit | هر sign/verify request با actor/service identity، correlation ID، result و policy version ثبت شود |

## 6. API contract پیشنهادی

| Endpoint | نقش | کنترل ضروری |
|---|---|---|
| `POST /v2/ledgers/{ledger_id}/records` | ثبت record و HMAC | OIDC، tenant isolation، optimistic concurrency، approval policy |
| `POST /v2/ledgers/{ledger_id}/export` | تولید payload و detached signature | export entitlement، redaction policy، audit event |
| `POST /v2/ledger-verifications` | verify trusted یا offline result ingestion | rate limit، trusted key policy، tamper-safe result |
| `GET /.well-known/ecopulse-ledger-keys.json` | کلید عمومی/metadata | key pinning، expiration، cache policy، rotation history |

Desktop باید فقط access token کوتاه‌عمر و outputهای API را نگه دارد. هیچ کلید cryptographic یا refresh token بلندمدت نباید به Evidence Pack افزوده شود.

## 7. آزمون و acceptance criteria

| آزمون | انتظار |
|---|---|
| تغییر payload بدون تغییر auth | `INVALID_SIGNATURE` یا HMAC mismatch |
| تغییر checksum/record hash | canonical payload mismatch یا auth mismatch |
| replay یک artifact برای tenant دیگر | context binding rejection |
| `kid` ناشناخته | `UNKNOWN_KEY`، fail closed |
| کلید قدیمی اما در grace window | verify موفق با key version تاریخی |
| کلید revoked | verify با policy `REVOKED_KEY` fail شود |
| signer بدون entitlement | API قبل از sign پاسخ 403 بدهد |
| concurrent append | sequence conflict؛ signature برای root اشتباه صادر نشود |

## 8. توصیه اجرایی

برای مشتریان سازمانی، **Hybrid HMAC + detached digital signature** توصیه می‌شود. HMAC کنترل write-path سرور را فراهم می‌کند؛ امضای نامتقارن، export قابل‌ارائه به audit و verification خارج از سامانه را ممکن می‌سازد. تنها افزودن HMAC به EXE یا SQLite محلی امنیت مطلوب ایجاد نمی‌کند، چون مهاجم می‌تواند secret را استخراج کند. تنها افزودن signature بدون authorization و append-only retention نیز replay یا misuse سرویس signer را حل نمی‌کند.

پیاده‌سازی باید با یک proof-of-concept غیرتولیدی شروع شود: یک KMS/HSM واقعی، یک tenant test، یک key rotation test و یک verifier مستقل. سپس پس از security review، threat-model sign-off و کنترل‌های identity/retention می‌توان آن را وارد نسخه Enterprise کرد.

## منابع

[1]: https://csrc.nist.gov/pubs/fips/180-4/upd1/final "NIST FIPS 180-4 — Secure Hash Standard"
[2]: https://csrc.nist.gov/pubs/fips/198-1/final "NIST FIPS 198-1 — The Keyed-Hash Message Authentication Code (HMAC)"
[3]: https://csrc.nist.gov/pubs/fips/186-5/final "NIST FIPS 186-5 — Digital Signature Standard"
[4]: https://csrc.nist.gov/pubs/sp/800/224/ipd "NIST SP 800-224 (Initial Public Draft) — HMAC recommendations"
