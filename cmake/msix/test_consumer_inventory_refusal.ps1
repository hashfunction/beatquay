# Copyright 2026 Trieflow LLC. MIT.
# Provider boundary replay; executes the real production traversal and refusal.
# These synthetic wrong-PID controls are not claims about Windows run34704891815.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'consumer-workflow.ps1')
function Check($Value,[string]$Message){if(-not $Value){throw $Message}}
if(-not ('Windows.Automation.TreeScope' -as [type])){
 Add-Type 'namespace Windows.Automation { public enum TreeScope { Subtree } public class Condition { public static object TrueCondition=new object(); }}'
}
function Snapshot([int]$Owner=744) {return @{available=$true;process_id=$Owner;type='Window';name='Select file for project-export...';
 automation_id='QApplication.QFileDialog';class_name='QFileDialog';native_window_handle=2883910;help='';value='';
 visible=$true;enabled=$true;x=232.0;y=81.0;width=600.0;height=400.0}}
$script:reads=[Collections.Generic.List[string]]::new();$script:nativeCalls=0;$script:failNative=$false
function Get-BeatQuayConsumerControl($Element){$script:reads.Add($Element.key);return $Element.snapshot}
function Get-BeatQuayConsumerRefusalNativeObservation($State){
 $script:nativeCalls++
 if($script:failNative){throw 'Native read unavailable'}
 return @{expected_process_id=$State.process.Id;retained_main_window_handle=2883910;main_process_id=744;foreground_window_handle=23;foreground_process_id=744}
}
function Reset-Graph([int]$RejectedPid=745){
 $script:reads.Clear();$script:nativeCalls=0;$script:failNative=$false
 $script:root=[pscustomobject]@{key='root';snapshot=(Snapshot)}
 $script:children=@([pscustomobject]@{key='first';snapshot=(Snapshot)},[pscustomobject]@{key='rejected';snapshot=(Snapshot $RejectedPid)},[pscustomobject]@{key='must-not-read';snapshot=(Snapshot)})
 $script:collection=[pscustomobject]@{Count=3}
 $script:collection|Add-Member ScriptMethod Item {param($index);return $script:children[$index]}
 $script:root|Add-Member ScriptMethod FindAll {param($scope,$condition);return $script:collection}
 $script:state=@{process=@{Id=744};workflow=@{current_action='export_project_wav';acceptance=$false;last_observation=@('prior complete observation')}}
}
function Refused {
 $errorRecord=$null
 try {Read-BeatQuayConsumerWindowInventory $state $root 2 4|Out-Null}catch{$errorRecord=$_}
 Check ($null -ne $errorRecord) 'Wrong PID was accepted.'
 Check ($errorRecord.Exception.Message -ceq 'Foreign control in owned consumer window') 'Original refusal message was replaced.'
 return $errorRecord
}
Reset-Graph
$failure=Refused
Check (($reads -join ',') -ceq 'root,first,rejected') 'Traversal continued after immediate ownership refusal.'
Check ($nativeCalls -eq 1) 'Failure native observation was repeated or omitted.'
$d=$state.workflow.inventory_refusal
Check ($d.expected_process_id -eq 744 -and $d.rejected.process_id -eq 745 -and $d.root.process_id -eq 744 -and
 $d.control_index -eq 1 -and $d.control_count -eq 3 -and $d.root_index -eq 2 -and $d.root_count -eq 4) 'Exact rejected/root traversal boundary was not retained.'
Check ($d.current_action -ceq 'export_project_wav' -and $d.primary_error -ceq $failure.Exception.Message -and
 $d.script_stack -match 'Get-BeatQuayConsumerWindowInventory' -and $d.native.foreground_window_handle -eq 23) 'Action, original stack or native facts missing.'
Check (-not $state.workflow.acceptance -and ($state.workflow.last_observation -join ',') -ceq 'prior complete observation') 'Partial inventory became a complete accepted observation.'
foreach($owner in @(0,7508)){
 Reset-Graph $owner;$null=Refused
 Check ($state.workflow.inventory_refusal.rejected.process_id -eq $owner -and ($reads -join ',') -ceq 'root,first,rejected') 'Zero/prior-process PID was hidden or retried.'
}
Reset-Graph;$script:failNative=$true;$null=Refused
Check ($null -eq $state.workflow.inventory_refusal.native -and $state.workflow.inventory_refusal.diagnostic_errors[0] -ceq 'Native read unavailable') 'Secondary native error replaced or hid original refusal.'
Reset-Graph;$children[1].snapshot.name='x'*20000;$children[1].snapshot.automation_id='y'*20000;$children[1].snapshot.value='z'*30000
$null=Refused;$d=$state.workflow.inventory_refusal
Check ($d.rejected.text_truncated -and $d.rejected.name.Length -eq 1024 -and $d.rejected.automation_id.Length -eq 1024 -and $d.rejected.value.Length -eq 2048 -and
 ($d|ConvertTo-Json -Depth 10 -Compress).Length -lt 16000) 'Rejected provider text was not bounded.'
Reset-Graph 744
$valid=Read-BeatQuayConsumerWindowInventory $state $root 2 4
Check ($valid.items.Count -eq 3 -and -not $state.workflow.ContainsKey('inventory_refusal') -and $nativeCalls -eq 0) 'Successful inventory acquired diagnostic state or changed traversal.'
Reset-Graph 744;$children[1].snapshot=@{available=$false;observation_error='Provider unavailable'}
$incomplete=Read-BeatQuayConsumerWindowInventory $state $root 2 4
$message=$null;try{Find-BeatQuayConsumerFileName $incomplete 744|Out-Null}catch{$message=$_.Exception.Message}
Check ($incomplete.snapshot.truncated -and $message -ceq 'Incomplete UI snapshot cannot authorize input' -and
 -not $state.workflow.ContainsKey('inventory_refusal') -and $nativeCalls -eq 0) 'Unavailable provider was relabeled or allowed to authorize input.'
Reset-Graph;$root.snapshot.process_id=0
$message=$null;try{Read-BeatQuayConsumerWindowInventory $state $root 2 4|Out-Null}catch{$message=$_.Exception.Message}
Check ($message -ceq 'Observed window PID changed after owned enumeration' -and ($reads -join ',') -ceq 'root' -and -not $state.workflow.ContainsKey('inventory_refusal')) 'Root ownership failure was relabeled or bypassed.'
Reset-Graph
$script:inputCount=0;$script:desktopReads=0
function Assert-BeatQuayConsumerOwner($State){}
function Get-BeatQuayConsumerDesktopElements($State){$script:desktopReads++;return $script:root}
function Set-BeatQuayConsumerValue {$script:inputCount++}
function Invoke-BeatQuayConsumerClick {$script:inputCount++}
$message=$null
try{Invoke-BeatQuayConsumerFileDialog $state 'Select file for project-export...' 'C:\fixture\Evening Pulse.wav' 'Save'}catch{$message=$_.Exception.Message}
Check ($message -ceq 'Foreign control in owned consumer window' -and $script:inputCount -eq 0 -and $script:desktopReads -eq 1 -and
 ($reads -join ',') -ceq 'root,first,rejected' -and $state.workflow.inventory_refusal.root_index -eq 0 -and
 $state.workflow.inventory_refusal.root_count -eq 1) 'Production filename route retried, continued input or lost its enumeration boundary.'
Reset-Graph
# Force failure of the metadata writer itself at the real reader catch boundary.
function Save-BeatQuayConsumerInventoryRefusal {throw 'Diagnostic writer failed'}
$null=Refused
Check (($reads -join ',') -ceq 'root,first,rejected' -and $state.workflow.inventory_refusal_diagnostic_error -ceq 'Diagnostic writer failed') 'Metadata failure caused further traversal or was not retained as secondary.'
'PASS ten production inventory/refusal cases; no native Windows execution claimed.'
