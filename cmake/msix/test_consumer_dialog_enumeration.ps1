# Copyright 2026 Trieflow LLC. MIT.
# Execute production enumeration/wait/value boundaries with captured provider data.
# Element identity aliases and graph variants below are replay scenarios, not
# claims that those duplicate desktop exposures occurred in run34688758325.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'consumer-workflow.ps1')
function Check($Value,[string]$Message){if(-not $Value){throw $Message}}
function Reject([scriptblock]$Action,[string]$Message){
 $failed=$false;try{& $Action|Out-Null}catch{$failed=$true}
 Check $failed $Message
}
function Copy-Record($Value){return $Value|ConvertTo-Json -Depth 16|ConvertFrom-Json -AsHashtable}
$record=Get-Content (Join-Path $PSScriptRoot 'fixtures/save-project-34688758325.json') -Raw|ConvertFrom-Json -AsHashtable
$mainElement=[pscustomobject]@{identity='main'}
$dialogElement=[pscustomobject]@{identity='save-dialog'}
$mainAlias=[pscustomobject]@{identity='main'}
$dialogAlias=[pscustomobject]@{identity='save-dialog'}
$secondDialog=[pscustomobject]@{identity='different-save-dialog'}
$script:inventoryCalls=[Collections.Generic.List[string]]::new()
$script:ownerCalls=0;$script:failOwnerAt=0
function Assert-BeatQuayConsumerOwner {
 param($State)
 $script:ownerCalls++
 if($script:ownerCalls -eq $script:failOwnerAt){throw 'Replay retained owner changed'}
}
function Get-BeatQuayConsumerDesktopElements {param($State);return $script:desktop}
function Test-BeatQuaySameConsumerElement {param($First,$Second);return $First.identity -ceq $Second.identity}
function Get-BeatQuayConsumerWindowInventory {
 param($Element,[int]$ProcessId)
 Check ($ProcessId -eq $record.process_id) 'Enumeration lost retained process identity.'
 $script:inventoryCalls.Add($Element.identity)
 $inventory=$script:inventories[$Element.identity]
 if(-not $inventory){throw 'Production requested an unobserved replay element.'}
 # The provider boundary returns the actual newly queried subtree. In particular,
 # dialog controls do not include their main accessible parent.
 return [pscustomobject]@{element=$Element;snapshot=$inventory.snapshot;items=$inventory.items}
}
function Start-Sleep {param([int]$Milliseconds)}
function Reset-Graph {
 $script:inventoryCalls.Clear();$script:ownerCalls=0;$script:failOwnerAt=0
 $copy=Copy-Record $record
 $dialogRoot=@($copy.controls|Where-Object {$_.type -ceq 'Window' -and $_.name -ceq 'Save Project'})
 Check ($dialogRoot.Count -eq 1) 'Captured dialog root is ambiguous.'
 $dialogItems=@(for($i=0;$i -lt $copy.controls.Count;$i++){
  $control=$copy.controls[$i]
  $element=if($control -eq $dialogRoot[0]){$dialogElement}else{[pscustomobject]@{identity="dialog-control-$i"}}
  @{element=$element;snapshot=$control}
 })
 $mainItems=@(@{element=$mainElement;snapshot=$copy.root})+$dialogItems
 $script:inventories=@{
  main=@{snapshot=@{title=$copy.root.name;root=$copy.root;process_id=$copy.process_id;truncated=$false;controls=@($mainItems.snapshot)};items=$mainItems}
  'save-dialog'=@{snapshot=@{title=$dialogRoot[0].name;root=$dialogRoot[0];process_id=$copy.process_id;truncated=$false;controls=@($dialogItems.snapshot)};items=$dialogItems}
 }
 $script:desktop=@($mainElement)
 $script:state=@{process=@{Id=$record.process_id};workflow=@{inputs=[Collections.Generic.List[object]]::new();current_action='replay'}}
}
Reset-Graph
$windows=@(Get-BeatQuayConsumerWindows $state)
Check ($windows.Count -eq 1 -and $windows[0].element.identity -ceq 'main' -and ($script:inventoryCalls -join ',') -ceq 'main') 'Default enumeration promoted nested windows.'
Reset-Graph
$windows=@(Get-BeatQuayConsumerWindows $state -IncludeNestedWindows)
Check (($windows.element.identity -join ',') -ceq 'main,save-dialog' -and ($script:inventoryCalls -join ',') -ceq 'main,save-dialog') 'Opt-in did not query the distinct actual dialog subtree exactly once.'
Check ($windows[1].snapshot.root.name -ceq 'Save Project' -and @($windows[1].items|Where-Object {$_.snapshot.automation_id -ceq $record.root.automation_id}).Count -eq 0) 'Dialog inventory retained its parent window.'
Reset-Graph
$selected=Wait-BeatQuayConsumerWindow $state 'Save Project' -Seconds 0
Check ($selected.element.identity -ceq 'save-dialog' -and $state.workflow.last_observation.Count -eq 2) 'Production exact-title wait did not opt into nested discovery.'
Reset-Graph
$selected=Find-BeatQuayConsumerInput $state 'Edit' ''
Check ($selected.window.element.identity -ceq 'main' -and $selected.control.snapshot.automation_id -ceq 'QApplication.QFileDialog.fileNameEdit' -and ($script:inventoryCalls -join ',') -ceq 'main') 'Global selector promoted nested windows or duplicated its filename control.'
foreach($order in @('main-first','dialog-first')){
 Reset-Graph
 $script:desktop=if($order -ceq 'main-first'){@($mainElement,$dialogAlias)}else{@($dialogAlias,$mainElement)}
 $selected=Wait-BeatQuayConsumerWindow $state 'Save Project' -Seconds 0
 Check ($selected.element.identity -ceq 'save-dialog' -and $state.workflow.last_observation.Count -eq 2 -and
  @($script:inventoryCalls|Where-Object {$_ -ceq 'save-dialog'}).Count -eq 1 -and
  @($script:inventoryCalls|Where-Object {$_ -ceq 'main'}).Count -eq 1) "Duplicate nested/desktop element escaped deduplication: $order"
}
Reset-Graph
$script:desktop=@($mainElement,$mainAlias)
Check (@(Get-BeatQuayConsumerWindows $state).Count -eq 1 -and ($script:inventoryCalls -join ',') -ceq 'main') 'Duplicate desktop root was emitted or queried twice.'
Reset-Graph
$other=Copy-Record $script:inventories['save-dialog']
$other.items=@(@{element=$secondDialog;snapshot=$other.snapshot.root})
$script:inventories['different-save-dialog']=$other
$script:inventories.main.items+=@(@{element=$secondDialog;snapshot=$other.snapshot.root})
Reject {Wait-BeatQuayConsumerWindow $state 'Save Project' -Seconds 0} 'Genuinely different same-title dialogs were silently deduplicated.'
Reset-Graph
$script:inventories.main.snapshot.truncated=$true
Reject {Wait-BeatQuayConsumerWindow $state 'Save Project' -Seconds 0} 'Incomplete parent authorized nested dialog input.'
Check (($script:inventoryCalls -join ',') -ceq 'main') 'Incomplete parent was used to query nested inventory.'
Reset-Graph
$script:failOwnerAt=2
Reject {Get-BeatQuayConsumerWindows $state -IncludeNestedWindows} 'Owner loss before nested inventory was accepted.'
Check (($script:inventoryCalls -join ',') -ceq 'main') 'Nested inventory queried after retained owner refusal.'
'PASS ten production default/opt-in, exact-title/global selector, duplicate-order, ambiguity and owner/inventory cases.'

# Static ValuePattern identifier only; the production setter is not replaced.
# There is no actual UIAutomation assembly loaded by this standalone replay.
if(-not ('Windows.Automation.ValuePattern' -as [type])){
 Add-Type 'namespace Windows.Automation { public class ValuePattern { public static object Pattern=new object(); }}'
}
$retained=@($record.controls|Where-Object {$_.automation_id -ceq 'QApplication.QFileDialog.fileNameEdit'})[0]
$script:pattern=[pscustomobject]@{Current=[pscustomobject]@{IsReadOnly=$false;Value=''};writes=0}
$script:pattern|Add-Member ScriptMethod SetValue {param($value);$this.writes++;$this.Current.Value=$value}
$valueElement=[pscustomobject]@{}
$valueElement|Add-Member ScriptMethod GetCurrentPattern {param($id);$script:patternQueries++;return $script:pattern}
function Get-BeatQuayConsumerControl {param($Element);return $script:live}
function Set-BeatQuayConsumerForeground {param($State,$Window);$script:foregroundCalls++}
foreach($case in @('unchanged','changed-id','changed-class','changed-help')){
 $script:live=Copy-Record $retained
 $script:pattern.Current.Value='';$script:pattern.writes=0;$script:patternQueries=0;$script:foregroundCalls=0
 $state.workflow.inputs.Clear()
 switch($case){
  'changed-id'{$script:live.automation_id='QApplication.QFileDialog.lookInEdit'}
  'changed-class'{$script:live.class_name='OtherEditor'}
  'changed-help'{$script:live.help='Different field'}
 }
 $action={Set-BeatQuayConsumerValue $state @{} @{element=$valueElement;snapshot=$retained} 'C:\owned\Evening Pulse.mmp'}
 if($case -ceq 'unchanged'){
  & $action
  Check ($script:pattern.writes -eq 1 -and $script:patternQueries -eq 1 -and $script:pattern.Current.Value -ceq 'C:\owned\Evening Pulse.mmp' -and $state.workflow.inputs.Count -eq 1) 'Unchanged observed filename did not receive exactly one verified value mutation.'
 }else{
  Reject $action "Live filename selector drift reached SetValue: $case"
  Check ($script:pattern.writes -eq 0 -and $script:patternQueries -eq 0 -and $state.workflow.inputs.Count -eq 0) "Changed live selector queried/mutated a pattern or recorded accepted input: $case"
 }
 Check ($script:foregroundCalls -eq 1) 'Production value setter skipped its existing foreground route.'
}
'PASS production value setter with unchanged captured filename and three live selector drift refusals before pattern access.'
