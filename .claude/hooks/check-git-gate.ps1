# PreToolUse hook: blocks `git commit*` / `git push*` until the /pre-commit
# skill has produced a SHIP verdict against the current diff within the last
# 10 minutes. Bypass with $env:FINOPS_PRECOMMIT_BYPASS = '1' for emergencies.
#
# Reads the Claude Code tool-call JSON from stdin and emits a PreToolUse
# decision JSON on stdout (deny) or exits 0 silently (allow).

# Note: do NOT set ErrorActionPreference=Stop here. git on Windows can emit
# benign warnings to stderr (e.g. LF/CRLF) that PowerShell wraps as
# NativeCommandError records; strict mode would abort the hook on those.

function Deny([string]$reason) {
    $payload = @{
        hookSpecificOutput = @{
            hookEventName = "PreToolUse"
            permissionDecision = "deny"
            permissionDecisionReason = $reason
        }
    } | ConvertTo-Json -Depth 5 -Compress
    [Console]::Out.Write($payload)
    exit 0
}

# 1. Read tool call from stdin.
$raw = [Console]::In.ReadToEnd()
if (-not $raw) { exit 0 }
try {
    $event = $raw | ConvertFrom-Json
} catch {
    # Malformed input — do not block. Better to let the operation through
    # than to wedge Claude Code on a parse error.
    exit 0
}

if ($event.tool_name -ne "Bash") { exit 0 }

$cmd = [string]$event.tool_input.command
if ([string]::IsNullOrWhiteSpace($cmd)) { exit 0 }

# Strip quoted argument ranges before matching, so the literal text
# `git commit` / `git push` inside a string argument (grep patterns, node -e
# snippets, commit message bodies that mention push) does not trigger the
# gate. A simple regex strip cannot handle bash's `'\''` escape-and-reopen
# pattern, so this is a small state machine over single quotes, double quotes
# and backslash escapes. Backticks and `$(...)` are intentionally left alone —
# those are command substitution, not data, and a `git push` inside them is a
# real invocation we want to gate.
function Strip-Quoted([string]$s) {
    $sb = [System.Text.StringBuilder]::new()
    $state = 0  # 0=normal, 1=single, 2=double
    for ($i = 0; $i -lt $s.Length; $i++) {
        $c = $s[$i]
        if ($state -eq 0) {
            if ($c -eq "'") { $state = 1; continue }
            if ($c -eq '"') { $state = 2; continue }
            if ($c -eq '\' -and $i + 1 -lt $s.Length) {
                # outside quotes: backslash escapes the next char.
                # Emit a space so adjacent tokens stay separated.
                $i++
                [void]$sb.Append(' ')
                continue
            }
            [void]$sb.Append($c)
        }
        elseif ($state -eq 1) {
            # bash single-quoted: no escapes, ends at the next `'`.
            if ($c -eq "'") { $state = 0 }
        }
        else {
            # bash double-quoted: backslash escapes the next char; ends at `"`.
            if ($c -eq '"') { $state = 0; continue }
            if ($c -eq '\' -and $i + 1 -lt $s.Length) { $i++ }
        }
    }
    return $sb.ToString()
}

$cmdForMatch = Strip-Quoted $cmd
if ($cmdForMatch -notmatch '\bgit\s+(commit|push)\b') { exit 0 }

# Operator escape hatch.
if ($env:FINOPS_PRECOMMIT_BYPASS -eq "1") { exit 0 }

# 2. Locate repo root from the hook's working directory or the event payload.
$cwd = if ($event.cwd) { [string]$event.cwd } else { (Get-Location).Path }
Push-Location $cwd
try {
    $repoRoot = (git rev-parse --show-toplevel) | Out-String
    $repoRoot = $repoRoot.Trim()
    if (-not $repoRoot) { exit 0 }  # not a git repo, nothing to gate
} finally {
    Pop-Location
}

$stateFile = Join-Path $repoRoot ".claude\state\precommit_ok.json"
if (-not (Test-Path $stateFile)) {
    Deny "Pre-commit gate not satisfied. Run /pre-commit first."
}

try {
    $state = Get-Content $stateFile -Raw | ConvertFrom-Json
} catch {
    Deny "Pre-commit state file is unreadable. Re-run /pre-commit."
}

# 3. Verdict must be SHIP.
if ($state.verdict -ne "SHIP") {
    Deny ("Last /pre-commit verdict was '{0}'. Re-run after fixes." -f $state.verdict)
}

# 4. Freshness window: 10 minutes.
$now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$age = $now - [int64]$state.timestamp
if ($age -gt 600) {
    Deny ("Pre-commit verdict is {0}s old (>600). Re-run /pre-commit." -f $age)
}

# 5. Diff hash must match the current diff so changes after /pre-commit are
# re-reviewed before they ship.
Push-Location $repoRoot
try {
    $currentDiff = (git diff HEAD) | Out-String
} finally {
    Pop-Location
}

$sha = [System.Security.Cryptography.SHA256]::Create()
$bytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($currentDiff))
$currentHash = [BitConverter]::ToString($bytes).Replace("-", "").ToLower()

if ($state.diff_hash -ne $currentHash) {
    Deny "Diff changed since last /pre-commit (hash mismatch). Re-run /pre-commit."
}

exit 0
