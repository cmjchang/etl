param([string]$ExportRoot = "")
$ErrorActionPreference = 'Stop'
& "$PSScriptRoot/.venv/Scripts/python.exe" "$PSScriptRoot/run_pipeline.py" --export-root $ExportRoot
exit $LASTEXITCODE
