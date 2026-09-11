$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows -or $env:CI -ne 'true') { throw 'Requires a disposable Windows CI runner.' }
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force build-evidence | Out-Null
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program exited $LASTEXITCODE" }
}
$lock = Get-Content distribution/candidate-inputs.json -Raw | ConvertFrom-Json
if ((git -C .ci-vcpkg rev-parse HEAD) -ne $lock.vcpkg.commit) { throw 'vcpkg revision mismatch.' }
$submodules = @(git submodule status --recursive)
if ($LASTEXITCODE -ne 0 -or @($submodules | Where-Object { -not $_.StartsWith(' ') }).Count) { throw 'Submodules are missing or changed.' }
foreach ($item in $lock.submodules) {
    if ((git -C $item.path rev-parse HEAD) -ne $item.commit) { throw "Submodule revision mismatch: $($item.path)" }
}
$submodules | Set-Content build-evidence/submodules.txt
Invoke-Checked ./.ci-vcpkg/bootstrap-vcpkg.bat @('-disableMetrics')
$env:VCPKG_ROOT = Join-Path (Get-Location) '.ci-vcpkg'
$env:VCPKG_DOWNLOADS = Join-Path (Get-Location) '.ci-vcpkg/downloads'
Invoke-Checked cmake @('--version')
cmake --version | Set-Content build-evidence/cmake.txt
ninja --version | Set-Content build-evidence/ninja.txt
cl 2>&1 | Out-String | Set-Content build-evidence/compiler.txt
qmake -query | Set-Content build-evidence/qt.txt
$flags = @('-S','.','-B','build','-G','Ninja','--toolchain',"$env:VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake",'-DCMAKE_BUILD_TYPE=RelWithDebInfo','-DTARGET_UARCH=official','-DWANT_QT6=ON','-DUSE_WERROR=ON','-DFORCE_VERSION=internal','-DLMMS_MINIMAL=ON','-DVCPKG_TARGET_TRIPLET=x64-windows','-DVCPKG_HOST_TRIPLET=x64-windows','-DWANT_CARLA=OFF','-DWANT_LV2=OFF','-DWANT_SUIL=OFF','-DWANT_JACK=OFF','-DWANT_WEAKJACK=OFF','-DWANT_SDL=OFF','-DWANT_STK=OFF','-DWANT_GIG=OFF','-DWANT_SF2=OFF','-DWANT_VST=OFF','-DWANT_VST_32=OFF','-DWANT_VST_64=OFF','-DWANT_CALF=OFF','-DWANT_CAPS=OFF','-DWANT_CMT=OFF','-DWANT_SWH=OFF','-DWANT_TAP=OFF','-DWANT_SID=OFF')
$flags | Set-Content build-evidence/configure-flags.txt
try {
    Invoke-Checked cmake $flags
    Invoke-Checked cmake @('--build','build','--parallel','2')
    $env:PATH = "$(Get-Location)/build;$(Get-Location)/build/vcpkg_installed/x64-windows/bin;$env:PATH"
    Invoke-Checked ctest @('--test-dir','build/tests','--timeout','60','--output-on-failure','--output-junit',"$(Get-Location)/build-evidence/tests.xml")
    Invoke-Checked cmake @('--install','build','--prefix',"$(Get-Location)/stage")
    Get-ChildItem stage -Recurse -File | ForEach-Object {
        @{ path=[IO.Path]::GetRelativePath((Join-Path (Get-Location) 'stage'), $_.FullName); bytes=$_.Length; sha256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash }
    } | ConvertTo-Json -Depth 3 | Set-Content build-evidence/stage-inventory.json
    @{ source_commit=$env:GITHUB_SHA; candidate=$lock.candidate; built=$true; tests_passed=$true; installed_stage=$true; modernization_accepted=$false; physical_audio_verified=$false; source_license_closure=$false; store_submitted=$false } | ConvertTo-Json | Set-Content build-evidence/result.json
} finally {
    Get-ChildItem .ci-vcpkg/downloads -File -ErrorAction SilentlyContinue | ForEach-Object {
        @{ file=$_.Name; bytes=$_.Length; sha256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash }
    } | ConvertTo-Json -Depth 3 | Set-Content build-evidence/dependency-downloads.json
    if (Test-Path build/vcpkg_installed/vcpkg/status) { Copy-Item build/vcpkg_installed/vcpkg/status build-evidence/vcpkg-installed-status.txt }
    Get-ChildItem build/vcpkg_installed/x64-windows/share -Recurse -File -Filter copyright -ErrorAction SilentlyContinue | ForEach-Object {
        $dest=Join-Path build-evidence/notices $_.Directory.Name
        New-Item -ItemType Directory -Force $dest | Out-Null
        Copy-Item $_.FullName (Join-Path $dest 'copyright.txt')
    }
}
