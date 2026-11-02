$ErrorActionPreference = 'Stop'
. 'D:/projects/limbo/toolchain-readiness-2026-11-02/Activate-TautToolchains.ps1'
$gateRoot = 'D:/projects/limbo/swift-oneof-scratch/global-gate-r0'
$env:TEMP = "$gateRoot/tmp"
$env:TMP = $env:TEMP
$env:GOCACHE = "$gateRoot/go-cache"
$env:GOTMPDIR = "$gateRoot/go-tmp"
$env:npm_config_cache = "$gateRoot/npm-cache"
$env:PYTHONPATH = "$gateRoot;D:/projects/limbo/taut-dev/taut/src;C:/Users/gianni/AppData/Local/Programs/Python/Python311/Lib/site-packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
$env:JAVA_TOOL_OPTIONS = '-Dfile.encoding=UTF-8'
$env:GIT_OPTIONAL_LOCKS = '0'
$env:XDG_CONFIG_HOME = "$gateRoot/gwz-xdg"
$env:GIT_CONFIG_GLOBAL = "$gateRoot/gwz-xdg/git/config"
$gateRepositories = @('D:/projects/limbo/taut-dev','D:/projects/limbo/taut-dev/taut','D:/projects/limbo/taut-dev/taut-shape-py','D:/projects/limbo/taut-dev/taut-shape-rs','D:/projects/limbo/taut-dev/taut-shape-ts')
New-Item -ItemType Directory -Force -Path $env:TEMP,$env:GOCACHE,$env:GOTMPDIR,"$gateRoot/gwz-xdg/git" | Out-Null
$gateGitLines = @('[safe]') + @($gateRepositories | ForEach-Object { "    directory = $_" })
[System.IO.File]::WriteAllText($env:GIT_CONFIG_GLOBAL,($gateGitLines -join "`n")+"`n",[System.Text.UTF8Encoding]::new($false))
$env:GIT_CONFIG_COUNT = '5'
for ($gateIndex=0; $gateIndex -lt $gateRepositories.Length; $gateIndex++) {
    [Environment]::SetEnvironmentVariable("GIT_CONFIG_KEY_$gateIndex",'safe.directory','Process')
    [Environment]::SetEnvironmentVariable("GIT_CONFIG_VALUE_$gateIndex",$gateRepositories[$gateIndex],'Process')
}
Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
Remove-Item Env:PYTEST_PLUGINS -ErrorAction SilentlyContinue
Set-Location $gateRoot
python "$gateRoot/run-global-gate.py" 2>&1 | Tee-Object -FilePath "$gateRoot/gate-console.log"
exit $LASTEXITCODE
