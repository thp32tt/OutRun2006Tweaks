Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'

$slots=[ordered]@{
    'X_BASE'=[ordered]@{
        Title='1. BASE (EXE semantic OFF)'
        Detail='현재 production semantic ownership 그대로. 비교 기준.'
    }
    'X_SCREEN_HUD'=[ordered]@{
        Title='2. SCREEN_HUD from EXE map'
        Detail='DispRank/TimeAttack/REV 등 확인된 screen HUD RVA만 SCREEN_HUD로 태깅.'
    }
    'X_WORLD_RANK'=[ordered]@{
        Title='3. WORLD_RANK from EXE map'
        Detail='sub_4BAD20 / WORLD_RIVAL_MARKER처럼 확인된 world billboard RVA만 태깅.'
    }
    'X_COMBINED'=[ordered]@{
        Title='4. COMBINED'
        Detail='확인된 SCREEN_HUD + WORLD_BILLBOARD semantic을 동시에 적용.'
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
$form.ClientSize=[System.Drawing.Size]::new(720,430)
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false

$title=New-Object System.Windows.Forms.Label
$title.Text='OutRun VR 테스트 셀렉터'
$title.Font=New-Object System.Drawing.Font('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=[System.Drawing.Point]::new(155,18)
$form.Controls.Add($title)

$guide=New-Object System.Windows.Forms.Label
$guide.Text='같은 코스/같은 시점에서 1→2→3→4 순서로 실행하세요. canonical EXE SHA-256이 맞을 때만 RVA semantic이 활성화됩니다.'
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
$status.Location=[System.Drawing.Point]::new(35,382)
$form.Controls.Add($status)

[void]$form.ShowDialog()
