# Copyright 2026 Trieflow LLC. MIT. Observation-policy fixtures, not GUI execution.
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
$good=[ordered]@{title='BeatSprig 1.0.1';process_id=123;visible=$true;width=800;height=600;screenshot_captured=$true;screenshot_sha256=('a'*64);sampled_colors=50;actionable_controls_verified=$true;actionable_control_count=3;controls=@()}
Assert-BeatQuayWindowEvidence $good
$first=[ordered]@{setup_title='BeatSprig - Settings';setup_visible=$true;action_name='OK';action_invoked=$true;editor_title='BeatSprig 1.0.1';editor_visible=$true}
$first.working_directory=[ordered]@{title='Working directory';visible=$true;action_name='Yes';action_invoked=$true;process_id=123;path=[IO.Path]::GetFullPath('BeatQuay');message=(Get-BeatQuayWorkingDirectoryMessage ([IO.Path]::GetFullPath('BeatQuay')))}
Assert-BeatQuayFirstRunEvidence $first
foreach($field in @('title','visible','action_name','action_invoked','process_id','path','message')){
  $bad=$first|ConvertTo-Json -Depth 5|ConvertFrom-Json -AsHashtable
  $bad.working_directory[$field]=switch($field){process_id{0} visible{$false} action_invoked{$false} default{'wrong'}}
  $rejected=$false; try{Assert-BeatQuayFirstRunEvidence $bad}catch{$rejected=$true}; if(-not $rejected){throw "Invalid working-directory evidence accepted: $field"}
}
foreach($field in @('setup_title','setup_visible','action_name','action_invoked','editor_title','editor_visible')){
  $bad=$first|ConvertTo-Json|ConvertFrom-Json -AsHashtable
  if($bad[$field] -is [bool]){$bad[$field]=$false}else{$bad[$field]='wrong'}
  $rejected=$false; try{Assert-BeatQuayFirstRunEvidence $bad}catch{$rejected=$true}; if(-not $rejected){throw "Invalid first-run evidence accepted: $field"}
}
foreach($case in @('title','controls','no-screenshot','blank-screenshot','small-window')){
  $bad=$good|ConvertTo-Json|ConvertFrom-Json -AsHashtable
  switch($case){title{$bad.title='LMMS'} controls{$bad.actionable_controls_verified=$false} no-screenshot{$bad.screenshot_captured=$false} blank-screenshot{$bad.sampled_colors=1} small-window{$bad.width=50}}
  $rejected=$false; try{Assert-BeatQuayWindowEvidence $bad}catch{$rejected=$true}; if(-not $rejected){throw "Invalid editor evidence accepted: $case"}
}
Write-Output 'PASS: exact first-run and editor evidence policies plus eighteen negative variants.'
