# Real first-run orchestration and filesystem ownership; only Windows UIA IO is substituted.
# Copyright 2026 Trieflow LLC. MIT.
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
$script:process=[Diagnostics.Process]::GetCurrentProcess()
$script:root=Join-Path ([IO.Path]::GetTempPath()) ('beatquay-first-run-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($script:root) | Out-Null
function Get-BeatQuayFirstRunWindows($Process) {
    $script:reads++
    $title=if ($script:stage -eq 0) {'Working directory'} else {'BeatQuay - Settings'}
    $action=if ($script:stage -eq 0) {'Yes'} else {'OK'}
    $message=Get-BeatQuayWorkingDirectoryMessage $script:workspace.path
    $row=[ordered]@{title=$title;process_id=$Process.Id;visible=$true;enabled=$true;width=500;height=350;class_name='QDialog';controls=@(
        [ordered]@{name=$message;control_type='Text';process_id=$Process.Id;visible=$true;enabled=$true},
        [ordered]@{name=$action;control_type='Button';process_id=$Process.Id;visible=$true;enabled=$true})}
    if ($script:stage -eq 0) {
        switch ($script:scenario) {
            wrong-title {$row.title='Other application'}
            wrong-content {$row.controls[0].name='Create an unrelated directory?'}
            wrong-process {$row.process_id++}
            foreign-action {$row.controls[1].process_id++}
            wrong-action {$row.controls[1].name='No'}
            disabled-action {$row.controls[1].enabled=$false}
            hidden-action {$row.controls[1].visible=$false}
            hidden-dialog {$row.visible=$false}
            duplicate-action {$row.controls+=@($row.controls[1])}
            raced-directory {[IO.Directory]::CreateDirectory($script:workspace.path) | Out-Null}
        }
    } elseif ($script:scenario -eq 'settings-failure') { $row.controls[1].name='Cancel' }
    if ($script:scenario -eq 'delayed-transition' -and $script:stage -eq 1 -and $script:reads -eq 2) {$row.title='Working directory'}
    if ($script:scenario -eq 'duplicate-dialog') {[pscustomobject]@{snapshot=$row;element='duplicate-element'}}
    if ($script:scenario -eq 'unexpected-modal') {
        $other=$row|ConvertTo-Json -Depth 5|ConvertFrom-Json -AsHashtable; $other.title='Error'
        [pscustomobject]@{snapshot=$other;element='other-modal'}
    }
    return [pscustomobject]@{snapshot=$row;element='fixture-element'}
}
function Invoke-BeatQuayFirstRunAction($Process,$Window,[string]$Title,[string]$Action,[string]$Message) {
    $script:actions.Add($Action)
    if ($script:stage -eq 0) {
        if ($Title -cne 'Working directory' -or $Action -cne 'Yes' -or $Message -cne (Get-BeatQuayWorkingDirectoryMessage $script:workspace.path)) {throw 'Wrong creation action'}
        [IO.Directory]::CreateDirectory((Join-Path $script:workspace.path 'projects/templates')) | Out-Null
        [IO.Directory]::CreateDirectory((Join-Path $script:workspace.path 'samples')) | Out-Null
    } elseif ($Title -cne 'BeatQuay - Settings' -or $Action -cne 'OK') {throw 'Wrong setup action'}
    $script:stage++
}
function Wait-BeatQuayFirstRunEditor($Process) {return @{title='BeatQuay 1.0.0';visible=$true}}
try {
    foreach ($script:scenario in @('normal','delayed-transition','wrong-title','wrong-content','wrong-process','foreign-action','wrong-action','disabled-action','hidden-action','hidden-dialog','duplicate-action','duplicate-dialog','unexpected-modal','raced-directory','settings-failure')) {
        $script:stage=0; $script:reads=0; $script:actions=[Collections.Generic.List[string]]::new()
        $script:workspace=New-BeatQuayWorkingDirectoryRecord (Join-Path $script:root $script:scenario) ('a'*40)
        $observations=[ordered]@{}
        $failure=$null
        try {$evidence=Complete-BeatQuayFirstRun $script:process $script:workspace 'exact-owned-package' $observations} catch {$failure=$_.Exception.Message}
        if ($script:scenario -in @('normal','delayed-transition')) {
            if ($failure -or ($script:actions -join ',') -cne 'Yes,OK' -or -not $script:workspace.ownership_established) {throw "Normal sequence failed: $failure"}
            Assert-BeatQuayFirstRunEvidence $evidence
            Remove-BeatQuayOwnedWorkingDirectory $script:workspace
            if (Test-Path $script:workspace.path) {throw 'Owned working directory was not removed'}
        } elseif ($script:scenario -eq 'settings-failure') {
            if (-not $failure -or ($script:actions -join ',') -cne 'Yes') {throw 'Invalid Settings accepted'}
            Remove-BeatQuayOwnedWorkingDirectory $script:workspace
            if (-not $script:workspace.cleanup_verified) {throw 'Failure after ownership did not clean owned directory'}
        } else {
            if (-not $failure -or $script:actions.Count -or -not $observations.Count) {throw "Unsafe interaction or missing failure observations: $script:scenario"}
            if ($script:scenario -eq 'raced-directory') {
                $cleanupFailure=$null; try {Remove-BeatQuayOwnedWorkingDirectory $script:workspace} catch {$cleanupFailure=$_}
                if (-not $cleanupFailure -or -not (Test-Path $script:workspace.path)) {throw 'Unowned raced directory was removed or hidden'}
            }
        }
        Write-Output "PASS first-run flow: $script:scenario"
    }
    foreach ($mutation in @('missing-marker','changed-marker','foreign-file','foreign-directory','linked-child')) {
        $script:scenario='normal'; $script:stage=0; $script:reads=0; $script:actions=[Collections.Generic.List[string]]::new()
        $script:workspace=New-BeatQuayWorkingDirectoryRecord (Join-Path $script:root $mutation) ('a'*40)
        Complete-BeatQuayFirstRun $script:process $script:workspace 'exact-owned-package' ([ordered]@{}) | Out-Null
        switch ($mutation) {
            missing-marker {Remove-Item $script:workspace.marker_path -Force}
            changed-marker {[IO.File]::WriteAllText($script:workspace.marker_path,'another owner')}
            foreign-file {[IO.File]::WriteAllText((Join-Path $script:workspace.path 'user-project.mmp'),'preserve')}
            foreign-directory {[IO.Directory]::CreateDirectory((Join-Path $script:workspace.path 'unobserved')) | Out-Null}
            linked-child {$linkType=if($IsWindows){'Junction'}else{'SymbolicLink'}; New-Item -ItemType $linkType -Path (Join-Path $script:workspace.path 'linked') -Target $script:root | Out-Null}
        }
        $failure=$null; try {Remove-BeatQuayOwnedWorkingDirectory $script:workspace} catch {$failure=$_}
        if (-not $failure -or -not (Test-Path $script:workspace.path) -or $script:workspace.cleanup_verified) {throw "Unproven directory cleanup accepted: $mutation"}
        Write-Output "PASS working-directory preservation: $mutation"
    }
    $preexisting=Join-Path $script:root 'preexisting'; [IO.Directory]::CreateDirectory($preexisting) | Out-Null
    $failure=$null; try {New-BeatQuayWorkingDirectoryRecord $preexisting ('a'*40)} catch {$failure=$_}
    if (-not $failure) {throw 'Preexisting working directory accepted'}

    $script:ActualCore=${function:Invoke-BeatQuayQualificationCore}
    function Invoke-BeatQuayQualificationCore([Collections.IDictionary]$Operations) {
        $state=$Operations.Preflight.Module.SessionState.PSVariable.GetValue('state')
        $state.output=$script:reportDirectory
        $state.package=Join-Path $script:reportDirectory 'source.msix'
        [IO.File]::WriteAllText($state.package,'unchanged unsigned fixture')
        $state.unsignedPackageSha256=(Get-FileHash $state.package -Algorithm SHA256).Hash.ToLowerInvariant()
        $state.workingDirectory=$script:workspace
        $state.firstRunObservations=$script:observations
        $state.cleanupProcessExit=@{wait_completed=$script:terminated;observation_error=$null}
        # Execute the production directory-cleanup closure in the real outer
        # reporting path, without running Windows installation or process IO.
        foreach ($name in @($Operations.Keys)) {if ($name -cne 'RemoveOwnedWorkingDirectory') {$Operations[$name]={}}}
        return & $script:ActualCore $Operations
    }
    foreach ($script:terminated in @($true,$false)) {
        $script:scenario='normal'; $script:stage=0; $script:reads=0; $script:actions=[Collections.Generic.List[string]]::new()
        $script:workspace=New-BeatQuayWorkingDirectoryRecord (Join-Path $script:root "termination-$script:terminated") ('a'*40)
        $script:observations=[ordered]@{}
        Complete-BeatQuayFirstRun $script:process $script:workspace 'exact-owned-package' $script:observations | Out-Null
        $script:reportDirectory=Join-Path $script:root "evidence-$script:terminated"
        [IO.Directory]::CreateDirectory($script:reportDirectory) | Out-Null
        $failure=$null
        try {Invoke-BeatQuayInstallQualification unused unused unused $script:reportDirectory | Out-Null} catch {$failure=$_}
        $receipt=Get-Content (Join-Path $script:reportDirectory 'installation-qualification.json') -Raw | ConvertFrom-Json
        if ($script:terminated) {
            if ($failure -or (Test-Path $script:workspace.path) -or -not $receipt.working_directory.cleanup_verified) {throw 'Proven termination did not permit controlled cleanup'}
        } else {
            if (-not $failure -or -not (Test-Path $script:workspace.marker_path) -or $receipt.installation_qualification_passed -or $receipt.cleanup_errors[0] -notmatch 'termination is unproven') {throw 'Unproven termination removed the workspace or hid cleanup failure'}
        }
        if (-not $receipt.first_run_observations.'Working directory' -or -not $receipt.first_run_observations.'BeatQuay - Settings') {throw 'First-run snapshots were not retained in the final receipt'}
        Write-Output "PASS real cleanup/reporting closure: terminated=$script:terminated"
    }
} finally {
    $script:process.Dispose()
    Remove-Item $script:root -Recurse -Force
}
