# Copyright 2026 Trieflow LLC. MIT. Native boundary and real provenance fixtures.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'collect-pe-imports.ps1') -LibraryOnly
Add-BeatQuayApiSetTypes
function Assert-Rejected([scriptblock]$Operation, [string]$Pattern) {
    try { & $Operation | Out-Null } catch {
        if ($_.Exception.Message -notmatch $Pattern) { throw }
        return
    }
    throw "Expected rejection: $Pattern"
}
if ($IsWindows) {
    foreach ($contract in @('api-ms-win-core-winrt-error-l1-1-1.dll',
        'api-ms-win-core-winrt-l1-1-0.dll','api-ms-win-core-winrt-string-l1-1-0.dll',
        'api-ms-win-shcore-scaling-l1-1-1.dll')) {
        $resolved=Resolve-BeatQuaySystemImport $contract ([Environment]::SystemDirectory)
        if ($resolved.contract -cne $contract -or $resolved.signatureStatus -cne 'Valid' -or
            $resolved.hostBytes -le 0) { throw 'Native API-set host evidence is incomplete.' }
    }
    Assert-Rejected { Resolve-BeatQuaySystemImport 'api-ms-win-beatquay-absent-l9-9-9.dll' ([Environment]::SystemDirectory) } 'not implemented'
    Write-Output 'PASS four observed native API sets and unavailable-contract rejection'
}
$base=if ($IsMacOS) { '/private/tmp' } else { [IO.Path]::GetTempPath() }
$root=Join-Path $base ('beatquay-api-set-'+[guid]::NewGuid().ToString('N'))
$system=Join-Path $root 'System32'
New-Item -ItemType Directory -Path $system -Force | Out-Null
$script:hostPath=Join-Path $system 'combase.dll'
[IO.File]::WriteAllText($script:hostPath,'known operating-system fixture bytes')
$script:resolveFailure=$false
$script:signatureStatus='Valid'
$script:signatureSubject='CN=Microsoft Windows Publisher, O=Microsoft Corporation, C=US'
$script:mutate=$false
$originalResolver=${function:Get-BeatQuayApiSetHost}
function Get-BeatQuayApiSetHost([string]$Contract) {
    if ($script:resolveFailure) { throw 'API set is not implemented on this OS.' }
    return $script:hostPath
}
function Get-AuthenticodeSignature([string]$LiteralPath) {
    if ($script:mutate) { [IO.File]::WriteAllText($LiteralPath,'changed host bytes') }
    [pscustomobject]@{Status=$script:signatureStatus;SignerCertificate=[pscustomobject]@{
        Subject=$script:signatureSubject;
        SubjectName=[Security.Cryptography.X509Certificates.X500DistinguishedName]::new($script:signatureSubject);
        Issuer='Fixture authority';Thumbprint=('A'*40)}}
}
try {
    $contract='api-ms-win-core-winrt-l1-1-0.dll'
    if (Test-Path (Join-Path $system $contract)) { throw 'Fixture must not contain a physical contract DLL.' }
    $record=Resolve-BeatQuaySystemImport $contract $system
    if ($record.contract -cne $contract -or $record.hostPath -cne $script:hostPath -or
        $record.hostSha256 -cne (Get-FileHash $script:hostPath -Algorithm SHA256).Hash.ToLowerInvariant() -or
        $record.hostBytes -ne 36 -or $record.loaderFlags -ne 2048 -or -not $record.apiSetImplemented) {
        throw 'Resolved contract did not retain its actual host provenance.'
    }
    $stage=Join-Path $root 'stage'
    New-Item -ItemType Directory -Path $stage | Out-Null
    $main=Join-Path $stage 'lmms.exe'
    $qt=Join-Path $stage 'Qt6Core.dll'
    [IO.File]::WriteAllText($main,"  $contract`n  Qt6Core.dll`n")
    [IO.File]::WriteAllText($qt,"  $contract`n")
    $dumpbin=Join-Path $root 'dumpbin.ps1'
    [IO.File]::WriteAllText($dumpbin,'Get-Content -LiteralPath $args[-1]; $global:LASTEXITCODE=0')
    $collected=Get-BeatQuayPeImportRecord $stage $dumpbin $system
    if ($collected.apiSetResolutions.Count -ne 1 -or $collected.files.Count -ne 2 -or
        $collected.unresolvedImports.Count -or $collected.ambiguousPackagedImports.Count) {
        throw 'Collector did not resolve repeated API-set references and the packaged dependency.'
    }
    $stagedContract=Join-Path $stage $contract
    [IO.File]::WriteAllText($stagedContract,'')
    $script:resolveFailure=$true
    $collected=Get-BeatQuayPeImportRecord $stage $dumpbin $system
    if ($collected.apiSetResolutions.Count -or $collected.unresolvedImports.Count) {
        throw 'Collector changed the existing unique packaged-contract path.'
    }
    Remove-Item $stagedContract
    $script:resolveFailure=$false
    Remove-Item $qt
    [IO.File]::WriteAllText($main,"  missing.dll`n")
    $collected=Get-BeatQuayPeImportRecord $stage $dumpbin $system
    if ($collected.unresolvedImports.Count -ne 1 -or $collected.resolutionErrors.Count -ne 1 -or
        $collected.apiSetResolutions.Count) { throw 'Collector hid an unresolved ordinary import.' }
    [IO.File]::WriteAllText($main,"  $contract`n")
    $script:resolveFailure=$true
    $collected=Get-BeatQuayPeImportRecord $stage $dumpbin $system
    if ($collected.unresolvedImports.Count -ne 1 -or $collected.resolutionErrors[0].error -notmatch 'not implemented' -or
        $collected.apiSetResolutions.Count) { throw 'Collector hid an unavailable API set.' }
    $script:resolveFailure=$false
    foreach ($folder in @('a','b')) {
        $directory=Join-Path $stage $folder
        New-Item -ItemType Directory $directory | Out-Null
        [IO.File]::WriteAllText((Join-Path $directory 'shared.dll'),'')
    }
    [IO.File]::WriteAllText($main,"  shared.dll`n")
    $collected=Get-BeatQuayPeImportRecord $stage $dumpbin $system
    if ($collected.ambiguousPackagedImports.Count -ne 1) { throw 'Collector hid an ambiguous packaged import.' }
    # An ordinary physical system import still passes without contract resolution.
    $script:resolveFailure=$true
    if ($null -ne (Resolve-BeatQuaySystemImport 'combase.dll' $system)) { throw 'Ordinary DLL became an API-set record.' }
    Assert-Rejected { Resolve-BeatQuaySystemImport 'missing.dll' $system } 'not found'
    Assert-Rejected { Resolve-BeatQuaySystemImport $contract $system } 'not implemented'
    foreach ($invalid in @('../combase.dll','api-ms-win-core-winrt.dll','api-ms-win-core-winrt-l1-1-0.exe')) {
        Assert-Rejected { Resolve-BeatQuaySystemImport $invalid $system } 'Invalid|not found'
    }
    $script:resolveFailure=$false
    foreach ($status in @('NotSigned','NotTrusted','HashMismatch')) {
        $script:signatureStatus=$status
        Assert-Rejected { Resolve-BeatQuaySystemImport $contract $system } 'signature'
    }
    $script:signatureStatus='Valid'
    foreach ($subject in @('CN=Microsoft Windows Publisher, O=Someone Else',
        'CN=Other, O=Microsoft Corporation','CN=Microsoft Windows Publisher, CN=Other, O=Microsoft Corporation',
        'CN=Other, O=Other, OU="CN=Microsoft Windows Publisher, O=Microsoft Corporation"')) {
        $script:signatureSubject=$subject
        Assert-Rejected { Resolve-BeatQuaySystemImport $contract $system } 'signer'
    }
    $script:signatureSubject='CN=Microsoft Windows Publisher, O=Microsoft Corporation, C=US'
    $actualHost=$script:hostPath
    foreach ($relative in @('System32Fake/combase.dll','System32/nested/combase.dll')) {
        $script:hostPath=Join-Path $root $relative
        New-Item -ItemType Directory -Path (Split-Path $script:hostPath -Parent) -Force | Out-Null
        [IO.File]::WriteAllText($script:hostPath,'foreign host')
        Assert-Rejected { Resolve-BeatQuaySystemImport $contract $system } 'System32'
    }
    $script:hostPath=$actualHost
    $script:mutate=$true
    Assert-Rejected { Resolve-BeatQuaySystemImport $contract $system } 'changed'
    $script:mutate=$false
    $linked=Join-Path $root 'LinkedSystem32'
    $kind=if ($IsWindows) { 'Junction' } else { 'SymbolicLink' }
    New-Item -ItemType $kind -Path $linked -Target $system | Out-Null
    $script:hostPath=Join-Path $linked 'combase.dll'
    Assert-Rejected { Resolve-BeatQuaySystemImport $contract $linked } 'Reparse'
    Write-Output 'PASS API-set resolution, collector deduplication/packaged/missing/ambiguous imports, malformed name, signature, host path, mutation and reparse fixtures'
} finally {
    ${function:Get-BeatQuayApiSetHost}=$originalResolver
    Remove-Item Function:\Get-AuthenticodeSignature
    Remove-Item -LiteralPath $root -Recurse -Force
}
