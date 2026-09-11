# Copyright 2026 Trieflow LLC. MIT. Actual OS contract resolution, never a name allowlist.
function Add-BeatQuayApiSetTypes {
    if (-not ('BeatQuayQualification.ApiSetResolver' -as [type])) {
        Add-Type -Path (Join-Path $PSScriptRoot 'api-set-resolver.cs')
    }
}

function Get-BeatQuayApiSetHost([string]$Contract) {
    Add-BeatQuayApiSetTypes
    return [BeatQuayQualification.ApiSetResolver]::Resolve($Contract)
}

function Assert-BeatQuayApiSetRegularPath([string]$Path) {
    $item=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while ($item) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point in API-set host path: $($item.FullName)" }
        $item=if ($item -is [IO.DirectoryInfo]) { $item.Parent } else { $item.Directory }
    }
}

function Resolve-BeatQuaySystemImport([string]$Import, [string]$SystemDirectory) {
    if ($Import -notmatch '^[A-Za-z0-9_.+\-]+\.(dll|exe)$') { throw 'Invalid imported module name.' }
    # Microsoft API-set naming convention only selects the OS query; it never
    # establishes availability. Preserve the old physical-file rule for other DLLs.
    if ($Import -notmatch '^(api|ext)-[a-z0-9-]+-l[0-9]+-[0-9]+-[0-9]+\.dll$') {
        if (-not (Test-Path -LiteralPath (Join-Path $SystemDirectory $Import) -PathType Leaf)) {
            throw "System import not found: $Import"
        }
        return $null
    }
    $contract=$Import.ToLowerInvariant()
    $resolved=Get-BeatQuayApiSetHost $contract
    if (-not [IO.Path]::IsPathFullyQualified($resolved)) { throw 'API-set host is not an absolute System32 path.' }
    $path=[IO.Path]::GetFullPath($resolved)
    $system=[IO.Path]::GetFullPath($SystemDirectory).TrimEnd([IO.Path]::DirectorySeparatorChar)
    if (-not ([IO.Path]::GetDirectoryName($path)).Equals($system,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'API-set host is not directly inside the actual System32 directory.'
    }
    Assert-BeatQuayApiSetRegularPath $path
    $item=Get-Item -LiteralPath $path -Force
    if ($item.PSIsContainer -or $item.Length -le 0) { throw 'API-set host is not a nonempty regular file.' }
    $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    $signature=Get-AuthenticodeSignature -LiteralPath $path
    $certificate=$signature.SignerCertificate
    if ([string]$signature.Status -cne 'Valid' -or -not $certificate) { throw 'API-set host lacks a valid Microsoft signature.' }
    $names=[Collections.Generic.List[string]]::new()
    $organizations=[Collections.Generic.List[string]]::new()
    foreach ($rdn in $certificate.SubjectName.EnumerateRelativeDistinguishedNames()) {
        if ($rdn.HasMultipleElements) { throw 'Ambiguous API-set host signer.' }
        switch ($rdn.GetSingleElementType().Value) {
            '2.5.4.3' { $names.Add($rdn.GetSingleElementValue()) }
            '2.5.4.10' { $organizations.Add($rdn.GetSingleElementValue()) }
        }
    }
    if ($names.Count -ne 1 -or $organizations.Count -ne 1 -or
        $names[0] -cnotin @('Microsoft Windows Publisher','Microsoft Corporation','Microsoft Windows') -or
        $organizations[0] -cne 'Microsoft Corporation') { throw 'API-set host signer is not Microsoft Windows.' }
    Assert-BeatQuayApiSetRegularPath $path
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $hash) {
        throw 'API-set host changed during signature verification.'
    }
    return [ordered]@{
        contract=$contract;apiSetImplemented=$true;loaderFlags=2048
        hostPath=$path;hostBytes=$item.Length;hostSha256=$hash
        signatureStatus=[string]$signature.Status;signerSubject=$certificate.Subject
        signerIssuer=$certificate.Issuer;signerThumbprint=$certificate.Thumbprint.ToLowerInvariant()
        signerCommonName=$names[0];signerOrganization=$organizations[0]
    }
}
