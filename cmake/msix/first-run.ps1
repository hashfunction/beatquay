# Exact normal first-run interactions and owned working-directory cleanup.
# Copyright 2026 Trieflow LLC. MIT.
function Get-BeatQuayWorkingDirectoryMessage([string]$Path) {
    $display=$Path.Replace('\','/').TrimEnd('/')+'/'
    return "The BeatSprig working directory $display does not exist. Create it now? You can change the directory later via Edit -> Settings."
}

function New-BeatQuayWorkingDirectoryRecord([string]$Path,[string]$SourceCommit) {
    $path=Get-CanonicalPath $Path
    if (Test-Path -LiteralPath $path) {throw 'Preexisting BeatQuay documents invalidate first-run qualification.'}
    return [ordered]@{path=$path;source_commit=$SourceCommit;absent_before_action=$false;action_invoked=$false;
        package_full_name=$null;process_id=0;ownership_established=$false;marker_path=$null;marker_sha256=$null;
        directories=@();cleanup_verified=$false}
}

function Confirm-BeatQuayWorkingDirectoryOwnership($Workspace,[int]$ProcessId,[string]$PackageFullName) {
    if (-not $Workspace.absent_before_action -or -not $Workspace.action_invoked -or $ProcessId -le 0 -or -not $PackageFullName) {throw 'Working-directory creation provenance is incomplete.'}
    Assert-NoReparsePath $Workspace.path
    $items=@(Get-ChildItem -LiteralPath $Workspace.path -Recurse -Force -ErrorAction Stop)
    foreach ($item in $items) {
        Assert-NoReparsePath $item.FullName
        if (-not $item.PSIsContainer) {throw 'Unexpected files appeared in the new working directory; preserving it.'}
    }
    $Workspace.directories=@($items | ForEach-Object {$_.FullName.Substring($Workspace.path.Length+1)} | Sort-Object)
    $marker=Join-Path $Workspace.path ('.beatquay-qualification-owner-'+[guid]::NewGuid().ToString('N')+'.json')
    Write-NewUtf8Json $marker ([ordered]@{source_commit=$Workspace.source_commit;package_full_name=$PackageFullName;process_id=$ProcessId;path=$Workspace.path})
    $Workspace.marker_path=$marker
    $Workspace.marker_sha256=(Get-FileHash -LiteralPath $marker -Algorithm SHA256).Hash.ToLowerInvariant()
    $Workspace.package_full_name=$PackageFullName; $Workspace.process_id=$ProcessId
    $Workspace.ownership_established=$true
}

function Remove-BeatQuayOwnedWorkingDirectory($Workspace) {
    if (-not $Workspace) {return}
    if (-not (Test-Path -LiteralPath $Workspace.path)) {
        if ($Workspace.ownership_established) {throw 'Owned working directory disappeared before controlled cleanup.'}
        return
    }
    if (-not $Workspace.ownership_established) {throw 'Unowned working directory appeared; preserving it.'}
    Assert-NoReparsePath $Workspace.path
    Assert-NoReparsePath $Workspace.marker_path
    if ((Get-FileHash -LiteralPath $Workspace.marker_path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Workspace.marker_sha256) {throw 'Working-directory ownership marker changed; preserving it.'}
    $items=@(Get-ChildItem -LiteralPath $Workspace.path -Recurse -Force -ErrorAction Stop)
    $directories=[Collections.Generic.List[string]]::new()
    foreach ($item in $items) {
        Assert-NoReparsePath $item.FullName
        if ($item.PSIsContainer) {$directories.Add($item.FullName.Substring($Workspace.path.Length+1))}
        elseif ($item.FullName -cne $Workspace.marker_path) {throw 'Unexpected working-directory file; preserving it.'}
    }
    if ((@($directories | Sort-Object) -join "`n") -cne (@($Workspace.directories) -join "`n")) {throw 'Working-directory structure changed; preserving it.'}
    # Nonrecursive deletion refuses late-arriving contents instead of deleting them.
    foreach ($relative in @($directories | Sort-Object Length -Descending)) {
        $path=Join-Path $Workspace.path $relative; Assert-NoReparsePath $path
        [IO.Directory]::Delete($path,$false)
    }
    Assert-NoReparsePath $Workspace.marker_path
    if ((Get-FileHash -LiteralPath $Workspace.marker_path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Workspace.marker_sha256) {throw 'Working-directory ownership marker changed during cleanup.'}
    [IO.File]::Delete($Workspace.marker_path)
    [IO.Directory]::Delete($Workspace.path,$false)
    $Workspace.cleanup_verified=$true
}

function Get-BeatQuayFirstRunWindowSnapshot($Window) {
    $current=$Window.Current
    $controls=[Collections.Generic.List[object]]::new(); $textTruncated=$false
    $children=$Window.FindAll([Windows.Automation.TreeScope]::Subtree,[Windows.Automation.Condition]::TrueCondition)
    for ($index=0; $index -lt [Math]::Min($children.Count,128); $index++) {
        $item=$children.Item($index).Current
        $name=[string]$item.Name
        if ($name.Length -gt 2048) {$name=$name.Substring(0,2048);$textTruncated=$true}
        $controls.Add([ordered]@{name=$name;control_type=$item.ControlType.ProgrammaticName.Replace('ControlType.','');
            process_id=$item.ProcessId;visible=(-not $item.IsOffscreen);enabled=$item.IsEnabled})
    }
    $title=[string]$current.Name
    if ($title.Length -gt 2048) {$title=$title.Substring(0,2048);$textTruncated=$true}
    return [ordered]@{title=$title;process_id=$current.ProcessId;visible=(-not $current.IsOffscreen);enabled=$current.IsEnabled;
        width=$current.BoundingRectangle.Width;height=$current.BoundingRectangle.Height;class_name=[string]$current.ClassName;
        controls=@($controls);truncated=($children.Count -gt 128 -or $textTruncated)}
}

function Get-BeatQuayFirstRunWindows([Diagnostics.Process]$Process) {
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
    $condition=[Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::ProcessIdProperty,$Process.Id)
    $windows=[Windows.Automation.AutomationElement]::RootElement.FindAll([Windows.Automation.TreeScope]::Children,$condition)
    for ($index=0; $index -lt [Math]::Min($windows.Count,8); $index++) {
        $window=$windows.Item($index)
        $snapshot=Get-BeatQuayFirstRunWindowSnapshot $window
        $snapshot.truncated=$snapshot.truncated -or $windows.Count -gt 8
        [pscustomobject]@{element=$window;snapshot=$snapshot}
    }
}

function Assert-BeatQuayFirstRunDialog($Snapshot,[int]$ProcessId,[string]$Title,[string]$Action,[string]$Message) {
    if ($Snapshot.title -cne $Title -or $Snapshot.process_id -ne $ProcessId -or -not $Snapshot.visible -or -not $Snapshot.enabled -or
        $Snapshot.width -le 0 -or $Snapshot.height -le 0 -or ($Snapshot.Contains('truncated') -and $Snapshot.truncated)) {throw "Missing exact visible owned first-run dialog: $Title"}
    if ($Message -and @($Snapshot.controls | Where-Object {$_.name -ceq $Message -and $_.control_type -ceq 'Text' -and $_.process_id -eq $ProcessId -and $_.visible}).Count -ne 1) {throw 'Working-directory prompt content does not match the exact fresh BeatQuay path.'}
    $buttons=@($Snapshot.controls | Where-Object {$_.name -ceq $Action -and $_.control_type -ceq 'Button' -and $_.process_id -eq $ProcessId -and $_.visible -and $_.enabled})
    if ($buttons.Count -ne 1) {throw "First-run $Title lacks one visible enabled owned $Action action."}
}

function Wait-BeatQuayFirstRunDialog([Diagnostics.Process]$Process,[string]$Title,$Observations) {
    $deadline=[DateTime]::UtcNow.AddSeconds(30)
    do {
        $Process.Refresh(); if ($Process.HasExited) {throw 'BeatQuay exited during first-run setup.'}
        $windows=@(Get-BeatQuayFirstRunWindows $Process)
        $Observations[$Title]=@($windows | ForEach-Object {$_.snapshot})
        foreach ($window in $windows) {
            if ($window.snapshot.process_id -ne $Process.Id -or ($window.snapshot.Contains('truncated') -and $window.snapshot.truncated)) {throw 'Owned startup observation is foreign or truncated; refusing interaction.'}
            $transition=$Title -ceq 'BeatSprig - Settings' -and $window.snapshot.title -ceq 'Working directory'
            if ($window.snapshot.visible -and $window.snapshot.title -cne $Title -and $window.snapshot.title -cne 'BeatSprig 1.0.1' -and -not $transition) {throw "Unexpected owned first-run surface: $($window.snapshot.title)"}
        }
        $matches=@($windows | Where-Object {$_.snapshot.title -ceq $Title})
        if ($matches.Count -gt 1) {throw "Ambiguous owned first-run dialog: $Title"}
        # Invoke is asynchronous: observe the first prompt disappear, then act on Settings.
        $oldPromptVisible=$Title -ceq 'BeatSprig - Settings' -and @($windows | Where-Object {$_.snapshot.title -ceq 'Working directory' -and $_.snapshot.visible}).Count -gt 0
        if ($matches.Count -eq 1 -and -not $oldPromptVisible) {return $matches[0]}
        Start-Sleep -Milliseconds 250
    } until ([DateTime]::UtcNow -ge $deadline)
    throw "Fresh installed activation did not show the exact $Title first-run dialog."
}

function Invoke-BeatQuayFirstRunAction([Diagnostics.Process]$Process,$Window,[string]$Title,[string]$Action,[string]$Message) {
    # Re-read the live provider immediately before Invoke; never use a stale snapshot to act.
    $Process.Refresh(); if ($Process.HasExited) {throw 'BeatQuay exited before the first-run action.'}
    Assert-BeatQuayFirstRunDialog (Get-BeatQuayFirstRunWindowSnapshot $Window.element) $Process.Id $Title $Action $Message
    $buttons=$Window.element.FindAll([Windows.Automation.TreeScope]::Subtree,
        [Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::NameProperty,$Action))
    $valid=@(for ($index=0;$index -lt $buttons.Count;$index++) {
        $button=$buttons.Item($index); $current=$button.Current
        if ($current.ControlType -eq [Windows.Automation.ControlType]::Button -and $current.ProcessId -eq $Process.Id -and $current.IsEnabled -and -not $current.IsOffscreen) {$button}
    })
    if ($valid.Count -ne 1) {throw 'First-run action changed before invocation.'}
    $pattern=$valid[0].GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern)
    if (-not $pattern) {throw 'First-run action is not invokable.'}
    $pattern.Invoke()
}

function Wait-BeatQuayFirstRunEditor([Diagnostics.Process]$Process) {
    $deadline=[DateTime]::UtcNow.AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 250; $Process.Refresh()
        if ($Process.HasExited) {throw 'BeatQuay exited while completing first-run setup.'}
    } until ($Process.MainWindowTitle -ceq 'BeatSprig 1.0.1' -or [DateTime]::UtcNow -ge $deadline)
    return @{title=$Process.MainWindowTitle;visible=($Process.MainWindowHandle -ne 0)}
}

function Complete-BeatQuayFirstRun([Diagnostics.Process]$Process,$Workspace,[string]$PackageFullName,$Observations) {
    $message=Get-BeatQuayWorkingDirectoryMessage $Workspace.path
    $working=Wait-BeatQuayFirstRunDialog $Process 'Working directory' $Observations
    Assert-BeatQuayFirstRunDialog $working.snapshot $Process.Id 'Working directory' 'Yes' $message
    if (Test-Path -LiteralPath $Workspace.path) {throw 'Working directory appeared before the observed creation action; preserving it.'}
    $Workspace.absent_before_action=$true
    Invoke-BeatQuayFirstRunAction $Process $working 'Working directory' 'Yes' $message
    $Workspace.action_invoked=$true
    $setup=Wait-BeatQuayFirstRunDialog $Process 'BeatSprig - Settings' $Observations
    Confirm-BeatQuayWorkingDirectoryOwnership $Workspace $Process.Id $PackageFullName
    Assert-BeatQuayFirstRunDialog $setup.snapshot $Process.Id 'BeatSprig - Settings' 'OK' ''
    Invoke-BeatQuayFirstRunAction $Process $setup 'BeatSprig - Settings' 'OK' ''
    $editor=Wait-BeatQuayFirstRunEditor $Process
    $snapshot=[ordered]@{working_directory=[ordered]@{title='Working directory';message=$message;path=$Workspace.path;process_id=$Process.Id;visible=$true;action_name='Yes';action_invoked=$true};
        setup_title='BeatSprig - Settings';setup_visible=$true;action_name='OK';action_invoked=$true;editor_title=$editor.title;editor_visible=$editor.visible}
    Assert-BeatQuayFirstRunEvidence $snapshot
    return $snapshot
}
