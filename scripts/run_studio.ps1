<#
.SYNOPSIS
  Start AstraBlox v1.0: one or more studio instances, each a Codex session running the lead with the lanes as its subagents.
.DESCRIPTION
  Each instance is `codex --session-name lead-<n> -c model_reasoning_effort=xhigh --dangerously-bypass-approvals-and-sandbox "<start prompt>"`
  in its own window, started from the checkout root with ASTRA_SESSION=lead and ASTRA_INSTANCE=lead-<n>. The lead reads
  game/VISION.md and board/STATE.md, claims a scene nobody else holds (board.py claim-scene) and works it with spawn_agent.
  Instances share only the files and the board; several of them work different scenes in parallel.
.PARAMETER Instances
  How many studio instances to start. Default 1.
.PARAMETER Stop
  Create the STOP file in the checkout root; every instance finishes its current step and halts.
.PARAMETER ClearStop
  Remove the STOP file before starting.
.PARAMETER DryRun
  Print the commands instead of opening windows.
.EXAMPLE
  .\scripts\run_studio.ps1
  .\scripts\run_studio.ps1 -Instances 3
  .\scripts\run_studio.ps1 -Stop
#>
[CmdletBinding()]
param(
    [ValidateRange(1, 16)][int]$Instances = 1,
    [switch]$Stop,
    [switch]$ClearStop,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$root = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$stopFile = Join-Path $root "STOP"
$shell = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell" }

if ($Stop) {
    Set-Content -Path $stopFile -Value ("STOP requested " + (Get-Date -Format o)) -Encoding UTF8
    Write-Host "STOP written to $stopFile; every instance halts after its current step."
    return
}
if ($ClearStop -and (Test-Path $stopFile)) { Remove-Item $stopFile -Force }
if (Test-Path $stopFile) { throw "STOP file present at $stopFile; run with -ClearStop to start." }
if (-not (Get-Command codex -ErrorAction SilentlyContinue)) { throw "codex not found on PATH" }

function Start-Window([string]$title, [string]$command) {
    $wrapped = "`$Host.UI.RawUI.WindowTitle = '$title'; Set-Location -LiteralPath '$root'; $command"
    if ($DryRun) { Write-Host "[$title] $command"; return }
    # -EncodedCommand: the command carries quotes and $env:, which Windows argument parsing would mangle
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($wrapped))
    Start-Process -FilePath $shell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encoded) -WorkingDirectory $root | Out-Null
}

for ($i = 1; $i -le $Instances; $i++) {
    $name = "lead-$i"
    $prompt = "You are studio instance $name: the lead of AGENTS.md with the lanes as your subagents. Read game/VISION.md and board/STATE.md, run python tools/board/board.py scenes, claim a scene from game/PLAN.md that no other instance holds (python tools/board/board.py claim-scene <id> --by $name), and run the scene cycle to acceptance. Never ask questions; decide, write the assumption into the scene card, continue until STOP exists."
    $cmd = "`$env:ASTRA_SESSION = 'lead'; `$env:ASTRA_INSTANCE = '$name'; codex --session-name $name -c model_reasoning_effort=xhigh --dangerously-bypass-approvals-and-sandbox `"$prompt`""
    Start-Window -title "astra:$name" -command $cmd
    Start-Sleep -Milliseconds 400
}
Write-Host "started $Instances instance(s): " + ((1..$Instances | ForEach-Object { "lead-$_" }) -join ", ")
