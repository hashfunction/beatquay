# Copyright 2026 Trieflow LLC. MIT. Disposable package qualification only.
[CmdletBinding()] param([Parameter(Mandatory)][string]$Python)
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
if(-not $IsWindows -or $env:CI -ne 'true' -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Requires disposable Windows CI and PowerShell 7.'}
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
function Invoke-Checked([string]$Program,[string[]]$Arguments){& $Program @Arguments|Out-Host;if($LASTEXITCODE -ne 0){throw "$Program failed with exit $LASTEXITCODE"}}
$pythonPath=(Resolve-Path -LiteralPath $Python).Path; $powerShell=(Get-Process -Id $PID).Path
Invoke-Checked $pythonPath @('cmake/msix/test_msix_qualification.py','-v')
Invoke-Checked $pythonPath @('cmake/msix/test_consumer_files.py','-v')
foreach($fixture in @('test_qualify_msix_install.ps1','test_appx_preflight.ps1','test_msix_evidence.ps1','test_registration_ownership.ps1','test_process_observation.ps1','test_window_evidence.ps1','test_first_run_flow.ps1','test_defender_module.ps1','test_temporary_ownership.ps1','test_consumer_workflow.ps1','test_consumer_tempo.ps1','test_consumer_display.ps1')){Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File',(Join-Path $PSScriptRoot $fixture))}
$sourceCommit=(git rev-parse HEAD).Trim(); if($LASTEXITCODE -ne 0 -or $sourceCommit -cne $env:GITHUB_SHA){throw 'Source differs from this qualification run.'}
$sdkVersion='10.0.26100.0'; $sdkDirectory=Join-Path ${env:ProgramFiles(x86)} "Windows Kits/10/bin/$sdkVersion/x64"
$packageOutput=Join-Path $env:RUNNER_TEMP ('beatquay-msix-'+[guid]::NewGuid().ToString('N'))
Invoke-Checked $pythonPath @('cmake/msix/msix_qualification.py','--release','stage','--artwork','data/branding/beatquay-256.png','--source-root','.','--source-commit',$sourceCommit,'--inventory','build-evidence/package-input.json','--evidence-root','build-evidence','--makeappx',(Join-Path $sdkDirectory 'makeappx.exe'),'--sdk-version',$sdkVersion,'--output',$packageOutput)
[IO.File]::Copy((Join-Path $packageOutput 'package-record.json'),(Join-Path (Get-Location) 'build-evidence/msix-package-record.json'),$false)
Invoke-Checked $powerShell @('-NoLogo','-NoProfile','-File','cmake/msix/qualify-msix-install.ps1','-Package',(Join-Path $packageOutput 'BeatSprig.Qualification_1.0.1.0_x64.msix'),'-PackageRecord',(Join-Path $packageOutput 'package-record.json'),'-SignTool',(Join-Path $sdkDirectory 'signtool.exe'),'-Output','build-evidence/msix-install','-Python',$pythonPath)
