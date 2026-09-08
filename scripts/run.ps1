<#
.SYNOPSIS
  Start one bounded AstraBlox task, or resume a specific workspace-bound session.
.DESCRIPTION
  One Codex invocation only, including headless mode. The Stop hook alone may
  continue it up to MaxContinues/deadline; hook failure never triggers a restart.
  Time/STOP limits are cooperative: they prevent new continuations/tasks, not an
  immediate process kill. Use Codex interrupt for immediate cancellation.
  Hook trust is normally managed through /hooks. TrustRepositoryHooks is an
  explicit one-invocation bypass for already-reviewed repository hooks.
.EXAMPLE
  .\scripts\run.ps1 -Mode BUILD -Objective "Build and verify the owner-selected bounded feature" -MaxMinutes 90 -ClearStop
  .\scripts\run.ps1 -Headless -Resume -MaxContinues 4 -MaxMinutes 30
  .\scripts\run.ps1 -Mode IMPROVE -Objective "world-builder reports WORLD BUILT but captures show blockout; see cycle-004" -MaxMinutes 60
  .\scripts\run.ps1 -Resume -SessionId "00000000-0000-0000-0000-000000000001"
#>
[CmdletBinding()]
param(
    [ValidateSet("PLAN", "BUILD", "PLAY", "REVIEW", "IMPROVE")][string]$Mode = "BUILD",
    [string]$Objective = "",
    [string]$Concept = "",
    [ValidateRange(0, 1000)][int]$MaxContinues = 12,
    [ValidateRange(1, 1440)][int]$MaxMinutes = 60,
    [switch]$Headless,
    [switch]$Resume,
    [string]$SessionId = "",
    [switch]$Reset,
    [switch]$ClearStop,
    [switch]$TrustRepositoryHooks
)
$ErrorActionPreference = "Stop"
$root = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$gm = Join-Path $root "gamemaster"
$logs = Join-Path $gm "logs"
$runPath = Join-Path $gm "run.json"
$runFlag = Join-Path $gm "RUN"
$stopFlag = Join-Path $gm "STOP"
$sessionPath = Join-Path $gm "session.json"
$lockPath = Join-Path $gm "launcher.lock"
$utf8 = [Text.UTF8Encoding]::new($false)
$lockHandle = $null
$armed = $false
$exitCode = 1
$previousRunId = $env:ASTRA_RUN_ID
$originalLocation = Get-Location

function Write-JsonFile([string]$Path, $Value) {
    $temporary = $Path + "." + [guid]::NewGuid().ToString() + ".tmp"
    try {
        [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 12), $utf8)
        if (Test-Path -LiteralPath $Path) {
            [IO.File]::Replace($temporary, $Path, [NullString]::Value)
        } else {
            [IO.File]::Move($temporary, $Path)
        }
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary }
    }
}

function Save-Session([string]$Id) {
    $parsed = [guid]::Empty
    if (-not [guid]::TryParse($Id, [ref]$parsed)) {
        throw "Codex returned an invalid session ID; resume is disabled."
    }
    $normalized = $parsed.ToString()
    $currentRun = Get-Content -LiteralPath $runPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($currentRun.run_id -ne $env:ASTRA_RUN_ID) { throw "Run identity changed." }
    if ($currentRun.session_id -and $currentRun.session_id -ne $normalized) {
        throw "Codex session identity does not match the explicit resume target."
    }
    Write-JsonFile $sessionPath @{ workspace = $root; session_id = $normalized }
    $currentRun.session_id = $normalized
    Write-JsonFile $runPath $currentRun
}

try {
    if ($Reset -and ($Resume -or $SessionId)) { throw "-Reset cannot be combined with resume." }
    if ($Concept -and ($Resume -or $SessionId)) {
        throw "A new concept must start a fresh session; omit -Resume/-SessionId."
    }
    New-Item -ItemType Directory -Force -Path $logs | Out-Null
    try {
        $lockHandle = [IO.File]::Open($lockPath, [IO.FileMode]::OpenOrCreate,
            [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    } catch { throw "Another AstraBlox launcher owns this workspace. Stop or finish it before launching again." }
    if ((Test-Path -LiteralPath $stopFlag) -and -not $ClearStop) {
        throw "gamemaster/STOP is set. For a newly authorized run pass -ClearStop."
    }
    if ($SessionId) { $Resume = $true }
    if ($Resume -and -not $SessionId) {
        if (-not (Test-Path -LiteralPath $sessionPath)) {
            throw "No persisted session ID. Supply -SessionId <UUID> or start without -Resume; no unrelated session will be resumed."
        }
        $savedSession = Get-Content -LiteralPath $sessionPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ([IO.Path]::GetFullPath($savedSession.workspace) -ne $root) {
            throw "Persisted session belongs to another workspace. Supply an explicit -SessionId or start fresh."
        }
        $SessionId = $savedSession.session_id
    }
    if ($Resume) {
        $parsedSession = [guid]::Empty
        if (-not [guid]::TryParse($SessionId, [ref]$parsedSession)) {
            throw "Resume requires an explicit valid session UUID."
        }
        $SessionId = $parsedSession.ToString()
    }
    $null = Get-Command codex -ErrorAction Stop
    if ($Reset) {
        # Archive only the explicitly named checkpoint files; Studio is untouched.
        $archive = Join-Path $logs ("reset-" + [guid]::NewGuid().ToString())
        New-Item -ItemType Directory -Path $archive | Out-Null
        foreach ($name in @("state.json", "architecture.md", "buglist.md", "roadmap.md", "changelog.md")) {
            $source = [IO.Path]::GetFullPath((Join-Path $gm $name))
            $destination = [IO.Path]::GetFullPath((Join-Path $archive $name))
            if (-not $source.StartsWith($gm + [IO.Path]::DirectorySeparatorChar) -or
                -not $destination.StartsWith($archive + [IO.Path]::DirectorySeparatorChar)) {
                throw "Reset path escaped its checkpoint/archive directory."
            }
            if (Test-Path -LiteralPath $source) { Move-Item -LiteralPath $source -Destination $destination }
        }
    }
    if (-not $Objective) {
        $Objective = if ($Concept) { "Implement and verify the supplied concept within this run." }
            else { "Complete the next bounded task already authorized in the checkpoint; if none exists, inspect and report a proposed next task." }
    }
    if ($Concept) { [IO.File]::WriteAllText((Join-Path $gm "concept.md"), $Concept, $utf8) }
    $runId = [guid]::NewGuid().ToString()
    $now = [DateTimeOffset]::UtcNow
    $runRecord = [ordered]@{
        schema_version = 1; run_id = $runId; workspace = $root; mode = $Mode
        objective = $Objective; status = "active"; next_action = "Load checkpoint and execute the authorized task"
        started_utc = $now.ToString("o"); deadline_utc = $now.AddMinutes($MaxMinutes).ToString("o")
        max_continues = $MaxContinues; continues = 0; session_id = $(if ($Resume) { $SessionId } else { $null })
    }
    Write-JsonFile $runPath $runRecord
    # Never leave a prior session as the resume target for a new, unidentified run.
    Write-JsonFile $sessionPath @{ workspace = $root; session_id = $(if ($Resume) { $SessionId } else { $null }) }
    # A fresh launch always gets a fresh counter; -Reset is unrelated.
    [IO.File]::WriteAllText((Join-Path $logs "continues.count"), "0", $utf8)
    [IO.File]::WriteAllText((Join-Path $gm "MAX_CONTINUES"), [string]$MaxContinues, $utf8)
    if ($ClearStop -and (Test-Path -LiteralPath $stopFlag)) { Remove-Item -LiteralPath $stopFlag }
    $env:ASTRA_RUN_ID = $runId
    [IO.File]::WriteAllText($runFlag, $runId, $utf8)
    $armed = $true
    Set-Location -LiteralPath $root
    $prompt = "AstraBlox bounded run $runId. Mode: $Mode. Objective: $Objective. Read AGENTS.md and gamemaster/run.json plus relevant checkpoint files. Deadline UTC: $($runRecord.deadline_utc). Respect the exclusive Studio Play/input/camera lease after all Edit builders finish. Complete only this authorized task. Set run status complete when acceptance is met, or blocked with exact evidence when an external dependency prevents progress; release Studio/input and finish. Do not extend the budget or invent another roadmap task."
    if ($Concept) { $prompt += "`nConcept:`n$Concept" }
    if ($Mode -eq "IMPROVE") { $prompt += " This run improves the studio itself, not the game: follow the Studio improvement route in AGENTS.md (studio-developer FIX, then a fresh studio-developer AUDIT); Studio may be closed; do not commit or push." }
    $codexArgs = @()
    if ($Headless) {
        $codexArgs += "exec"
        if ($Resume) { $codexArgs += "resume" }
        $codexArgs += @("--json", "--skip-git-repo-check")
    } elseif ($Resume) { $codexArgs += "resume" }
    if ($TrustRepositoryHooks) { $codexArgs += "--dangerously-bypass-hook-trust" }
    if ($Resume) { $codexArgs += $SessionId }
    $codexArgs += $prompt
    Write-Host "AstraBlox $Mode | $MaxMinutes minutes | at most $MaxContinues continuations | run $runId"
    if ($Headless) {
        & codex @codexArgs | ForEach-Object {
            $line = [string]$_
            Write-Output $line
            $event = $null
            try { $event = $line | ConvertFrom-Json -ErrorAction Stop } catch { }
            if ($event -and $event.type -eq "thread.started") { Save-Session $event.thread_id }
        }
    } else { & codex @codexArgs }
    $exitCode = $LASTEXITCODE
    if ($null -eq $exitCode) { $exitCode = 0 }
} catch {
    Write-Error -Message $_ -ErrorAction Continue
    $exitCode = 1
} finally {
    if ($armed) {
        try {
            $finalRun = Get-Content -LiteralPath $runPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($finalRun.run_id -eq $env:ASTRA_RUN_ID) {
                if ($finalRun.status -eq "active") {
                    $finalRun.status = if (Test-Path -LiteralPath $stopFlag) { "stopped" }
                        elseif ($exitCode -ne 0) { "failed" } else { "checkpointed" }
                }
                $finalRun | Add-Member -NotePropertyName exit_code -NotePropertyValue $exitCode -Force
                Write-JsonFile $runPath $finalRun
            }
        } catch { Write-Warning "Run checkpoint could not be finalized; inspect gamemaster/run.json." }
        if (Test-Path -LiteralPath $runFlag) { Remove-Item -LiteralPath $runFlag -ErrorAction SilentlyContinue }
        Write-Host "Bounded run ended. No automatic restart. Inspect gamemaster/run.json for its outcome."
    }
    $env:ASTRA_RUN_ID = $previousRunId
    Set-Location -LiteralPath $originalLocation.Path
    if ($null -ne $lockHandle) {
        $lockHandle.Dispose()
        # Keep the empty lock file: the OS handle, not existence, owns the lease.
    }
}
exit $exitCode
