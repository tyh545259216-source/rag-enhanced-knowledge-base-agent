# 从本项目启动外部 nanobot，不安装依赖或修改 Provider。
[CmdletBinding()]
param([string]$PythonExecutable, [string]$NanobotPath, [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $PythonExecutable) {
    if (-not $NanobotPath) { $NanobotPath = Join-Path (Split-Path -Parent $projectRoot) 'nanobot' }
    if (-not (Test-Path -LiteralPath $NanobotPath -PathType Container)) {
        throw 'nanobot directory not found. Use -NanobotPath or -PythonExecutable.'
    }
    $PythonExecutable = Join-Path $NanobotPath '.venv/Scripts/python.exe'
}
if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    throw 'Python executable not found. Install both projects into one environment, then use -PythonExecutable.'
}
$PythonExecutable = (Resolve-Path -LiteralPath $PythonExecutable).Path
$configPath = Join-Path $projectRoot 'config.yaml'
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) { throw 'Project config.yaml not found.' }
# 使用 config 的实际 store_dir，不写索引。
$preflight = 'import sys; from pathlib import Path; import nanobot; from knowledge_base_agent.rag.config import load_config; from importlib.metadata import entry_points; config=load_config(Path(sys.argv[1])); assert any(e.name=="search_knowledge_base" for e in entry_points(group="nanobot.tools")), "search_knowledge_base entry point missing; install this project into the selected Python environment"; assert all((config.store_dir/name).is_file() for name in ("index.faiss","metadata.json","index_info.json")), "Index files missing; run knowledge_base_agent.ingest separately"'
$preflight | & $PythonExecutable -B - $configPath
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed. Check the selected environment and build the knowledge base separately.' }
if ($CheckOnly) { Write-Output 'Preflight OK. Ready to run: python -m nanobot webui'; return }
$hadConfig = Test-Path Env:KNOWLEDGE_BASE_CONFIG
$previousConfig = $env:KNOWLEDGE_BASE_CONFIG
Push-Location $projectRoot
try {
    $env:KNOWLEDGE_BASE_CONFIG = $configPath
    & $PythonExecutable -m nanobot webui
    if ($LASTEXITCODE -ne 0) { throw "nanobot WebUI exited with code $LASTEXITCODE" }
}
finally {
    Pop-Location
    if ($hadConfig) { $env:KNOWLEDGE_BASE_CONFIG = $previousConfig }
    else { Remove-Item Env:KNOWLEDGE_BASE_CONFIG -ErrorAction SilentlyContinue }
}
