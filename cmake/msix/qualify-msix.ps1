# Copyright 2026 Trieflow LLC. MIT. Two fixed-identity disposable installation lifecycles.
[CmdletBinding()] param([Parameter(Mandatory)][string]$Python)
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
if(-not $IsWindows -or $env:CI -ne 'true' -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Requires disposable Windows CI and PowerShell 7.'}
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
. (Join-Path $PSScriptRoot 'qualification-bindings.ps1')
function Invoke-Checked([string]$Program,[string[]]$Arguments){& $Program @Arguments|Out-Host;if($LASTEXITCODE -ne 0){throw "$Program failed with exit $LASTEXITCODE"}}
$pythonPath=(Resolve-Path -LiteralPath $Python).Path; $powerShell=(Get-Process -Id $PID).Path
Invoke-Checked $pythonPath @('cmake/msix/test_msix_qualification.py','-v')
Invoke-Checked $pythonPath @('cmake/msix/test_consumer_files.py','-v')
foreach($fixture in @('test_source_publication.py','test_store_workflow_evidence.py','test_export_store_package.py')){Invoke-Checked $pythonPath @((Join-Path $PSScriptRoot $fixture),'-v')}
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File',(Join-Path $PSScriptRoot 'test_module_rejection.ps1'))
foreach($fixture in @('test_qualify_msix_install.ps1','test_store_identity.ps1','test_store_export_dispatch.ps1','test_appx_preflight.ps1','test_msix_evidence.ps1','test_registration_ownership.ps1','test_process_observation.ps1','test_window_evidence.ps1','test_first_run_flow.ps1','test_defender_module.ps1','test_temporary_ownership.ps1','test_consumer_workflow.ps1','test_consumer_export_combo.ps1','test_consumer_tempo.ps1','test_consumer_dialogs.ps1','test_consumer_dialog_enumeration.ps1','test_consumer_display.ps1')){Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File',(Join-Path $PSScriptRoot $fixture))}
$sourceCommit=(git rev-parse HEAD).Trim(); if($LASTEXITCODE -ne 0 -or $sourceCommit -cne $env:GITHUB_SHA){throw 'Source differs from this qualification run.'}
$null=Get-BeatQuayRunBinding $sourceCommit $env:GITHUB_RUN_ID $env:GITHUB_RUN_ATTEMPT
$exportRequested=$env:BEATSPRIG_EXPORT_STORE_PACKAGE
if($exportRequested -cnotin @($null,'','false','true')){throw 'Malformed Store export opt-in.'}
if($exportRequested -ceq 'true' -and ($env:GITHUB_EVENT_NAME -cne 'workflow_dispatch' -or
    $env:BEATSPRIG_REVIEWED_PUBLIC_SOURCE -cnotmatch '^[0-9a-f]{40}$' -or
    $env:BEATSPRIG_REVIEWED_PUBLIC_SOURCE -cne $sourceCommit)){throw 'Store export requires an exact reviewed public-source workflow dispatch.'}
$packagePaths=[ordered]@{}
$sdkVersion='10.0.26100.0'; $sdkDirectory=Join-Path ${env:ProgramFiles(x86)} "Windows Kits/10/bin/$sdkVersion/x64"
Invoke-BeatQuayIdentityLifecycles {
    param($mode)
    $packageOutput=Join-Path $env:RUNNER_TEMP ('beatsprig-msix-'+$mode+'-'+[guid]::NewGuid().ToString('N'))
    $packageName=if($mode -ceq 'store'){'BeatSprig_1.0.1.0_x64.msix'}else{'BeatSprig.Qualification_1.0.1.0_x64.msix'}
    $recordOutput=if($mode -ceq 'store'){'build-evidence/msix-store-package-record.json'}else{'build-evidence/msix-package-record.json'}
    $installationOutput=if($mode -ceq 'store'){'build-evidence/msix-store-install'}else{'build-evidence/msix-install'}
    Invoke-Checked $pythonPath @('cmake/msix/msix_qualification.py','--release','stage','--artwork','data/branding/beatquay-256.png','--source-root','.','--source-commit',$sourceCommit,'--inventory','build-evidence/package-input.json','--evidence-root','build-evidence','--makeappx',(Join-Path $sdkDirectory 'makeappx.exe'),'--sdk-version',$sdkVersion,'--output',$packageOutput,'--identity-mode',$mode)
    [IO.File]::Copy((Join-Path $packageOutput 'package-record.json'),(Join-Path (Get-Location) $recordOutput),$false)
    # The complete lifecycle returns only after normal close, uninstall, unsigned
    # preservation and every owned cleanup check; a failure stops the next mode.
    Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','cmake/msix/qualify-msix-install.ps1','-Package',(Join-Path $packageOutput $packageName),'-PackageRecord',(Join-Path $packageOutput 'package-record.json'),'-SignTool',(Join-Path $sdkDirectory 'signtool.exe'),'-Output',$installationOutput,'-Python',$pythonPath,'-IdentityMode',$mode)
    $packagePaths[$mode]=Join-Path $packageOutput $packageName
}
if($exportRequested -ceq 'true'){
    Invoke-Checked $pythonPath @('cmake/msix/export_store_package.py','--qualification-package',$packagePaths.qualification,'--store-package',$packagePaths.store,'--reviewed-public-source',$env:BEATSPRIG_REVIEWED_PUBLIC_SOURCE)
}
