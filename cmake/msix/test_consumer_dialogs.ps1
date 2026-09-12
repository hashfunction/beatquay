# Copyright 2026 Trieflow LLC. MIT. Actual Windows provider replay, not native UI execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'consumer-workflow.ps1')
function Check($Value,[string]$Message){if(-not $Value){throw $Message}}
function Reject([scriptblock]$Action,[string]$Message){$failed=$false;try{& $Action}catch{$failed=$true};Check $failed $Message}
$record=Get-Content (Join-Path $PSScriptRoot 'fixtures/save-project-34688758325.json') -Raw|ConvertFrom-Json -AsHashtable
function MakeWindow {
 $copy=$record|ConvertTo-Json -Depth 12|ConvertFrom-Json -AsHashtable
 @{snapshot=@{root=$copy.root;truncated=$copy.truncated};items=@($copy.controls|ForEach-Object {@{snapshot=$_;element=$_.automation_id}})}
}
$window=MakeWindow
$nested=@(Get-BeatQuayNestedConsumerWindows $window $record.process_id)
Check ($nested.Count -eq 1 -and $nested[0].snapshot.name -ceq 'Save Project' -and $nested[0].snapshot.class_name -ceq 'lmms::gui::VersionedSaveDialog') 'Actual nested Save Project was not discovered.'
$edit=Find-BeatQuayConsumerFileName $window $record.process_id
Check ($edit.snapshot.class_name -ceq 'QLineEdit' -and $edit.snapshot.automation_id -ceq 'QApplication.QFileDialog.fileNameEdit') 'Actual fully qualified filename editor not selected.'
foreach($mutation in @('foreign_root','incomplete_root','foreign_child','missing_child','wrong_role','duplicate_filename','foreign_filename','suffix_only_filename','wrong_editor_class')){
 $bad=MakeWindow
 switch($mutation){
  foreign_root{$bad.snapshot.root.process_id++}
  incomplete_root{$bad.snapshot.truncated=$true}
  foreign_child{$bad.items[0].snapshot.process_id++}
  missing_child{$bad.items[0].snapshot.available=$false}
  wrong_role{$bad.items[0].snapshot.type='Group'}
  duplicate_filename{$bad.items+=@($bad.items|Where-Object {$_.snapshot.class_name -ceq 'QLineEdit'})}
  foreign_filename{($bad.items|Where-Object {$_.snapshot.class_name -ceq 'QLineEdit'}).snapshot.process_id++}
  suffix_only_filename{($bad.items|Where-Object {$_.snapshot.class_name -ceq 'QLineEdit'}).snapshot.automation_id='fileNameEdit'}
  wrong_editor_class{($bad.items|Where-Object {$_.snapshot.class_name -ceq 'QLineEdit'}).snapshot.class_name='ForeignEditor'}
 }
 if($mutation -in @('foreign_root','incomplete_root','foreign_child','missing_child')){
  Reject {Get-BeatQuayNestedConsumerWindows $bad $record.process_id} "Accepted invalid nested inventory: $mutation"
 }elseif($mutation -ceq 'wrong_role'){
  Check (@(Get-BeatQuayNestedConsumerWindows $bad $record.process_id).Count -eq 0) 'Nonwindow was treated as dialog.'
 }else{Reject {Find-BeatQuayConsumerFileName $bad $record.process_id} "Accepted invalid editor: $mutation"}
}
Write-Output 'PASS actual nested Save Project/filename provider replay and nine invalid ownership, inventory and selector cases.'
