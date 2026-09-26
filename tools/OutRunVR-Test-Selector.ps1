Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'

$slots=[ordered]@{
    'R56_01_ZERO'=[ordered]@{ Title='01. BASE - ZERO DISPARITY'; Detail='R55-A 기준선. 일반 HUD를 좌/우 같은 원본 2D 좌표로 강제.' }
    'R56_02_SCALE35'=[ordered]@{ Title='02. BASE - ZERO + 35%'; Detail='R55-B 기준선. 일반 HUD가 35%로 줄어드는지 재확인.' }
    'R56_03_WORLD35'=[ordered]@{ Title='03. BASE - WORLD 35%'; Detail='R55-C 기준선. 일반 HUD finite world-plane/head lock 확인.' }
    'R56_04_RANKZERO'=[ordered]@{ Title='04. BASE - RANK ZERO'; Detail='R55-D 기준선. exact WORLD_BILLBOARD zero-disparity 재확인.' }

    'R56_05_POSITION_XP96'=[ordered]@{ Title='05. POSITION +96X'; Detail='DispRank 8개 원본 callsite의 X를 직접 +96. 6th/6가 움직이면 producer 확정.' }
    'R56_06_POSITION_XM96'=[ordered]@{ Title='06. POSITION -96X'; Detail='DispRank X를 직접 -96. 05와 반대 이동하면 6th/6 producer 강한 확증.' }
    'R56_07_POSITION_XS35'=[ordered]@{ Title='07. POSITION X 35%'; Detail='DispRank X만 화면 중앙 기준 35% 축소. 일반 HUD와 무관한 producer 크기/좌표 판별.' }
    'R56_08_POSITION_XCENTER'=[ordered]@{ Title='08. POSITION X CENTER'; Detail='DispRank X를 320에 강제. POSITION이 중앙으로 몰리면 정확한 경로.' }

    'R56_09_RANK13_XP96'=[ordered]@{ Title='09. RANK 1-3 +96X'; Detail='sub_4BAD20의 sprani 1~3등 producer를 직접 +96X.' }
    'R56_10_RANK13_XM96'=[ordered]@{ Title='10. RANK 1-3 -96X'; Detail='sprani 1~3등 producer를 직접 -96X. 09와 대칭 여부 확인.' }
    'R56_11_RANK13_YM72'=[ordered]@{ Title='11. RANK 1-3 -72Y'; Detail='sprani 1~3등을 위로 72. 화면 변화가 있으면 최종 visible producer 확인.' }
    'R56_12_RANK13_CENTER'=[ordered]@{ Title='12. RANK 1-3 CENTER'; Detail='sprani 1~3등 좌표를 320,208에 강제. producer 소유권 강한 시각 증명.' }

    'R56_13_RANK46_XP96'=[ordered]@{ Title='13. RANK 4-6 +96X'; Detail='sub_4BAD20의 put_clip_sprite 4등 이후 digit producer를 직접 +96X.' }
    'R56_14_RANK46_YM72'=[ordered]@{ Title='14. RANK 4-6 -72Y'; Detail='put_clip_sprite 4등 이후 digit producer를 직접 -72Y.' }
    'R56_15_RANK46_CENTER'=[ordered]@{ Title='15. RANK 4-6 CENTER'; Detail='4등 이후 digit 좌표를 320,208에 강제. 변화 없으면 다른 visible path 가능성.' }

    'R56_16_RANK13_AS_HUD'=[ordered]@{ Title='16. RANK 1-3 AS HUD'; Detail='1~3등 queue node를 WORLD_BILLBOARD 대신 SCREEN_HUD로 태그해 최종 semantic 전달 확인.' }
    'R56_17_RANK46_AS_HUD'=[ordered]@{ Title='17. RANK 4-6 AS HUD'; Detail='4등 이후 queue node를 SCREEN_HUD로 태그. 1~3과 semantic 수명 차이 비교.' }
    'R56_18_RANK46_NEXTDRAW'=[ordered]@{ Title='18. RANK 4-6 NEXT DRAW'; Detail='4등 이후 exact producer에서 다음 D3D draw에 WORLD_BILLBOARD one-shot 전달.' }
    'R56_19_POSITION_NEXTDRAW'=[ordered]@{ Title='19. POSITION NEXT DRAW'; Detail='DispRank exact callsite에서 다음 D3D draw에 SCREEN_HUD one-shot 전달.' }
    'R56_20_ALLSCREEN_RAW'=[ordered]@{ Title='20. ALL R30 SCREEN RAW'; Detail='R30이 소유한 모든 screen-space XYZRHW/shader를 좌우 동일 원본 좌표/WVP로 강제. 안 바뀌는 요소는 R30 밖.' }
}

function Run-Test([string]$variant){
    & $selector -Backend d3d9 -TestProfile CORRECTNESS -VariantId $variant
    if($LASTEXITCODE -and $LASTEXITCODE -ne 0){throw "Failed to prepare $variant"}
    Start-Process powershell -ArgumentList @(
        '-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,'-TestProfile','CORRECTNESS'
    ) -WorkingDirectory $root
}

$form=New-Object System.Windows.Forms.Form
$form.Text='OutRun VR R56 - 20 Probe Matrix'
$form.StartPosition='CenterScreen'
$form.ClientSize=[System.Drawing.Size]::new(980,760)
$form.MinimumSize=[System.Drawing.Size]::new(850,620)

$title=New-Object System.Windows.Forms.Label
$title.Text='OutRun VR R56 - 20개 HUD 경로 판별'
$title.Font=New-Object System.Drawing.Font('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=[System.Drawing.Point]::new(28,18)
$form.Controls.Add($title)

$guide=New-Object System.Windows.Forms.Label
$guide.Text='권장 순서: 01~04 기준선 → 05~08 POSITION → 09~12 차량 1~3등 → 13~18 차량 4~6등 → 19~20 최종 ownership. 같은 코스/시점에서 각 후보를 짧게 비교하세요.'
$guide.AutoSize=$false
$guide.Size=[System.Drawing.Size]::new(910,44)
$guide.Location=[System.Drawing.Point]::new(30,58)
$form.Controls.Add($guide)

$panel=New-Object System.Windows.Forms.Panel
$panel.Location=[System.Drawing.Point]::new(20,108)
$panel.Size=[System.Drawing.Size]::new(940,590)
$panel.Anchor='Top,Bottom,Left,Right'
$panel.AutoScroll=$true
$form.Controls.Add($panel)

$y=8
foreach($key in $slots.Keys){
    $cfg=$slots[$key]

    $button=New-Object System.Windows.Forms.Button
    $button.Text=$cfg.Title
    $button.Tag=$key
    $button.Size=[System.Drawing.Size]::new(300,48)
    $button.Location=[System.Drawing.Point]::new(10,$y)
    $button.Add_Click({
        try{
            Run-Test ([string]$this.Tag)
            $status.Text="실행: $($this.Tag)"
        }catch{
            [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'실행 실패')|Out-Null
        }
    })
    $panel.Controls.Add($button)

    $label=New-Object System.Windows.Forms.Label
    $label.Text=$cfg.Detail
    $label.AutoSize=$false
    $label.Size=[System.Drawing.Size]::new(585,44)
    $label.Location=[System.Drawing.Point]::new(325,($y+3))
    $panel.Controls.Add($label)

    $y+=56
}

$status=New-Object System.Windows.Forms.Label
$status.Text='준비됨 - START_HERE_VR_TEST.cmd 하나만 실행하면 됩니다.'
$status.Font=New-Object System.Drawing.Font('Segoe UI',10,[System.Drawing.FontStyle]::Bold)
$status.AutoSize=$true
$status.Location=[System.Drawing.Point]::new(30,715)
$status.Anchor='Bottom,Left'
$form.Controls.Add($status)

[void]$form.ShowDialog()
