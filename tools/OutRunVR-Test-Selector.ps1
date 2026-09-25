Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'

$slots=[ordered]@{
    'R54_A_NEXTDRAW'=[ordered]@{
        Title='1. A - NEXT DRAW LATCH'
        Detail='queue exact semantic을 다음 D3D draw에 1회 직접 전달. 가장 좁은 수정.'
    }
    'R54_B_STICKY'=[ordered]@{
        Title='2. B - STICKY NODE'
        Detail='현재 SpriteNode가 끝날 때까지 exact SCREEN_HUD/WORLD_RANK를 유지. multi-draw node 대응.'
    }
    'R54_C_FULL_OWNER'=[ordered]@{
        Title='3. C - FULL OWNER'
        Detail='sticky semantic + c64/WVP 단계에서도 exact queue semantic을 강제 복구. 가장 유력한 수정.'
    }
    'R54_D_HUD_PLANE'=[ordered]@{
        Title='4. D - HUD PLANE FORCE'
        Detail='C 방식 + generic queue HUD까지 finite HUD plane으로 승격. 화면 HUD 크기/머리추종 분리 확인.'
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
$guide.Text='같은 코스/시점에서 1→2→3→4 순서로 짧게 테스트하세요. 화면 변화가 생기는 첫 버전이 핵심입니다. F11 VR Recenter도 메뉴/게임에서 같이 확인하세요.
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
