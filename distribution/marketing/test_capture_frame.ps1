# Copyright 2026 Trieflow LLC. MIT. Replay observed Windows geometry; native reads remain pending.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$file=Join-Path $PSScriptRoot 'capture_frame.ps1'
if(-not (Test-Path $file)){throw 'Owned capture frame policy is not implemented'}
. $file
function Check($Value,$Message){if(-not $Value){throw $Message}}
function Snapshot {
 $main=@{available=$true;process_id=744;native_window_handle=2883910;type='Window';visible=$true;enabled=$true;
  class_name='lmms::gui::MainWindow';name='Evening Pulse - BeatSprig 1.0.1 - [Song-Editor]';x=232.0;y=81.0;width=1456.0;height=901.0}
 return @{main=$main;foreground=$main.Clone();main_native_pid=744;foreground_native_pid=744;foreground_handle=2883910;
  native_visible=$true;minimized=$false;native_rect=@{x=224;y=50;width=1472;height=940};
  desktop=@{x=0;y=0;width=1920;height=1080};display=@{width=1920;height=1080;bits=32};dpi=96}
}
$state=@{process=@{Id=744};workflow=@{main_window_handle=2883910}}
$title='Evening Pulse - BeatSprig 1.0.1 - [Song-Editor]'
$good=Snapshot
Assert-BeatSprigMarketingFrame $good $state $title @()
foreach($mutation in @('pid','native_pid','handle','foreground','hidden','minimized','offscreen','outside_frame','small','dpi','type','title','disabled','display')){
 $bad=Snapshot
 switch($mutation){
  pid{$bad.main.process_id=0} native_pid{$bad.main_native_pid=7508} handle{$bad.main.native_window_handle=42}
  foreground{$bad.foreground_native_pid=7508} hidden{$bad.native_visible=$false} minimized{$bad.minimized=$true}
  offscreen{$bad.desktop.width=1400} outside_frame{$bad.native_rect.width=1400} small{$bad.main.width=1399}
  dpi{$bad.dpi=120} type{$bad.main.type='Pane'} title{$bad.main.name='Untitled'} disabled{$bad.foreground.enabled=$false}
  display{$bad.display.bits=24}
 }
 $failed=$false;try{Assert-BeatSprigMarketingFrame $bad $state $title @()}catch{$failed=$true}
 Check $failed "Frame mutation was accepted: $mutation"
}
$good=Snapshot;$good.main.enabled=$false;$good.foreground=$good.main.Clone()
$good.foreground.native_window_handle=2818072;$good.foreground_handle=2818072;$good.foreground.name='Export project';$good.foreground.enabled=$true
Assert-BeatSprigMarketingFrame $good $state $title @('Export project')
$good.foreground.name='Foreign dialog'
$failed=$false;try{Assert-BeatSprigMarketingFrame $good $state $title @('Export project')}catch{$failed=$true}
Check $failed 'Unobserved foreground dialog title was accepted'
$script:ownerCalls=0
function Assert-BeatQuayConsumerOwner($State){$script:ownerCalls++}
function Resolve-BeatQuayConsumerWindowTitle($State,$Title){return $Title+' - [Song-Editor]'}
function Get-BeatSprigMarketingNativeFrame($State){return Snapshot}
$observed=Read-BeatSprigMarketingFrame $state 'Evening Pulse - BeatSprig 1.0.1' @()
Check ($ownerCalls -eq 2 -and $observed.width -is [int] -and $observed.width -eq 1456 -and $observed.x -is [int] -and
 $observed.x -eq 232 -and $observed.original_observation.main.width -is [double]) 'Actual UIA double coordinates did not match original integer GDI capture metadata'
'PASS actual-size frame and allowed owned modal cases plus15 refusal mutations; no native read/capture claimed.'
