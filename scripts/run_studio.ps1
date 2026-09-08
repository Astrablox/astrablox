<#
.SYNOPSIS
  Start the AstraBlox v0.3 studio: one Codex session per lane plus the supervisor, each in its own window.
.DESCRIPTION
  Lanes and their reasoning effort come from tools/board/lanes.json (contract §2, §13). For each lane a new
  PowerShell window runs `codex --session-name <lane> -c model_reasoning_effort=<effort>
  --dangerously-bypass-approvals-and-sandbox "<start prompt>"` from the checkout root; the lane's role
  is loaded by Codex from its name. The supervisor (tools/board/supervisor.py) gets its own window.
  Sessions are long-lived: signals between them go through `codex queue` (see board/README.md).
.PARAMETER Lanes
  Subset of lanes to start, e.g. -Lanes lead,world. Default: all lanes in lanes.json.
.PARAMETER NoSupervisor
  Do not open the supervisor window.
.PARAMETER Stop
  Create the STOP file in the checkout root; the supervisor sends STOP to every session and exits.
.PARAMETER ClearStop
  Remove the STOP file before starting.
.PARAMETER DryRun
  Print the commands instead of opening windows.
.EXAMPLE
  .\scripts\run_studio.ps1
  .\scripts\run_studio.ps1 -Lanes lead,world,studio
  .\scripts\run_studio.ps1 -Stop
#>
[CmdletBinding()]
param(
    [string[]]$Lanes = @(),
    [switch]$NoSupervisor,
    [switch]$Stop,
    [switch]$ClearStop,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$root = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$stopFile = Join-Path $root "STOP"
$lanesFile = Join-Path $root "tools\board\lanes.json"
$python = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "py" }
$shell = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell" }

if ($Stop) {
    Set-Content -Path $stopFile -Value ("STOP requested " + (Get-Date -Format o)) -Encoding UTF8
    Write-Host "STOP written to $stopFile; the supervisor will signal every session."
    return
}
if ($ClearStop -and (Test-Path $stopFile)) { Remove-Item $stopFile -Force }
if (Test-Path $stopFile) { throw "STOP file present at $stopFile; run with -ClearStop to start." }
if (-not (Get-Command codex -ErrorAction SilentlyContinue)) { throw "codex not found on PATH" }

$all = (Get-Content $lanesFile -Raw | ConvertFrom-Json).lanes
$selected = if ($Lanes.Count -gt 0) {
    $wanted = $Lanes | ForEach-Object { $_.Split(",") } | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    $all | Where-Object { $wanted -contains $_.name }
} else { $all }
if (-not $selected) { throw "no lanes matched: $($Lanes -join ',')" }

function Start-Window([string]$title, [string]$command) {
    $wrapped = "`$Host.UI.RawUI.WindowTitle = '$title'; Set-Location -LiteralPath '$root'; $command"
    if ($DryRun) { Write-Host "[$title] $command"; return }
    # -EncodedCommand: the command carries quotes and $env:, which Windows argument parsing would mangle
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($wrapped))
    Start-Process -FilePath $shell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encoded) -WorkingDirectory $root | Out-Null
}

foreach ($lane in $selected) {
    $name = $lane.name
    $prompt = "You are the $name session of the AstraBlox studio. Read board/STATE.md, then run: python tools/board/board.py next --lane $name -- and work the task it names (claim it first, refresh the heartbeat with board.py heartbeat --session $name while working, finish with a report and a signal to lead). When there is no task, wait for signals; a signal names a file, read it before acting. Never ask questions; decide, write the assumption in the report, continue."
    $cmd = "`$env:ASTRA_SESSION = '$name'; codex --session-name $name -c model_reasoning_effort=$($lane.effort) --dangerously-bypass-approvals-and-sandbox `"$prompt`""
    Start-Window -title "astra:$name" -command $cmd
    Start-Sleep -Milliseconds 400
}
if (-not $NoSupervisor) {
    Start-Window -title "astra:supervisor" -command "`$env:ASTRA_SESSION = 'supervisor'; $python tools\board\supervisor.py"
}
Write-Host ("started: " + (($selected | ForEach-Object { $_.name }) -join ", ") + $(if ($NoSupervisor) { "" } else { ", supervisor" }))
