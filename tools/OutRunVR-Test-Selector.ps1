Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'

$slots=[ordered]@{
    'R55_A_ZERO'=[ordered]@{
        Title='1. A - ZERO DISPARITY'
        Detail='화면 HUD를 좌/우 완전히 같은 2D 좌표로 강제. 갈라짐이 사라지는지 확인.'
    }
    'R55_B_SCALE35'=[ordered]@{
        Title='2. B - ZERO + 35% SCALE'
        Detail='A와 같은 zero-disparity에 화면 HUD를 35%로 강제 축소. 경로가 보이면 크기가 확실히 달라져야 함.'
    }
    'R55_C_WORLD35'=[ordered]@{
        Title='3. C - WORLD PLANE 35%'
        Detail='HUD를 35% finite world-plane + head inverse로 배치. 머리 추종 제거 실제 후보.'
    }
    'R55_D_RANKZERO'=[ordered]@{
        Title='4. D - WORLD HUD + RANK ZERO'
        Detail='C + 차량 위 exact WORLD_BILLBOARD를 좌/우 같은 좌표로 강제. 특히 4/5등 마커 경로 확인.'
    }
}

function Run-Test([string]$variant){
    & $selector -Backend d3d9 -TestProfile CORRECTNESS -VariantId $variant
    if($LASTEXITCODE -and $LASTEXITCODE -ne 0){throw "Failed to prepare $variant"}
    Start-Process powershell -ArgumentList @(
        '-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,'-TestProfile','CORRECTNESS'
    ) -WorkingDirectory $root
}

$form=New-Object System.Windows.Forms.Form
$form.Text='OutRun VR Test Selector'
$form.StartPosition='CenterScreen'
$form.ClientSize=[System.Drawing.Size]::new(720,440)
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false

$title=New-Object System.Windows.Forms.Label
$title.Text='OutRun VR 테스트 셀렉터'
$title.Font=New-Object System.Drawing.Font('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=[System.Drawing.Point]::new(155,18)
$form.Controls.Add($title)

$guide=New-Object System.Windows.Forms.Label
$guide.Text='같은 코스/시점에서 1→2→3→4 순서로 짧게 테스트하세요. 이번 네 모드는 최종 좌표 수식 자체가 서로 다릅니다. 특히 2번은 HUD가 35%로 줄지 않으면 보이는 HUD가 이 경로가 아닙니다.'
$guide.AutoSize=$false
$guide.Size=[System.Drawing.Size]::new(650,44)
$guide.Location=[System.Drawing.Point]::new(35,58)
$form.Controls.Add($guide)

$y=112
foreach($key in $slots.Keys){
    $cfg=$slots[$key]
    $button=New-Object System.Windows.Forms.Button
    $button.Text=$cfg.Title
    $button.Tag=$key
    $button.Size=[System.Drawing.Size]::new(260,54)
    $button.Location=[System.Drawing.Point]::new(35,$y)
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
    $label.Size=[System.Drawing.Size]::new(385,50)
    $label.Location=[System.Drawing.Point]::new(305,($y+3))
    $form.Controls.Add($label)
    $y+=66
}

$status=New-Object System.Windows.Forms.Label
$status.Text='준비됨'
$status.Font=New-Object System.Drawing.Font('Segoe UI',10,[System.Drawing.FontStyle]::Bold)
$status.AutoSize=$true
$status.Location=[System.Drawing.Point]::new(35,390)
$form.Controls.Add($status)

[void]$form.ShowDialog()
