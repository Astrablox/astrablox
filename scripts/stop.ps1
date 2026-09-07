# Request cooperative stop. Current tool/action may finish; no next continuation.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$gm = Join-Path $root "gamemaster"
New-Item -ItemType Directory -Force -Path $gm | Out-Null
[IO.File]::WriteAllText((Join-Path $gm "STOP"), "Owner requested stop", [Text.UTF8Encoding]::new($false))
if (Test-Path -LiteralPath (Join-Path $gm "RUN")) {
    Remove-Item -LiteralPath (Join-Path $gm "RUN") -ErrorAction SilentlyContinue
}
Write-Host "Stop requested. Finish safe cleanup/checkpoint and release Studio/input; no new task or continuation. Use Codex interrupt for immediate cancellation."
