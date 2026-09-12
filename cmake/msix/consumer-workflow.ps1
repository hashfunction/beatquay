# Copyright 2026 Trieflow LLC. MIT. Normal installed consumer UI and unedited native screen capture.
. (Join-Path $PSScriptRoot 'consumer-display.ps1')

function Add-BeatQuayConsumerTypes {
 if ('BeatQuayConsumer.Native' -as [type]) {return}
 Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
namespace BeatQuayConsumer {
 public static class Native {
  [StructLayout(LayoutKind.Sequential)] struct POINT {public int X,Y;}
  [StructLayout(LayoutKind.Sequential)] struct INPUT {public uint type;public UNION data;}
  [StructLayout(LayoutKind.Explicit)] struct UNION {[FieldOffset(0)]public MOUSE mouse;[FieldOffset(0)]public KEY key;}
  [StructLayout(LayoutKind.Sequential)] struct MOUSE {public int x,y;public uint data,flags,time;public UIntPtr extra;}
  [StructLayout(LayoutKind.Sequential)] struct KEY {public ushort vk,scan;public uint flags,time;public UIntPtr extra;}
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hwnd,int command);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint pid);
  [DllImport("user32.dll")] public static extern uint GetDpiForWindow(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hwnd,int x,int y,int width,int height,bool repaint);
  [DllImport("user32.dll")] static extern bool SetCursorPos(int x,int y);
  [DllImport("user32.dll")] static extern IntPtr WindowFromPoint(POINT point);
  [DllImport("user32.dll")] static extern IntPtr GetAncestor(IntPtr hwnd,uint flags);
  [DllImport("user32.dll",SetLastError=true)] static extern uint SendInput(uint count,INPUT[] inputs,int size);
  public static void Foreground(int pid){uint actual;GetWindowThreadProcessId(GetForegroundWindow(),out actual);if(pid<=0||actual!=pid)throw new InvalidOperationException("Owned foreground process changed");}
  static void Send(INPUT input){if(SendInput(1,new[]{input},Marshal.SizeOf<INPUT>())!=1)throw new Win32Exception(Marshal.GetLastWin32Error());}
  public static void Key(int pid,ushort key,bool up){Foreground(pid);Send(new INPUT{type=1,data=new UNION{key=new KEY{vk=key,flags=up?2u:0u}}});}
  public static void Click(int pid,int x,int y){Foreground(pid);uint actual;GetWindowThreadProcessId(WindowFromPoint(new POINT{X=x,Y=y}),out actual);if(actual!=pid)throw new InvalidOperationException("Click point is covered by a foreign window");if(!SetCursorPos(x,y))throw new InvalidOperationException("Cannot position owned input");Send(new INPUT{type=0,data=new UNION{mouse=new MOUSE{flags=2}}});Send(new INPUT{type=0,data=new UNION{mouse=new MOUSE{flags=4}}});}
  public static void RequireTempoPointer(int pid,long expected,long foreground,int hitPid,long hitRoot){if(pid<=0||expected==0||foreground!=expected||hitPid!=pid||hitRoot!=expected)throw new InvalidOperationException("Exact native tempo foreground/hit ownership changed");}
  public static void TempoPointer(int pid,IntPtr main,int x,int y,string kind){
   if(kind!="wheel"&&kind!="context")throw new InvalidOperationException("Unexpected tempo pointer action");
   Foreground(pid);if(GetForegroundWindow()!=main)throw new InvalidOperationException("Tempo main foreground changed");
   if(!SetCursorPos(x,y))throw new InvalidOperationException("Cannot position tempo pointer");
   uint actual;IntPtr hit=WindowFromPoint(new POINT{X=x,Y=y});GetWindowThreadProcessId(hit,out actual);
   RequireTempoPointer(pid,main.ToInt64(),GetForegroundWindow().ToInt64(),(int)actual,GetAncestor(hit,2).ToInt64());
   if(kind=="wheel"){Send(new INPUT{type=0,data=new UNION{mouse=new MOUSE{flags=0x800,data=120}}});}
   else{INPUT[] packet={new INPUT{type=0,data=new UNION{mouse=new MOUSE{flags=8}}},new INPUT{type=0,data=new UNION{mouse=new MOUSE{flags=16}}}};uint sent=SendInput(2,packet,Marshal.SizeOf<INPUT>());if(sent!=2){if(sent==1)Send(packet[1]);throw new InvalidOperationException("Tempo context click input incomplete");}}
  }
  public static void DismissTempoMenu(int pid,IntPtr main,IntPtr menu){
   uint actual;GetWindowThreadProcessId(menu,out actual);IntPtr foreground=GetForegroundWindow();
   if(pid<=0||main==IntPtr.Zero||menu==IntPtr.Zero||actual!=pid||(foreground!=main&&foreground!=menu))throw new InvalidOperationException("Tempo popup ownership changed before Escape");
   Foreground(pid);Key(pid,0x1b,false);Key(pid,0x1b,true);
  }
 }
}
'@
}

function Assert-BeatQuayConsumerControl($Snapshot,[int]$ProcessId,[string]$Type,[string]$Name) {
 if($ProcessId -le 0 -or -not $Snapshot.available -or $Snapshot.process_id -ne $ProcessId -or
  -not $Snapshot.visible -or -not $Snapshot.enabled -or $Snapshot.width -le 0 -or $Snapshot.height -le 0 -or
  $Snapshot.type -cne $Type -or ($Name -and $Snapshot.name -cne $Name)){throw "Control is not the exact visible enabled owned input: $Type / $Name"}
}

function Get-BeatQuayConsumerControl($Element) {
 try {
  $type=$Element.GetCurrentPropertyValue([Windows.Automation.AutomationElement]::ControlTypeProperty,$true)
  if($null -eq $type -or $type -eq [Windows.Automation.AutomationElement]::NotSupported){throw 'Control type unavailable'}
  $c=$Element.Current;$b=$c.BoundingRectangle
  $value=$null;$pattern=$null
  if($Element.TryGetCurrentPattern([Windows.Automation.ValuePattern]::Pattern,[ref]$pattern)){$value=[string]$pattern.Current.Value}
  return @{available=$true;name=[string]$c.Name;type=$type.ProgrammaticName.Replace('ControlType.','');help=[string]$c.HelpText;
   automation_id=[string]$c.AutomationId;class_name=[string]$c.ClassName;process_id=$c.ProcessId;visible=(-not $c.IsOffscreen);enabled=$c.IsEnabled;
   x=$b.X;y=$b.Y;width=$b.Width;height=$b.Height;value=$value}
 } catch {return @{available=$false;observation_error=$_.Exception.Message}}
}

function Assert-BeatQuayConsumerOwner($State) {
 $State.process.Refresh()
 if(-not $State.processOwned -or $State.process.HasExited -or $State.processHandle.IsInvalid -or $State.processHandle.IsClosed){throw 'Retained consumer process is not live and owned'}
 if([BeatQuayQualification.NativePackageProbe]::GetFullName($State.process.Handle) -cne $State.ownedPackageFullName -or
  (Get-CanonicalPath $State.process.MainModule.FileName) -ine (Get-CanonicalPath (Join-Path $State.installed.InstallLocation 'beatsprig.exe'))){throw 'Consumer process package/executable identity changed'}
}

function Get-BeatQuayConsumerWindows($State) {
 Assert-BeatQuayConsumerOwner $State
 $condition=[Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::ProcessIdProperty,$State.process.Id)
 $windows=[Windows.Automation.AutomationElement]::RootElement.FindAll([Windows.Automation.TreeScope]::Children,$condition)
 if($windows.Count -gt 8){throw 'Consumer window count exceeds bound'}
 foreach($index in 0..($windows.Count-1)){
  if($windows.Count -eq 0){break}
  $element=$windows.Item($index);$current=Get-BeatQuayConsumerControl $element
  $items=[Collections.Generic.List[object]]::new();$controls=[Collections.Generic.List[object]]::new();$truncated=(-not $current.available)
  if($current.available){
   if($current.process_id -ne $State.process.Id){throw 'Observed window PID changed after owned enumeration'}
   $all=$element.FindAll([Windows.Automation.TreeScope]::Subtree,[Windows.Automation.Condition]::TrueCondition)
   if($all.Count -gt 1500){throw 'Consumer control inventory exceeds bound'}
   for($i=0;$i -lt $all.Count;$i++){
    $child=$all.Item($i);$snapshot=Get-BeatQuayConsumerControl $child
    if(-not $snapshot.available){$truncated=$true}
    elseif($snapshot.name.Length -gt 4096 -or $snapshot.help.Length -gt 4096 -or ($snapshot.value -and $snapshot.value.Length -gt 16384)){throw 'Consumer control text exceeds bound'}
    $items.Add(@{element=$child;snapshot=$snapshot});$controls.Add($snapshot)
   }
  }
  $snapshot=@{title=if($current.available){$current.name}else{''};process_id=$State.process.Id;truncated=$truncated;root=$current;controls=@($controls)}
  [pscustomobject]@{element=$element;snapshot=$snapshot;items=@($items)}
 }
}

function Resolve-BeatQuayConsumerWindowTitle($State,[string]$Title) {
 # Qt's native MDI title merge is enabled only after the actual Song-Editor filled
 # the MDI area. Dialog titles and unmaximized main titles stay exact.
 if($State.workflow.Contains('song_editor_maximized') -and $State.workflow.song_editor_maximized -and
  ($Title -ceq 'BeatSprig 1.0.1' -or $Title.EndsWith(' - BeatSprig 1.0.1',[StringComparison]::Ordinal))){return $Title+' - [Song-Editor]'}
 return $Title
}

function Wait-BeatQuayConsumerWindow($State,[string]$Title,[int]$Seconds=30) {
 $Title=Resolve-BeatQuayConsumerWindowTitle $State $Title
 $deadline=[DateTime]::UtcNow.AddSeconds($Seconds)
 do {
  $windows=@(Get-BeatQuayConsumerWindows $State)
  $State.workflow.last_observation=@($windows|ForEach-Object {$_.snapshot})
  $matches=@($windows|Where-Object {$_.snapshot.title -ceq $Title -and -not $_.snapshot.truncated -and $_.snapshot.root.visible -and $_.snapshot.root.enabled})
  if($matches.Count -gt 1){throw "Ambiguous owned consumer window: $Title"}
  if($matches.Count -eq 1){return $matches[0]}
  Start-Sleep -Milliseconds 200
 }while([DateTime]::UtcNow -lt $deadline)
 throw "Exact complete owned consumer window did not appear: $Title"
}

function Find-BeatQuayConsumerControl($Window,[int]$ProcessId,[string]$Type,[string]$Name,[string]$AutomationId='', [string]$Help='') {
 if($Window.snapshot.truncated){throw 'Incomplete UI snapshot cannot authorize input'}
 $matches=@($Window.items|Where-Object {$s=$_.snapshot;$s.available -and $s.type -ceq $Type -and $s.process_id -eq $ProcessId -and $s.visible -and $s.enabled -and
  (-not $Name -or $s.name -ceq $Name) -and (-not $AutomationId -or $s.automation_id -ceq $AutomationId) -and (-not $Help -or $s.help -ceq $Help)})
 if($matches.Count -ne 1){throw "Expected one owned $Type input: $Name / $AutomationId / $Help; found $($matches.Count)"}
 return $matches[0]
}

function Get-BeatQuaySongTitlePoint($Main,$Song,$Content,$Area,[int]$ProcessId) {
 $mainId='QApplication.lmms::gui::MainWindow'
 $areaId=$mainId+'.QWidget.QWidget.QSplitter.QMdiArea'
 $songId=$areaId+'.QWidget.lmms::gui::SubWindow'
 foreach($pair in @(@($Main,'Window','lmms::gui::MainWindow',$mainId),@($Area,'Pane','QMdiArea',$areaId),
   @($Song,'Window','lmms::gui::SubWindow',$songId),@($Content,'Window','lmms::gui::SongEditorWindow',($songId+'.lmms::gui::SongEditorWindow')))){
  $s=$pair[0];Assert-BeatQuayConsumerControl $s $ProcessId $pair[1] ''
  if($s.class_name -cne $pair[2] -or $s.automation_id -cne $pair[3]){throw 'Unexpected Song-Editor provider ancestry'}
  foreach($key in @('x','y','width','height')){if(-not [double]::IsFinite($s[$key])){throw 'Nonfinite Song-Editor geometry'}}
 }
 if($Song.name -cne 'Song-Editor' -or $Main.name -cne 'BeatSprig 1.0.1'){throw 'Unexpected Song-Editor surface title'}
 foreach($pair in @(@($Area,$Main),@($Song,$Area),@($Content,$Song))){
  $child=$pair[0];$parent=$pair[1]
  if($child.x -lt $parent.x -or $child.y -lt $parent.y -or $child.x+$child.width -gt $parent.x+$parent.width -or
   $child.y+$child.height -gt $parent.y+$parent.height){throw 'Song-Editor surface lies outside its observed parent'}
 }
 $titleHeight=$Content.y-$Song.y
 # Observed outer/content rectangles define the title strip. Source places the icon
 # in the left 24px and at most three 17px custom buttons plus gaps at the right.
 if($Song.width -lt 200 -or $titleHeight -lt 18 -or $titleHeight -gt 40 -or
  $Content.x-$Song.x -gt 8 -or $Song.x+$Song.width-$Content.x-$Content.width -gt 8 -or
  $Song.y+$Song.height-$Content.y-$Content.height -gt 8){throw 'Song-Editor title strip is not the source-defined layout'}
 return @{x=[int][Math]::Round($Song.x+$Song.width/2);y=[int][Math]::Round($Song.y+$titleHeight/2)}
}

function Get-BeatQuaySongEditorSurface($State,$Main) {
 $song=Find-BeatQuayConsumerControl $Main $State.process.Id 'Window' 'Song-Editor'
 # QAccessibleMdiSubWindow exposes exactly its widget(), not custom title buttons.
 $children=$song.element.FindAll([Windows.Automation.TreeScope]::Children,[Windows.Automation.Condition]::TrueCondition)
 if($children.Count -ne 1){throw 'Song-Editor lacks its one direct accessible content window'}
 $area=Find-BeatQuayConsumerControl $Main $State.process.Id 'Pane' '' 'QApplication.lmms::gui::MainWindow.QWidget.QWidget.QSplitter.QMdiArea'
 $surface=@{main=(Get-BeatQuayConsumerControl $Main.element);song=(Get-BeatQuayConsumerControl $song.element);
  content=(Get-BeatQuayConsumerControl $children.Item(0));area=(Get-BeatQuayConsumerControl $area.element);song_element=$song.element}
 foreach($entry in @(@($surface.main,'Window','lmms::gui::MainWindow',$Main.snapshot.root.automation_id),
   @($surface.song,'Window','lmms::gui::SubWindow',$song.snapshot.automation_id),
   @($surface.content,'Window','lmms::gui::SongEditorWindow',($song.snapshot.automation_id+'.lmms::gui::SongEditorWindow')),
   @($surface.area,'Pane','QMdiArea',$area.snapshot.automation_id))){
  Assert-BeatQuayConsumerControl $entry[0] $State.process.Id $entry[1] ''
  foreach($key in @('x','y','width','height')){if(-not [double]::IsFinite($entry[0][$key])){throw 'Nonfinite live Song-Editor geometry'}}
  if($entry[0].class_name -cne $entry[2] -or $entry[0].automation_id -cne $entry[3]){throw 'Live Song-Editor provider identity changed'}
 }
 if($surface.song.name -cne 'Song-Editor'){throw 'Live MDI content title changed'}
 return $surface
}

function Assert-BeatQuaySongTitleHit($Surface,$Point) {
 $hit=[Windows.Automation.AutomationElement]::FromPoint([Windows.Point]::new($Point.x,$Point.y))
 if($null -eq $hit -or -not [Windows.Automation.Automation]::Compare($hit,$Surface.song_element)){
  throw 'Title-strip point is covered by a different accessible surface'
 }
}

function Send-BeatQuayConsumerTitleClick($State,$Point) {
 [BeatQuayConsumer.Native]::Click($State.process.Id,$Point.x,$Point.y)
}

function Invoke-BeatQuayConsumerMaximizeSongEditor($State) {
 $main=Wait-BeatQuayConsumerWindow $State 'BeatSprig 1.0.1'
 Set-BeatQuayConsumerForeground $State $main
 $surface=Get-BeatQuaySongEditorSurface $State $main
 $point=Get-BeatQuaySongTitlePoint $surface.main $surface.song $surface.content $surface.area $State.process.Id
 # Normal Qt title-bar double-click, with no synthetic button or WindowPattern on
 # the top-level QWindow. Recheck exact live geometry and accessible hit each time.
 for($click=0;$click -lt 2;$click++){
  Assert-BeatQuayConsumerOwner $State
  $current=Get-BeatQuaySongEditorSurface $State $main
  $now=Get-BeatQuaySongTitlePoint $current.main $current.song $current.content $current.area $State.process.Id
  if($now.x -ne $point.x -or $now.y -ne $point.y -or
   @('x','y','width','height'|Where-Object {$current.song[$_] -ne $surface.song[$_]}).Count){throw 'Song-Editor geometry changed between title clicks'}
  Assert-BeatQuaySongTitleHit $current $now
  Send-BeatQuayConsumerTitleClick $State $now
  $State.workflow.inputs.Add(@{action=$State.workflow.current_action;kind='native_title_click';click_index=$click;control=$current.song;content=$current.content;x=$now.x;y=$now.y})
  if($click -eq 0){Start-Sleep -Milliseconds 70}
 }
 $deadline=[DateTime]::UtcNow.AddSeconds(30)
 do{
  $windows=@(Get-BeatQuayConsumerWindows $State)
  $State.workflow.last_observation=@($windows|ForEach-Object {$_.snapshot})
  $matches=@($windows|Where-Object {$_.snapshot.title -ceq 'BeatSprig 1.0.1 - [Song-Editor]' -and
   -not $_.snapshot.truncated -and $_.snapshot.root.visible -and $_.snapshot.root.enabled})
  if($matches.Count -gt 1){throw 'Ambiguous maximized main window'}
  if($matches.Count -eq 1){
   $main=$matches[0];$current=Get-BeatQuaySongEditorSurface $State $main
   if(@('x','y','width','height'|Where-Object {[Math]::Abs($current.song[$_]-$current.area[$_]) -gt 1}).Count -eq 0){
    $State.workflow.song_editor_maximized=$true
    Save-BeatQuayConsumerStage $State 'song_editor_maximized' $main
    return
   }
  }
  Start-Sleep -Milliseconds 200
 }while([DateTime]::UtcNow -lt $deadline)
 throw 'Song-Editor did not fill its actual owned MDI area after the title-bar double-click'
}

function Set-BeatQuayConsumerForeground($State,$Window) {
 Assert-BeatQuayConsumerOwner $State
 $handle=[IntPtr]$Window.element.Current.NativeWindowHandle
 if($handle -eq [IntPtr]::Zero){throw 'Input window lacks a native handle'}
 [BeatQuayConsumer.Native]::SetForegroundWindow($handle)|Out-Null
 Start-Sleep -Milliseconds 100
 [BeatQuayConsumer.Native]::Foreground($State.process.Id)
}

function Invoke-BeatQuayConsumerClick($State,$Window,$Control,[switch]$Double) {
 Set-BeatQuayConsumerForeground $State $Window
 $snapshot=Get-BeatQuayConsumerControl $Control.element
 Assert-BeatQuayConsumerControl $snapshot $State.process.Id $Control.snapshot.type $Control.snapshot.name
 if($snapshot.automation_id -cne $Control.snapshot.automation_id -or $snapshot.class_name -cne $Control.snapshot.class_name -or $snapshot.help -cne $Control.snapshot.help){throw 'Input selector changed before click'}
 $x=[int]($snapshot.x+$snapshot.width/2);$y=[int]($snapshot.y+$snapshot.height/2)
 [BeatQuayConsumer.Native]::Click($State.process.Id,$x,$y)
 if($Double){Start-Sleep -Milliseconds 70;[BeatQuayConsumer.Native]::Click($State.process.Id,$x,$y)}
 $State.workflow.inputs.Add(@{action=$State.workflow.current_action;kind=if($Double){'native_double_click'}else{'native_click'};control=$snapshot;x=$x;y=$y})
}

function Send-BeatQuayConsumerKeys($State,$Window,[int[]]$Keys) {
 Set-BeatQuayConsumerForeground $State $Window
 $down=[Collections.Generic.List[int]]::new()
 try{foreach($key in $Keys){[BeatQuayConsumer.Native]::Key($State.process.Id,[uint16]$key,$false);$down.Add($key)}}
 finally{for($i=$down.Count-1;$i -ge 0;$i--){[BeatQuayConsumer.Native]::Key($State.process.Id,[uint16]$down[$i],$true)}}
 $State.workflow.inputs.Add(@{action=$State.workflow.current_action;kind='native_key_chord';window=$Window.snapshot.title;keys=$Keys})
}

function Set-BeatQuayConsumerValue($State,$Window,$Control,[string]$Value) {
 if($Value.Length -gt 1024){throw 'Consumer text input exceeds bound'}
 Set-BeatQuayConsumerForeground $State $Window
 $current=Get-BeatQuayConsumerControl $Control.element
 Assert-BeatQuayConsumerControl $current $State.process.Id $Control.snapshot.type $Control.snapshot.name
 $pattern=$Control.element.GetCurrentPattern([Windows.Automation.ValuePattern]::Pattern)
 if($pattern.Current.IsReadOnly){throw 'Consumer value input is read-only'}
 $pattern.SetValue($Value)
 if([string]$pattern.Current.Value -cne $Value){throw 'Consumer value did not match the actual UI field after input'}
 $State.workflow.inputs.Add(@{action=$State.workflow.current_action;kind='uia_value';control=$current;value=$Value})
}

function Invoke-BeatQuayConsumerFileDialog($State,[string]$Title,[string]$Path,[string]$Action) {
 $window=Wait-BeatQuayConsumerWindow $State $Title
 # QFileDialog's actual filename editor objectName; do not type into an arbitrary edit control.
 $edit=Find-BeatQuayConsumerControl $window $State.process.Id 'Edit' '' 'fileNameEdit'
 Set-BeatQuayConsumerValue $State $window $edit $Path
 $window=Wait-BeatQuayConsumerWindow $State $Title
 Invoke-BeatQuayConsumerClick $State $window (Find-BeatQuayConsumerControl $window $State.process.Id 'Button' $Action)
}

function Assert-BeatQuayConsumerExportResult($Snapshot,[int]$ProcessId,[string]$Path,[long]$Bytes) {
 if($Snapshot.title -cne 'Export completed' -or $Snapshot.process_id -ne $ProcessId -or $Snapshot.truncated -or $Bytes -le 44){throw 'No exact complete owned export result'}
 $details=@($Snapshot.controls|Where-Object {$_.available -and $_.type -ceq 'Edit' -and $_.process_id -eq $ProcessId -and $_.visible -and $_.value})
 if($details.Count -ne 1){throw 'Export result lacks exact readable result details'}
 $lines=@(([string]$details[0].value).Replace("`r",'').Split("`n")|Where-Object {$_ -ne ''})
 if($lines.Count -ne 2 -or $lines[0].Replace('\','/') -cne $Path.Replace('\','/') -or $lines[1] -cne "Completed: $Bytes bytes"){throw 'Export result path/bytes differ or contain warnings/residue'}
}

function Invoke-BeatQuayConsumerFileCheck($State,[string[]]$Arguments) {
 $result=& $State.python (Join-Path $PSScriptRoot 'consumer_files.py') @Arguments
 if($LASTEXITCODE -ne 0){throw "Independent consumer file verification failed: $($Arguments[0])"}
 return ($result -join "`n"|ConvertFrom-Json -AsHashtable)
}

function Remove-BeatQuayOwnedProfile($Profile,[bool]$ProcessTerminated) {
 if(-not $Profile){return}
 if(-not (Test-Path -LiteralPath $Profile.path)){if($Profile.ownership_established){throw 'Owned profile disappeared'};return}
 if(-not $ProcessTerminated -or -not $Profile.absent_before_activation -or -not $Profile.ownership_established -or $Profile.process_id -le 0 -or -not $Profile.package_full_name){throw 'Profile ownership/termination is unproven; preserving settings'}
 Assert-NoReparsePath $Profile.path
 if((Get-Item -LiteralPath $Profile.path -Force).CreationTimeUtc.ToString('o') -cne $Profile.creation_utc){throw 'Owned profile file was replaced; preserving settings'}
 if((Get-FileHash -LiteralPath $Profile.path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Profile.sha256){throw 'Owned profile changed after its last attributed observation; preserving settings'}
 [IO.File]::Delete($Profile.path)
 if(Test-Path -LiteralPath $Profile.path){throw 'Owned profile remains'}
 $Profile.cleanup_verified=$true
}

function Find-BeatQuayConsumerInput($State,[string]$Type,[string]$Name,[string]$Help='') {
 $deadline=[DateTime]::UtcNow.AddSeconds(15)
 do{
  $windows=@(Get-BeatQuayConsumerWindows $State);$State.workflow.last_observation=@($windows|ForEach-Object {$_.snapshot})
  $matches=@(foreach($window in $windows){if(-not $window.snapshot.truncated){foreach($control in $window.items){$s=$control.snapshot
   if($s.available -and $s.visible -and $s.enabled -and $s.process_id -eq $State.process.Id -and
    (-not $Type -or $s.type -ceq $Type) -and (-not $Name -or $s.name -ceq $Name) -and (-not $Help -or $s.help -ceq $Help)){
     @{window=$window;control=$control}
   }
  }}})
  if($matches.Count -gt 1){throw "Ambiguous live consumer selector: $Type / $Name / $Help"}
  if($matches.Count -eq 1){return $matches[0]}
  Start-Sleep -Milliseconds 200
 }while([DateTime]::UtcNow -lt $deadline)
 throw "Live consumer selector did not appear: $Type / $Name / $Help"
}

function Save-BeatQuayConsumerStage($State,[string]$Stage,$Window) {
 if($State.workflow.stages.Count -ge 20){throw 'Consumer stage evidence exceeds bound'}
 $State.workflow.stages.Add(@{stage=$Stage;observed_utc=[DateTime]::UtcNow.ToString('o');window=$Window.snapshot})
}

function Save-BeatQuayConsumerScreen($State,[string]$Name,[string]$EditorTitle,[string[]]$AllowedDialogs=@()) {
 $EditorTitle=Resolve-BeatQuayConsumerWindowTitle $State $EditorTitle
 Assert-BeatQuayConsumerOwner $State
 $windows=@(Get-BeatQuayConsumerWindows $State)
 $main=@($windows|Where-Object {$_.snapshot.title -ceq $EditorTitle -and -not $_.snapshot.truncated -and $_.snapshot.root.available -and $_.snapshot.root.visible})
 if($main.Count -ne 1){throw 'Capture lacks exact live project window'}
 foreach($window in $windows){if($window.snapshot.root.available -and $window.snapshot.root.visible -and $window.snapshot.title -cne $EditorTitle -and $window.snapshot.title -cnotin $AllowedDialogs){throw "Unexpected visible surface before capture: $($window.snapshot.title)"}}
 [BeatQuayConsumer.Native]::Foreground($State.process.Id)
 $root=$main[0].element.Current;$b=$root.BoundingRectangle
 $rectangle=[Drawing.Rectangle]::new([int]$b.X,[int]$b.Y,[int]$b.Width,[int]$b.Height)
 if($b.Width -lt 1400 -or $b.Height -lt 850 -or -not [Windows.Forms.SystemInformation]::VirtualScreen.Contains($rectangle)){throw 'Actual project capture is not readable and fully inside the native desktop'}
 $path=Join-Path $State.workflow.output ($Name+'.png')
 if(Test-Path -LiteralPath $path){throw 'Capture output already exists'}
 $bitmap=[Drawing.Bitmap]::new($rectangle.Width,$rectangle.Height);$graphics=[Drawing.Graphics]::FromImage($bitmap)
 try{$graphics.CopyFromScreen($rectangle.X,$rectangle.Y,0,0,$bitmap.Size);$bitmap.Save($path,[Drawing.Imaging.ImageFormat]::Png)}finally{$graphics.Dispose();$bitmap.Dispose()}
 $State.workflow.screenshots.Add(@{file=$Name+'.png';sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant();
  captured_utc=[DateTime]::UtcNow.ToString('o');method='native CopyFromScreen; no pixel editing, resizing, overlay or emulation';
  source_commit=$env:GITHUB_SHA;package_sha256=$State.unsignedPackageSha256;package_full_name=$State.ownedPackageFullName;
  process_id=$State.process.Id;executable_sha256=$State.executableSha256;project_title=$EditorTitle;
  x=$rectangle.X;y=$rectangle.Y;width=$rectangle.Width;height=$rectangle.Height;
  dpi=[BeatQuayConsumer.Native]::GetDpiForWindow([IntPtr]$root.NativeWindowHandle);display=$State.displayEvidence.after;
  foreground_window=[BeatQuayConsumer.Native]::GetForegroundWindow().ToInt64();allowed_dialogs=$AllowedDialogs})
}

function Confirm-BeatQuayConsumerProfile($State,[switch]$Initial,[switch]$AfterClose) {
 $record=$State.profile
 if(-not $record -or -not $record.absent_before_activation -or -not $State.processOwned -or
  ($AfterClose -and (-not $State.cleanClose -or -not $State.processExit.normal_exit))){throw 'Profile attribution lacks exact owned activation or normal close'}
 if(-not $AfterClose){Assert-BeatQuayConsumerOwner $State}
 Assert-NoReparsePath $record.path
 $item=Get-Item -LiteralPath $record.path -Force
 if($item.PSIsContainer -or $item.LinkType -or $item.Length -le 0 -or $item.Length -gt 2MB -or
  $item.CreationTimeUtc -lt $State.activationStartedUtc -or $item.CreationTimeUtc -gt [DateTime]::UtcNow){throw 'Profile creation is outside owned activation or file bounds'}
 if($Initial){
  $record.initial_path=Join-Path $State.temporary '.beatquay-profile-initial.xml'
  [IO.File]::Copy($record.path,$record.initial_path,$false)
  $record.creation_utc=$item.CreationTimeUtc.ToString('o')
 }elseif($item.CreationTimeUtc.ToString('o') -cne $record.creation_utc){throw 'Owned profile file was replaced'}
 $beforeHash=(Get-FileHash -LiteralPath $record.path -Algorithm SHA256).Hash.ToLowerInvariant()
 $arguments=@('profile','--before',$record.initial_path,'--after',$record.path,'--working',$State.workingDirectory.path)
 foreach($project in $record.projects){$arguments+=@('--project',$project)}
 $checked=Invoke-BeatQuayConsumerFileCheck $State $arguments
 $afterHash=(Get-FileHash -LiteralPath $record.path -Algorithm SHA256).Hash.ToLowerInvariant()
 if($beforeHash -cne $afterHash -or $checked.after_sha256 -cne $afterHash){throw 'Profile changed during ownership verification'}
 $record.sha256=$afterHash;$record.process_id=$State.process.Id;$record.package_full_name=$State.ownedPackageFullName
 $record.ownership_established=$true
 $record.observations.Add(@{action=if($Initial){'normal_first_run'}elseif($AfterClose){'normal_close'}else{$State.workflow.current_action};
  sha256=$afterHash;changed_fields=$checked.changed_fields;observed_utc=[DateTime]::UtcNow.ToString('o')})
}

function Confirm-BeatQuayConsumerFailureProfile($State) {
 $State.workflow.profile_attribution_error=$null
 try {
  # Before mandatory process termination, retain the original handle/package gate
  # and the same XML allowlist/creation-time/hash check used after successful actions.
  if($State.profile -and $State.profile.ownership_established){Confirm-BeatQuayConsumerProfile $State}
 }catch{$State.workflow.profile_attribution_error=$_.Exception.Message}
}

function Find-BeatQuayConsumerTempo($Main,[int]$ProcessId) {
 # SongEditor creates the sole direct mainToolbar LcdSpinBox and binds m_tempoModel.
 # UIA records its full QObject ancestry and Group role; QWidget tooltip is not HelpText.
 $control=Find-BeatQuayConsumerControl $Main $ProcessId 'Group' '' 'QApplication.lmms::gui::MainWindow.QWidget.mainToolbar.lmms::gui::LcdSpinBox'
 if($control.snapshot.class_name -cne 'lmms::gui::LcdSpinBox'){throw 'Unexpected native tempo widget class'}
 return $control
}

function Get-BeatQuayTempoPoint($Main,$Tempo,[int]$ProcessId) {
 Assert-BeatQuayConsumerControl $Main $ProcessId 'Window' ''
 Assert-BeatQuayConsumerControl $Tempo $ProcessId 'Group' ''
 $mainId='QApplication.lmms::gui::MainWindow'
 if($Main.class_name -cne 'lmms::gui::MainWindow' -or $Main.automation_id -cne $mainId -or
  $Tempo.class_name -cne 'lmms::gui::LcdSpinBox' -or $Tempo.automation_id -cne ($mainId+'.QWidget.mainToolbar.lmms::gui::LcdSpinBox')){throw 'Unexpected tempo provider ancestry'}
 foreach($s in @($Main,$Tempo)){foreach($key in @('x','y','width','height')){if(-not [double]::IsFinite($s[$key])){throw 'Nonfinite tempo geometry'}}}
 if($Tempo.x -lt $Main.x -or $Tempo.y -lt $Main.y -or $Tempo.x+$Tempo.width -gt $Main.x+$Main.width -or $Tempo.y+$Tempo.height -gt $Main.y+$Main.height){throw 'Tempo lies outside owned main window'}
 return @{x=[int]($Tempo.x+$Tempo.width/2);y=[int]($Tempo.y+$Tempo.height/2)}
}

function Assert-BeatQuayTempoHit($Control,$Point) {
 $hit=[Windows.Automation.AutomationElement]::FromPoint([Windows.Point]::new($Point.x,$Point.y))
 if($null -eq $hit -or -not [Windows.Automation.Automation]::Compare($hit,$Control.element)){throw 'Tempo point is covered by a different accessible surface'}
}

function Send-BeatQuayTempoPointer($State,$Main,$Point,[string]$Kind) {
 [BeatQuayConsumer.Native]::TempoPointer($State.process.Id,[IntPtr]$Main.element.Current.NativeWindowHandle,$Point.x,$Point.y,$Kind)
}

function Invoke-BeatQuayTempoPointer($State,$Main,[ValidateSet('context','wheel')][string]$Kind) {
 Set-BeatQuayConsumerForeground $State $Main
 $control=Find-BeatQuayConsumerTempo $Main $State.process.Id
 Assert-BeatQuayConsumerOwner $State
 $current=Get-BeatQuayConsumerControl $control.element
 $point=Get-BeatQuayTempoPoint (Get-BeatQuayConsumerControl $Main.element) $current $State.process.Id
 Assert-BeatQuayTempoHit $control $point
 Send-BeatQuayTempoPointer $State $Main $point $Kind
 $State.workflow.inputs.Add(@{action=$State.workflow.current_action;kind=('native_tempo_'+$Kind);control=$current;x=$point.x;y=$point.y;wheel_delta=if($Kind -ceq 'wheel'){120}else{0};observed_utc=[DateTime]::UtcNow.ToString('o')})
}

function Assert-BeatQuayTempoMenu($Menu,[int]$ProcessId,[int]$Value) {
 if($Menu.snapshot.truncated -or $Menu.snapshot.title -cne 'BeatSprig' -or $Menu.snapshot.root.class_name -cne 'lmms::gui::CaptionMenu' -or
  $Menu.snapshot.root.automation_id -cne 'QApplication.lmms::gui::CaptionMenu'){throw 'Unexpected tempo context menu'}
 Assert-BeatQuayConsumerControl $Menu.snapshot.root $ProcessId 'Window' 'BeatSprig'
 $caption=@($Menu.items|Where-Object {$s=$_.snapshot;$s.available -and $s.process_id -eq $ProcessId -and $s.visible -and -not $s.enabled -and $s.type -ceq 'MenuItem' -and $s.name -ceq 'Tempo'})
 if($caption.Count -ne 1){throw 'Context menu lacks exact disabled Tempo caption'}
 $valueItem=Find-BeatQuayConsumerControl $Menu $ProcessId 'MenuItem' "Copy value ($Value)"
 foreach($item in @($caption[0],$valueItem)){
  if($item.snapshot.class_name -cne 'QAction' -or $item.snapshot.automation_id -cne 'QApplication.lmms::gui::CaptionMenu.QAction'){throw 'Unexpected tempo menu action ancestry'}
 }
}

function Wait-BeatQuayTempoMenu($State,[int]$Value) {
 $menu=Wait-BeatQuayConsumerWindow $State 'BeatSprig'
 Assert-BeatQuayTempoMenu $menu $State.process.Id $Value
 return $menu
}

function Test-BeatQuayTempoMenuDismissed($Windows) {
 if(@($Windows|Where-Object {$_.snapshot.truncated -or -not $_.snapshot.root.available}).Count){throw 'Incomplete inventory after tempo menu Escape'}
 return @($Windows|Where-Object {$_.snapshot.root.visible -and $_.snapshot.root.class_name -ceq 'lmms::gui::CaptionMenu'}).Count -eq 0
}

function Confirm-BeatQuayTempoValue($State,$Main,[int]$Value) {
 Invoke-BeatQuayTempoPointer $State $Main 'context'
 $menu=Wait-BeatQuayTempoMenu $State $Value
 Save-BeatQuayConsumerStage $State "tempo_value_$Value" $menu
 Assert-BeatQuayConsumerOwner $State
 # Read the actual source-defined menu without copying any clipboard value.
 [BeatQuayConsumer.Native]::DismissTempoMenu($State.process.Id,[IntPtr]$Main.element.Current.NativeWindowHandle,[IntPtr]$menu.element.Current.NativeWindowHandle)
 $State.workflow.inputs.Add(@{action=$State.workflow.current_action;kind='native_escape_tempo_menu';value=$Value})
 $deadline=[DateTime]::UtcNow.AddSeconds(15)
 do{
  $windows=@(Get-BeatQuayConsumerWindows $State);$State.workflow.last_observation=@($windows|ForEach-Object {$_.snapshot})
  if(Test-BeatQuayTempoMenuDismissed $windows){return}
  Start-Sleep -Milliseconds 200
 }while([DateTime]::UtcNow -lt $deadline)
 throw 'Actual tempo context menu did not dismiss'
}

function Invoke-BeatQuayConsumerTempoEdit($State) {
 $main=Wait-BeatQuayConsumerWindow $State 'BeatSprig 1.0.1'
 Confirm-BeatQuayTempoValue $State $main 112
 # LcdSpinBox::wheelEvent adds one model step per event. A fresh context-menu
 # read proves every event was consumed; there are exactly four detents, no retry.
 foreach($value in 113..116){
  Invoke-BeatQuayTempoPointer $State $main 'wheel'
  # This source path updates tempo/model journalling without setting Song's
  # modified flag. The captured native caption remains the same; the following
  # exact menu value, not a guessed title change, proves each wheel was consumed.
  $main=Wait-BeatQuayConsumerWindow $State 'BeatSprig 1.0.1'
  Confirm-BeatQuayTempoValue $State $main $value
 }
}

function Select-BeatQuayConsumerCombo($State,$Window,[string]$Label,[string]$Value) {
 $labelControl=Find-BeatQuayConsumerControl $Window $State.process.Id 'Text' $Label
 $label=$labelControl.snapshot
 $combos=@($Window.items|Where-Object {$s=$_.snapshot;$s.available -and $s.type -ceq 'ComboBox' -and $s.visible -and $s.enabled -and
   $s.process_id -eq $State.process.Id -and $s.x -ge ($label.x+$label.width-4) -and
   [Math]::Abs(($s.y+$s.height/2)-($label.y+$label.height/2)) -lt [Math]::Max($s.height,$label.height)/2})
 if($combos.Count -ne 1){throw "Missing unambiguous native combo adjacent to $Label"}
 Invoke-BeatQuayConsumerClick $State $Window $combos[0]
 # The normal Qt popup exposes its actual named list option; select that observed row.
 $option=Find-BeatQuayConsumerInput $State 'ListItem' $Value
 Invoke-BeatQuayConsumerClick $State $option.window $option.control
}

function Invoke-BeatQuayConsumerWorkflow($State) {
 Add-Type -AssemblyName UIAutomationClient
 Add-Type -AssemblyName UIAutomationTypes
 Add-Type -AssemblyName System.Drawing
 Add-Type -AssemblyName System.Windows.Forms
 Add-BeatQuayConsumerTypes
 $output=Join-Path $State.output 'consumer-workflow';New-Item -ItemType Directory -Path $output -ErrorAction Stop|Out-Null
 $State.workflow=[ordered]@{schema_version=1;source_commit=$env:GITHUB_SHA;package_full_name=$State.ownedPackageFullName;package_sha256=$State.unsignedPackageSha256;
  process_id=$State.process.Id;executable_sha256=$State.executableSha256;output=$output;acceptance=$false;current_action='preflight';primary_error=$null;
  file_verification=$null;wave_verification=$null;stages=[Collections.Generic.List[object]]::new();inputs=[Collections.Generic.List[object]]::new();
  screenshots=[Collections.Generic.List[object]]::new();last_observation=@();cli_render_used=$false;physical_audio_output_claimed=$false;marketing_branding_review_required=$true}
 try{
  Assert-BeatQuayConsumerOwner $State
  Start-BeatQuayConsumerDisplay $State
  $main=Wait-BeatQuayConsumerWindow $State 'BeatSprig 1.0.1'
  $handle=[IntPtr]$main.element.Current.NativeWindowHandle
  [BeatQuayConsumer.Native]::ShowWindow($handle,9)|Out-Null
  Set-BeatQuayConsumerForeground $State $main
  $area=[Windows.Forms.Screen]::FromHandle($handle).WorkingArea
  if($area.Width -lt 1472 -or $area.Height -lt 940 -or [BeatQuayConsumer.Native]::GetDpiForWindow($handle) -ne 96){throw 'Native display cannot contain the actual 1472 by 940 editor at its recorded 100% scale'}
  if(-not [BeatQuayConsumer.Native]::MoveWindow($handle,$area.X+[int](($area.Width-1472)/2),$area.Y+[int](($area.Height-940)/2),1472,940,$true)){throw 'Normal native window resize failed'}
  Start-Sleep -Milliseconds 400
  $work=Join-Path $State.temporary 'Evening Pulse';New-Item -ItemType Directory -Path $work -ErrorAction Stop|Out-Null
  $first=Join-Path $work 'Evening Pulse.mmp';$reopened=Join-Path $work 'Evening Pulse Reopened.mmp';$wave=Join-Path $work 'Evening Pulse.wav'
  $State.workflow.project_paths=@{first=$first;reopened=$reopened;wave=$wave}
  foreach($path in @($first,$reopened,$wave)){if(Test-Path -LiteralPath $path){throw 'A consumer output exists before its UI creation'}}
  $template=Join-Path $State.installed.InstallLocation 'data/projects/templates/BeatSprig-Drum-Grid.mpt'
  foreach($name in @('BeatSprig-Drum-Grid.mpt','BEATSPRIG-PROVENANCE.md','CC0-1.0.txt')){
   $relative='data/projects/templates/'+$name
   Assert-FileMatchesRecord (Join-Path $State.installed.InstallLocation $relative) (Get-RecordPayloadEntry $State.record $relative) 'Original starter and attribution'|Out-Null
  }
  $State.profile.projects+=@($template,'factoryprojects:templates/BeatSprig-Drum-Grid.mpt')
  $State.workflow.current_action='new_from_original_template'
  foreach($name in @('File','New from template','BeatSprig-Drum-Grid')){
   $input=Find-BeatQuayConsumerInput $State 'MenuItem' $name
   Invoke-BeatQuayConsumerClick $State $input.window $input.control
  }
  # Source implements this as a new unmodified untitled project, with no original template file selected for overwriting.
  $main=Wait-BeatQuayConsumerWindow $State 'BeatSprig 1.0.1'
  foreach($name in @('Low pulse','Backbeat','Short ticks')){$null=Find-BeatQuayConsumerControl $main $State.process.Id 'CheckBox' $name}
  Confirm-BeatQuayConsumerProfile $State
  Save-BeatQuayConsumerStage $State 'original_template_opened' $main
  $State.workflow.current_action='maximize_song_editor'
  Invoke-BeatQuayConsumerMaximizeSongEditor $State
  $State.workflow.current_action='edit_tempo_116'
  Invoke-BeatQuayConsumerTempoEdit $State
  $main=Wait-BeatQuayConsumerWindow $State 'BeatSprig 1.0.1'
  $State.workflow.current_action='save_original_project'
  Send-BeatQuayConsumerKeys $State $main @(0x11,0x53)
  $State.profile.projects+=@($first)
  Invoke-BeatQuayConsumerFileDialog $State 'Save Project' $first 'Save'
  $main=Wait-BeatQuayConsumerWindow $State 'Evening Pulse - BeatSprig 1.0.1'
  $firstHash=(Get-FileHash -LiteralPath $first -Algorithm SHA256).Hash.ToLowerInvariant()
  Confirm-BeatQuayConsumerProfile $State
  Save-BeatQuayConsumerStage $State 'project_saved' $main
  # Save a working-editor capture before creating the independently checked reopened copy.
  Save-BeatQuayConsumerScreen $State '01-evening-pulse-project' 'Evening Pulse - BeatSprig 1.0.1'
  $State.workflow.current_action='new_then_reopen_saved_project'
  Send-BeatQuayConsumerKeys $State $main @(0x11,0x4e)
  $main=Wait-BeatQuayConsumerWindow $State 'BeatSprig 1.0.1'
  Save-BeatQuayConsumerStage $State 'new_empty_project_before_reopen' $main
  Send-BeatQuayConsumerKeys $State $main @(0x11,0x4f)
  Invoke-BeatQuayConsumerFileDialog $State 'Open Project' $first 'Open'
  $main=Wait-BeatQuayConsumerWindow $State 'Evening Pulse - BeatSprig 1.0.1'
  $State.workflow.current_action='save_reopened_memory_to_new_project'
  Send-BeatQuayConsumerKeys $State $main @(0x11,0x10,0x53)
  $State.profile.projects+=@($reopened)
  Invoke-BeatQuayConsumerFileDialog $State 'Save Project' $reopened 'Save'
  $main=Wait-BeatQuayConsumerWindow $State 'Evening Pulse Reopened - BeatSprig 1.0.1'
  $State.workflow.file_verification=Invoke-BeatQuayConsumerFileCheck $State @('project','--template',$template,'--first',$first,'--reopened',$reopened,'--root',$work)
  if($State.workflow.file_verification.template_sha256 -cne (Get-RecordPayloadEntry $State.record 'data/projects/templates/BeatSprig-Drum-Grid.mpt').sha256){throw 'Independent project comparison used a changed installed starter'}
  if((Get-FileHash -LiteralPath $first -Algorithm SHA256).Hash.ToLowerInvariant() -cne $firstHash){throw 'Reopen mutated the original saved project'}
  Confirm-BeatQuayConsumerProfile $State
  Save-BeatQuayConsumerStage $State 'reopened_project_verified' $main
  $State.workflow.current_action='export_project_wav'
  Send-BeatQuayConsumerKeys $State $main @(0x11,0x45)
  Invoke-BeatQuayConsumerFileDialog $State 'Select file for project-export...' $wave 'Save'
  $dialog=Wait-BeatQuayConsumerWindow $State 'Export project'
  Select-BeatQuayConsumerCombo $State $dialog 'Sampling rate:' '44100 Hz'
  $dialog=Wait-BeatQuayConsumerWindow $State 'Export project'
  Select-BeatQuayConsumerCombo $State $dialog 'Bit depth:' '16 Bit integer'
  $dialog=Wait-BeatQuayConsumerWindow $State 'Export project'
  foreach($name in @('Export as loop (remove extra bar)','Export between loop markers')){
   $control=Find-BeatQuayConsumerControl $dialog $State.process.Id 'CheckBox' $name
   $toggle=$control.element.GetCurrentPattern([Windows.Automation.TogglePattern]::Pattern)
   if($toggle.Current.ToggleState -ne [Windows.Automation.ToggleState]::Off){throw 'Unrequested loop export setting is active'}
  }
  Save-BeatQuayConsumerStage $State 'export_settings' $dialog
  Save-BeatQuayConsumerScreen $State '02-export-project' 'Evening Pulse Reopened - BeatSprig 1.0.1' @('Export project')
  if(Test-Path -LiteralPath $wave){throw 'WAV exists before actual Start action'}
  Invoke-BeatQuayConsumerClick $State $dialog (Find-BeatQuayConsumerControl $dialog $State.process.Id 'Button' 'Start')
  $State.workflow.current_action='wait_actual_export_completion'
  $completed=Wait-BeatQuayConsumerWindow $State 'Export completed' 90
  Assert-NoReparsePath $wave
  Assert-BeatQuayConsumerExportResult $completed.snapshot $State.process.Id $wave (Get-Item -LiteralPath $wave).Length
  $State.workflow.wave_verification=Invoke-BeatQuayConsumerFileCheck $State @('wave','--path',$wave,'--root',$work)
  Save-BeatQuayConsumerStage $State 'actual_export_completed' $completed
  Save-BeatQuayConsumerScreen $State '03-export-completed' 'Evening Pulse Reopened - BeatSprig 1.0.1' @('Export project','Export completed')
  Invoke-BeatQuayConsumerClick $State $completed (Find-BeatQuayConsumerControl $completed $State.process.Id 'Button' 'Close')
  $main=Wait-BeatQuayConsumerWindow $State 'Evening Pulse Reopened - BeatSprig 1.0.1'
  $State.workflow.current_action='stop_transport_and_verify_persistence'
  Invoke-BeatQuayConsumerClick $State $main (Find-BeatQuayConsumerControl $main $State.process.Id 'Button' 'Stop (Space)')
  $main=Wait-BeatQuayConsumerWindow $State 'Evening Pulse Reopened - BeatSprig 1.0.1'
  $null=Find-BeatQuayConsumerControl $main $State.process.Id 'Button' 'Play (Space)'
  $finalFiles=Invoke-BeatQuayConsumerFileCheck $State @('project','--template',$template,'--first',$first,'--reopened',$reopened,'--root',$work)
  if(($finalFiles|ConvertTo-Json -Compress) -cne ($State.workflow.file_verification|ConvertTo-Json -Compress)){throw 'Export changed saved project bytes or semantics'}
  # Metadata artifact keeps actual small projects and original attribution; audio is independently verified then removed with owned temp.
  foreach($path in @($first,$reopened)){[IO.File]::Copy($path,(Join-Path $output ([IO.Path]::GetFileName($path))),$false)}
  Save-BeatQuayConsumerStage $State 'stopped_project_unchanged' $main
  $State.workflow.acceptance=$true
 }catch{
  $primary=$_;$State.workflow.primary_error=$primary.Exception.Message
  Confirm-BeatQuayConsumerFailureProfile $State
  throw $primary
 }
 finally{Write-NewUtf8Json (Join-Path $output 'consumer-workflow.json') $State.workflow}
}
