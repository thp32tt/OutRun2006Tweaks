Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selectScript=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runScript=Join-Path $root 'Run-OutRunVRTest.ps1'
$gameExe=Join-Path $root 'OR2006C2C.EXE'

function Show-Error([string]$Message){
    [void][System.Windows.Forms.MessageBox]::Show($Message,'OutRun VR Tonight Test',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Error)
}

function Write-Target([string]$Backend){
    $target=switch($Backend){
        'd3d9' {
            [ordered]@{
                SchemaVersion=1
                RendererTarget='d3d9ex-reference'
                LaunchBackend='d3d9'
                Stage='2026-09-29-protected-reference'
                NativeDrawPathActive=$true
                VariantId='A_CONTROL'
                DevelopmentBranch='vr-d3d9ex-focus'
            }
        }
        'dx11' {
            [ordered]@{
                SchemaVersion=1
                RendererTarget='dx11-native'
                LaunchBackend='dx11'
                Stage='R97-dormant-fixed-function-pipeline-native-draw-not-active'
                NativeDrawPathActive=$false
                VariantId='R57_05_RANK_PROJECTED_IPD'
                DevelopmentBranch='vr-dx11-native-r71'
            }
        }
        'dxvk-safe' {
            [ordered]@{
                SchemaVersion=1
                RendererTarget='dxvk'
                LaunchBackend='dxvk-safe'
                Stage='R71-stock-dxvk-3.1.1-two-pass-safe'
                NativeDrawPathActive=$false
                VariantId='E_DXVK_SAFE'
                DxvkVersion='3.1.1'
                DevelopmentBranch='vr-dxvk-r71-disasm'
            }
        }
        default { throw "Unsupported backend: $Backend" }
    }
    $target|ConvertTo-Json -Depth 5|Set-Content (Join-Path $root 'VR_ONE_CLICK_TARGET.json') -Encoding UTF8
}

function Start-TonightTest([string]$Backend,[string]$Profile){
    try{
        if(!(Test-Path $gameExe -PathType Leaf)){
            throw "OR2006C2C.EXE not found. Extract this test package directly into the OutRun 2006 game folder, then run START_HERE_TONIGHT.cmd again."
        }
        if(!(Test-Path $selectScript -PathType Leaf)){throw "Select-OutRunVRBackend.ps1 missing."}
        if(!(Test-Path $runScript -PathType Leaf)){throw "Run-OutRunVRTest.ps1 missing."}

        $running=Get-Process -ErrorAction SilentlyContinue|Where-Object{
            $_.ProcessName -ieq 'OR2006C2C' -or $_.ProcessName -ieq 'outrun-vr-host'
        }
        if($running){throw 'OutRun or outrun-vr-host.exe is already running. Close it before starting another test.'}

        Write-Target $Backend
        & $selectScript -Backend $Backend -TestProfile $Profile -VariantId AUTO
        if($LASTEXITCODE -and $LASTEXITCODE -ne 0){throw "Backend selection failed with exit code $LASTEXITCODE"}

        $args=@(
            '-NoProfile','-ExecutionPolicy','Bypass',
            '-File',('"'+$runScript+'"'),
            '-TestProfile',$Profile
        )
        Start-Process powershell.exe -ArgumentList $args -WorkingDirectory $root
    }catch{
        Show-Error $_.Exception.Message
    }
}

$form=New-Object System.Windows.Forms.Form
$form.Text='OutRun 2006 VR - Tonight Test 2026-09-29'
$form.StartPosition='CenterScreen'
$form.ClientSize=[System.Drawing.Size]::new(760,430)
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false

$title=New-Object System.Windows.Forms.Label
$title.Text='OutRun VR Tonight Test'
$title.Font=New-Object System.Drawing.Font('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=[System.Drawing.Point]::new(24,20)
$form.Controls.Add($title)

$note=New-Object System.Windows.Forms.Label
$note.Text='Choose one backend. After the game exits, logs are collected automatically and an OutRun2_VR_ANALYZE_*.zip is created.'+[Environment]::NewLine+'DX11 is the current R97 branch: native draw routing is still dormant; this run gathers current branch/runtime evidence.'
$note.AutoSize=$false
$note.Size=[System.Drawing.Size]::new(710,62)
$note.Location=[System.Drawing.Point]::new(26,60)
$form.Controls.Add($note)

$profileLabel=New-Object System.Windows.Forms.Label
$profileLabel.Text='Profile'
$profileLabel.AutoSize=$true
$profileLabel.Location=[System.Drawing.Point]::new(28,135)
$form.Controls.Add($profileLabel)

$profileBox=New-Object System.Windows.Forms.ComboBox
$profileBox.DropDownStyle='DropDownList'
[void]$profileBox.Items.Add('CORRECTNESS')
[void]$profileBox.Items.Add('PERFORMANCE')
[void]$profileBox.Items.Add('CONTROL')
$profileBox.SelectedIndex=0
$profileBox.Location=[System.Drawing.Point]::new(90,131)
$profileBox.Size=[System.Drawing.Size]::new(170,28)
$form.Controls.Add($profileBox)

$buttons=@(
    @('DX9Ex Reference','d3d9','Protected reference/fallback. Use this first when a comparison baseline is needed.'),
    @('DX11 Current','dx11','Current vr-dx11-native-r71 branch. Native fixed-function draw path remains dormant; DirectGPU/census evidence is collected.'),
    @('DXVK SAFE','dxvk-safe','Pinned DXVK 3.1.1 SAFE two-pass path. Multiview remains disabled.')
)

$y=185
foreach($b in $buttons){
    $btn=New-Object System.Windows.Forms.Button
    $btn.Text=$b[0]
    $btn.Size=[System.Drawing.Size]::new(190,48)
    $btn.Location=[System.Drawing.Point]::new(28,$y)
    $backend=$b[1]
    $btn.Add_Click({
        Start-TonightTest $backend ([string]$profileBox.SelectedItem)
    }.GetNewClosure())
    $form.Controls.Add($btn)

    $desc=New-Object System.Windows.Forms.Label
    $desc.Text=$b[2]
    $desc.AutoSize=$false
    $desc.Size=[System.Drawing.Size]::new(500,48)
    $desc.Location=[System.Drawing.Point]::new(235,$y+3)
    $form.Controls.Add($desc)
    $y+=58
}

$openLogs=New-Object System.Windows.Forms.Button
$openLogs.Text='Open logs folder'
$openLogs.Size=[System.Drawing.Size]::new(140,32)
$openLogs.Location=[System.Drawing.Point]::new(28,372)
$openLogs.Add_Click({
    $logs=Join-Path $root 'logs'
    New-Item -ItemType Directory -Force $logs|Out-Null
    Start-Process explorer.exe -ArgumentList ('"'+$logs+'"')
})
$form.Controls.Add($openLogs)

$help=New-Object System.Windows.Forms.Label
$help.Text='Test loop: select -> play/reproduce -> exit game -> upload newest OutRun2_VR_ANALYZE_*.zip'
$help.AutoSize=$true
$help.Location=[System.Drawing.Point]::new(185,380)
$form.Controls.Add($help)

[void]$form.ShowDialog()
