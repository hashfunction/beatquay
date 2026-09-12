# Copyright 2026 Trieflow LLC. MIT. Test-only screen delegate; no rendered pixels claimed.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$implementation=Join-Path $PSScriptRoot 'capture_observer.ps1'
if(-not (Test-Path $implementation)){throw 'Retained original capture observer is not implemented'}
. $implementation
function Check($Value,$Message){if(-not $Value){throw $Message}}
function Reject([scriptblock]$Action){$failed=$false;try{& $Action}catch{$failed=$true};Check $failed 'Expected refusal did not occur'}
$work=Join-Path ([IO.Path]::GetTempPath()) ('beatsprig-observer-fixture-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $work 'cmake/msix')|Out-Null
$file=Join-Path $work 'cmake/msix/consumer-workflow.ps1'
try{
 $text=@'
function Save-BeatQuayConsumerScreen($State,[string]$Name,[string]$EditorTitle,[string[]]$AllowedDialogs=@()) {
 $State.original_calls++
 $State.workflow.screenshots.Add(@{file=$Name+'.png';project_title=$EditorTitle;allowed_dialogs=$AllowedDialogs;
  process_id=744;main_window_handle=10;foreground_window=10;x=0;y=0;width=$State.capture_width;height=901;dpi=96;display=@{width=1920;height=1080}})
}
'@
 [IO.File]::WriteAllText($file,$text)
 . $file
 $original=(Get-Command Save-BeatQuayConsumerScreen).ScriptBlock
 $sourceRecord=@{bytes=(Get-Item $file).Length;sha256=(Get-FileHash $file).Hash.ToLowerInvariant()}
 $state=@{qualifiedSource=$work;record=@{sourceInputs=@{'cmake/msix/consumer-workflow.ps1'=$sourceRecord}};original_calls=0;capture_width=1456;
  workflow=@{screenshots=[Collections.Generic.List[object]]::new();current_action='save_original_project'};captureFrames=[Collections.Generic.List[object]]::new()}
 function Assert-FileMatchesRecord($Path,$Record,$Label){
  if((Get-Item $Path).Length -ne $Record.bytes -or (Get-FileHash $Path).Hash.ToLowerInvariant() -cne $Record.sha256){throw 'Changed qualified source bytes'}
 }
 function Assert-NoReparsePath($Path){if((Get-Item $Path).LinkType){throw 'Linked source'}}
 $state.originalScreen=New-BeatSprigOriginalScreen $state $original
 $script:frameCalls=0;$script:failFrameAt=0;$script:changeAfter=$false
 function Read-BeatSprigMarketingFrame($State,$Title,$Dialogs){
  $script:frameCalls++
  if($script:frameCalls -eq $script:failFrameAt){throw 'Frame no longer owned'}
  return @{main_pid=744;main_handle=10;foreground_pid=744;foreground_handle=if($script:changeAfter -and $script:frameCalls%2 -eq 0){11}else{10};
   title=$Title;dpi=96;x=0;y=0;width=1456;height=901;display=@{width=1920;height=1080};observed_utc=[DateTime]::UtcNow.ToString('o')}
 }
 Invoke-BeatSprigOriginalScreen $state '01-evening-pulse-project' 'Evening Pulse - BeatSprig 1.0.1' @()
 Check ($state.original_calls -eq 1 -and $state.captureFrames.Count -eq 1 -and $script:frameCalls -eq 2) 'Original delegate or frame sequencing differs'
 $script:failFrameAt=3
 Reject {Invoke-BeatSprigOriginalScreen $state '01-evening-pulse-project' 'Evening Pulse - BeatSprig 1.0.1' @()}
 Check ($state.original_calls -eq 1) 'Original screen helper ran after before-frame refusal'
 $script:failFrameAt=0;$script:frameCalls=0;$script:changeAfter=$true
 Reject {Invoke-BeatSprigOriginalScreen $state '01-evening-pulse-project' 'Evening Pulse - BeatSprig 1.0.1' @()}
 Check ($state.original_calls -eq 2 -and $state.captureFrames.Count -eq 1) 'Changed after-frame was accepted or capture was retried'
 $script:changeAfter=$false
 [IO.File]::AppendAllText($file,'# source mutation')
 Reject {Invoke-BeatSprigOriginalScreen $state '01-evening-pulse-project' 'Evening Pulse - BeatSprig 1.0.1' @()}
 Check ($state.original_calls -eq 2) 'Changed original source ran'
 [IO.File]::WriteAllText($file,$text)
 $retained=$state.originalScreen.scriptblock;$state.originalScreen.scriptblock={throw 'substituted'}
 Reject {Invoke-BeatSprigOriginalScreen $state '01-evening-pulse-project' 'Evening Pulse - BeatSprig 1.0.1' @()}
 $state.originalScreen.scriptblock=$retained
 Check ($state.original_calls -eq 2) 'Substituted scriptblock ran'
 foreach($name in @('foreign','02-export-project')){
  Reject {Invoke-BeatSprigOriginalScreen $state $name 'Evening Pulse - BeatSprig 1.0.1' @()}
 }
 Reject {Invoke-BeatSprigOriginalScreen $state '01-evening-pulse-project' 'Evening Pulse - BeatSprig 1.0.1' @('Foreign dialog')}
 Check ($state.original_calls -eq 2) 'Unobserved scene/title/dialog contract reached original capture'
 $state.capture_width=1400
 Reject {Invoke-BeatSprigOriginalScreen $state '01-evening-pulse-project' 'Evening Pulse - BeatSprig 1.0.1' @()}
 Check ($state.original_calls -eq 3 -and $state.captureFrames.Count -eq 1) 'Capture metadata disagreed with frame but was accepted or replayed'
 $realSource=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
 $realFile=Join-Path $realSource 'cmake/msix/consumer-workflow.ps1'
 . $realFile
 $realState=@{qualifiedSource=$realSource;record=@{sourceInputs=@{'cmake/msix/consumer-workflow.ps1'=@{
   bytes=(Get-Item $realFile).Length;sha256=(Get-FileHash $realFile).Hash.ToLowerInvariant()}}}}
 $real=New-BeatSprigOriginalScreen $realState (Get-Command Save-BeatQuayConsumerScreen).ScriptBlock
 Check ($real.scriptblock.File -ceq $realFile -and $real.script_sha256.Length -eq 64) 'Actual unchanged production screen function lost its source/AST provenance'
 'PASS retained original source/scriptblock, before/after frame, no retry, and fixed scene refusals; no native capture claimed.'
}finally{Remove-Item $work -Recurse -Force}
