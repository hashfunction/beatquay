# Copyright 2026 Trieflow LLC. MIT. No registry or installation mutations in these fixtures.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$helper=Join-Path $PSScriptRoot 'runner-shell.ps1'
if(-not (Test-Path -LiteralPath $helper)){throw 'Missing required exact-runner shell preparation boundary'}
. $helper
. (Join-Path $PSScriptRoot 'qualification-bindings.ps1')
$pin=Get-BeatSprigShellPin
function Copy-Data($Value){return ($Value|ConvertTo-Json -Depth 30|ConvertFrom-Json -AsHashtable)}
function Refuses([scriptblock]$Action,[string]$Reason){$errorText=$null;try{& $Action|Out-Null}catch{$errorText=$_.Exception.Message};if(-not $errorText -or $errorText -notlike "*$Reason*"){throw "Expected refusal '$Reason', got '$errorText'"}}
$context=[ordered]@{windows=$true;os64=$true;process64=$true;ci='true';actions='true';environment='github-hosted';repository='hashfunction/beatquay';image_os='win22';image_version='20260907.297.1';system_root='C:\Windows'}
Assert-BeatSprigShellContext $context $pin
foreach($key in $context.Keys){$bad=Copy-Data $context;$bad[$key]=if($bad[$key] -is [bool]){$false}else{'foreign'};Refuses {Assert-BeatSprigShellContext $bad $pin} 'runner'}
$product=[ordered]@{hive='LocalMachine';view='Registry64';key=$pin.product.code;values=@{DisplayName=$pin.product.name;DisplayVersion=$pin.product.version;Publisher='TortoiseSVN';WindowsInstaller=1;InstallLocation='';UninstallString='MsiExec.exe /I'+$pin.product.code}}
$before=[ordered]@{products=@($product);registry=@($pin.registry);files=@($pin.files);errors=@()}
Assert-BeatSprigShellState $before $pin 'present'
foreach($name in @('DisplayName','DisplayVersion','Publisher','WindowsInstaller','InstallLocation','UninstallString')){
    $bad=Copy-Data $before;$bad.products[0].values[$name]='foreign';Refuses {Assert-BeatSprigShellState $bad $pin 'present'} 'product'
}
foreach($name in @('hive','view','key')){$bad=Copy-Data $before;$bad.products[0][$name]='foreign';Refuses {Assert-BeatSprigShellState $bad $pin 'present'} 'product'}
foreach($name in @('path','bytes','sha256')){$bad=Copy-Data $before;$bad.files[0][$name]='foreign';Refuses {Assert-BeatSprigShellState $bad $pin 'present'} 'files'}
foreach($name in @('hive','view','key','name','value','kind')){$bad=Copy-Data $before;$bad.registry[0][$name]='foreign';Refuses {Assert-BeatSprigShellState $bad $pin 'present'} 'registry'}
foreach($name in @('products','files','registry')){
    $bad=Copy-Data $before;$bad[$name]=@();Refuses {Assert-BeatSprigShellState $bad $pin 'present'} $name
    $bad=Copy-Data $before;$bad[$name]+=$bad[$name][0];Refuses {Assert-BeatSprigShellState $bad $pin 'present'} $name
}
$absent=@{products=@();registry=@();files=@();errors=@()};Assert-BeatSprigShellState $absent $pin 'absent'
foreach($name in @('products','files','registry')){$bad=Copy-Data $absent;$bad[$name]=@($before[$name][0]);Refuses {Assert-BeatSprigShellState $bad $pin 'absent'} $name}
$bad=Copy-Data $absent;$bad.errors=@('access denied');Refuses {Assert-BeatSprigShellState $bad $pin 'absent'} 'observation'

# Exercise the production sequencing policy. Only Windows reads and msiexec are
# controlled at their boundary; real context/state/mutation/exit validation runs.
$script:sequence=[Collections.Generic.List[string]]::new();$script:readIndex=0
$script:states=@($before,$before,$absent);$script:exit=0
function Read-Fixture {$script:sequence.Add('read');$value=$script:states[$script:readIndex];$script:readIndex++;return $value}
function Uninstall-Fixture {$script:sequence.Add('uninstall');return @{completed=$true;exit_code=$script:exit;process_id=123;observation_error=$null}}
$receipt=@{before=$null;rechecked=$null;uninstall=$null;after=$null;prepared=$false}
Invoke-BeatSprigShellPreparation $context $pin $receipt ${function:Read-Fixture} ${function:Uninstall-Fixture}
if(-not $receipt.prepared -or ($script:sequence -join ',') -cne 'read,read,uninstall,read'){throw 'Preparation did not preserve exact read/mutation/uninstall/absence order'}
foreach($exit in @(3010,1603,1614)){
    $script:exit=$exit;$script:readIndex=0;$script:sequence.Clear();$receipt=@{prepared=$false}
    Refuses {Invoke-BeatSprigShellPreparation $context $pin $receipt ${function:Read-Fixture} ${function:Uninstall-Fixture}} 'uninstall'
    if($receipt.prepared -or $receipt.uninstall.exit_code -ne $exit -or ($script:sequence -join ',') -cne 'read,read,uninstall'){throw 'Uninstall failure was hidden or later reads executed'}
}
$script:exit=0;$script:readIndex=0;$script:states=@($before,(Copy-Data $before),$absent);$script:states[1].products[0].values.InstallLocation='C:\Program Files\TortoiseSVN\'
$script:sequence.Clear();Refuses {Invoke-BeatSprigShellPreparation $context $pin @{} ${function:Read-Fixture} ${function:Uninstall-Fixture}} 'changed'
if('uninstall' -in $script:sequence){throw 'Mutation reached uninstall'}
$script:readIndex=0;$script:states=@($before,$before,$before);$receipt=@{}
Refuses {Invoke-BeatSprigShellPreparation $context $pin $receipt ${function:Read-Fixture} ${function:Uninstall-Fixture}} 'remain'
if($receipt.prepared -or $receipt.uninstall.exit_code -ne 0){throw 'Original success exit concealed remaining inputs'}
foreach($value in @($false,'true')){
    $script:readIndex=0;$script:states=@($before,$before,$absent);$receipt=@{}
    Refuses {Invoke-BeatSprigShellPreparation $context $pin $receipt ${function:Read-Fixture} {return @{completed=$value;exit_code=0;process_id=123;observation_error=$null}}} 'uninstall'
}
$parent=if($IsMacOS){'/private/tmp'}else{[IO.Path]::GetTempPath()}
$fixture=Join-Path $parent ('beatsprig-shell-file-'+[guid]::NewGuid().ToString('N'));$null=New-Item -ItemType Directory $fixture
try{
    $file=Join-Path $fixture 'original.dll';[IO.File]::WriteAllBytes($file,[byte[]](0,1,2,255))
    $actual=Get-BeatSprigShellFile $file
    if($actual.bytes -ne 4 -or $actual.sha256 -cne '3d1f57c984978ef98a18378c8166c1cb8ede02c03eeb6aee7e2f121dfeee3e56'){throw 'Original DLL bytes/hash differ'}
    $link=Join-Path $fixture 'alias';$null=New-Item -ItemType $(if($IsWindows){'Junction'}else{'SymbolicLink'}) -Path $link -Target $fixture
    try{Refuses {Get-BeatSprigShellFile (Join-Path $link 'absent.dll')} 'reparse'}finally{Remove-Item -LiteralPath $link -Force}
    if($null -ne (Get-BeatSprigShellFile (Join-Path $fixture 'absent.dll'))){throw 'Missing DLL returned a file'}
    # Run the real fresh-launch receipt/file verifier; only OS context and the
    # native registry/file inventory are replaced with explicitly generated data.
    $script:fixtureContext=$context;$script:fixtureState=$absent
    function Get-BeatSprigShellContext{return $script:fixtureContext}
    function Get-BeatSprigShellState($Pin){return $script:fixtureState}
    $oldBinding=@($env:GITHUB_SHA,$env:GITHUB_RUN_ID,$env:GITHUB_RUN_ATTEMPT)
    try{
        $env:GITHUB_SHA='a'*40;$env:GITHUB_RUN_ID='123456';$env:GITHUB_RUN_ATTEMPT='1'
        $path=Join-Path $fixture 'runner-shell-preparation.json'
        $generated=@{prepared=$true;error=$null;context=$context;binding=(Get-BeatQuayRunBinding $env:GITHUB_SHA $env:GITHUB_RUN_ID $env:GITHUB_RUN_ATTEMPT);
            pin_sha256=(Get-FileHash (Join-Path $PSScriptRoot '../../distribution/runner-shell-inputs.json')).Hash.ToLowerInvariant();
            before=$before;rechecked=$before;after=$absent;uninstall=@{completed=$true;exit_code=0;observation_error=$null}}
        [IO.File]::WriteAllText($path,($generated|ConvertTo-Json -Depth 30))
        foreach($mode in @('qualification','store')){
            $observed=Assert-BeatSprigShellAbsentBeforeLaunch $path $mode
            if(-not $observed.absent -or $observed.identity_mode -cne $mode -or $observed.preparation.sha256 -cne (Get-FileHash $path).Hash.ToLowerInvariant()){throw 'Original fresh-launch file binding differs'}
            $script:fixtureState=$before;Refuses {Assert-BeatSprigShellAbsentBeforeLaunch $path $mode} 'remain';$script:fixtureState=$absent
        }
        $env:GITHUB_RUN_ATTEMPT='2';Refuses {Assert-BeatSprigShellAbsentBeforeLaunch $path 'store'} 'source/run';$env:GITHUB_RUN_ATTEMPT='1'
        foreach($value in @($false,'true')){
            $generated.prepared=$value;[IO.File]::WriteAllText($path,($generated|ConvertTo-Json -Depth 30))
            Refuses {Assert-BeatSprigShellAbsentBeforeLaunch $path 'store'} 'source/run'
        }
    }finally{$env:GITHUB_SHA=$oldBinding[0];$env:GITHUB_RUN_ID=$oldBinding[1];$env:GITHUB_RUN_ATTEMPT=$oldBinding[2]}
}finally{Remove-Item -LiteralPath $fixture -Recurse -Force}
Write-Output 'PASS exact runner/product/DLL/registry/shared-client refusals, read failures, strict absence, mutation before uninstall, original exits and production sequencing.'
