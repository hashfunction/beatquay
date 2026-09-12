# Copyright 2026 Trieflow LLC. MIT. Exercise production input/completion gates without claiming native UI execution.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
. (Join-Path $PSScriptRoot 'consumer-workflow.ps1')
function Check($Value,[string]$Message){if(-not $Value){throw $Message}}
function Reject([scriptblock]$Action,[string]$Message){$failed=$false;try{& $Action}catch{$failed=$true};Check $failed $Message}
function Snapshot {return @{name='Start';type='Button';process_id=123;visible=$true;enabled=$true;x=10;y=20;width=100;height=30;available=$true;help='';automation_id='';class_name='QPushButton'}}
$s=Snapshot
Assert-BeatQuayConsumerControl $s 123 'Button' 'Start'
foreach($field in @('name','type','process_id','visible','enabled','width','available')){
 $bad=Snapshot
 switch($field){name{$bad.name='Replace and export'} type{$bad.type='Text'} process_id{$bad.process_id=124} visible{$bad.visible=$false} enabled{$bad.enabled=$false} width{$bad.width=0} available{$bad.available=$false}}
 Reject {Assert-BeatQuayConsumerControl $bad 123 'Button' 'Start'} "Unqualified $field input was accepted."
}
Reject {Assert-BeatQuayConsumerControl (Snapshot) 0 'Button' 'Start'} 'Zero owned process accepted.'
$path=Join-Path ([IO.Path]::GetTempPath()) 'Evening Pulse.wav'
$complete=@{title='Export completed';process_id=123;truncated=$false;controls=@(@{name="${path}`nCompleted: 1824844 bytes";type='Edit';process_id=123;visible=$true;enabled=$true;available=$true;value="${path}`nCompleted: 1824844 bytes"})}
Assert-BeatQuayConsumerExportResult $complete 123 $path 1824844
foreach($mutation in @('title','pid','bytes','path','partial','truncated')){
 $bad=$complete|ConvertTo-Json -Depth 8|ConvertFrom-Json -AsHashtable
 switch($mutation){title{$bad.title='Export failed'} pid{$bad.process_id=124} bytes{$bad.controls[0].value="${path}`nCompleted: 1 bytes"} path{$bad.controls[0].value="foreign.wav`nCompleted: 1824844 bytes"} partial{$bad.controls[0].value += "`nRetained render or staging entry: partial.wav"} truncated{$bad.truncated=$true}}
 Reject {Assert-BeatQuayConsumerExportResult $bad 123 $path 1824844} "Invalid export result $mutation accepted."
}
$work=Join-Path $PSScriptRoot ('.consumer-fixture-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work|Out-Null
try{
 $file=Join-Path $work '.beatquayrc.xml';[IO.File]::WriteAllText($file,'owned')
 $record=@{path=$file;creation_utc=(Get-Item -LiteralPath $file -Force).CreationTimeUtc.ToString('o');absent_before_activation=$true;ownership_established=$true;process_id=123;package_full_name='owned-package';sha256=(Get-FileHash $file -Algorithm SHA256).Hash.ToLowerInvariant();cleanup_verified=$false}
 Reject {Remove-BeatQuayOwnedProfile $record $false} 'Profile deleted without retained target termination.'
 [IO.File]::WriteAllText($file,'foreign mutation')
 Reject {Remove-BeatQuayOwnedProfile $record $true} 'Changed profile was deleted.'
 Check (Test-Path $file) 'Foreign profile was not retained.'
 [IO.File]::WriteAllText($file,'owned');$record.ownership_established=$false
 Reject {Remove-BeatQuayOwnedProfile $record $true} 'Unowned profile was deleted.'
 $record.ownership_established=$true;Remove-BeatQuayOwnedProfile $record $true
 Check ($record.cleanup_verified -and -not (Test-Path $file)) 'Exact owned profile was not removed.'
}finally{Remove-Item $work -Recurse -Force}
# The real profile observer and Python verifier must attribute only known normal UI writes.
$work=Join-Path $PSScriptRoot ('.profile-fixture-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work|Out-Null
$process=[Diagnostics.Process]::GetCurrentProcess()
try{
 function Assert-BeatQuayConsumerOwner($State){if(-not $State.processOwned){throw 'fixture process unowned'}}
 $profilePath=Join-Path $work '.beatquayrc.xml'
 $xml='<lmms version="1.0.0"><paths workingdir="C:/owned/BeatQuay/"/><app configured="1"/><ui/><recentfiles/><favoriteitems/></lmms>'
 [IO.File]::WriteAllText($profilePath,$xml)
 $profile=@{path=$profilePath;absent_before_activation=$true;ownership_established=$false;process_id=0;package_full_name=$null;sha256=$null;creation_utc=$null;initial_path=$null;projects=@();observations=[Collections.Generic.List[object]]::new();cleanup_verified=$false}
 $python=(Get-Command $(if($IsWindows){'python.exe'}else{'python3'}) -ErrorAction Stop).Source
 $state=@{profile=$profile;process=$process;processOwned=$true;activationStartedUtc=[DateTime]::UtcNow.AddMinutes(-1);temporary=$work;workingDirectory=@{path='C:/owned/BeatQuay'};python=$python;ownedPackageFullName='owned-package';workflow=@{current_action='save_project'};cleanClose=$false;processExit=$null}
 $profile.absent_before_activation=$false
 Reject {Confirm-BeatQuayConsumerProfile $state -Initial} 'Preexisting profile acquired ownership.'
 $profile.absent_before_activation=$true
 Confirm-BeatQuayConsumerProfile $state -Initial
 Check ($profile.ownership_established -and $profile.observations.Count -eq 1) 'Normal first-run profile did not acquire exact ownership.'
 $state.profile.projects=@('C:/owned/Evening Pulse.mmp')
 [IO.File]::WriteAllText($profilePath,$xml.Replace('<recentfiles/>','<recentfiles><file path="C:/owned/Evening Pulse.mmp"/></recentfiles>'))
 Confirm-BeatQuayConsumerProfile $state
 $prior=$profile.sha256
 [IO.File]::WriteAllText($profilePath,$xml.Replace('configured="1"','configured="0"'))
 Reject {Confirm-BeatQuayConsumerProfile $state} 'Unexpected config mutation refreshed ownership hash.'
 Check ($profile.sha256 -ceq $prior) 'Rejected profile mutation erased last attributable hash.'
 Reject {Confirm-BeatQuayConsumerProfile $state -AfterClose} 'Profile attribution accepted unproven normal close.'
 # Replay an early consumer failure after ConfigManager saved the opened template.
 $profile.projects=@('C:/owned/BeatSprig-Drum-Grid.mpt','factoryprojects:templates/BeatSprig-Drum-Grid.mpt')
 $known=$xml.Replace('<recentfiles/>','<recentfiles><file path="factoryprojects:templates/BeatSprig-Drum-Grid.mpt"/></recentfiles>')
 [IO.File]::WriteAllText($profilePath,$known)
 $state.workflow.current_action='maximize_song_editor'
 Confirm-BeatQuayConsumerFailureProfile $state
 Check (-not $state.workflow.profile_attribution_error -and $profile.observations[-1].action -ceq 'maximize_song_editor') 'Known template write was not attributed before failure cleanup.'
 $prior=$profile.sha256
 foreach($mutation in @('foreign_recent','foreign_setting','workingdir','untracked_ui','replaced','unowned_process')){
  $changed=$known;$savedCreation=$profile.creation_utc
  switch($mutation){
   foreign_recent{$changed=$known.Replace('factoryprojects:templates/BeatSprig-Drum-Grid.mpt','C:/foreign.mmp')}
   foreign_setting{$changed=$known.Replace('configured="1"','configured="0"')}
   workingdir{$changed=$known.Replace('C:/owned/BeatQuay/','C:/foreign/')}
   untracked_ui{$changed=$known.Replace('<ui/>','<ui unknown="1"/>')}
   replaced{$profile.creation_utc='2000-01-01T00:00:00.0000000Z'}
   unowned_process{$state.processOwned=$false}
  }
  [IO.File]::WriteAllText($profilePath,$changed)
  Confirm-BeatQuayConsumerFailureProfile $state
  Check ([bool]$state.workflow.profile_attribution_error -and $profile.sha256 -ceq $prior) "Failure attribution accepted $mutation or overwrote owned hash."
  Check (Test-Path -LiteralPath $profilePath) 'Failure attribution mutated the profile.'
  if($mutation -ne 'unowned_process'){Reject {Remove-BeatQuayOwnedProfile $profile $true} 'Foreign settings deleted after attribution refusal.'}
  $state.processOwned=$true;$profile.creation_utc=$savedCreation
 }
 [IO.File]::WriteAllText($profilePath,$known)
 Confirm-BeatQuayConsumerFailureProfile $state
 Remove-BeatQuayOwnedProfile $profile $true
 Check ($profile.cleanup_verified -and -not (Test-Path -LiteralPath $profilePath)) 'Known template profile did not clean up after proven process termination.'

}finally{$process.Dispose();Remove-Item $work -Recurse -Force}
Add-BeatQuayConsumerTypes
Check ($null -ne ('BeatQuayConsumer.Native' -as [type])) 'Native observed-input helper failed compilation.'
Write-Output 'PASS: actual production control/ownership/completion/profile boundaries; native UI execution remains pending Windows.'

# Replay the actual native rectangles/identities from the failed installed run.
$captured=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'fixtures/song-editor-34678072633.json') -Raw|ConvertFrom-Json -AsHashtable
$nativeMain=$captured.controls[0].Clone();$nativeMain.name='BeatSprig 1.0.1'; # Current title applied only to replay; historical fixture stays unchanged.
$nativeArea=$captured.controls[1];$nativeSong=$captured.controls[2];$nativeContent=$captured.controls[3]
$point=Get-BeatQuaySongTitlePoint $nativeMain $nativeSong $nativeContent $nativeArea 7720
Check ($point.x -eq 428 -and $point.y -eq 178) 'Observed Song-Editor title strip was not selected.'
foreach($mutation in @('foreign_pid','wrong_title','wrong_class','wrong_ancestry','empty_size','hidden','disabled','content_outside','title_missing','title_oversized','narrow','outside_area','main_identity','nonfinite')){
 $m=$nativeMain.Clone();$s=$nativeSong.Clone();$c=$nativeContent.Clone();$a=$nativeArea.Clone()
 switch($mutation){
  foreign_pid{$s.process_id=1} wrong_title{$s.name='Mixer'} wrong_class{$s.class_name='QDialog'} wrong_ancestry{$c.automation_id='foreign.SongEditorWindow'}
  empty_size{$s.width=0} hidden{$s.visible=$false} disabled{$s.enabled=$false} content_outside{$c.x=0} title_missing{$c.y=$s.y} title_oversized{$c.y=$s.y+80}
  narrow{$s.width=120} outside_area{$a.x=300} main_identity{$m.class_name='QDialog'} nonfinite{$s.x=[double]::NaN}
 }
 Reject {Get-BeatQuaySongTitlePoint $m $s $c $a 7720} "Unqualified title-strip geometry accepted: $mutation"
}
$tempoItem=@{snapshot=$captured.controls[4];element='actual tempo element'}
$tempoWindow=@{snapshot=@{truncated=$false};items=@($tempoItem)}
Check ((Find-BeatQuayConsumerTempo $tempoWindow 7720).element -ceq 'actual tempo element') 'Actual empty-help tempo was not selected.'
foreach($mutation in @('pid','type','class','ancestry','hidden','duplicate')){
 $c=$captured.controls[4].Clone()
 switch($mutation){pid{$c.process_id=2} type{$c.type='Edit'} class{$c.class_name='QWidget'} ancestry{$c.automation_id += '.foreign'} hidden{$c.visible=$false}}
 $bad=@{snapshot=@{truncated=$false};items=@(@{snapshot=$c})}
 if($mutation -eq 'duplicate'){$bad.items+=@(@{snapshot=$c.Clone()})}
 Reject {Find-BeatQuayConsumerTempo $bad 7720} "Invalid native tempo selector accepted: $mutation"
}
# Exercise the production direct-child provider boundary against captured native data.
# Only the platform observation calls are replayed; selectors and refusals are production.
if(-not ('Windows.Automation.TreeScope' -as [type])){
 Add-Type 'namespace System.Windows.Automation { public enum TreeScope { Children=2 } public class Condition { public static readonly object TrueCondition=new object(); } }'
}
$savedReader=${function:Get-BeatQuayConsumerControl}
function Get-BeatQuayConsumerControl($Element){return $Element.snapshot}
function ReplayElement($Snapshot){
 $e=[pscustomobject]@{snapshot=$Snapshot;children=@();queried=$false}
 $e|Add-Member -MemberType ScriptMethod -Name FindAll -Value {
  param($Scope,$Condition)
  if($Scope -ne [Windows.Automation.TreeScope]::Children){throw 'Expected exact direct-child traversal'}
  $this.queried=$true
  $r=[pscustomobject]@{Count=$this.children.Count;entries=$this.children}
  $r|Add-Member -MemberType ScriptMethod -Name Item -Value {param($Index);return $this.entries[$Index]}
  return $r
 }
 return $e
}
try{
 $mainElement=ReplayElement $nativeMain;$songElement=ReplayElement $nativeSong;$contentElement=ReplayElement $nativeContent;$areaElement=ReplayElement $nativeArea
 $songElement.children=@($contentElement)
 $providerMain=@{element=$mainElement;snapshot=@{truncated=$false;root=$nativeMain};items=@(
  @{element=$songElement;snapshot=$nativeSong},@{element=$areaElement;snapshot=$nativeArea})}
 $providerState=@{process=@{Id=7720}}
 $observed=Get-BeatQuaySongEditorSurface $providerState $providerMain
 Check ($songElement.queried -and $observed.content.automation_id -ceq $nativeContent.automation_id) 'Actual direct content provider was not required.'
 foreach($mutation in @('missing_child','extra_child','content_pid','content_class','content_id','truncated')){
  $songElement.children=@($contentElement);$contentElement.snapshot=$nativeContent.Clone();$providerMain.snapshot.truncated=$false
  switch($mutation){
   missing_child{$songElement.children=@()} extra_child{$songElement.children=@($contentElement,$contentElement)}
   content_pid{$contentElement.snapshot.process_id=5} content_class{$contentElement.snapshot.class_name='QDialog'}
   content_id{$contentElement.snapshot.automation_id='foreign'} truncated{$providerMain.snapshot.truncated=$true}
  }
  Reject {Get-BeatQuaySongEditorSurface $providerState $providerMain} "Invalid direct provider accepted: $mutation"
 }
}finally{${function:Get-BeatQuayConsumerControl}=$savedReader}

# Execute the production maximization sequencer with native observation/input endpoints recorded.
# The provider selection/point guards above are real; these seams cannot exercise Windows UIA on macOS.
$script:titleCalls=[Collections.Generic.List[string]]::new();$script:titleHitFailure=0;$script:surfaceRead=0;$script:titleChange=$false;$script:noMaximize=$false;$script:postReads=0
function Wait-BeatQuayConsumerWindow($State,$Title){return @{snapshot=@{title=$Title}}}
function Set-BeatQuayConsumerForeground($State,$Window){$script:titleCalls.Add('foreground')}
function Get-BeatQuayConsumerWindows($State){
 $script:postReads++;if($script:noMaximize -and $script:postReads -gt 1){throw 'Bounded fixture ends unmaximized observation'}
 return @{snapshot=@{title='BeatSprig 1.0.1 - [Song-Editor]';truncated=$false;root=@{visible=$true;enabled=$true}}}}
function Get-BeatQuaySongEditorSurface($State,$Main){
 $script:surfaceRead++
 $s=$nativeSong.Clone()
 if($script:titleChange -and $script:surfaceRead -eq 3){$s.x++;$s.width--}
 if($script:surfaceRead -gt 3 -and -not $script:noMaximize){$s.x=$nativeArea.x;$s.y=$nativeArea.y;$s.width=$nativeArea.width;$s.height=$nativeArea.height}
 return @{main=$nativeMain;song=$s;content=$nativeContent;area=$nativeArea;song_element='exact retained element'}
}
function Assert-BeatQuaySongTitleHit($Surface,$Point){
 $script:titleCalls.Add('hit')
 if($script:titleHitFailure -gt 0 -and @($script:titleCalls|Where-Object {$_ -eq 'hit'}).Count -eq $script:titleHitFailure){throw 'Point belongs to another accessible surface'}
}
function Send-BeatQuayConsumerTitleClick($State,$Point){$script:titleCalls.Add('click')}
$state=@{process=@{Id=7720};processOwned=$true;workflow=@{current_action='maximize_song_editor';inputs=[Collections.Generic.List[object]]::new();stages=[Collections.Generic.List[object]]::new()}}
Invoke-BeatQuayConsumerMaximizeSongEditor $state
Check (($script:titleCalls -join ',') -ceq 'foreground,hit,click,hit,click') 'Title-bar input was not individually hit-tested.'
Check ($state.workflow.inputs.Count -eq 2) 'Native title clicks were not recorded.'
Check ($state.workflow.song_editor_maximized -and $state.workflow.stages.Count -eq 1) 'Post-input full-area proof missing.'
Check ((Resolve-BeatQuayConsumerWindowTitle $state 'BeatSprig 1.0.1') -ceq 'BeatSprig 1.0.1 - [Song-Editor]') 'Actual maximized title not resolved.'
Check ((Resolve-BeatQuayConsumerWindowTitle $state 'Evening Pulse - BeatSprig 1.0.1') -ceq 'Evening Pulse - BeatSprig 1.0.1 - [Song-Editor]') 'Saved project title not resolved.'
Check ((Resolve-BeatQuayConsumerWindowTitle $state 'Export completed') -ceq 'Export completed') 'Dialog title changed.'
$state.workflow.song_editor_maximized=$false
Check ((Resolve-BeatQuayConsumerWindowTitle $state 'BeatSprig 1.0.1') -ceq 'BeatSprig 1.0.1') 'Suffix accepted without actual full-area proof.'
foreach($failure in @(1,2)){
 $script:titleCalls.Clear();$script:surfaceRead=0;$script:titleHitFailure=$failure
 Reject {Invoke-BeatQuayConsumerMaximizeSongEditor $state} 'Foreign title hit still sent input.'
 Check (@($script:titleCalls|Where-Object {$_ -eq 'click'}).Count -eq ($failure-1)) 'Input occurred after failed exact-element hit proof.'
}
$script:titleCalls.Clear();$script:surfaceRead=0;$script:titleHitFailure=0;$script:titleChange=$true
Reject {Invoke-BeatQuayConsumerMaximizeSongEditor $state} 'Geometry changed between double clicks.'
Check (@($script:titleCalls|Where-Object {$_ -eq 'click'}).Count -eq 1) 'Second click went to changed geometry.'
Write-Output 'PASS: actual captured MDI title geometry, 14 refusals, production double-click sequencing and per-click refusal.'

$script:titleCalls.Clear();$script:surfaceRead=0;$script:postReads=0;$script:titleChange=$false;$script:noMaximize=$true
$state.workflow.song_editor_maximized=$false;$oldStages=$state.workflow.stages.Count
Reject {Invoke-BeatQuayConsumerMaximizeSongEditor $state} 'No actual full-area maximization still succeeded.'
Check (-not $state.workflow.song_editor_maximized -and $state.workflow.stages.Count -eq $oldStages) 'Unmaximized geometry produced a success receipt.'
Write-Output 'PASS: required maximized geometry and exact source-defined MDI titles; profile failure attribution retains six foreign/ownership refusals.'
