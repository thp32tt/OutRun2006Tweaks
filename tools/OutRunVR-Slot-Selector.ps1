Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'

$slots=[ordered]@{
    'CURRENT_FOCUS'=[ordered]@{Backend='d3d9';Profile='CORRECTNESS';Title='MAIN R84 / R29-R33';Help='기본 구조 개선 렌더러. Quest3 검증 필요.'}
    'R26_SAFE'=[ordered]@{Backend='d3d9';Profile='CORRECTNESS';Title='R26 SAFE / 기존 보호판';Help='기존 R26+HUD 렌더러 복귀. CURRENT FOCUS로 R84 재선택.'}
    'R84_TEST'=[ordered]@{Backend='d3d9';Profile='CORRECTNESS';Title='R84 TEST / 개편 경로';Help='기본 R84와 동일한 독립 렌더러 A/B 진단.'}
    'A_CONTROL'=[ordered]@{Backend='d3d9';Profile='CONTROL';Title='A CONTROL / R51 기준';Help='R51 보호 기준 비교.'}
    'B_HUD'=[ordered]@{Backend='d3d9';Profile='HUD_SCREEN';Title='B HUD';Help='6th/6, YES/NO, 시간/랭크 HUD 확인.'}
    'C_FLARE'=[ordered]@{Backend='d3d9';Profile='HUD_WORLD';Title='C FLARE / WORLD';Help='렌즈 플레어/월드 마커 producer 진단.'}
    'D_PERF'=[ordered]@{Backend='d3d9';Profile='PERFORMANCE';Title='D PERFORMANCE';Help='프레임 페이싱/fence telemetry.'}
    'G_COCKPIT'=[ordered]@{Backend='d3d9';Profile='CORRECTNESS';Title='G COCKPIT (실험)';Help='운전석 카메라만 별도로 활성화.'}
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
    & $selector -Backend $cfg.Backend -TestProfile $cfg.Profile -VariantId $slot
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
       $session.VariantId -ne $slot){
        throw "Slot preparation session identity mismatch for $slot"
    }
    # The manifest and the actual installed backend marker must agree.
    $active=Get-Active
    if($active.backend -ne $cfg.Backend -or
       $active.variant -ne $slot -or
       $active.profile -ne $cfg.Profile){
        throw "Slot preparation active backend identity mismatch for $slot"
    }
}

function Start-Slot([string]$slot){
    Prepare-Slot $slot
    $cfg=$slots[$slot]
    $gpuSetting = if ($gpuCheck.Checked) { 'ON' } else { 'OFF' }
    if ($gpuSetting -eq 'ON' -and $cfg.Backend -ne 'd3d9') { throw 'GPU detailed profiling is DX9Ex-only.' }
    $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,'-TestProfile',$cfg.Profile,'-GpuDiagnostics',$gpuSetting)
    # Start-Process joins string[] arguments without quoting the -File value.
    # Quote the full script path; OutRun is often installed under a folder
    # containing spaces. The runner trap writes a launch error + modal dialog.
    $quotedRunner = '"' + $runner + '"'
    $launchArgs = "-NoProfile -ExecutionPolicy Bypass -File $quotedRunner -TestProfile $($cfg.Profile) -GpuDiagnostics $gpuSetting"
    Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList $launchArgs -WorkingDirectory $root -WindowStyle Normal -ErrorAction Stop
}

$form=New-Object System.Windows.Forms.Form
$form.Text='OutRun VR Slot Selector V2'
$form.StartPosition='CenterScreen'
$form.ClientSize=New-Object System.Drawing.Size(620,795)
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
$form.ClientSize=[System.Drawing.Size]::new(620, [int]($y+225))

$gpuCheck=New-Object System.Windows.Forms.CheckBox
$gpuCheck.Text='GPU 상세 진단 (타임스탬프 + 투명/깊이 + VR 페이싱 + NVIDIA GPU 사용률)'
$gpuCheck.Checked=$false
$gpuCheck.AutoSize=$false
$gpuCheck.Size=New-Object System.Drawing.Size(570,30)
$gpuCheck.Location=[System.Drawing.Point]::new(35, [int]($y+12))
$form.Controls.Add($gpuCheck)

$helpBox=New-Object System.Windows.Forms.TextBox
$helpBox.Multiline=$true
$helpBox.ReadOnly=$true
$helpBox.ScrollBars='Vertical'
$helpBox.Size=New-Object System.Drawing.Size(550,92)
$helpBox.Location=[System.Drawing.Point]::new(35, [int]($y+52))
$helpBox.Text='권장: D PERFORMANCE + GPU 상세 진단 체크 → 물가/모래/건물 동일 구간 측정. 기본 OFF. DX9Ex 전용이며 로그 ZIP 자동 수집. 기존 A/B 옵션은 반투명 SSAA와 반사 해상도 비교에 사용.'
$form.Controls.Add($helpBox)

$note=New-Object System.Windows.Forms.Label
$note.Text='게임 종료 후 collector가 자동 실행되어 OutRun2_VR_ANALYZE_<slot>_<profile>_<session>.zip 을 만듭니다.'
$note.AutoSize=$false
$note.Size=New-Object System.Drawing.Size(550,40)
$note.Location=[System.Drawing.Point]::new(35, [int]($y+167))
$form.Controls.Add($note)

[void]$form.ShowDialog()
