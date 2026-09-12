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
 $record=@{path=$file;absent_before_activation=$true;ownership_established=$true;process_id=123;package_full_name='owned-package';sha256=(Get-FileHash $file -Algorithm SHA256).Hash.ToLowerInvariant();cleanup_verified=$false}
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
}finally{$process.Dispose();Remove-Item $work -Recurse -Force}
Add-BeatQuayConsumerTypes
Check ($null -ne ('BeatQuayConsumer.Native' -as [type])) 'Native observed-input helper failed compilation.'
Write-Output 'PASS: actual production control/ownership/completion/profile boundaries; native UI execution remains pending Windows.'
