param([switch]$AllRegression, [switch]$Parity)
$ErrorActionPreference='Stop'
$exampleRoot=$PSScriptRoot
$tautRoot=(Resolve-Path (Join-Path $exampleRoot '../../..')).Path
$limboRoot=(Resolve-Path (Join-Path $tautRoot '../..')).Path
. (Join-Path $limboRoot 'toolchain-readiness-2026-11-02/Activate-TautToolchains.ps1')
$shapeRoot=Join-Path (Split-Path $tautRoot) 'taut-shape-rs'
$pytestPackages=Join-Path $env:LOCALAPPDATA 'Programs/Python/Python311/Lib/site-packages'
$env:PYTHONPATH="$tautRoot/src;$pytestPackages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:JAVA_TOOL_OPTIONS='-Dfile.encoding=UTF-8'
$env:GIT_CONFIG_COUNT='1'
$env:GIT_CONFIG_KEY_0='safe.directory'
$env:GIT_CONFIG_VALUE_0=$tautRoot.Replace('\','/')
$env:TEMP=Join-Path $exampleRoot 'scratch'
$env:TMP=$env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$resultsRoot=Join-Path $exampleRoot 'results'
New-Item -ItemType Directory -Force -Path $resultsRoot | Out-Null

function Invoke-Recorded([string]$Log,[string]$Command,[string[]]$Arguments) {
    & $Command @Arguments 2>&1 | Tee-Object -FilePath (Join-Path $resultsRoot $Log)
    if ($LASTEXITCODE -ne 0) { throw "Check failed ($LASTEXITCODE): $Command $($Arguments -join ' ')" }
}

Invoke-Recorded 'canonical-inventory.log' 'python' @("$tautRoot/rust/sync_foundation.py",'--check')
Invoke-Recorded 'feature-regression-tests.log' 'python' @('-m','pytest',"$tautRoot/src/tests/test_rust_oneof.py", "$tautRoot/src/tests/test_rust.py", "$tautRoot/src/tests/test_rust_external_types.py", "$tautRoot/src/tests/test_oneof.py", "$tautRoot/src/tests/test_python_runtime_distribution.py", "$tautRoot/src/tests/test_scaffold.py",'-q')
Invoke-Recorded 'foundation-no-std.log' 'cargo' @('check','--offline','--manifest-path',"$tautRoot/rust/taut-foundation/Cargo.toml",'--no-default-features')
Invoke-Recorded 'foundation-clippy.log' 'cargo' @('clippy','--offline','--manifest-path',"$tautRoot/rust/taut-foundation/Cargo.toml",'--all-features','--','-D','warnings')
Invoke-Recorded 'shape-no-std.log' 'cargo' @('check','--offline','--manifest-path',"$shapeRoot/Cargo.toml",'-p','taut-shape','--no-default-features')
# The unchanged Rust test invokes python3, which is a Windows Store alias on
# this host. Execute its exact checker with the verified stable Python instead.
Invoke-Recorded 'shape-process-globals.log' 'python' @("$shapeRoot/scripts/checks/check_process_globals.py",'--repo',$shapeRoot)
Invoke-Recorded 'shape-tests.log' 'cargo' @('test','--offline','--manifest-path',"$shapeRoot/Cargo.toml",'--workspace','--all-features','--','--skip','no_new_process_global_state')
Invoke-Recorded 'shape-clippy.log' 'cargo' @('clippy','--offline','--manifest-path',"$shapeRoot/Cargo.toml",'--all-targets','--all-features','--','-D','warnings')
Invoke-Recorded 'examples.log' 'python' @("$exampleRoot/generate_examples.py")
Invoke-Recorded 'package-build.log' 'python' @("$exampleRoot/verify_package.py")
if ($Parity) {
    Invoke-Recorded 'codec-parity.log' 'python' @('-m','taut.cli','parity','--require-all','--jobs','2')
}
if ($AllRegression) {
    Invoke-Recorded 'broad-regression-tests.log' 'python' @('-m','pytest',"$tautRoot/src/tests",'-q','-m','not gate')
}
