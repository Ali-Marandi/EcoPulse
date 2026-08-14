[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path $_ -PathType Leaf })]
    [string]$Path,

    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,

    [string]$ExpectedSubject = ""
)

$ErrorActionPreference = "Stop"

$resolvedPath = (Resolve-Path -LiteralPath $Path).Path
$artifact = Get-Item -LiteralPath $resolvedPath
$signature = Get-AuthenticodeSignature -FilePath $resolvedPath

if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
    throw "Authenticode verification failed for '$resolvedPath'. Status: $($signature.Status)."
}

if ([string]::IsNullOrWhiteSpace($signature.SignerCertificate.Subject)) {
    throw "The signed artifact does not expose a signer subject."
}

if (-not [string]::IsNullOrWhiteSpace($ExpectedSubject) -and
    $signature.SignerCertificate.Subject -notlike "*$ExpectedSubject*") {
    throw "Unexpected signer subject '$($signature.SignerCertificate.Subject)'. Expected to contain '$ExpectedSubject'."
}

if ($null -eq $signature.TimeStamperCertificate) {
    throw "No RFC 3161 timestamp certificate was found. Rejecting a release whose signature cannot survive certificate expiry."
}

$hash = Get-FileHash -LiteralPath $resolvedPath -Algorithm SHA256
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$manifest = [ordered]@{
    schema_version       = "1.0"
    generated_at_utc     = (Get-Date).ToUniversalTime().ToString("o")
    filename             = $artifact.Name
    file_size_bytes      = $artifact.Length
    sha256               = $hash.Hash.ToLowerInvariant()
    authenticode_status  = $signature.Status.ToString()
    signer_subject       = $signature.SignerCertificate.Subject
    signer_thumbprint    = $signature.SignerCertificate.Thumbprint
    timestamp_present    = $true
    timestamp_subject    = $signature.TimeStamperCertificate.Subject
    timestamp_thumbprint = $signature.TimeStamperCertificate.Thumbprint
}

$manifestPath = Join-Path $OutputDirectory "$($artifact.Name).release-manifest.json"
$checksumPath = Join-Path $OutputDirectory "$($artifact.Name).sha256"

$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding utf8NoBOM
"$($hash.Hash.ToLowerInvariant()) *$($artifact.Name)" | Set-Content -LiteralPath $checksumPath -Encoding ascii

Write-Host "Signed artifact verified: $($artifact.Name)"
Write-Host "SHA-256: $($hash.Hash.ToLowerInvariant())"
Write-Host "Manifest: $manifestPath"
