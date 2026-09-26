Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'
$probe=Join-Path $root 'outrun-d3d9on12-probe.exe'

$slots=[ordered]@{
    'R58_01_CONFIRMED_13_HEAD'=@('01. 1-3 CONFIRMED HEAD','R57-06에서 성공한 1~3등 head-inverse 재투영만 유지.')
    'R58_02_BAD20_46_DIRECT_HEAD'=@('02. BAD20 4+ DIRECT','4등 이후 digit 최종 SpriteNode를 BAEE2 anchor에 직접 연결.')
    'R58_03_SIBLING_BB3_HEAD'=@('03. SIBLING BB3','BB3D6 Calc3D2D → BB550 sprite 계열만 추가 추적.')
    'R58_04_SIBLING_BB6_HEAD'=@('04. SIBLING BB6','BB6F0 Calc3D2D → BB796 sprite 계열만 추가 추적.')
    'R58_05_SIBLING_BBB_HEAD'=@('05. SIBLING BBB','BBB85 Calc3D2D → BBC5A sprite 계열만 추가 추적.')
    'R58_06_SIBLING_BBD_HEAD'=@('06. SIBLING BBD','BBDC5 Calc3D2D → BC2E5/BC346 sprite 계열만 추가 추적.')
    'R58_07_ALL_PROJECTED_HEAD'=@('07. ALL PROJECTED','1~3 + BAD20 4+ + sibling 전체를 head-inverse 방식으로 통합.')
    'R58_08_POSITION_SUPPRESS'=@('08. POSITION SUPPRESS','DispRank로 추정한 9개 producer를 제거. 6th/6가 남으면 다른 owner.')
    'R58_09_POSITION_DIRECT_HUD'=@('09. POSITION DIRECT HUD','DispRank가 만든 최종 node를 직접 SCREEN_HUD로 등록, HudScale 사용.')
    'R58_10_POSITION_DIRECT_HUD35'=@('10. POSITION DIRECT 35%','09와 동일하되 35% 강제. 6th/6 ownership을 눈으로 확정.')
}

function Start-VRTest([string]$backend,[string]$variant){
    & $selector -Backend $backend -TestProfile CORRECTNESS -VariantId $variant
    if($LASTEXITCODE -and $LASTEXITCODE -ne 0){throw "Failed to prepare $backend / $variant"}
    Start-Process powershell -ArgumentList @(
        '-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,
        '-TestProfile','CORRECTNESS'
    ) -WorkingDirectory $root
}

$form=New-Object System.Windows.Forms.Form
$form.Text='OutRun VR R58 HUD / Rank Root-Cause Test'
$form.StartPosition='CenterScreen'
$form.ClientSize=[System.Drawing.Size]::new(1040,790)
$form.MinimumSize=[System.Drawing.Size]::new(920,680)

$title=New-Object System.Windows.Forms.Label
$title.Text='OutRun VR R58 - HMD evidence-driven HUD / rival rank isolation'
$title.Font=New-Object System.Drawing.Font('Segoe UI',15,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=[System.Drawing.Point]::new(24,16)
$form.Controls.Add($title)

$guide=New-Object System.Windows.Forms.Label
$guide.Text='권장 순서: 01 → 02 → 08 → 10. 02가 4~6등에 안 먹으면 03~06을 확인하고, 맞는 family가 나오면 07로 통합 확인하세요.'
$guide.AutoSize=$false
$guide.Size=[System.Drawing.Size]::new(990,48)
$guide.Location=[System.Drawing.Point]::new(26,54)
$form.Controls.Add($guide)

$backendBox=New-Object System.Windows.Forms.GroupBox
$backendBox.Text='통합 Renderer / Transport 비교'
$backendBox.Location=[System.Drawing.Point]::new(22,108)
$backendBox.Size=[System.Drawing.Size]::new(990,150)
$form.Controls.Add($backendBox)

$backendButtons=@(
    @('DX9Ex + D3D11 Host','d3d9','R58_07_ALL_PROJECTED_HEAD','기준. DirectGPU 실패 시 fallback 허용.'),
    @('DX11 Host DirectGPU','dx11','R58_07_ALL_PROJECTED_HEAD','D3D9Ex 게임 + D3D11 OpenXR host. DirectGPU-only / ACK run identity.'),
    @('DXVK SAFE','dxvk-safe','R58_07_ALL_PROJECTED_HEAD','DXVK provider-local Ex probe, multiview off, fallback 허용.'),
    @('DXVK MULTIVIEW','dxvk','R58_07_ALL_PROJECTED_HEAD','DXVK + multiviewpatcher 실험 경로.'),
    @('DX12 STRICT','dx12','R58_07_ALL_PROJECTED_HEAD','실험적 D3D9On12 기대 경로. Probe PASS 후 실행.')
)
$x=14
foreach($b in $backendButtons){
    $btn=New-Object System.Windows.Forms.Button
    $btn.Text=$b[0]
    $btn.Size=[System.Drawing.Size]::new(184,45)
    $btn.Location=[System.Drawing.Point]::new($x,28)
    $backend=$b[1]; $variant=$b[2]
    $btn.Add_Click({ Start-VRTest $backend $variant }.GetNewClosure())
    $backendBox.Controls.Add($btn)
    $tip=New-Object System.Windows.Forms.ToolTip
    $tip.SetToolTip($btn,$b[3])
    $x+=192
}

$probeBtn=New-Object System.Windows.Forms.Button
$probeBtn.Text='DX12 D3D9On12 PROBE'
$probeBtn.Size=[System.Drawing.Size]::new(220,38)
$probeBtn.Location=[System.Drawing.Point]::new(14,86)
$probeBtn.Add_Click({
    if(!(Test-Path $probe)){[System.Windows.Forms.MessageBox]::Show('outrun-d3d9on12-probe.exe가 없습니다.','DX12 Probe');return}
    Start-Process cmd -ArgumentList @('/k',('"' + $probe + '"')) -WorkingDirectory $root
})
$backendBox.Controls.Add($probeBtn)

$note=New-Object System.Windows.Forms.Label
$note.Text='DX12 Probe 결과에서 d3d9on12_bridge / legacy_create_device / resource_interop / legacy_reset / DX12_POC_RESULT 가 모두 PASS여야 합니다.'
$note.AutoSize=$false
$note.Size=[System.Drawing.Size]::new(735,40)
$note.Location=[System.Drawing.Point]::new(248,86)
$backendBox.Controls.Add($note)

$r57Box=New-Object System.Windows.Forms.GroupBox
$r57Box.Text='R58 HUD / 차량 순위 원인 분리'
$r57Box.Location=[System.Drawing.Point]::new(22,270)
$r57Box.Size=[System.Drawing.Size]::new(990,485)
$r57Box.Anchor='Top,Bottom,Left,Right'
$form.Controls.Add($r57Box)

$panel=New-Object System.Windows.Forms.Panel
$panel.Location=[System.Drawing.Point]::new(10,22)
$panel.Size=[System.Drawing.Size]::new(970,450)
$panel.Anchor='Top,Bottom,Left,Right'
$panel.AutoScroll=$true
$r57Box.Controls.Add($panel)

$y=8
foreach($id in $slots.Keys){
    $row=New-Object System.Windows.Forms.Panel
    $row.Location=[System.Drawing.Point]::new(8,$y)
    $row.Size=[System.Drawing.Size]::new(925,62)

    $btn=New-Object System.Windows.Forms.Button
    $btn.Text=$slots[$id][0]
    $btn.Size=[System.Drawing.Size]::new(260,48)
    $btn.Location=[System.Drawing.Point]::new(0,4)
    $variant=$id
    $btn.Add_Click({ Start-VRTest 'd3d9' $variant }.GetNewClosure())
    $row.Controls.Add($btn)

    $desc=New-Object System.Windows.Forms.Label
    $desc.Text=$slots[$id][1]
    $desc.AutoSize=$false
    $desc.Size=[System.Drawing.Size]::new(640,48)
    $desc.Location=[System.Drawing.Point]::new(275,7)
    $row.Controls.Add($desc)

    $panel.Controls.Add($row)
    $y+=66
}

[void]$form.ShowDialog()
