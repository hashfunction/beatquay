# Copyright 2026 Trieflow LLC. MIT. Real fixed-mode and file-binding boundaries.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
$store=Get-BeatQuayPackageIdentity 'store'
if($store.packageName -cne '1659hashfunction.BeatQuay' -or $store.publisher -cne 'CN=B6A2631A-FD32-45CC-AE12-82466975F528' -or $store.applicationId -cne 'BeatQuay' -or $store.version -cne '1.0.1.0'){throw 'Fixed Store contract differs'}
function Must-Refuse([scriptblock]$Action){$refused=$false;try{& $Action|Out-Null}catch{$refused=$true};if(-not $refused){throw 'Unsafe identity/binding was accepted'}}
foreach($mode in @('Store','','foreign')){Must-Refuse {Get-BeatQuayPackageIdentity $mode}}
$identityRun='123456';$identityAttempt='2';$identityCommit='a'*40
foreach($mode in @('qualification','store')){
    $record=[pscustomobject]@{schemaVersion=1;sourceCommit=$identityCommit;workflowRunId=$identityRun;workflowRunAttempt=$identityAttempt;
        identityMode=$mode;qualificationIdentityOnly=($mode -ceq 'qualification');storeIdentityStaged=($mode -ceq 'store');
        signed=$false;publicRelease=$false;licenseClearanceClaimed=$false;correspondingSourceComplete=$false;installationQualificationPassed=$false;
        identity=[pscustomobject](Get-BeatQuayPackageIdentity $mode)}
    Assert-BeatQuayIdentityRecord $record $mode $identityCommit $identityRun $identityAttempt
    Must-Refuse {Assert-BeatQuayIdentityRecord $record $(if($mode -ceq 'store'){'qualification'}else{'store'}) $identityCommit $identityRun $identityAttempt}
    Must-Refuse {Assert-BeatQuayIdentityRecord $record $mode $identityCommit $identityRun '1'}
    foreach($key in @('signed','publicRelease','installationQualificationPassed')){$record.$key=$true;Must-Refuse {Assert-BeatQuayIdentityRecord $record $mode $identityCommit $identityRun $identityAttempt};$record.$key=$false}
    $record.storeIdentityStaged='true';Must-Refuse {Assert-BeatQuayIdentityRecord $record $mode $identityCommit $identityRun $identityAttempt}
}
$candidate=[pscustomobject]@{Name=$store.packageName;Publisher=$store.publisher;Version=$store.version;Architecture='X64';
    PackageFamilyName='1659hashfunction.BeatQuay_r3hxytd7jt6c4';PackageFullName='1659hashfunction.BeatQuay_1.0.1.0_x64__r3hxytd7jt6c4'}
Assert-BeatQuayRegistrationIdentity $candidate 'store'
foreach($key in @('Name','Publisher','Version','Architecture','PackageFamilyName','PackageFullName')){
    $saved=$candidate.$key;$candidate.$key='foreign';Must-Refuse {Assert-BeatQuayRegistrationIdentity $candidate 'store'};$candidate.$key=$saved
}
$script:identityCalls=[Collections.Generic.List[string]]::new()
Invoke-BeatQuayIdentityLifecycles {param($mode)$script:identityCalls.Add($mode)}
if(($script:identityCalls -join ',') -cne 'qualification,store'){throw 'Both complete lifecycles must be dispatched in order'}
$script:identityCalls.Clear()
Must-Refuse {Invoke-BeatQuayIdentityLifecycles {param($mode)$script:identityCalls.Add($mode);throw 'First lifecycle failed'}}
if(($script:identityCalls -join ',') -cne 'qualification'){throw 'Store lifecycle began after failed first cleanup'}
$parent=if($IsMacOS){'/private/tmp'}else{[IO.Path]::GetTempPath()}
$fixture=Join-Path $parent ('beatsprig-helper-binding-'+[guid]::NewGuid().ToString('N'));New-Item -ItemType Directory $fixture|Out-Null
try{
    $expected=[ordered]@{}
    foreach($name in Get-BeatQuayQualificationHelperPaths){
        $path=Join-Path $fixture $name;New-Item -ItemType Directory (Split-Path -Parent $path) -Force|Out-Null
        [IO.File]::WriteAllText($path,'owned helper fixture '+$name)
        $expected[$name]=@{bytes=(Get-Item $path).Length;sha256=(Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant()}
    }
    $inputs=$expected|ConvertTo-Json -Depth 4|ConvertFrom-Json
    $bound=Get-BeatQuayQualificationHelperBindings $fixture $inputs
    if($bound.Count -ne 10){throw 'Incomplete actual helper binding'}
    foreach($name in $expected.Keys){
        $path=Join-Path $fixture $name;$original=[IO.File]::ReadAllBytes($path);[IO.File]::WriteAllText($path,'changed')
        Must-Refuse {Get-BeatQuayQualificationHelperBindings $fixture $inputs}
        [IO.File]::WriteAllBytes($path,$original)
    }
    $inputs.PSObject.Properties.Remove('cmake/msix/consumer_files.py')
    Must-Refuse {Get-BeatQuayQualificationHelperBindings $fixture $inputs}
}finally{Remove-Item -LiteralPath $fixture -Recurse -Force}
Write-Output 'PASS fixed identities, cross-mode/run/typed-state refusals, exact Store registration, two lifecycle order/failure, and all 10 real helper file bindings.'

# Execute the real ActivateAndVerify closure up to the native broker boundary.
# The external installed verifier is controlled; no installation/UI is simulated
# as accepted, and the real outer receipt writer still records the failure.
function Invoke-CheckedNative([string]$Program,[string[]]$Arguments) {
    if($Program -cne 'fixture-python' -or [IO.Path]::GetFileName($Arguments[0]) -cne 'verify_record.py' -or
       $Arguments[[Array]::IndexOf($Arguments,'--identity-mode')+1] -cne $script:receiptMode -or
       $Arguments[[Array]::IndexOf($Arguments,'--installed-root')+1] -cne 'owned-installed-root'){throw 'Wrong installed verification route'}
    if(-not $script:verifierReturns){throw 'Independent installed verifier refused'}
}
function Add-BeatQuayActivationTypes {throw 'Stopped before native broker'}
function Invoke-BeatQuayQualificationCore([Collections.IDictionary]$Operations) {
    $state=$Operations.Preflight.Module.SessionState.PSVariable.GetValue('state')
    $state.output=$script:receiptDirectory;$state.package=Join-Path $state.output 'original.msix'
    [IO.File]::WriteAllText($state.package,'original unsigned fixture')
    $state.unsignedPackageSha256=(Get-FileHash $state.package -Algorithm SHA256).Hash.ToLowerInvariant()
    $state.python='fixture-python';$state.installed=[pscustomobject]@{InstallLocation='owned-installed-root';PackageFullName='fixture'}
    $primary=$null
    try{& $Operations.ActivateAndVerify|Out-Null}catch{$primary=$_.Exception.Message}
    return [pscustomobject]@{installation_qualification_passed=$false;primary_error=$primary;cleanup_errors=@()}
}
foreach($script:receiptMode in @('qualification','store')){
    foreach($script:verifierReturns in @($false,$true)){
        $script:receiptDirectory=Join-Path $parent ('beatsprig-installed-flag-'+[guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory $script:receiptDirectory|Out-Null
        try{
            Must-Refuse {Invoke-BeatQuayInstallQualification unused unused unused $script:receiptDirectory -Mode $script:receiptMode}
            $receipt=Get-Content (Join-Path $script:receiptDirectory 'installation-qualification.json') -Raw|ConvertFrom-Json
            $expectedError=if($script:verifierReturns){'Stopped before native broker'}else{'Independent installed verifier refused'}
            if($receipt.primary_error -cne $expectedError -or $receipt.installed_identity_verified -ne $script:verifierReturns -or
               $receipt.store_identity_used -ne ($script:verifierReturns -and $script:receiptMode -ceq 'store') -or
               $receipt.installation_qualification_passed -or $receipt.process_identity_ownership_established){throw 'Installed verification timing falsely claimed broker/UI acceptance'}
        }finally{Remove-Item -LiteralPath $script:receiptDirectory -Recurse -Force}
    }
}
Write-Output 'PASS four actual installed-verification receipt boundaries: before verifier return, after return, both fixed modes, never broker/UI acceptance.'
