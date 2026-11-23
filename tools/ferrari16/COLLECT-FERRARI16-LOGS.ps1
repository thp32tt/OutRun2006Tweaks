#Requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$GameRoot,
      [Parameter(Mandatory=$true)][string]$OutputRoot)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath $GameRoot).Path.TrimEnd('\','/')
$marker=Join-Path $root '.ferrari16-isolated.json'
$m=Get-Content -LiteralPath $marker -Raw|ConvertFrom-Json
if($m.Purpose -ne 'FERRARI16_ISOLATED_V003_TEST_COPY' -or
   ![string]::Equals([string]$m.TestRoot,$root,[StringComparison]::OrdinalIgnoreCase)){
    throw 'Only isolated Ferrari16 game copy logs may be collected.'
}
$out=[IO.Path]::GetFullPath($OutputRoot).TrimEnd('\','/')
if(Test-Path -LiteralPath $out){throw 'Output must be a new directory'}
if($out.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -or $out -eq $root){
    throw 'Export logs outside the test game root.'
}
New-Item -ItemType Directory -Path $out -ErrorAction Stop|Out-Null
$files=[ordered]@{}
foreach($folder in @($root,(Join-Path $root 'logs'),(Join-Path $root 'crashes'),
                      (Join-Path $root 'CrashDumps'))){
    if(!(Test-Path -LiteralPath $folder -PathType Container)){continue}
    foreach($filter in @('*.log','*.dmp','*.mdmp','*.stacktrace')){
        Get-ChildItem -LiteralPath $folder -Filter $filter -File | ForEach-Object {
            if($_.Attributes -band [IO.FileAttributes]::ReparsePoint){return}
            $name=([IO.Path]::GetFileName($folder)+'_'+$_.Name)
            $dest=Join-Path $out $name
            if(Test-Path -LiteralPath $dest){throw "Log name collision: $name"}
            Copy-Item -LiteralPath $_.FullName -Destination $dest -ErrorAction Stop
            $files[$name]=(Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
}
([ordered]@{Schema=1;Purpose='FERRARI16_PRIVATE_LOGS';RuntimeValidation='UNTESTED'
    SourceRoot=$root;CollectedUtc=[DateTime]::UtcNow.ToString('o');Files=$files}|
    ConvertTo-Json -Depth 5)|
    Set-Content -LiteralPath (Join-Path $out 'LOG_SHA256.json') -Encoding UTF8
Write-Host "PASS: $($files.Count) log/dump files captured; review sensitive content before sharing."
