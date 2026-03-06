param(
    [ValidateSet("real", "snapshot")]
    [string]$Mode = "snapshot",
    [string]$Snapshot = "2026-03-06-course-baseline"
)

if (-not (Test-Path ".env")) {
    throw "Arquivo .env nao encontrado. Copie .env.example para .env."
}

Get-Content ".env" | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $parts = $_ -split '=', 2
    if ($parts.Length -eq 2) {
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim())
    }
}

if ($Mode -eq "real") {
    python scripts/course_bootstrap.py --mode real
} else {
    python scripts/course_bootstrap.py --mode snapshot --snapshot $Snapshot
}

python scripts/api_smoke.py
