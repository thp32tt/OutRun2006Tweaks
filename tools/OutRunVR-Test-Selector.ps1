Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'
$probe=Join-Path $root 'outrun-d3d9on12-probe.exe'

$slots=[ordered]@{
    'R57_01_POSITION_KIND1_HUD35'=@('01. POSITION kind=1 only','첫 sprani/SPRARGS2 요소만 SCREEN_HUD + 35%.')
    'R57_02_POSITION_KIND0_HUD35'=@('02. POSITION kind=0 only','뒤 8개 put_clip_sprite/SPRARGS만 SCREEN_HUD + 35%.')
    'R57_03_POSITION_ALL_WORLD35'=@('03. POSITION complete fix','kind=1+kind=0 전체 exact SCREEN_HUD + finite plane 35%.')
    'R57_04_RANK_ALL_AS_HUD'=@('04. VEHICLE RANK as HUD','차량 위 1~6등을 HUD로 강제해 최종 draw ownership 확인.')
    'R57_05_RANK_PROJECTED_IPD'=@('05. RANK projected-IPD','Calc3D2D view X/Y/Z 보존 후 eye IPD/FOV 재투영. 우선 테스트.')
    'R57_06_RANK_PROJECTED_HEAD'=@('06. RANK + head inverse','05에 head inverse까지 적용해 camera-space 가설 비교.')
    'R57_07_RANK_PROJECTED_13'=@('07. RANK 1-3 only','sprani/SPRARGS2 1~3등만 projected-world-marker.')
    'R57_08_RANK_PROJECTED_46'=@('08. RANK 4-6 only','put_clip_sprite/SPRARGS 4등 이후만 projected-world-marker.')
    'R57_09_RANK_PROJECTED_ZERO'=@('09. projected owner / zero','semantic은 유지하고 양안 위치 보정만 끔.')
    'R57_10_RANK_PROJECTED_TRACE'=@('10. projected trace only','깊이/양안 delta를 계산·기록하되 화면은 원본 유지.')
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
$form.Text='OutRun VR 2026-09-26 Nightly Unified Test'
$form.StartPosition='CenterScreen'
$form.ClientSize=[System.Drawing.Size]::new(1040,790)
$form.MinimumSize=[System.Drawing.Size]::new(920,680)

$title=New-Object System.Windows.Forms.Label
$title.Text='OutRun VR Nightly - R57 + DX9Ex / DX11 Host / DXVK / DX12'
$title.Font=New-Object System.Drawing.Font('Segoe UI',15,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=[System.Drawing.Point]::new(24,16)
$form.Controls.Add($title)

$guide=New-Object System.Windows.Forms.Label
$guide.Text='권장 순서: R57 03 → 05 → 06. 그 다음 같은 R57_05로 DX11 Host, DXVK SAFE, DXVK MULTIVIEW를 비교하세요. DX12는 먼저 D3D9On12 Probe PASS를 확인한 뒤 STRICT를 실행하세요.'
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
    @('DX9Ex + D3D11 Host','d3d9','R57_05_RANK_PROJECTED_IPD','기준. DirectGPU 실패 시 fallback 허용.'),
    @('DX11 Host DirectGPU','dx11','R57_05_RANK_PROJECTED_IPD','D3D9Ex 게임 + D3D11 OpenXR host. DirectGPU-only / ACK run identity.'),
    @('DXVK SAFE','dxvk-safe','R57_05_RANK_PROJECTED_IPD','DXVK provider-local Ex probe, multiview off, fallback 허용.'),
    @('DXVK MULTIVIEW','dxvk','R57_05_RANK_PROJECTED_IPD','DXVK + multiviewpatcher 실험 경로.'),
    @('DX12 STRICT','dx12','R57_05_RANK_PROJECTED_IPD','실험적 D3D9On12 기대 경로. Probe PASS 후 실행.')
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
$r57Box.Text='R57 HUD / 차량 순위 원인 분리'
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
