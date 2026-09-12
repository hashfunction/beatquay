# Copyright 2026 Trieflow LLC. MIT. Production tempo guards and bounded input sequence.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'consumer-workflow.ps1')
function Check($Value,$Message){if(-not $Value){throw $Message}}
function Reject([scriptblock]$Action,$Message){$failed=$false;try{& $Action}catch{$failed=$true};Check $failed $Message}
$captured=Get-Content (Join-Path $PSScriptRoot 'fixtures/tempo-34681627248.json') -Raw|ConvertFrom-Json -AsHashtable
$main=$captured.main;$tempo=$captured.tempo
$point=Get-BeatQuayTempoPoint $main $tempo 3772
Check ($point.x -eq 502 -and $point.y -eq 117) 'Exact native tempo center differs.'
foreach($mutation in @('pid','class','id','type','hidden','disabled','empty','nan','outside','main_pid','main_class','main_id')){
 $m=$main.Clone();$t=$tempo.Clone()
 switch($mutation){pid{$t.process_id=5} class{$t.class_name='QWidget'} id{$t.automation_id+='foreign'} type{$t.type='Button'} hidden{$t.visible=$false} disabled{$t.enabled=$false} empty{$t.width=0} nan{$t.x=[double]::NaN} outside{$t.x=0} main_pid{$m.process_id=5} main_class{$m.class_name='QDialog'} main_id{$m.automation_id='foreign'}}
 Reject {Get-BeatQuayTempoPoint $m $t 3772} "Unsafe tempo geometry accepted: $mutation"
}
Add-BeatQuayConsumerTypes
[BeatQuayConsumer.Native]::RequireTempoPointer(3772,100,100,3772,100)
foreach($values in @(@(0,100,100,3772,100),@(3772,0,0,3772,0),@(3772,100,101,3772,100),@(3772,100,100,2,100),@(3772,100,100,3772,101))){
 Reject {[BeatQuayConsumer.Native]::RequireTempoPointer($values[0],$values[1],$values[2],$values[3],$values[4])} 'Unsafe native pointer ownership accepted.'
}
# Source-defined menu fixtures are hypothetical provider records, not Windows evidence.
$menu=@{snapshot=@{title='Tempo';truncated=$false;root=@{available=$true;process_id=3772;visible=$true;enabled=$true;width=220;height=160;type='Menu';name='Tempo';class_name='lmms::gui::CaptionMenu'}};items=@(
 @{snapshot=@{available=$true;process_id=3772;visible=$true;enabled=$false;type='MenuItem';name='Tempo'}},
 @{snapshot=@{available=$true;process_id=3772;visible=$true;enabled=$true;type='MenuItem';name='Copy value (112)';width=220;height=25}})}
Assert-BeatQuayTempoMenu $menu 3772 112
foreach($mutation in @('pid','class','title','truncated','missing_caption','wrong_value','duplicate')){
 $bad=$menu|ConvertTo-Json -Depth 8|ConvertFrom-Json -AsHashtable
 switch($mutation){pid{$bad.snapshot.root.process_id=1} class{$bad.snapshot.root.class_name='QMenu'} title{$bad.snapshot.title='Volume'} truncated{$bad.snapshot.truncated=$true} missing_caption{$bad.items=$bad.items[1..1]} wrong_value{$bad.items[1].snapshot.name='Copy value (113)'} duplicate{$bad.items+=@($bad.items[1])}}
 Reject {Assert-BeatQuayTempoMenu $bad 3772 112} "Unsafe tempo menu accepted: $mutation"
}
# Execute the production sequencer; only platform observation/input endpoints are seams.
$script:calls=[Collections.Generic.List[string]]::new();$script:failAt=''
$script:liveTempo=$tempo
function Set-BeatQuayConsumerForeground($State,$Main){$script:calls.Add('foreground')}
function Assert-BeatQuayConsumerOwner($State){$script:calls.Add('owner');if($script:failAt -ceq 'owner'){throw 'Retained process no longer owned'}}
function Get-BeatQuayConsumerControl($Element){return $Element.snapshot}
function Assert-BeatQuayTempoHit($Control,$Point){$script:calls.Add('hit');if($script:failAt -ceq 'hit'){throw 'Different exact UIA hit'}}
function Send-BeatQuayTempoPointer($State,$Main,$Point,$Kind){$script:calls.Add('send');if($script:failAt -ceq 'send'){throw 'Native foreground or pointer ownership changed'}}
$state=@{process=@{Id=3772};workflow=@{current_action='edit_tempo_116';inputs=[Collections.Generic.List[object]]::new()}}
$tempoElement=@{snapshot=$tempo};$mainWindow=@{element=@{snapshot=$main};snapshot=@{truncated=$false};items=@(@{element=$tempoElement;snapshot=$tempo})}
Invoke-BeatQuayTempoPointer $state $mainWindow wheel
Check (($script:calls -join ',') -ceq 'foreground,owner,hit,send' -and $state.workflow.inputs.Count -eq 1 -and $state.workflow.inputs[0].wheel_delta -eq 120) 'Production pointer order/receipt differs.'
foreach($failure in @('owner','hit','send','changed_live_geometry')){
 $script:calls.Clear();$script:failAt=$failure;$state.workflow.inputs.Clear();$tempoElement.snapshot=$tempo.Clone()
 if($failure -ceq 'changed_live_geometry'){$tempoElement.snapshot.x=0}
 Reject {Invoke-BeatQuayTempoPointer $state $mainWindow wheel} 'Unqualified pointer action succeeded.'
 Check ($state.workflow.inputs.Count -eq 0) 'Failed native input produced successful receipt.'
 if($failure -cne 'send'){Check (-not $script:calls.Contains('send')) 'Native input happened after ownership/hit/geometry refusal.'}
}
$script:calls.Clear();$script:failAt=''
function Invoke-BeatQuayTempoPointer($State,$Main,[string]$Kind){$script:calls.Add($Kind);if($script:failAt -ceq $Kind){throw 'Exact hit/foreground ownership refused'}}
function Confirm-BeatQuayTempoValue($State,$Main,[int]$Value){$script:calls.Add("verify_$Value");if($script:failAt -ceq "verify_$Value"){throw 'Observed menu value differs'}}
function Wait-BeatQuayConsumerWindow($State,$Title){$script:calls.Add('window');return @{snapshot=@{title=$Title}}}
$state=@{process=@{Id=3772};workflow=@{}}
Invoke-BeatQuayConsumerTempoEdit $state
Check (($script:calls -join ',') -ceq 'window,verify_112,wheel,window,verify_113,wheel,window,verify_114,wheel,window,verify_115,wheel,window,verify_116') 'Tempo route did not prove every single native detent.'
foreach($failure in @('verify_112','verify_113','verify_114','verify_115','verify_116','wheel')){
 $script:calls.Clear();$script:failAt=$failure
 Reject {Invoke-BeatQuayConsumerTempoEdit $state} 'Unproved tempo route continued.'
 Check ($script:calls[-1] -ceq $failure) 'Input occurred after failed tempo proof.'
}
Write-Output 'PASS: exact captured tempo geometry, 12 refusals, native ownership guard, seven menu refusals and actual four-detent sequencing with six stop boundaries. Windows UI remains pending.'
