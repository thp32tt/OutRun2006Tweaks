Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'

$slots=[ordered]@{
    'X_COMBINED'=[ordered]@{
        Title='1. COMBINED FIX (먼저 테스트)'
        Detail='cross-thread semantic 보존 + SCREEN_HUD + WORLD_RANK를 함께 적용. 화면 HUD와 차량 순위 마커의 실제 수정 후보.'
    }
    'X_SCREEN_HUD'=[ordered]@{
        Title='2. SCREEN HUD ONLY'
        Detail='DispRank/TimeAttack/REV 등 확인된 화면 HUD만 정확한 SCREEN_HUD로 처리. 고정 HUD/리사이즈 확인용.'
    }
    'X_WORLD_RANK'=[ordered]@{
        Title='3. WORLD RANK ONLY'
        Detail='1~5등 차량 위 마커의 WORLD_BILLBOARD semantic만 적용. 특히 4/5등 위치/머리추종 확인용.'
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
$form.ClientSize=[System.Drawing.Size]::new(720,390)
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false

$title=New-Object System.Windows.Forms.Label
$title.Text='OutRun VR 테스트 셀렉터'
$title.Font=New-Object System.Drawing.Font('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=[System.Drawing.Point]::new(155,18)
$form.Controls.Add($title)

$guide=New-Object System.Windows.Forms.Label
$guide.Text='먼저 1번 COMBINED FIX를 테스트하세요. 남은 문제가 있으면 2/3번으로 원인을 분리합니다. F11 > Configure Input Bindings에서 VR Recenter도 원하는 휠/키에 지정해 메뉴와 게임에서 모두 확인하세요.'
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
$status.Location=[System.Drawing.Point]::new(35,340)
$form.Controls.Add($status)

[void]$form.ShowDialog()
