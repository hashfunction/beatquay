# Copyright 2026 Trieflow LLC. MIT. Delegate original qualified pixels without editing input/UI code.
function Get-BeatSprigScriptHash([string]$Text) {
 return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($Text))).ToLowerInvariant()
}

function Assert-BeatSprigOriginalScreen($State) {
 $retained=$State.originalScreen
 Assert-NoReparsePath $retained.path
 Assert-FileMatchesRecord $retained.path $State.record.sourceInputs.'cmake/msix/consumer-workflow.ps1' 'Qualified original screen helper'|Out-Null
 if(-not $retained.scriptblock.File -or [IO.Path]::GetFullPath($retained.scriptblock.File) -ine $retained.path -or
   (Get-BeatSprigScriptHash $retained.scriptblock.Ast.Extent.Text) -cne $retained.script_sha256){throw 'Retained original screen scriptblock changed'}
}

function New-BeatSprigOriginalScreen($State,[scriptblock]$Original) {
 $path=[IO.Path]::GetFullPath((Join-Path $State.qualifiedSource 'cmake/msix/consumer-workflow.ps1'))
 Assert-NoReparsePath $path
 Assert-FileMatchesRecord $path $State.record.sourceInputs.'cmake/msix/consumer-workflow.ps1' 'Qualified original screen helper'|Out-Null
 $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
 if($errors.Count){throw 'Original qualified source does not parse'}
 $functions=@($ast.FindAll({param($node);$node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Save-BeatQuayConsumerScreen'},$true))
 if($functions.Count -ne 1 -or -not $Original.File -or [IO.Path]::GetFullPath($Original.File) -ine $path -or
  $Original.Ast.Extent.Text -cne $functions[0].Extent.Text){throw 'Screen delegate is not the exact qualified source function'}
 return @{path=$path;source_sha256=$State.record.sourceInputs.'cmake/msix/consumer-workflow.ps1'.sha256;
  script_sha256=(Get-BeatSprigScriptHash $Original.Ast.Extent.Text);scriptblock=$Original}
}

function Invoke-BeatSprigOriginalScreen($State,[string]$Name,[string]$EditorTitle,[string[]]$AllowedDialogs=@()) {
 $scenes=@{
  '01-evening-pulse-project'=@('Evening Pulse - BeatSprig 1.0.1','save_original_project',@())
  '02-export-project'=@('Evening Pulse Reopened - BeatSprig 1.0.1','export_project_wav',@('Export project'))
  '03-export-completed'=@('Evening Pulse Reopened - BeatSprig 1.0.1','wait_actual_export_completion',@('Export project','Export completed'))
 }
 if(-not $scenes.ContainsKey($Name)){throw 'Unexpected capture scene'}
 $scene=$scenes[$Name]
 if($EditorTitle -cne $scene[0] -or $State.workflow.current_action -cne $scene[1] -or
  (@($AllowedDialogs)|ConvertTo-Json -Compress) -cne (@($scene[2])|ConvertTo-Json -Compress)){throw 'Capture scene/title/dialog contract changed'}
 Assert-BeatSprigOriginalScreen $State
 $before=Read-BeatSprigMarketingFrame $State $EditorTitle $AllowedDialogs
 $count=$State.workflow.screenshots.Count
 # Execute the retained original body with its original file context; never
 # stringify/recompile it or alter its pixel, UI, input or screenshot arguments.
 & $State.originalScreen.scriptblock $State $Name $EditorTitle $AllowedDialogs
 Assert-BeatSprigOriginalScreen $State
 $after=Read-BeatSprigMarketingFrame $State $EditorTitle $AllowedDialogs
 foreach($key in @('main_pid','main_handle','foreground_pid','foreground_handle','title','dpi','x','y','width','height','display')){
  if(($before[$key]|ConvertTo-Json -Depth 8 -Compress) -cne ($after[$key]|ConvertTo-Json -Depth 8 -Compress)){throw "Native capture frame changed: $key"}
 }
 if($State.workflow.screenshots.Count -ne $count+1 -or $State.workflow.screenshots[$count].file -cne $Name+'.png'){throw 'Original helper did not produce exactly the requested raw capture'}
 $screen=$State.workflow.screenshots[$count]
 $fields=@{process_id='main_pid';main_window_handle='main_handle';foreground_window='foreground_handle';project_title='title';
  dpi='dpi';x='x';y='y';width='width';height='height';display='display'}
 foreach($key in $fields.Keys){
  if(($screen[$key]|ConvertTo-Json -Depth 8 -Compress) -cne ($before[$fields[$key]]|ConvertTo-Json -Depth 8 -Compress)){throw "Original capture differs from observed frame: $key"}
 }
 $State.captureFrames.Add(@{file=$Name+'.png';before=$before;after=$after;
  original_source_sha256=$State.originalScreen.source_sha256;original_script_sha256=$State.originalScreen.script_sha256})
}
