$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'collect-ms-runtime-origins.ps1')
$fixture=Join-Path $PSScriptRoot ('.runtime-origin-fixture-'+[Guid]::NewGuid().ToString('N'))
$created=$false
try {
    New-Item -ItemType Directory -Path $fixture | Out-Null; $created=$true
    $runtimeInput=Join-Path $fixture 'original.dll'
    [byte[]]$original=0,255,13,10,42,17
    [IO.File]::WriteAllBytes($runtimeInput,$original)
    $record=Get-RegularRuntimeRecord $runtimeInput
    $expected=(Get-FileHash -LiteralPath $runtimeInput -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($record.bytes -ne 6 -or $record.sha256 -cne $expected) { throw 'Actual runtime reader changed file bytes or hash.' }
    foreach ($key in 'fileVersion','productVersion','companyName') {
        if (-not $record.ContainsKey($key) -or $record[$key] -isnot [string]) { throw 'Missing explicit version observation.' }
    }
    $renamed=Join-Path $fixture 'renamed.dll'
    Move-Item -LiteralPath $runtimeInput -Destination $renamed
    Move-Item -LiteralPath $renamed -Destination $runtimeInput
    if ((Get-FileHash -LiteralPath $runtimeInput -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expected) { throw 'Original changed after read/handle-close check.' }
    $rejected=$false
    try { Get-RegularRuntimeRecord $fixture | Out-Null } catch { $rejected=$true }
    if (-not $rejected) { throw 'Actual reader accepted directory input.' }
    Write-Output 'Runtime reader: exact bytes/hash, explicit metadata, closed file handle, directory rejection passed.'
} finally {
    if ($created) {
        $files=@(Get-ChildItem -LiteralPath $fixture -Force)
        foreach ($file in $files) {
            if ($file.PSIsContainer -or $file.Name -notin @('original.dll','renamed.dll') -or
                (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) -or
                ([Convert]::ToBase64String([IO.File]::ReadAllBytes($file.FullName)) -cne [Convert]::ToBase64String($original))) {
                throw 'Refusing cleanup of changed/foreign runtime fixture.'
            }
        }
        foreach ($file in $files) { Remove-Item -LiteralPath $file.FullName }
        Remove-Item -LiteralPath $fixture -Force
    }
}
