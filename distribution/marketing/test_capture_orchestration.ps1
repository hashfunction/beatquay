# Copyright 2026 Trieflow LLC. MIT. Production closures with file/native boundaries isolated.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$folder=$PSScriptRoot;$source=[IO.Path]::GetFullPath((Join-Path $folder '../..'))
. (Join-Path $source 'cmake/msix/qualify-msix-install.ps1') -LibraryOnly
. (Join-Path $folder 'capture.ps1') -LibraryOnly
function Check($Value,$Message){if(-not $Value){throw $Message}}
function Reject([scriptblock]$Action,[string]$Expected){try{& $Action;throw 'missing refusal'}catch{if($_.Exception.Message -notlike "*$Expected*"){throw}}}
# Retain the actual operation closures without executing platform effects.
function Invoke-BeatQuayQualificationCore($Operations){$script:operations=$Operations;throw 'fixture operations retained'}
$Python=(Get-Command python3).Source;$QualifiedSource=$source;$Inputs='fixture inputs';$Output='fixture output';$ShellReceipt='fixture shell';$originalScreen={}
Reject {Invoke-BeatSprigMarketingCapture} 'fixture operations retained'
$state=$script:operations.Preflight.Module.SessionState.PSVariable.GetValue('state')
Check ($null -ne $state -and $state.identityMode -ceq 'store') 'Exact Store state not captured'
Check ($state.python -ceq $Python -and $state.qualifiedSource -ceq $source) 'Capture dependency arguments were lost in closure'
$script:calls=[Collections.Generic.List[string]]::new()
function Assert-BeatQuayWindowsCi {$script:calls.Add('ci')}
function Invoke-CheckedNative($Program,$Arguments){$script:calls.Add('verify');throw 'original inputs refused'}
$env:GITHUB_EVENT_NAME='workflow_dispatch';$env:GITHUB_REPOSITORY='hashfunction/beatquay'
Reject {& $script:operations.Preflight} 'original inputs refused'
Check (($script:calls -join ',') -ceq 'ci,verify' -and -not $state.output -and -not $state.temporary -and -not $state.installAttempted) 'Preflight refusal mutated capture state'
# Execute real owned-file cleanup through the production cleanup closure.
function Invoke-CheckedNative($Program,$Arguments){& $Program @Arguments;if($LASTEXITCODE -ne 0){throw 'owned file command refused'}}
$work=Join-Path ([IO.Path]::GetTempPath()) ('beatsprig-capture-core-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work|Out-Null
try{
 $state.output=$work;$state.demoRecord=Join-Path $work 'owned-demo.json';$demo=Join-Path $work 'demo'
 Invoke-CheckedNative $Python @((Join-Path $folder 'owned_files.py'),'create','--root',$demo,'--kind','demo','--record',$state.demoRecord)
 $state.process=[pscustomobject]@{Id=1};$state.processOwned=$false
 Reject {& $script:operations.RemoveTemporaryFiles} 'termination unproven'
 Check (Test-Path $demo) 'Unowned process allowed cleanup'
 $state.process=$null
 [IO.File]::WriteAllText((Join-Path $demo 'foreign.txt'),'preserve')
 Reject {& $script:operations.RemoveTemporaryFiles} 'owned file command refused'
 Check (Test-Path (Join-Path $demo 'foreign.txt')) 'Untracked file was removed'
 Remove-Item -LiteralPath (Join-Path $demo 'foreign.txt')
 & $script:operations.RemoveTemporaryFiles
 Check (-not (Test-Path $demo) -and $state.ownedFilesCleaned) 'Marker-only failure cleanup did not finish'
}finally{Remove-Item -LiteralPath $work -Recurse -Force}
Write-Output 'PASS: capture closure bindings, immediate preflight refusal, retained process and exact owned-tree cleanup boundaries'
