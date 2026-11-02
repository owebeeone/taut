param([switch]$AllRegression, [switch]$Parity)
$ErrorActionPreference = 'Stop'
$exampleRoot = $PSScriptRoot
$limboRoot = (Resolve-Path (Join-Path $exampleRoot '../../../../..')).Path
. (Join-Path $limboRoot 'toolchain-readiness-2026-11-02/Activate-TautToolchains.ps1')
$tautRoot = (Resolve-Path (Join-Path $exampleRoot '../../..')).Path
$shapeRoot = Join-Path (Split-Path $tautRoot) 'taut-shape-py'
$pytestPackages = Join-Path $env:LOCALAPPDATA 'Programs/Python/Python311/Lib/site-packages'
$env:PYTHONPATH = "$tautRoot/src;$shapeRoot/src;$pytestPackages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:JAVA_TOOL_OPTIONS = '-Dfile.encoding=UTF-8'
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'safe.directory'
$env:GIT_CONFIG_VALUE_0 = $tautRoot.Replace('\','/')
$env:TEMP = Join-Path $exampleRoot 'scratch'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$resultsRoot = Join-Path $exampleRoot 'results'
New-Item -ItemType Directory -Force -Path $resultsRoot | Out-Null

function Invoke-RecordedPython([string]$Log, [string[]]$PythonArgs) {
    & python @PythonArgs 2>&1 | Tee-Object -FilePath (Join-Path $resultsRoot $Log)
    if ($LASTEXITCODE -ne 0) { throw "Python check failed ($LASTEXITCODE): $($PythonArgs -join ' ')" }
}

Invoke-RecordedPython 'feature-tests.log' @('-m','pytest', "$tautRoot/src/tests/test_oneof.py", "$tautRoot/src/tests/test_python_runtime_distribution.py", '-q')
Invoke-RecordedPython 'shape-tests.log' @('-m','pytest', "$shapeRoot/tests", '-q')
Invoke-RecordedPython 'generate.log' @("$exampleRoot/generate_examples.py")
Invoke-RecordedPython 'source-examples.log' @('-I','-S','-B', "$exampleRoot/inspect_examples.py", '--mode','source')
Invoke-RecordedPython 'package-examples.log' @('-I','-S','-B', "$exampleRoot/inspect_examples.py", '--mode','package', '--runtime-root', "$tautRoot/src")
Invoke-RecordedPython 'disabled-examples.log' @('-I','-S','-B', "$exampleRoot/inspect_examples.py", '--mode','disabled')
if ($AllRegression) {
    Invoke-RecordedPython 'regression-tests.log' @('-m','pytest', "$tautRoot/src/tests", '-q','-m','not gate')
}
if ($Parity) {
    Invoke-RecordedPython 'codec-parity.log' @('-m','taut.cli','parity','--require-all','--jobs','2')
}
