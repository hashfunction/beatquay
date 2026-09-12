# Copyright 2026 Trieflow LLC. MIT. Execute the actual dispatch tail; no native acceptance is simulated.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualification-bindings.ps1')
$production=Get-Content (Join-Path $PSScriptRoot 'qualify-msix.ps1') -Raw
$tail=$production.Substring($production.IndexOf('$exportRequested='))
$scriptBlock=[scriptblock]::Create($tail)
$sourceCommit='a'*40;$pythonPath='owned-fixture-python';$powerShell='owned-fixture-pwsh'
$script:dispatchCalls=[Collections.Generic.List[object]]::new()
function Invoke-Checked([string]$Program,[string[]]$Arguments){
    $script:dispatchCalls.Add(@{program=$Program;arguments=$Arguments})
    if($Arguments[0] -ceq 'cmake/msix/msix_qualification.py'){
        $output=$Arguments[[Array]::IndexOf($Arguments,'--output')+1]
        New-Item -ItemType Directory $output|Out-Null
        [IO.File]::WriteAllText((Join-Path $output 'package-record.json'),'owned generated dispatcher fixture only')
    }elseif($Program -ceq $powerShell){
        $mode=$Arguments[[Array]::IndexOf($Arguments,'-IdentityMode')+1]
        if($mode -ceq $script:failMode){throw "Fixture lifecycle failure: $mode"}
    }elseif($Arguments[0] -cne 'cmake/msix/export_store_package.py'){throw 'Unexpected dispatch'}
}
$variables=@('BEATSPRIG_EXPORT_STORE_PACKAGE','BEATSPRIG_REVIEWED_PUBLIC_SOURCE','GITHUB_EVENT_NAME','RUNNER_TEMP','ProgramFiles(x86)')
$saved=@{};foreach($name in $variables){$saved[$name]=[Environment]::GetEnvironmentVariable($name)}
$parent=if($IsMacOS){'/private/tmp'}else{[IO.Path]::GetTempPath()}
$fixture=Join-Path $parent ('beatsprig-export-dispatch-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $fixture|Out-Null
$location=Get-Location
try{
    foreach($case in @('false','empty','true','qualification-failure','store-failure','wrong-source','wrong-event','malformed')){
        $root=Join-Path $fixture $case;New-Item -ItemType Directory (Join-Path $root 'build-evidence')|Out-Null
        Set-Location $root;$env:RUNNER_TEMP=$root;[Environment]::SetEnvironmentVariable('ProgramFiles(x86)',$root)
        $env:BEATSPRIG_EXPORT_STORE_PACKAGE=if($case -ceq 'false'){'false'}elseif($case -ceq 'empty'){''}elseif($case -ceq 'malformed'){'TRUE'}else{'true'}
        $env:BEATSPRIG_REVIEWED_PUBLIC_SOURCE=if($case -ceq 'wrong-source'){'b'*40}else{$sourceCommit}
        $env:GITHUB_EVENT_NAME=if($case -ceq 'wrong-event'){'push'}else{'workflow_dispatch'}
        $script:failMode=if($case -ceq 'qualification-failure'){'qualification'}elseif($case -ceq 'store-failure'){'store'}else{''}
        $script:dispatchCalls.Clear();$failure=$null
        try{. $scriptBlock}catch{$failure=$_.Exception.Message}
        $expectedFailure=$case -cnotin @('false','empty','true')
        if([bool]$failure -ne $expectedFailure){throw "Wrong dispatch outcome for ${case}: $failure"}
        $exports=@($script:dispatchCalls|Where-Object {$_.arguments[0] -ceq 'cmake/msix/export_store_package.py'})
        if($exports.Count -ne $(if($case -ceq 'true'){1}else{0})){throw "Unexpected export after $case"}
        if($case -cin @('wrong-source','wrong-event','malformed') -and $script:dispatchCalls.Count){throw 'Invalid review performed work'}
        if($case -ceq 'qualification-failure' -and $script:dispatchCalls.Count -ne 2){throw 'Second lifecycle ran after first failure'}
        if($case -ceq 'store-failure' -and $script:dispatchCalls.Count -ne 4){throw 'Export ran after second failure'}
        if($case -ceq 'true'){
            if($script:dispatchCalls.Count -ne 5){throw 'Expected pack/install/pack/install/export order'}
            $exportArguments=$exports[0].arguments
            if($exportArguments.Count -ne 7 -or $exportArguments[1] -cne '--qualification-package' -or $exportArguments[3] -cne '--store-package' -or
                $exportArguments[5] -cne '--reviewed-public-source' -or $exportArguments[6] -cne $sourceCommit -or
                [IO.Path]::GetFileName($exportArguments[2]) -cne 'BeatSprig.Qualification_1.0.1.0_x64.msix' -or
                [IO.Path]::GetFileName($exportArguments[4]) -cne 'BeatSprig_1.0.1.0_x64.msix' -or
                [IO.Path]::GetDirectoryName($exportArguments[2]) -ceq [IO.Path]::GetDirectoryName($exportArguments[4])){throw 'Original package paths or exact source were lost across callback scope'}
        }
    }
}finally{
    Set-Location $location
    foreach($name in $variables){[Environment]::SetEnvironmentVariable($name,$saved[$name])}
    Remove-Item -LiteralPath $fixture -Recurse -Force
}
Write-Output 'PASS 8 actual dispatcher scenarios: default/no export, exact original two paths, both lifecycle failures, wrong source/event and malformed opt-in.'
