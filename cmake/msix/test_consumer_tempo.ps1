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
# Exact captured Windows provider shape, bound to the original failed receipt.
$menuCapture=Get-Content (Join-Path $PSScriptRoot 'fixtures/tempo-menu-34684975836.json') -Raw|ConvertFrom-Json -AsHashtable
Check ($menuCapture.run_id -eq 34684975836 -and $menuCapture.source_artifact_sha256 -ceq '51a0861cbea41f6635978b7a6549e80b9ffffe061dabbb4d53e4cda111a7b358') 'Captured menu provenance changed.'
$menu=@{snapshot=$menuCapture.menu;items=@($menuCapture.menu.controls|ForEach-Object {@{snapshot=$_}})}
Assert-BeatQuayTempoMenu $menu 4796 112
foreach($mutation in @('pid','class','id','title','root_name','type','truncated','unavailable','hidden','disabled','empty',
 'missing_caption','duplicate_caption','enabled_caption','caption_pid','caption_class','caption_id','wrong_value','duplicate','value_disabled','value_hidden','value_pid','value_class','value_id')){
 $bad=$menu|ConvertTo-Json -Depth 8|ConvertFrom-Json -AsHashtable
 switch($mutation){
  pid{$bad.snapshot.root.process_id=1} class{$bad.snapshot.root.class_name='QMenu'} id{$bad.snapshot.root.automation_id='foreign'}
  title{$bad.snapshot.title='Tempo'} root_name{$bad.snapshot.root.name='Tempo'} type{$bad.snapshot.root.type='Menu'}
  truncated{$bad.snapshot.truncated=$true} unavailable{$bad.snapshot.root.available=$false} hidden{$bad.snapshot.root.visible=$false}
  disabled{$bad.snapshot.root.enabled=$false} empty{$bad.snapshot.root.width=0}
  missing_caption{$bad.items=@($bad.items|Where-Object {$_.snapshot.name -cne 'Tempo'})}
  duplicate_caption{$bad.items+=@($bad.items[1])} enabled_caption{$bad.items[1].snapshot.enabled=$true}
  caption_pid{$bad.items[1].snapshot.process_id=1} caption_class{$bad.items[1].snapshot.class_name='QWidget'} caption_id{$bad.items[1].snapshot.automation_id='foreign'}
  wrong_value{$bad.items[4].snapshot.name='Copy value (113)'} duplicate{$bad.items+=@($bad.items[4])}
  value_disabled{$bad.items[4].snapshot.enabled=$false} value_hidden{$bad.items[4].snapshot.visible=$false} value_pid{$bad.items[4].snapshot.process_id=1}
  value_class{$bad.items[4].snapshot.class_name='QWidget'} value_id{$bad.items[4].snapshot.automation_id='foreign'}
 }
 Reject {Assert-BeatQuayTempoMenu $bad 4796 112} "Unsafe tempo menu accepted: $mutation"
}
$script:menuWindow=$menu;$script:menuTitle=''
function Wait-BeatQuayConsumerWindow($State,$Title){$script:menuTitle=$Title;return $script:menuWindow}
$selected=Wait-BeatQuayTempoMenu @{process=@{Id=4796}} 112
Check ($script:menuTitle -ceq 'BeatSprig' -and [object]::ReferenceEquals($selected,$menu)) 'Production wait did not discover the actual native popup title.'
$script:menuWindow=$menu|ConvertTo-Json -Depth 8|ConvertFrom-Json -AsHashtable;$script:menuWindow.snapshot.root.class_name='Other'
Reject {Wait-BeatQuayTempoMenu @{process=@{Id=4796}} 112} 'Title-only popup authorized the tempo route.'
$onlyMain=@{snapshot=@{truncated=$false;root=@{available=$true;process_id=4796;visible=$true;class_name='lmms::gui::MainWindow'}}}
Check (-not (Test-BeatQuayTempoMenuDismissed @($onlyMain,$menu))) 'Still-visible actual BeatSprig CaptionMenu counted as dismissed.'
Check (Test-BeatQuayTempoMenuDismissed @($onlyMain)) 'Complete main-only inventory did not establish dismissal.'
$renamed=$menu|ConvertTo-Json -Depth 8|ConvertFrom-Json -AsHashtable;$renamed.snapshot.title='Unexpected'
Check (-not (Test-BeatQuayTempoMenuDismissed @($onlyMain,$renamed))) 'Changed popup title concealed a visible CaptionMenu.'
$hidden=$menu|ConvertTo-Json -Depth 8|ConvertFrom-Json -AsHashtable;$hidden.snapshot.root.visible=$false
Check (Test-BeatQuayTempoMenuDismissed @($onlyMain,$hidden)) 'Actually hidden menu was not recognized.'
foreach($target in @($onlyMain,$menu)){
 $bad=$target|ConvertTo-Json -Depth 8|ConvertFrom-Json -AsHashtable;$bad.snapshot.truncated=$true
 Reject {Test-BeatQuayTempoMenuDismissed @($bad)} 'Incomplete inventory granted dismissal.'
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
Write-Output 'PASS: exact captured tempo geometry, 12 refusals, native ownership guard, 24 menu refusals and observed popup dismissal and actual four-detent sequencing with six stop boundaries. Windows UI remains pending.'
