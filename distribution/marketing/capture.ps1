# Copyright 2026 Trieflow LLC. MIT.
# Capture-only orchestration adapted from the qualified BeatSprig installer.
# Reticle-derived installation ownership notice: cmake/msix/RETICLEQUAY-MIT.txt.
# Its exact helper functions and native input workflow remain unchanged.
[CmdletBinding()]
param([string]$Inputs,[string]$QualifiedSource,[string]$Output,[string]$Python,[string]$ShellReceipt,[switch]$LibraryOnly)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$script:captureScriptRoot=$PSScriptRoot

function Invoke-BeatSprigMarketingCapture {
    $state = [ordered]@{
        package = $null; record = $null; output = $null; temporary = $null; signedCopy = $null
        publicCertificate = $null; certificate = $null; trustedCertificate = $null; trustAttempted = $false
        installed = $null; installedByUs = $false; process = $null; processOwned = $false; cleanupProcessExit = $null
        installAttempted = $false; brokerProcessId = 0; addCompleted = $false; ownedPackageFullName = $null; preflightPackageFullNames = @(); residualPackageFullNames = @(); processHandle = $null; processExit = $null
        unsignedPackageSha256 = $null; signedPackageSha256 = $null; signTool = $null
        aumid = $null; processPackageFullName = $null; modules = @(); window = $null; moduleRejection=$null
        python = $Python; firstRun = $null; firstRunObservations = [ordered]@{}; workingDirectory = $null
        executableSha256 = $null; workflow = $null; profile = $null; activationStartedUtc = $null
        displayOriginalMode=$null; displayDevice=$null; displayRestoreRequired=$false; displayEvidence=$null
        cleanClose = $false; uninstallVerified = $false
        identityMode='store';runBinding=$null;helperBindings=$null;installedIdentityVerified=$false
        runnerShell=[ordered]@{preflight=$null;before_activation=$null}
        qualifiedSource=$QualifiedSource;inputs=$Inputs;originalScreen=$null;captureFrames=[Collections.Generic.List[object]]::new()
        signingTemporary=$null;demoRecord=$null;demoSeal=$null;signingRecord=$null;signingSeal=$null;ownedFilesCleaned=$false
        startedAtUtc=[DateTime]::UtcNow.ToString('o')
    }
    $expectedIdentity = Get-BeatQuayPackageIdentity 'store'

    $operations = [ordered]@{}
    $operations.Preflight = {
        Assert-BeatQuayWindowsCi
        if($env:GITHUB_EVENT_NAME -cne 'workflow_dispatch' -or $env:GITHUB_REPOSITORY -cne 'hashfunction/beatquay'){throw 'Manual BeatSprig capture dispatch required'}
        if(-not [IO.Path]::IsPathFullyQualified($state.python)){throw 'Absolute capture Python required'}
        Invoke-CheckedNative $state.python @((Join-Path $captureScriptRoot 'verify_prepared.py'),'--inputs',$Inputs,'--qualified-source',$QualifiedSource)
        $prepared=Get-Content -LiteralPath (Join-Path $Inputs 'capture-inputs.json') -Raw|ConvertFrom-Json -DateKind String
        $state.package=$prepared.package_path
        $state.record=Get-Content -LiteralPath $prepared.package_record_path -Raw|ConvertFrom-Json -DateKind String
        $state.runBinding=Get-BeatQuayRunBinding $env:GITHUB_SHA $env:GITHUB_RUN_ID $env:GITHUB_RUN_ATTEMPT
        Assert-BeatQuayIdentityRecord $state.record 'store' $prepared.qualified.source_commit $prepared.qualified.workflow_run_id $prepared.qualified.workflow_run_attempt
        $state.helperBindings=Get-BeatQuayQualificationHelperBindings $QualifiedSource $state.record.sourceInputs
        $state.unsignedPackageSha256=Assert-FileMatchesRecord $state.package $prepared.qualified.package 'Original unsigned Store package'
        $state.signTool=$state.record.makeAppx.path -replace 'makeappx.exe$','signtool.exe'
        $export=Get-Content -LiteralPath (Join-Path $Inputs 'store/BeatSprig_1.0.1.0_x64.export.json') -Raw|ConvertFrom-Json -DateKind String
        Assert-FileMatchesRecord $state.signTool $export.originalSdkTools.store.signTool 'Original SDK SignTool'|Out-Null
        $state.signTool=[ordered]@{path=$state.signTool;bytes=$export.originalSdkTools.store.signTool.bytes;sha256=$export.originalSdkTools.store.signTool.sha256;sdk_version='10.0.26100.0'}
        if(Test-Path -LiteralPath $Output){throw 'Capture output exists; preserving it'}
        New-Item -ItemType Directory -Path $Output -ErrorAction Stop|Out-Null
        $state.output=[IO.Path]::GetFullPath($Output)
        $profilePath=Join-Path $env:USERPROFILE '.beatquayrc.xml'
        if(Test-Path -LiteralPath $profilePath){throw 'Preexisting BeatSprig compatibility profile; preserving it'}
        $state.profile=[ordered]@{path=$profilePath;source_commit=$env:GITHUB_SHA;absent_before_activation=$false;ownership_established=$false;
            process_id=0;package_full_name=$null;sha256=$null;creation_utc=$null;initial_path=$null;projects=@();
            observations=[Collections.Generic.List[object]]::new();cleanup_verified=$false}
        $state.workingDirectory=New-BeatQuayWorkingDirectoryRecord (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'BeatQuay') $env:GITHUB_SHA
        Import-Module -Name Appx -UseWindowsPowerShell -Global -ErrorAction Stop
        $existing=@(Get-AppxPackage -Name $expectedIdentity.packageName -ErrorAction Stop)
        $state.preflightPackageFullNames=@($existing|ForEach-Object {[string]$_.PackageFullName})
        if($existing.Count){throw 'Existing same-name Store registration; no replacement or removal authorized'}
        if(Test-Path -LiteralPath 'C:\BeatSprig Demo'){throw 'Friendly demo directory already exists; preserving it'}
        $state.runnerShell.preflight=Assert-BeatSprigShellAbsentBeforeLaunch $ShellReceipt 'store'
        $state.demoRecord=Join-Path $state.output 'owned-demo.json'
        Invoke-CheckedNative $state.python @((Join-Path $captureScriptRoot 'owned_files.py'),'create','--root','C:\BeatSprig Demo','--kind','demo','--record',$state.demoRecord)
        $state.temporary='C:\BeatSprig Demo'
        $state.originalScreen=New-BeatSprigOriginalScreen $state $originalScreen
    }.GetNewClosure()

    $operations.PrepareSignedCopy = {
        $runnerTemp = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [IO.Path]::GetTempPath() }
        $temporaryCandidate = Join-Path $runnerTemp ('.beatsprig-marketing-sign-' + [guid]::NewGuid().ToString('N'))
        $state.signingRecord=Join-Path $state.output 'owned-signing.json'
        Invoke-CheckedNative $state.python @((Join-Path $captureScriptRoot 'owned_files.py'),'create','--root',$temporaryCandidate,'--kind','signing','--record',$state.signingRecord)
        $state.signingTemporary=$temporaryCandidate
        $state.signedCopy = Join-Path $state.signingTemporary 'BeatSprig.Marketing.signed.msix'
        [IO.File]::Copy($state.package, $state.signedCopy, $false)
        $state.publicCertificate = Join-Path $state.signingTemporary 'BeatSprig.Marketing.public.cer'
        $state.certificate = New-SelfSignedCertificate -Type Custom -KeyUsage DigitalSignature -KeyExportPolicy NonExportable -KeySpec Signature `
            -CertStoreLocation 'Cert:\CurrentUser\My' -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3','2.5.29.19={text}') `
            -Subject $expectedIdentity.publisher -FriendlyName 'BeatSprig ephemeral marketing capture' -NotAfter (Get-Date).AddHours(12)
        Export-Certificate -Cert $state.certificate -FilePath $state.publicCertificate -Force | Out-Null
        $state.trustAttempted = $true
        $state.trustedCertificate = Import-Certificate -FilePath $state.publicCertificate -CertStoreLocation 'Cert:\LocalMachine\TrustedPeople'
        foreach ($arguments in @(
            @('sign','/fd','SHA256','/sha1',$state.certificate.Thumbprint,'/s','My',$state.signedCopy),
            @('verify','/pa','/all','/v',$state.signedCopy)
        )) {
            if ((Get-Item -LiteralPath $state.signTool.path).Length -ne $state.signTool.bytes -or
                (Get-FileHash -LiteralPath $state.signTool.path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $state.signTool.sha256) {
                throw 'SignTool changed after qualification preflight.'
            }
            Invoke-CheckedNative $state.signTool.path $arguments
        }
        if ((Get-Item -LiteralPath $state.signTool.path).Length -ne $state.signTool.bytes -or
            (Get-FileHash -LiteralPath $state.signTool.path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $state.signTool.sha256) {
            throw 'SignTool changed during qualification signing.'
        }
        $signature = Get-AuthenticodeSignature -LiteralPath $state.signedCopy
        if ($signature.Status -ne [Management.Automation.SignatureStatus]::Valid -or $signature.SignerCertificate.Thumbprint -ne $state.certificate.Thumbprint) {
            throw "Test-copy signature is not valid for the ephemeral certificate: $($signature.Status)"
        }
        if ((Get-FileHash -LiteralPath $state.package -Algorithm SHA256).Hash.ToLowerInvariant() -ne $state.unsignedPackageSha256) { throw 'Unsigned source package changed during signing.' }
        $state.signedPackageSha256 = (Get-FileHash -LiteralPath $state.signedCopy -Algorithm SHA256).Hash.ToLowerInvariant()
        $state.signingSeal=Join-Path $state.output 'owned-signing-seal.json'
        Invoke-CheckedNative $state.python @((Join-Path $captureScriptRoot 'owned_files.py'),'seal','--record',$state.signingRecord,'--seal',$state.signingSeal)
    }.GetNewClosure()

    $operations.Install = {
        $state.installAttempted = $true
        Add-AppxPackage -Path $state.signedCopy -ErrorAction Stop
        $state.addCompleted = $true
        $matches = @(Get-AppxPackage -Name $expectedIdentity.packageName -ErrorAction Stop)
        if ($matches.Count -ne 1) { throw 'Expected exactly one installed qualification package.' }
        $candidate = $matches[0]
        Assert-BeatQuayRegistrationIdentity $candidate $state.identityMode
        # Ownership is established only after our Add succeeds and one exact
        # expected registration is observed. A failed/partial Add cannot confer it.
        $state.installed = $candidate
        $state.ownedPackageFullName = [string]$candidate.PackageFullName
        $state.installedByUs = $true
        $state.aumid = [string]$state.installed.PackageFamilyName + '!' + $expectedIdentity.applicationId
        foreach ($entry in $state.record.payload.PSObject.Properties) {
            $relative = $entry.Name
            $expected = Get-RecordPayloadEntry $state.record $relative
            $hash = Assert-FileMatchesRecord (Join-Path $state.installed.InstallLocation ($relative -replace '/', [IO.Path]::DirectorySeparatorChar)) $expected $relative
            if ($relative -eq 'beatsprig.exe') { $state.executableSha256 = $hash }

        }
    }.GetNewClosure()

    $operations.ActivateAndVerify = {
        Invoke-CheckedNative $state.python @((Join-Path $captureScriptRoot 'verify_prepared.py'),'--inputs',$Inputs,'--qualified-source',$QualifiedSource,'--installed-root',$state.installed.InstallLocation)
        $state.installedIdentityVerified=$true
        $state.runnerShell.before_activation=Assert-BeatSprigShellAbsentBeforeLaunch $ShellReceipt 'store'
        Add-BeatQuayActivationTypes
        if(Test-Path -LiteralPath $state.profile.path){throw 'Profile appeared before owned activation; preserving it'}
        $state.profile.absent_before_activation=$true
        $state.activationStartedUtc=[DateTime]::UtcNow
        $processId = [BeatQuayQualification.ActivationBroker]::Activate($state.aumid)
        $state.brokerProcessId = [int]$processId
        $state.process = [Diagnostics.Process]::GetProcessById([int]$processId)
        $state.processHandle = $state.process.SafeHandle
        if ($state.processHandle.IsInvalid -or $state.processHandle.IsClosed) { throw 'Cannot retain the live broker-activated process handle.' }
        $expectedExecutable = Get-CanonicalPath (Join-Path $state.installed.InstallLocation 'beatsprig.exe')
        if ((Get-CanonicalPath $state.process.MainModule.FileName) -ine $expectedExecutable) { throw 'Broker returned an executable outside the owned installed path.' }
        $state.processPackageFullName = [BeatQuayQualification.NativePackageProbe]::GetFullName($state.process.Handle)
        if ($state.processPackageFullName -cne $state.ownedPackageFullName) { throw 'Broker process does not have the exact owned package identity.' }
        Assert-FileMatchesRecord $expectedExecutable (Get-RecordPayloadEntry $state.record 'beatsprig.exe') 'Activated executable' | Out-Null
        $state.processOwned = $true
        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        do {
            Start-Sleep -Milliseconds 250
            $state.process.Refresh()
            if ($state.process.HasExited) { throw "Activated BeatQuay exited during startup: $($state.process.ExitCode)" }
        } until ($state.process.MainWindowHandle -ne 0 -or [DateTime]::UtcNow -ge $deadline)
        if ($state.process.MainWindowHandle -eq 0) { throw 'Activated BeatQuay did not create a main window.' }
        $state.firstRun = Complete-BeatQuayFirstRun $state.process $state.workingDirectory $state.ownedPackageFullName $state.firstRunObservations
        Confirm-BeatQuayConsumerProfile $state -Initial
        $state.processPackageFullName = [BeatQuayQualification.NativePackageProbe]::GetFullName($state.process.Handle)
        if ($state.processPackageFullName -cne [string]$state.installed.PackageFullName) { throw 'Activated process does not own the exact installed package full name.' }
        Start-Sleep -Seconds 3
        $state.process.Refresh()
        if ($state.process.HasExited -or $state.process.MainWindowHandle -eq 0 -or $state.process.MainWindowTitle -cne 'BeatSprig 1.0.1') { throw 'Activated BeatQuay did not survive the stable-window interval.' }
        $state.modules = @(Get-BeatQuayVerifiedModules $state)
        Write-NewUtf8Json (Join-Path $state.output 'loaded-modules.json') $state.modules
        $state.window = Get-WindowQualification $state.process $state.output
        $state.process.Refresh()
        if ($state.process.HasExited -or $state.process.MainWindowHandle -eq 0) { throw 'Activated BeatQuay did not survive the stable-window interval.' }
    }.GetNewClosure()

    $operations.ConsumerWorkflow = {
        $null=Get-BeatQuayQualificationHelperBindings $QualifiedSource $state.record.sourceInputs
        Invoke-BeatQuayConsumerWorkflow $state
        if(-not $state.workflow -or -not $state.workflow.acceptance){throw 'Actual installed musical project/export workflow did not pass'}
        $state.modules=@(Get-BeatQuayVerifiedModules $state)
        # Original runtime checks now also cover the actual instrument loaded by the UI-created project.
        $synth=@($state.modules|Where-Object {$_.origin -ceq 'package' -and $_.name -ieq 'kicker.dll'})
        if($synth.Count -ne 1){throw 'Actual UI project did not load exactly one verified packaged Kicker synth'}
        Write-NewUtf8Json (Join-Path $state.output 'loaded-modules-after-workflow.json') $state.modules
        $null=Get-BeatQuayQualificationHelperBindings $QualifiedSource $state.record.sourceInputs
    }.GetNewClosure()

    $operations.CloseCleanly = {
        if (-not $state.process.CloseMainWindow()) { throw 'Activated BeatQuay refused a normal main-window close request.' }
        $state.processExit = Get-BeatQuayProcessExitEvidence $state.process 15000
        if (-not $state.processExit.normal_exit) { throw ('Activated BeatQuay normal-close observation failed: ' + ($state.processExit | ConvertTo-Json -Compress)) }
        $state.cleanClose = $true
        Confirm-BeatQuayConsumerProfile $state -AfterClose
        $state.demoSeal=Join-Path $state.output 'owned-demo-seal.json'
        Invoke-CheckedNative $state.python @((Join-Path $captureScriptRoot 'owned_files.py'),'seal','--record',$state.demoRecord,'--seal',$state.demoSeal)
    }.GetNewClosure()

    $operations.UninstallAndVerify = {
        if (-not $state.installedByUs -or -not $state.ownedPackageFullName) { throw 'Exact installed package ownership was not established.' }
        Remove-AppxPackage -Package $state.ownedPackageFullName -ErrorAction Stop
        if (@(Get-AppxPackage -Name $expectedIdentity.packageName -ErrorAction Stop).Count -ne 0) { throw 'Package registration remains after uninstall.' }
        $state.uninstallVerified = $true
    }.GetNewClosure()

    $operations.StopOwnedProcess = {
        # Retain and use the original attached Process/OS handle, never reacquire
        # a potentially recycled PID during cleanup.
        try {
            if ($state.processOwned -and $state.process -and $state.processHandle) {
                if (-not $state.process.HasExited) { $state.process.Kill() }
                $state.cleanupProcessExit = Get-BeatQuayProcessExitEvidence $state.process 10000
                if (-not $state.cleanupProcessExit.wait_completed -or $state.cleanupProcessExit.observation_error) { throw ('Owned process cleanup failed: ' + ($state.cleanupProcessExit | ConvertTo-Json -Compress)) }
            }
        } finally {
            if ($state.process) { $state.process.Dispose() }
        }
    }.GetNewClosure()

    $operations.RemoveOwnedPackage = {
        if ($state.installAttempted) {
            $remaining = @(Get-AppxPackage -Name $expectedIdentity.packageName -ErrorAction Stop)
            $state.residualPackageFullNames = @($remaining | ForEach-Object { [string]$_.PackageFullName })
            if ($state.installedByUs -and $state.ownedPackageFullName) {
                $owned = @($remaining | Where-Object { [string]$_.PackageFullName -ceq $state.ownedPackageFullName })
                if ($owned.Count -gt 1) { throw 'Ambiguous duplicate registration state; all registrations preserved.' }
                if ($owned.Count -eq 1) { Remove-AppxPackage -Package $state.ownedPackageFullName -ErrorAction Stop }
            }
            # A matching registration after a failed Add may belong to another
            # invocation. Report residue without removing identity-tuple matches.
            $remaining = @(Get-AppxPackage -Name $expectedIdentity.packageName -ErrorAction Stop)
            $state.residualPackageFullNames = @($remaining | ForEach-Object { [string]$_.PackageFullName })
            if ($remaining.Count) { throw ('Unowned or unresolved package registrations preserved: ' + ($state.residualPackageFullNames -join ', ')) }
            if ($state.addCompleted -and -not $state.installedByUs) {
                throw 'Registration cleanup remains uncertain: Add completed but exact ownership was never observed; registrations were preserved.'
            }
        }
    }.GetNewClosure()

    $operations.RemoveTrustedCertificate = {
        if ($state.trustAttempted -and $state.certificate) {
            $path = 'Cert:\LocalMachine\TrustedPeople\' + $state.certificate.Thumbprint
            if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force -ErrorAction Stop }
            if (Test-Path -LiteralPath $path) { throw 'Trusted public certificate remains after cleanup.' }
        }
    }.GetNewClosure()

    $operations.RemovePersonalCertificate = {
        if ($state.certificate) {
            $path = 'Cert:\CurrentUser\My\' + $state.certificate.Thumbprint
            if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -DeleteKey -Force -ErrorAction Stop }
            if (Test-Path -LiteralPath $path) { throw 'Ephemeral personal certificate remains after cleanup.' }
        }
    }.GetNewClosure()

    $operations.RemoveOwnedProfile = {
        $terminated=$state.cleanupProcessExit -and $state.cleanupProcessExit.wait_completed -and -not $state.cleanupProcessExit.observation_error
        Remove-BeatQuayOwnedProfile $state.profile ([bool]$terminated)
    }.GetNewClosure()

    $operations.RestoreDisplay = { Restore-BeatQuayConsumerDisplay $state }.GetNewClosure()

    $operations.RemoveOwnedWorkingDirectory = {
        if ($state.workingDirectory -and $state.workingDirectory.ownership_established -and
            (-not $state.cleanupProcessExit -or -not $state.cleanupProcessExit.wait_completed -or $state.cleanupProcessExit.observation_error)) {
            throw 'Owned process termination is unproven; preserving its working directory.'
        }
        Remove-BeatQuayOwnedWorkingDirectory $state.workingDirectory
    }.GetNewClosure()

    $operations.RemoveTemporaryFiles = {
        $stopped= -not $state.process -or ($state.processOwned -and $state.cleanupProcessExit -and $state.cleanupProcessExit.wait_completed -and -not $state.cleanupProcessExit.observation_error)
        if(-not $stopped){throw 'Retained process termination unproven; preserving owned capture trees'}
        foreach($kind in @('demo','signing')){
            $record=$state[$kind+'Record'];$seal=$state[$kind+'Seal']
            if($record -and (Test-Path -LiteralPath $record)){
                if(-not $seal -or -not (Test-Path -LiteralPath $seal)){
                    # Failure cleanup accepts only the marker-only tree. Unsealed
                    # product/signing outputs remain for explicit diagnosis.
                    $seal=Join-Path $state.output ('owned-'+$kind+'-failure-seal.json')
                    Invoke-CheckedNative $state.python @((Join-Path $captureScriptRoot 'owned_files.py'),'seal-empty','--record',$record,'--seal',$seal)
                }
                Invoke-CheckedNative $state.python @((Join-Path $captureScriptRoot 'owned_files.py'),'cleanup','--record',$record,'--seal',$seal,'--stopped')
            }
        }
        $state.ownedFilesCleaned=$true
    }.GetNewClosure()

    $result=Invoke-BeatQuayQualificationCore -Operations $operations
    if(-not $state.output){throw $result.primary_error}
    $unsignedUnchanged=$false
    $evidenceErrors=[Collections.Generic.List[string]]::new()
    try {$unsignedUnchanged=(Assert-FileMatchesRecord $state.package $state.record.containerVerification.package 'Final original unsigned package') -ceq $state.unsignedPackageSha256}
    catch {$evidenceErrors.Add($_.Exception.Message)}
    $passed=$result.installation_qualification_passed -and $unsignedUnchanged -and $state.cleanClose -and $state.uninstallVerified -and
        $state.ownedFilesCleaned -and $state.profile.cleanup_verified -and $state.workflow -and $state.workflow.acceptance -and $state.captureFrames.Count -eq 3 -and $evidenceErrors.Count -eq 0
    $evidence=[ordered]@{
        schema_version=1;capture_started_at_utc=$state.startedAtUtc;purpose='marketing screenshots only';consumer_acceptance=$false;installation_qualification_claimed=$false
        capture_passed=[bool]$passed;capture_source_commit=$env:GITHUB_SHA;capture_run_id=$env:GITHUB_RUN_ID;capture_run_attempt=$env:GITHUB_RUN_ATTEMPT
        qualified_source_commit=$state.record.sourceCommit;unsigned_package_sha256=$state.unsignedPackageSha256;unsigned_package_unchanged=$unsignedUnchanged
        signed_copy_sha256=$state.signedPackageSha256;certificate_private_key_exported=$false;identity_mode='store';identity=$expectedIdentity
        owned_package_full_name=$state.ownedPackageFullName;activated_process_package_full_name=$state.processPackageFullName
        registration_ownership_established=$state.installedByUs;process_identity_ownership_established=$state.processOwned
        residual_package_full_names=@($state.residualPackageFullNames);helper_bindings=$state.helperBindings;runner_shell=$state.runnerShell
        original_consumer_observation=$state.workflow;frames=@($state.captureFrames);loaded_modules=$state.modules;loaded_module_rejection=$state.moduleRejection
        process_exit=$state.processExit;cleanup_process_exit=$state.cleanupProcessExit;clean_close_verified=$state.cleanClose;uninstall_verified=$state.uninstallVerified
        owned_profile=$state.profile;working_directory=$state.workingDirectory;native_display=$state.displayEvidence;owned_files_cleaned=$state.ownedFilesCleaned
        primary_error=$result.primary_error;cleanup_errors=@($result.cleanup_errors);evidence_errors=@($evidenceErrors)
        completed_operations=@($result.completed_operations);completed_cleanup=@($result.completed_cleanup);generated_at_utc=[DateTime]::UtcNow.ToString('o')
    }
    Write-NewUtf8Json (Join-Path $state.output 'capture-result.json') $evidence
    if(-not $passed){throw ('Capture failed. Primary: '+$result.primary_error+'; cleanup: '+($result.cleanup_errors -join '; '))}
    Invoke-CheckedNative $state.python @((Join-Path $captureScriptRoot 'finish_capture.py'),'--inputs',$Inputs,'--qualified-source',$QualifiedSource,'--capture',$state.output)
}

if(-not $LibraryOnly){
    # Refuse unbound or changed source/package inputs before dot-sourcing any
    # qualified helper, creating demo state, signing or touching registration.
    & $Python (Join-Path $PSScriptRoot 'verify_prepared.py') --inputs $Inputs --qualified-source $QualifiedSource
    if($LASTEXITCODE -ne 0){throw 'Reviewed capture inputs did not verify'}
    . (Join-Path $QualifiedSource 'cmake/msix/qualify-msix-install.ps1') -LibraryOnly -Python $Python -Output $Output
    . (Join-Path $PSScriptRoot 'capture_frame.ps1')
    . (Join-Path $PSScriptRoot 'capture_observer.ps1')
    $script:originalScreen=(Get-Command Save-BeatQuayConsumerScreen).ScriptBlock
    function Save-BeatQuayConsumerScreen($State,[string]$Name,[string]$EditorTitle,[string[]]$AllowedDialogs=@()){
        Invoke-BeatSprigOriginalScreen $State $Name $EditorTitle $AllowedDialogs
    }
    Invoke-BeatSprigMarketingCapture
}
