[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path $_ -PathType Leaf })]
    [string]$Path,

    [Parameter(Mandatory = $true)]
    [string]$ReportDirectory
)

$ErrorActionPreference = "Stop"
$resolvedPath = (Resolve-Path -LiteralPath $Path).Path
New-Item -ItemType Directory -Path $ReportDirectory -Force | Out-Null

$platformRoot = Join-Path $env:ProgramData "Microsoft\Windows Defender\Platform"
$platform = if (Test-Path $platformRoot) {
    Get-ChildItem -LiteralPath $platformRoot -Directory |
        Sort-Object Name -Descending |
        Select-Object -First 1
}

$mpCmdRun = if ($null -ne $platform) {
    Join-Path $platform.FullName "MpCmdRun.exe"
} else {
    Join-Path $env:ProgramFiles "Windows Defender\MpCmdRun.exe"
}

if (-not (Test-Path $mpCmdRun)) {
    throw "Microsoft Defender MpCmdRun.exe was not found. Run this gate on an approved Windows scanner image with Defender enabled."
}

$scanLog = Join-Path $ReportDirectory "defender-scan.log"
$hash = (Get-FileHash -LiteralPath $resolvedPath -Algorithm SHA256).Hash.ToLowerInvariant()

# Release scanning is non-destructive: the artifact remains intact for evidence collection.
& $mpCmdRun -SignatureUpdate *>&1 | Tee-Object -FilePath $scanLog -Append
if ($LASTEXITCODE -ne 0) { throw "Defender intelligence update failed with exit code $LASTEXITCODE." }

& $mpCmdRun -CheckExclusion -Path $resolvedPath *>&1 | Tee-Object -FilePath $scanLog -Append

& $mpCmdRun -Scan -ScanType 3 -File $resolvedPath -DisableRemediation -ReturnHR *>&1 |
    Tee-Object -FilePath $scanLog -Append
if ($LASTEXITCODE -ne 0) { throw "Microsoft Defender custom scan failed or reported a detection. Exit code: $LASTEXITCODE." }

$report = [ordered]@{
    schema_version = "1.0"
    scanned_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    scanner        = "Microsoft Defender MpCmdRun"
    artifact       = (Split-Path $resolvedPath -Leaf)
    sha256         = $hash
    outcome        = "passed"
    log_file       = (Split-Path $scanLog -Leaf)
}

$reportPath = Join-Path $ReportDirectory "defender-scan-report.json"
$report | ConvertTo-Json | Set-Content -LiteralPath $reportPath -Encoding utf8NoBOM
Write-Host "Defender release scan passed for SHA-256 $hash"
