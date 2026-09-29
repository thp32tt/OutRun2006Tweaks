Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'

function Invoke-R71Test([string]$profile,[string]$variant){
    try {
        & $selector -Backend d3d9 -TestProfile $profile -VariantId $variant
        if($LASTEXITCODE -and $LASTEXITCODE -ne 0){
            throw "Failed to prepare DX9Ex / $variant / $profile"
        }
        $form.Hide()
        & powershell -NoProfile -ExecutionPolicy Bypass -File $runner -TestProfile $profile
        if($LASTEXITCODE -and $LASTEXITCODE -ne 0){
            throw "VR test runner exited with code $LASTEXITCODE"
        }
        [System.Windows.Forms.MessageBox]::Show(
            "테스트와 로그 수집이 완료되었습니다. 패키지 폴더의 최신 OutRun2_VR_ANALYZE_*.zip 만 업로드하면 됩니다.",
            "OutRun VR R71"
        ) | Out-Null
        $form.Close()
    } catch {
        $form.Show()
        [System.Windows.Forms.MessageBox]::Show(
            $_.Exception.Message,
            "OutRun VR R71 - 테스트 실패",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    }
}

$form=New-Object System.Windows.Forms.Form
$form.Text='OutRun VR R71 - HUD / Lens Flare Evening Test'
$form.StartPosition='CenterScreen'
$form.ClientSize=[System.Drawing.Size]::new(820,520)
$form.MinimumSize=[System.Drawing.Size]::new(820,520)
$form.MaximizeBox=$false

$title=New-Object System.Windows.Forms.Label
$title.Text='OutRun 2006 VR R71 - HUD / Lens Flare Test'
$title.Font=New-Object System.Drawing.Font('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=[System.Drawing.Point]::new(24,20)
$form.Controls.Add($title)

$summary=New-Object System.Windows.Forms.Label
$summary.Text=@'
오늘 밤 확인 대상
• HUD / 메뉴 / YES-NO / 6th/6 및 OutRun 체크포인트·결과 화면의 2중 출력·헤드락
• Lens flare 2중 출력: exact projected-screen owner + L/R mono fusion
• Rival rank marker: queue node에 vehicle-relative projected anchor 유지
• SkyGlow: HUD가 그려지기 전에 합성해 HUD/메뉴가 희거나 반투명해지는 회귀 방지
• 보호 항목: 도로/배경/차량 3D stereo, stage-transition 개선, recenter
'@
$summary.AutoSize=$false
$summary.Size=[System.Drawing.Size]::new(760,180)
$summary.Location=[System.Drawing.Point]::new(28,70)
$form.Controls.Add($summary)

$full=New-Object System.Windows.Forms.Button
$full.Text='1. R71 전체 테스트 (권장)'
$full.Font=New-Object System.Drawing.Font('Segoe UI',12,[System.Drawing.FontStyle]::Bold)
$full.Size=[System.Drawing.Size]::new(350,70)
$full.Location=[System.Drawing.Point]::new(28,270)
$full.Add_Click({ Invoke-R71Test 'CORRECTNESS' 'R71_HUD_FLARE' })
$form.Controls.Add($full)

$quick=New-Object System.Windows.Forms.Button
$quick.Text='2. HUD / 메뉴 빠른 테스트'
$quick.Font=New-Object System.Drawing.Font('Segoe UI',12,[System.Drawing.FontStyle]::Regular)
$quick.Size=[System.Drawing.Size]::new(350,70)
$quick.Location=[System.Drawing.Point]::new(410,270)
$quick.Add_Click({ Invoke-R71Test 'HUD_MENU' 'R71_HUD_MENU' })
$form.Controls.Add($quick)

$guide=New-Object System.Windows.Forms.Label
$guide.Text=@'
사용 방법
1) 가능하면 "R71 전체 테스트"를 실행
2) 게임을 정상 종료하면 host 종료 → 로그 수집 → 자동 분석 → ZIP 생성까지 자동 수행
3) 최신 OutRun2_VR_ANALYZE_*.zip 하나만 프로젝트 채팅에 업로드
HUD가 여전히 반투명하면 이번 빌드의 bounded alpha/blend 진단 로그로 다음 수정 대상을 바로 좁힐 수 있습니다.
'@
$guide.AutoSize=$false
$guide.Size=[System.Drawing.Size]::new(760,120)
$guide.Location=[System.Drawing.Point]::new(28,370)
$form.Controls.Add($guide)

[void]$form.ShowDialog()
