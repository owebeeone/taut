. 'D:/projects/limbo/toolchain-readiness-2026-11-02/Activate-TautToolchains.ps1'
$env:PYTHONPATH='D:/projects/limbo/taut-dev/taut/src;C:/Users/gianni/AppData/Local/Programs/Python/Python311/Lib/site-packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TEMP='D:/projects/limbo/swift-oneof-scratch/remediation-r1/tmp'
$env:TMP=$env:TEMP
$env:GOCACHE='D:/projects/limbo/swift-oneof-scratch/remediation-r1/gocache'
$env:GOMODCACHE='D:/projects/limbo/swift-oneof-scratch/remediation-r1/gomodcache'
$env:XDG_CONFIG_HOME='D:/projects/limbo/swift-oneof-scratch/gwz-xdg'
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
