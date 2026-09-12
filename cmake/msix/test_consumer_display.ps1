$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'consumer-display.ps1')
function Check($Condition,[string]$Message){if(-not $Condition){throw $Message}}
Add-BeatQuayConsumerDisplayTypes
Check ([Runtime.InteropServices.Marshal]::SizeOf([BeatQuayConsumerDisplay.Mode]::new()) -eq 220 -and
    [Runtime.InteropServices.Marshal]::OffsetOf([BeatQuayConsumerDisplay.Mode],'dmPelsWidth').ToInt32() -eq 172 -and
    [Runtime.InteropServices.Marshal]::SizeOf([BeatQuayConsumerDisplay.DisplayDevice]::new()) -eq 840) 'Native Unicode display structure layout differs.'
foreach($flag in @(1,0x100,0x200,0x10000000)){
    $failed=$false;try{$null=[BeatQuayConsumerDisplay.DisplayModes]::Change('not-a-device',[BeatQuayConsumerDisplay.Mode]::new(),$flag)}catch{$failed=$_.Exception.Message -match 'Only native test and dynamic change'}
    Check $failed 'Persistent, unsafe or other unapproved native change flags reached the OS.'
}
function Mode($Width,$Height,$Bits=32){[pscustomobject]@{dmPelsWidth=$Width;dmPelsHeight=$Height;dmBitsPerPel=$Bits;dmDisplayFrequency=60;dmDisplayOrientation=0;dmDisplayFlags=0;dmDriverExtra=0}}
$original=Mode 1024 768;$desired=Mode 1920 1080
Check ((Get-BeatQuayConsumerModeChoice @((Mode 1280 720),$desired,(Mode 2560 1440))).dmPelsWidth -eq 1920) 'A supported 1080p mode was not selected.'
foreach($modes in @(@((Mode 1024 768)),@((Mode 1920 1080 16)),@((Mode 4000 3000)))){
    $failed=$false;try{$null=Get-BeatQuayConsumerModeChoice $modes}catch{$failed=$true};Check $failed 'Absent/unsafe/oversized supported mode was accepted.'
}
$script:current=$original;$script:calls=[Collections.Generic.List[int]]::new();$script:rejectTest=$false;$script:partialApplyFailure=$false
function Get-BeatQuayConsumerDisplayState([string]$Device){@{device='fixture-primary';current=$script:current;modes=@($original,$desired)}}
function Set-BeatQuayConsumerDisplayMode([string]$Device,$Mode,[int]$Flags){$script:calls.Add($Flags);if($Flags -eq 2){if($script:rejectTest){return -2};return 0};$script:current=$Mode;if($script:partialApplyFailure -and $Mode.dmPelsWidth -eq 1920){return -1};return 0}
$state=@{displayOriginalMode=$null;displayDevice=$null;displayRestoreRequired=$false;displayEvidence=$null}
Start-BeatQuayConsumerDisplay $state
Check ($script:current.dmPelsWidth -eq 1920 -and $script:calls.Count -eq 2 -and $script:calls[0] -eq 2 -and $script:calls[1] -eq 0) 'Production display change skipped native test or used persistent/unsafe flags.'
Restore-BeatQuayConsumerDisplay $state
Check ($script:current.dmPelsWidth -eq 1024 -and $state.displayEvidence.restore_verified -eq $true) 'Production restore did not restore the retained original mode.'
$script:calls.Clear();$script:rejectTest=$true
$state=@{displayOriginalMode=$null;displayDevice=$null;displayRestoreRequired=$false;displayEvidence=$null}
$failed=$false;try{Start-BeatQuayConsumerDisplay $state}catch{$failed=$true}
Check ($failed -and $script:calls.Count -eq 1 -and $script:current.dmPelsWidth -eq 1024 -and -not $state.displayRestoreRequired) 'Failed CDS_TEST changed the actual mode.'
$script:calls.Clear();$script:rejectTest=$false;$script:partialApplyFailure=$true
$state=@{displayOriginalMode=$null;displayDevice=$null;displayRestoreRequired=$false;displayEvidence=$null}
$failed=$false;try{Start-BeatQuayConsumerDisplay $state}catch{$failed=$true}
Check ($failed -and $state.displayRestoreRequired -and $script:current.dmPelsWidth -eq 1920) 'Partial native apply failure lost required restoration state.'
Restore-BeatQuayConsumerDisplay $state
Check ($script:current.dmPelsWidth -eq 1024 -and $state.displayEvidence.restore_verified -eq $true -and $script:calls[2] -eq 0) 'Partial apply failure did not restore the retained original mode dynamically.'
Write-Output 'PASS: native structure/flag boundary, enumerated safe selection, test-before-apply, flags 0, original-mode restoration, failed-test preservation and partial-apply recovery.'
