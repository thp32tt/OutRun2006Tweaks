Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$launcher=Join-Path $root 'Invoke-OutRunVROneClick.ps1'
if(!(Test-Path $launcher -PathType Leaf)){throw "One-click launcher missing: $launcher"}

# Preserve the HMD-proven R57 selector contract as diagnostic metadata.
# The evening UI below intentionally launches the current branch target/variant,
# but these identities remain visible to baseline verification and manual fallback.
$provenBackendBaseline=@(
    @('DX9Ex + D3D11 Host','d3d9','R57_06_RANK_PROJECTED_HEAD'),
    @('DX11 Host DirectGPU','dx11','R57_06_RANK_PROJECTED_HEAD'),
    @('DXVK SAFE','dxvk-safe','R57_06_RANK_PROJECTED_HEAD')
)
$provenDiagnosticSlots=[ordered]@{
    'R57_05_RANK_PROJECTED_IPD'=@('comparison','projected-IPD diagnostic')
    'R57_06_RANK_PROJECTED_HEAD'=@('proven-default','head-inverse projected rank')
}

$form=New-Object System.Windows.Forms.Form
$form.Text='OutRun 2006 VR - Tonight Test Selector'
$form.StartPosition='CenterScreen'
$form.ClientSize=[System.Drawing.Size]::new(760,470)
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false

$title=New-Object System.Windows.Forms.Label
$title.Text='OutRun 2006 VR - 테스트 실행 선택'
$title.Font=New-Object System.Drawing.Font('Segoe UI',15,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=[System.Drawing.Point]::new(24,20)
$form.Controls.Add($title)

$info=New-Object System.Windows.Forms.Label
$info.Text="START_HERE에서 선택한 모드로 preflight 검증 후 실행합니다.
게임 종료 후 로그를 자동 수집/분석하고 OutRun2_VR_ANALYZE_*.zip을 생성합니다."
$info.AutoSize=$false
$info.Size=[System.Drawing.Size]::new(710,52)
$info.Location=[System.Drawing.Point]::new(26,58)
$form.Controls.Add($info)

$backendLabel=New-Object System.Windows.Forms.Label
$backendLabel.Text='백엔드'
$backendLabel.Location=[System.Drawing.Point]::new(28,124)
$backendLabel.AutoSize=$true
$form.Controls.Add($backendLabel)

$backend=New-Object System.Windows.Forms.ComboBox
$backend.DropDownStyle='DropDownList'
$backend.Location=[System.Drawing.Point]::new(28,148)
$backend.Size=[System.Drawing.Size]::new(330,30)
[void]$backend.Items.Add('DXVK SAFE - 오늘 밤 기본 테스트')
[void]$backend.Items.Add('DX11 - 관찰/센서스 (native draw 비활성)')
[void]$backend.Items.Add('D3D9Ex - 검증 기준 비교')
[void]$backend.Items.Add('2D - VR 비활성 대조')
$backend.SelectedIndex=0
$form.Controls.Add($backend)

$profileLabel=New-Object System.Windows.Forms.Label
$profileLabel.Text='테스트 프로필'
$profileLabel.Location=[System.Drawing.Point]::new(390,124)
$profileLabel.AutoSize=$true
$form.Controls.Add($profileLabel)

$profile=New-Object System.Windows.Forms.ComboBox
$profile.DropDownStyle='DropDownList'
$profile.Location=[System.Drawing.Point]::new(390,148)
$profile.Size=[System.Drawing.Size]::new(330,30)
[void]$profile.Items.Add('CORRECTNESS - 화면/HUD/렌즈플레어 우선')
[void]$profile.Items.Add('PERFORMANCE - 프레임/대기/복사 측정')
[void]$profile.Items.Add('STAGE_DIAGNOSTIC - 스테이지 전환 진단')
$profile.SelectedIndex=0
$form.Controls.Add($profile)

$notes=New-Object System.Windows.Forms.TextBox
$notes.Multiline=$true
$notes.ReadOnly=$true
$notes.ScrollBars='Vertical'
$notes.Location=[System.Drawing.Point]::new(28,200)
$notes.Size=[System.Drawing.Size]::new(692,150)
$notes.Text=@"
권장 순서
1) DXVK SAFE + CORRECTNESS
2) 문제가 있으면 D3D9Ex + CORRECTNESS 비교
3) 성능 확인은 DXVK SAFE + PERFORMANCE

DX11은 현재 native draw가 아직 활성화되지 않은 관찰 단계이므로
정상 동작 확정용이 아니라 DX11 센서스/로그 확보용입니다.

실행 중 생성되는 기존 로그는 세션별로 분리되고,
게임 종료 후 자동 분석 결과와 원본 로그가 ZIP 하나로 묶입니다.
"@
$form.Controls.Add($notes)

$run=New-Object System.Windows.Forms.Button
$run.Text='선택한 설정으로 실행'
$run.Size=[System.Drawing.Size]::new(220,46)
$run.Location=[System.Drawing.Point]::new(500,378)
$run.DialogResult=[System.Windows.Forms.DialogResult]::OK
$form.AcceptButton=$run
$form.Controls.Add($run)

$cancel=New-Object System.Windows.Forms.Button
$cancel.Text='취소'
$cancel.Size=[System.Drawing.Size]::new(100,46)
$cancel.Location=[System.Drawing.Point]::new(382,378)
$cancel.DialogResult=[System.Windows.Forms.DialogResult]::Cancel
$form.CancelButton=$cancel
$form.Controls.Add($cancel)

$result=$form.ShowDialog()
if($result -ne [System.Windows.Forms.DialogResult]::OK){exit 2}

$backendValue=switch($backend.SelectedIndex){
    0 {'dxvk-safe'}
    1 {'dx11'}
    2 {'d3d9'}
    3 {'2d'}
    default {throw 'Invalid backend selection.'}
}
$profileValue=switch($profile.SelectedIndex){
    0 {'CORRECTNESS'}
    1 {'PERFORMANCE'}
    2 {'STAGE_DIAGNOSTIC'}
    default {throw 'Invalid test profile selection.'}
}

Write-Host "Selected backend=$backendValue profile=$profileValue"
& $launcher -Backend $backendValue -TestProfile $profileValue -VariantId AUTO -AllowTargetOverride
exit $LASTEXITCODE
