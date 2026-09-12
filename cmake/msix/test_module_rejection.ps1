# Real module-origin rejection with a controlled process-module enumerator.
# Copyright 2026 Trieflow LLC. MIT.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
$parent=if($IsMacOS){'/private/tmp'}else{[IO.Path]::GetTempPath()}
$root=Join-Path $parent ('beatsprig-module-rejection-'+[guid]::NewGuid().ToString('N'))
$previousSystemRoot=$env:SystemRoot
New-Item -ItemType Directory $root|Out-Null
try{
    $env:SystemRoot=Join-Path $root 'windows'
    $path=Join-Path $root 'unknown-module.dll';[IO.File]::WriteAllText($path,'owned original module fixture')
    foreach($scenario in @('write','collision','hash-read-error')){
        $output=Join-Path $root $scenario;New-Item -ItemType Directory $output|Out-Null
        $state=[ordered]@{installed=[pscustomobject]@{InstallLocation=(Join-Path $root 'package')};record=[pscustomobject]@{runtime=[pscustomobject]@{}};
            process=[pscustomobject]@{Id=$PID;Modules=@([pscustomobject]@{FileName=$path;ModuleName='unknown-module.dll'})};
            processPackageFullName='exact-observed-package';ownedPackageFullName='exact-owned-package';output=$output;moduleRejection=$null;
            workflow=[ordered]@{acceptance=$true;current_action='stop_transport_and_verify_persistence'}}
        $receipt=Join-Path $output 'loaded-module-rejection.json'
        if($scenario -ceq 'collision'){[IO.File]::WriteAllText($receipt,'preserve original evidence')}
        # Hash failure is injected only after the real path/origin predicate has
        # rejected the module, so the primary error must remain that rejection.
        if($scenario -ceq 'hash-read-error'){
            function Get-FileHash {throw 'controlled metadata hash read failed'}
        }
        $caught=$null
        try{Get-BeatQuayVerifiedModules $state|Out-Null}catch{$caught=$_}
        if($scenario -ceq 'hash-read-error'){Remove-Item Function:\Get-FileHash}
        if(-not $caught -or $caught.Exception.Message -cne 'Defender module is outside its platform root.'){throw 'Original module-origin rejection was replaced or accepted'}
        $observation=$state.moduleRejection
        if(-not $observation -or $observation.process_id -ne $PID -or $observation.module_name -cne 'unknown-module.dll' -or
           $observation.module_path -cne $path -or $observation.activated_process_package_full_name -cne 'exact-observed-package' -or
           $observation.owned_package_full_name -cne 'exact-owned-package' -or $observation.reason -cne $caught.Exception.Message -or
           $observation.current_action -cne 'stop_transport_and_verify_persistence' -or -not $observation.consumer_workflow_completed_before_rejection -or
           $observation.origin_accepted -or $observation.installation_qualification_passed){throw 'Missing original module context or false acceptance'}
        if($observation.install_root -cne (Join-Path $root 'package') -or $observation.windows_root -cne $env:SystemRoot -or
           $observation.defender_root -cne (Join-Path ([Environment]::GetFolderPath('CommonApplicationData')) 'Microsoft/Windows Defender/Platform')){throw 'Exact attempted origin roots were lost'}
        if($scenario -ceq 'collision'){
            if([IO.File]::ReadAllText($receipt) -cne 'preserve original evidence' -or -not $observation.evidence_error){throw 'Existing evidence was replaced or write refusal hidden'}
        }else{
            $saved=Get-Content $receipt -Raw|ConvertFrom-Json
            if($saved.reason -cne $caught.Exception.Message -or $saved.module_path -cne $path){throw 'Original rejection receipt was not retained'}
        }
        if($scenario -ceq 'hash-read-error'){
            if($null -ne $observation.sha256 -or $observation.observation_errors.Count -ne 1){throw 'Unobserved module bytes were invented'}
        }else{
            if($observation.sha256 -cne (Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant() -or
               $observation.bytes -ne (Get-Item $path).Length -or $observation.observation_errors.Count){throw 'Recorded original module hash/length differs'}
        }
        Write-Output "PASS original module refusal, bounded metadata and preservation: $scenario"
    }
}finally{$env:SystemRoot=$previousSystemRoot;Remove-Item -LiteralPath $root -Recurse -Force}
