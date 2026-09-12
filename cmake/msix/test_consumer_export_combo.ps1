$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'consumer-workflow.ps1')
$fixture=Get-Content -Raw (Join-Path $PSScriptRoot 'fixtures/export-dialog-34692467712.json') | ConvertFrom-Json -AsHashtable
$script:actions=[Collections.Generic.List[object]]::new()
$script:failAt=''
function New-ObservedExportWindow {
 $observation=($fixture.observation | ConvertTo-Json -Depth 40 | ConvertFrom-Json -AsHashtable)
 return @{snapshot=$observation;items=@($observation.controls|ForEach-Object {@{snapshot=$_}})}
}
# Replace only OS input and newly opened popup observation boundaries. Label lookup
# and combo selection run the production functions against the actual Windows tree.
function Invoke-BeatQuayConsumerClick($State,$Window,$Control) {
 $script:actions.Add(@{kind='click';snapshot=$Control.snapshot})
 if($script:failAt -ceq 'click'){throw 'Injected native click failure'}
}
function Find-BeatQuayConsumerInput($State,[string]$Type,[string]$Name) {
 $script:actions.Add(@{kind='observe';type=$Type;name=$Name})
 if($script:failAt -ceq 'observe'){throw 'Injected popup observation failure'}
 return @{window=@{};control=@{snapshot=@{type=$Type;name=$Name}}}
}
function Check($Condition,[string]$Message) {if(-not $Condition){throw $Message}}
$state=@{process=@{Id=$fixture.observation.process_id}}
foreach($case in @(@('File format:','WAV (*.wav)',523),@('Sampling rate:','44100 Hz',553),@('Bit depth:','16 Bit integer',583))) {
 $script:actions.Clear();$window=New-ObservedExportWindow
 Select-BeatQuayConsumerCombo $state $window $case[0] $case[1]
 Check ($script:actions.Count -eq 3) 'Expected one combo click, one popup observation, and one option click'
 Check ($script:actions[0].snapshot.type -ceq 'ComboBox' -and $script:actions[0].snapshot.y -eq $case[2]) 'Wrong actual label-adjacent combo selected'
 Check ($script:actions[1].type -ceq 'ListItem' -and $script:actions[1].name -ceq $case[1]) 'Wrong popup observation requested'
 Check ($script:actions[2].snapshot.name -ceq $case[1]) 'Wrong popup option clicked'
}
foreach($mutation in @('truncated','missing-label','duplicate-label','foreign-label','hidden-label','disabled-label','missing-combo','duplicate-combo','foreign-combo','hidden-combo','disabled-combo')) {
 $window=New-ObservedExportWindow;$script:actions.Clear()
 $label=@($window.items|Where-Object {$_.snapshot.name -ceq 'Sampling rate:'})[0]
 $combo=@($window.items|Where-Object {$_.snapshot.type -ceq 'ComboBox' -and $_.snapshot.y -eq 553})[0]
 switch($mutation) {
  'truncated' {$window.snapshot.truncated=$true}
  'missing-label' {$label.snapshot.name='Other label'}
  'duplicate-label' {$window.items+=@($label)}
  'foreign-label' {$label.snapshot.process_id++}
  'hidden-label' {$label.snapshot.visible=$false}
  'disabled-label' {$label.snapshot.enabled=$false}
  'missing-combo' {$combo.snapshot.type='Text'}
  'duplicate-combo' {$window.items+=@($combo)}
  'foreign-combo' {$combo.snapshot.process_id++}
  'hidden-combo' {$combo.snapshot.visible=$false}
  'disabled-combo' {$combo.snapshot.enabled=$false}
 }
 $caught=$null
 try {Select-BeatQuayConsumerCombo $state $window 'Sampling rate:' '44100 Hz'} catch {$caught=$_}
 Check ($null -ne $caught) "Unsafe observation accepted: $mutation"
 Check ($script:actions.Count -eq 0) "Input occurred before refusal: $mutation"
}
foreach($boundary in @('click','observe')) {
 $script:actions.Clear();$script:failAt=$boundary;$caught=$null
 try {Select-BeatQuayConsumerCombo $state (New-ObservedExportWindow) 'Sampling rate:' '44100 Hz'} catch {$caught=$_}
 Check ($null -ne $caught -and $caught.Exception.Message -like 'Injected * failure') 'Original input failure was lost'
 $expected=if($boundary -ceq 'click'){1}else{2}
 Check ($script:actions.Count -eq $expected) 'Input was replayed after failure'
}
Write-Output 'PASS: 3 actual export combo selections, 11 unsafe observation refusals, and 2 input failures without replay.'
