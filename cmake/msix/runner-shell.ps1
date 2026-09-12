# Copyright 2026 Trieflow LLC. MIT. Only the pinned disposable GitHub image.
# TortoiseSVN is an image input, not an accepted application runtime origin.
function Get-BeatSprigShellPin {
    Get-Content -LiteralPath (Join-Path $PSScriptRoot '../../distribution/runner-shell-inputs.json') -Raw | ConvertFrom-Json -AsHashtable
}
function Get-BeatSprigShellContext {
    [ordered]@{windows=$IsWindows;os64=[Environment]::Is64BitOperatingSystem;process64=[Environment]::Is64BitProcess;
        ci=$env:CI;actions=$env:GITHUB_ACTIONS;environment=$env:RUNNER_ENVIRONMENT;repository=$env:GITHUB_REPOSITORY;
        image_os=$env:ImageOS;image_version=$env:ImageVersion;system_root=$env:SystemRoot}
}
function Assert-BeatSprigShellContext($Context,$Pin) {
    $expected=@{windows=$true;os64=$true;process64=$true;ci='true';actions='true';environment='github-hosted';
        repository=$Pin.repository;image_os=$Pin.image_os;image_version=$Pin.image_version;system_root='C:\Windows'}
    foreach($key in $expected.Keys){if($Context[$key] -isnot $expected[$key].GetType() -or $Context[$key] -cne $expected[$key]){throw "Unapproved disposable runner context: $key"}}
}
function ConvertTo-BeatSprigShellCanonical($Value) {
    # ConvertFrom-Json -AsHashtable preserves key order; sort object keys too so
    # independently read Windows registry ordering cannot affect comparison.
    if($Value -is [Collections.IDictionary]){$out=[ordered]@{};foreach($k in @($Value.Keys|Sort-Object -CaseSensitive)){$out[$k]=ConvertTo-BeatSprigShellCanonical $Value[$k]};return $out}
    if($Value -is [array]){return ,@($Value|ForEach-Object {ConvertTo-BeatSprigShellCanonical $_})}
    return $Value
}
function Get-BeatSprigShellJson($Value){ConvertTo-Json -InputObject (ConvertTo-BeatSprigShellCanonical $Value) -Depth 30 -Compress}
function Assert-BeatSprigShellState($State,$Pin,[string]$Phase) {
    if($Phase -cnotin @('present','absent')){throw 'Unknown shell preparation phase'}
    if($State.errors.Count){throw 'Shell observation failed: '+($State.errors -join '; ')}
    if($Phase -ceq 'absent'){
        foreach($key in @('products','files','registry')){if($State[$key].Count){throw "Shell $key remain after uninstall"}}
        return
    }
    if($State.products.Count -ne 1){throw 'Unknown Tortoise products'}
    $p=$State.products[0];$v=$p.values
    if($p.hive -cne 'LocalMachine' -or $p.view -cne 'Registry64' -or $p.key -cne $Pin.product.code -or
        $v.DisplayName -cne $Pin.product.name -or $v.DisplayVersion -cne $Pin.product.version -or $v.Publisher -cne 'TortoiseSVN' -or
        ($v.WindowsInstaller -isnot [int] -and $v.WindowsInstaller -isnot [long]) -or $v.WindowsInstaller -ne 1 -or
        $v.InstallLocation -cnotin @('','C:\Program Files\TortoiseSVN\') -or
        $v.UninstallString -cnotin @(('MsiExec.exe /I'+$Pin.product.code),('MsiExec.exe /X'+$Pin.product.code))) {throw 'Unknown original Tortoise product identity/path'}
    foreach($key in @('files','registry')){
        $sort=if($key -ceq 'files'){@('path')}else{@('hive','view','key','name')}
        if((Get-BeatSprigShellJson @($State[$key]|Sort-Object -Property $sort -CaseSensitive)) -cne
            (Get-BeatSprigShellJson @($Pin[$key]|Sort-Object -Property $sort -CaseSensitive))){throw "Unknown original Tortoise $key"}
    }
}
function Get-BeatSprigShellFile([string]$Path) {
    # Check every existing ancestor even when the target DLL is absent.
    $current=$Path
    while($current){
        if(Test-Path -LiteralPath $current){$item=Get-Item -LiteralPath $current -Force -ErrorAction Stop;if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Shell input has a reparse ancestor'}}
        $current=[IO.Path]::GetDirectoryName($current)
    }
    if(-not (Test-Path -LiteralPath $Path)){return $null}
    $before=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if($before.PSIsContainer){throw 'Shell DLL path is a directory'}
    $hash=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    $after=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if($before.Length -ne $after.Length -or $before.LastWriteTimeUtc -ne $after.LastWriteTimeUtc -or $before.CreationTimeUtc -ne $after.CreationTimeUtc){throw 'Shell DLL changed during hash read'}
    return @{path=$Path;bytes=$after.Length;sha256=$hash}
}
function Get-BeatSprigShellState($Pin) {
    $products=[Collections.Generic.List[object]]::new();$rows=[Collections.Generic.List[object]]::new();$files=[Collections.Generic.List[object]]::new();$errors=[Collections.Generic.List[string]]::new()
    $identifiers='Software\Microsoft\Windows\CurrentVersion\Explorer\ShellIconOverlayIdentifiers'
    $approved='Software\Microsoft\Windows\CurrentVersion\Shell Extensions\Approved'
    $classes=@($Pin.registry|Where-Object {$_.key -like 'Software\Classes\CLSID\*'}|Select-Object -ExpandProperty key -Unique)
    $guids=@($Pin.registry|Where-Object {$_.key -ceq $approved}|Select-Object -ExpandProperty name -Unique)
    foreach($hive in @('LocalMachine','CurrentUser')){foreach($view in @('Registry64','Registry32')){
        $base=$null
        try{
            $base=[Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::$hive,[Microsoft.Win32.RegistryView]::$view)
            $uninstall=$base.OpenSubKey('Software\Microsoft\Windows\CurrentVersion\Uninstall',$false)
            if($uninstall){try{foreach($key in $uninstall.GetSubKeyNames()){
                $entry=$uninstall.OpenSubKey($key,$false)
                try{
                    $name=$entry.GetValue('DisplayName','',[Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
                    if($key -ieq $Pin.product.code -or $name -match '(?i)Tortoise'){
                        $values=[ordered]@{};foreach($field in @('DisplayName','DisplayVersion','Publisher','WindowsInstaller','InstallLocation','UninstallString')){$values[$field]=$entry.GetValue($field,'',[Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)}
                        $products.Add(@{hive=$hive;view=$view;key=$key;values=$values})
                    }
                }finally{$entry.Dispose()}
            }}finally{$uninstall.Dispose()}}
            $paths=[Collections.Generic.List[string]]::new();foreach($key in $classes){$paths.Add($key)}
            foreach($root in @($identifiers,'Software\TortoiseOverlays')){
                $entry=$base.OpenSubKey($root,$false)
                if($entry){try{foreach($child in $entry.GetSubKeyNames()){
                    $key=$root+'\'+$child;$item=$base.OpenSubKey($key,$false)
                    try{
                        $id=$item.GetValue('','');$related=$root -ceq 'Software\TortoiseOverlays' -or $child -match '(?i)Tortoise' -or $id -iin $guids
                        if($root -ceq $identifiers -and $id -is [string] -and $id -match '^\{[0-9a-fA-F-]{36}\}$'){
                            $classPath='Software\Classes\CLSID\'+$id+'\InProcServer32';$server=$base.OpenSubKey($classPath,$false)
                            if($server){try{if($server.GetValue('','') -match '(?i)TortoiseOverlays'){$related=$true;if($classPath -notin $paths){$paths.Add($classPath)}}}finally{$server.Dispose()}}
                        }
                        if($related){$paths.Add($key)}
                    }finally{$item.Dispose()}
                }}finally{$entry.Dispose()}}
            }
            $paths.Add($approved)
            foreach($key in $paths){
                $entry=$base.OpenSubKey($key,$false)
                if($entry){try{
                    foreach($name in $entry.GetValueNames()){
                        $value=$entry.GetValue($name,$null,[Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
                        if($key -cne $approved -or $name -iin $guids -or $value -match '(?i)TortoiseOverlays'){
                            $rows.Add(@{hive=$hive;view=$view;key=$key;name=$name;value=$value;kind=[string]$entry.GetValueKind($name)})
                        }
                    }
                    # Empty but still registered class/provider keys must not be
                    # mistaken for absence; unexpected descendants also refuse.
                    if($key -cne $approved -and ($entry.ValueCount -eq 0 -or $entry.SubKeyCount -ne 0)){$errors.Add("Unexpected registry topology: $hive/$view/$key")}
                }finally{$entry.Dispose()}}
            }
        }catch{$errors.Add($_.Exception.Message)}finally{if($base){$base.Dispose()}}
    }}
    foreach($file in $Pin.files){try{$record=Get-BeatSprigShellFile $file.path;if($record){$files.Add($record)}}catch{$errors.Add($_.Exception.Message)}}
    return [ordered]@{products=@($products|Sort-Object hive,view,key -CaseSensitive);registry=@($rows|Sort-Object hive,view,key,name -CaseSensitive);files=@($files|Sort-Object path -CaseSensitive);errors=@($errors)}
}
function Invoke-BeatSprigShellPreparation($Context,$Pin,$Receipt,[scriptblock]$ReadState,[scriptblock]$Uninstall) {
    Assert-BeatSprigShellContext $Context $Pin
    $Receipt.prepared=$false;$Receipt.before=& $ReadState;Assert-BeatSprigShellState $Receipt.before $Pin 'present'
    $Receipt.rechecked=& $ReadState;Assert-BeatSprigShellState $Receipt.rechecked $Pin 'present'
    if((Get-BeatSprigShellJson $Receipt.before) -cne (Get-BeatSprigShellJson $Receipt.rechecked)){throw 'Original shell inputs changed before uninstall'}
    $Receipt.uninstall=& $Uninstall
    if($Receipt.uninstall.completed -isnot [bool] -or -not $Receipt.uninstall.completed -or
        ($Receipt.uninstall.exit_code -isnot [int] -and $Receipt.uninstall.exit_code -isnot [long]) -or $Receipt.uninstall.exit_code -ne 0 -or
        $Receipt.uninstall.observation_error){throw 'Original MSI uninstall did not complete with exit 0'}
    $Receipt.after=& $ReadState;Assert-BeatSprigShellState $Receipt.after $Pin 'absent';$Receipt.prepared=$true
}
function Start-BeatSprigShellPreparation([string]$OutputPath) {
    $pin=Get-BeatSprigShellPin;$context=Get-BeatSprigShellContext
    Assert-BeatSprigShellContext $context $pin
    $binding=Get-BeatQuayRunBinding $env:GITHUB_SHA $env:GITHUB_RUN_ID $env:GITHUB_RUN_ATTEMPT
    # Exclusive metadata file is reserved before the sole machine mutation.
    $stream=[IO.File]::Open($OutputPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    $receipt=[ordered]@{schema_version=1;binding=$binding;context=$context;started_utc=[DateTime]::UtcNow.ToString('o');
        pin_sha256=(Get-FileHash (Join-Path $PSScriptRoot '../../distribution/runner-shell-inputs.json')).Hash.ToLowerInvariant();
        before=$null;rechecked=$null;uninstall=$null;after=$null;prepared=$false;error=$null;completed_utc=$null}
    try{
        Invoke-BeatSprigShellPreparation $context $pin $receipt {Get-BeatSprigShellState $pin} {
            # Never execute an uninstall command obtained from the registry.
            $program='C:\Windows\System32\msiexec.exe';$native=Get-BeatSprigShellFile $program
            if(-not $native){throw 'System MSI executable absent'}
            $process=[Diagnostics.Process]::new();$process.StartInfo.FileName=$program;$process.StartInfo.UseShellExecute=$false
            foreach($argument in @('/x',$pin.product.code,'/qn','/norestart','REBOOT=ReallySuppress')){$process.StartInfo.ArgumentList.Add($argument)}
            $result=[ordered]@{program=$native;arguments=@($process.StartInfo.ArgumentList);process_id=$null;completed=$false;exit_code=$null;observation_error=$null}
            try{
                if(-not $process.Start()){throw 'MSI process did not start'}
                $result.process_id=$process.Id;$result.completed=$process.WaitForExit(120000)
                if($result.completed){$result.exit_code=$process.ExitCode}
            }catch{$result.observation_error=$_.Exception.Message}finally{$process.Dispose()}
            return $result
        }
    }catch{$receipt.error=$_.Exception.Message;throw}finally{
        $receipt.completed_utc=[DateTime]::UtcNow.ToString('o');$bytes=[Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Depth 30));$stream.Write($bytes,0,$bytes.Length);$stream.Dispose()
    }
}
function Assert-BeatSprigShellAbsentBeforeLaunch([string]$ReceiptPath,[string]$Mode) {
    $pin=Get-BeatSprigShellPin;$context=Get-BeatSprigShellContext;Assert-BeatSprigShellContext $context $pin
    $null=Get-BeatQuayPackageIdentity $Mode
    $ReceiptPath=[IO.Path]::GetFullPath($ReceiptPath)
    $original=Get-BeatSprigShellFile $ReceiptPath
    if(-not $original){throw 'Original runner shell preparation receipt absent'}
    $receipt=Get-Content -LiteralPath $ReceiptPath -Raw|ConvertFrom-Json -AsHashtable
    if($receipt.prepared -isnot [bool] -or -not $receipt.prepared -or $receipt.error -or
        $receipt.uninstall.completed -isnot [bool] -or -not $receipt.uninstall.completed -or $receipt.uninstall.observation_error -or
        ($receipt.uninstall.exit_code -isnot [int] -and $receipt.uninstall.exit_code -isnot [long]) -or $receipt.uninstall.exit_code -ne 0 -or
        $receipt.pin_sha256 -cne (Get-FileHash (Join-Path $PSScriptRoot '../../distribution/runner-shell-inputs.json')).Hash.ToLowerInvariant() -or
        (Get-BeatSprigShellJson $receipt.binding) -cne (Get-BeatSprigShellJson (Get-BeatQuayRunBinding $env:GITHUB_SHA $env:GITHUB_RUN_ID $env:GITHUB_RUN_ATTEMPT))){throw 'Runner shell receipt source/run/exit/pin differs'}
    Assert-BeatSprigShellContext $receipt.context $pin
    Assert-BeatSprigShellState $receipt.before $pin 'present';Assert-BeatSprigShellState $receipt.rechecked $pin 'present';Assert-BeatSprigShellState $receipt.after $pin 'absent'
    if((Get-BeatSprigShellJson $receipt.before) -cne (Get-BeatSprigShellJson $receipt.rechecked)){throw 'Original shell inputs changed before uninstall'}
    $observed=Get-BeatSprigShellState $pin;Assert-BeatSprigShellState $observed $pin 'absent'
    if((Get-BeatSprigShellJson $original) -cne (Get-BeatSprigShellJson (Get-BeatSprigShellFile $ReceiptPath))){throw 'Runner shell receipt changed during verification'}
    return @{identity_mode=$Mode;observed_utc=[DateTime]::UtcNow.ToString('o');preparation=$original;context=$context;absent=$true;state=$observed}
}
