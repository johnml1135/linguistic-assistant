<#
.SYNOPSIS
  Launch the ik_llama.cpp OpenAI-compatible server for a GGUF model.

.DESCRIPTION
  Serves a local model at http://<ListenHost>:<Port>/v1 so the harness (Python now, C#
  later) can talk to it through the standard openai_compat adapter.

  Two modes:
    * default (foreground): execs the server and blocks. Intended to be launched as a
      child process by the caller, which polls GET /health and terminates the child when
      done. This is the cleanest cross-language lifecycle (subprocess.Popen / Process).
    * -WaitForReady: backgrounds the server, polls /health until ready, prints the PID,
      and returns (leaving the server running). Handy for interactive use.

.PARAMETER Model
  Path to the .gguf model file (required).

.PARAMETER CtxSize
  Context window. Default 4096. (32k is tight on a 24GB 3090 — see research/models.)

.PARAMETER NGpuLayers
  Layers offloaded to GPU. Default 999 (= all). Lower for hybrid CPU/GPU.

.PARAMETER Port / ListenHost
  Bind address. Default 127.0.0.1:8080.

.PARAMETER ServerExe
  Path to llama-server.exe. Defaults to the path recorded by install-ik-llama.ps1.

.PARAMETER ExtraArgs
  Any remaining args are passed through to llama-server (e.g. --parallel, --threads).

.EXAMPLE
  ./serving/run-ik-llama-server.ps1 -Model D:\gguf\gemma-4-27b-IQ4_K.gguf -CtxSize 16384

.EXAMPLE
  # background + wait, for interactive use
  ./serving/run-ik-llama-server.ps1 -Model D:\gguf\qwen3.6-27b-Q4_K_M.gguf -WaitForReady
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Model,
    [int]$CtxSize = 4096,
    [int]$NGpuLayers = 999,
    [int]$Port = 8080,
    [string]$ListenHost = '127.0.0.1',
    [string]$ServerExe,
    [switch]$WaitForReady,
    [int]$ReadyTimeoutSec = 180,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$ExtraArgs
)

$ErrorActionPreference = 'Stop'

# Resolve the server binary: explicit param -> marker file written by the installer.
if (-not $ServerExe) {
    $marker = Join-Path $PSScriptRoot '.ik_llama_server_path.txt'
    if (Test-Path $marker) { $ServerExe = (Get-Content $marker -Raw).Trim() }
}
if (-not $ServerExe -or -not (Test-Path $ServerExe)) {
    throw "llama-server.exe not found. Run serving/install-ik-llama.ps1 first, or pass -ServerExe."
}
if (-not (Test-Path $Model)) { throw "Model file not found: $Model" }

# All-string arg list so Start-Process / call-operator quoting is predictable.
$serverArgs = @(
    '--model', "$Model",
    '--ctx-size', "$CtxSize",
    '-ngl', "$NGpuLayers",
    '--host', "$ListenHost",
    '--port', "$Port"
)
if ($ExtraArgs) { $serverArgs += $ExtraArgs }

$endpoint = "http://${ListenHost}:${Port}"
Write-Host "ik_llama.cpp: $ServerExe"
Write-Host "model:        $Model"
Write-Host "endpoint:     $endpoint/v1  (ctx=$CtxSize, ngl=$NGpuLayers)"

if ($WaitForReady) {
    $proc = Start-Process -FilePath $ServerExe -ArgumentList $serverArgs -PassThru -NoNewWindow
    $deadline = (Get-Date).AddSeconds($ReadyTimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ($proc.HasExited) { throw "Server exited early (code $($proc.ExitCode))." }
        try {
            $r = Invoke-WebRequest -Uri "$endpoint/health" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) {
                Write-Host "ready on $endpoint/v1 (pid $($proc.Id))"
                Write-Output $proc.Id
                return
            }
        }
        catch { Start-Sleep -Milliseconds 500 }
    }
    throw "Server did not become ready within $ReadyTimeoutSec s."
}
else {
    # Foreground: caller manages lifecycle and polls $endpoint/health for readiness.
    & $ServerExe @serverArgs
    exit $LASTEXITCODE
}
