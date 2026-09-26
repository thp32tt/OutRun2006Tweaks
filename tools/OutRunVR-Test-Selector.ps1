Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'

$slots=[ordered]@{
    'R56_A_DISPRANK35'=[ordered]@{
        Title='1. A - POSITION DIRECT 35%'
        Detail='6th/6 POSITION의 EXE 8개 put_clip_sprite CALL을 직접 소유하고 해당 노드만 35% 축소. 일반 HUD 분류 우회.'
    }
    'R56_B_RANK_BASECAM'=[ordered]@{
        Title='2. B - RANK BASE CAMERA'
        Detail='차량 순위 Calc3D2D 순간에만 HMD culling camera를 원래 게임 카메라로 복원. 머리추종 원인 확인/수정.'
    }
    'R56_C_RANKCLIP35'=[ordered]@{
        Title='3. C - RANK BASE + 4PLUS 35%'
        Detail='B + 4등 이후 put_clip_sprite 숫자만 35% 축소. 1~3 sprani와 4+ clip 경로를 눈으로 분리.'
    }
    'R56_D_COMBINED'=[ordered]@{
        Title='4. D - COMBINED FIX'
        Detail='A+B 결합. 일반 HUD는 기존 world-fixed 0.55 유지, POSITION 직접 소유 + 차량 순위 base-camera projection.'
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
$guide.Text='이번에는 producer 자체를 분리합니다. A는 6th/6 POSITION, B는 차량순위 머리추종, C는 4등 이후 clip 숫자, D는 A+B 결합입니다. 같은 코스/시점에서 1→2→3→4 순서로 테스트하세요.'
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
