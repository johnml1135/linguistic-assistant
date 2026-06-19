<#
.SYNOPSIS
  Download approved NT audio for the research audio add-on into a gitignored cache.

.DESCRIPTION
  Reads research/audio/sources/audio_sources.json through the audit (audio.sources). Only sources
  that pass the exact-text-match + music-free + acceptable-license gate are downloaded. When none
  qualify, it prints the curated language/text/audio alternatives and exits WITHOUT downloading a
  near-match. Default is a dry run; pass -Execute to actually download.

.PARAMETER Execute
  Perform the downloads. Without this, the script only prints the plan (or the alternatives).

.PARAMETER Python
  Python executable to use for the audit (stdlib only). Default: python.

.EXAMPLE
  pwsh -File scripts/audio-download.ps1            # dry run / show alternatives
  pwsh -File scripts/audio-download.ps1 -Execute   # download approved sources
#>
[CmdletBinding()]
param(
    [switch]$Execute,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$research = Join-Path $repoRoot "research"
$cacheRoot = Join-Path $research ".cache/audio"

Push-Location $research
try {
    $reportJson = & $Python -m audio.sources --json
    if ($LASTEXITCODE -ne 0) { throw "audio source audit failed (exit $LASTEXITCODE)." }
    $report = $reportJson | ConvertFrom-Json

    if ($report.approved_count -eq 0) {
        Write-Host "No approved audio source (exact-match + music-free + license gate)." -ForegroundColor Yellow
        & $Python -m audio.sources
        Write-Host "`nNothing to download. Approve a source in audio/sources/audio_sources.json first," -ForegroundColor Yellow
        Write-Host "or pick one of the alternatives above and add it as an approved entry." -ForegroundColor Yellow
        return
    }

    New-Item -ItemType Directory -Force -Path $cacheRoot | Out-Null
    foreach ($s in $report.approved) {
        $dest = Join-Path $cacheRoot $s.target_id
        Write-Host ("plan: {0} -> {1}" -f $s.audio_url, $dest) -ForegroundColor Cyan
        if ($Execute) {
            New-Item -ItemType Directory -Force -Path $dest | Out-Null
            $out = Join-Path $dest ("{0}.audio" -f $s.target_id)
            Invoke-WebRequest -UseBasicParsing -Uri $s.audio_url -OutFile $out
            Write-Host ("downloaded: {0}" -f $out) -ForegroundColor Green
        }
    }
    if (-not $Execute) { Write-Host "`nDry run. Re-run with -Execute to download." -ForegroundColor Yellow }
}
finally {
    Pop-Location
}
