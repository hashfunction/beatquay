# Copyright 2026 Trieflow LLC. MIT. Fixed package contracts and observed source bindings.
function Get-BeatQuayPackageIdentity([string]$Mode) {
    if($Mode -cnotin @('qualification','store')){throw 'Only the fixed qualification and store modes are supported.'}
    $identity=[ordered]@{packageName='Trieflow.BeatQuay.Qualification';publisher='CN=BeatQuay-CI-Qualification';version='1.0.1.0';
        architecture='x64';applicationId='BeatQuay';executable='beatsprig.exe';deviceFamily='Windows.Desktop';
        minVersion='10.0.19041.0';maxVersionTested='10.0.26100.0';capability='runFullTrust'}
    if($Mode -ceq 'store'){
        $identity.packageName='1659hashfunction.BeatQuay'
        $identity.publisher='CN=B6A2631A-FD32-45CC-AE12-82466975F528'
    }
    return $identity
}

function Get-BeatQuayRunBinding([string]$SourceCommit,[string]$RunId,[string]$RunAttempt) {
    if($SourceCommit -cnotmatch '^[0-9a-f]{40}$' -or $RunId -cnotmatch '^[1-9][0-9]*$' -or $RunAttempt -cnotmatch '^[1-9][0-9]*$'){
        throw 'Exact source commit, workflow run and attempt are required.'
    }
    return [ordered]@{source_commit=$SourceCommit;workflow_run_id=$RunId;workflow_run_attempt=$RunAttempt}
}

function Assert-BeatQuayIdentityRecord($Record,[string]$Mode,[string]$SourceCommit,[string]$RunId,[string]$RunAttempt) {
    $expected=Get-BeatQuayPackageIdentity $Mode
    $null=Get-BeatQuayRunBinding $SourceCommit $RunId $RunAttempt
    if($Record.schemaVersion -ne 1 -or $Record.sourceCommit -cne $SourceCommit -or $Record.identityMode -cne $Mode -or
        $Record.workflowRunId -isnot [string] -or $Record.workflowRunId -cne $RunId -or
        $Record.workflowRunAttempt -isnot [string] -or $Record.workflowRunAttempt -cne $RunAttempt){throw 'Package source/run/attempt or fixed mode differs.'}
    $flags=@{qualificationIdentityOnly=($Mode -ceq 'qualification');storeIdentityStaged=($Mode -ceq 'store');
        signed=$false;publicRelease=$false;licenseClearanceClaimed=$false;correspondingSourceComplete=$false;installationQualificationPassed=$false}
    foreach($name in $flags.Keys){
        if($Record.$name -isnot [bool] -or $Record.$name -ne $flags[$name]){throw "Package is not the expected unsigned staged identity: $name"}
    }
    if(@($Record.identity.PSObject.Properties).Count -ne $expected.Count){throw 'Unexpected package identity fields.'}
    foreach($field in $expected.Keys){if($Record.identity.$field -isnot [string] -or $Record.identity.$field -cne $expected[$field]){throw "Qualification identity mismatch: $field"}}
}

function Assert-BeatQuayRegistrationIdentity($Candidate,[string]$Mode) {
    $expected=Get-BeatQuayPackageIdentity $Mode
    if([string]$Candidate.Name -cne $expected.packageName -or [string]$Candidate.Publisher -cne $expected.publisher -or
        [string]$Candidate.Version -cne $expected.version -or [string]$Candidate.Architecture -cne 'X64' -or
        -not ([string]$Candidate.PackageFullName).StartsWith($expected.packageName+'_'+$expected.version+'_x64_',[StringComparison]::Ordinal) -or
        -not [string]$Candidate.PackageFamilyName){throw 'Installed publisher/version/architecture differs from the fixed identity.'}
    if($Mode -ceq 'store' -and ([string]$Candidate.PackageFamilyName -cne '1659hashfunction.BeatQuay_r3hxytd7jt6c4' -or
        [string]$Candidate.PackageFullName -cne '1659hashfunction.BeatQuay_1.0.1.0_x64__r3hxytd7jt6c4')){throw 'Installed Store family/full name differs from the assigned identity.'}
}

function Invoke-BeatQuayIdentityLifecycles([scriptblock]$Action) {
    foreach($mode in @('qualification','store')) { & $Action $mode | Out-Host }
}

function Get-BeatQuayQualificationHelperPaths {
    @('cmake/msix/qualify-msix-install.ps1','cmake/msix/consumer-workflow.ps1','cmake/msix/consumer-display.ps1',
        'cmake/msix/first-run.ps1','cmake/msix/consumer_files.py','tests/scripted/starter_render.py',
        'cmake/msix/verify_record.py','cmake/msix/msix_qualification.py','cmake/msix/qualification-bindings.ps1',
        'cmake/msix/ms_runtime_origins.py','cmake/msix/runner-shell.ps1','distribution/runner-shell-inputs.json')
}

function Get-BeatQuayQualificationHelperBindings([string]$SourceRoot,$SourceInputs) {
    $result=[ordered]@{}
    foreach($name in Get-BeatQuayQualificationHelperPaths){
        $expected=$SourceInputs.PSObject.Properties[$name]
        if(-not $expected){throw "Qualification helper is absent from source-bound package inputs: $name"}
        $hash=Assert-FileMatchesRecord (Join-Path $SourceRoot $name) $expected.Value $name
        $result[$name]=@{bytes=[int64]$expected.Value.bytes;sha256=$hash}
    }
    return $result
}
