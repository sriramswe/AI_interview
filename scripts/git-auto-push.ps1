param(
    [ValidateRange(1, 120)]
    [int]$DebounceSeconds = 8,
    [ValidateRange(1, 30)]
    [int]$PollSeconds = 2,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$GitArguments,
        [switch]$AllowFailure
    )

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = @(& git @GitArguments 2>&1 | ForEach-Object { "$_" })
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "git $($GitArguments -join ' ') failed (exit $exitCode):`n$($output -join "`n")"
    }

    return ,@{
        ExitCode = $exitCode
        Output   = $output
    }
}

function Test-SensitivePath {
    param([string]$Path)

    if ($Path -match '(^|/)\.env($|\.)' -and $Path -notmatch '(^|/)\.env\.example$') {
        return $true
    }

    return $Path -match '(^|/)[^/]*(secret|credential)[^/]*($|/)|\.(pem|key|p12|pfx)$'
}

function Get-EligibleChanges {
    $changedPaths = (Invoke-Git -GitArguments @('diff', '--name-only', 'HEAD')).Output
    $eligible = @(
        $changedPaths |
            Where-Object {
                $_ -and
                -not $protectedPaths.Contains($_) -and
                -not (Test-SensitivePath -Path $_)
            } |
            Sort-Object -Unique
    )
    return ,$eligible
}

function Get-ChangeSignature {
    param([string[]]$Paths)

    $parts = foreach ($path in $Paths) {
        $localPath = Join-Path $repositoryRoot ($path -replace '/', '\')
        if (Test-Path -LiteralPath $localPath) {
            $item = Get-Item -LiteralPath $localPath
            "$path|$($item.Length)|$($item.LastWriteTimeUtc.Ticks)"
        }
        else {
            "$path|deleted"
        }
    }

    return $parts -join "`n"
}

$rootResult = Invoke-Git -GitArguments @('rev-parse', '--show-toplevel')
$repositoryRoot = ($rootResult.Output -join "`n").Trim()
Set-Location -LiteralPath $repositoryRoot

$branchResult = Invoke-Git -GitArguments @('branch', '--show-current')
$currentBranch = ($branchResult.Output -join "`n").Trim()
if ($currentBranch -ne 'master') {
    throw "Auto-push is configured for master, but the current branch is '$currentBranch'. Switch to master before starting."
}

$remoteResult = Invoke-Git -GitArguments @('remote')
if ($remoteResult.Output -notcontains 'origin') {
    throw "Git remote 'origin' is not configured."
}

$protectedPaths = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
$initialChanges = (Invoke-Git -GitArguments @('diff', '--name-only', 'HEAD')).Output
foreach ($path in $initialChanges) {
    if ($path) {
        [void]$protectedPaths.Add($path)
    }
}

Write-Host "Watching $repositoryRoot"
Write-Host "Tracked changes will be committed and pushed to origin/master after $DebounceSeconds seconds of inactivity."
Write-Host "Changes already present at startup, untracked files, and likely secret files will not be auto-pushed."
Write-Host "Press Ctrl+C to stop."

$lastSignature = $null
$quietSince = $null
$pushPending = $false
$nextPushAttempt = [DateTime]::MinValue

if ($DryRun) {
    $eligible = Get-EligibleChanges
    if ($eligible.Count -eq 0) {
        Write-Host 'Dry run: no new eligible tracked changes detected.'
    }
    else {
        Write-Host 'Dry run: eligible tracked changes:'
        $eligible | ForEach-Object { Write-Host "  $_" }
    }
    exit 0
}

while ($true) {
    $now = Get-Date
    $eligiblePaths = Get-EligibleChanges

    if ($eligiblePaths.Count -eq 0) {
        $lastSignature = $null
        $quietSince = $null
    }
    else {
        $signature = Get-ChangeSignature -Paths $eligiblePaths
        if ($signature -ne $lastSignature) {
            $lastSignature = $signature
            $quietSince = $now
            Write-Host "Detected tracked change(s): $($eligiblePaths -join ', ')"
        }
        elseif (($now - $quietSince).TotalSeconds -ge $DebounceSeconds) {
            [void](Invoke-Git -GitArguments (@('add', '-u', '--') + $eligiblePaths))
            $commitArguments = @('commit', '--only', '-m', 'chore: auto-push changes', '--') + $eligiblePaths
            $commitResult = Invoke-Git -GitArguments $commitArguments

            if ($commitResult.Output.Count -gt 0) {
                $commitResult.Output | ForEach-Object { Write-Host $_ }
            }
            $pushPending = $true
            $nextPushAttempt = [DateTime]::MinValue

            $lastSignature = $null
            $quietSince = $null
        }
    }

    if ($pushPending -and $now -ge $nextPushAttempt) {
        $pushResult = Invoke-Git -GitArguments @('push', 'origin', 'HEAD:master') -AllowFailure
        if ($pushResult.ExitCode -eq 0) {
            $pushResult.Output | ForEach-Object { Write-Host $_ }
            Write-Host 'Push to origin/master succeeded.'
            $pushPending = $false
        }
        else {
            Write-Warning "Push failed; will retry in 30 seconds. $($pushResult.Output -join ' ')"
            $nextPushAttempt = (Get-Date).AddSeconds(30)
        }
    }

    Start-Sleep -Seconds $PollSeconds
}
