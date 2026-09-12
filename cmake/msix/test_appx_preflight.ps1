# Real preflight, core orchestration, and failure evidence with a controlled Appx importer.
# Copyright 2026 Trieflow LLC. MIT.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
$script:ActualCore=${function:Invoke-BeatQuayQualificationCore}
$script:ActualFileMatch=${function:Assert-FileMatchesRecord}
$temporaryBase=if ($IsMacOS) { '/private/tmp' } else { [IO.Path]::GetTempPath() }
$script:root=Join-Path $temporaryBase ('beatquay-appx-test-'+[guid]::NewGuid().ToString('N'))
$script:events=[Collections.Generic.List[string]]::new()
$script:scenario=''
$previousProfile=$env:USERPROFILE
$previousSha=$env:GITHUB_SHA
$previousRun=$env:GITHUB_RUN_ID
$previousAttempt=$env:GITHUB_RUN_ATTEMPT
$env:USERPROFILE=Join-Path $script:root 'profile'
$env:GITHUB_SHA='a'*40
$env:GITHUB_RUN_ID='123456'
$env:GITHUB_RUN_ATTEMPT='2'
$Python=Join-Path $script:root 'python'

# The host OS, original runner probe and external Python verifier are controlled. The
# production preflight still checks the record, exact identity, files and hashes.
function Assert-BeatQuayWindowsCi {}
function Assert-FileMatchesRecord([string]$Path,$Expected,[string]$Label){
    if($Label -ceq 'Original runner shell preparation'){
        if([IO.Path]::GetFileName($Path) -cne 'runner-shell-preparation.json'){throw 'Wrong original runner receipt route'}
        $Path=Join-Path $script:root 'runner-shell-preparation.json'
    }
    return & $script:ActualFileMatch $Path $Expected $Label
}
function Assert-BeatSprigShellAbsentBeforeLaunch([string]$Path,[string]$Mode){
    if([IO.Path]::GetFileName($Path) -cne 'runner-shell-preparation.json' -or $Mode -cne $script:identityMode){throw 'Wrong runner absence route'}
    $script:events.Add('runner-probe')
    if($script:scenario -ceq 'runner-present'){throw 'Original runner overlay still present'}
    return @{absent=$true;identity_mode=$Mode}
}
function Invoke-CheckedNative([string]$Program,[string[]]$Arguments) {
    if ($Program -cne $Python -or [IO.Path]::GetFileName($Arguments[0]) -cne 'verify_record.py') { throw 'Unexpected native tool before Appx initialization' }
    $modeIndex=[Array]::IndexOf($Arguments,'--identity-mode')
    if($modeIndex -lt 0 -or $Arguments[$modeIndex+1] -cne $script:identityMode){throw 'Independent verifier did not receive the selected fixed mode'}
    $script:events.Add('verify-record')
}
function Import-Module {
    [CmdletBinding()] param([string]$Name,[switch]$UseWindowsPowerShell,[Alias('Global')][switch]$ImportGlobally)
    $script:events.Add('import')
    if ($Name -cne 'Appx' -or -not $UseWindowsPowerShell) { throw 'Appx must use the Windows PowerShell compatibility host' }
    if ($script:scenario -eq 'import-failed') {
        # Even an importer that writes a nonterminating error must stop preflight.
        $action=if ($PSBoundParameters.ContainsKey('ErrorAction')) { $PSBoundParameters.ErrorAction } else { 'Continue' }
        Write-Error 'Appx compatibility import failed' -ErrorAction $action
        return
    }
    # Import a real module at the requested scope. Other production closures
    # must see its exports after the preflight closure and this importer return.
    & $script:preflightModule {
        param($ModulePath,$ImportGlobally)
        Microsoft.PowerShell.Core\Import-Module -Name $ModulePath -Global:$ImportGlobally -ErrorAction Stop
    } (Join-Path $script:root 'FixtureAppx.psm1') $ImportGlobally
}
function Invoke-BeatQuayQualificationCore([Collections.IDictionary]$Operations) {
    $script:preflightModule=$Operations.Preflight.Module
    $preparationEvents=$script:events
    $preparationName=(Get-BeatQuayPackageIdentity $script:identityMode).packageName
    $Operations.PrepareSignedCopy={
        $preparationEvents.Add('prepare')
        # This is a different dynamic module from Preflight; it must still see
        # the imported package query when signing/install/cleanup begin.
        if (@(Get-AppxPackage -Name $preparationName -ErrorAction Stop).Count) { throw 'Unexpected fixture registration' }
        throw 'Reached preparation after compatible Appx preflight'
    }.GetNewClosure()
    # Leave real Install, activation and every ownership-aware cleanup intact.
    return & $script:ActualCore $Operations
}

try {
    [IO.Directory]::CreateDirectory((Join-Path $script:root '10.0.26100.0/x64')) | Out-Null
    $package=Join-Path $script:root 'original.msix'
    $makeappx=Join-Path $script:root '10.0.26100.0/x64/makeappx.exe'
    $signtool=Join-Path $script:root '10.0.26100.0/x64/signtool.exe'
    $shell=Join-Path $script:root 'runner-shell-preparation.json'
    foreach ($file in @($package,$makeappx,$signtool,$shell)) { [IO.File]::WriteAllText($file,'fixture bytes') }
    $hash=(Get-FileHash $package -Algorithm SHA256).Hash.ToLowerInvariant()
    $record=[ordered]@{
        sourceCommit=$env:GITHUB_SHA;workflowRunId=$env:GITHUB_RUN_ID;workflowRunAttempt=$env:GITHUB_RUN_ATTEMPT
        schemaVersion=1;qualificationIdentityOnly=$true;storeIdentityStaged=$false;identityMode='qualification';signed=$false;publicRelease=$false
        licenseClearanceClaimed=$false;correspondingSourceComplete=$false;installationQualificationPassed=$false
        identity=[ordered]@{packageName='Trieflow.BeatQuay.Qualification';publisher='CN=BeatQuay-CI-Qualification';version='1.0.1.0';architecture='x64';applicationId='BeatQuay';executable='beatsprig.exe';deviceFamily='Windows.Desktop';minVersion='10.0.19041.0';maxVersionTested='10.0.26100.0';capability='runFullTrust'}
        containerVerification=@{package=@{sha256=$hash}}
        makeAppx=@{path=$makeappx;bytes=(Get-Item $makeappx).Length;sha256=$hash;sdkVersion='10.0.26100.0'}
        sourceInputs=[ordered]@{}
        evidenceInputs=@{'runner-shell-preparation.json'=@{bytes=(Get-Item $shell).Length;sha256=$hash}}
    }
    foreach($name in Get-BeatQuayQualificationHelperPaths){
        $path=Join-Path $PSScriptRoot "../../$name"
        $record.sourceInputs[$name]=@{bytes=(Get-Item -LiteralPath $path).Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
    }
    $recordPath=Join-Path $script:root 'record.json'
    @'
function Get-AppxPackage {
    [CmdletBinding()]param([string]$Name)
    if ($Name -cne $global:BeatSprigFixturePackageName) { throw 'Unscoped compatibility package query' }
    return @()
}
function Add-AppxPackage { throw 'Appx mutation reached before successful preflight and signing' }
function Remove-AppxPackage { throw 'Unowned Appx cleanup reached' }
Export-ModuleMember -Function Get-AppxPackage,Add-AppxPackage,Remove-AppxPackage
'@ | Set-Content (Join-Path $script:root 'FixtureAppx.psm1') -Encoding utf8

    foreach($script:identityMode in @('qualification','store')) {
      # The real module has its own scope; expose only the fixture's expected mode.
      $global:BeatSprigFixturePackageName=(Get-BeatQuayPackageIdentity $script:identityMode).packageName
      $record.identityMode=$script:identityMode
      $record.qualificationIdentityOnly=$script:identityMode -ceq 'qualification'
      $record.storeIdentityStaged=$script:identityMode -ceq 'store'
      $record.identity=Get-BeatQuayPackageIdentity $script:identityMode
      $record | ConvertTo-Json -Depth 10 | Set-Content $recordPath -Encoding utf8
      foreach ($script:scenario in @('runner-present','import-failed','import-succeeded')) {
        $script:events.Clear()
        $output=Join-Path $script:root ($script:identityMode+'-'+$script:scenario)
        $failure=$null
        try { Invoke-BeatQuayInstallQualification $package $recordPath $signtool $output -Mode $script:identityMode | Out-Null }
        catch { $failure=$_.Exception.Message }
        $evidence=Get-Content (Join-Path $output 'installation-qualification.json') -Raw | ConvertFrom-Json
        $expected=if($script:scenario -ceq 'runner-present'){'Original runner overlay still present'}elseif ($script:scenario -eq 'import-failed') { 'Appx compatibility import failed' } else { 'Reached preparation after compatible Appx preflight' }
        $expectedEvents=if($script:scenario -ceq 'runner-present'){'verify-record,runner-probe'}elseif ($script:scenario -eq 'import-failed') { 'verify-record,runner-probe,import' } else { 'verify-record,runner-probe,import,prepare' }
        if ($evidence.primary_error -cne $expected -or $failure -notlike "*$expected*") { throw "Wrong preflight outcome: $failure" }
        if (($script:events -join ',') -cne $expectedEvents) { throw "Import/preparation ordering changed: $($script:events -join ',')" }
        if ($evidence.installation_qualification_passed -or $evidence.add_appx_completed -or $evidence.registration_ownership_established -or $evidence.process_identity_ownership_established -or $evidence.signed_copy_sha256) { throw 'Preflight fixture falsely claimed signing, installation, activation or acceptance' }
        if (-not $evidence.unsigned_package_unchanged -or $evidence.cleanup_errors.Count -or $evidence.evidence_errors.Count) { throw 'Initialization failure lost package integrity or safe cleanup evidence' }
        if($evidence.identity_mode -cne $script:identityMode -or $evidence.workflow_run_id -cne $env:GITHUB_RUN_ID -or $evidence.workflow_run_attempt -cne $env:GITHUB_RUN_ATTEMPT -or
           @($evidence.helper_bindings.PSObject.Properties).Count -ne 12 -or $evidence.installed_identity_verified -or $evidence.store_identity_used){throw 'Staged identity or helper metadata claimed installation or lost current run binding'}
        Write-Output "PASS real recorded Appx preflight: $script:identityMode / $script:scenario"
      }
    }
} finally {
    $env:USERPROFILE=$previousProfile
    $env:GITHUB_SHA=$previousSha
    $env:GITHUB_RUN_ID=$previousRun
    $env:GITHUB_RUN_ATTEMPT=$previousAttempt
    Remove-Variable BeatSprigFixturePackageName -Scope Global -ErrorAction SilentlyContinue
    Remove-Module FixtureAppx -ErrorAction SilentlyContinue
    if (Test-Path $script:root) { Remove-Item $script:root -Recurse -Force }
}
