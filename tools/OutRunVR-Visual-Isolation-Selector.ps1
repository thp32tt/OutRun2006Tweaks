Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'

$slots=[ordered]@{
    'V_BASE'=[ordered]@{
        Title='1. BASE'
        Detail='현재 DX9Ex 기준. production 화면 경로 그대로.'
    }
    'V_OVERLAY_BYPASS'=[ordered]@{
        Title='2. OVERLAY BYPASS'
        Detail='generic SCREEN_OVERLAY_2D의 R30 보정을 끄고 R29로 넘김. HUD/메뉴/2D 화면 깨짐 격리.'
    }
    'V_XYZRHW_WORLD_BYPASS'=[ordered]@{
        Title='3. XYZRHW WORLD BYPASS'
        Detail='CPU pre-transformed particle/decal/world XYZRHW 재투영만 끔. 연기/스키드/플레어/화면 조각 깨짐 격리.'
    }
    'V_HEAD_TRACKING_OFF'=[ordered]@{
        Title='4. HEAD TRACKING OFF'
        Detail='stereo transport는 유지하고 renderer head WVP injection만 끔. 머리 움직임 연동 왜곡 격리.'
    }
    'V_SKYGLOW_OFF'=[ordered]@{
        Title='5. SKY GLOW OFF'
        Detail='stereo sky-glow postprocess만 끔. 밝은 화면/플레어/후처리 깨짐 격리.'
    }
}

function Prepare([string]$variant){
    & $selector -Backend d3d9 -TestProfile CORRECTNESS -VariantId $variant
    if($LASTEXITCODE -and $LASTEXITCODE -ne 0){throw "Failed to prepare $variant"}
}
function Run-Test([string]$variant){
    Prepare $variant
    Start-Process powershell -ArgumentList @(
        '-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,'-TestProfile','CORRECTNESS'
    ) -WorkingDirectory $root
}

$form=New-Object System.Windows.Forms.Form
$form.Text='OutRun VR Visual Isolation Matrix'
$form.StartPosition='CenterScreen'
$form.ClientSize=New-Object System.Drawing.Size(700,560)
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false

$title=New-Object System.Windows.Forms.Label
$title.Text='OutRun VR 화면 오류 격리 테스트'
$title.Font=New-Object System.Drawing.Font('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=New-Object System.Drawing.Point(150,18)
$form.Controls.Add($title)

$guide=New-Object System.Windows.Forms.Label
$guide.Text='같은 코스/시점에서 1 -> 2 -> 3 -> 4 -> 5 순서로 테스트하세요. 각 버튼은 변수 하나만 바꿉니다. 게임 종료 후 로그 ZIP은 자동 생성됩니다.'
$guide.AutoSize=$false
$guide.Size=New-Object System.Drawing.Size(630,48)
$guide.Location=New-Object System.Drawing.Point(35,58)
$form.Controls.Add($guide)

$y=115
foreach($key in $slots.Keys){
    $cfg=$slots[$key]
    $button=New-Object System.Windows.Forms.Button
    $button.Text=$cfg.Title
    $button.Tag=$key
    $button.Size=New-Object System.Drawing.Size(210,54)
    $button.Location=New-Object System.Drawing.Point(35,$y)
    $button.Add_Click({
        try{
            Run-Test ([string]$this.Tag)
            $status.Text="실행: $($this.Tag)"
        }catch{
            [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'실행 실패')|Out-Null
        }
    })
    $form.Controls.Add($button)

    $label=New-Object System.Windows.Forms.Label
    $label.Text=$cfg.Detail
    $label.AutoSize=$false
    $label.Size=New-Object System.Drawing.Size(405,50)
    $label.Location=New-Object System.Drawing.Point(255,$y+3)
    $form.Controls.Add($label)
    $y+=68
}

$status=New-Object System.Windows.Forms.Label
$status.Text='준비됨'
$status.Font=New-Object System.Drawing.Font('Segoe UI',10,[System.Drawing.FontStyle]::Bold)
$status.AutoSize=$true
$status.Location=New-Object System.Drawing.Point(35,470)
$form.Controls.Add($status)

$bottom=New-Object System.Windows.Forms.Label
$bottom.Text='중요: 화면이 정상으로 바뀌는 최초 번호를 기억하세요. 해당 ZIP만 올려도 되지만 가능하면 1~5 ZIP을 모두 올리면 자동 비교합니다.'
$bottom.AutoSize=$false
$bottom.Size=New-Object System.Drawing.Size(630,48)
$bottom.Location=New-Object System.Drawing.Point(35,500)
$form.Controls.Add($bottom)

[void]$form.ShowDialog()
