# Copyright 2026 Trieflow LLC. MIT. Read-only frame observations around original pixels.
function Add-BeatSprigMarketingFrameTypes {
 if('BeatSprigMarketing.FrameNative' -as [type]){return}
 Add-Type @'
using System; using System.Runtime.InteropServices;
namespace BeatSprigMarketing {
 public static class FrameNative {
  [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left,Top,Right,Bottom; }
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd,out Rect rectangle);
 }
}
'@
}

function Assert-BeatSprigMarketingFrame($Frame,$State,[string]$Title,[string[]]$Dialogs) {
 $main=$Frame.main;$front=$Frame.foreground;$owner=$State.process.Id;$handle=$State.workflow.main_window_handle
 if($owner -le 0 -or $handle -eq 0 -or -not $main.available -or -not $front.available -or
   $main.process_id -ne $owner -or $front.process_id -ne $owner -or $Frame.main_native_pid -ne $owner -or $Frame.foreground_native_pid -ne $owner -or
   $main.native_window_handle -ne $handle -or $front.native_window_handle -ne $Frame.foreground_handle -or
   $main.type -cne 'Window' -or $front.type -cne 'Window' -or $main.class_name -cne 'lmms::gui::MainWindow' -or $main.name -cne $Title -or
   -not $main.visible -or -not $front.visible -or -not $front.enabled -or -not $Frame.native_visible -or $Frame.minimized){throw 'Native capture frame is not the exact visible owned surface'}
 if(($Frame.foreground_handle -eq $handle -and $front.name -cne $Title) -or
   ($Frame.foreground_handle -ne $handle -and $front.name -cnotin $Dialogs)){throw 'Unexpected foreground surface at capture'}
 if($Frame.dpi -ne 96 -or $Frame.display.bits -ne 32 -or $main.width -lt 1400 -or $main.height -lt 850){throw 'Capture is not the original readable native scale'}
 foreach($bounds in @($main,$Frame.desktop,$Frame.native_rect)){
  foreach($key in @('x','y','width','height')){if(-not [double]::IsFinite([double]$bounds[$key])){throw 'Nonfinite capture geometry'}}
  if($bounds.width -le 0 -or $bounds.height -le 0){throw 'Empty native capture bounds'}
 }
 foreach($bounds in @($Frame.desktop,$Frame.native_rect)){
  if($main.x -lt $bounds.x -or $main.y -lt $bounds.y -or $main.x+$main.width -gt $bounds.x+$bounds.width -or
    $main.y+$main.height -gt $bounds.y+$bounds.height){throw 'Actual capture lies outside its native window or desktop'}
 }
}

function Get-BeatSprigMarketingNativeFrame($State) {
 Add-BeatSprigMarketingFrameTypes
 $main=[IntPtr]$State.workflow.main_window_handle;$front=[BeatQuayConsumer.Native]::GetForegroundWindow()
 [uint32]$mainPid=0;[uint32]$frontPid=0
 [BeatQuayConsumer.Native]::GetWindowThreadProcessId($main,[ref]$mainPid)|Out-Null
 [BeatQuayConsumer.Native]::GetWindowThreadProcessId($front,[ref]$frontPid)|Out-Null
 # Refuse a foreign HWND before querying its accessible content.
 if($mainPid -ne $State.process.Id -or $frontPid -ne $State.process.Id){throw 'Native capture HWND belongs to a different process'}
 $mainSnapshot=Get-BeatQuayConsumerControl ([Windows.Automation.AutomationElement]::FromHandle($main))
 $frontSnapshot=Get-BeatQuayConsumerControl ([Windows.Automation.AutomationElement]::FromHandle($front))
 $rectangle=[BeatSprigMarketing.FrameNative+Rect]::new()
 if(-not [BeatSprigMarketing.FrameNative]::GetWindowRect($main,[ref]$rectangle)){throw 'Native capture frame is unavailable'}
 $desktop=[Windows.Forms.SystemInformation]::VirtualScreen
 return @{main=$mainSnapshot;foreground=$frontSnapshot;main_native_pid=$mainPid;foreground_native_pid=$frontPid;foreground_handle=$front.ToInt64();
  native_visible=[BeatSprigMarketing.FrameNative]::IsWindowVisible($main);minimized=[BeatSprigMarketing.FrameNative]::IsIconic($main);
  native_rect=@{x=$rectangle.Left;y=$rectangle.Top;width=$rectangle.Right-$rectangle.Left;height=$rectangle.Bottom-$rectangle.Top};
  desktop=@{x=$desktop.X;y=$desktop.Y;width=$desktop.Width;height=$desktop.Height};
  display=(Convert-BeatQuayConsumerMode (Get-BeatQuayConsumerDisplayState $State.displayDevice).current);dpi=[BeatQuayConsumer.Native]::GetDpiForWindow($main)}
}

function Read-BeatSprigMarketingFrame($State,[string]$EditorTitle,[string[]]$AllowedDialogs) {
 Assert-BeatQuayConsumerOwner $State
 $frame=Get-BeatSprigMarketingNativeFrame $State
 $title=Resolve-BeatQuayConsumerWindowTitle $State $EditorTitle
 Assert-BeatSprigMarketingFrame $frame $State $title $AllowedDialogs
 Assert-BeatQuayConsumerOwner $State
 # Use the unchanged original helper's integer Drawing.Rectangle conversion;
 # retain the original UIA doubles alongside it, without altering any pixels.
 return @{observed_utc=[DateTime]::UtcNow.ToString('o');main_pid=$frame.main_native_pid;main_handle=[int64]$State.workflow.main_window_handle;
  foreground_pid=$frame.foreground_native_pid;foreground_handle=[int64]$frame.foreground_handle;
  title=$title;dpi=$frame.dpi;x=[int]$frame.main.x;y=[int]$frame.main.y;width=[int]$frame.main.width;height=[int]$frame.main.height;
  display=$frame.display;original_observation=$frame}
}
