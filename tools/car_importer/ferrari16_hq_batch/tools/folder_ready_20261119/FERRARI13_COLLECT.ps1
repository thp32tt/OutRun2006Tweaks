$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$folder=Join-Path $root 'FERRARI13_DIAG'
New-Item -ItemType Directory -Path $folder -Force|Out-Null
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$stage=Join-Path $folder ('CAPTURE_'+$stamp)
New-Item -ItemType Directory -Path $stage -Force|Out-Null
$lines=New-Object System.Collections.Generic.List[string]
$lines.Add('CapturedUTC='+((Get-Date).ToUniversalTime().ToString('o')))
foreach($name in @('OR2006C2C.EXE','dinput8.dll','outrun-vr-host.exe','OutRun2006Tweaks.ini','OutRun2006Tweaks.user.ini')){
    $p=Join-Path $root $name
    if(Test-Path -LiteralPath $p -PathType Leaf){
        $item=Get-Item -LiteralPath $p
        $value=$name+' bytes='+$item.Length
        if($name -in @('dinput8.dll','outrun-vr-host.exe')){ $value+=' sha256='+((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()) }
        $lines.Add($value)
    }else{ $lines.Add('MISSING '+$name) }
}
$procs=@(Get-Process -Name 'OR2006C2C','outrun-vr-host' -ErrorAction SilentlyContinue|ForEach-Object{$_.ProcessName+':'+$_.Id})
$lines.Add('Processes='+($procs -join ','))
$patterns=@('OutRun2006Tweaks*.log','outrun-vr-host*.log','outrun-vr-watchdog*.log','crash.log','OR2006C2C*.log','OUTRUNVR_LAUNCH_ERROR.txt')
$sources=@()
foreach($pattern in $patterns){$sources+=@(Get-ChildItem -LiteralPath $root -File -Filter $pattern -ErrorAction SilentlyContinue)}
$sources+=@(Get-ChildItem -LiteralPath $folder -File -Filter 'FERRARI13_RUN_*.log' -ErrorAction SilentlyContinue)
$sources=@($sources|Sort-Object FullName -Unique|Sort-Object LastWriteTime -Descending|Select-Object -First 30)
$remaining=[long](24*1024*1024);$num=0
foreach($f in $sources){
    if($remaining -le 0){break}
    $limit=[long][Math]::Min(4*1024*1024,$remaining)
    try{
        $s=New-Object System.IO.FileStream($f.FullName,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,[System.IO.FileShare]::ReadWrite)
        try{
            $len=$s.Length
            $offset=[long][Math]::Max(0,[long]($len-$limit))
            [void]$s.Seek($offset,[System.IO.SeekOrigin]::Begin)
            $dst=Join-Path $stage (('{0:D2}_' -f $num)+$f.Name)
            $o=[System.IO.File]::Create($dst)
            try{
                $buf=New-Object byte[] 65536
                $left=[long]($len-$offset)
                while($left -gt 0){
                    $n=$s.Read($buf,0,[int][Math]::Min($buf.Length,$left))
                    if($n -le 0){break}
                    $o.Write($buf,0,$n)
                    $left-=$n
                }
            }finally{$o.Dispose()}
            $remaining-=(Get-Item -LiteralPath $dst).Length
            $lines.Add($f.Name+' original='+$len+' tailCopied='+($len-$offset))
            $num++
        }finally{$s.Dispose()}
    }catch{$lines.Add('Log read error: '+$f.Name+' '+$_.Exception.Message)}
}
if($num -eq 0){$lines.Add('NO_LOG_FILES_FOUND: check if dinput8.dll was loaded and OUTRUN_VR_FILE_LOG=1 was inherited.')}
foreach($d in @(Get-ChildItem -LiteralPath $root -File -Filter '*.dmp' -ErrorAction SilentlyContinue|Select-Object -First 8)){
    $lines.Add('Crash dump exists (not copied because possibly large): '+$d.FullName)
}
[IO.File]::WriteAllLines((Join-Path $stage 'SUMMARY.txt'),$lines.ToArray(),[Text.Encoding]::UTF8)
Add-Type -AssemblyName System.IO.Compression.FileSystem
$dest=Join-Path $folder ('FERRARI13_LOGS_'+$stamp+'.zip')
[IO.Compression.ZipFile]::CreateFromDirectory($stage,$dest)
Write-Host ('DIAGNOSTIC ZIP: '+$dest)
Write-Host 'Share this diagnostic ZIP for white-screen investigation. The game may remain open while collecting.'