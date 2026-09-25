Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'

$slots=[ordered]@{
    'CURRENT_FOCUS'=[ordered]@{Backend='d3d9';Profile='CORRECTNESS';Title='CURRENT FOCUS / CORRECTNESS';Help='최신 통합본. 기본 시점/월드/HUD 전체 확인.'}
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
    $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$selector,
        '-Backend',$cfg.Backend,'-TestProfile',$cfg.Profile,'-VariantId',$slot)
    $p=Start-Process powershell -Wait -PassThru -WindowStyle Hidden -ArgumentList $args
    if($p.ExitCode -ne 0){throw "Slot preparation failed: $slot"}
}

function Start-Slot([string]$slot){
    Prepare-Slot $slot
    $cfg=$slots[$slot]
    $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,'-TestProfile',$cfg.Profile)
    Start-Process powershell -ArgumentList $args -WorkingDirectory $root
}

$form=New-Object System.Windows.Forms.Form
$form.Text='OutRun VR Slot Selector V2'
$form.StartPosition='CenterScreen'
$form.ClientSize=[System.Drawing.Size]::new(620,720)
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false

$title=New-Object System.Windows.Forms.Label
$title.Text='OutRun VR Slot Selector V2'
$title.Font=New-Object System.Drawing.Font('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=[System.Drawing.Point]::new(145,18)
$form.Controls.Add($title)

$desc=New-Object System.Windows.Forms.Label
$desc.Text='슬롯 버튼 하나로 바이너리 + 설정 + 프로필 + 로그 이름을 같이 변경합니다. 게임 종료 후 로그 ZIP과 자동 분석 요약을 생성합니다.'
$desc.AutoSize=$false
$desc.Size=[System.Drawing.Size]::new(550,46)
$desc.Location=[System.Drawing.Point]::new(35,55)
$form.Controls.Add($desc)

$status=New-Object System.Windows.Forms.Label
$status.AutoSize=$false
$status.Size=[System.Drawing.Size]::new(550,28)
$status.Location=[System.Drawing.Point]::new(35,105)
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
    $btn.Size=[System.Drawing.Size]::new(255,46)
    $btn.Location=[System.Drawing.Point]::new(35,$y)
    $btn.Tag=$slot
    if($slot -notin @('CURRENT_FOCUS','E_DXVK_SAFE','G_COCKPIT')){
        $slotPath=Join-Path $root ("slots/"+$slot)
        if(!(Test-Path $slotPath)){
            $btn.Enabled=$false
            $btn.Text+=' (payload 없음)'
        }
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
    $run.Size=[System.Drawing.Size]::new(140,46)
    $run.Location=[System.Drawing.Point]::new(300,$y)
    $run.Tag=$slot
    $run.Enabled=$btn.Enabled
    $run.Add_Click({
        try{
            Start-Slot ([string]$this.Tag)
            Refresh-Status
        }catch{
            [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'실행 실패')|Out-Null
        }
    })
    $form.Controls.Add($run)

    $profile=New-Object System.Windows.Forms.Label
    $profile.Text="$($cfg.Backend) / $($cfg.Profile)"
    $profile.AutoSize=$true
    $profile.Location=[System.Drawing.Point]::new(450,($y+14))
    $form.Controls.Add($profile)
    $y+=58
}

$helpBox=New-Object System.Windows.Forms.TextBox
$helpBox.Multiline=$true
$helpBox.ReadOnly=$true
$helpBox.ScrollBars='Vertical'
$helpBox.Size=[System.Drawing.Size]::new(550,92)
$helpBox.Location=[System.Drawing.Point]::new(35,560)
$helpBox.Text='권장: CURRENT_FOCUS -> A_CONTROL -> D_PERF -> B_HUD -> C_FLARE. G_COCKPIT은 별도 카메라 실험입니다. E_DXVK_SAFE는 현재 SBS fallback이 확인되어 진단용입니다.'
$form.Controls.Add($helpBox)

$note=New-Object System.Windows.Forms.Label
$note.Text='게임 종료 후 collector가 자동 실행되어 OutRun2_VR_ANALYZE_<slot>_<profile>_<session>.zip 을 만듭니다.'
$note.AutoSize=$false
$note.Size=[System.Drawing.Size]::new(550,40)
$note.Location=[System.Drawing.Point]::new(35,665)
$form.Controls.Add($note)

[void]$form.ShowDialog()
