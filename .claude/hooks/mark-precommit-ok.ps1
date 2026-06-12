# Writes `.claude/state/precommit_ok.json` recording the verdict + diff hash
# of the last /pre-commit run. The git-gate hook reads this file to decide
# whether to allow `git commit`/`git push` through.
#
# Called from the /pre-commit skill after the verdict is rendered.
#
# Usage:
#   pwsh .claude/hooks/mark-precommit-ok.ps1 -Verdict SHIP
#   pwsh .claude/hooks/mark-precommit-ok.ps1 -Verdict FIX

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("SHIP", "FIX")]
    [string]$Verdict
)

# Note: do NOT set ErrorActionPreference=Stop here. git on Windows often
# emits CRLF/LF or other warnings to stderr; PowerShell wraps those as
# NativeCommandError records which would abort the script even though git
# exited 0.

$repoRoot = (git rev-parse --show-toplevel) | Out-String
$repoRoot = $repoRoot.Trim()
if (-not $repoRoot) {
    Write-Error "not a git repo"
    exit 1
}

$stateDir = Join-Path $repoRoot ".claude\state"
if (-not (Test-Path $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
}

Push-Location $repoRoot
try {
    $currentDiff = (git diff HEAD) | Out-String
} finally {
    Pop-Location
}

$sha = [System.Security.Cryptography.SHA256]::Create()
$bytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($currentDiff))
$diffHash = [BitConverter]::ToString($bytes).Replace("-", "").ToLower()

$state = [ordered]@{
    verdict = $Verdict
    diff_hash = $diffHash
    timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    iso_time = (Get-Date).ToUniversalTime().ToString("o")
}

$stateFile = Join-Path $stateDir "precommit_ok.json"
$state | ConvertTo-Json | Set-Content -Path $stateFile -Encoding UTF8

Write-Output ("precommit state written: verdict={0} hash={1}" -f $Verdict, $diffHash.Substring(0, 12))
