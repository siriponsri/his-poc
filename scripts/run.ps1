param([ValidateSet('init','config','up','start','stop','status','logs','seed','native-up','native-seed')][string]$Action='up')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python is required for the launcher. Install Python 3.12+ and retry.' }
python scripts/dev.py $Action
if ($LASTEXITCODE -ne 0) { throw "HIS launcher failed ($LASTEXITCODE). Read the error above. No database reset was attempted." }
