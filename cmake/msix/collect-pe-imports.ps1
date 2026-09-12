[CmdletBinding()] param([string]$Stage='stage',[string]$Output='build-evidence/pe-imports.json',[switch]$LibraryOnly)
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'api-set-resolution.ps1')
function Get-BeatQuayPeImportRecord([string]$Root, [string]$Dumpbin, [string]$SystemDirectory) {
$root=(Resolve-Path -LiteralPath $Root).Path
$all=@(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.Extension -in @('.exe','.dll') })
$byName=@{}; foreach($file in $all){ $key=$file.Name.ToLowerInvariant(); if(-not $byName.ContainsKey($key)){$byName[$key]=@()}; $byName[$key]+=$file }
$unresolved=[Collections.Generic.List[string]]::new(); $ambiguous=[Collections.Generic.List[string]]::new(); $rows=[Collections.Generic.List[object]]::new()
$apiSets=@{}; $resolutionErrors=[Collections.Generic.List[object]]::new()
foreach($file in $all | Sort-Object FullName){
  $outputText=& $dumpbin /nologo /dependents $file.FullName 2>&1 | Out-String
  if($LASTEXITCODE -ne 0){ throw "dumpbin failed for $($file.FullName)" }
  # Sort lowercase ASCII keys ordinally, as Python's casefold ordering does.
  # OrdinalIgnoreCase instead puts libA.dll before lib_.dll. Keep the spelling
  # from the first dumpbin reference while deduplicating by its lowercase key.
  $importNames=[Collections.Generic.SortedDictionary[string,string]]::new([StringComparer]::Ordinal)
  foreach($match in [regex]::Matches($outputText,'(?m)^\s+([A-Za-z0-9_.+\-]+\.(?i:dll|exe))\s*$')) {
    $name=$match.Groups[1].Value; $key=$name.ToLowerInvariant()
    if(-not $importNames.ContainsKey($key)) { $importNames.Add($key,$name) }
  }
  $imports=@($importNames.Values)
  foreach($import in $imports){
    $key=$import.ToLowerInvariant()
    if($byName.ContainsKey($key)){ if(@($byName[$key]).Count -ne 1){$ambiguous.Add("$($file.Name):$import")} }
    else {
      try {
        if (-not $apiSets.ContainsKey($key)) {
          $resolution=Resolve-BeatQuaySystemImport $import $systemDirectory
          if ($resolution) { $apiSets[$key]=$resolution }
        }
      } catch {
        $unresolved.Add("$($file.Name):$import")
        $resolutionErrors.Add([ordered]@{file=$file.Name;import=$import;error=$_.Exception.Message})
      }
    }
  }
  $relative=[IO.Path]::GetRelativePath($root,$file.FullName).Replace('\','/')
  $rows.Add([ordered]@{path=$relative;bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant();imports=@($imports)})
}
$record=[ordered]@{schemaVersion=1;tool=[ordered]@{path=$dumpbin;bytes=(Get-Item $dumpbin).Length;sha256=(Get-FileHash $dumpbin -Algorithm SHA256).Hash.ToLowerInvariant()};files=@($rows);unresolvedImports=@($unresolved);ambiguousPackagedImports=@($ambiguous);systemDirectory=$systemDirectory;apiSetResolutions=@($apiSets.Values|Sort-Object contract);resolutionErrors=@($resolutionErrors)}
return $record
}
if ($LibraryOnly) { return }
if (-not $IsWindows -or $env:CI -ne 'true') { throw 'PE import collection requires disposable Windows CI.' }
if (Test-Path -LiteralPath $Output) { throw 'PE import evidence exists and will not be replaced.' }
$dumpbin=(Get-Command dumpbin.exe -ErrorAction Stop).Source
$record=Get-BeatQuayPeImportRecord $Stage $dumpbin ([Environment]::SystemDirectory)
$parent=Split-Path -Parent $Output; New-Item -ItemType Directory -Force $parent | Out-Null
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($record|ConvertTo-Json -Depth 10)+[Environment]::NewLine)
$stream=[IO.FileStream]::new((Join-Path (Resolve-Path $parent) (Split-Path -Leaf $Output)),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
if($record.unresolvedImports.Count -or $record.ambiguousPackagedImports.Count){throw 'Unresolved or ambiguous PE imports remain; evidence retained.'}
