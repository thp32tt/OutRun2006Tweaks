# Dedicated GPU measurement GUI (separate ZIP).
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
if(!(Test-Path $runner) -or !(Test-Path $selector)){throw 'GPU lab runner/selector missing'}

$form=New-Object System.Windows.Forms.Form
$form.Text='OutRun 2006 VR - GPU Performance Lab'
$form.StartPosition='CenterScreen'
$form.ClientSize=[System.Drawing.Size]::new(655,675)
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false
function Add-Label([string]$name,[int]$y){
    $x=New-Object System.Windows.Forms.Label
    $x.Text=$name
    $x.Location=[System.Drawing.Point]::new(28,$y)
    $x.Size=[System.Drawing.Size]::new(215,30)
    $x.Font=[System.Drawing.Font]::new('Segoe UI',10)
    $form.Controls.Add($x)
}
function Add-Choice([int]$y,[string[]]$items,[int]$index){
    $x=New-Object System.Windows.Forms.ComboBox
    $x.DropDownStyle='DropDownList'
    $x.Location=[System.Drawing.Point]::new(252,$y)
    $x.Size=[System.Drawing.Size]::new(360,29)
    [void]$x.Items.AddRange([object[]]$items)
    $x.SelectedIndex=$index
    $form.Controls.Add($x)
    return $x
}
$heading=New-Object System.Windows.Forms.Label
$heading.Text='DX9Ex | GPU Performance Measurement'
$heading.Font=[System.Drawing.Font]::new('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$heading.Location=[System.Drawing.Point]::new(28,14)
$heading.Size=[System.Drawing.Size]::new(604,40)
$form.Controls.Add($heading)
$hint=New-Object System.Windows.Forms.Label
$hint.Text='옵션 선택 → GPU 측정 시작 → 동일 물가/모래/건물 구간 주행 → 로그 ZIP 자동 생성'
$hint.Location=[System.Drawing.Point]::new(28,60)
$hint.Size=[System.Drawing.Size]::new(615,34)
$form.Controls.Add($hint)
Add-Label 'A/B 프리셋' 105
$preset=Add-Choice 102 @('A 기준','B 컬링 ON','C 권장 - 컬링 ON / SSAA OFF','D 반사 512','E SkyGlow OFF','사용자 지정') 0
Add-Label '반투명 SSAA' 151
$alpha=Add-Choice 148 @('ON 기준 화질','OFF 비용 비교') 0
Add-Label '반사 해상도' 197
$reflection=Add-Choice 194 @('1024','512') 0
Add-Label 'SkyGlow / bloom' 243
$sky=Add-Choice 240 @('4 기준','0 비활성화 진단') 0
Add-Label '스테이지 컬링' 289
$culling=Add-Choice 286 @('OFF 기준','ON 비용 비교') 0
Add-Label 'VR MSAA (GPU 비용)' 335
$msaa=Add-Choice 332 @('4x 원래 VR 기본값','2x GPU 비교','OFF GPU 비교') 0
Add-Label '주행 구간' 381
$scene=Add-Choice 378 @('WATERFRONT','SAND_SPRAY','DENSE_BUILDINGS','OTHER') 0

$script:updating=$false
$preset.Add_SelectedIndexChanged({
    if($script:updating -or $preset.SelectedIndex -ge 5){return}
    $script:updating=$true
    try {
        $alpha.SelectedIndex=if($preset.SelectedIndex -in @(2,3)){1}else{0}
        $reflection.SelectedIndex=if($preset.SelectedIndex -eq 3){1}else{0}
        $sky.SelectedIndex=if($preset.SelectedIndex -eq 4){1}else{0}
        $culling.SelectedIndex=if($preset.SelectedIndex -ge 1){1}else{0}
    } finally {$script:updating=$false}
})
foreach($ctrl in @($alpha,$reflection,$sky,$culling,$msaa)){
    $ctrl.Add_SelectedIndexChanged({
        if(!$script:updating -and $preset.SelectedIndex -ne 5){
            $script:updating=$true
            try{$preset.SelectedIndex=5}finally{$script:updating=$false}
        }
    })
}
$note=New-Object System.Windows.Forms.Label
$note.Text='A~E 비교는 계측 ON입니다. 실측 권장 C를 계측 OFF로 실행하려면 아래 성능 주행 버튼을 사용하세요.'
$note.Location=[System.Drawing.Point]::new(28,438)
$note.Size=[System.Drawing.Size]::new(590,50)
$form.Controls.Add($note)
$start=New-Object System.Windows.Forms.Button
$start.Text='A~E 성능 측정 (계측 ON)'
$start.Location=[System.Drawing.Point]::new(28,507)
$start.Size=[System.Drawing.Size]::new(385,49)
$start.Font=[System.Drawing.Font]::new('Segoe UI',11,[System.Drawing.FontStyle]::Bold)
$form.Controls.Add($start)
$quit=New-Object System.Windows.Forms.Button
$quit.Text='닫기'
$quit.Location=[System.Drawing.Point]::new(445,507)
$quit.Size=[System.Drawing.Size]::new(164,49)
$quit.Add_Click({$form.Close()})
$form.Controls.Add($quit)
$start.Add_Click({
    try {
        if(!(Test-Path (Join-Path $root 'OR2006C2C.EXE'))){throw '원본 OR2006C2C.EXE가 있는 폴더에 ZIP을 압축해제하세요.'}
        if(Get-Process -Name OR2006C2C -ErrorAction SilentlyContinue){throw '게임이 이미 실행 중입니다.'}
        $a=if($alpha.SelectedIndex -eq 0){'ON'}else{'OFF'}
        $r=if($reflection.SelectedIndex -eq 0){'1024'}else{'512'}
        $g=if($sky.SelectedIndex -eq 0){'4'}else{'0'}
        $c=if($culling.SelectedIndex -eq 0){'OFF'}else{'ON'}
        $aa=@('4X','2X','OFF')[$msaa.SelectedIndex]
        $tag=@('WATERFRONT','SAND_SPRAY','DENSE_BUILDINGS','OTHER')[$scene.SelectedIndex]
        & $selector -Backend d3d9 -TestProfile PERFORMANCE -VariantId CURRENT_FOCUS
        if($LASTEXITCODE -and $LASTEXITCODE -ne 0){throw 'DX9Ex 백엔드 준비 실패'}
        $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',
            ('"{0}"' -f $runner),'-TestProfile','PERFORMANCE','-GpuDiagnostics','ON',
            '-GpuLabTransparency',$a,'-GpuLabReflection',$r,
            '-GpuLabSkyGlow',$g,'-GpuLabCulling',$c,'-GpuLabMsaa',$aa,'-GpuLabScene',$tag)
        $p=Start-Process -FilePath 'powershell.exe' -ArgumentList $args -WorkingDirectory $root -PassThru
        if(!$p){throw '게임 측정 프로세스 시작 실패'}
        $form.WindowState=[System.Windows.Forms.FormWindowState]::Minimized
    }catch{
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'GPU 측정 실행 실패')|Out-Null
        $form.WindowState=[System.Windows.Forms.FormWindowState]::Normal
    }
})
# Start with the best measured A~E trial while preserving the full matrix.
# Assign after the selection callbacks exist so C's toggles are synchronized.
$preset.SelectedIndex=2
$production=New-Object System.Windows.Forms.Button
$production.Text='권장 C 실주행 (GPU 계측 OFF / HUD 검사 OFF)'
$production.Location=[System.Drawing.Point]::new(28,568)
$production.Size=[System.Drawing.Size]::new(581,46)
$production.Font=[System.Drawing.Font]::new('Segoe UI',10,[System.Drawing.FontStyle]::Bold)
$form.Controls.Add($production)
$production.Add_Click({
    try {
        if(!(Test-Path (Join-Path $root 'OR2006C2C.EXE'))){throw '원본 OR2006C2C.EXE가 있는 게임 폴더에서 실행하세요.'}
        if(Get-Process -Name OR2006C2C -ErrorAction SilentlyContinue){throw '게임이 이미 실행 중입니다.'}
        & $selector -Backend d3d9 -TestProfile PERFORMANCE -VariantId CURRENT_FOCUS
        if($LASTEXITCODE -and $LASTEXITCODE -ne 0){throw 'DX9Ex 백엔드 준비 실패'}
        $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',
            ('"{0}"' -f $runner),'-TestProfile','PERFORMANCE','-GpuDiagnostics','OFF',
            '-GpuLabTransparency','OFF','-GpuLabReflection','1024',
            '-GpuLabSkyGlow','4','-GpuLabCulling','ON',
            '-GpuLabMsaa','4X','-GpuLabScene','OTHER')
        $p=Start-Process -FilePath 'powershell.exe' -ArgumentList $args -WorkingDirectory $root -PassThru
        if(!$p){throw '계측 OFF 실주행 프로세스 시작 실패'}
        $form.WindowState=[System.Windows.Forms.FormWindowState]::Minimized
    }catch{
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'성능 주행 실행 실패')|Out-Null
        $form.WindowState=[System.Windows.Forms.FormWindowState]::Normal
    }
})
[void]$form.ShowDialog()
