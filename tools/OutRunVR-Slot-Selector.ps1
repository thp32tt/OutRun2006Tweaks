Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'

$slots=[ordered]@{
    'A_SEAT_STOCK'=[ordered]@{Backend='d3d9';Profile='COCKPIT_PARTICLES';Variant='G_COCKPIT';Scale='1.00';Title='A 운전석 기본 크기 100%';Help='운전석 ON, 전체 차체 1.00x / 위치는 F11에서 조절.'}
    'B_SEAT_115'=[ordered]@{Backend='d3d9';Profile='COCKPIT_PARTICLES';Variant='G_COCKPIT';Scale='1.15';Title='B 운전석 차량 115%';Help='운전석 ON, 전체 차체 1.15x / 이전 실험 기본 배율.'}
    'C_SEAT_130'=[ordered]@{Backend='d3d9';Profile='COCKPIT_PARTICLES';Variant='G_COCKPIT';Scale='1.30';Title='C 운전석 차량 130%';Help='운전석 ON, 전체 차체 1.30x / 시야 가림 및 위치 확인.'}
    'CURRENT_FOCUS'=[ordered]@{Backend='d3d9';Profile='CORRECTNESS';Title='MAIN R84 / R29-R33';Help='기본 구조 개선 렌더러. Quest3 검증 필요.'}
    'R26_SAFE'=[ordered]@{Backend='d3d9';Profile='CORRECTNESS';Title='R26 SAFE / 기존 보호판';Help='기존 R26+HUD 렌더러 복귀. CURRENT FOCUS로 R84 재선택.'}
    'R84_TEST'=[ordered]@{Backend='d3d9';Profile='CORRECTNESS';Title='R84 TEST / 개편 경로';Help='기본 R84와 동일한 독립 렌더러 A/B 진단.'}
    'A_CONTROL'=[ordered]@{Backend='d3d9';Profile='CONTROL';Title='A CONTROL / R51 기준';Help='R51 보호 기준 비교.'}
    'B_HUD'=[ordered]@{Backend='d3d9';Profile='HUD_SCREEN';Title='B HUD';Help='6th/6, YES/NO, 시간/랭크 HUD 확인.'}
    'C_FLARE'=[ordered]@{Backend='d3d9';Profile='HUD_WORLD';Title='C FLARE / WORLD';Help='렌즈 플레어/월드 마커 producer 진단.'}
    'D_PERF'=[ordered]@{Backend='d3d9';Profile='PERFORMANCE';Title='D PERFORMANCE';Help='프레임 페이싱/fence telemetry.'}
    'G_COCKPIT'=[ordered]@{Backend='d3d9';Profile='COCKPIT_PARTICLES';Title='G COCKPIT + PARTICLES (실험)';Help='운전석/전체 차량/운전자 가림과 검증된 WorldParticle 양안 업로드 시험. 유리 PMT 교체는 포함하지 않음.'}
    'E_DXVK_SAFE'=[ordered]@{Backend='dxvk-safe';Profile='CORRECTNESS';Title='E DXVK SAFE (진단)';Help='현재 SBS/DesktopDup fallback 재현용. 성능 기준으로 사용 금지.'}
}

function Get-Active {
    $r=@{backend='unknown';variant='unknown';profile='unknown'}
    $p=Join-Path $root 'ACTIVE_VR_BACKEND.txt'
    if(Test-Path $p){
        Get-Content $p|ForEach-Object{
            if($_ -match '^([^=]+)=(.*)$'){$r[$matches[1]]=$matches[2].Trim()}
        }
    }
    return $r
}

function Prepare-Slot([string]$slot){
    if(!$slots.Contains($slot)){throw "Unknown slot: $slot"}
    $cfg=$slots[$slot]
    $actualVariant=if($cfg.Contains('Variant')){[string]$cfg.Variant}else{$slot}
    $sessionPath=Join-Path $root 'CURRENT_VR_SESSION.json'
    # A previous successful test can leave this file behind. Its existence
    # is not evidence that the selector actually prepared this launch.
    $previousSessionId=$null
    if(Test-Path -LiteralPath $sessionPath){
        try{
            $previousSessionId=[string]((Get-Content -LiteralPath $sessionPath -Raw -ErrorAction Stop |
                ConvertFrom-Json -ErrorAction Stop).SessionId)
        }catch{
            $previousSessionId=$null
        }
    }
    # Direct invocation preserves spaces and propagates backend/PE/hash errors.
    & $selector -Backend $cfg.Backend -TestProfile $cfg.Profile -VariantId $actualVariant
    if(-not (Test-Path -LiteralPath $sessionPath)){
        throw "Slot preparation did not create a session: $slot"
    }
    try{
        $session=Get-Content -LiteralPath $sessionPath -Raw -ErrorAction Stop |
            ConvertFrom-Json -ErrorAction Stop
    }catch{
        throw "Slot preparation produced an unreadable session for $slot : $($_.Exception.Message)"
    }
    if(-not $session.SessionId -or
        ($previousSessionId -and $session.SessionId -eq $previousSessionId)){
        throw "Slot preparation reused a stale session for $slot"
    }
    if($session.Backend -ne $cfg.Backend -or
       $session.TestProfile -ne $cfg.Profile -or
       $session.VariantId -ne $actualVariant){
        throw "Slot preparation session identity mismatch for $slot"
    }
    # The manifest and the actual installed backend marker must agree.
    $active=Get-Active
    if($active.backend -ne $cfg.Backend -or
       $active.variant -ne $actualVariant -or
       $active.profile -ne $cfg.Profile){
        throw "Slot preparation active backend identity mismatch for $slot"
    }
}

function Start-Slot([string]$slot){
    Prepare-Slot $slot
    $cfg=$slots[$slot]
    $gpuSetting = if ($gpuCheck.Checked) { 'ON' } else { 'OFF' }
    if ($gpuSetting -eq 'ON' -and $cfg.Backend -ne 'd3d9') { throw 'GPU detailed profiling is DX9Ex-only.' }
    $vehicleScale=if($cfg.Contains('Scale')){[string]$cfg.Scale}else{'DEFAULT'}
    $glassProbe=if($cfg.Contains('Scale')){[string]$glassProbeBox.SelectedItem}else{'DEFAULT'}
    $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,'-TestProfile',$cfg.Profile,'-GpuDiagnostics',$gpuSetting,'-CockpitVehicleScale',$vehicleScale,'-CockpitGlassProbeOpacity',$glassProbe)
    # Start-Process joins string[] arguments without quoting the -File value.
    # Quote the full script path; OutRun is often installed under a folder
    # containing spaces. The runner trap writes a launch error + modal dialog.
    $quotedRunner = '"' + $runner + '"'
    $launchArgs = "-NoProfile -ExecutionPolicy Bypass -File $quotedRunner -TestProfile $($cfg.Profile) -GpuDiagnostics $gpuSetting -CockpitVehicleScale $vehicleScale -CockpitGlassProbeOpacity $glassProbe"
    Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList $launchArgs -WorkingDirectory $root -WindowStyle Normal -ErrorAction Stop
}

$form=New-Object System.Windows.Forms.Form
$form.Text='OutRun VR Slot Selector V2'
$form.StartPosition='CenterScreen'
$form.ClientSize=New-Object System.Drawing.Size(620,840)
$form.AutoScroll=$true
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false

$title=New-Object System.Windows.Forms.Label
$title.Text='OutRun VR Slot Selector V2'
$title.Font=New-Object System.Drawing.Font('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=New-Object System.Drawing.Point(145,18)
$form.Controls.Add($title)

$desc=New-Object System.Windows.Forms.Label
$desc.Text='슬롯 버튼 하나로 바이너리 + 설정 + 프로필 + 로그 이름을 같이 변경합니다. 게임 종료 후 로그 ZIP과 자동 분석 요약을 생성합니다.'
$desc.AutoSize=$false
$desc.Size=New-Object System.Drawing.Size(550,46)
$desc.Location=New-Object System.Drawing.Point(35,55)
$form.Controls.Add($desc)

$status=New-Object System.Windows.Forms.Label
$status.AutoSize=$false
$status.Size=New-Object System.Drawing.Size(550,28)
$status.Location=New-Object System.Drawing.Point(35,105)
$status.Font=New-Object System.Drawing.Font('Segoe UI',10,[System.Drawing.FontStyle]::Bold)
$form.Controls.Add($status)

function Refresh-Status {
    $a=Get-Active
    $status.Text="현재: $($a.variant) / $($a.backend) / $($a.profile)"
}
Refresh-Status

$y=145
foreach($slot in $slots.Keys){
    $cfg=$slots[$slot]
    $btn=New-Object System.Windows.Forms.Button
    $btn.Text=$cfg.Title
    $btn.Size=New-Object System.Drawing.Size(255,46)
    $btn.Location=New-Object System.Drawing.Point(35,$y)
    $btn.Tag=$slot
    # The DX9Ex ACTIVE test ZIP intentionally ships one shared backends/d3d9
    # executable pair, not separate slots/A_CONTROL, slots/B_HUD, etc.  The
    # backend selector already falls back to that pair for each HUD profile.
    # Enable a button only when its *effective* payload can actually launch.
    $slotPath=Join-Path $root ("slots/"+$slot)
    $backendPath=Join-Path $root 'backends/d3d9'
    $effectivePath=if($cfg.Backend -eq 'd3d9' -and ($slot -eq 'R84_TEST' -or $slot -eq 'R26_SAFE')) {
        $slotPath
    } elseif($cfg.Backend -eq 'd3d9') {
        # Canonical R26 baseline for HUD and performance comparisons.
        $backendPath
    } elseif(Test-Path $slotPath) {
        $slotPath
    } else {
        $backendPath
    }
    $hasPayload=(Test-Path (Join-Path $effectivePath 'dinput8.dll')) -and (Test-Path (Join-Path $effectivePath 'outrun-vr-host.exe'))
    if($cfg.Backend -eq 'dxvk-safe') {
        # SAFE mode additionally needs its independent DXVK x86 provider.
        $hasPayload=$hasPayload -and (Test-Path (Join-Path $root 'backends/dxvk/d3d9.dll'))
    }
    if(-not $hasPayload) {
        $btn.Enabled=$false
        $btn.Text+=' (payload 없음)'
    }
    $btn.Add_Click({
        try{
            Prepare-Slot ([string]$this.Tag)
            Refresh-Status
            $cfg=$slots[[string]$this.Tag]
            $helpBox.Text="$($cfg.Title)
$($cfg.Help)

설정 완료. 아래 실행 버튼을 누르세요."
        }catch{
            [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'슬롯 전환 실패')|Out-Null
        }
    })
    $form.Controls.Add($btn)

    $run=New-Object System.Windows.Forms.Button
    $run.Text='설정 + 바로 실행'
    $run.Size=New-Object System.Drawing.Size(140,46)
    $run.Location=New-Object System.Drawing.Point(300,$y)
    $run.Tag=$slot
    $run.Enabled=$btn.Enabled
    $run.Add_Click({
        try{
            # Do not keep the selector or the PowerShell console above the game.
            $form.WindowState=[System.Windows.Forms.FormWindowState]::Minimized
            Start-Slot ([string]$this.Tag)
            Refresh-Status
        }catch{
            $form.WindowState=[System.Windows.Forms.FormWindowState]::Normal
            [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'실행 실패')|Out-Null
        }
    })
    $form.Controls.Add($run)

    $profile=New-Object System.Windows.Forms.Label
    $profile.Text="$($cfg.Backend) / $($cfg.Profile)"
    $profile.AutoSize=$true
    $profile.Location=[System.Drawing.Point]::new(450, ($y + 14))
    $form.Controls.Add($profile)
    $y+=58
}
# An added R84 row must never overlap diagnostics, help or the collector note.
# Keep the window usable on 1080p displays; extra test rows scroll.
$form.ClientSize=[System.Drawing.Size]::new(620,840)

$gpuCheck=New-Object System.Windows.Forms.CheckBox
$gpuCheck.Text='GPU 상세 진단 (타임스탬프 + 투명/깊이 + VR 페이싱 + NVIDIA GPU 사용률)'
$gpuCheck.Checked=$false
$gpuCheck.AutoSize=$false
$gpuCheck.Size=New-Object System.Drawing.Size(570,30)
$gpuCheck.Location=[System.Drawing.Point]::new(35, [int]($y+12))
$form.Controls.Add($gpuCheck)


$glassProbeLabel=New-Object System.Windows.Forms.Label
$glassProbeLabel.Text='유리 불투명도 후보 (진단값만 기록, 실제 렌더 미적용)'
$glassProbeLabel.AutoSize=$true
$glassProbeLabel.Location=[System.Drawing.Point]::new(35,[int]($y+53))
$form.Controls.Add($glassProbeLabel)
$glassProbeBox=New-Object System.Windows.Forms.ComboBox
$glassProbeBox.DropDownStyle='DropDownList'
foreach($value in @('0.20','0.30','0.50','0.80')){[void]$glassProbeBox.Items.Add($value)}
$glassProbeBox.SelectedItem='0.30'
$glassProbeBox.Size=New-Object System.Drawing.Size(130,26)
$glassProbeBox.Location=[System.Drawing.Point]::new(35,[int]($y+78))
$form.Controls.Add($glassProbeBox)

# PC game/PMT assets are immutable in the DX9Ex cockpit workflow.
# The legacy disk-model patch controls were deliberately removed. Live
# runtime glass alpha remains gated on verified player windshield ownership.
$helpBox=New-Object System.Windows.Forms.TextBox
$helpBox.Multiline=$true
$helpBox.ReadOnly=$true
$helpBox.ScrollBars='Vertical'
$helpBox.Size=New-Object System.Drawing.Size(550,92)
$helpBox.Location=[System.Drawing.Point]::new(35, [int]($y+176))
$helpBox.Text='A/B/C 운전석은 모두 ON, 차체 배율만 100/115/130% 비교. 일반 CURRENT_FOCUS는 운전석 OFF 대조군. 테스트 종료 후 다시 선택하면 매번 새로운 로그가 분리 저장됩니다. F11에서 위치/배율도 조절 가능합니다. 운전석 기본 ON. F11 > VR > DriverSeatVehicleScale로 차량 크기 조절. F11의 DriverSeatGlassOpacity는 현재 진단 설정이며 유리에 적용되지 않습니다. 원본 차량 PMT·EXE 수정 금지에 따라 파일 변경 버튼은 제거했습니다. 재질 식별을 위해 DriverSeatGlassMaterialTrace를 켜고 재실행 후 로그 ZIP을 확인하세요. Quest3/VDXR 실기 검증 전에는 유리 효과를 보장하지 않습니다.'
$form.Controls.Add($helpBox)

$note=New-Object System.Windows.Forms.Label
$note.Text='게임 종료 후 collector가 자동 실행되어 OutRun2_VR_ANALYZE_<slot>_<profile>_<session>.zip 을 만듭니다.'
$note.AutoSize=$false
$note.Size=New-Object System.Drawing.Size(550,40)
$note.Location=[System.Drawing.Point]::new(35, [int]($y+283))
$form.Controls.Add($note)

[void]$form.ShowDialog()
