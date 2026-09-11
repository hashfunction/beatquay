[CmdletBinding()] param([string]$Stage='stage',[string]$Output='build-evidence/pe-imports.json')
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
if (-not $IsWindows -or $env:CI -ne 'true') { throw 'PE import collection requires disposable Windows CI.' }
if (Test-Path -LiteralPath $Output) { throw 'PE import evidence exists and will not be replaced.' }
$root=(Resolve-Path -LiteralPath $Stage).Path
$dumpbin=(Get-Command dumpbin.exe -ErrorAction Stop).Source
$all=@(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.Extension -in @('.exe','.dll') })
$byName=@{}; foreach($file in $all){ $key=$file.Name.ToLowerInvariant(); if(-not $byName.ContainsKey($key)){$byName[$key]=@()}; $byName[$key]+=$file }
$unresolved=[Collections.Generic.List[string]]::new(); $ambiguous=[Collections.Generic.List[string]]::new(); $rows=[Collections.Generic.List[object]]::new()
foreach($file in $all | Sort-Object FullName){
  $outputText=& $dumpbin /nologo /dependents $file.FullName 2>&1 | Out-String
  if($LASTEXITCODE -ne 0){ throw "dumpbin failed for $($file.FullName)" }
  $imports=@([regex]::Matches($outputText,'(?im)^\s+([A-Za-z0-9_.+\-]+\.(?:dll|exe))\s*$') | ForEach-Object{$_.Groups[1].Value} | Sort-Object -Unique)
  foreach($import in $imports){
    $key=$import.ToLowerInvariant()
    if($byName.ContainsKey($key)){ if(@($byName[$key]).Count -ne 1){$ambiguous.Add("$($file.Name):$import")} }
    else { $system=Join-Path $env:SystemRoot "System32/$import"; if(-not (Test-Path -LiteralPath $system -PathType Leaf)){$unresolved.Add("$($file.Name):$import")} }
  }
  $relative=[IO.Path]::GetRelativePath($root,$file.FullName).Replace('\','/')
  $rows.Add([ordered]@{path=$relative;bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant();imports=@($imports)})
}
$record=[ordered]@{schemaVersion=1;tool=[ordered]@{path=$dumpbin;bytes=(Get-Item $dumpbin).Length;sha256=(Get-FileHash $dumpbin -Algorithm SHA256).Hash.ToLowerInvariant()};files=@($rows);unresolvedImports=@($unresolved);ambiguousPackagedImports=@($ambiguous)}
$parent=Split-Path -Parent $Output; New-Item -ItemType Directory -Force $parent | Out-Null
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($record|ConvertTo-Json -Depth 10)+[Environment]::NewLine)
$stream=[IO.FileStream]::new((Join-Path (Resolve-Path $parent) (Split-Path -Leaf $Output)),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
if($unresolved.Count -or $ambiguous.Count){throw 'Unresolved or ambiguous PE imports remain; evidence retained.'}
