Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'

$slots=[ordered]@{
    'R57_01_POSITION_KIND1_HUD35'=[ordered]@{
        Title='01. POSITION kind=1 only'
        Detail='6th/6 POSITION의 첫 sprani/SPRARGS2 요소만 정확히 SCREEN_HUD + 35% 처리. 움직이면 kind=1 경로 확정.'
    }
    'R57_02_POSITION_KIND0_HUD35'=[ordered]@{
        Title='02. POSITION kind=0 only'
        Detail='뒤 8개 put_clip_sprite/SPRARGS 요소만 SCREEN_HUD + 35%. 01과 서로 다른 구성요소를 분리 판별.'
    }
    'R57_03_POSITION_ALL_WORLD35'=[ordered]@{
        Title='03. POSITION complete fix'
        Detail='kind=1 + kind=0 전체를 exact SCREEN_HUD로 태그하고 35% finite world-plane 적용. POSITION 실제 수정 후보.'
    }
    'R57_04_RANK_ALL_AS_HUD'=[ordered]@{
        Title='04. VEHICLE RANK as HUD control'
        Detail='차량 위 1~6등을 일부러 SCREEN_HUD로 처리. 갈라짐/머리추종이 사라지면 최종 owner가 맞다는 음성 대조군.'
    }
    'R57_05_RANK_PROJECTED_IPD'=[ordered]@{
        Title='05. VEHICLE RANK projected-IPD'
        Detail='Calc3D2D 직전의 실제 view X/Y/Z를 보존하고 양안 IPD/FOV로 다시 투영. 가장 유력한 실제 해결 후보.'
    }
    'R57_06_RANK_PROJECTED_HEAD'=[ordered]@{
        Title='06. VEHICLE RANK + head inverse'
        Detail='05에 head inverse까지 추가. Calc3D2D 입력 카메라가 이미 head-sync 되었는지 05와 직접 판별.'
    }
    'R57_07_RANK 1-3 projected'
    =[ordered]@{
        Title='07. RANK 1-3 projected only'
        Detail='sprani/SPRARGS2인 1~3등만 새 projected-world-marker 경로. 4~6은 기존 경로 유지.'
    }
    'R57_08_RANK 4-6 projected'
    =[ordered]@{
        Title='08. RANK 4-6 projected only'
        Detail='put_clip_sprite/SPRARGS인 4~6등만 새 경로. 1~3과의 렌더 타입 차이를 직접 분리.'
    }
    'R57_09_RANK_PROJECTED_ZERO'=[ordered]@{
        Title='09. projected owner / zero'
        Detail='ProjectedWorldMarker semantic은 유지하되 양안 재투영을 끔. semantic 전달과 위치 수식을 분리 검증.'
    }
    'R57_10_RANK_PROJECTED_TRACE'=[ordered]@{
        Title='10. projected trace only'
        Detail='view X/Y/Z와 projected owner를 계측하되 화면 위치는 원본 유지. 로그만으로 producer→queue→draw 연결 확인.'
    }
}

# PowerShell ordered-hashtable key syntax cannot contain the display spacing aliases above.
$slots.Remove('R57_07_RANK 1-3 projected')
$slots.Remove('R57_08_RANK 4-6 projected')
$slots['R57_07_RANK_PROJECTED_13']=[ordered]@{
    Title='07. RANK 1-3 projected only'
    Detail='sprani/SPRARGS2인 1~3등만 새 projected-world-marker 경로. 4~6은 기존 경로 유지.'
}
$slots['R57_08_RANK_PROJECTED_46']=[ordered]@{
    Title='08. RANK 4-6 projected only'
    Detail='put_clip_sprite/SPRARGS인 4~6등만 새 경로. 1~3과의 렌더 타입 차이를 직접 분리.'
}

function Run-Test([string]$variant){
    & $selector -Backend d3d9 -TestProfile CORRECTNESS -VariantId $variant
    if($LASTEXITCODE -and $LASTEXITCODE -ne 0){throw "Failed to prepare $variant"}
    Start-Process powershell -ArgumentList @(
        '-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,
        '-TestProfile','CORRECTNESS'
    ) -WorkingDirectory $root
}

$form=New-Object System.Windows.Forms.Form
$form.Text='OutRun VR R57 - Orthogonal HUD / Rank Matrix'
$form.StartPosition='CenterScreen'
$form.ClientSize=[System.Drawing.Size]::new(980,710)
$form.MinimumSize=[System.Drawing.Size]::new(850,610)

$title=New-Object System.Windows.Forms.Label
$title.Text='OutRun VR R57 - 원인 분리 10개 테스트'
$title.Font=New-Object System.Drawing.Font(
    'Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=[System.Drawing.Point]::new(28,18)
$form.Controls.Add($title)

$guide=New-Object System.Windows.Forms.Label
$guide.Text='중복 기준선은 제거했습니다. 01~03은 6th/6 POSITION, 04~10은 차량 위 1~6등입니다. 우선 01→03, 그 다음 05→06을 테스트하면 됩니다. 07~10은 결과가 애매할 때 원인을 더 세분화합니다.'
$guide.AutoSize=$false
$guide.Size=[System.Drawing.Size]::new(910,48)
$guide.Location=[System.Drawing.Point]::new(30,58)
$form.Controls.Add($guide)

$panel=New-Object System.Windows.Forms.Panel
$panel.Location=[System.Drawing.Point]::new(20,112)
$panel.Size=[System.Drawing.Size]::new(940,520)
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
            [System.Windows.Forms.MessageBox]::Show(
                $_.Exception.Message,'실행 실패')|Out-Null
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
$status.Text='준비됨 - START_HERE_VR_TEST.cmd 하나만 실행'
$status.Font=New-Object System.Drawing.Font(
    'Segoe UI',10,[System.Drawing.FontStyle]::Bold)
$status.AutoSize=$true
$status.Location=[System.Drawing.Point]::new(30,660)
$status.Anchor='Bottom,Left'
$form.Controls.Add($status)

[void]$form.ShowDialog()
