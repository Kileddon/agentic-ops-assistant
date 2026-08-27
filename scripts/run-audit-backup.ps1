$ErrorActionPreference = "Stop"

if (-not $env:OPS_AUDIT_BACKUP_DIRECTORY) {
    throw "OPS_AUDIT_BACKUP_DIRECTORY must be set."
}

uv run ops-backup-latest-audit
