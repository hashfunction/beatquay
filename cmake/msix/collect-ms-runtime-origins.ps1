param([string]$Selection, [string]$Stage, [string]$SourceCommit, [string]$Output)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Get-RegularRuntimeRecord([string]$Path) {
    $file=Get-Item -LiteralPath $Path -Force
    if ($file.PSIsContainer) { throw "Runtime input must be a regular file: $Path" }
    $node=$file
    while ($null -ne $node) {
        if (($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Runtime reparse point refused: $Path" }
        $node=if ($node -is [IO.FileInfo]) { $node.Directory } else { $node.Parent }
    }
    $stream=[IO.File]::Open($file.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        $hash=[Security.Cryptography.SHA256]::Create()
        try { $sha=([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
        finally { $hash.Dispose() }
        $version=[Diagnostics.FileVersionInfo]::GetVersionInfo($file.FullName)
        return @{bytes=$stream.Length;sha256=$sha;fileVersion=[string]$version.FileVersion;productVersion=[string]$version.ProductVersion;companyName=[string]$version.CompanyName}
    } finally { $stream.Dispose() }
}

function Invoke-MsRuntimeOriginCollection {
    if ($env:OS -ne 'Windows_NT' -or $env:CI -ne 'true') { throw 'Microsoft origin collection requires the actual Windows CI build.' }
    if ($SourceCommit -cnotmatch '^[0-9a-f]{40}$') { throw 'Exact source commit required.' }
    if (Test-Path -LiteralPath $Output) { throw 'Runtime origin output already exists.' }
    $selected=Get-Content -LiteralPath $Selection -Raw -Encoding utf8 | ConvertFrom-Json
    $selectorHash=(Get-RegularRuntimeRecord $Selection).sha256
    if ($selected.schemaVersion -ne 1 -or $selected.architecture -cne 'x64' -or $selected.buildType -cne 'RelWithDebInfo') { throw 'Unexpected runtime discovery configuration.' }
    $seen=@{}; $files=@()
    foreach ($path in $selected.sourcePaths) {
        $name=[IO.Path]::GetFileName([string]$path)
        if ($seen.ContainsKey($name.ToLowerInvariant())) { throw "Duplicate selected runtime basename: $name" }
        $seen[$name.ToLowerInvariant()]=$true
        $original=Get-RegularRuntimeRecord $path
        $staged=Get-RegularRuntimeRecord (Join-Path $Stage $name)
        if ($original.bytes -ne $staged.bytes -or $original.sha256 -cne $staged.sha256) { throw "Staged runtime differs from its selected original: $name" }
        $signature=Get-AuthenticodeSignature -LiteralPath $path
        $files+=@{path=$name;sourcePath=[string]$path;bytes=$original.bytes;sha256=$original.sha256;
            fileVersion=$original.fileVersion;productVersion=$original.productVersion;companyName=$original.companyName;
            signatureStatus=[string]$signature.Status;
            signerSubject=$(if ($null -ne $signature.SignerCertificate) { [string]$signature.SignerCertificate.Subject } else { '' })}
        $after=Get-RegularRuntimeRecord $path
        if ($after.bytes -ne $original.bytes -or $after.sha256 -cne $original.sha256) { throw 'Runtime origin changed during observation.' }
    }
    if ((Get-RegularRuntimeRecord $Selection).sha256 -cne $selectorHash) { throw 'Runtime selector changed during observation.' }
    $record=@{schemaVersion=1;sourceCommit=$SourceCommit;selectionSha256=$selectorHash;
        files=@($files | Sort-Object path);licenseClearanceClaimed=$false;
        redistributionTerms=@{
            visualStudio='https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution';
            visualStudioLicense='https://visualstudio.microsoft.com/license-terms/vs2022-ga-proenterprise/';
            universalCrt='https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment?view=msvc-170'}}
    $parent=Split-Path -Parent $Output
    if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($record | ConvertTo-Json -Depth 8)+"`n")
    $out=[IO.File]::Open($Output,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $out.Write($bytes,0,$bytes.Length) } finally { $out.Dispose() }
}

if ($MyInvocation.InvocationName -ne '.') { Invoke-MsRuntimeOriginCollection }
