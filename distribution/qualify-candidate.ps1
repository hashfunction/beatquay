$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows -or $env:CI -ne 'true') { throw 'Requires a disposable Windows CI runner.' }
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force build-evidence | Out-Null
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program exited $LASTEXITCODE" }
}
$sourceCommit=(git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $sourceCommit -cne $env:GITHUB_SHA) { throw 'Source differs from this qualification run.' }
. (Join-Path $PSScriptRoot '../cmake/msix/qualification-bindings.ps1')
$runBinding=Get-BeatQuayRunBinding $sourceCommit $env:GITHUB_RUN_ID $env:GITHUB_RUN_ATTEMPT
$sourceStatus=@(git status --porcelain --untracked-files=all)
$sourceStatusExit=$LASTEXITCODE
Set-Content -LiteralPath build-evidence/source-status-before-build.txt -Value $sourceStatus -Encoding utf8
Set-Content -LiteralPath build-evidence/source-status-exit-code.txt -Value $sourceStatusExit -Encoding utf8
if ($sourceStatusExit -ne 0 -or $sourceStatus.Count) { throw 'Source checkout must be clean before native build and package evidence collection.' }
$lock = Get-Content distribution/candidate-inputs.json -Raw | ConvertFrom-Json
Invoke-Checked python @('tests/scripted/test_source_checkout.py','-v')
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
    Invoke-Checked cmake @('--build','build','--parallel','2','--','-k','0')
    $env:PATH = "$(Get-Location)/build;$(Get-Location)/build/vcpkg_installed/x64-windows/bin;$env:PATH"
    $testInventory = & ctest --test-dir build/tests --show-only=json-v1
    if ($LASTEXITCODE -ne 0) { throw 'Unable to inventory native test suites.' }
    $registeredTests = ($testInventory | ConvertFrom-Json).tests
    if ('BeatQuayTemplateTest' -notin @($registeredTests.name)) { throw 'Required native starter-template suite is absent.' }
    Invoke-Checked ctest @('--test-dir','build/tests','--no-tests=error','--timeout','60','--output-on-failure','--output-junit',"$(Get-Location)/build-evidence/tests.xml")
    Invoke-Checked ctest @('--test-dir','build/tests','-R','^RenderManagerLifecycleTest$','--no-tests=error','--repeat','until-fail:10','--timeout','60','--output-on-failure','--output-log',"$(Get-Location)/build-evidence/lifecycle-repeat.log",'--output-junit',"$(Get-Location)/build-evidence/lifecycle-repeat.xml")
    Invoke-Checked cmake @('--install','build','--prefix',"$(Get-Location)/stage")
    Get-ChildItem stage -Recurse -File | ForEach-Object {
        @{ path=[IO.Path]::GetRelativePath((Join-Path (Get-Location) 'stage'), $_.FullName); bytes=$_.Length; sha256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash }
    } | ConvertTo-Json -Depth 3 | Set-Content build-evidence/stage-inventory.json
    Invoke-Checked python @('-m','unittest','discover','-s','tests/scripted','-p','test_candidate_render.py')
    Invoke-Checked python @('tests/scripted/candidate_render.py','--executable',"$(Get-Location)/stage/beatsprig.exe",'--stage',"$(Get-Location)/stage",'--work',"$(Get-Location)/.cache/native-render-smoke",'--evidence',"$(Get-Location)/build-evidence")
    Invoke-Checked python @('distribution/generate_starters.py','--check')
    Invoke-Checked python @('-m','unittest','discover','-s','tests/scripted','-p','test_starter*.py','-v')
    Invoke-Checked python @('tests/scripted/starter_render.py','--source',"$(Get-Location)",'--stage',"$(Get-Location)/stage",'--work',"$(Get-Location)/.cache/native-starter-smoke",'--evidence',"$(Get-Location)/build-evidence")
    @{ source_commit=$sourceCommit; workflow_run_id=$runBinding.workflow_run_id; workflow_run_attempt=$runBinding.workflow_run_attempt; candidate=$lock.candidate; built=$true; tests_passed=$true; lifecycle_repeat_passed=$true; lifecycle_repeat_count=10; installed_stage=$true; native_render_smoke_passed=$true; native_render_error_exit_passed=$true; native_installed_starter_renders_passed=$true; starter_template_suite_required=$true; modernization_accepted=$false; physical_audio_verified=$false; source_license_closure=$false; store_submitted=$false } | ConvertTo-Json | Set-Content build-evidence/result.json
} finally {
    $qtReports = @(Get-ChildItem build/tests -File -Filter '*.qt-test.*' -ErrorAction SilentlyContinue)
    if ($qtReports.Count) {
        New-Item -ItemType Directory -Force build-evidence/qt-tests | Out-Null
        $qtReports | Copy-Item -Destination build-evidence/qt-tests
    }
    Get-ChildItem .qt-archives -File -ErrorAction SilentlyContinue | ForEach-Object {
        @{ file=$_.Name; bytes=$_.Length; sha256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash }
    } | ConvertTo-Json -Depth 3 | Set-Content build-evidence/qt-downloads.json
    Get-ChildItem .ci-vcpkg/downloads -File -ErrorAction SilentlyContinue | ForEach-Object {
        @{ file=$_.Name; bytes=$_.Length; sha256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash }
    } | ConvertTo-Json -Depth 3 | Set-Content build-evidence/dependency-downloads.json
    if (Test-Path build/vcpkg_installed/vcpkg/status) { Copy-Item build/vcpkg_installed/vcpkg/status build-evidence/vcpkg-installed-status.txt }
}

# Packaging runs only after the native try/finally completed successfully and
# all same-run evidence inputs exist. Package binaries remain runner-private.
$noticeRoot=Join-Path (Get-Location) 'build-evidence/notices'
if (Test-Path -LiteralPath $noticeRoot) { throw 'Dependency notice output already exists and will not be replaced.' }
New-Item -ItemType Directory -Path (Join-Path $noticeRoot 'vcpkg') | Out-Null
Get-ChildItem build/vcpkg_installed/x64-windows/share -Recurse -File -Filter copyright -ErrorAction SilentlyContinue | ForEach-Object {
    $dest=Join-Path $noticeRoot "vcpkg/$($_.Directory.Name)"
    New-Item -ItemType Directory -Path $dest | Out-Null
    [IO.File]::Copy($_.FullName,(Join-Path $dest 'copyright.txt'),$false)
}
$qtNoticeArguments=@('distribution/collect_qt_notices.py','--version',[string]$lock.qt.version,'--output',(Join-Path $noticeRoot 'qt'))
foreach ($archive in $lock.qt.archives) {
    $qtNoticeArguments += @('--module',[string]$archive)
}
Invoke-Checked python $qtNoticeArguments
Invoke-Checked python @('-m','unittest','discover','-s','tests/scripted','-p','test_qt_notices.py','-v')
Invoke-Checked python @('-m','unittest','discover','-s','tests/scripted','-p','test_native_source.py','-v')
Invoke-Checked python @('tests/scripted/test_license_resource.py','-v')
Invoke-Checked python @('distribution/native_source.py','collect','--source',"$(Get-Location)",
    '--evidence',"$(Get-Location)/build-evidence",'--downloads',"$(Get-Location)/.ci-vcpkg/downloads",
    '--source-commit',$sourceCommit,'--output',(Join-Path $noticeRoot 'native'))
if (@(Get-ChildItem -LiteralPath (Join-Path $noticeRoot 'vcpkg') -Recurse -File).Count -eq 0 -or
    @(Get-ChildItem -LiteralPath (Join-Path $noticeRoot 'qt') -Recurse -File).Count -eq 0) {
    throw 'Actual Qt and vcpkg dependency notice collections must both be nonempty.'
}
$powerShell=(Get-Process -Id $PID).Path
Copy-Item -LiteralPath build/ms-runtime-selection.json -Destination build-evidence/ms-runtime-selection.json
Invoke-Checked python @('-m','unittest','discover','-s','cmake/msix','-p','test_ms_runtime_origins.py','-v')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','cmake/msix/test_ms_runtime_collection.ps1')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','cmake/msix/collect-ms-runtime-origins.ps1',
    '-Selection','build-evidence/ms-runtime-selection.json','-Stage','stage','-SourceCommit',$sourceCommit,
    '-Output','build-evidence/ms-runtime-origins.json')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','cmake/msix/test_api_set_resolution.ps1')
Invoke-Checked python @('cmake/msix/test_pe_import_collection.py','--powershell',$powerShell,'-v')
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','cmake/msix/collect-pe-imports.ps1','-Stage','stage','-Output','build-evidence/pe-imports.json')
Invoke-Checked python @('cmake/msix/prepare_inventory.py','--source-commit',$sourceCommit)
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','cmake/msix/qualify-msix.ps1','-Python',(Get-Command python).Source)
