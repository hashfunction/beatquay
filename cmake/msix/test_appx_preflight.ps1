# Real preflight, core orchestration, and failure evidence with a controlled Appx importer.
# Copyright 2026 Trieflow LLC. MIT.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
$script:ActualCore=${function:Invoke-BeatQuayQualificationCore}
$temporaryBase=if ($IsMacOS) { '/private/tmp' } else { [IO.Path]::GetTempPath() }
$script:root=Join-Path $temporaryBase ('beatquay-appx-test-'+[guid]::NewGuid().ToString('N'))
$script:events=[Collections.Generic.List[string]]::new()
$script:scenario=''
$previousProfile=$env:USERPROFILE
$previousSha=$env:GITHUB_SHA
$env:USERPROFILE=Join-Path $script:root 'profile'
$env:GITHUB_SHA='a'*40
$Python=Join-Path $script:root 'python'

# Only the host OS gate and the external Python verifier are substituted. The
# production preflight still checks the record, exact identity, files and hashes.
function Assert-BeatQuayWindowsCi {}
function Invoke-CheckedNative([string]$Program,[string[]]$Arguments) {
    if ($Program -cne $Python -or [IO.Path]::GetFileName($Arguments[0]) -cne 'verify_record.py') { throw 'Unexpected native tool before Appx initialization' }
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
    $Operations.PrepareSignedCopy={
        $preparationEvents.Add('prepare')
        # This is a different dynamic module from Preflight; it must still see
        # the imported package query when signing/install/cleanup begin.
        if (@(Get-AppxPackage -Name 'Trieflow.BeatQuay.Qualification' -ErrorAction Stop).Count) { throw 'Unexpected fixture registration' }
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
    foreach ($file in @($package,$makeappx,$signtool)) { [IO.File]::WriteAllText($file,'fixture bytes') }
    $hash=(Get-FileHash $package -Algorithm SHA256).Hash.ToLowerInvariant()
    $record=[ordered]@{
        sourceCommit=$env:GITHUB_SHA;schemaVersion=1;qualificationIdentityOnly=$true;signed=$false;publicRelease=$false
        licenseClearanceClaimed=$false;installationQualificationPassed=$false
        identity=[ordered]@{packageName='Trieflow.BeatQuay.Qualification';publisher='CN=BeatQuay-CI-Qualification';version='1.0.0.0';architecture='x64';applicationId='BeatQuay';executable='lmms.exe';deviceFamily='Windows.Desktop';minVersion='10.0.19041.0';maxVersionTested='10.0.26100.0';capability='runFullTrust'}
        containerVerification=@{package=@{sha256=$hash}}
        makeAppx=@{path=$makeappx;bytes=(Get-Item $makeappx).Length;sha256=$hash;sdkVersion='10.0.26100.0'}
    }
    $recordPath=Join-Path $script:root 'record.json'
    $record | ConvertTo-Json -Depth 10 | Set-Content $recordPath -Encoding utf8
    @'
function Get-AppxPackage {
    [CmdletBinding()]param([string]$Name)
    if ($Name -cne 'Trieflow.BeatQuay.Qualification') { throw 'Unscoped compatibility package query' }
    return @()
}
function Add-AppxPackage { throw 'Appx mutation reached before successful preflight and signing' }
function Remove-AppxPackage { throw 'Unowned Appx cleanup reached' }
Export-ModuleMember -Function Get-AppxPackage,Add-AppxPackage,Remove-AppxPackage
'@ | Set-Content (Join-Path $script:root 'FixtureAppx.psm1') -Encoding utf8

    foreach ($script:scenario in @('import-failed','import-succeeded')) {
        $script:events.Clear()
        $output=Join-Path $script:root $script:scenario
        $failure=$null
        try { Invoke-BeatQuayInstallQualification $package $recordPath $signtool $output | Out-Null }
        catch { $failure=$_.Exception.Message }
        $evidence=Get-Content (Join-Path $output 'installation-qualification.json') -Raw | ConvertFrom-Json
        $expected=if ($script:scenario -eq 'import-failed') { 'Appx compatibility import failed' } else { 'Reached preparation after compatible Appx preflight' }
        $expectedEvents=if ($script:scenario -eq 'import-failed') { 'verify-record,import' } else { 'verify-record,import,prepare' }
        if ($evidence.primary_error -cne $expected -or $failure -notlike "*$expected*") { throw "Wrong preflight outcome: $failure" }
        if (($script:events -join ',') -cne $expectedEvents) { throw "Import/preparation ordering changed: $($script:events -join ',')" }
        if ($evidence.installation_qualification_passed -or $evidence.add_appx_completed -or $evidence.registration_ownership_established -or $evidence.process_identity_ownership_established -or $evidence.signed_copy_sha256) { throw 'Preflight fixture falsely claimed signing, installation, activation or acceptance' }
        if (-not $evidence.unsigned_package_unchanged -or $evidence.cleanup_errors.Count -or $evidence.evidence_errors.Count) { throw 'Initialization failure lost package integrity or safe cleanup evidence' }
        Write-Output "PASS real recorded Appx preflight: $script:scenario"
    }
} finally {
    $env:USERPROFILE=$previousProfile
    $env:GITHUB_SHA=$previousSha
    Remove-Module FixtureAppx -ErrorAction SilentlyContinue
    if (Test-Path $script:root) { Remove-Item $script:root -Recurse -Force }
}
